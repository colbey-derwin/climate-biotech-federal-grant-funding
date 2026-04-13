"""
refine_stage2_classifications.py

FOCUSED REFINEMENT SCRIPT for Stage 2 classifications.
Re-classifies Grant Type, Application Area, and Research Approach with improved prompts.

Target: >95% accuracy on all three categories.

TEST MODE: Uses validation grant IDs to test improvements
PRODUCTION MODE: Updates the main stage2_characterized_all_years.csv file

Usage:
  # Test mode (use validation grants)
  python refine_stage2_classifications.py --test
  
  # Production mode (update all grants)
  python refine_stage2_classifications.py

Requirements:
  pip install anthropic pandas tqdm
  export ANTHROPIC_API_KEY=your_key_here
"""
# NEW:
import os
import re
import json
import time
import argparse
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import anthropic

# =============================================================================
# API KEY LOADING
# =============================================================================
def _load_api_key() -> str:
    # Try to load from .env file in project root or script directory
    script_dir = Path(__file__).resolve().parent
    
    # Check for .env in script directory first
    env_path = script_dir / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    
    # Check for .env in project root
    project_root = script_dir.parent.parent  # Adjust based on script location
    env_path = project_root / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    
    # Check environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    
    raise EnvironmentError(
        "\n\nNo Anthropic API key found. Fix with ONE of:\n"
        "  Option A (recommended): create a .env file in project root or script directory:\n"
        f"    echo 'ANTHROPIC_API_KEY=sk-ant-...' > {project_root}/.env\n"
        "  Option B: set the environment variable:\n"
        "    export ANTHROPIC_API_KEY=sk-ant-...\n"
        "\nGet your key at: https://console.anthropic.com/settings/keys\n"
    )

ANTHROPIC_API_KEY = _load_api_key()

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/grant_classifier/
PROJECT_ROOT = SCRIPT_DIR.parent.parent       # climate_biotech_federal_grant_funding/

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Multiyear validation file
MANUAL_CLASSIFICATIONS = DATA_DIR / "YOUR_MANUAL_CLASSIFICATIONS_multiyear.xlsx"

# Input file (from climate_biotech_two_stage_classifier_multiyear.py output)
INFILE = OUTPUT_DIR / "stage2_characterized_all_years.csv"

# Output files
OUT_REFINED = OUTPUT_DIR / "stage2_characterized_all_years.csv"  # Overwrites original
OUT_BACKUP = OUTPUT_DIR / "stage2_characterized_all_years_backup.csv"  # Backup
OUT_TEST_RESULTS = OUTPUT_DIR / "refinement_test_results.csv"
OUT_LOG = OUTPUT_DIR / "refinement_log.json"

# =============================================================================
# SETTINGS
# =============================================================================
# TEST MODE TOGGLE - Set to True to test with validation grants only
TEST_MODE = True  # Set to False for production mode (updates main file)

# MODEL SELECTION
# Options: "claude-sonnet-4-6" (recommended, latest), "claude-opus-4-6" (most accurate, expensive)
REFINE_MODEL = "claude-sonnet-4-6"  # Upgraded from May 2025 version for better accuracy
BATCH_SIZE = 10
MAX_TOKENS = 4096
SLEEP_S = 1.5
MAX_RETRIES = 4

# Validation grant IDs - updated with new manual classifications
VALIDATION_GRANT_IDS = [
    "NSF::1902014",
    "NSF::1912482",
    "NSF::1900272",
    "NSF::1936020",
    "NSF::1938112",
    "USASpending::NNX17AK19G",
    "USASpending::20193352229989",
    "NSF::1916601",
    "NSF::1904185",
    "NSF::1925160",
    "NSF::1847226",
    "USASpending::80NSSC17K0035",
    "NSF::1904700",
    "USASpending::R56DK122380",
    "USASpending::DESC0019472",
    "NSF::1926482",
    "NSF::1914683",
    "NSF::1852245",
    "NSF::1907683",
    "NSF::1936770",
    "NSF::1855128",
    "NSF::1847289",
    "NSF::1921075",
    "USASpending::20196701229713",
    "NSF::1844720",
    "NSF::1843365",
    "NSF::1907163",
    "NSF::1944693",
    "NSF::1903662",
    "NSF::1848212",
    "NSF::1927155",
    "NSF::1913245",
    "NSF::1900699",
    "NSF::1917074",
    "USASpending::DEAR0001103",
    "NSF::1841506",
    "USASpending::20193882129057",
    "NSF::1924464",
    "NSF::1846984",
    "USASpending::DEEE0007563",
    "NSF::1847182",
    "USASpending::80NSSC18K0840",
    "USASpending::80NSSC18K0345",
    "NSF::1855014",
    "USASpending::20193842028971",
    "NSF::1903690",
    "NSF::1936761",
    "USASpending::F19AC00771",
    "NSF::1924466",
    "USASpending::00D86019",
    "USASpending::DEAR0001961",
    "NSF::2042182",
    "USASpending::G19AC00032",
    "NSF::2308873",
    "USASpending::DEFE0032506",
    "NSF::1933793",
    "USASpending::00D93221",
    "NSF::2031085",
    "USASpending::20235140239421",
    "NSF::1926689",
    "NSF::2328291",
    "NSF::1951231",
    "NSF::1914546",
]

