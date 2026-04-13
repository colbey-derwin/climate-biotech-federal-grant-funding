#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_insufficient_abstracts_multiyear.py

Analyze grants with INSUFFICIENT ABSTRACTS (<150 characters) by funding agency.
Shows which agencies had climate biotech grants excluded due to short abstracts.
Compares to total kept grants to show % of climate biotech removed.

Processes ALL YEARS (2019-2025) from combined datasets.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
# =========================
# PATHS
# =========================

## Get the project root directory
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/
PROJECT_ROOT = SCRIPT_DIR.parent               # climate_biotech_federal_grant_funding/

# Input/Output directories
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

KEPT_FILE = OUTPUT_DIR / "climate_biotech_filtered_all_years.csv"
INSUFFICIENT_FILE = OUTPUT_DIR / "climate_biotech_insufficient_abstract_all_years.csv"

print("="*70)
print("INSUFFICIENT ABSTRACT ANALYSIS BY AGENCY (ALL YEARS)")
print("Grants that passed climate × bio filter but have <150 char abstracts")
print("="*70)

print("\nLoading data...")

# Load kept grants (final - with sufficient abstracts)
try:
    kept = pd.read_csv(KEPT_FILE, low_memory=False)
    print(f"Loaded {len(kept):,} kept grants (sufficient abstracts)")
except FileNotFoundError:
    print(f"\n⚠️  File not found: {KEPT_FILE}")
    print("Run the filter script first to generate this file.")
    exit(1)

# Load insufficient abstract grants
try:
    insuf = pd.read_csv(INSUFFICIENT_FILE, low_memory=False)
    print(f"Loaded {len(insuf):,} grants with insufficient abstracts")
except FileNotFoundError:
    print(f"\n⚠️  File not found: {INSUFFICIENT_FILE}")
    print("Run the filter script first to generate this file.")
    exit(1)

# Determine agency column name
agency_col = None
if 'funder' in insuf.columns:
    agency_col = 'funder'
elif 'funding_agency' in insuf.columns:
    agency_col = 'funding_agency'
elif 'awarding_agency' in insuf.columns:
    agency_col = 'awarding_agency'
else:
    print("\n⚠️  Cannot find agency column!")
    print("Available columns:", insuf.columns.tolist()[:20])
    exit(1)

print(f"Using agency column: '{agency_col}'")

# Determine amount column
amount_col = None
if 'award_amount' in insuf.columns:
    amount_col = 'award_amount'
elif 'amount' in insuf.columns:
    amount_col = 'amount'
else:
    print("\n⚠️  Cannot find amount column!")
    exit(1)

print(f"Using amount column: '{amount_col}'")

# =========================
# OVERALL STATISTICS
# =========================
print("\n" + "="*70)
print("OVERALL STATISTICS (ALL YEARS)")
print("="*70)

# Total climate biotech (kept + insufficient)
total_climate_biotech = len(kept) + len(insuf)
total_climate_biotech_funding = kept[amount_col].sum() + insuf[amount_col].sum()

total_funding = insuf[amount_col].sum()
avg_abstract_len = insuf['abstract_length'].mean() if 'abstract_length' in insuf.columns else 0

print(f"\nTOTAL CLIMATE BIOTECH GRANTS (post-formula removal):")
print(f"  {total_climate_biotech:,} grants")
print(f"  ${total_climate_biotech_funding:,.0f}")

print(f"\nKept (sufficient abstracts ≥150 chars):")
print(f"  {len(kept):,} grants ({len(kept)/total_climate_biotech*100:.1f}%)")
print(f"  ${kept[amount_col].sum():,.0f} ({kept[amount_col].sum()/total_climate_biotech_funding*100:.1f}%)")

print(f"\nRemoved (insufficient abstracts <150 chars):")
print(f"  {len(insuf):,} grants ({len(insuf)/total_climate_biotech*100:.1f}%)")
print(f"  ${total_funding:,.0f} ({total_funding/total_climate_biotech_funding*100:.1f}%)")
print(f"  Average abstract length: {avg_abstract_len:.1f} characters")

