"""
climate_biotech_two_stage_classifier_multiyear_CORRECTED.py

MULTI-YEAR VERSION: Processes climate_biotech_filtered_all_years.csv (2019-2025)
LOGIC IS 100% IDENTICAL to single-year version - only input/output paths changed

Two-stage LLM classification pipeline for climate biotech grants.
Updated with validation findings, decision tree approach, and comprehensive Stage 2 characterization.

STAGE 1: Biotech Fit Check (KEEP/REMOVE)
  - Uses decision tree approach with ordered checks
  - Based on validation of 39 REMOVED grants (31 correct, 2 false negatives, 6 borderline)
  - Uses Haiku for speed and cost-efficiency
  
STAGE 2: Deep Characterization (KEEP grants only)
  - Grant type (research / infrastructure / deployment / other)
  - Research stage (Use Inspired Research / Bench Scale Tech Development / Piloting) - research only
  - Research approach (collaborative_interdisciplinary / single_focus) - public_facing research only
  - Infrastructure subtype (physical / shared_resources / collaborative) - infrastructure only
  - Orientation (industry_facing / public_facing) - all grants
  - Application area (14 categories) - all grants
  - Uses Sonnet for nuanced classification

Usage:
  python climate_biotech_two_stage_classifier_UPDATED.py

Requirements:
  pip install anthropic pandas tqdm
  export ANTHROPIC_API_KEY=your_key_here
"""

# NEW:
import os
import re
import json
import time
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import anthropic

# =============================================================================
# API KEY LOADING
# =============================================================================
# NEW (replace entire _load_api_key function):
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
# NEW:
# Get the project root directory
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/grant_classifier/
PROJECT_ROOT = SCRIPT_DIR.parent.parent       # climate_biotech_federal_grant_funding/

# Input/Output directories
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Input file (from climate_biotech_filter_multiyear.py output)
INFILE = OUTPUT_DIR / "climate_biotech_filtered_all_years.csv"

# Stage 1 outputs
OUT_STAGE1_ALL = OUTPUT_DIR / "stage1_biotech_fit_all_years.csv"
OUT_STAGE1_EXCL = OUTPUT_DIR / "stage1_excluded_all_years.csv"
OUT_STAGE1_REVIEW = OUTPUT_DIR / "stage1_review_all_years.csv"

# Stage 2 outputs
OUT_STAGE2_CHAR = OUTPUT_DIR / "stage2_characterized_all_years.csv"
OUT_STAGE2_REVIEW = OUTPUT_DIR / "stage2_review_all_years.csv"

# Stage 1 on pools the main flow previously skipped — short-abstract & formula.
# Ports biomining's Stage 2-Short / Stage 2-Formula pattern, but runs only
# Stage 1 KEEP/REMOVE on each pool (no Stage 2 characterization — abstracts
# are too short / the grant is non-competitive, so full axis-assignment isn't
# meaningful). See run_stage1_excluded_pools() at the bottom of this file.
INSUFFICIENT_CSV = OUTPUT_DIR / "climate_biotech_insufficient_abstract_all_years.csv"
MERGED_CSV = OUTPUT_DIR / "merged_all_years.csv"
EXCLUDED_CSV = OUTPUT_DIR / "climate_biotech_excluded_all_years.csv"
OUT_STAGE1_SHORT = OUTPUT_DIR / "stage1_shortabstract_all_years.csv"
OUT_STAGE1_FORMULA = OUTPUT_DIR / "stage1_formula_all_years.csv"

# Log
OUT_LOG = OUTPUT_DIR / "two_stage_classification_log_all_years.json"

# =============================================================================
# SETTINGS
# =============================================================================
# Stage 1: Biotech fit (fast, binary)
STAGE1_MODEL = "claude-haiku-4-5-20251001"
STAGE1_BATCH_SIZE = 20
STAGE1_MAX_TOKENS = 4096

# Stage 2: Deep characterization (nuanced, multi-axis)
STAGE2_MODEL = "claude-sonnet-4-20250514"
STAGE2_BATCH_SIZE = 10
STAGE2_MAX_TOKENS = 4096

SLEEP_S = 1.5
MAX_RETRIES = 4
RESUME = True  # skip already-classified rows

# Test mode: run small sample first
TEST_MODE = False
TEST_SAMPLE_SIZE = 50

# Validation grant IDs - these are the specific 50 grants from the validation Excel file
# When TEST_MODE = True, use these specific grants for comparison with manual validation
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
]


