"""
test_llm_classifier_accuracy.py

Tests LLM classifier accuracy against manual classifications.
Outputs summary scores and detailed error analysis.
"""

import pandas as pd
import numpy as np
from collections import defaultdict

## =============================================================================
# FILE PATHS - CONFIGURED
# =============================================================================
from pathlib import Path

# Get the project root directory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # Adjust based on script location

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

# Input files
MANUAL_CLASSIFICATIONS = DATA_DIR / "2019" / "YOUR_MANUAL_CLASSIFICATIONS_2019.xlsx"
STAGE1_OUTPUT = OUTPUT_DIR / "stage1_biotech_fit.csv"
STAGE2_OUTPUT = OUTPUT_DIR / "stage2_characterized.csv"

# Results output
RESULTS_OUTPUT = OUTPUT_DIR / "accuracy_test_results.xlsx"

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
        
        # Load LLM Stage 2
        self.stage2 = pd.read_csv(STAGE2_OUTPUT)
        self.stage2[LLM_ID_COLUMN] = self.stage2[LLM_ID_COLUMN].astype(str).str.strip()
        print(f"✓ Loaded {len(self.stage2)} Stage 2 LLM results")
        
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
        
        print(f"✓ Merged dataset: {len(self.merged)} grants\n")
        
        self.results = {}
        self.error_details = {}
    
    def test_category(self, category_name, manual_col, llm_col, reasoning_col=None):
        """Test accuracy for a single category."""
        # Filter to rows where both exist
        valid = self.merged[[manual_col, llm_col]].dropna()
        
        if len(valid) == 0:
            return {
                'category': category_name,
                'total': 0,
                'correct': 0,
                'incorrect': 0,
                'accuracy': 0.0,
                'errors': []
            }
        
        # Calculate matches
        matches = (self.merged[manual_col] == self.merged[llm_col])
        correct = matches.sum()
        total = len(valid)
        incorrect = total - correct
        accuracy = correct / total if total > 0 else 0.0
        
        # Collect errors
        errors = []
        for idx, row in self.merged.iterrows():
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
            ('Application Area', 'YOUR_s2_application_area', 'LLM_s2_application_area'),
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

if __name__ == "__main__":
    main()