print(f"\n📊 IMPACT: {len(insuf)/total_climate_biotech*100:.1f}% of climate biotech grants")
print(f"           {total_funding/total_climate_biotech_funding*100:.1f}% of climate biotech funding")
print(f"           REMOVED due to insufficient abstract length")

if 'abstract_length' in insuf.columns:
    print("\nAbstract length distribution (insufficient):")
    print(f"  0 chars (missing): {(insuf['abstract_length'] == 0).sum():,}")
    print(f"  1-30 chars: {((insuf['abstract_length'] > 0) & (insuf['abstract_length'] <= 30)).sum():,}")
    print(f"  31-60 chars: {((insuf['abstract_length'] > 30) & (insuf['abstract_length'] <= 60)).sum():,}")
    print(f"  61-89 chars: {((insuf['abstract_length'] > 60) & (insuf['abstract_length'] < 90)).sum():,}")
    print(f"  90-149 chars: {((insuf['abstract_length'] >= 90) & (insuf['abstract_length'] < 150)).sum():,}")

# =========================
# BY YEAR
# =========================
if 'year' in insuf.columns and 'year' in kept.columns:
    print("\n" + "="*70)
    print("INSUFFICIENT ABSTRACTS BY YEAR")
    print("="*70)
    
    year_insuf = insuf.groupby('year').agg({
        'award_id': 'count',
        amount_col: 'sum'
    }).rename(columns={'award_id': 'insuf_count', amount_col: 'insuf_funding'})
    
    year_kept = kept.groupby('year').agg({
        'award_id': 'count',
        amount_col: 'sum'
    }).rename(columns={'award_id': 'kept_count', amount_col: 'kept_funding'})
    
    year_comparison = year_insuf.join(year_kept, how='outer').fillna(0)
    year_comparison['total_count'] = year_comparison['insuf_count'] + year_comparison['kept_count']
    year_comparison['total_funding'] = year_comparison['insuf_funding'] + year_comparison['kept_funding']
    year_comparison['pct_insuf'] = (year_comparison['insuf_count'] / year_comparison['total_count'] * 100)
    
    print(f"\n{'Year':<6} {'Kept':>8} {'Insuf':>8} {'Total':>8} {'% Insuf':>9}")
    print("-"*45)
    for year, row in year_comparison.iterrows():
        print(f"{int(year):<6} {int(row['kept_count']):>8,} {int(row['insuf_count']):>8,} "
              f"{int(row['total_count']):>8,} {row['pct_insuf']:>8.1f}%")

# =========================
# BY AGENCY
# =========================
print("\n" + "="*70)
print("INSUFFICIENT ABSTRACTS BY AGENCY")
print("Compared to each agency's total kept climate biotech grants")
print("="*70)

# Get kept funding by agency for comparison
kept_by_agency = kept.groupby(agency_col).agg({
    'award_id': 'count',
    amount_col: 'sum'
}).rename(columns={'award_id': 'kept_count', amount_col: 'kept_funding'})

# Get insufficient by agency
insuf_by_agency = insuf.groupby(agency_col).agg({
    'award_id': 'count',
    amount_col: 'sum'
}).rename(columns={'award_id': 'insuf_count', amount_col: 'insuf_funding'})

# Merge to compare
comparison = insuf_by_agency.join(kept_by_agency, how='left').fillna(0)

# Calculate totals for each agency (kept + insufficient)
comparison['total_count'] = comparison['insuf_count'] + comparison['kept_count']
comparison['total_funding'] = comparison['insuf_funding'] + comparison['kept_funding']

# Calculate % of agency's own climate biotech that is insufficient
comparison['pct_of_agency_funding'] = (comparison['insuf_funding'] / comparison['total_funding'] * 100).fillna(0)

# Calculate % of ALL insufficient funding
comparison['pct_of_all_insufficient'] = (comparison['insuf_funding'] / total_funding * 100).fillna(0)

# Sort by insufficient funding
comparison = comparison.sort_values('insuf_funding', ascending=False)

print(f"\n{'Agency':<45} {'Insuf':>7} {'Insuf $':>15} {'% All Insuf':>12} {'% of Agency':>12}")
print("-"*95)
for agency, row in comparison.head(20).iterrows():
    print(f"{str(agency)[:45]:<45} "
          f"{int(row['insuf_count']):>7,} "
          f"${int(row['insuf_funding']):>14,.0f} "
          f"{row['pct_of_all_insufficient']:>11.1f}% "
          f"{row['pct_of_agency_funding']:>11.1f}%")

