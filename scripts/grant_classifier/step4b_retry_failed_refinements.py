"""
step4b_retry_failed_refinements.py

Troubleshooting tool for step 4 (refine_stage2_classifications_multiyear).

When step 4 runs at scale, a small fraction of batches fail due to transient
Anthropic API issues — empty response.content, JSON parse errors, ID drift, or
the LLM dropping items from a batch. Those grants keep their pre-refinement
Stage 2 classifications instead of getting refined.

This script:
  1. Reads `refinement_log.json` produced by step 4 and identifies every grant
     ID that didn't successfully make it through refinement.
  2. Excludes IDs already handled by previous runs of this retry script (tracked
     in `refinement_retry_log.json`).
  3. Re-calls the refinement API on each remaining grant at BATCH_SIZE = 1
     (eliminates ID/count mismatch failure modes entirely).
  4. Saves progress after EACH successful grant — both the CSV and the retry
     log — so that Ctrl-C or a crash loses no work.

Usage:
    python3 scripts/grant_classifier/step4b_retry_failed_refinements.py

Re-running is safe and idempotent. Each run targets only the grants still
outstanding. Most transient API failures clear within 15–30 minutes; two or
three passes usually reach zero failures. Grants that persistently fail
typically trigger some content-filter or token issue and need to be classified
by hand (~5 minutes for a handful of abstracts).

Prompt source:
    Imports REFINEMENT_SYSTEM_PROMPT from step 4. No prompt drift possible —
    if you update step 4's prompt, this script picks it up automatically.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm
import anthropic

# =============================================================================
# PATHS
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
PROJECT_ROOT = SCRIPT_DIR.parent.parent

CURRENT_FILE = OUTPUT_DIR / "stage2_characterized_all_years.csv"
REFINEMENT_LOG = OUTPUT_DIR / "refinement_log.json"
RETRY_LOG = OUTPUT_DIR / "refinement_retry_log.json"
PRE_RERUN_BACKUP = OUTPUT_DIR / "stage2_characterized_all_years_backup_before_retry.csv"

# =============================================================================
# IMPORT PROMPT FROM STEP 4 (no drift)
# =============================================================================
sys.path.insert(0, str(SCRIPT_DIR))
from step4_refine_stage2_classifications_multiyear import REFINEMENT_SYSTEM_PROMPT  # noqa: E402

# =============================================================================
# SETTINGS (conservative — retry prioritizes reliability over speed)
# =============================================================================
REFINE_MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 1
MAX_TOKENS = 4096
SLEEP_S = 2.5
MAX_RETRIES = 5


# =============================================================================
# API KEY
# =============================================================================
def _load_api_key():
    for candidate in (PROJECT_ROOT / ".env", SCRIPT_DIR / ".env", Path.home() / ".env"):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    raise RuntimeError(
        "No ANTHROPIC_API_KEY found. Set environment variable or .env file."
    )


# =============================================================================
# FAILURE DETECTION
# =============================================================================
def identify_failed_ids_from_log():
    """Parse step 4's refinement_log.json for unambiguously-failed grant IDs."""
    log = json.loads(REFINEMENT_LOG.read_text())
    failed = set()
    stats = {"total_batches": len(log), "api_errors": 0, "partial": 0}

    for entry in log:
        sent = [str(x) for x in entry.get("ids", [])]
        raw = entry.get("raw_response", "") or ""

        if not raw.strip().startswith("["):
            failed.update(sent)
            stats["api_errors"] += 1
            continue

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        try:
            parsed = json.loads(match.group(0)) if match else []
        except json.JSONDecodeError:
            failed.update(sent)
            stats["api_errors"] += 1
            continue

        if not isinstance(parsed, list):
            failed.update(sent)
            stats["api_errors"] += 1
            continue

        got = {str(p.get("grant_id", "")).strip() for p in parsed if isinstance(p, dict)}
        missing = set(sent) - got
        if missing:
            failed.update(missing)
            stats["partial"] += 1

    return failed, stats


def load_retry_log():
    if not RETRY_LOG.exists():
        return set()
    try:
        return set(json.loads(RETRY_LOG.read_text()).get("refined_ids", []))
    except Exception:
        return set()


def checkpoint_retry_log(refined_ids_set):
    RETRY_LOG.write_text(json.dumps({"refined_ids": sorted(refined_ids_set)}, indent=2))


