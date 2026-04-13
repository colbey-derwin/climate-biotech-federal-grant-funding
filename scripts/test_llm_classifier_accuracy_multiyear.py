"""
test_llm_classifier_accuracy_multiyear.py

Tests LLM classifier accuracy against manual classifications (ALL YEARS).
Outputs summary scores and detailed error analysis.

Note: Currently uses 2019 validation set. When you create additional 
manual classification files, update MANUAL_CLASSIFICATIONS path.
"""

# NEW:
import os
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

# =============================================================================
# FILE PATHS - CONFIGURED
# =============================================================================
# Get the project root directory
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/
PROJECT_ROOT = SCRIPT_DIR.parent              # climate_biotech_federal_grant_funding/

# Data and output directories
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

# Manual classifications - updated with new validation grants (63 total)
# NOTE: Last 13 grants (added April 2026) only have APPLICATION_AREA classifications
MANUAL_CLASSIFICATIONS = DATA_DIR / "YOUR_MANUAL_CLASSIFICATIONS_multiyear.xlsx"

# LLM outputs - multi-year versions
STAGE1_OUTPUT = OUTPUT_DIR / "stage1_biotech_fit_all_years.csv"
STAGE2_OUTPUT = OUTPUT_DIR / "stage2_characterized_all_years.csv"
STAGE2_REFINED_TEST = OUTPUT_DIR / "refinement_test_results.csv"  # NEW: Refined test results
RESULTS_OUTPUT = OUTPUT_DIR / "accuracy_test_results_stage2_all_years.xlsx"  # Different name to avoid overwriting

# Grant ID column name in LLM outputs
LLM_ID_COLUMN = "unique_key"

# =============================================================================
# MAIN TESTING CLASS
# =============================================================================

