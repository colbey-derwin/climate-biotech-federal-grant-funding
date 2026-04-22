# Climate Biotech Federal Grant Analysis Pipeline

**Output (dataset)**: `scripts/grant_classifier/output/stage2_characterized_all_years_with_industry_framing.csv`
**Output (exploratory plots)**: `visualization/*.html`
**GitHub**: https://github.com/colbey-derwin/climate-biotech-federal-grant-funding

**Goal**: Identify and characterize federal funding for climate biotechnology research across all agencies (NSF, DOE, DOD, USDA, EPA, etc.) from 2019-2025. Show how much funding goes to different research stages, application areas, and whether research considers commercial viability.

**Time period**: FY2019-FY2025 federal grants from NSF Award API + USASpending.gov

---

## The Classification System

Every climate biotech grant is classified across **5 dimensions**:

| Dimension | What it means | Categories |
|-----------|--------------|------------|
| **Grant Type** | What kind of grant is it? | `research` / `infrastructure` / `deployment` / `other` |
| **Orientation** | Who is it for? | `industry_facing` / `public_facing` |
| **Research Stage** | How far along? (research only) | `Use Inspired Research` / `Bench Scale Tech Development` / `Piloting` |
| **Application Area** | What's being made? | 14 categories (biofuels, bioplastics, carbon capture, etc.) |
| **Research Approach** | How is it structured? (public research only) | `collaborative` / `single_focus` |

Plus a **bonus flag**:
- **Industry Framing**: Does the grant study commercial viability? (TRUE for deployment, industry-facing research, and public research that includes TEA/LCA/cost analysis)

### The 14 Application Areas

1. **crop_productivity_traditional** — Traditional agriculture productivity improvements
2. **precision_fermentation** — Precision fermentation for proteins, fats, ingredients
3. **cellular_agriculture** — Cell-cultured meat, dairy, seafood
4. **specialty_bioproducts** — Novel ingredients, flavors, alternative proteins
5. **platform_biochemicals** — Drop-in or novel chemicals from biology
6. **biopolymers_materials** — Bioplastics, textiles, construction materials
7. **biogas_gaseous_energy** — Methane, hydrogen, other gases
8. **liquid_biofuels** — Ethanol, biodiesel, SAF, marine fuels
9. **biological_carbon_capture** — Photosynthesis-based carbon removal
10. **carbon_utilization_biotech** — CO2 as feedstock for bio-products
11. **pollution_degradation_remediation** — Breaking down pollutants, cleaning contamination
12. **bioextraction_biomining** — Metal recovery using biological processes
13. **ecosystem_monitoring** — Biosensors, eDNA, bioindicators for environmental monitoring
14. **enabling_technology** — Foundational tools, platforms, core capabilities

### The Key Question: What is Climate Biotech?

**Climate biotech** = Using biological mechanisms to address the climate crisis and restore planetary health

This is an **intersection filter**: We need BOTH climate/environmental relevance AND biological approach.

**KEEP if**: (CLIMATE × BIO) × NOT excluded × sufficient abstract

Examples:
- ✅ "Engineering algae for biofuel production" → Climate (biofuel) × Bio (algae engineering)
- ✅ "Microbial degradation of PFAS in groundwater" → Climate (pollution) × Bio (microbial)
- ✅ "Biochar for soil carbon sequestration" → Climate (carbon) × Bio (biological soil processes)
- ❌ "Solar panel efficiency improvements" → Climate (energy) but NO biological approach
- ❌ "Cancer immunotherapy development" → Bio (biotech) but NO climate connection
- ❌ "Observational study of bird migration" → Both, but pure ecology without solutions focus

---

## The Actual Process (Play-by-Play)

### PHASE 1: Development & Validation (2019 Only)

**Purpose**: Develop the classification methodology on a single year where we can iterate quickly and cheaply.

**Why 2019?**: Pre-pandemic baseline year with complete data. Perfect for testing before scaling up.

**Strategy**: 
1. Download 2019 data only (~50,000 total grants)
2. Filter to climate biotech (~2,000-5,000 grants)
3. Manually classify 50 grants as validation set
4. Run LLM classification on validation set only
5. Test accuracy, iterate on prompts, repeat
6. Once accuracy is good (>90%), move to Phase 2

**Runtime**: ~15-25 minutes per iteration  
**Cost**: ~$0.30 per iteration

This fast iteration cycle lets you test new prompts, fix errors, and refine the methodology before spending $60 and 10 hours on the full dataset.

#### Step 0: Download 2019 Data

**NSF Awards** (JSON files):