# =============================================================================
# IMPROVED REFINEMENT PROMPT
# =============================================================================
REFINEMENT_SYSTEM_PROMPT = """You are an expert at classifying climate biotech research grants with exceptional precision.

You will receive grants that have ALREADY been classified, and your job is to REFINE three specific classifications:
1. Grant Type
2. Application Area  
3. Research Approach

## CLASSIFICATION WORKFLOW

Follow these steps IN ORDER:

**STEP 1: Orientation** (already provided - do not change)
Use the orientation value provided in the input.

**STEP 2: Grant Type** (ALL grants - REFINE THIS)

Ask: What is the PRIMARY deliverable or activity of this grant?

**CRITICAL DISAMBIGUATION RULES:**

**research** - Conducting research, experiments, studies, or analysis WHERE THE RESEARCH ITSELF IS THE PRIMARY GOAL.
  
  ✓ INCLUDE AS RESEARCH:
  - Research that builds models, frameworks, databases, or tools AS PART OF the research process
  - Research that includes pilot/demonstration implementation TO EVALUATE/COMPARE approaches
  - **Technology development/proof-of-concept grants** (even if framed as commercialization research)
  - Comparative studies even if they build something to compare
  - Building tools TO ANSWER research questions
  - Grants that "demonstrate", "prove feasibility", "test performance", "evaluate" approaches
  
  Key test: Is the primary goal to ANSWER A RESEARCH QUESTION, EVALUATE/COMPARE approaches, DEMONSTRATE feasibility, or GENERATE NEW KNOWLEDGE? If YES → research
  
  Examples: 
  - "investigate X", "compare ecological performance and cost benefits"
  - "demonstrate proof-of-concept for this technology"
  - "prove feasibility of approach"
  - "evaluate performance and cost"
  - "build integrated framework for modeling and demonstrate through case studies"
  
  ❌ NOT research if:
  - Building infrastructure for others to use (no research question being answered)
  - Deploying proven technology with no evaluation

**infrastructure** - Building resources for OTHERS to use, including:
  - Physical: Equipment, facilities, buildings
  - Digital: Shared databases, platforms, repositories, tools
  - Human capital: Training programs, workshops, capacity building, educational programs
  - Collaborative: Networks, conferences, community building
  
  Key test: Is the primary goal to BUILD A RESOURCE that OTHERS will use? If YES → infrastructure
  
  Only infrastructure if the resource IS the final product for others, not if built to answer the grant's own research questions.
  
  Examples: "establish training program in X", "workshop series on Y", "build shared database", "create community of practice"

**deployment** - Full-scale implementation of proven technology with NO RESEARCH COMPONENT.
  
  Key test: Is anyone learning anything new? Is any evaluation/comparison happening? If NO to both → deployment

**other** - Truly doesn't fit above (awards, purely administrative coordination, unusual edge cases)

**STEP 3: Research Stage** (research grants only - already provided, do not change)
Use the research_stage value provided in the input.

**STEP 4: Research Approach** (public_facing research grants only - REFINE THIS)

If orientation = industry_facing → set to null, skip to STEP 5

If orientation = public_facing AND grant_type = research:

**collaborative_interdisciplinary** - ONLY if the abstract EXPLICITLY describes integrating or combining multiple disciplines as a CORE feature of the research approach.

Look for explicit language like:
- "interdisciplinary approach"
- "Collaborative Research"
- "integration of [discipline] and [discipline]"
- "combining [field] and [field]"
- "integrating X and Y across disciplines"

Examples:
- "integration of advanced modeling methods from engineering, environmental science, natural science, and data science" ✓
- "interdisciplinary approach combining ecology and engineering" ✓

**single_focus** - Everything else, including:
- Using multiple techniques/methods from one primary discipline
- Mentioning multiple fields without stating integration
- CAREER grants (unless they explicitly state interdisciplinary integration)

NOT interdisciplinary:
- "using genomics, proteomics, and metabolomics" (multiple techniques, one field)
- "biochemistry and bioengineering approaches" (related subfields)
- "Collaborative Research:" in title alone (multi-institution ≠ interdisciplinary)

**Key test:** Does the abstract explicitly use words like "interdisciplinary", "integration of disciplines", or "combining [field] and [field]"? If YES → collaborative_interdisciplinary. Otherwise → single_focus.

**STEP 5: Infrastructure Subtype** (infrastructure grants only - already provided, do not change)
Use the infrastructure_subtype value provided in the input.

**STEP 6: Application Area** (ALL grants)
**Core principle: Classify by what the RESEARCH is advancing, not by products mentioned in passing.**
**Critical question: What is this grant's PRIMARY CONTRIBUTION to the field?**

**CLASSIFY BY OUTCOME, NOT PROCESS:**
The application area should reflect what the research is PRODUCING or ACHIEVING, not HOW it's doing it.

- If a grant improves CO2 fixation to produce chemicals → classify by the CHEMICAL OUTPUT (platform_biochemicals), not the carbon capture process
- If a grant treats waste to produce valuable products → classify by the PRODUCT (platform_biochemicals, biogas, etc.), not the waste treatment
- If a grant treats waste to clean water/remove pollutants → classify by the REMEDIATION OUTCOME (pollution_degradation_remediation)
- If a grant engineers organisms that naturally fix CO2 to make MORE of a specific product → classify by the PRODUCT

Ask: "What is the END RESULT this research is optimizing for?" That's your classification.

Read the full abstract and ask:

Read the full abstract and ask:
1. What biological system, organism, pathway, or process is being engineered/developed/optimized?
2. What is the MAIN innovation - the thing that didn't exist or work well before?
3. If multiple outputs are mentioned, which one is the research designed to improve?

**Classification logic:**

**For organism/pathway engineering grants:**
- If developing organisms to produce liquid fuels (ethanol, biodiesel, SAF) → liquid_transportation_fuels
- If developing organisms to produce gaseous energy (biogas, methane, hydrogen) → biogas_gaseous_energy
- If developing organisms to produce chemical building blocks → platform_biochemicals
- If developing organisms to produce polymers or materials → bio_based_materials
- If developing organisms to produce proteins/specialty products → specialty_bioproducts

**For carbon/GHG management grants:**
- If developing NEW CO2 capture/fixation technology or organisms → biological_carbon_capture
  - Key test: Is the PRIMARY innovation about capturing MORE CO2 or developing NEW capture mechanisms?
  - Examples: Novel carbonic anhydrase enzymes, new gas fermentation pathways, engineering NEW photosynthetic organisms
  - NOT carbon capture: Engineering organisms that ALREADY do photosynthesis to make products better (classify by the product)
  
- If developing mineral weathering or enhanced rock weathering → bio_mineral_weathering
- If developing methane removal/oxidation or methanotroph engineering → methane_removal_oxidation

**For environmental remediation grants:**
- If developing methods to REMOVE, PREVENT, or DEGRADE pollutants/contaminants/excess nutrients → pollution_degradation_remediation
  - Key test: Is the goal to GET RID OF the pollutant or prevent it from entering the environment?
  - Includes: Biodegradation, bioremediation, detoxification, pollution prevention, nutrient reduction
  - Examples: PFAS degradation, plastic biodegradation, stormwater contaminant removal, preventing nutrient runoff with cover crops
  
- If developing methods to EXTRACT and RECOVER valuable nutrients/resources FROM wastewater for REUSE → wastewater_nutrient_recovery
  - Key test: Is the goal to CAPTURE the nutrient/resource and USE IT for something valuable?
  - Examples: Phosphorus recovery for fertilizer, nitrogen extraction for reuse, biogas production from wastewater treatment
  - NOT recovery: Simply reducing/removing excess nutrients (that's pollution_degradation_remediation)
  
- If developing biomining or metal/mineral recovery → biomining_resource_recovery

**For agricultural grants:**
- If developing traditional crop improvement (breeding, GMO, conventional pest control) → crop_productivity_traditional
- If developing soil microbiome or nitrogen fixation technology → soil_microbiome_n_fixation
- If developing seaweed, marine, or aquatic biotechnology → marine_aquatic_biotech

**For monitoring/infrastructure:**
- If developing sensors, detection tools, or monitoring systems → ecosystem_monitoring
- If developing databases/models/analysis tools → research_infrastructure

**CRITICAL: Classify by PRIMARY research contribution, not byproducts.** 
- If the grant's main goal is to PRODUCE a chemical/fuel/material → classify by that product category
- If the grant's main goal is to TREAT waste and producing something valuable is secondary → classify by the treatment goal
- Example: "Produce platform chemicals from dairy waste" → platform_biochemicals (primary goal is chemical production)
- Example: "Treat wastewater and recover nitrogen" → wastewater_nutrient_recovery (primary goal is recovery)
- Example: "Remove stormwater contaminants" → pollution_degradation_remediation (primary goal is removal)

**Hierarchical decision tree when multiple categories could apply:**
1. Is the PRIMARY innovation about carbon/GHG management (CO2 capture, sequestration, weathering, methane removal)? → Use carbon/GHG categories
2. Is it about energy/fuels specifically? → Use energy categories
3. Is it about remediation/cleanup? → Use remediation categories
4. Is it about agriculture/crops/soil? → Use agriculture categories
5. Is it about producing chemicals/materials for manufacturing? → Use bioproducts categories
6. Is it about monitoring/tools/infrastructure? → Use monitoring categories

Choose ONE primary climate biotech application:

**ENERGY & FUELS:**
- liquid_transportation_fuels - Liquid fuels (ethanol, biodiesel, sustainable aviation fuel, renewable diesel)
- biogas_gaseous_energy - Gaseous energy carriers (biogas, biomethane, biohydrogen, syngas)

**CARBON & GHG MANAGEMENT:**
- biological_carbon_capture - NEW or IMPROVED CO2 capture/fixation technologies (carbonic anhydrase enzymes, Wood-Ljungdahl pathway engineering, C1 gas fermentation, developing NEW photosynthetic organisms). NOT for engineering existing photosynthetic organisms to make products better.
- bio_mineral_weathering - Enhanced rock weathering, mineral carbonation for carbon removal
- methane_removal_oxidation - Atmospheric methane removal, methane oxidation, methanotroph engineering

**BIOPRODUCTS & MANUFACTURING:**
- platform_biochemicals - Chemical building blocks, organic acids, platform chemicals that are INPUTS for manufacturing. The grant produces the chemical, not the final polymer/material.
- bio_based_materials - Bioplastics, biodegradable polymers, bio-based materials, living materials. The grant produces the FINAL polymer/material, not just the chemical building block.
- specialty_bioproducts - Cultured meat, precision fermentation proteins, enzymes, high-value molecules

**ENVIRONMENTAL REMEDIATION:**
- pollution_degradation_remediation - Removing, preventing, or degrading pollutants and contaminants (PFAS, plastics, pesticides, excess nutrients). Includes biodegradation, bioremediation, detoxification, and pollution prevention.
- wastewater_nutrient_recovery - Extracting and recovering valuable nutrients/resources FROM wastewater for reuse (nitrogen recovery for fertilizer, phosphorus extraction, biogas production). NOT simple removal - must involve capturing for reuse.
- biomining_resource_recovery - Rare earth elements, critical minerals, metal recovery from waste

**AGRICULTURE & ECOSYSTEMS:**
- crop_productivity_traditional - Traditional crop breeding, conventional agricultural biotechnology, pest control
- soil_microbiome_n_fixation - Soil microbiome engineering, biological nitrogen fixation, rhizosphere manipulation
- marine_aquatic_biotech - Seaweed cultivation, marine carbon sequestration, aquaculture, coral restoration

**MONITORING & INFRASTRUCTURE:**
- ecosystem_monitoring - Biosensors, environmental monitoring, detection tools, ecological assessment
- research_infrastructure - Databases, models, analysis platforms, research tools (use sparingly)

**CATCH-ALL (use only if truly doesn't fit):**
- other_climate_biotech - Doesn't fit above categories

## OUTPUT FORMAT

**CRITICAL INSTRUCTION:** You will receive multiple grants. Return a JSON ARRAY of objects, one for each grant.

Your response must be ONLY a JSON array starting with [ and ending with ]. Do NOT include:
- Any explanation before or after the JSON
- Any "Looking at" or "Following the steps" text
- Any markdown code blocks or formatting
- Any text outside the JSON array

Format:
[
  {
    "grant_id": "unique_key from input",
    "grant_type": "research" | "infrastructure" | "deployment" | "other",
    "research_approach": "collaborative_interdisciplinary" | "single_focus" | null,
    "application_area": [one of the areas listed above],
    "confidence": "high" | "low",
    "reasoning": "Brief explanation of refinements made (1-2 sentences)"
  },
  {
    "grant_id": "...",
    ...
  }
]

REPEAT: Return ONLY the JSON array. Start with [ and end with ]. Nothing else.

IMPORTANT:
- research_approach is null if grant_type != "research" OR orientation = "industry_facing"
- Focus on the THREE categories being refined: grant_type, research_approach, application_area
- Use the decision trees and specific examples to disambiguate close cases
"""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _safe_str(val):
    """Convert value to string safely."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()

def _extract_json_array(text: str):
    """Extract JSON array from LLM response, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find JSON array in text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        raise ValueError(f"Could not parse JSON: {e}\nText: {text[:500]}")