class AccuracyTester:
    def __init__(self):
        """Initialize and load all data."""
        print("="*80)
        print("LOADING DATA")
        print("="*80)
        
        # Load manual classifications
        self.manual = pd.read_excel(MANUAL_CLASSIFICATIONS)
        self.manual['grant_id'] = self.manual['grant_id'].astype(str).str.strip()
        print(f"✓ Loaded {len(self.manual)} manual classifications")
        
        # Load LLM Stage 1
        self.stage1 = pd.read_csv(STAGE1_OUTPUT)
        self.stage1[LLM_ID_COLUMN] = self.stage1[LLM_ID_COLUMN].astype(str).str.strip()
        print(f"✓ Loaded {len(self.stage1)} Stage 1 LLM results")
        
        # Show year distribution in Stage 1
        if 'year' in self.stage1.columns:
            print(f"  Stage 1 year distribution:")
            for year, count in sorted(self.stage1['year'].value_counts().items()):
                print(f"    {year}: {count:,} grants")
        
        # Load LLM Stage 2
        # Try refined test results first (if refine script was run in test mode)
        if STAGE2_REFINED_TEST.exists():
            self.stage2 = pd.read_csv(STAGE2_REFINED_TEST)
            print(f"✓ Loaded {len(self.stage2)} Stage 2 LLM results (FROM REFINED TEST)")
        else:
            self.stage2 = pd.read_csv(STAGE2_OUTPUT)
            print(f"✓ Loaded {len(self.stage2)} Stage 2 LLM results")
        
        self.stage2[LLM_ID_COLUMN] = self.stage2[LLM_ID_COLUMN].astype(str).str.strip()
        
        # Show year distribution in Stage 2
        if 'year' in self.stage2.columns:
            print(f"  Stage 2 year distribution:")
            for year, count in sorted(self.stage2['year'].value_counts().items()):
                print(f"    {year}: {count:,} grants")
        
        # Merge everything
        self.merged = self.manual.copy()
        
        # Merge Stage 1
        s1_cols = [LLM_ID_COLUMN, 's1_decision', 's1_confidence', 's1_reasoning']
        s1_subset = self.stage1[s1_cols].copy()
        s1_subset.columns = ['grant_id', 'LLM_s1_decision', 'LLM_s1_confidence', 'LLM_s1_reasoning']
        self.merged = self.merged.merge(s1_subset, on='grant_id', how='left')
        
        # Merge Stage 2
        s2_cols = [LLM_ID_COLUMN, 's2_grant_type', 's2_orientation', 's2_research_stage', 
                   's2_application_area', 's2_research_approach', 's2_confidence']
        s2_subset = self.stage2[s2_cols].copy()
        s2_subset.columns = ['grant_id', 'LLM_s2_grant_type', 'LLM_s2_orientation', 
                             'LLM_s2_research_stage', 'LLM_s2_application_area', 
                             'LLM_s2_research_approach', 'LLM_s2_confidence']
        self.merged = self.merged.merge(s2_subset, on='grant_id', how='left')
        
        print(f"✓ Merged dataset: {len(self.merged)} grants")
        
        # Check for duplicates created by merge
        duplicates = self.merged[self.merged.duplicated('grant_id', keep=False)]
        if len(duplicates) > 0:
            num_dup_ids = duplicates['grant_id'].nunique()
            print(f"⚠️  WARNING: Found {len(duplicates)} duplicate rows affecting {num_dup_ids} grant IDs")
            print(f"   This suggests duplicate grant IDs in your LLM output files.")
            print(f"   Tests will use first occurrence only.\n")
        else:
            print(f"✓ No duplicates detected in merged data\n")
        
        self.results = {}
        self.error_details = {}
    
    def test_category(self, category_name, manual_col, llm_col, reasoning_col=None):
        """Test accuracy for a single category."""
        # Filter to rows where both exist (valid comparison rows only)
        valid_mask = self.merged[manual_col].notna() & self.merged[llm_col].notna()
        valid_rows = self.merged[valid_mask].copy()
        
        if len(valid_rows) == 0:
            return {
                'category': category_name,
                'total': 0,
                'correct': 0,
                'incorrect': 0,
                'accuracy': 0.0,
                'errors': []
            }
        
        # Remove duplicates - keep first occurrence only
        valid_rows = valid_rows.drop_duplicates(subset=['grant_id'], keep='first')
        
        # Calculate matches on deduplicated valid rows only
        matches = (valid_rows[manual_col] == valid_rows[llm_col])
        correct = matches.sum()
        total = len(valid_rows)
        incorrect = total - correct
        accuracy = correct / total if total > 0 else 0.0
        
        # Collect errors (from deduplicated rows only)
        errors = []
        for idx, row in valid_rows.iterrows():
            manual_val = row.get(manual_col)
            llm_val = row.get(llm_col)
            
            if pd.notna(manual_val) and pd.notna(llm_val) and manual_val != llm_val:
                error = {
                    'grant_id': row['grant_id'],
                    'title': row['title'],
                    'manual_value': manual_val,
                    'llm_value': llm_val,
                }
                
                # Add reasoning if available
                if reasoning_col and reasoning_col in row:
                    error['llm_reasoning'] = row[reasoning_col]
                
                errors.append(error)
        
        return {
            'category': category_name,
            'total': total,
            'correct': correct,
            'incorrect': incorrect,
            'accuracy': accuracy,
            'errors': errors
        }
    
    def run_tests(self):
        """Run all accuracy tests."""
        print("="*80)
        print("RUNNING ACCURACY TESTS")
        print("="*80)
        print()
        
        # Stage 1
        print("STAGE 1: BIOTECH FIT (KEEP/REMOVE)")
        print("-" * 80)
        s1_result = self.test_category(
            'Stage 1: Decision',
            'YOUR_s1_decision',
            'LLM_s1_decision',
            'LLM_s1_reasoning'
        )
        self.results['stage1_decision'] = s1_result
        print(f"Total: {s1_result['total']}")
        print(f"Correct: {s1_result['correct']}")
        print(f"Incorrect: {s1_result['incorrect']}")
        print(f"ACCURACY: {s1_result['accuracy']:.2%}")
        print()
        
        # Stage 2 categories
        print("STAGE 2: DETAILED CLASSIFICATIONS")
        print("-" * 80)
        
        categories = [
            ('Grant Type', 'YOUR_s2_grant_type', 'LLM_s2_grant_type'),
            ('Orientation', 'YOUR_s2_orientation', 'LLM_s2_orientation'),
            ('Research Stage', 'YOUR_s2_research_stage', 'LLM_s2_research_stage'),
            ('Application Area', 'NEW_s2_application_area', 'LLM_s2_application_area'),  # Use NEW categories
            ('Research Approach', 'YOUR_s2_research_approach', 'LLM_s2_research_approach'),
        ]
        
        for name, manual_col, llm_col in categories:
            result = self.test_category(name, manual_col, llm_col)
            self.results[f"stage2_{name.lower().replace(' ', '_')}"] = result
            
            if result['total'] > 0:
                print(f"{name}:")
                print(f"  Total: {result['total']}")
                print(f"  Correct: {result['correct']}")
                print(f"  Incorrect: {result['incorrect']}")
                print(f"  ACCURACY: {result['accuracy']:.2%}")
                print()
    
    def print_summary(self):
        """Print overall summary."""
        print("="*80)
        print("SUMMARY SCORES")
        print("="*80)
        print()
        print(f"{'CATEGORY':<40} {'TOTAL':<10} {'CORRECT':<10} {'ACCURACY':<10}")
        print("-" * 80)
        
        for key, result in self.results.items():
            if result['total'] > 0:
                category_name = result['category']
                print(f"{category_name:<40} {result['total']:<10} {result['correct']:<10} {result['accuracy']:>8.2%}")
        
        print()
    
    def print_errors(self):
        """Print detailed error information for each category."""
        print("="*80)
        print("ERROR DETAILS BY CATEGORY")
        print("="*80)
        print()
        
        for key, result in self.results.items():
            if len(result['errors']) > 0:
                print(f"\n{result['category'].upper()}")
                print("-" * 80)
                print(f"Found {len(result['errors'])} errors:\n")
                
                for i, error in enumerate(result['errors'], 1):
                    print(f"{i}. Grant ID: {error['grant_id']}")
                    print(f"   Title: {error['title'][:70]}...")
                    print(f"   Manual Classification: {error['manual_value']}")
                    print(f"   LLM Classification: {error['llm_value']}")
                    
                    if 'llm_reasoning' in error and pd.notna(error['llm_reasoning']):
                        reasoning = str(error['llm_reasoning'])[:200]
                        print(f"   LLM Reasoning: {reasoning}...")
                    
                    print()
    
    def export_to_excel(self):
        """Export results to Excel with multiple sheets."""
        print("="*80)
        print("EXPORTING RESULTS")
        print("="*80)
        
        with pd.ExcelWriter(RESULTS_OUTPUT, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = []
            for key, result in self.results.items():
                summary_data.append({
                    'Category': result['category'],
                    'Total': result['total'],
                    'Correct': result['correct'],
                    'Incorrect': result['incorrect'],
                    'Accuracy': result['accuracy']
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Error sheets for each category
            for key, result in self.results.items():
                if len(result['errors']) > 0:
                    error_df = pd.DataFrame(result['errors'])
                    # Excel sheet name: remove invalid chars and limit to 31 chars
                    sheet_name = result['category'].replace(':', '-').replace('/', '-')[:31]
                    error_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Full comparison sheet
            self.merged.to_excel(writer, sheet_name='Full Comparison', index=False)
        
        print(f"✓ Results exported to: {RESULTS_OUTPUT}")
        print()

def main():
    """Main execution."""
    tester = AccuracyTester()
    tester.run_tests()
    tester.print_summary()
    tester.print_errors()
    tester.export_to_excel()
    
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)
    print()
    print("VALIDATION SET COMPOSITION:")
    print("  - 50 grants with full Stage 1 + Stage 2 classifications")
    print("  - 13 grants with APPLICATION_AREA classification only (added April 2026)")
    print("  - Total: 63 validation grants")

if __name__ == "__main__":
    main()