```bash
# NSF API - Fiscal Year 2019 (Oct 1, 2018 - Sep 30, 2019)
# Download all awards, extract JSONs, place in: /data/2019/NSF2019/*.json

# Example API call (you'll need to paginate):
curl "https://api.nsf.gov/awards/v1/awards.json?printFields=id,title,abstractText,startDate,expDate,piFirstName,piLastName&dateStart=10/01/2018&dateEnd=09/30/2019&offset=0" > batch1.json
```

**USASpending.gov** (CSV):

1. Go to https://www.usaspending.gov/download_center/award_data_archive
2. Select **Fiscal Year 2019**
3. Select **Award Type: Grants** (Prime Awards, not Sub-Awards)
4. Download CSV (~2-5GB)
5. Rename to `USASpending2019.csv`
6. Place in: `/data/2019/USASpending2019.csv`

Expected structure:
```
data/
└── 2019/
    ├── NSF2019/              # Folder with individual .json files
    │   ├── 1234567.json
    │   ├── 1234568.json
    │   └── ...
    ├── USASpending2019.csv
    └── YOUR_MANUAL_CLASSIFICATIONS_2019.xlsx  # You'll create this
```

#### Step 1: Merge 2019 Data

**Script**: `step1_merge_master_2019.py`

```bash
cd scripts/grant_classifier
python step1_merge_master_2019.py
```

**What it does**:
- Loads NSF JSON metadata (title, abstract, PI, institution, directorate, division)
- Loads USASpending CSV (funding amounts for ALL agencies)
- For NSF grants: Merges JSON metadata + USASpending amounts by award_id
- For non-NSF grants: Uses USASpending data only
- Creates `unique_key` = `{source}::{award_id}` (e.g., "NSF::1902014", "DOE::DE-EE0009876")

**Output**: `/scripts/grant_classifier/output/merged_2019.csv` (~50,000 rows)

**Runtime**: ~5-10 minutes

#### Step 2: Climate Biotech Filter (2019)

**Script**: `step2_climate_biotech_filter_2019.py`

```bash
python step2_climate_biotech_filter_2019.py
```

**Logic**: Check in order:

1. **Has CLIMATE/ENVIRONMENTAL evidence?** (must have ≥1)
   - Carbon: "carbon capture", "carbon sequestration", "biofuel", "decarbonization"
   - Pollution: "pollution remediation", "wastewater treatment", "PFAS degradation"
   - Agriculture: "sustainable agriculture", "soil health", "nitrogen use efficiency"
   - Ecosystems: "ecosystem restoration", "biodiversity conservation"
   - Bio-based: "bioplastics", "biochemicals", "biomaterials"

2. **Has BIOLOGICAL approach?** (must have ≥1)
   - Core bio: "biotechnology", "synthetic biology", "genetic engineering"
   - Organisms: "microbe", "microbial", "algae", "enzyme", "bacteria", "fungi"
   - Processes: "fermentation", "biocatalysis", "metabolic engineering"

3. **Is it EXCLUDED?** (auto-reject if yes)
   - Pure biomedical: Heavy medical/clinical terminology without climate context
   - Pure computer science: Software/AI with no biological component
   - Pure ecology: Observational ecology without solutions/industrial focus
   - Formula grants: Type (A) capacity-building, not competitive research

4. **Has sufficient abstract?** (must have ≥150 characters)
   - Needed for LLM to make informed decisions
   - Grants with shorter abstracts saved separately for manual review

**Output**:
- `climate_biotech_filtered.csv` (~2,000-5,000 grants) ← **This is what we classify**
- `climate_biotech_excluded.csv` (rejected grants)
- `climate_biotech_insufficient_abstract.csv` (short abstracts, potential manual review)

**Runtime**: ~2-5 minutes

#### Step 3: Create Validation Set (Manual)

This is the **critical step** that makes the whole pipeline work.

**What to do**:
1. Open `climate_biotech_filtered.csv`
2. Sample ~50 diverse grants (mix of agencies, application areas, grant types)
3. For each grant, manually classify all 5 dimensions:
   - `YOUR_s1_decision`: KEEP or REMOVE
   - `YOUR_s2_grant_type`: research / infrastructure / deployment / other
   - `YOUR_s2_orientation`: industry_facing / public_facing
   - `YOUR_s2_research_stage`: Use Inspired Research / Bench Scale Tech Development / Piloting
   - `YOUR_s2_application_area`: (one of 14 categories)
   - `YOUR_s2_research_approach`: collaborative / single_focus
