#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step5_post_classification_industry_relevance_flags_multiyear.py

POST-PROCESSING: add two keyword-based flag columns to the Stage 2 classified
climate biotech dataset. Structure and keyword lists are intentionally
identical to the biomining pipeline's `add_keyword_flags_multiyear.py` so the
two analyses share methodology.

Runs AFTER step3_..._two_stage_classifier_multiyear.py (and optional step4).

Input:  scripts/grant_classifier/output/stage2_characterized_all_years.csv
Output: scripts/grant_classifier/output/stage2_characterized_all_years_with_industry_framing.csv
        (same filename as before — downstream scripts don't need to change)

Produces two new boolean columns:
  1. industry_framing     — TEA, LCA, commercial viability, cost/market language
  2. open_access_sharing  — open-access, data-sharing, shared-facility language

No grant-type- or orientation-aware overrides: both flags are pure
word-boundary keyword matches against the grant abstract. That matches
the biomining methodology. (Earlier climate biotech versions of this step
had type-aware logic for industry_framing — removed for parity with
biomining so that cross-analysis comparisons are apples-to-apples.)

Runtime: ~1–2 minutes on the full dataset (no LLM calls).
"""

import re
from pathlib import Path
from typing import List

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/grant_classifier/
PROJECT_ROOT = SCRIPT_DIR.parent.parent       # climate_biotech_federal_grant_funding/

OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

INFILE = OUTPUT_DIR / "stage2_characterized_all_years.csv"
OUTFILE = OUTPUT_DIR / "stage2_characterized_all_years_with_industry_framing.csv"


# =============================================================================
# KEYWORD LISTS — identical to biomining pipeline's add_keyword_flags_multiyear.py
# =============================================================================

# INDUSTRY FRAMING — 17 keywords
INDUSTRY_KEYWORDS: List[str] = [
    # Techno-economic analysis
    "techno-economic analysis",
    "technoeconomic",
    "TEA",

    # Life cycle assessment
    "life cycle assessment",
    "lifecycle assessment",
    "LCA",

    # Economic viability
    "economic feasibility",
    "economic viability",

    # Commercial viability
    "commercial feasibility",
    "commercial viability",
    "commercialization pathway",

    # Cost analysis
    "cost analysis",
    "cost-benefit analysis",

    # Scalability & market
    "scalability analysis",
    "scale-up economics",
    "market analysis",
    "market potential",
]

# OPEN ACCESS / SHARING — 29 keywords
SHARING_KEYWORDS: List[str] = [
    # Open access
    "open access",
    "open-access",
    "openly available",
    "publicly available",
    "public access",
    "free access",

    # Shared resources
    "shared facility",
    "shared platform",
    "shared resource",
    "shared database",
    "shared infrastructure",
    "community resource",
    "community facility",
    "community platform",

    # Data sharing
    "data sharing",
    "data repository",
    "open data",
    "open source",
    "open-source",

    # Availability language
    "available to researchers",
    "available to the community",
    "available to the public",
    "made available",
    "will be shared",
    "will be made available",

    # Collaborative access
    "collaborative facility",
    "multi-user facility",
    "user facility",
    "shared access",
]


# =============================================================================
# HELPERS
# =============================================================================
def normalize_text(text) -> str:
    """Lowercase, collapse whitespace. NaN → empty string."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text


def has_keyword(abstract, keywords: List[str]) -> bool:
    """Case-insensitive word-boundary match for any keyword in list."""
    if pd.isna(abstract):
        return False
    normalized = normalize_text(abstract)
    for keyword in keywords:
        norm_kw = normalize_text(keyword)
        pattern = r"\b" + re.escape(norm_kw) + r"\b"
        if re.search(pattern, normalized):
            return True
    return False


def find_matching_keywords(abstract, keywords: List[str]) -> List[str]:
    """Return list of keywords from `keywords` that appear in `abstract`."""
    if pd.isna(abstract):
        return []
    normalized = normalize_text(abstract)
    matched = []
    for keyword in keywords:
        norm_kw = normalize_text(keyword)
        pattern = r"\b" + re.escape(norm_kw) + r"\b"
        if re.search(pattern, normalized):
            matched.append(keyword)
    return matched


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 80)
    print("STEP 5 — KEYWORD FLAGS (industry_framing + open_access_sharing)")
    print("=" * 80)
    print()

    if not INFILE.exists():
        print(f"❌ Input not found: {INFILE}")
        print("   Run step3_climate_biotech_two_stage_classifier_multiyear.py first.")
        return

    print(f"Loading: {INFILE}")
    df = pd.read_csv(INFILE, low_memory=False)
    print(f"✓ Loaded {len(df):,} rows")
    print()

    required = ["abstract"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"❌ Missing required column(s): {missing}")
        return

    # ---- Keyword lists ----
    print("Keyword lists:")
    print(f"  Industry framing:     {len(INDUSTRY_KEYWORDS)} keywords")
    print(f"  Open access / sharing: {len(SHARING_KEYWORDS)} keywords")
    print()

    # ---- Apply flags ----
    print("Scanning abstracts...")
    df["industry_framing"] = df["abstract"].apply(
        lambda x: has_keyword(x, INDUSTRY_KEYWORDS)
    )
    industry_count = int(df["industry_framing"].sum())
    print(f"  ✓ industry_framing:     {industry_count:,} / {len(df):,} "
          f"({industry_count / len(df) * 100:.1f}%)")

    df["open_access_sharing"] = df["abstract"].apply(
        lambda x: has_keyword(x, SHARING_KEYWORDS)
    )
    sharing_count = int(df["open_access_sharing"].sum())
    print(f"  ✓ open_access_sharing:  {sharing_count:,} / {len(df):,} "
          f"({sharing_count / len(df) * 100:.1f}%)")
    print()

    # ---- Breakdown by grant type (if available) ----
    if "s2_grant_type" in df.columns:
        print("Flag rates by grant type:")
        print(f"  {'Grant Type':<20}{'n':>8}{'industry':>12}{'open-access':>14}")
        print(f"  {'-' * 54}")
        for gt in sorted(df["s2_grant_type"].dropna().unique()):
            subset = df[df["s2_grant_type"] == gt]
            n = len(subset)
            ind = int(subset["industry_framing"].sum())
            shr = int(subset["open_access_sharing"].sum())
            print(f"  {str(gt):<20}{n:>8,}"
                  f"{ind:>8,} ({ind / n * 100:>3.0f}%)"
                  f"{shr:>10,} ({shr / n * 100:>3.0f}%)")
        print()

    # ---- Verification sample ----
    print("Verification — one flagged grant per category:")
    ind_flagged = df[df["industry_framing"]]
    if len(ind_flagged) > 0:
        sample = ind_flagged.iloc[0]
        matched = find_matching_keywords(sample.get("abstract"), INDUSTRY_KEYWORDS)
        title = str(sample.get("title", "(no title)"))[:80]
        print(f"  industry_framing:")
        print(f"    Title:    {title}")
        print(f"    Matched:  {matched[:3]}")

    shr_flagged = df[df["open_access_sharing"]]
    if len(shr_flagged) > 0:
        sample = shr_flagged.iloc[0]
        matched = find_matching_keywords(sample.get("abstract"), SHARING_KEYWORDS)
        title = str(sample.get("title", "(no title)"))[:80]
        print(f"  open_access_sharing:")
        print(f"    Title:    {title}")
        print(f"    Matched:  {matched[:3]}")
    print()

    # ---- Save ----
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTFILE, index=False)
    print(f"✓ Saved: {OUTFILE.name}")
    print(f"  Rows: {len(df):,}")
    print(f"  New columns: industry_framing (bool), open_access_sharing (bool)")
    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
