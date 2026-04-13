#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
climate_biotech_filter_phase1_v2.py

EXPANDED DEFINITION (2025):
Climate biotech = Using biological mechanisms to address the climate crisis and restore planetary health

Biology is central to both the causes and solutions of our climate problems:
- Fossil resources originate from organisms
- Carbon cycling is dominated by biological processes
- Soil health, food systems, and ecosystems are intrinsically biological

This filter captures biotechnology applied to:
- Climate/Carbon: GHG reduction, carbon capture, biofuels (fossil fuel replacement)
- Pollution/Remediation: Cleaning contamination, heavy metals, toxics
- Waste: Converting waste to resources, wastewater treatment
- Regeneration: Restoring ecosystems, building soil health, sustainable agriculture
- Bio-based Economy: Replacing fossil-based materials/chemicals with bio-based alternatives

CORE LOGIC: We need BOTH climate/environmental relevance AND biological approach.
This is an intersection filter, not a union.

KEEP if: CLIMATE/ENVIRONMENTAL evidence × BIO evidence × NOT excluded

Climate/Environmental evidence = terms indicating planetary health/climate solutions
Bio evidence = terms indicating biological/biotech approach
Exclusion = pure CS, pure medical, pure ecology with no industrial/solution tie

"""

import os
import re
import pandas as pd

# =========================
# PATHS - CONFIGURATION
# =========================
# This script runs AFTER merge_master_2019.py
# It takes the merged CSV as input and filters for climate biotech

from pathlib import Path

# Get the project root directory
# Assuming script is in scripts/ or scripts/single_year_grant_classifier/
SCRIPT_DIR = Path(__file__).resolve().parent
# Adjust based on actual location - if in scripts/, use .parent once
# If in scripts/single_year_grant_classifier/, use .parent.parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Adjust if needed

# Input/Output directories
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Input file (from merge_master_2019.py output)
INFILE = OUTPUT_DIR / "merged_2019.csv"

# Output files
OUT_KEPT = OUTPUT_DIR / "climate_biotech_filtered.csv"
OUT_EXCL = OUTPUT_DIR / "climate_biotech_excluded.csv"

# =========================
# SETTINGS
# =========================
# Higher thresholds = more permissive = fewer exclusions
# Let LLM classification handle edge cases in Phase 2
BIOMED_EXCLUDE_THRESHOLD = 3  # Raised from 3
PURE_CS_EXCLUDE_THRESHOLD = 3  # Raised from 3
PURE_ECOLOGY_EXCLUDE_THRESHOLD = 5  # Raised from 3 - keep ecology with industrial context

# =========================
# CLIMATE & ENVIRONMENTAL EVIDENCE TERMS (EXPANDED DEFINITION)
# =========================
# These indicate the grant is addressing climate/planetary health problems
# Biology is central to both causes and solutions
# But they still need BIO evidence to be kept

CLIMATE_SECTORS = {
    # Energy & Electricity
    "renewable energy", "clean energy", "solar energy", "wind energy",
    "energy storage", "battery storage", "grid storage",
    "geothermal", "carbon-free energy",
    
    # Carbon Management
    "carbon capture", "carbon sequestration", "carbon removal",
    "direct air capture", "co2 capture", "co2 removal",
    "carbon utilization", "co2 utilization", "ccus",
    "carbon dioxide reduction", "carbon negative",
    "carbon cycle", "carbon emission", "co2 emission",
    "atmospheric co2", "atmospheric carbon",
    
    # Manufacturing & Industry
    "industrial decarbonization", "industrial emissions", "industrial emission",
    "green hydrogen", "hydrogen production", "clean hydrogen",
    "sustainable aviation fuel", "saf", "e-fuel",
    "low-carbon cement", "green cement", "clean steel",
    "circular economy", "industrial sustainability",
    
    # Agriculture & Food
    "agricultural emissions", "agricultural emission", "enteric methane", "livestock emissions", "livestock emission",
    "nitrous oxide", "n2o emissions", "n2o emission", "fertilizer emissions", "fertilizer emission",
    "sustainable agriculture", "climate-smart agriculture",
    "alternative protein", "cultivated meat", "precision fermentation protein",
    "food system emissions", "food system emission", "agricultural sustainability",
    
    # Transportation
    "electric vehicle", "ev battery", "vehicle electrification",
    "transportation emissions", "transportation emission", "mobility decarbonization",
    "shipping emissions", "shipping emission", "maritime fuel",
    
    # Buildings & Materials
    "building decarbonization", "building emissions", "building emission",
    "low-carbon materials", "sustainable materials",
    "construction emissions", "construction emission",
    
    # General Climate
    "climate change mitigation", "climate mitigation", "climate change",
    "greenhouse gas reduction", "greenhouse gas", "ghg reduction", "ghg", 
    "emissions reduction", "emission reduction",
    "decarbonization", "net zero", "carbon neutral",
    "climate tech", "climate technology", "climate solution",
    "sustainable energy", "clean energy", "renewable energy",
    
    # Environmental Remediation & Pollution Cleanup
    "environmental remediation", "pollution remediation", "contamination cleanup",
    "heavy metal removal", "toxic waste", "soil remediation", "groundwater cleanup",
    "wastewater treatment", "water treatment", "industrial effluent",
    "waste valorization", "waste conversion", "organic waste", "landfill gas",
    "ecosystem restoration", "habitat restoration", "mine reclamation",
    "pollutant removal", "contaminant removal", "environmental cleanup",
    
    # Ocean & Marine
    "ocean acidification", "blue carbon",
    "coastal ecosystem restoration", "marine carbon sequestration",
    
    # Forestry & Land Use
    "deforestation", "reforestation", "afforestation",
    "forest carbon", "soil carbon", "land degradation",
    
    # Mining & Extractives
    "acid mine drainage", "mine waste", "tailings",
    "mine site remediation",
    
    # Plastics & Waste
    "plastic pollution", "microplastic", "plastic degradation",
    
    # Water Resources
    "water pollution", "water quality",
}
# ========================="

# =========================
# BIO EVIDENCE TERMS
# =========================
# These indicate the grant uses biological/biotech approaches
# But they still need CLIMATE evidence to be kept

BIO_APPROACHES = {
    # Genetic Engineering & Synthetic Biology
    "synthetic biology", "metabolic engineering", "genetic engineering",
    "crispr", "gene editing", "genome editing", "genome engineering",
    "directed evolution", "protein engineering", "enzyme engineering",
    "genetic modification", "genetically modified", "transgenic",
    "gene expression", "gene regulation",
    
    # Microbial & Fermentation
    "microbial", "microbe", "microorganism",
    "bacteria", "bacterial", "bacterium",
    "microbial production", "microbial synthesis", "bacterial production",
    "yeast fermentation", "fungal", "algal cultivation",
    "fungi",
    "fermentation", "bioprocess", "bioreactor", "cell culture",
    "microbial strain", "bacterial strain", "engineered strain", "production strain",
    "cell factory", "microbial factory",
    
    # Enzymatic & Biocatalysis
    "enzymatic", "enzyme",
    "biocatalyst", "biocatalysis", "biocatalytic",
    "enzymatic conversion", "enzymatic synthesis", "enzyme-catalyzed",
    
    # Biomass & Feedstocks
    "biomass conversion", "lignocellulosic", "cellulosic",
    "lignocellulosic biomass", "cellulosic biomass",
    "feedstock", "biological feedstock", "waste biomass",
    "agricultural waste", "crop residue",
    
    # Photosynthesis & Biological Systems
    "photosynthetic", "photosynthesis", "photoautotroph",
    "cyanobacteria", "cyanobacterial", "microalgae", "algae", "algal",
    
    # Biotech Products & Processes
    "biofuel", "bioethanol", "biodiesel", "biogas", "biomethane",
    "bioplastic", "biopolymer", "biomaterial",
    "biochemical", "biosynthetic", "biosynthesis",
    "biomanufacturing", "bio-based production",
    
    # Organism Engineering
    "engineered organism", "engineered microbe", "engineered bacteria",
    "designer organism", "chassis organism",
    
    # Degradation & Treatment
    "biodegradation", "biodegradable", "biological degradation",
    "biological treatment",
    
    # Fungal Systems
    "mycelium",
    
    # Marine Biology
    "seaweed", "kelp", "macroalgae",
    
    # Soil Biology
    "soil microbe", "rhizosphere",
}

# =========================
# STANDALONE AUTO-KEEP QUERIES
# =========================
# These queries are SO SPECIFIC to climate biotech that they auto-qualify
# They implicitly contain both climate AND bio evidence
STANDALONE_KEEP = {
    # Biofuels
    "biofuel", "biofuels", "bioethanol", "biodiesel", "biogas", "biomethane",
    "algal fuel", "algal fuels",
    "cellulosic ethanol",
    "advanced biofuel", "advanced biofuels",
    "sustainable aviation fuel", "sustainable aviation fuels", "biojet fuel", "biojet fuels", "saf",
    "biomass-to-liquid", "btl",
    
    # Carbon Capture
    "carbon fixation", "biological carbon capture", "microbial carbon capture",
    "algal carbon capture",
    
    # Agricultural Emissions
    "enteric methane reduction", "methane-reducing",
    
    # Remediation
    "phytoremediation", "bioremediation", "bioaugmentation",
    "mycoremediation", "biosorption",
    "phytomining", "constructed wetland", "constructed wetlands",
    
    # Mining & Metals
    "biomining", "bioleaching", "biooxidation", "biohydrometallurgy",
    
    # Biorefining & Manufacturing
    "biorefinery", "biorefineries", "biorefining",
    "biomanufacturing",
    
    # Bio-based Products
    "bio-based chemical", "bio-based chemicals",
    "biosurfactant", "biosurfactants",
    "bioplastic", "bioplastics",
    "biopolymer", "biopolymers",
    "bio-based material", "bio-based materials",
    "biolubricant", "biolubricants",
    
    # Textiles & Fashion
    "bio-textile", "bio-textiles",
    "microbial leather", "mycelium leather",
    "bio-based fiber", "bio-based fibers",
    
    # Construction & Building
    "bio-cement", "biocement",
    "bio-concrete", "bioconcrete",
    "mycelium insulation",
    
    # Chemicals & Solvents
    "bio-solvent", "bio-solvents",
    "bio-adhesive", "bio-adhesives",
    "bio-coating", "bio-coatings",
    
    # Packaging
    "bio-packaging",
    
    # Agriculture Inputs
    "biofertilizer", "biofertilizers",
    "biopesticide", "biopesticides",
    "biostimulant", "biostimulants",
    
    # Energy Storage
    "bio-battery", "bio-batteries",
    
    # Waste-to-Value
    "waste-to-biofuel", "waste-to-biofuels",
    "anaerobic digestion",
    
    # Soil/Agriculture
    "biochar",
    
    # Bio-energy
    "microbial fuel cell", "microbial fuel cells",
    "biohydrogen", "bioelectricity",
}

# =========================
# EXCLUSIONS
# =========================
# These override even if climate × bio is present

PURE_BIOMEDICAL = [
    "clinical trial", "clinical study", "patient", "patients",
    "hospital", "healthcare", "health care",
    "cancer therapy", "cancer treatment", "tumor",
    "drug development", "drug delivery", "pharmaceutical",
    "disease mechanism", "disease pathway", "pathogenesis",
    "therapeutic", "therapy", "treatment",
    "vaccine", "antibody", "immunotherapy",
    "diagnosis", "diagnostic",
]

PURE_COMPUTER_SCIENCE = [
    "machine learning", "deep learning", "neural network",
    "artificial intelligence", "computer vision",
    "data mining", "text mining", "web mining",
    "natural language processing", "nlp",
    "software engineering", "algorithm development",
    "database", "data structure",
]

PURE_ECOLOGY_NO_INDUSTRIAL = [
    "biodiversity conservation", "species conservation",
    "wildlife conservation", "habitat conservation",
    "ecosystem services", "ecological services",
    "population ecology", "community ecology",
    "food web", "trophic",
    "species diversity", "species richness",
    "conservation biology", "restoration ecology",
]

# =========================
# HELPERS
# =========================
def _norm(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def _build_phrase_regex(phrases):
    parts = []
    for p in phrases:
        p = p.strip().lower()
        esc = re.escape(p)
        esc = esc.replace(r"\ ", r"[\s\-]+")
        parts.append(esc)
    return re.compile(r"\b(" + "|".join(parts) + r")\b", flags=re.IGNORECASE)

def _count_phrase_matches(phrases, text: str) -> int:
    if not isinstance(text, str) or not text:
        return 0
    t = text.lower()
    hits = 0
    for p in phrases:
        p2 = p.strip().lower()
        if not p2:
            continue
        esc = re.escape(p2).replace(r"\ ", r"[\s\-]+")
        rx = re.compile(r"\b" + esc + r"\b", flags=re.IGNORECASE)
        if rx.search(t):
            hits += 1
    return hits

# Build regex patterns
RX_CLIMATE = _build_phrase_regex(CLIMATE_SECTORS)
RX_BIO = _build_phrase_regex(BIO_APPROACHES)

# =========================
# FILTER LOGIC
# =========================
def apply_climate_biotech_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    CORE LOGIC: CLIMATE × BIO = KEEP
    
    KEEP if:
    1. Standalone auto-keep query (implicitly has both), OR
    2. Has climate evidence AND has bio evidence AND not excluded
    
    EXCLUDE if:
    - Hits exclusion threshold (biomedical, CS, or pure ecology)
    """
    df = df.copy()
    
    # Ensure required columns exist
    for c in ["title", "abstract"]:
        if c not in df.columns:
            df[c] = pd.NA
    
    # Build text blob (include POR text if available for NSF grants)
    if "por_text" in df.columns:
        df["text_blob"] = (
            df["title"].fillna("").astype(str) + " | " +
            df["abstract"].fillna("").astype(str) + " | " +
            df["por_text"].fillna("").astype(str)
        ).map(_norm)
    else:
        df["text_blob"] = (
            df["title"].fillna("").astype(str) + " | " +
            df["abstract"].fillna("").astype(str)
        ).map(_norm)
    
    # Note: Merged data doesn't have query_used field
    # Standalone terms are detected in title/abstract/por_text directly
    # Use word boundaries to ensure exact matches
    standalone_pattern = r'\b(' + '|'.join(re.escape(term) for term in STANDALONE_KEEP) + r')\b'
    standalone_regex = re.compile(standalone_pattern, re.IGNORECASE)
    
    df["standalone_keep"] = df["text_blob"].apply(
        lambda s: bool(standalone_regex.search(s))
    )
    
    # Check for CLIMATE evidence
    df["has_climate"] = df["text_blob"].apply(lambda s: bool(RX_CLIMATE.search(s)))
    
    # Check for BIO evidence
    df["has_bio"] = df["text_blob"].apply(lambda s: bool(RX_BIO.search(s)))
    
    # Exclusion counts
    df["biomed_count"] = df["text_blob"].apply(
        lambda s: _count_phrase_matches(PURE_BIOMEDICAL, s)
    )
    df["cs_count"] = df["text_blob"].apply(
        lambda s: _count_phrase_matches(PURE_COMPUTER_SCIENCE, s)
    )
    df["ecology_count"] = df["text_blob"].apply(
        lambda s: _count_phrase_matches(PURE_ECOLOGY_NO_INDUSTRIAL, s)
    )
    
    df["excluded_biomed"] = df["biomed_count"] >= BIOMED_EXCLUDE_THRESHOLD
    df["excluded_cs"] = df["cs_count"] >= PURE_CS_EXCLUDE_THRESHOLD
    df["excluded_ecology"] = df["ecology_count"] >= PURE_ECOLOGY_EXCLUDE_THRESHOLD
    
    # Any exclusion flag
    df["excluded_any"] = df["excluded_biomed"] | df["excluded_cs"] | df["excluded_ecology"]
    
    # CORE DECISION: CLIMATE × BIO
    df["keep_climate_biotech"] = (
        df["standalone_keep"] |
        (df["has_climate"] & df["has_bio"] & (~df["excluded_any"]))
    )
    
    # Reason tracking
    def _reason(row):
        if row["keep_climate_biotech"]:
            if row["standalone_keep"]:
                return "kept_standalone"
            elif row["has_climate"] and row["has_bio"]:
                return "kept_climate_x_bio"
            else:
                return "kept_other"
        
        # Exclusions
        if row["excluded_biomed"]:
            return "excluded_biomedical"
        if row["excluded_cs"]:
            return "excluded_computer_science"
        if row["excluded_ecology"]:
            return "excluded_pure_ecology"
        
        # Missing evidence
        if row["has_climate"] and not row["has_bio"]:
            return "excluded_climate_no_bio"
        if row["has_bio"] and not row["has_climate"]:
            return "excluded_bio_no_climate"
        if not row["has_climate"] and not row["has_bio"]:
            return "excluded_no_evidence"
        
        return "excluded_other"
    
    df["filter_reason"] = df.apply(_reason, axis=1)
    
    return df