def _build_grant_text(row) -> str:
    """Build text representation of a grant for LLM input."""
    title = _safe_str(row.get("title", ""))
    abstract = _safe_str(row.get("abstract", ""))
    award_type = _safe_str(row.get("award_type", ""))
    institution = _safe_str(row.get("institution", ""))
    unique_key = _safe_str(row.get("unique_key", ""))
    
    # Include current classifications for context
    current_grant_type = _safe_str(row.get("s2_grant_type", ""))
    current_orientation = _safe_str(row.get("s2_orientation", ""))
    current_research_stage = _safe_str(row.get("s2_research_stage", ""))
    current_research_approach = _safe_str(row.get("s2_research_approach", ""))
    current_application_area = _safe_str(row.get("s2_application_area", ""))
    current_infrastructure_subtype = _safe_str(row.get("s2_infrastructure_subtype", ""))
    
    return f"""Grant ID: {unique_key}
Title: {title}
Award Type: {award_type}
Institution: {institution}
Abstract: {abstract}

Current Classifications:
- orientation: {current_orientation}
- grant_type: {current_grant_type}
- research_stage: {current_research_stage}
- research_approach: {current_research_approach}
- infrastructure_subtype: {current_infrastructure_subtype}
- application_area: {current_application_area}"""

# =============================================================================
# REFINEMENT CLASSIFIER
# =============================================================================
def refine_batch(client, batch, model=REFINE_MODEL, max_tokens=MAX_TOKENS):
    """
    Refine grant_type, application_area, and research_approach for a batch of grants.
    Returns: (parsed_results, raw_response_text)
    """
    grant_texts = [_build_grant_text(row) for row in batch]
    
    user_msg = "Refine these grant classifications (focus on grant_type, application_area, research_approach):\n\n" + "\n\n---\n\n".join(grant_texts)
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=REFINEMENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}]
            )
            
            # Safety check: ensure response.content exists and has elements
            if not response.content or len(response.content) == 0:
                raise ValueError("API returned empty response.content")
            
            raw_text = response.content[0].text
            results = _extract_json_array(raw_text)
            
            # Validate results
            expected_ids = {_safe_str(r.get("unique_key")) for r in batch}
            returned_ids = {_safe_str(r.get("grant_id")) for r in results}
            
            if expected_ids != returned_ids:
                print(f"  ⚠️  ID mismatch. Expected {len(expected_ids)}, got {len(returned_ids)}")
            
            return results, raw_text
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  ⚠️  Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ Failed after {MAX_RETRIES} attempts: {e}")
                # Return empty results for this batch
                return [], str(e)