# =============================================================================
# LLM CALL (single grant, mirrors step 4 formatting)
# =============================================================================
def _safe_str(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _build_grant_text(row):
    return f"""Grant ID: {_safe_str(row.get("unique_key"))}
Title: {_safe_str(row.get("title"))}
Abstract: {_safe_str(row.get("abstract"))}

Current Classifications:
- orientation: {_safe_str(row.get("s2_orientation"))}
- grant_type: {_safe_str(row.get("s2_grant_type"))}
- research_stage: {_safe_str(row.get("s2_research_stage"))}
- research_approach: {_safe_str(row.get("s2_research_approach"))}
- infrastructure_subtype: {_safe_str(row.get("s2_infrastructure_subtype"))}
- application_area: {_safe_str(row.get("s2_application_area"))}"""


def refine_one_grant(client, row):
    """Call the refinement API on one grant. Returns (result_dict, ok)."""
    user_msg = "Refine these grant classifications:\n\n" + _build_grant_text(row)
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=REFINE_MODEL,
                max_tokens=MAX_TOKENS,
                system=REFINEMENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            if not response.content or not getattr(response.content[0], "text", None):
                raise RuntimeError("API returned empty response.content")
            text = response.content[0].text
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON array in response: {text[:200]}")
            parsed = json.loads(match.group(0))
            if not isinstance(parsed, list) or not parsed:
                raise ValueError("Empty or non-list JSON response")
            return parsed[0], True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)
            else:
                tqdm.write(f"  failed after {MAX_RETRIES} attempts: {str(e)[:110]}")
                return None, False
    return None, False


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 80)
    print("STEP 4b — RETRY FAILED REFINEMENTS")
    print("=" * 80)

    for required in (CURRENT_FILE, REFINEMENT_LOG):
        if not required.exists():
            sys.exit(f"Missing required file: {required}")

    # ----- Identify targets ---------------------------------------------------
    print("\n[1/4] Reading step 4 refinement_log.json...")
    failed_all, stats = identify_failed_ids_from_log()
    already_refined = load_retry_log()
    to_retry = failed_all - already_refined

    print(f"    Batches in step 4 log:           {stats['total_batches']}")
    print(f"    Fully failed batches:            {stats['api_errors']}")
    print(f"    Partially failed batches:        {stats['partial']}")
    print(f"    Original unique failures:        {len(failed_all)}")
    print(f"    Refined by previous retry runs:  {len(already_refined)}")
    print(f"    Remaining to retry this run:     {len(to_retry)}")

    if not to_retry:
        print("\nAll originally-failed grants have been refined. Nothing to do.")
        return

    # ----- Load CSV, filter to targets ---------------------------------------
    print("\n[2/4] Filtering CSV to target grants...")
    df = pd.read_csv(CURRENT_FILE)
    df["unique_key"] = df["unique_key"].astype(str).str.strip()

    mask = df["unique_key"].isin(to_retry)
    targets = df[mask].drop_duplicates("unique_key").reset_index(drop=True)
    print(f"    Unique grants to refine: {len(targets)}")

    if len(targets) == 0:
        print("    No matching rows found in CSV. Exiting.")
        return

    # ----- Pre-run safety backup ---------------------------------------------
    print("\n[3/4] Writing pre-retry backup...")
    df.to_csv(PRE_RERUN_BACKUP, index=False)
    print(f"    → {PRE_RERUN_BACKUP.name}")

    # ----- Refine (with per-grant checkpoint) --------------------------------
    print(f"\n[4/4] Refining {len(targets)} grants (batch size = {BATCH_SIZE})...")
    client = anthropic.Anthropic(api_key=_load_api_key())

    succeeded = 0
    failed_this_run = []

    for i in tqdm(range(len(targets)), desc="Refining"):
        row = targets.iloc[i]
        gid = str(row["unique_key"]).strip()
        result, ok = refine_one_grant(client, row)

        if ok and result:
            # Broadcast update to all rows with this unique_key (multi-year safe)
            m = df["unique_key"] == gid
            df.loc[m, "s2_grant_type"] = result.get("grant_type")
            df.loc[m, "s2_application_area"] = result.get("application_area")
            df.loc[m, "s2_research_approach"] = result.get("research_approach")
            df.loc[m, "s2_confidence"] = result.get("confidence")

            # Checkpoint: save immediately so Ctrl-C / crash loses nothing
            df.to_csv(CURRENT_FILE, index=False)
            already_refined.add(gid)
            checkpoint_retry_log(already_refined)
            succeeded += 1
        else:
            failed_this_run.append(gid)

        time.sleep(SLEEP_S)

    # ----- Summary -----------------------------------------------------------
    print("\n" + "=" * 80)
    print("RETRY COMPLETE")
    print("=" * 80)
    print(f"Refined this run:               {succeeded} / {len(targets)}")
    print(f"Still failing after this run:   {len(failed_this_run)}")
    print(f"Cumulative refined (all runs):  {len(already_refined)} / {len(failed_all)}")

    if failed_this_run:
        print("\nRun this script again in 15–30 min — transient API issues usually clear.")
        print("Next run will target only the still-failing grants.")
    else:
        print("\nZero failures remaining. Proceed to step 5.")


if __name__ == "__main__":
    main()