# =========================
# SECTOR PREVIEW (for kept grants only)
# =========================
def assign_sector_preview(df: pd.DataFrame) -> pd.DataFrame:
    """
    For KEPT grants, hint at which climate sector they might belong to.
    These are just breadcrumbs for the LLM, not final classifications.
    """
    df = df.copy()
    
    # Only assign previews to kept grants
    kept_mask = df["keep_climate_biotech"]
    
    df.loc[kept_mask, "preview_energy"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(solar|wind|geothermal|energy storage|battery|renewable energy|grid)\b",
        case=False, regex=True
    )
    
    df.loc[kept_mask, "preview_carbon_mgmt"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(carbon capture|carbon sequestration|co2 capture|direct air capture|ccus)\b",
        case=False, regex=True
    )
    
    df.loc[kept_mask, "preview_manufacturing"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(hydrogen|steel|cement|industrial|chemical production|sustainable fuel)\b",
        case=False, regex=True
    )
    
    df.loc[kept_mask, "preview_agriculture"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(agriculture|fertilizer|nitrogen|methane|livestock|crop|protein|food)\b",
        case=False, regex=True
    )
    
    df.loc[kept_mask, "preview_fuels"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(biofuel|bioethanol|biodiesel|aviation fuel|sustainable fuel|e-fuel)\b",
        case=False, regex=True
    )
    
    df.loc[kept_mask, "preview_materials"] = df.loc[kept_mask, "text_blob"].str.contains(
        r"\b(bioplastic|biomaterial|low-carbon material|sustainable material|biopolymer)\b",
        case=False, regex=True
    )
    
    return df

