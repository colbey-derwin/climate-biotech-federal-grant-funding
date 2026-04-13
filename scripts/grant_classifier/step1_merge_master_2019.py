#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Merge Script for 2019 Grant Data

Strategy:
1. Process NSF grants specially:
   - Metadata from NSF JSON files
   - 2019 funding amounts from USASpending (sum ALL transaction types A+B+C+D)
   - Merge NSF JSON + NSF USASpending by award_id

2. Process all other agencies:
   - Remove NSF grants from USASpending
   - Group by award_id and sum amounts
   - Use USASpending metadata

3. Combine NSF + non-NSF into master file

Output: Unified dataset with all agencies
"""

import os
import json
import re
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# =============================================================================
# CONFIGURATION
# =============================================================================
# Get the project root directory
# Script is in scripts/single_year_grant_classifier/merge_master_2019.py
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/single_year_grant_classifier/
PROJECT_ROOT = SCRIPT_DIR.parent.parent       # Go up 2 levels! ← CHANGED

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "2019"
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

# Input files
NSF_JSON_DIR = RAW_DATA_DIR / "NSF2019"
USASPENDING_CSV = RAW_DATA_DIR / "USASpending2019.csv"

# Output file
OUTPUT_FILE = OUTPUT_DIR / "merged_2019.csv"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*80)
print("MASTER MERGE: NSF JSONs + USASpending 2019")
print("="*80)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def clean_whitespace(s: str) -> str:
    """Normalize whitespace in text fields."""
    if not isinstance(s, str):
        return ""
    return re.sub(r"\s+", " ", s).strip()

# =============================================================================
# PART 1: LOAD NSF JSON METADATA
# =============================================================================
print("\n" + "="*80)
print("PART 1: Loading NSF JSON files...")
print("="*80)

json_files = list(Path(NSF_JSON_DIR).glob("*.json"))
print(f"Found {len(json_files):,} JSON files")

nsf_metadata = {}

for json_file in tqdm(json_files, desc="Loading NSF JSONs"):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        award_id = str(data.get("awd_id", ""))
        if not award_id:
            continue
        
        # Extract POR (Project Outcomes Report) text if available
        por_text = ""
        if "por" in data and data["por"]:
            por_cntn = data["por"].get("por_cntn", "")
            por_txt = data["por"].get("por_txt_cntn", "")
            por_text = por_txt if por_txt else por_cntn
        
        # Get PI info
        pi_name = ""
        pi_email = ""
        if "pi" in data and data["pi"] and len(data["pi"]) > 0:
            pi_name = data["pi"][0].get("pi_full_name", "")
            pi_email = data["pi"][0].get("pi_email_addr", "")
        
        # Get institution info
        inst_name = ""
        inst_city = ""
        inst_state = ""
        if "inst" in data and data["inst"]:
            inst_name = data["inst"].get("inst_name", "")
            inst_city = data["inst"].get("inst_city_name", "")
            inst_state = data["inst"].get("inst_state_code", "")
        
        nsf_metadata[award_id] = {
            'award_id': award_id,
            'title': clean_whitespace(data.get('awd_titl_txt', '')),
            'abstract': clean_whitespace(data.get('awd_abstract_narration', '')),
            'por_text': clean_whitespace(por_text),
            'start_date': data.get('awd_eff_date', ''),
            'end_date': data.get('awd_exp_date', ''),
            'pi_name': pi_name,
            'pi_email': pi_email,
            'institution': inst_name,
            'inst_city': inst_city,
            'inst_state': inst_state,
            'directorate': data.get('dir_abbr', ''),
            'division': data.get('div_abbr', ''),
            'program': data.get('org_code', ''),
            'award_type': data.get('awd_istr_txt', ''),
        }
        
    except Exception as e:
        print(f"\nError loading {json_file.name}: {e}")
        continue

print(f"Loaded metadata for {len(nsf_metadata):,} NSF grants")

# =============================================================================
# PART 2: LOAD USASPENDING DATA
# =============================================================================
print("\n" + "="*80)
print("PART 2: Loading USASpending CSV...")
print("="*80)

df = pd.read_csv(USASPENDING_CSV, low_memory=False)
print(f"Loaded {len(df):,} total USASpending rows")

# =============================================================================
# PART 3: PROCESS NSF GRANTS FROM USASPENDING
# =============================================================================
print("\n" + "="*80)
print("PART 3: Processing NSF grants from USASpending...")
print("="*80)

# Identify NSF grants
is_nsf = (
    df["awarding_agency_name"].fillna("").str.upper().str.contains("NATIONAL SCIENCE FOUNDATION|\\bNSF\\b", regex=True) |
    df["funding_agency_name"].fillna("").str.upper().str.contains("NATIONAL SCIENCE FOUNDATION|\\bNSF\\b", regex=True)
)

nsf_usa = df[is_nsf].copy()
print(f"Found {len(nsf_usa):,} NSF transactions in USASpending")

# Extract NSF award ID (7-digit number)
nsf_usa['award_id'] = nsf_usa['award_id_fain'].astype(str).str.extract(r'(\d{7})', expand=False)

# Remove rows without valid award ID
nsf_usa = nsf_usa[nsf_usa['award_id'].notna()].copy()
print(f"  {len(nsf_usa):,} transactions with valid NSF award IDs")

# Group by award_id and sum ALL transaction types (A+B+C+D)
print("\nGrouping NSF transactions by award_id (summing ALL types A+B+C+D)...")

nsf_grouped = nsf_usa.groupby('award_id').agg({
    'federal_action_obligation': 'sum',  # Sum ALL transactions
    'period_of_performance_start_date': 'first',
    'period_of_performance_current_end_date': 'first',
    'transaction_description': 'first',
    'recipient_name': 'first',
    'recipient_city_name': 'first',
    'recipient_state_code': 'first',
}).reset_index()

print(f"  Grouped into {len(nsf_grouped):,} unique NSF grants")
print(f"  Total NSF funding from USASpending: ${nsf_grouped['federal_action_obligation'].sum():,.0f}")

# =============================================================================
# PART 4: MERGE NSF METADATA + USASPENDING AMOUNTS
# =============================================================================
print("\n" + "="*80)
print("PART 4: Merging NSF metadata with USASpending amounts...")
print("="*80)

# Convert NSF metadata to DataFrame
nsf_meta_df = pd.DataFrame.from_dict(nsf_metadata, orient='index').reset_index(drop=True)

# Merge NSF metadata with USASpending amounts
nsf_merged = pd.merge(
    nsf_meta_df,
    nsf_grouped[['award_id', 'federal_action_obligation']],
    on='award_id',
    how='outer',
    indicator=True
)

# Handle 3 cases for NSF grants
print("\nNSF Merge Results:")
print(f"  In both (JSON + USASpending): {(nsf_merged['_merge'] == 'both').sum():,}")
print(f"  Only in JSON: {(nsf_merged['_merge'] == 'right_only').sum():,}")
print(f"  Only in USASpending: {(nsf_merged['_merge'] == 'left_only').sum():,}")

# Create final NSF dataset
nsf_final = nsf_merged.copy()
nsf_final['source'] = 'NSF'
nsf_final['funder'] = 'National Science Foundation'

# Use USASpending amount if available, otherwise use 0 (for JSON-only grants)
nsf_final['award_amount'] = nsf_final['federal_action_obligation'].fillna(0)

# Clean up
nsf_final = nsf_final.drop(['federal_action_obligation', '_merge'], axis=1)

print(f"\nFinal NSF dataset: {len(nsf_final):,} grants")
print(f"  Total NSF funding: ${nsf_final['award_amount'].sum():,.0f}")

# =============================================================================
# PART 5: PROCESS NON-NSF AGENCIES FROM USASPENDING
# =============================================================================
print("\n" + "="*80)
print("PART 5: Processing non-NSF agencies from USASpending...")
print("="*80)

# Get all NON-NSF grants
non_nsf = df[~is_nsf].copy()
print(f"Found {len(non_nsf):,} non-NSF transactions")

# Standardize schema
non_nsf_standardized = pd.DataFrame({
    'source': 'USASpending',
    'award_id': non_nsf['award_id_fain'].fillna(non_nsf['award_id_uri']),
    'title': non_nsf['transaction_description'].fillna(
        non_nsf['prime_award_base_transaction_description'].fillna(
            non_nsf['cfda_title'].fillna(non_nsf['award_id_fain'])
        )
    ).apply(clean_whitespace),
    'abstract': non_nsf['funding_opportunity_goals_text'].fillna(
        non_nsf['transaction_description'].fillna("")
    ).apply(clean_whitespace),
    'por_text': '',
    'start_date': non_nsf['period_of_performance_start_date'],
    'end_date': non_nsf['period_of_performance_current_end_date'],
    'award_amount': pd.to_numeric(non_nsf['federal_action_obligation'], errors='coerce'),
    'pi_name': non_nsf['recipient_name'],
    'pi_email': '',
    'institution': non_nsf['recipient_name'],
    'inst_city': non_nsf['recipient_city_name'],
    'inst_state': non_nsf['recipient_state_code'],
    'directorate': '',
    'division': '',
    'program': non_nsf['cfda_number'],
    'award_type': non_nsf['assistance_type_description'],
    'funder': non_nsf['awarding_agency_name'].fillna(non_nsf['funding_agency_name']),
})

# Group by award_id and sum amounts
print("\nGrouping non-NSF transactions by award_id...")

def first_nonempty(series):
    """Get first non-empty value from series."""
    for val in series:
        if pd.notna(val) and (not isinstance(val, str) or val.strip()):
            return val
    return pd.NA

agg_dict = {
    'source': 'first',
    'title': first_nonempty,
    'abstract': first_nonempty,
    'por_text': 'first',
    'start_date': 'first',
    'end_date': 'first',
    'award_amount': 'sum',  # SUM all transactions
    'pi_name': first_nonempty,
    'pi_email': 'first',
    'institution': first_nonempty,
    'inst_city': first_nonempty,
    'inst_state': first_nonempty,
    'directorate': 'first',
    'division': 'first',
    'program': first_nonempty,
    'award_type': first_nonempty,
    'funder': first_nonempty,
}

non_nsf_grouped = non_nsf_standardized.groupby('award_id', as_index=False).agg(agg_dict)

print(f"  Grouped into {len(non_nsf_grouped):,} unique non-NSF grants")
print(f"  Total non-NSF funding: ${non_nsf_grouped['award_amount'].sum():,.0f}")

# =============================================================================
# PART 6: COMBINE NSF + NON-NSF INTO MASTER FILE
# =============================================================================
print("\n" + "="*80)
print("PART 6: Combining NSF + non-NSF into master file...")
print("="*80)

# Ensure both have same columns
all_cols = ['source', 'award_id', 'title', 'abstract', 'por_text', 
            'start_date', 'end_date', 'award_amount', 'pi_name', 'pi_email',
            'institution', 'inst_city', 'inst_state', 'directorate', 'division',
            'program', 'award_type', 'funder']

# Add missing columns to NSF if needed
for col in all_cols:
    if col not in nsf_final.columns:
        nsf_final[col] = ''

# Reorder columns
nsf_final = nsf_final[all_cols]
non_nsf_grouped = non_nsf_grouped[all_cols]

# Combine
master = pd.concat([nsf_final, non_nsf_grouped], ignore_index=True)

# Create unique key
master['unique_key'] = master['source'] + '::' + master['award_id'].astype(str)

# Convert dates
master['start_date'] = pd.to_datetime(master['start_date'], errors='coerce')
master['end_date'] = pd.to_datetime(master['end_date'], errors='coerce')
master['year'] = master['start_date'].dt.year

# =============================================================================
# PART 7: SAVE AND SUMMARIZE
# =============================================================================
print("\n" + "="*80)
print("PART 7: Saving master file...")
print("="*80)

master.to_csv(OUTPUT_FILE, index=False)

print(f"\n✅ Master file saved: {OUTPUT_FILE}")
print(f"\n{'='*80}")
print("MASTER MERGE COMPLETE")
print("="*80)

print(f"\nTotal grants: {len(master):,}")
print(f"Total funding: ${master['award_amount'].sum():,.0f}")

print(f"\nBreakdown by source:")
print(master['source'].value_counts())

print(f"\nTop 10 funders:")
print(master['funder'].value_counts().head(10))

print(f"\nNSF grants breakdown:")
nsf_only = master[master['source'] == 'NSF']
print(f"  Total NSF grants: {len(nsf_only):,}")
print(f"  Total NSF funding: ${nsf_only['award_amount'].sum():,.0f}")
print(f"  With USASpending amounts: {(nsf_only['award_amount'] > 0).sum():,}")
print(f"  Without USASpending amounts: {(nsf_only['award_amount'] == 0).sum():,}")

print("\n" + "="*80)
print("NEXT STEP: Run climate_biotech_filter.py on this master file")
print("="*80)
