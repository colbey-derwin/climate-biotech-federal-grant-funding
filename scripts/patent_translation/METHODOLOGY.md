# Methodology — Patent Translation Analysis

## 1. Scope

The analysis is restricted to **early-stage federal climate biotech grants**, defined as grants classified by the upstream pipeline as:

- `research_stage == "Use Inspired Research"`, OR
- `research_stage == "Bench Scale Tech Development"`

Grants at Piloting, Deployment, Infrastructure, and Other stages are excluded. This is a principled scoping decision — Homeworld Collective's funding focus is early-stage research, and the thesis is about early-stage specifically. All findings are claims about early-stage grants only; no inference is made about late-stage federal funding.

## 2. Unit of analysis

Each row is one grant. The outcome variable is that grant's attributed patent count (defined in §5). Predictors are the grant's characteristics from the upstream classification plus controls.

## 3. Predictor variables (grant characteristics)

All drawn from `stage2_characterized_all_years_with_industry_framing.csv`.

| Variable | Type | Values |
|---|---|---|
| `orientation` | categorical | industry_facing, public_facing |
| `research_approach` | categorical | collaborative, single_focus |
| `industry_framing` | binary | TRUE, FALSE (NULL grants excluded from this term) |
| `application_area` | categorical (14 levels) | crop_productivity_traditional, precision_fermentation, …, enabling_technology |
| `research_stage` | categorical (2 levels within scope) | Use Inspired Research, Bench Scale Tech Development |

## 4. Control variables

| Variable | Purpose |
|---|---|
| `log(amount)` | Larger grants may produce more of everything |
| `year_awarded` | Recent grants have less time to produce patents |
| `years_since_end` | Continuous time-lag control |
| `funder` (fixed effects) | NSF, DOE, USDA, EPA, DOD — agencies fund different work |

## 5. Outcome variable — attributed patents

For each grant `G`:

```
attributed_patents(G) = Σ  topic_weight × timing_weight × acknowledgment_share
                       over all (paper π, patent P) where
                         π acknowledged G in OpenAlex  AND  P cites π via Lens
```

Where:

- `topic_weight ∈ [0,1]` — cosine similarity between grant abstract and patent abstract, using a sentence-level embedding model (OpenAI text-embedding-3-small or equivalent open-weight).
- `timing_weight ∈ {0,1}` — 1 if the grant's active period overlaps the patent's plausible conception window (filing date − 18 months to filing date − 6 months); 0 otherwise.
- `acknowledgment_share = 1 / k` — where `k` is the number of grants the paper acknowledged. Fractional attribution across multi-grant papers.

**Secondary outcomes reported alongside:**

- `attributed_patents_industry_only` — restricted to patents with company (non-university, non-government, non-nonprofit) assignees. This is the stronger commercial translation signal.
- `unweighted_paper_patent_count` — raw count without weighting, as a sensitivity check.
- `log(attributed_patents + 1)` — log-transformed version, used as regression outcome because patent counts are heavily right-skewed.

## 6. Regression specification

Primary model:

```
log(attributed_patents_industry_only + 1)
    ~ industry_framing
    + orientation
    + research_approach
    + research_stage
    + application_area
    + log(amount)
    + years_since_end
    + funder_fixed_effects
```

Fit via OLS with HC3 robust standard errors. Report coefficient, 95% CI, and p-value for each predictor.

**Secondary models (sensitivity analyses):**

1. Same regression with `attributed_patents` (all assignees) as outcome — tests whether the industry-patent effect differs from the all-patent effect.
2. Same regression with `unweighted_paper_patent_count` — tests whether the topic+timing weighting changes the findings directionally.
3. Negative binomial model with raw patent count as outcome — alternative specification for count data.
4. Regression restricted to grants that ended before 2022 — removes time-lag censoring for recent grants.

If all four sensitivity analyses produce qualitatively the same conclusion for a given characteristic, the finding is robust. Disagreement across models is reported honestly.

## 7. Reported findings

For each predictor, the paper/website reports:

1. The point estimate and 95% CI.
2. The implied effect size in plain language (e.g., "grants with industry framing are associated with X% more patents").
3. A marginal-means visualization showing predicted patent counts across predictor levels, holding other variables at their means.
4. The fraction of federal early-stage grants carrying the characteristic (descriptive statistic for the gap story).

## 8. Multiple comparisons

Six primary predictors × one primary outcome = 6 primary tests. Apply Benjamini-Hochberg FDR correction at α = 0.05. Pre-specified secondary predictors (interactions, sensitivity models) are reported uncorrected and clearly flagged as exploratory.

## 9. Linkage-quality reporting

For transparency, the analysis reports:

- % of early-stage grants for which OpenAlex returned ≥1 linked paper
- % by funder (NSF ≈ 85%, DOE ≈ 75%, USDA/EPA/DOD typically lower)
- Mean and median papers per grant
- Mean and median patents per paper
- Distribution of topic-similarity weights (to flag if weighting is doing a lot of work)

If linkage coverage is below 50% for any funder, regression results are reported twice — once on the full sample, once on the linked subsample — with both interpretations explained.

## 10. Known limitations

1. **Acknowledgment-line noise.** Papers sometimes omit grants, cite boilerplate lab-support grants, or misattribute. Topic + timing weighting mitigates but does not eliminate this.
2. **Patent citations are a floor, not a ceiling.** Research that translated via policy, open-source tools, or industry adoption without patent citation is not captured.
3. **Time lag.** Grants ended after 2021 may appear artificially low-patent because patents take 3–5 years after paper publication. Sensitivity analysis restricting to grants ending before 2022 addresses this.
4. **Non-US patents.** Lens covers global patents, which is good, but linkage quality to US federal grants is best when citing patents are US-filed. Fraction of non-US citing patents is reported.
5. **Correlation, not causation.** All claims are associational. Policy recommendations derived from findings must acknowledge this.

## 11. What the analysis does *not* do

- No per-PI disambiguation or PI-as-inventor analysis. The thesis is about grant characteristics, not PI behavior.
- No stage-comparison regression. Scope is early-stage only.
- No longitudinal modeling of grant → paper → patent as sequential events. All outcomes collapsed to counts.
- No attempt to attribute causation or simulate counterfactuals.

## 12. Homeworld comparison (optional, §6 in pipeline)

If Homeworld's own grantmaking data is available and classified with the same taxonomy, a descriptive comparison is produced:

- For each characteristic, the % of federal early-stage grants carrying it vs the % of Homeworld early-stage grants carrying it.
- No regression — purely descriptive. The narrative claim is that Homeworld's portfolio concentrates where federal funding is sparse on these characteristics.

## 13. Versioning

All code in `scripts/patent_translation/` is under git control. Each script's output CSV carries a header comment with the commit hash of the code that produced it. Reproducibility is a requirement, not a bonus.