# =============================================================================
# STAGE 1: BIOTECH FIT SYSTEM PROMPT (EXPANDED DEFINITION)
# =============================================================================
STAGE1_SYSTEM_PROMPT = """You are an expert classifier determining whether federal research grants fit the scope of CLIMATE BIOTECH research.

## DEFINITION: Climate Biotech
Realizing the full potential of biology toward a healthy climate - including direct interventions, enabling technologies, diagnostic/monitoring tools that enable action, climate adaptation solutions, and supply chain biotech that uses biological approaches.

**CRITICAL DISTINCTION**: Climate biotech uses biology to address climate change through interventions, tools that enable action, adaptation, or supply chains. It is NOT pure observation/documentation of climate impacts.

## THE DECISION TREE

Follow these checks IN ORDER. Stop at the first REMOVE match. Must pass ALL checks to KEEP.

### CHECK 1: Biological Component Present?
Does the grant involve biological systems OR bio-derived materials?

**Biological systems:** Organisms, enzymes, microbes, genetic engineering, synthetic biology, enzymatic processes

**Bio-derived materials:** Biologically-produced materials (lignin, NOM, cellulose) for climate/environmental solutions

→ If NO biological component: REMOVE "No biological component"
→ If YES: Continue to CHECK 2

(Note: Most grants pass this check due to keyword pre-filtering)

### CHECK 2: Biomedical Focus?
Is this grant primarily focused on treating human disease AFTER it occurs rather than preventing disease by addressing environmental exposures?

**REMOVE if:** 
- Developing therapies, drugs, or clinical treatments for patients with existing disease
- Medical interventions without environmental biotech component
- Research primarily about immune systems, disease mechanisms, or pathogen biology where environmental/climate connection is minimal or tacked on at the end

**KEEP if:** 
- Using biotech approaches to understand, monitor, or prevent disease from environmental exposures
- Biosensors/metagenomics tracking environmental health risks
- Studying causation using biological/molecular methods
- Developing remediation, monitoring, or early warning systems

→ If YES (treating existing disease or primarily biomedical): REMOVE "Biomedical focus"
→ If NO (preventing disease via environmental biotech): Continue to CHECK 3

### CHECK 3: Pure Computer Science?
Is this developing new general-purpose computational methods where biology just happens to be the test dataset?

**REMOVE if:** Novel ML architecture tested on biological data, general-purpose database system demonstrated with genomic sequences

**KEEP if:** Databases, ML tools, or software specifically designed to enable biotech development

→ If YES (general methods, biology is incidental): REMOVE "Computer science methods development"
→ If NO (tools specifically for biotech): Continue to CHECK 4

### CHECK 4: Climate/Environmental Relevance - Is This Actually Climate Biotech?

**This is the MAIN climate filter. Apply these tests in order:**

**TEST A - Window-Dressing Detection:**
Is climate mentioned but the research is fundamentally about something else?

REMOVE if BOTH conditions are true:
1. Main research keywords indicate non-climate focus: "immune response", "receptor signaling", "pathogen recognition", "disease mechanism", "cellular cooperation", "biofilm formation", "metabolic pathway" (basic biology with no climate context)
2. AND climate connection uses only weak hypothetical language: "could be used", "may enable", "potential for", "would allow", "possible application"

Examples to REMOVE (window-dressing):
- Grant studying immune receptors that ends with "findings could enable climate-resilient crops"
- Grant about bacterial colonization mechanisms that says "may help engineer microbiota for climate adaptation"  
- Grant on cellular cooperation in biofilms with "applications to biofuels and remediation" tacked on

Examples to KEEP (genuine climate focus):
- Grant engineering microbiota WHERE climate/agriculture challenge is explained upfront
- Grant on bacterial processes WHERE carbon sequestration is the stated experimental goal

**TEST B - Implicit Climate Solutions:**
Even if climate isn't prominently mentioned, is this inherently a climate solution?

KEEP if the PRIMARY research activity is developing:
- Agricultural pest control or crop protection using biological methods (biopesticides, beneficial microbes, disease resistance)
- Bio-based materials specifically designed to replace fossil-derived plastics, composites, or resins
- Chemical production from biomass where the grant emphasizes renewable/sustainable replacement of petrochemicals
- Biochar production or soil carbon sequestration methods
- Bioremediation or biodegradation of pollutants
- Biomining or bioleaching for extracting critical minerals

Key test: Is the grant ACTIVELY DEVELOPING one of these categories as its main goal? Or just mentioning them as possible future applications?

DO NOT trigger TEST B just because:
- Grant mentions "biomass" or "biofuel" in passing while doing basic biology research
- Synthetic biology work that could theoretically apply to these areas someday
- General microbial engineering without specific climate application focus

**TEST C - Explicit Climate Focus:**
KEEP if:
- Abstract opens with climate/environmental problem statement
- Climate/environmental challenge is what drives and justifies the research
- Grant explicitly targets emissions, carbon, pollution, remediation, or climate adaptation

**Apply tests in order. If TEST A flags it (window-dressing) → REMOVE. If TEST B or TEST C apply → KEEP.**

→ If fails all tests: REMOVE "Insufficient climate/environmental relevance"
→ If passes TEST B or C: Continue to CHECK 5

### CHECK 5: Pure Observation Without Action-Enabling Component?
Is this grant producing knowledge about nature OR tools that enable climate action?

**Simple test - Look for language patterns:**

**REMOVE if abstract uses ONLY observation language:**
- "understand how", "characterize", "quantify", "measure", "track", "document", "examine", "investigate", "study"
- WITHOUT any of: "inform", "guide", "enable", "optimize", "support decisions", "for treatment", "for management"

**KEEP if abstract includes action-enabling language:**
- "to inform decisions/policy/management"
- "to guide treatment/remediation/restoration"  
- "to optimize", "to target", "to enable response"
- "for early warning", "for detection and response"

**Concrete examples:**

REMOVE (observation only):
- "Develop methods to track coral microbiome dynamics and quantify changes" (no stated use)
- "Characterize biodiversity responses to warming" (no action connection)
- "Measure microbial community shifts under climate stress" (pure documentation)

KEEP (action-enabling):
- "Biosensor to detect contamination and guide treatment decisions"
- "Monitor conditions to optimize bioremediation deployment"
- "Track pathogens to inform early warning systems"

**Key test:** Search abstract for action verbs like "inform", "guide", "enable", "optimize". If found → KEEP. If only observation verbs → REMOVE.

→ If purely observational (no action verbs): REMOVE "Observational monitoring without action-enabling component"
→ If action-enabling (has action verbs): Continue to CHECK 6

### CHECK 6: Climate Impact Study Without Application?
Is this studying HOW climate affects organisms/ecosystems WITHOUT connecting to biotech interventions or climate action?

**REMOVE:**
- Climate-carbon cycle modeling for academic understanding alone
- Studies of how warming affects interactions without stated biotech application
- Predicting ecosystem responses without connecting to conservation, adaptation, or policy

**KEEP:**
- Using biological/molecular methods to study impacts
- Modeling to inform climate mitigation strategies or policy decisions
- Understanding impacts to guide adaptation or biotech development
- Research that explicitly informs resource management or conservation action

**Key test:** Does the study use biotech methods OR produce knowledge that explicitly informs climate action/policy?

→ If YES: Continue to CHECK 7
→ If NO (pure academic understanding): REMOVE "Climate impact study without stated application"

### CHECK 7: Does Grant Develop Climate Biotech Solutions or Tools?
Final check - does this grant actually develop something useful for climate?

Look for ANY of these:

**Direct interventions:**
- Engineer, design, develop, create, optimize biological systems for climate solutions
- Bio-derived materials for remediation or sustainable products

**Diagnostic/monitoring tools that enable action:**
- Biosensors, metagenomics, detection methods for climate/environmental problems
- Monitoring systems to improve preparedness, response, or treatment decisions
- Early warning systems, pathogen surveillance

**Enabling technologies:**
- Databases, models using biological data to inform climate action or policy
- Tools for analyzing or optimizing biotech solutions

**Climate supply chain biotech:**
- Biomining for critical minerals (batteries, clean energy infrastructure)
- Bio-based materials replacing carbon-intensive alternatives

**Climate adaptation:**
- Resilience tools, disaster preparedness, health protection using biotech
- Climate-resilient agriculture or ecosystem restoration methods

→ If develops any of above: KEEP
→ If none of above: REMOVE "No biotech solutions, tools, or climate action connection"

## EDGE CASES

**Equipment/Infrastructure/Buildings:**
- Dedicated to climate biotech research → KEEP
- Multi-purpose for many unrelated projects → REMOVE

**Workshops/Capacity Building/Training:**
- Focused on climate biotech topics → KEEP
- General science or unrelated topics → REMOVE

## KEY PATTERNS

**KEEP patterns:**
- Direct interventions: "engineer microbes for carbon capture," "develop biofuels"
- Sustainable agriculture: "pest management," "soil health," "climate-resilient crops"
- Bio-based materials: "bioplastics," "bio-composites replacing fossil materials"
- Diagnostic tools: "biosensors for detecting," "metagenomics to track"
- Monitoring for action: "to inform treatment," "to guide decisions," "to optimize"
- Supply chain: "biomining for battery metals," "critical minerals for clean energy"
- Adaptation: "early warning systems," "climate-resilient varieties"

**REMOVE patterns:**  
- Window-dressing: Climate mentioned only at end of immunology/basic biology research
- Pure observation: "Understanding how X affects Y" without stated action/application
- Academic ecology: Monitoring climate impacts for documentation only
- Biomedical: Disease treatment without environmental focus

## OUTPUT FORMAT (JSON only):
{
  "grant_id": "unique_key from input",
  "decision": "KEEP" or "REMOVE",
  "confidence": "high" or "low",
  "reasoning": "1-2 sentence explanation stating which check determined the decision"
}

IMPORTANT:
- Follow checks 1-7 in order, stop at first REMOVE
- Must pass ALL checks to KEEP
"""