4. Save as: `/data/2019/YOUR_MANUAL_CLASSIFICATIONS_2019.xlsx`

**Required columns**:
- `grant_id` (the unique_key from merged data)
- `title`
- `abstract`
- `YOUR_s1_decision`
- `YOUR_s2_grant_type`
- `YOUR_s2_orientation`
- `YOUR_s2_research_stage`
- `YOUR_s2_application_area`
- `YOUR_s2_research_approach`

**How to classify**: See `classification_guide.md` for detailed decision rules and examples.

**Time required**: ~2-3 hours for 50 grants (depends on your domain knowledge)

#### Step 4: LLM Classification (Validation Set)

**Script**: `step3_climate_biotech_two_stage_classifier_2019.py`

**CRITICAL**: Default setting is `TEST_MODE = True`, which uses your 50 validation grants.

```bash
# Make sure TEST_MODE = True in the script (it is by default)
python step3_climate_biotech_two_stage_classifier_2019.py
```

**What it does**:

**Stage 1** (Haiku 4.5 - Fast & Cheap):
- Binary decision: Is this grant actually climate biotech?
- Uses decision tree:
  1. CHECK: Infrastructure/admin (cores, training)? → Everything_else (REMOVE)
  2. CHECK: Clinical intervention (trial, treatment)? → Everything_else (REMOVE)
  3. CHECK: Has biological component? → If no, REMOVE
  4. CHECK: Is it biomedical? → If yes and no climate tie, REMOVE
  5. CHECK: Is it pure ecology? → If yes and no solutions focus, REMOVE
  6. CHECK: Has climate/environmental connection? → If no, REMOVE
  7. All checks pass → KEEP
- Output: KEEP or REMOVE + confidence (high/low) + reasoning

**Stage 2** (Sonnet 4 - Nuanced & Accurate):
- Only runs on grants marked KEEP in Stage 1
- Classifies all 5 dimensions
- Output: Full characterization + confidence

**Model specifics**:
- Stage 1: `claude-haiku-4-5-20251001` (~$0.001 per grant)
- Stage 2: `claude-sonnet-4-20250514` (~$0.005 per grant)

**Output**:
- `stage1_biotech_fit.csv` (50 grants with Stage 1 decisions)
- `stage2_characterized.csv` (KEEP grants with Stage 2 classifications)
- `two_stage_classification_log.json` (detailed logging)

**Runtime**: ~5 minutes (50 grants)  
**Cost**: ~$0.30

#### Step 5: Test Accuracy

**Script**: `test_llm_classifier_accuracy_2019.py`

```bash
python test_llm_classifier_accuracy_2019.py
```

**What it does**:
- Compares LLM classifications to your manual classifications
- Calculates accuracy for each dimension
- Identifies specific errors for review
- Creates Excel file with:
  - Summary sheet: Overall accuracy scores
  - Error sheets: One per category with misclassified examples
  - Full comparison: Side-by-side LLM vs. manual

**Output**: `accuracy_test_results.xlsx`

**What to look for**:
- Stage 1 Decision: Should be >95% accurate
- Grant Type: Should be >90% accurate
- Application Area: Most errors happen here - look for patterns
- Orientation: Should be >85% accurate

**Runtime**: <1 minute

#### Step 6: Iterate (The Most Important Step)

**This is where the magic happens**. You'll repeat Steps 4-5 multiple times, refining prompts each time.

**Common error patterns** (from our experience):

| Error Pattern | What's happening | Fix |
|--------------|------------------|-----|
| Mechanism studies → Everything_else | Grants studying "role of [protein]" or "[pathway] in [process]" not recognized | Add examples to prompt of mechanism studies |
| Intervention studies → Environmental | "Smoking cessation" or "dietary intervention" flagged as environmental | Strengthen clinical intervention check |
| Industry research → Public | Grants with industry partners still tagged public | Clarify orientation decision rules |
| Wrong application area | Biofuel grant tagged as biochemicals | Add more examples per category |

**How to iterate**:
1. Review errors in `accuracy_test_results.xlsx`
2. Find patterns (e.g., "All kinase studies are wrong")
3. Update prompts in `step3_climate_biotech_two_stage_classifier_2019.py`
4. Re-run classification (Step 4) - only takes 5 minutes!
5. Re-test accuracy (Step 5)
6. Repeat until accuracy >90% on all dimensions

**Typical iteration count**: 3-5 rounds to get good accuracy

**Time investment**: ~1-2 days of prompt engineering

**Why this matters**: These prompts will classify 10,000+ grants in Phase 2. Getting them right here saves massive cleanup later.

