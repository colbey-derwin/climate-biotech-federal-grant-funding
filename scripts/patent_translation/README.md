# Patent Translation Analysis

Downstream analysis that links classified climate biotech grants to the patents their research contributed to, to test which grant characteristics correlate with downstream technology translation.

**Scope:** Restricted to **early-stage** climate biotech grants only — Use Inspired Research and Bench Scale Tech Development. Piloting, Deployment, and Infrastructure grants are excluded because they fall outside Homeworld Collective's funding focus.

**Thesis tested:** Early-stage federal climate biotech grants that carry translational characteristics (industry framing, collaborative research approach, industry-facing orientation) produce more downstream patents than early-stage grants that lack them — and a substantial fraction of federal early-stage funding is going to grants that lack those characteristics.

See `METHODOLOGY.md` for the detailed study design, `PRE_REGISTRATION.md` for the formal hypothesis and what counts as support vs refutation.

## Inputs

All produced upstream by the main classification pipeline (`scripts/grant_classifier/`):

| File | Source | Used for |
|---|---|---|
| `output/stage2_characterized_all_years_with_industry_framing.csv` | step1–step5 pipeline | Grant classification (5-dim taxonomy + industry framing flag) |
| `output/merged_all_years.csv` | step1_merge_master_multiyear.py | Grant metadata (PI, abstract, agency, year, amount) |

Plus external data sources (fetched by scripts in this folder):

| Source | Access | Used for |
|---|---|---|
| OpenAlex API | Free, no key | Grant → papers via funding acknowledgments |
| Lens Scholarly API | Free academic (pending approval) | Papers → patents linkage + patent metadata |
| Lens Patent API | Free academic (pending approval) | Patent assignee types, claims, filing dates |

## Pipeline (planned)

Each script is independent and re-runnable. Caches intermediate CSVs in `output/` so external APIs aren't re-queried.

| # | Script | Input | Output |
|---|---|---|---|
| 1 | `step1_filter_early_stage.py` | stage2 CSV | `output/early_stage_grants.csv` — filtered to Use Inspired + Bench Scale |
| 2 | `step2_link_openalex.py` | early_stage_grants.csv | `output/grants_with_papers.csv` — adds list of OpenAlex paper IDs per grant |
| 3 | `step3_link_lens_patents.py` | grants_with_papers.csv | `output/grants_with_patents.csv` — adds patent citation list per paper, with assignee type + filing date |
| 4 | `step4_attribute_patents.py` | grants_with_patents.csv | `output/grants_attributed.csv` — topic + timing weighted patent credit per grant |
| 5 | `step5_translation_regression.py` | grants_attributed.csv | `output/regression_results.csv`, `output/coefficient_plot.png` |
| 6 | `step6_homeworld_comparison.py` | federal + Homeworld classifications | `output/homeworld_vs_federal.csv` — distributional comparison (optional, needs Homeworld data) |

## What this analysis answers

1. Within early-stage climate biotech grants, do translational characteristics (industry framing, collaborative approach, industry-facing orientation) predict more downstream patents, controlling for amount, year, agency, and application area?
2. What fraction of federal early-stage grants carry each translational characteristic?
3. If the first answer is positive, what's the magnitude of the gap — i.e., how much higher is the patent rate for grants that carry the characteristics vs those that don't?
4. (If Homeworld's grantmaking data is available) How does Homeworld's early-stage portfolio compare to federal early-stage on these characteristics?

## What this analysis does not answer

- Causal claims (no "X caused Y" — only association).
- Per-grant attribution is fractional, not exact. A grant's patent credit is its topic-weighted, timing-weighted share of the patents its papers were cited by.
- Translation beyond patents — open-source tools, policy influence, teaching materials — is not captured.
- Recent grants (2023+) will have artificially low patent counts because of time lag. Sensitivity analysis will test robustness to this.
- Claims about late-stage federal funding. Scope is early-stage only.

## Running the pipeline

Once upstream classification is done and Lens API is approved:

```bash
cd scripts/patent_translation

export LENS_API_TOKEN=<your Lens token>    # or put in .env
export OPENALEX_EMAIL=<your email>         # polite user identifier for OpenAlex

python3 step1_filter_early_stage.py
python3 step2_link_openalex.py
python3 step3_link_lens_patents.py
python3 step4_attribute_patents.py
python3 step5_translation_regression.py
python3 step6_homeworld_comparison.py     # optional, needs Homeworld classification input
```

Each step ~10–60 minutes depending on API rate limits and sample size.

## Status

- [ ] Upstream pipeline complete (waiting on step5 of main classifier)
- [ ] Lens API approved (pending)
- [ ] Pre-registration posted to OSF (pending)
- [ ] Homeworld grantmaking data classified (pending; optional)
- [ ] Step 1–6 scripts drafted (pending — will write against real column names once upstream is done)