# =============================================================================
# STAGE 2: DEEP CHARACTERIZATION SYSTEM PROMPT
# =============================================================================
STAGE2_SYSTEM_PROMPT = """You are an expert at characterizing climate biotech research grants across multiple dimensions.

## CLASSIFICATION WORKFLOW

Follow these steps IN ORDER:

**STEP 1: Orientation** (ALL grants)
Check in this order, stop at first match:
1. Award Type contains SBIR/STTR OR Title contains "I-Corps"? → industry_facing
2. Abstract contains "non-profit" or "not-for-profit" or "nonprofit"? → public_facing
3. Recipient Institution contains University/College/Institute/School? → public_facing
4. Recipient Institution contains state name + Tech/State (e.g., Georgia Tech, Ohio State)? → public_facing
5. Recipient Institution: National Lab/Government agency/Tribal? → public_facing
6. Recipient Institution contains Foundation/Action/Restoration/Community/Corps (not I-Corps)? → public_facing
7. Recipient Institution: Private company (LLC/Inc/Corp)? → industry_facing
8. Abstract contains IP/patent/commercialization language? → industry_facing
9. Default → public_facing

**STEP 2: Grant Type** (ALL grants)

Ask: What is the PRIMARY deliverable or activity of this grant?

- **research**: Conducting research, experiments, studies, or analysis WHERE THE RESEARCH ITSELF IS THE PRIMARY GOAL. This includes research that builds models, frameworks, databases, or tools AS PART OF the research process, and research that includes pilot/demonstration implementation TO EVALUATE/COMPARE approaches.
  
  Key test: Is the primary goal to ANSWER A RESEARCH QUESTION, EVALUATE/COMPARE approaches, or GENERATE NEW KNOWLEDGE? If YES → research
  
  Examples: "investigate X", "compare ecological performance and cost benefits", "build integrated framework for modeling and demonstrate through case studies"
  
  Critical: Implementation AS PART OF a comparative/evaluation study = research. Building tools TO ANSWER research questions = research.
  
  (If research → go to STEP 3)

- **infrastructure**: Building physical equipment, shared databases/platforms/tools, or facilities WHERE THE INFRASTRUCTURE ITSELF IS THE PRIMARY DELIVERABLE for others to use.
  
  Key test: Is the primary goal to BUILD A TOOL/FACILITY that OTHERS will use? If YES → infrastructure
  
  Only infrastructure if the tool IS the final product for others, not if built to answer the grant's own research questions.
  
  (If infrastructure → go to STEP 5)

- **deployment**: Full-scale implementation of proven technology with NO RESEARCH COMPONENT. No evaluation, no comparison, no learning objectives.
  
  Key test: Is anyone learning anything new? Is any evaluation/comparison happening? If NO to both → deployment
  
  (If deployment → go to STEP 6)

- **other**: None of above categories fit
  
  (If other → go to STEP 6)

**STEP 3: Research Stage** (research grants only)

Follow the decision tree in order, stop at first match:

**1. Use Inspired Research** - Foundational knowledge or capability development

Output is KNOWLEDGE, FOUNDATIONAL UNDERSTANDING, or ENABLING CAPABILITIES that future technology development will depend on - NOT a specific end-use technology.

**Three categories of Use Inspired Research:**

a) **PURE KNOWLEDGE GENERATION** (observational/computational only):
   - Mechanism studies, characterization, modeling, simulation
   - Ecological surveys, inventories, databases
   - No physical prototype or process being built
   - Examples: "understand mechanisms of", "characterize", "role of X in Y"

b) **FOUNDATIONAL TOOL/METHOD DEVELOPMENT** (building capabilities for future research):
   - Developing genetic engineering tools, vectors, CRISPR systems
   - Creating analytical methods, assays, protocols, platforms
   - Building research instruments or capabilities
   - KEY DISTINCTION: The tool/method itself is NOT the end product - it ENABLES others to build end products later
   - Examples: "develop genetic tools to engineer Clostridia", "create analytical methods for"
   - CAREER grants focused on building capabilities often fall here

c) **FUNDAMENTAL PROCESS RESEARCH** (studying processes broadly, not proving specific tech):
   - Investigating how processes work at fundamental level across multiple approaches
   - Testing different pathways/catalysts/mechanisms to understand which work and why
   - Establishing baseline feasibility across broad design space
   - KEY DISTINCTION: Focus is on understanding the SCIENCE of a process type, not proving ONE specific configuration
   - Examples: "investigate catalysts for biomass pyrolysis", "engineering biofilm-electrode interactions"

Key test for Use Inspired Research:
- Is this building FOUNDATIONAL UNDERSTANDING or CAPABILITIES that MANY future technologies could use? → YES
- Could MULTIPLE different specific applications emerge from this work? → YES
- Is the output a specific ready-to-deploy technology for ONE specific use? → NO

Signals: "develop tools/methods/capabilities", "investigate/explore/study", "understand/establish/characterize", CAREER grants building research capabilities

**2. Bench Scale Tech Development** - First-time proof-of-concept for SPECIFIC technology

A SPECIFIC, NOVEL technology/process/system is being built and tested for a SPECIFIC END USE for the FIRST TIME at lab/bench scale.

Key characteristics:
- The grant has ONE SPECIFIC end-use target (e.g., "produce biofuel X from feedstock Y using strain Z")
- Testing whether THIS PARTICULAR APPROACH works
- A NEW approach being demonstrated for the first time
- The core question is "does THIS SPECIFIC THING work at all?"
- Output is a working prototype demonstrating feasibility of THIS specific configuration

CRITICAL DISTINCTION from Use Inspired Research:
- Use Inspired = developing capabilities/understanding that enable MANY future technologies
- Bench Scale = proving ONE specific technology works for ONE specific use

Signals: "proof of concept", "demonstrate feasibility of", "EAGER", "SBIR Phase I", specific product + specific organism/process + specific substrate all named

**3. Piloting** - Optimizing/scaling KNOWN technology

A KNOWN, PREVIOUSLY DEMONSTRATED technology or process is being optimized, scaled, or piloted.

Key characteristics:
- A prototype or working process already EXISTS and has been demonstrated
- The core question is "how do we make this work BETTER or BIGGER?"
- Output is performance improvement, scale-up results, or pilot demonstration

Signals: "pilot-scale", "scale-up", "SBIR Phase II" (always Piloting), "optimize", explicit reference to prior work

**Special rules:**
- EAGER grants: Always have specific technology target → Bench Scale Tech Development minimum
- CAREER grants: Often focused on capability building → default to Use Inspired unless clear specific end-use technology target

**DECISION TREE - Follow in order, stop at first match:**

Step 1: Is the output PURELY knowledge/data with nothing physical built? → Use Inspired Research

Step 2: Is this developing FOUNDATIONAL TOOLS/METHODS/CAPABILITIES that enable future research rather than proving a specific end-use technology? → Use Inspired Research

Step 3: Is this FUNDAMENTAL PROCESS RESEARCH studying how processes work generally rather than proving one specific configuration for one specific use? → Use Inspired Research

Step 4: Is this building/testing a SPECIFIC NEW technology for a SPECIFIC end use for the FIRST time? → Bench Scale Tech Development

Step 5: Is a known technology being optimized/scaled/piloted? → Piloting

(Then go to STEP 4)

**STEP 4: Research Approach** (public_facing research grants only)

- If orientation = industry_facing → set to null, skip to STEP 6

- If public_facing AND abstract EXPLICITLY describes integrating or combining multiple disciplines as a core feature of the research approach (e.g., "integration of advanced modeling methods from engineering, environmental science, natural science, and data science", "interdisciplinary approach combining X and Y", "integrating observations and modeling across the earth system") → collaborative_interdisciplinary

- If public_facing AND no explicit interdisciplinary integration language → single_focus

Key distinction: Simply using multiple techniques/methods or mentioning multiple fields does NOT equal interdisciplinary. Only classify as collaborative_interdisciplinary if the abstract explicitly emphasizes integration/combining of disciplines as a core approach.

(Then go to STEP 6)

**STEP 5: Infrastructure Subtype** (infrastructure grants only)
- Equipment/facilities/buildings? → physical
- Databases/repositories/platforms? → shared_resources
- Workshops/conferences/training? → collaborative
(Then go to STEP 6)

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
    "research_stage": "Use Inspired Research" | "Bench Scale Tech Development" | "Piloting" | null,
    "research_approach": "collaborative_interdisciplinary" | "single_focus" | null,
    "infrastructure_subtype": "physical" | "shared_resources" | "collaborative" | null,
    "orientation": "industry_facing" | "public_facing",
    "application_area": [one of the 14 areas listed above],
    "confidence": "high" | "low"
  },
  {
    "grant_id": "...",
    ...
  }
]

REPEAT: Return ONLY the JSON array. Start with [ and end with ]. Nothing else.

IMPORTANT:
- Your response must be ONLY the JSON object
- Follow classification steps in order mentally but output only JSON
- research_stage is null if grant_type != "research"
- research_approach is null if grant_type != "research" OR orientation = "industry_facing"
- infrastructure_subtype is null if grant_type != "infrastructure"
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
    agency = _safe_str(row.get("agency", ""))
    recipient = _safe_str(row.get("recipient_name", ""))
    award_key = _safe_str(row.get("unique_key", ""))
    
    return f"""Grant ID: {award_key}