#### Step 7 (Optional): Refine with Better Model

**Script**: `step4_refine_stage2_classifications_multiyear.py --test`

Once you have good accuracy (~90%), you can try the **refinement step**:

```bash
# Test mode first
python step4_refine_stage2_classifications_multiyear.py --test
```

**What it does**:
- Re-classifies Grant Type, Application Area, and Research Approach
- Uses **Sonnet 4.6** (latest model, more accurate but more expensive)
- Uses improved prompts based on validation findings
- Only updates these 3 categories (keeps Orientation and Research Stage)

**When to use**:
- You've plateaued at ~90% accuracy and want to push to >95%
- You have specific categories that keep erroring
- You're willing to spend more per grant for higher accuracy

**Model upgrade**:
- Original: Sonnet 4 (May 2025) - `claude-sonnet-4-20250514`
- Refined: Sonnet 4.6 (latest) - `claude-sonnet-4-6`
- Cost increase: ~2x per grant, but only runs on Stage 2

**Runtime**: ~5 minutes on validation set  
**Cost**: ~$0.50 (for 50 grants)

**Output**: `refinement_test_results.csv`

Compare to original Stage 2 results to see if accuracy improved. If yes, use refinement in Phase 2.

---

### PHASE 2: Production Run (2019-2025)

**Purpose**: Apply the validated methodology to the full dataset.

**When to start**: When your 2019 validation accuracy is >90% on all dimensions.

**What changes**: 
- Process all years (2019-2025) instead of just 2019
- Set `TEST_MODE = False` to process all grants, not just validation set
- Use `*_multiyear.py` scripts instead of `*_2019.py` scripts
- Files have `_all_years` suffix instead of `_2019`

**Runtime**: ~10-15 hours total  
**Cost**: ~$60 for LLM classification

#### Step 0: Download All Years (2019-2025)

Repeat the 2019 download process for each year:

```
data/
├── 2019/
│   ├── NSF2019/*.json
│   └── USASpending2019.csv
├── 2020/
│   ├── NSF2020/*.json
│   └── USASpending2020.csv
├── 2021/
│   ├── NSF2021/*.json
│   └── USASpending2021.csv
... (through 2025)
```

**Note**: Each year is ~2-5GB for USASpending + ~500MB-1GB for NSF JSONs

#### Step 1: Merge All Years

**Script**: `step1_merge_master_multiyear.py`

```bash
cd scripts/grant_classifier
python step1_merge_master_multiyear.py
```

**What it does**:
- Same logic as 2019 merge, but loops over all years
- Combines all years into single file with `year` column
- Creates unique_key for cross-year tracking

**Output**: `merged_all_years.csv` (~350,000-500,000 rows across all years)

**Runtime**: ~15-30 minutes

#### Step 2: Climate Biotech Filter (All Years)

**Script**: `step2_climate_biotech_filter_multiyear.py`

```bash
python step2_climate_biotech_filter_multiyear.py
```

**Logic**: Identical to 2019 filter, just processes all years

**Output**:
- `climate_biotech_filtered_all_years.csv` (~15,000-30,000 grants) ← **Full dataset to classify**
- `climate_biotech_excluded_all_years.csv`
- `climate_biotech_insufficient_abstract_all_years.csv`

**Runtime**: ~5-10 minutes

#### Step 3: LLM Classification (Full Dataset)

**Script**: `step3_climate_biotech_two_stage_classifier_multiyear.py`

**CRITICAL**: Change `TEST_MODE = False` in the script before running!

```python
# In the script, change this line:
TEST_MODE = False  # Change from True to False for production
```

Then run:
```bash
python step3_climate_biotech_two_stage_classifier_multiyear.py
```

**What it does**:
- Uses the same prompts you validated in Phase 1
- Processes ALL climate biotech grants from all years
- Saves checkpoints every 10 batches (can resume if interrupted)

**Output**:
- `stage1_biotech_fit_all_years.csv` (all grants with Stage 1 decisions)
- `stage2_characterized_all_years.csv` (KEEP grants with Stage 2 classifications)
- `stage1_review_all_years.csv` (low-confidence KEEP decisions for manual review)
- `stage2_review_all_years.csv` (low-confidence Stage 2 classifications for manual review)
- `two_stage_classification_log_all_years.json`

**Runtime**: ~6-10 hours (depends on grant count)  
**Cost**: ~$60 (for ~10,000 grants)

**Features**:
- Auto-resume from checkpoints if interrupted
- Progress bars with ETA
- Detailed logging to JSON
- Separates low-confidence grants for review

