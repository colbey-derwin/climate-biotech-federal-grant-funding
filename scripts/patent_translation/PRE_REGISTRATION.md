# Pre-Registration — Patent Translation Analysis

**Status:** Draft. Post to OSF (osf.io/registries) before running step5 (`translation_regression.py`) on real linked data. Once posted, amend only with explicit, timestamped deviations.

**Principal investigator:** [name]
**Affiliation:** [affiliation]
**Date drafted:** [fill in at time of posting]
**Target analysis date:** [fill in when running]

---

## 1. Research question

Among federal early-stage climate biotech grants (Use Inspired Research and Bench Scale Tech Development, FY2019–FY2025), do grants carrying translational characteristics — industry framing, collaborative research approach, industry-facing orientation — produce more downstream patents than grants that lack them, after controlling for funding amount, time elapsed, funding agency, and application area?

## 2. Population

Federal climate biotech research grants meeting all of the following:

- Classified as climate biotech by the two-stage LLM pipeline (Stage 1 KEEP).
- Classified by Stage 2 as `research_stage ∈ {"Use Inspired Research", "Bench Scale Tech Development"}`.
- Awarded in fiscal years 2019 through 2025.
- Sourced from NSF Awards API or USASpending.gov.
- Sufficient abstract length for classification (≥ 150 characters).
- Not formula grants (`award_type != "FORMULA GRANT (A)"`).

Expected n after filtering: 3,000–5,000 grants.

## 3. Primary hypotheses

| H# | Hypothesis | Predictor | Expected direction |
|---|---|---|---|
| H1 | Industry framing predicts more patents | `industry_framing == TRUE` | positive |
| H2 | Collaborative approach predicts more patents | `research_approach == "collaborative"` | positive |
| H3 | Industry-facing orientation predicts more patents | `orientation == "industry_facing"` | positive |

These are one-sided predictions based on Homeworld's working thesis.

## 4. Secondary hypotheses (exploratory, no directional prediction)

- Application area has a significant effect on patent output (F-test across 14 levels).
- Bench Scale Tech Development produces more patents than Use Inspired Research within the early-stage subset.
- Industry framing effect size differs across application areas (interaction term).

## 5. Predictor definitions

Exact as classified by the upstream LLM pipeline. See repo `README.md` and `classification_guide.md` for the full taxonomy. In brief:

- **Industry framing (TRUE/FALSE):** Does the abstract contain techno-economic analysis, life-cycle assessment, economic feasibility, commercial viability, scalability, or market-analysis language?
- **Research approach (collaborative/single_focus):** Does the abstract explicitly describe integrating multiple disciplines as a core feature of the research?
- **Orientation (industry_facing/public_facing):** Is the grant oriented toward industry translation or public-good research?

## 6. Outcome variable

`log(attributed_patents_industry_only + 1)` for each grant.

`attributed_patents_industry_only` is defined in `METHODOLOGY.md` §5 and is computed as the sum, over all (paper, patent) pairs where the paper acknowledged the grant and the patent cited the paper, of (topic-weight × timing-weight × acknowledgment-share), restricted to patents with a non-academic commercial assignee.

## 7. Statistical model

OLS regression with HC3 robust standard errors:

```
log(attributed_patents_industry_only + 1)
    ~ industry_framing
    + research_approach
    + orientation
    + research_stage
    + application_area
    + log(amount)
    + years_since_end
    + funder_fixed_effects
```

Primary inference: coefficient sign + 95% CI + Benjamini-Hochberg FDR-corrected p-value for H1, H2, H3.

## 8. Decision rules — what counts as support vs refutation

| Outcome | Interpretation |
|---|---|
| H1, H2, H3 all positive and significant after FDR correction | Thesis strongly supported |
| 2 of 3 primary hypotheses positive and significant | Thesis partially supported; specify which characteristics matter |
| 1 of 3 positive and significant | Thesis weakly supported; effect is more specific than claimed |
| None significant | Thesis not supported. Report honestly: early-stage federal grants' patent output is not meaningfully associated with these characteristics |
| Any primary coefficient significantly **negative** | Thesis contradicted for that characteristic. Report honestly and revise |

**Commitment:** Results are reported regardless of which decision rule the data triggers. No publication is contingent on the thesis being supported.

## 9. Sample size justification

No a priori power analysis — sample size is determined by the upstream classification pipeline and is not a design choice. With expected n ≈ 3,000–5,000 and ~6 predictors plus controls, standard rules-of-thumb (≥ 20 observations per predictor) are satisfied by a wide margin. Power to detect effect sizes as small as Cohen's f² = 0.01 will exceed 0.90 at α = 0.05.

## 10. Sensitivity analyses (pre-specified)

1. Restrict to grants ending before FY 2022 (removes time-lag censoring).
2. Use `attributed_patents` (all assignees) instead of industry-only as outcome.
3. Use `unweighted_paper_patent_count` (no topic/timing/share weighting).
4. Negative binomial regression on raw count outcome.

If all four agree qualitatively with the primary model for a given hypothesis, the finding is considered robust. Disagreement is reported.

## 11. Deviations from pre-registration

Any deviation (adding a predictor, changing an outcome definition, restricting the sample beyond what's specified here) must be logged in `DEVIATIONS.md` with timestamp and justification. Exploratory analyses not pre-specified are reported as exploratory and not tested against the primary hypothesis.

## 12. Data and code availability

Code: `scripts/patent_translation/` in the project repo.
Data: Federal grant data is public (USASpending, NSF). Classification output CSV is produced by the repo pipeline. OpenAlex and Lens queries are reproducible given the grant IDs. Intermediate and final output CSVs will be archived to OSF alongside this pre-registration.

---

**Signatures / Acknowledgment of pre-registration:**

- [ ] Principal investigator signed off on analysis plan before running step5.
- [ ] Pre-registration posted to OSF. OSF URL: _______________________
- [ ] Timestamp of OSF posting: _______________________