# =========================
# MAIN
# =========================
def main():
    print(f"Loading: {INFILE}")
    df = pd.read_csv(INFILE, low_memory=False)
    print(f"  {len(df)} rows loaded")
    
    print("\nApplying CLIMATE × BIO filter...")
    out = apply_climate_biotech_filter(df)
    
    print("Assigning sector previews...")
    out = assign_sector_preview(out)
    
    # Split kept vs excluded
    kept_raw = out.loc[out["keep_climate_biotech"]].copy()
    excl = out.loc[~out["keep_climate_biotech"]].copy()
    
    # ==============================================================================
    # FORMULA GRANT REMOVAL
    # ==============================================================================
    # Remove "FORMULA GRANT (A)" type grants from kept
    # These are capacity-building/extension grants, not competitive research
    
    kept_raw["is_formula_grant"] = (
        kept_raw.get("award_type", pd.Series(dtype=str)).fillna("").astype(str) == "FORMULA GRANT (A)"
    )
    
    n_formula = kept_raw["is_formula_grant"].sum()
    amt_formula = kept_raw.loc[kept_raw["is_formula_grant"], "award_amount"].sum() if n_formula > 0 else 0
    
    formula_grants = kept_raw[kept_raw["is_formula_grant"] == True].copy()
    kept = kept_raw[kept_raw["is_formula_grant"] == False].copy()
    
    print(f"\n--- Formula Grant Removal ---")
    print(f"Formula grants found in kept data: {n_formula} (${amt_formula:,.0f})")
    print(f"Formula grants removed from final kept dataset")
    print(f"Final kept grants (after formula removal): {len(kept)}")
    
    # ==============================================================================
    # ABSTRACT LENGTH FILTER
    # ==============================================================================
    # Remove grants with insufficient abstract length (can't classify without context)
    # Apply BEFORE LLM classification to save costs
    
    kept["abstract_length"] = kept["abstract"].fillna("").astype(str).str.len()
    kept["sufficient_abstract"] = kept["abstract_length"] >= 150  # 150 character minimum
    
    insufficient_abstract = kept[~kept["sufficient_abstract"]].copy()
    kept_final = kept[kept["sufficient_abstract"]].copy()
    
    print(f"\n--- Abstract Length Filter ---")
    print(f"Grants with sufficient abstract (≥150 chars): {len(kept_final)}")
    print(f"Grants with insufficient abstract (<150 chars): {len(insufficient_abstract)}")
    print(f"  (Excluded from LLM classification - insufficient context)")
    
    # Save outputs
    kept_final.to_csv(OUT_KEPT, index=False)
    excl.to_csv(OUT_EXCL, index=False)
    
    # Optionally save insufficient abstracts separately for review
    if len(insufficient_abstract) > 0:
        insufficient_path = OUTPUT_DIR / "climate_biotech_insufficient_abstract.csv"
        insufficient_abstract.to_csv(insufficient_path, index=False)
        print(f"  Saved insufficient abstracts: {insufficient_path}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("FILTERING COMPLETE")
    print("="*70)
    print(f"Input rows: {len(df):,}")
    print(f"Kept rows (CLIMATE × BIO): {len(kept_final):,}")
    print(f"Excluded rows: {len(excl):,}")
    print(f"Insufficient abstract: {len(insufficient_abstract):,}")
    print(f"\nSaved kept: {OUT_KEPT}")
    print(f"Saved excluded: {OUT_EXCL}")
    
    print("\n--- Keep reasons ---")
    if len(kept_final) > 0:
        print(kept_final["filter_reason"].value_counts(dropna=False))
    
    print("\n--- Exclusion reasons (top 15) ---")
    if len(excl) > 0:
        print(excl["filter_reason"].value_counts(dropna=False).head(15))
    
    print("\n--- Evidence analysis (all grants) ---")
    print(f"Has climate evidence: {out['has_climate'].sum():,} ({out['has_climate'].sum()/len(out)*100:.1f}%)")
    print(f"Has bio evidence: {out['has_bio'].sum():,} ({out['has_bio'].sum()/len(out)*100:.1f}%)")
    print(f"Has BOTH (climate × bio): {(out['has_climate'] & out['has_bio']).sum():,}")
    print(f"Climate YES, Bio NO: {(out['has_climate'] & ~out['has_bio']).sum():,}")
    print(f"Climate NO, Bio YES: {(~out['has_climate'] & out['has_bio']).sum():,}")
    print(f"Neither: {(~out['has_climate'] & ~out['has_bio']).sum():,}")
    
    if len(kept_final) > 0:
        print("\n--- Sector preview distribution (kept grants) ---")
        print(f"Energy: {kept_final['preview_energy'].sum()}")
        print(f"Carbon Management: {kept_final['preview_carbon_mgmt'].sum()}")
        print(f"Manufacturing: {kept_final['preview_manufacturing'].sum()}")
        print(f"Agriculture: {kept_final['preview_agriculture'].sum()}")
        print(f"Fuels: {kept_final['preview_fuels'].sum()}")
        print(f"Materials: {kept_final['preview_materials'].sum()}")

if __name__ == "__main__":
    main()