# =========================
# DOE AND DOD SPECIFIC
# =========================
print("\n" + "="*70)
print("DOE & DOD DETAILED BREAKDOWN")
print("="*70)

for agency_pattern in ['DOE', 'DEPARTMENT OF ENERGY', 'DOD', 'DEPARTMENT OF DEFENSE']:
    agency_insuf = insuf[insuf[agency_col].astype(str).str.contains(agency_pattern, case=False, na=False)]
    
    if len(agency_insuf) > 0:
        agency_funding = agency_insuf[amount_col].sum()
        avg_len = agency_insuf['abstract_length'].mean() if 'abstract_length' in agency_insuf.columns else 0
        
        print(f"\n{agency_pattern}:")
        print(f"  Insufficient abstract grants: {len(agency_insuf):,}")
        print(f"  Insufficient abstract funding: ${agency_funding:,.0f}")
        
        # Calculate % within this department
        dept_total_grants = kept[kept[agency_col].astype(str).str.contains(agency_pattern, case=False, na=False)]
        dept_total_count = len(dept_total_grants)
        dept_total_funding = dept_total_grants[amount_col].sum()
        
        # Add back insufficient to get true department total
        dept_total_count_with_insuf = dept_total_count + len(agency_insuf)
        dept_total_funding_with_insuf = dept_total_funding + agency_funding
        
        pct_grants = (len(agency_insuf) / dept_total_count_with_insuf * 100) if dept_total_count_with_insuf > 0 else 0
        pct_funding = (agency_funding / dept_total_funding_with_insuf * 100) if dept_total_funding_with_insuf > 0 else 0
        
        print(f"  % of {agency_pattern} grants with insufficient abstracts: {pct_grants:.1f}%")
        print(f"  % of {agency_pattern} funding with insufficient abstracts: {pct_funding:.1f}%")
        print(f"  ({len(agency_insuf):,} of {dept_total_count_with_insuf:,} total {agency_pattern} grants)")
        print(f"  Average abstract length: {avg_len:.1f} chars")
        
        # Show examples
        print(f"\n  Sample grants:")
        for idx, row in agency_insuf.head(5).iterrows():
            abstract_len = row.get('abstract_length', 0)
            abstract_preview = str(row.get('abstract', ''))[:60]
            year = row.get('year', 'N/A')
            print(f"    [{year}] {row['award_id']}: {row['title'][:60]}...")
            print(f"      Abstract ({abstract_len} chars): {abstract_preview}...")

# =========================
# KEEP REASON BREAKDOWN
# =========================
if 'filter_reason' in insuf.columns:
    print("\n" + "="*70)
    print("WHY WERE THESE KEPT? (Despite short abstracts)")
    print("="*70)
    
    print("\nKeep reason breakdown:")
    for reason, count in insuf['filter_reason'].value_counts().items():
        amt = insuf[insuf['filter_reason']==reason][amount_col].sum()
        pct = count / len(insuf) * 100
        print(f"  {reason}: {count:,} grants ({pct:.1f}%) - ${amt:,.0f}")

# =========================
# RECOMMENDATIONS
# =========================
print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70)

standalone_count = (insuf['filter_reason'] == 'kept_standalone').sum() if 'filter_reason' in insuf.columns else 0

print(f"\nTotal grants with insufficient abstracts: {len(insuf):,} (${total_funding:,.0f})")

if standalone_count > 0:
    print(f"\nStandalone keeps: {standalone_count:,}")
    print("  → These matched terms like 'biofuel', 'biorefinery' - likely legitimate climate biotech")
    print("  → Consider: Manual review or accept with limited LLM classification")

print("\nOptions:")
print("  1. Exclude from analysis (insufficient context for LLM)")
print("  2. Manual review for high-value grants")
print("  3. Flag for follow-up research to find better abstracts")
print("  4. Include in LLM but flag as 'limited context'")

print("\n" + "="*70)
print("ANALYSIS COMPLETE")
print("="*70)