def apply_refinement_results(df, results_dict):
    """Apply refinement results to dataframe."""
    for idx, row in df.iterrows():
        gid = str(row.get("unique_key", "")).strip()
        if gid in results_dict:
            r = results_dict[gid]
            # Update the three refined categories
            df.at[idx, "s2_grant_type"] = r.get("grant_type", row.get("s2_grant_type"))
            df.at[idx, "s2_application_area"] = r.get("application_area", row.get("s2_application_area"))
            df.at[idx, "s2_research_approach"] = r.get("research_approach", row.get("s2_research_approach"))
            df.at[idx, "s2_confidence"] = r.get("confidence", row.get("s2_confidence"))
            
            # Add refinement note
            df.at[idx, "refinement_reasoning"] = r.get("reasoning", "")

# =============================================================================
# TEST ACCURACY FUNCTION
# =============================================================================
def test_accuracy(refined_df):
    """Test accuracy against manual classifications."""
    print("\n" + "="*80)
    print("TESTING ACCURACY AGAINST MANUAL CLASSIFICATIONS")
    print("="*80)
    
    # Load manual classifications
    manual = pd.read_excel(MANUAL_CLASSIFICATIONS)
    manual['grant_id'] = manual['grant_id'].astype(str).str.strip()
    
    # Merge with refined results
    test_df = manual.merge(
        refined_df[['unique_key', 's2_grant_type', 's2_application_area', 's2_research_approach']],
        left_on='grant_id',
        right_on='unique_key',
        how='inner'
    )
    
    results = {}
    
    # Test Grant Type
    valid = test_df[['YOUR_s2_grant_type', 's2_grant_type']].dropna()
    if len(valid) > 0:
        matches = (test_df['YOUR_s2_grant_type'] == test_df['s2_grant_type'])
        correct = matches.sum()
        total = len(valid)
        accuracy = correct / total if total > 0 else 0.0
        results['Grant Type'] = {'total': total, 'correct': correct, 'accuracy': accuracy}
        print(f"\nGrant Type:")
        print(f"  Total: {total}")
        print(f"  Correct: {correct}")
        print(f"  Accuracy: {accuracy:.2%}")
    
    # Test Application Area
    valid = test_df[['NEW_s2_application_area', 's2_application_area']].dropna()
    if len(valid) > 0:
        matches = (test_df['NEW_s2_application_area'] == test_df['s2_application_area'])
        correct = matches.sum()
        total = len(valid)
        accuracy = correct / total if total > 0 else 0.0
        results['Application Area'] = {'total': total, 'correct': correct, 'accuracy': accuracy}
        print(f"\nApplication Area:")
        print(f"  Total: {total}")
        print(f"  Correct: {correct}")
        print(f"  Accuracy: {accuracy:.2%}")
    
    # Test Research Approach
    valid = test_df[['YOUR_s2_research_approach', 's2_research_approach']].dropna()
    if len(valid) > 0:
        matches = (test_df['YOUR_s2_research_approach'] == test_df['s2_research_approach'])
        correct = matches.sum()
        total = len(valid)
        accuracy = correct / total if total > 0 else 0.0
        results['Research Approach'] = {'total': total, 'correct': correct, 'accuracy': accuracy}
        print(f"\nResearch Approach:")
        print(f"  Total: {total}")
        print(f"  Correct: {correct}")
        print(f"  Accuracy: {accuracy:.2%}")
    
    print("\n" + "="*80)
    return results, test_df

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    # Allow command-line override of TEST_MODE setting
    parser = argparse.ArgumentParser(description='Refine Stage 2 classifications')
    parser.add_argument('--test', action='store_true', help='Run in test mode (overrides TEST_MODE setting)')
    parser.add_argument('--production', action='store_true', help='Run in production mode (overrides TEST_MODE setting)')
    args = parser.parse_args()
    
    # Determine mode: command-line args override the TEST_MODE setting
    if args.production:
        test_mode = False
    elif args.test:
        test_mode = True
    else:
        test_mode = TEST_MODE  # Use the setting at top of file
    
    print("="*80)
    print("STAGE 2 CLASSIFICATION REFINEMENT")
    print("="*80)
    print(f"Mode: {'TEST (validation grants only)' if test_mode else 'PRODUCTION (all grants)'}")
    print()
    
    # Load data
    print("Loading data...")
    df = pd.read_csv(INFILE)
    df['unique_key'] = df['unique_key'].astype(str).str.strip()
    print(f"✓ Loaded {len(df)} grants from {INFILE}")
    
    # Filter to grants that need refinement
    # Only refine grants that were classified in Stage 2 (have s2_grant_type)
    refinement_mask = df['s2_grant_type'].notna()
    
    if test_mode:
        # Test mode: only validation grants
        refinement_mask = refinement_mask & df['unique_key'].isin(VALIDATION_GRANT_IDS)
        df_all_rows = df[refinement_mask].copy()  # Keep ALL rows including duplicates
        print(f"✓ Test mode: Selected {len(df_all_rows)} validation rows")
        
        # DEDUPLICATE for LLM processing (avoid confusing LLM with duplicate grants)
        df_refine = df_all_rows.drop_duplicates(subset='unique_key', keep='first').reset_index(drop=True)
        print(f"  Deduplicating for refinement: {len(df_refine)} unique grants ({len(df_all_rows) - len(df_refine)} duplicates removed)")
    else:
        # Production mode: create backup first
        print(f"✓ Production mode: Creating backup at {OUT_BACKUP}")
        df.to_csv(OUT_BACKUP, index=False)
        
        df_all_rows = df[refinement_mask].copy()  # Keep ALL rows
        
        # DEDUPLICATE for LLM processing
        df_refine = df_all_rows.drop_duplicates(subset='unique_key', keep='first').reset_index(drop=True)
        print(f"  Deduplicating for refinement: {len(df_refine)} unique grants ({len(df_all_rows) - len(df_refine)} duplicates removed)")
    
    if len(df_refine) == 0:
        print("No grants to refine!")
        return
    
    # Process batches
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    rows = [df_refine.iloc[i] for i in range(len(df_refine))]
    batches = [rows[i:i+BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    
    all_results = {}
    log_entries = []
    
    print(f"\nProcessing {len(batches)} batches ({BATCH_SIZE} grants each)...\n")
    
    for batch_idx, batch in enumerate(tqdm(batches, desc="Refining")):
        results, raw_text = refine_batch(client, batch)
        
        log_entries.append({
            "batch": batch_idx,
            "ids": [_safe_str(r.get("unique_key")) for r in batch],
            "raw_response": raw_text,
        })
        
        for r in results:
            gid = str(r.get("grant_id", "")).strip()
            all_results[gid] = r
        
        time.sleep(SLEEP_S)
    
    # Apply results
    apply_refinement_results(df_refine, all_results)
    
    # Update original dataframe
    for idx, row in df.iterrows():
        if row['unique_key'] in df_refine['unique_key'].values:
            refined_row = df_refine[df_refine['unique_key'] == row['unique_key']].iloc[0]
            df.at[idx, 's2_grant_type'] = refined_row['s2_grant_type']
            df.at[idx, 's2_application_area'] = refined_row['s2_application_area']
            df.at[idx, 's2_research_approach'] = refined_row['s2_research_approach']
            df.at[idx, 's2_confidence'] = refined_row['s2_confidence']
            if 'refinement_reasoning' in refined_row:
                df.at[idx, 'refinement_reasoning'] = refined_row['refinement_reasoning']
    
    # Save results
    if test_mode:
        df.to_csv(OUT_TEST_RESULTS, index=False)
        print(f"\n✓ Test results saved to: {OUT_TEST_RESULTS}")
        
        # Test accuracy
        accuracy_results, test_df = test_accuracy(df_refine)
        
        # Save detailed test results
        test_output_path = OUTPUT_DIR / "refinement_test_comparison.xlsx"
        with pd.ExcelWriter(test_output_path, engine='openpyxl') as writer:
            test_df.to_excel(writer, sheet_name='Comparison', index=False)
        print(f"✓ Detailed comparison saved to: {test_output_path}")
        
    else:
        df.to_csv(OUT_REFINED, index=False)
        print(f"\n✓ Refined results saved to: {OUT_REFINED}")
        print(f"✓ Backup saved to: {OUT_BACKUP}")
    
    # Save log
    with open(OUT_LOG, "w") as f:
        json.dump(log_entries, f, indent=2, default=str)
    print(f"✓ Log saved to: {OUT_LOG}")
    
    print("\n" + "="*80)
    print("REFINEMENT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