**Pro tip**: Run overnight or on a weekend. The script will save checkpoints, so if it crashes you can resume where it left off.

#### Step 4 (Optional): Refine Classifications

**Script**: `step4_refine_stage2_classifications_multiyear.py`

**Only run this if**:
- Phase 1 refinement improved accuracy
- You want >95% accuracy on Grant Type, Application Area, Research Approach
- You're willing to spend extra for the better model

```bash
# Production mode (updates the main file)
python step4_refine_stage2_classifications_multiyear.py
```

**What it does**:
- Re-classifies Grant Type, Application Area, Research Approach using Sonnet 4.6
- Creates backup of original file first
- Overwrites `stage2_characterized_all_years.csv` with refined classifications

**Runtime**: ~30-60 minutes  
**Additional cost**: ~$30-40 (on top of Step 3 cost)

**Output**: Updated `stage2_characterized_all_years.csv` with improved classifications

#### Step 5: Add Industry Framing Flags

**Script**: `step5_post_classification_industry_relevance_flags_multiyear.py`

```bash
python step5_post_classification_industry_relevance_flags_multiyear.py
```

**What it does**:
- Adds `industry_framing` column (TRUE/FALSE/NULL)
- Logic:
  - Deployment grants: ALWAYS TRUE (inherently commercial)
  - Industry-facing research: ALWAYS TRUE (that's what industry-facing means)
  - Public-facing research: Check abstract for keywords → TRUE/FALSE
  - Infrastructure: Check abstract for keywords → TRUE/FALSE
  - Other: NULL (not applicable)

**Keywords detected** (18 total):
- Techno-economic analysis (TEA, technoeconomic)
- Life cycle assessment (LCA, lifecycle assessment)
- Economic feasibility/viability
- Commercial feasibility/viability/pathway
- Cost analysis, cost-benefit analysis
- Scalability analysis, scale-up economics
- Market analysis, market potential

**Output**: `stage2_characterized_all_years_with_industry_framing.csv` ← **FINAL DATASET**

**Runtime**: ~2 minutes

**Why this matters**: Even within public-facing research, some grants explicitly study commercial viability. This flag identifies them.

#### Step 6 (Optional): Validate Production Accuracy

**Script**: `test_llm_classifier_accuracy_multiyear.py`

```bash
python test_llm_classifier_accuracy_multiyear.py
```

**What it does**:
- Tests accuracy on the same 50 validation grants from Phase 1
- But now using results from the full production run
- Verifies that prompts still work well on real production data

**Input**: Needs `/data/YOUR_MANUAL_CLASSIFICATIONS_multiyear.xlsx` (copy from 2019 file, or expand to include more validation grants from other years)

**Output**: `accuracy_test_results_stage2_all_years.xlsx`

**Why run this**: Sanity check that production classifications match your validation expectations

**Runtime**: <1 minute

#### Step 7 (Optional): Analyze Insufficient Abstracts

**Script**: `analyze_insufficient_abstracts_multiyear.py`

```bash
python analyze_insufficient_abstracts_multiyear.py
```

**What it shows** (console output only):
- How many grants excluded due to short abstracts (<150 chars)
- Breakdown by agency and year
- % of each agency's climate biotech portfolio excluded
- Examples from DOE, DOD (agencies with shortest abstracts)

**Runtime**: <1 minute

**Why run this**: Understand data gaps and potential biases. Some agencies (especially DOD) have very short abstracts, which limits LLM classification quality.

---

## Visualization

Once Phase 2 is complete, generate visualizations.

**Input file**: `stage2_characterized_all_years_with_industry_framing.csv` (final dataset)

**Location**: `/visualization/` folder (separate from `/scripts/`)

### The 6 Visualizations

All are standalone HTML files that open in any browser. No dependencies needed.

#### 1. Main Report Dashboard
**Script**: `visualize_climate_biotech_funding_report.py`

```bash
cd visualization
python visualize_climate_biotech_funding_report.py
```

**Output**: `climate_biotech_report.html`

**Shows**:
- % of federal funding going to climate biotech (overall & by year)
- Timeline trends by grant type (research/infrastructure/deployment)
- Top funding agencies
- Links to other visualizations

#### 2. Sankey Diagrams (Funding Flow)
**Scripts**: 
- `visualize_climate_biotech_funding_sankey_funding.py` (by dollars)
- `visualize_climate_biotech_funding_sankey_count.py` (by grant count)

```bash
python visualize_climate_biotech_funding_sankey_funding.py
python visualize_climate_biotech_funding_sankey_count.py
```

**Output**: 
- `climate_biotech_sankey_funding.html`
- `climate_biotech_sankey_count.html`

**Shows**: Flow from Grant Type → Orientation → Research Stage → Application Area

#### 3. Research Stage Flow
**Script**: `visualize_climate_biotech_funding_research_stage.py`

```bash
python visualize_climate_biotech_funding_research_stage.py
```

**Output**: `research_stage_funding_flow.html`

**Shows**: Flowing streams showing how funding flows across research stages, broken down by application area

#### 4. De-risked Categories Scatter
**Script**: `visualize_climate_biotech_funding_derisking.py`

```bash
python visualize_climate_biotech_funding_derisking.py
```

**Output**: `derisked_categories_scatter.html`

**Shows**: Which application areas have lots of pilot/deployment funding (= "de-risked"). Bubble size = total funding.

#### 5. Miscellaneous Plots
**Script**: `visualize_climate_biotech_funding_misc_plots.py`

```bash
python visualize_climate_biotech_funding_misc_plots.py
```

**Output**: `misc_plots.html`

**Shows**: Top institutions, geographic distribution, industry framing analysis, time series trends

#### 6. View All

```bash
# Open main report (has links to others)
open climate_biotech_report.html
```

---

## Project Structure

```
climate_biotech_federal_grant_funding/
├── data/
│   ├── 2019/
│   │   ├── NSF2019/*.json
│   │   ├── USASpending2019.csv
│   │   └── YOUR_MANUAL_CLASSIFICATIONS_2019.xlsx
│   ├── 2020/
│   ├── 2021/
│   ├── 2022/
│   ├── 2023/
│   ├── 2024/
│   ├── 2025/
│   └── YOUR_MANUAL_CLASSIFICATIONS_multiyear.xlsx
│
├── scripts/
│   └── grant_classifier/
│       ├── output/                         # All pipeline outputs
│       │   ├── merged_2019.csv
│       │   ├── merged_all_years.csv
│       │   ├── climate_biotech_filtered.csv
│       │   ├── climate_biotech_filtered_all_years.csv
│       │   ├── stage1_biotech_fit.csv
│       │   ├── stage1_biotech_fit_all_years.csv
│       │   ├── stage2_characterized.csv
│       │   ├── stage2_characterized_all_years.csv
│       │   ├── stage2_characterized_all_years_with_industry_framing.csv  # FINAL
│       │   ├── accuracy_test_results.xlsx
│       │   └── accuracy_test_results_stage2_all_years.xlsx
│       │
│       ├── step1_merge_master_2019.py
│       ├── step1_merge_master_multiyear.py
│       ├── step2_climate_biotech_filter_2019.py
│       ├── step2_climate_biotech_filter_multiyear.py
│       ├── step3_climate_biotech_two_stage_classifier_2019.py
│       ├── step3_climate_biotech_two_stage_classifier_multiyear.py
│       ├── step4_refine_stage2_classifications_multiyear.py
│       ├── step5_post_classification_industry_relevance_flags_multiyear.py
│       ├── test_llm_classifier_accuracy_2019.py
│       ├── test_llm_classifier_accuracy_multiyear.py
│       ├── analyze_insufficient_abstracts_2019.py
│       └── analyze_insufficient_abstracts_multiyear.py
│
└── visualization/
    ├── climate_biotech_report.html
    ├── climate_biotech_sankey_funding.html
    ├── climate_biotech_sankey_count.html
    ├── research_stage_funding_flow.html
    ├── derisked_categories_scatter.html
    ├── misc_plots.html
    ├── visualize_climate_biotech_funding_report.py
    ├── visualize_climate_biotech_funding_sankey_funding.py
    ├── visualize_climate_biotech_funding_sankey_count.py
    ├── visualize_climate_biotech_funding_research_stage.py
    ├── visualize_climate_biotech_funding_derisking.py
    └── visualize_climate_biotech_funding_misc_plots.py
```

---

## Complete Workflow Summary

### PHASE 1: Development (2019 only)

**Goal**: Get accuracy >90% on 50 validation grants

```bash
# Download 2019 data (manual)
# Create validation set (manual - 50 grants)

cd scripts/grant_classifier

# Run pipeline on 2019
python step1_merge_master_2019.py
python step2_climate_biotech_filter_2019.py
python step3_climate_biotech_two_stage_classifier_2019.py  # TEST_MODE=True by default
python test_llm_classifier_accuracy_2019.py

# Review errors, update prompts, repeat Steps 3-4 until accuracy >90%

# Optional: Test refinement
python step4_refine_stage2_classifications_multiyear.py --test
```

**Time**: 1-2 days (mostly prompt engineering)  
**Cost**: $5-10 (multiple iterations)

### PHASE 2: Production (2019-2025)

**Goal**: Classify the full dataset

```bash
# Download all years 2019-2025 (manual)

cd scripts/grant_classifier

# Run full pipeline
python step1_merge_master_multiyear.py
python step2_climate_biotech_filter_multiyear.py

# CRITICAL: Change TEST_MODE=False in step3 script!
python step3_climate_biotech_two_stage_classifier_multiyear.py

# Optional: Refine
python step4_refine_stage2_classifications_multiyear.py

# Add industry flags
python step5_post_classification_industry_relevance_flags_multiyear.py

# Optional: Validate & analyze
python test_llm_classifier_accuracy_multiyear.py
python analyze_insufficient_abstracts_multiyear.py

# Generate visualizations
cd ../../visualization
python visualize_climate_biotech_funding_report.py
python visualize_climate_biotech_funding_sankey_funding.py
python visualize_climate_biotech_funding_sankey_count.py
python visualize_climate_biotech_funding_research_stage.py
python visualize_climate_biotech_funding_derisking.py
python visualize_climate_biotech_funding_misc_plots.py

# View results
open climate_biotech_report.html
```

**Time**: ~10-15 hours (mostly LLM classification running overnight)  
**Cost**: ~$60-100 (depending on refinement)

---

## Requirements

### Software
```bash
# Python 3.8+
python --version

# Required packages
pip install pandas tqdm anthropic openpyxl
```

### API Keys
```bash
# Anthropic API key (for LLM classification)
export ANTHROPIC_API_KEY=sk-ant-...

# Or create .env file in project root:
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
```

Get your API key at: https://console.anthropic.com/settings/keys

### Data Sources
- **NSF**: https://www.nsf.gov/developer/
- **USASpending.gov**: https://www.usaspending.gov/download_center/award_data_archive

---

## What Worked and What Didn't

### Worked ✅

**Two-phase approach**: Develop on 2019 first, then scale to all years. Fast iteration on prompts before committing to expensive full run.

**Decision tree with strict ordering**: Filter infrastructure/clinical FIRST, then check environmental vs. mechanistic. Order matters.

**Two-stage classification**: Stage 1 (Haiku - fast binary) → Stage 2 (Sonnet - nuanced multi-axis). Stage 1 catches obvious rejects cheaply.

**PROJECT_TITLE + ABSTRACT**: Titles alone were ambiguous. Full abstracts gave enough context.

**Iterative QC**: Sample → find errors → update prompts → re-run. Repeated 3-5 times in Phase 1.

**Validation set**: 50 manually classified grants as ground truth. Enabled measuring accuracy objectively.

**Checkpoint system**: Save progress every 10 batches. Can resume if interrupted (crucial for 10-hour runs).

**Keyword + LLM hybrid**: Keyword filter (fast, cheap) narrows to ~5% of grants. LLM classifies deeply (slow, expensive) on that subset only.

### Didn't Work ❌

**Claude Haiku for nuanced classification**: Too aggressive, confidently wrong on edge cases. Would tag mechanism studies as environmental if they mentioned any exposure. Haiku works great for binary decisions (Stage 1), but not for nuanced multi-axis classification (Stage 2).

**Single-pass classification**: Tried to classify all 5 dimensions at once. Errors cascaded. Two-stage (binary first, then characterization) was more reliable.

**Titles alone**: "Targeting EGFR in lung cancer" could be mechanistic or clinical or deployment. Needed full abstract.

**Trusting the first run**: Every disease area / application area had systematic errors that required manual review and prompt updates.

**Processing all years at once in development**: Wasted time and money. Should develop on single year first.

**Low abstract length threshold**: Originally used 90 characters. Too permissive - many grants lacked context for LLM. Increased to 150 characters.

**No validation set**: Early versions had no ground truth. Couldn't measure accuracy objectively. Creating 50 manual classifications enabled real accuracy metrics.

---

## Key Findings

**Placeholder - Fill in after running full pipeline**

- Total climate biotech grants (2019-2025): [X,XXX grants]
- Total climate biotech funding (2019-2025): [$X.XB]
- % of total federal grant funding: [X.X%]
- Funding by grant type:
  - Research: [X%]
  - Infrastructure: [X%]
  - Deployment: [X%]
- Funding by research stage:
  - Use Inspired Research: [X%]
  - Bench Scale Tech Development: [X%]
  - Piloting: [X%]
- Top application areas by funding: [list]
- % with industry framing: [X%]

---

## Troubleshooting

### API Key Issues

**Problem**: `No Anthropic API key found`

**Solution**:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Or create .env file
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
```

### TEST_MODE Confusion

**Problem**: Multiyear script only processes 50 grants

**Solution**: Change `TEST_MODE = False` in the script before running

### Classifier Crashes Partway

**Problem**: LLM classification stops after 2 hours

**Solution**: Just re-run with `RESUME = True` (default). It will skip already-classified grants and continue where it left off. Look for checkpoint files: `stage1_checkpoint_all_years.csv`, `stage2_checkpoint_all_years.csv`

### Wrong Accuracy in Phase 1

**Problem**: Validation shows only 70% accuracy

**Solution**: This is expected in early iterations. Review error patterns in the Excel file, update prompts, re-run. Typical iterations: 3-5 rounds to reach >90%.

### Memory Issues

**Problem**: Computer slows down / freezes

**Solution**: 
- Close other applications
- Multi-year datasets are large (>1M rows total)
- Consider processing fewer years at once
- Scripts use `low_memory=False` for pandas (already set)

### High Costs

**Problem**: API costs higher than expected

**Solution**:
- Did you set `TEST_MODE = False` when you meant `TEST_MODE = True`?
- Check grant count in filtered file before classification
- Expected cost: ~$0.006 per grant for Stage 1+2
- 10,000 grants = ~$60, 20,000 grants = ~$120

### Visualization Not Working

**Problem**: HTML files show no data

**Solution**:
- Verify input CSV has all required columns
- Check JavaScript console for errors (F12 in browser)
- Re-run classification if data seems incomplete
- Make sure you're using the final file: `stage2_characterized_all_years_with_industry_framing.csv`

---

## Model Specifications

| Stage | Model | Version | Purpose | Cost/grant | Speed |
|-------|-------|---------|---------|-----------|-------|
| Stage 1 | Claude Haiku | 4.5 (Oct 2025) | Binary KEEP/REMOVE | ~$0.001 | ~1-2 sec |
| Stage 2 | Claude Sonnet | 4 (May 2025) | 5-dimension classification | ~$0.005 | ~2-3 sec |
| Refinement | Claude Sonnet | 4.6 (latest) | Improved accuracy on 3 dimensions | ~$0.008 | ~3-4 sec |

**Total cost per grant**:
- Without refinement: ~$0.006 (Stage 1 + Stage 2)
- With refinement: ~$0.014 (Stage 1 + Stage 2 + Refine)

**10,000 grants**:
- Without refinement: ~$60
- With refinement: ~$140

---

## File Naming Conventions

| Phase | File Suffix | Example |
|-------|------------|---------|
| Development (2019) | `_2019.csv` or no suffix | `merged_2019.csv`, `stage1_biotech_fit.csv` |
| Production (2019-2025) | `_all_years.csv` | `merged_all_years.csv`, `stage1_biotech_fit_all_years.csv` |

**Script naming**:
- Development: `*_2019.py`
- Production: `*_multiyear.py`

---

## Support & Documentation

- **NSF API**: https://www.nsf.gov/developer/
- **USASpending.gov**: https://www.usaspending.gov/data-dictionary
- **Anthropic API**: https://docs.anthropic.com/
- **Claude Models**: https://docs.anthropic.com/en/docs/about-claude/models

---

## Citations

If you use this pipeline:

**Data sources**:
- National Science Foundation Award Search API
- USASpending.gov, U.S. Department of Treasury

**Classification**:
- Anthropic Claude AI (Haiku 4.5, Sonnet 4, Sonnet 4.6)

**Pipeline**: [Your attribution]

---

## Future Enhancements

**Validation expansion**:
- Expand validation set beyond 50 grants
- Create year-specific validation sets (2020, 2021, etc.)
- Test classifier on other domains (health biotech, industrial biotech)

**Additional data sources**:
- SBIR/STTR grants (small business grants)
- ARPA-E projects (advanced energy R&D)
- State-level grant programs

**Improved classification**:
- Add technology readiness level (TRL) scoring
- Classify by specific technology approach (CRISPR, fermentation, etc.)
- Track collaborations between institutions

**Better visualizations**:
- Network graphs of institution collaborations
- Geographic heat maps
- Time series animations
- Export to Tableau/PowerBI formats

---

**Questions?**

See inline documentation in each script, or review the error logs in `/scripts/grant_classifier/output/*.json`.