Title: {title}
Agency: {agency}
Recipient: {recipient}
Abstract: {abstract}"""

# =============================================================================
# STAGE 1: BIOTECH FIT CLASSIFIER
# =============================================================================
def classify_stage1_batch(client, batch, model=STAGE1_MODEL, max_tokens=STAGE1_MAX_TOKENS):
    """
    Classify a batch of grants for biotech fit.
    Returns: (parsed_results, raw_response_text)
    """
    grant_texts = [_build_grant_text(row) for row in batch]
    
    user_msg = "Classify these grants for climate biotech fit:\n\n" + "\n\n---\n\n".join(grant_texts)
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=STAGE1_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}]
            )
            
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
                return [{"grant_id": _safe_str(r.get("unique_key")), 
                        "decision": "REMOVE", 
                        "confidence": "low",
                        "reasoning": "Classification failed"} for r in batch], str(e)

def apply_stage1_results(df, results_dict):
    """Apply Stage 1 classification results to dataframe."""
    for idx, row in df.iterrows():
        gid = str(row.get("unique_key", "")).strip()
        if gid in results_dict:
            r = results_dict[gid]
            df.at[idx, "s1_decision"] = r.get("decision", "REMOVE")
            df.at[idx, "s1_confidence"] = r.get("confidence", "low")
            df.at[idx, "s1_reasoning"] = r.get("reasoning", "")

# =============================================================================
# STAGE 2: DEEP CHARACTERIZATION CLASSIFIER
# =============================================================================
def classify_stage2_batch(client, batch, model=STAGE2_MODEL, max_tokens=STAGE2_MAX_TOKENS):
    """
    Deep characterization for grants that passed Stage 1.
    Returns: (parsed_results, raw_response_text)
    """
    grant_texts = [_build_grant_text(row) for row in batch]
    
    user_msg = "Characterize these climate biotech grants:\n\n" + "\n\n---\n\n".join(grant_texts)
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=STAGE2_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}]
            )
            
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
                return [{"grant_id": _safe_str(r.get("unique_key")),
                        "research_stage": "unknown",
                        "orientation": "unknown", 
                        "collaboration": "unknown",
                        "confidence": "low",
                        "reasoning": "Classification failed"} for r in batch], str(e)

def apply_stage2_results(df, results_dict):
    """Apply Stage 2 characterization results to dataframe."""
    for idx, row in df.iterrows():
        gid = str(row.get("unique_key", "")).strip()
        if gid in results_dict:
            r = results_dict[gid]
            df.at[idx, "s2_grant_type"] = r.get("grant_type", "unknown")
            df.at[idx, "s2_research_stage"] = r.get("research_stage")
            df.at[idx, "s2_research_approach"] = r.get("research_approach")
            df.at[idx, "s2_infrastructure_subtype"] = r.get("infrastructure_subtype")
            df.at[idx, "s2_orientation"] = r.get("orientation", "unknown")
            df.at[idx, "s2_application_area"] = r.get("application_area", "unknown")
            df.at[idx, "s2_confidence"] = r.get("confidence", "low")
            # df.at[idx, "s2_reasoning"] = r.get("reasoning", "")  # Removed to prevent JSON truncation

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def main():
    print("="*70)
    print("CLIMATE BIOTECH TWO-STAGE LLM CLASSIFIER")
    print("EXPANDED DEFINITION: Biology for planetary health")
    print("="*70)
    print()
    
    # Load data
    print("Loading input data...")
    df = pd.read_csv(INFILE)
    print(f"  Loaded {len(df)} grants from keyword-filtered dataset")
    print()
    
    # Initialize Stage 1 columns
    s1_cols = ["s1_decision", "s1_confidence", "s1_reasoning"]
    for col in s1_cols:
        if col not in df.columns:
            df[col] = pd.NA
    
    # Initialize Stage 2 columns
    s2_cols = ["s2_grant_type", "s2_research_stage", "s2_research_approach",
               "s2_infrastructure_subtype", "s2_orientation", "s2_application_area",
               "s2_confidence"]
    for col in s2_cols:
        if col not in df.columns:
            df[col] = pd.NA
    
    # ==========================================================================
    # STAGE 1: BIOTECH FIT CHECK
    # ==========================================================================
    print("="*70)
    print("STAGE 1: BIOTECH FIT CHECK (Haiku)")
    print("="*70)
    print()
    
    # Check for resume
    if RESUME and OUT_STAGE1_ALL.exists():
        print("  Resuming from existing Stage 1 results...")
        existing = pd.read_csv(OUT_STAGE1_ALL)
        classified_keys = set(existing[existing["s1_decision"].notna()]["unique_key"].astype(str))
        print(f"  Found {len(classified_keys)} already-classified grants")
    else:
        classified_keys = set()
    
    # Determine what needs Stage 1 classification
    s1_todo_mask = ~df["unique_key"].astype(str).isin(classified_keys)
    df_s1_todo = df[s1_todo_mask].copy().reset_index(drop=True)
    df_s1_done = df[~s1_todo_mask].copy()
    
    # Test mode - use specific validation grants
    if TEST_MODE:
        print(f"  TEST MODE: selecting {len(VALIDATION_GRANT_IDS)} validation grants")
        # Filter to only the validation grant IDs
        df_s1_todo = df_s1_todo[df_s1_todo['unique_key'].isin(VALIDATION_GRANT_IDS)].copy().reset_index(drop=True)
        print(f"  Found {len(df_s1_todo)} validation grants in dataset")
        if len(df_s1_todo) == 0:
            print(f"  WARNING: No validation grants found! Check that unique_key format matches.")
            print(f"  Falling back to random sample of {TEST_SAMPLE_SIZE} grants")
            df_s1_todo = df[s1_todo_mask].sample(n=TEST_SAMPLE_SIZE, random_state=42).reset_index(drop=True)
    
    print(f"  Grants needing Stage 1 classification: {len(df_s1_todo)}")
    
    if len(df_s1_todo) > 0:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        rows = [df_s1_todo.iloc[i] for i in range(len(df_s1_todo))]
        batches = [rows[i:i+STAGE1_BATCH_SIZE] for i in range(0, len(rows), STAGE1_BATCH_SIZE)]
        
        all_s1_results = {}
        s1_log = []
        
        print(f"\nProcessing {len(batches)} Stage 1 batches ({STAGE1_BATCH_SIZE} grants each)...\n")
        
        for batch_idx, batch in enumerate(tqdm(batches, desc="Stage 1")):
            results, raw_text = classify_stage1_batch(client, batch)
            
            s1_log.append({
                "stage": 1,
                "batch": batch_idx,
                "ids": [_safe_str(r.get("unique_key")) for r in batch],
                "raw_response": raw_text,
            })
            
            for r in results:
                gid = str(r.get("grant_id", "")).strip()
                if gid:
                    all_s1_results[gid] = r
            
            time.sleep(SLEEP_S)
            
            # Checkpoint every 10 batches
            if (batch_idx + 1) % 10 == 0:
                apply_stage1_results(df_s1_todo, all_s1_results)
                combined = pd.concat([df_s1_done, df_s1_todo], ignore_index=True)
                combined.to_csv(OUT_STAGE1_ALL, index=False)
                print(f"\n  Checkpoint at batch {batch_idx+1} — saved {OUT_STAGE1_ALL}")
        
        # Final Stage 1 apply
        apply_stage1_results(df_s1_todo, all_s1_results)
        df = pd.concat([df_s1_done, df_s1_todo], ignore_index=True)
        df.to_csv(OUT_STAGE1_ALL, index=False)
    else:
        print("  All grants already classified in Stage 1. Loading existing results.")
        df = pd.read_csv(OUT_STAGE1_ALL)
        s1_log = []
    
    # Stage 1 outputs
    s1_kept = df[df["s1_decision"] == "KEEP"].copy()
    s1_excl = df[df["s1_decision"] == "REMOVE"].copy()
    s1_review = df[df["s1_confidence"] == "low"].copy()
    
    s1_excl.to_csv(OUT_STAGE1_EXCL, index=False)
    s1_review.to_csv(OUT_STAGE1_REVIEW, index=False)
    
    print("\n" + "="*70)
    print("STAGE 1 COMPLETE")
    print("="*70)
    print(f"Total grants:       {len(df)}")
    print(f"KEEP:               {len(s1_kept)}")
    print(f"REMOVE:             {len(s1_excl)}")
    print(f"Low confidence:     {len(s1_review)}  → review manually")
    print()
    
    # ==========================================================================
    # STAGE 2: DEEP CHARACTERIZATION (KEEP only)
    # ==========================================================================
    print("="*70)
    print("STAGE 2: DEEP CHARACTERIZATION (Sonnet)")
    print("="*70)
    print()
    
    # Check for resume
    if RESUME and OUT_STAGE2_CHAR.exists():
        print("  Resuming from existing Stage 2 results...")
        existing = pd.read_csv(OUT_STAGE2_CHAR)
        s2_classified_keys = set(existing[existing["s2_grant_type"].notna()]["unique_key"].astype(str))
        print(f"  Found {len(s2_classified_keys)} already-characterized grants")
    else:
        s2_classified_keys = set()
    
    # Only characterize KEEP grants
    s2_todo_mask = (s1_kept["s1_decision"] == "KEEP") & (~s1_kept["unique_key"].astype(str).isin(s2_classified_keys))
    df_s2_todo = s1_kept[s2_todo_mask].copy().reset_index(drop=True)
    df_s2_done = s1_kept[~s2_todo_mask].copy()
    
    # Test mode - use specific validation grants
    if TEST_MODE:
        print(f"  TEST MODE: selecting validation grants that were KEPT in Stage 1")
        # Filter to only the validation grant IDs that were KEPT
        df_s2_todo = df_s2_todo[df_s2_todo['unique_key'].isin(VALIDATION_GRANT_IDS)].copy().reset_index(drop=True)
        print(f"  Found {len(df_s2_todo)} validation grants to characterize")
        if len(df_s2_todo) == 0:
            print(f"  WARNING: No validation grants in KEEP set!")
            print(f"  Falling back to random sample of {TEST_SAMPLE_SIZE} grants")
            df_s2_todo = s1_kept[s2_todo_mask].sample(n=min(TEST_SAMPLE_SIZE, len(s1_kept[s2_todo_mask])), random_state=42).reset_index(drop=True)
    
    print(f"  Grants needing Stage 2 characterization: {len(df_s2_todo)}")
    
    if len(df_s2_todo) > 0:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        rows = [df_s2_todo.iloc[i] for i in range(len(df_s2_todo))]
        batches = [rows[i:i+STAGE2_BATCH_SIZE] for i in range(0, len(rows), STAGE2_BATCH_SIZE)]
        
        all_s2_results = {}
        s2_log = []
        
        print(f"\nProcessing {len(batches)} Stage 2 batches ({STAGE2_BATCH_SIZE} grants each)...\n")
        
        for batch_idx, batch in enumerate(tqdm(batches, desc="Stage 2")):
            results, raw_text = classify_stage2_batch(client, batch)
            
            s2_log.append({
                "stage": 2,
                "batch": batch_idx,
                "ids": [_safe_str(r.get("unique_key")) for r in batch],
                "raw_response": raw_text,
            })
            
            for r in results:
                gid = str(r.get("grant_id", "")).strip()
                if gid:
                    all_s2_results[gid] = r
            
            time.sleep(SLEEP_S)
            
            # Checkpoint every 10 batches
            if (batch_idx + 1) % 10 == 0:
                apply_stage2_results(df_s2_todo, all_s2_results)
                combined = pd.concat([df_s2_done, df_s2_todo], ignore_index=True)
                combined.to_csv(OUT_STAGE2_CHAR, index=False)
                print(f"\n  Checkpoint at batch {batch_idx+1} — saved {OUT_STAGE2_CHAR}")
        
        # Final Stage 2 apply
        apply_stage2_results(df_s2_todo, all_s2_results)
        df_s2_final = pd.concat([df_s2_done, df_s2_todo], ignore_index=True)
        df_s2_final.to_csv(OUT_STAGE2_CHAR, index=False)
        
        # Combine logs
        full_log = s1_log + s2_log
    else:
        print("  All KEEP grants already characterized in Stage 2. Loading existing results.")
        df_s2_final = pd.read_csv(OUT_STAGE2_CHAR)
        full_log = s1_log
    
    # Stage 2 outputs
    s2_review = df_s2_final[df_s2_final["s2_confidence"] == "low"].copy()
    s2_review.to_csv(OUT_STAGE2_REVIEW, index=False)
    
    # Save log
    with open(OUT_LOG, "w") as f:
        json.dump(full_log, f, indent=2, default=str)
    
    print("\n" + "="*70)
    print("STAGE 2 COMPLETE")
    print("="*70)
    print(f"Total characterized:  {len(df_s2_final)}")
    print(f"Low confidence:       {len(s2_review)}  → review manually")
    print()
    
    # Summary statistics
    print("--- Grant Type ---")
    print(df_s2_final["s2_grant_type"].value_counts(dropna=False).to_string())
    print()
    
    print("--- Orientation ---")
    print(df_s2_final["s2_orientation"].value_counts(dropna=False).to_string())
    print()
    
    print("--- Application Area ---")
    print(df_s2_final["s2_application_area"].value_counts(dropna=False).to_string())
    print()
    
    print("--- Research Stage (research grants only) ---")
    research_grants = df_s2_final[df_s2_final["s2_grant_type"] == "research"]
    if len(research_grants) > 0:
        print(research_grants["s2_research_stage"].value_counts(dropna=False).to_string())
    else:
        print("No research grants")
    print()
    
    print("--- Research Approach (public_facing research only) ---")
    public_research = df_s2_final[(df_s2_final["s2_grant_type"] == "research") & 
                                  (df_s2_final["s2_orientation"] == "public_facing")]
    if len(public_research) > 0:
        print(public_research["s2_research_approach"].value_counts(dropna=False).to_string())
    else:
        print("No public_facing research grants")
    print()
    
    print(f"All outputs saved to: {OUTPUT_DIR}")
    print()
    print("="*70)
    print("TWO-STAGE CLASSIFICATION COMPLETE")
    print("="*70)


def run_stage1_excluded_pools():
    """
    Run Stage 1 KEEP/REMOVE on two pools the main flow skips:
      (1) climate_biotech_insufficient_abstract_all_years.csv  (short abstracts)
      (2) formula grants — reconstructed from merged − excluded set-difference.

    Mirrors biomining's Stage 2-Short / Stage 2-Formula pattern. ONLY runs
    Stage 1 (KEEP/REMOVE) — no Stage 2 characterization — because short-
    abstract and formula grants lack the context for reliable 6-axis tagging.

    Writes two NEW CSVs (stage1_shortabstract_all_years.csv and
    stage1_formula_all_years.csv). Does NOT alter the main Stage 1 / Stage 2
    outputs. Skips each pool if its output file already exists.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _apply(df_in, label, out_path):
        if out_path.exists():
            print(f"✓ {out_path.name} exists — skipping (delete to re-run)")
            return
        if df_in is None or len(df_in) == 0:
            print(f"⚠️  {label}: 0 rows to classify — skipping")
            return
        batches = [df_in.iloc[i:i + STAGE1_BATCH_SIZE].to_dict("records")
                   for i in range(0, len(df_in), STAGE1_BATCH_SIZE)]
        print(f"\n{label}: {len(df_in):,} grants / {len(batches)} batches")
        decisions = {}
        for i, batch in enumerate(batches, 1):
            results, _ = classify_stage1_batch(client, batch)
            for r in results:
                decisions[str(r.get("grant_id", "")).strip()] = r
            if i % 10 == 0 or i == len(batches):
                print(f"  batch {i}/{len(batches)}")
        df_out = df_in.copy()
        for col in ("s1_decision", "s1_confidence", "s1_reasoning"):
            df_out[col] = None
        for idx, row in df_out.iterrows():
            gid = str(row.get("unique_key", "")).strip()
            if gid in decisions:
                r = decisions[gid]
                df_out.at[idx, "s1_decision"] = r.get("decision")
                df_out.at[idx, "s1_confidence"] = r.get("confidence")
                df_out.at[idx, "s1_reasoning"] = r.get("reasoning")
        df_out.to_csv(out_path, index=False)
        print(f"✓ Wrote {out_path}")
        print(f"  KEEP:   {(df_out['s1_decision'] == 'KEEP').sum():,}")
        print(f"  REMOVE: {(df_out['s1_decision'] == 'REMOVE').sum():,}")

    # Pool 1: short-abstract (keyword-matched, < 150 char abstract)
    if INSUFFICIENT_CSV.exists():
        df_short = pd.read_csv(INSUFFICIENT_CSV, low_memory=False)
        _apply(df_short, "Non-Categorizable (short abstract)", OUT_STAGE1_SHORT)
    else:
        print(f"⚠️  {INSUFFICIENT_CSV.name} not found — skipping short-abstract pool")

    # Pool 2: formula grants (keyword-matched, FORMULA GRANT — reconstructed
    # via set-difference since step2 drops them from kept_final without saving).
    if EXCLUDED_CSV.exists() and MERGED_CSV.exists():
        excluded_keys = set()
        for chunk in pd.read_csv(EXCLUDED_CSV, chunksize=200_000, low_memory=False,
                                 usecols=["unique_key", "award_type"]):
            m = chunk["award_type"].fillna("").astype(str).str.startswith("FORMULA GRANT")
            excluded_keys.update(chunk.loc[m, "unique_key"].astype(str).tolist())
        missing_rows = []
        for chunk in pd.read_csv(MERGED_CSV, chunksize=200_000, low_memory=False):
            m = chunk["award_type"].fillna("").astype(str).str.startswith("FORMULA GRANT")
            sub = chunk.loc[m].copy()
            if sub.empty:
                continue
            sub["unique_key"] = sub["unique_key"].astype(str)
            miss = sub[~sub["unique_key"].isin(excluded_keys)]
            if len(miss):
                missing_rows.append(miss)
        df_formula = pd.concat(missing_rows, ignore_index=True) if missing_rows else None
        _apply(df_formula, "Climate Biotech Formula (reconstructed)", OUT_STAGE1_FORMULA)
    else:
        print(f"⚠️  merged_all_years.csv or climate_biotech_excluded_all_years.csv not found — skipping formula pool")


if __name__ == "__main__":
    main()
    # Extension: also Stage-1-classify the two previously-skipped pools so the
    # viz can show LLM-confirmed KEEP/REMOVE counts on Non-Categorizable +
    # Formula branches (ported from biomining's Stage 2-Short / Stage 2-Formula).
    run_stage1_excluded_pools()