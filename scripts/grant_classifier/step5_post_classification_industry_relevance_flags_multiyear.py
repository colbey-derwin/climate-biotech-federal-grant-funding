#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_industry_framing.py

POST-PROCESSING SCRIPT: Add industry_framing column to Stage 2 classified data

Flags public_facing research grants that include industry/commercial viability
analysis (TEA, LCA, etc.) in their abstracts.

Input:  stage2_characterized_all_years.csv
Output: stage2_characterized_all_years_with_industry_framing.csv

Runtime: ~2 minutes
"""

import os
import re
import pandas as pd
from typing import List
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/grant_classifier/
PROJECT_ROOT = SCRIPT_DIR.parent.parent       # climate_biotech_federal_grant_funding/

OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

INFILE = OUTPUT_DIR / "stage2_characterized_all_years.csv"
OUTFILE = OUTPUT_DIR / "stage2_characterized_all_years_with_industry_framing.csv"

# =============================================================================
# INDUSTRY FRAMING KEYWORDS - APPROVED LIST
# =============================================================================
# EXACTLY as specified - 18 keywords total
INDUSTRY_KEYWORDS = [
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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    if pd.isna(text):
        return ""
    # Convert to lowercase, collapse whitespace
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    return text

def has_industry_keyword(abstract: str, keywords: List[str]) -> bool:
    """
    Check if abstract contains any industry framing keyword.
    Case-insensitive matching with word boundaries.
    """
    if pd.isna(abstract):
        return False
    
    normalized = normalize_text(abstract)
    
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        
        # Use word boundaries to prevent matching within words
        # \b matches word boundaries (transition between \w and \W)
        pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
        
        if re.search(pattern, normalized):
            return True
    
    return False

def assign_industry_framing(row: pd.Series, keywords: List[str]) -> bool:
    """
    Assign industry_framing flag based on grant type, orientation, and keywords.
    
    Logic (UPDATED - FORCE 100%):
    - Deployment: ALWAYS True (inherently industry/commercial work)
    - Industry-facing research: ALWAYS True (inherently industry-oriented)
    - Public-facing research: Check abstract for keywords → True/False
    - Infrastructure: Check abstract for keywords → True/False
    - Other: Return None (not applicable)
    """
    grant_type = row.get('s2_grant_type', None)
    orientation = row.get('s2_orientation', None)
    abstract = row.get('abstract', '')
    
    # FORCE: Deployment is ALWAYS industry-informed (it's deploying technology!)
    if grant_type == 'deployment':
        return True
    
    # FORCE: Industry-facing research is ALWAYS industry-informed (that's what industry-facing means!)
    elif grant_type == 'research' and orientation == 'industry_facing':
        return True
    
    # Apply keyword matching to public-facing research
    elif grant_type == 'research' and orientation == 'public_facing':
        return has_industry_keyword(abstract, keywords)
    
    # Apply keyword matching to infrastructure
    elif grant_type == 'infrastructure':
        return has_industry_keyword(abstract, keywords)
    
    # Not applicable to other grant types
    else:
        return None

# =============================================================================
# MAIN PROCESSING
# =============================================================================

def main():
    print("="*80)
    print("ADD INDUSTRY FRAMING TO STAGE 2 DATA")
    print("="*80)
    print()
    
    # Load data
    print(f"Loading: {INFILE}")
    df = pd.read_csv(INFILE, low_memory=False)
    print(f"✓ Loaded {len(df):,} grants")
    print()
    
    # Check required columns
    required_cols = ['s2_grant_type', 's2_orientation', 'abstract']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"❌ ERROR: Missing required columns: {missing}")
        return
    
    # Display keyword list
    print("Industry Framing Keywords (18 total):")
    print("-"*80)
    for i, keyword in enumerate(INDUSTRY_KEYWORDS, 1):
        print(f"  {i:2d}. {keyword}")
    print()
    
    # Count target population
    research_grants = df[df['s2_grant_type'] == 'research']
    public_research = research_grants[research_grants['s2_orientation'] == 'public_facing']
    industry_research = research_grants[research_grants['s2_orientation'] == 'industry_facing']
    infrastructure_grants = df[df['s2_grant_type'] == 'infrastructure']
    deployment_grants = df[df['s2_grant_type'] == 'deployment']
    
    total_applicable = len(public_research) + len(industry_research) + len(infrastructure_grants) + len(deployment_grants)
    
    print("Target Population:")
    print(f"  Total grants:              {len(df):,}")
    print(f"  Public-facing research:    {len(public_research):,}")
    print(f"  Industry-facing research:  {len(industry_research):,}")
    print(f"  Infrastructure:            {len(infrastructure_grants):,}")
    print(f"  Deployment:                {len(deployment_grants):,}")
    print(f"  ───────────────────────────────────")
    print(f"  Total applicable:          {total_applicable:,}")
    print()
    
    # Apply industry framing logic
    print("Processing grants...")
    df['industry_framing'] = df.apply(
        lambda row: assign_industry_framing(row, INDUSTRY_KEYWORDS), 
        axis=1
    )
    
    # Summary statistics
    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    print()
    
    # Count by category
    flagged = df[df['industry_framing'] == True]
    not_flagged = df[df['industry_framing'] == False]
    not_applicable = df[df['industry_framing'].isna()]
    
    print(f"Industry Framing = True:  {len(flagged):,} grants")
    print(f"Industry Framing = False: {len(not_flagged):,} grants")
    print(f"Not Applicable (null):    {len(not_applicable):,} grants")
    print()
    
    # Percentage of applicable grants with industry framing
    if total_applicable > 0:
        pct_with_framing = (len(flagged) / total_applicable) * 100
        print(f"% of Applicable Grants with Industry Framing: {pct_with_framing:.1f}%")
        print()
    
    # Breakdown by grant type (if available)
    if len(flagged) > 0:
        print("Breakdown by Grant Type:")
        print("-"*80)
        
        # Use df instead of public_research since df has the industry_framing column
        for grant_type in ['research', 'infrastructure', 'deployment', 'other']:
            type_grants = df[df['s2_grant_type'] == grant_type]
            if len(type_grants) > 0:
                type_flagged = type_grants[type_grants['industry_framing'] == True]
                if len(type_flagged) > 0:
                    pct = (len(type_flagged) / len(type_grants)) * 100
                    print(f"  {grant_type:20s}: {len(type_flagged):4d}/{len(type_grants):4d} ({pct:5.1f}%)")
        print()
        
        # For research, break down by orientation
        research_flagged = df[(df['s2_grant_type'] == 'research') & (df['industry_framing'] == True)]
        if len(research_flagged) > 0:
            print("Research Breakdown by Orientation:")
            print("-"*80)
            
            public_flagged = research_flagged[research_flagged['s2_orientation'] == 'public_facing']
            industry_flagged = research_flagged[research_flagged['s2_orientation'] == 'industry_facing']
            
            if len(public_flagged) > 0:
                pct = (len(public_flagged) / len(public_research)) * 100 if len(public_research) > 0 else 0
                print(f"  Public-facing:   {len(public_flagged):4d}/{len(public_research):4d} ({pct:5.1f}%)")
            
            if len(industry_flagged) > 0:
                pct = (len(industry_flagged) / len(industry_research)) * 100 if len(industry_research) > 0 else 0
                print(f"  Industry-facing: {len(industry_flagged):4d}/{len(industry_research):4d} ({pct:5.1f}%)")
            print()
    
    # Show example flagged grants
    if len(flagged) > 0:
        print("Example Flagged Grants (first 3):")
        print("-"*80)
        for idx, row in flagged.head(3).iterrows():
            print(f"Title: {row.get('title', 'N/A')[:100]}")
            print(f"Stage: {row.get('s2_research_stage', 'N/A')}")
            
            # Find which keyword(s) matched
            abstract = normalize_text(row.get('abstract', ''))
            matched = []
            for keyword in INDUSTRY_KEYWORDS:
                if normalize_text(keyword) in abstract:
                    matched.append(keyword)
            print(f"Keywords: {', '.join(matched[:3])}")  # Show first 3 matches
            print()
    
    # Save output
    print("="*80)
    print("SAVING OUTPUT")
    print("="*80)
    print()
    
    df.to_csv(OUTFILE, index=False)
    print(f"✓ Saved: {OUTFILE}")
    print(f"  Total rows: {len(df):,}")
    print(f"  New column: industry_framing (bool/null)")
    print()
    
    # Verification
    print("Verification:")
    print(f"  Original file:  {len(pd.read_csv(INFILE)):,} rows")
    print(f"  New file:       {len(df):,} rows")
    print(f"  Match:          {'✓ YES' if len(pd.read_csv(INFILE)) == len(df) else '❌ NO'}")
    print()
    
    print("="*80)
    print("COMPLETE")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Review the flagged grants to verify keyword matching is working")
    print("  2. Use this file for visualization: stage2_characterized_all_years_with_industry_framing.csv")
    print()

if __name__ == "__main__":
    main()
