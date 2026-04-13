#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualize_climate_biotech_funding.py

Professional visualizations of climate biotech grant funding (2019-2025).
Focus on FUNDING AMOUNTS ($), not grant counts.

Creates publication-quality plots:
- Time series trends by various dimensions
- Vertical bar charts for classifications
- Breakdown by research approach (collaborative vs single focus)
- Top funders, application areas, etc.

Output: PNG files + summary statistics
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from matplotlib.ticker import FuncFormatter
import warnings
warnings.filterwarnings('ignore')

# Set professional style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
sns.set_context("notebook", font_scale=1.1)

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent  # visualization/
PROJECT_ROOT = SCRIPT_DIR.parent              # climate_biotech_federal_grant_funding/

OUTPUT_DIR_CLASSIFIER = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

STAGE2_FILE = OUTPUT_DIR_CLASSIFIER / "stage2_characterized_all_years_with_industry_framing.csv"
OUTPUT_DIR = SCRIPT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Color schemes
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'accent': '#F18F01',
    'success': '#06A77D',
    'warning': '#D4AF37',
    'neutral': '#6C757D',
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def millions_formatter(x, pos):
    """Format y-axis as millions of dollars."""
    return f'${x/1e6:.0f}M'

def billions_formatter(x, pos):
    """Format y-axis as billions of dollars."""
    return f'${x/1e9:.1f}B'

def save_plot(filename, dpi=300):
    """Save plot with consistent settings."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    plt.tight_layout()
    plt.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
    print(f"✓ Saved: {filename}")
    plt.close()

def format_currency(value):
    """Format currency values for display."""
    if value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.1f}M"
    elif value >= 1e3:
        return f"${value/1e3:.0f}K"
    else:
        return f"${value:.0f}"

# =============================================================================
# LOAD DATA
# =============================================================================
print("="*80)
print("CLIMATE BIOTECH FUNDING VISUALIZATIONS")
print("="*80)
print()

print("Loading data...")
df = pd.read_csv(STAGE2_FILE, low_memory=False)
print(f"✓ Loaded {len(df):,} characterized grants")
print(f"  Total funding: {format_currency(df['award_amount'].sum())}")
print()

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================
print("="*80)
print("SUMMARY STATISTICS")
print("="*80)
print()

total_funding = df['award_amount'].sum()
total_grants = len(df)
avg_grant = df['award_amount'].mean()

print(f"Total Grants: {total_grants:,}")
print(f"Total Funding: {format_currency(total_funding)}")
print(f"Average Grant: {format_currency(avg_grant)}")
print()

# Year range
if 'year' in df.columns:
    years = sorted(df['year'].unique())
    print(f"Year Range: {min(years)} - {max(years)}")
    print()

# =============================================================================
# 1. FUNDING TRENDS OVER TIME (TIME SERIES)
# =============================================================================
print("Creating time series visualizations...")

if 'year' in df.columns:
    # Overall funding by year
    yearly_funding = df.groupby('year')['award_amount'].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(yearly_funding['year'], yearly_funding['award_amount'], 
            marker='o', linewidth=2.5, markersize=8, color=COLORS['primary'])
    ax.fill_between(yearly_funding['year'], yearly_funding['award_amount'], 
                     alpha=0.3, color=COLORS['primary'])
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding Trends (2019-2025)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.grid(True, alpha=0.3)
    
    # Add value labels on points
    for idx, row in yearly_funding.iterrows():
        ax.annotate(format_currency(row['award_amount']), 
                   (row['year'], row['award_amount']),
                   textcoords="offset points", xytext=(0,10), 
                   ha='center', fontsize=9, fontweight='bold')
    
    save_plot('01_funding_trends_overall.png')

# =============================================================================
# 2. FUNDING BY GRANT TYPE
# =============================================================================
print("Creating grant type visualizations...")

grant_type_funding = df.groupby('s2_grant_type')['award_amount'].sum().sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(range(len(grant_type_funding)), grant_type_funding.values, 
              color=COLORS['primary'], edgecolor='black', linewidth=1.2)

# Color the bars differently
colors_list = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['success']]
for i, bar in enumerate(bars):
    bar.set_color(colors_list[i % len(colors_list)])

ax.set_xticks(range(len(grant_type_funding)))
ax.set_xticklabels(grant_type_funding.index, rotation=0, fontsize=11)
ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
ax.set_title('Climate Biotech Funding by Grant Type', 
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='y', alpha=0.3)

# Add value labels on bars
for i, (idx, val) in enumerate(grant_type_funding.items()):
    ax.text(i, val, format_currency(val), 
           ha='center', va='bottom', fontsize=10, fontweight='bold')

save_plot('02_funding_by_grant_type.png')

# Grant type over time
if 'year' in df.columns:
    grant_type_yearly = df.groupby(['year', 's2_grant_type'])['award_amount'].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for grant_type in grant_type_yearly['s2_grant_type'].unique():
        if pd.notna(grant_type):
            data = grant_type_yearly[grant_type_yearly['s2_grant_type'] == grant_type]
            ax.plot(data['year'], data['award_amount'], 
                   marker='o', linewidth=2, markersize=6, label=grant_type)
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding Trends by Grant Type', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.legend(loc='best', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3)
    
    save_plot('03_funding_trends_by_grant_type.png')

# =============================================================================
# 3. FUNDING BY ORIENTATION
# =============================================================================
print("Creating orientation visualizations...")

orientation_funding = df.groupby('s2_orientation')['award_amount'].sum().sort_values(ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(range(len(orientation_funding)), orientation_funding.values,
              color=[COLORS['primary'], COLORS['accent']], 
              edgecolor='black', linewidth=1.2)

ax.set_xticks(range(len(orientation_funding)))
ax.set_xticklabels(orientation_funding.index, rotation=0, fontsize=11)
ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
ax.set_title('Climate Biotech Funding by Orientation', 
             fontsize=14, fontweight='bold', pad=20)
ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='y', alpha=0.3)

# Add value labels and percentages
for i, (idx, val) in enumerate(orientation_funding.items()):
    pct = (val / total_funding) * 100
    ax.text(i, val, f'{format_currency(val)}\n({pct:.1f}%)', 
           ha='center', va='bottom', fontsize=10, fontweight='bold')

save_plot('04_funding_by_orientation.png')

# Orientation over time
if 'year' in df.columns:
    orientation_yearly = df.groupby(['year', 's2_orientation'])['award_amount'].sum().reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for orientation in orientation_yearly['s2_orientation'].unique():
        if pd.notna(orientation):
            data = orientation_yearly[orientation_yearly['s2_orientation'] == orientation]
            ax.plot(data['year'], data['award_amount'], 
                   marker='o', linewidth=2.5, markersize=7, label=orientation)
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding Trends by Orientation', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.legend(loc='best', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3)
    
    save_plot('05_funding_trends_by_orientation.png')

# =============================================================================
# 4. FUNDING BY RESEARCH STAGE (research grants only)
# =============================================================================
print("Creating research stage visualizations...")

research_grants = df[df['s2_grant_type'] == 'research'].copy()

if len(research_grants) > 0 and 's2_research_stage' in research_grants.columns:
    stage_funding = research_grants.groupby('s2_research_stage')['award_amount'].sum().sort_values(ascending=False)
    
    # Clean up labels
    label_map = {
        'Use Inspired Research': 'Use-Inspired\nResearch',
        'Bench Scale Tech Development': 'Bench Scale\nTech Dev',
        'Piloting': 'Piloting'
    }
    stage_labels = [label_map.get(x, x) for x in stage_funding.index]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(stage_funding)), stage_funding.values,
                  color=[COLORS['success'], COLORS['warning'], COLORS['secondary']], 
                  edgecolor='black', linewidth=1.2)
    
    ax.set_xticks(range(len(stage_funding)))
    ax.set_xticklabels(stage_labels, rotation=0, fontsize=11)
    ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding by Research Stage\n(Research Grants Only)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.grid(True, axis='y', alpha=0.3)
    
    # Add value labels
    for i, (idx, val) in enumerate(stage_funding.items()):
        ax.text(i, val, format_currency(val), 
               ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    save_plot('06_funding_by_research_stage.png')
    
    # Research stage over time
    if 'year' in research_grants.columns:
        stage_yearly = research_grants.groupby(['year', 's2_research_stage'])['award_amount'].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for stage in stage_yearly['s2_research_stage'].unique():
            if pd.notna(stage):
                data = stage_yearly[stage_yearly['s2_research_stage'] == stage]
                ax.plot(data['year'], data['award_amount'], 
                       marker='o', linewidth=2, markersize=6, label=stage)
        
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
        ax.set_title('Climate Biotech Funding Trends by Research Stage', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        save_plot('07_funding_trends_by_research_stage.png')

# =============================================================================
# 5. RESEARCH APPROACH ANALYSIS (collaborative vs single focus)
# =============================================================================
print("Creating research approach visualizations...")

# Filter to public_facing research grants (where research_approach is classified)
public_research = df[(df['s2_grant_type'] == 'research') & 
                     (df['s2_orientation'] == 'public_facing')].copy()

if len(public_research) > 0 and 's2_research_approach' in public_research.columns:
    approach_funding = public_research.groupby('s2_research_approach')['award_amount'].sum().sort_values(ascending=False)
    approach_counts = public_research.groupby('s2_research_approach').size().sort_values(ascending=False)
    
    # Summary statistics
    print("\n" + "="*80)
    print("RESEARCH APPROACH BREAKDOWN")
    print("(Public-Facing Research Grants Only)")
    print("="*80)
    print()
    
    for approach in approach_funding.index:
        if pd.notna(approach):
            funding = approach_funding[approach]
            count = approach_counts[approach]
            pct_funding = (funding / approach_funding.sum()) * 100
            pct_count = (count / approach_counts.sum()) * 100
            avg = funding / count
            
            print(f"{approach}:")
            print(f"  Grants: {count:,} ({pct_count:.1f}%)")
            print(f"  Funding: {format_currency(funding)} ({pct_funding:.1f}%)")
            print(f"  Average: {format_currency(avg)}")
            print()
    
    # Bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(approach_funding)), approach_funding.values,
                  color=[COLORS['primary'], COLORS['accent']], 
                  edgecolor='black', linewidth=1.2)
    
    ax.set_xticks(range(len(approach_funding)))
    ax.set_xticklabels(['Collaborative\nInterdisciplinary', 'Single\nFocus'] 
                       if len(approach_funding) == 2 else approach_funding.index, 
                       rotation=0, fontsize=11)
    ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding by Research Approach\n(Public-Facing Research Grants)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.grid(True, axis='y', alpha=0.3)
    
    # Add value labels with counts
    for i, approach in enumerate(approach_funding.index):
        if pd.notna(approach):
            funding = approach_funding[approach]
            count = approach_counts[approach]
            ax.text(i, funding, f'{format_currency(funding)}\n({count:,} grants)', 
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    save_plot('08_funding_by_research_approach.png')
    
    # Research approach over time
    if 'year' in public_research.columns:
        approach_yearly = public_research.groupby(['year', 's2_research_approach'])['award_amount'].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for approach in approach_yearly['s2_research_approach'].unique():
            if pd.notna(approach):
                data = approach_yearly[approach_yearly['s2_research_approach'] == approach]
                ax.plot(data['year'], data['award_amount'], 
                       marker='o', linewidth=2.5, markersize=7, label=approach)
        
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Total Funding', fontsize=12, fontweight='bold')
        ax.set_title('Climate Biotech Funding Trends by Research Approach\n(Public-Facing Research)', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
        ax.legend(loc='best', frameon=True, shadow=True, 
                 labels=['Collaborative Interdisciplinary', 'Single Focus'])
        ax.grid(True, alpha=0.3)
        
        save_plot('09_funding_trends_by_research_approach.png')

# =============================================================================
# 6. FUNDING BY APPLICATION AREA
# =============================================================================
print("Creating application area visualizations...")

app_area_funding = df.groupby('s2_application_area')['award_amount'].sum().sort_values(ascending=False)

# Top 10 application areas
top_10_areas = app_area_funding.head(10)

fig, ax = plt.subplots(figsize=(12, 8))
bars = ax.barh(range(len(top_10_areas)), top_10_areas.values,
               color=COLORS['primary'], edgecolor='black', linewidth=1.2)

# Color gradient
colors_gradient = sns.color_palette("coolwarm", len(top_10_areas))
for i, bar in enumerate(bars):
    bar.set_color(colors_gradient[i])

ax.set_yticks(range(len(top_10_areas)))
ax.set_yticklabels(top_10_areas.index, fontsize=10)
ax.set_xlabel('Total Funding', fontsize=12, fontweight='bold')
ax.set_title('Climate Biotech Funding by Application Area\n(Top 10)', 
             fontsize=14, fontweight='bold', pad=20)
ax.xaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='x', alpha=0.3)
ax.invert_yaxis()

# Add value labels
for i, (idx, val) in enumerate(top_10_areas.items()):
    ax.text(val, i, f' {format_currency(val)}', 
           va='center', fontsize=9, fontweight='bold')

save_plot('10_funding_by_application_area.png')

# =============================================================================
# 7. TOP FUNDERS
# =============================================================================
print("Creating funder visualizations...")

if 'funder' in df.columns:
    funder_funding = df.groupby('funder')['award_amount'].sum().sort_values(ascending=False)
    top_10_funders = funder_funding.head(10)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(range(len(top_10_funders)), top_10_funders.values,
                   color=COLORS['secondary'], edgecolor='black', linewidth=1.2)
    
    # Color gradient
    colors_gradient = sns.color_palette("viridis", len(top_10_funders))
    for i, bar in enumerate(bars):
        bar.set_color(colors_gradient[i])
    
    # Shorten funder names for display
    funder_labels = [f[:50] + '...' if len(f) > 50 else f for f in top_10_funders.index]
    
    ax.set_yticks(range(len(top_10_funders)))
    ax.set_yticklabels(funder_labels, fontsize=10)
    ax.set_xlabel('Total Funding', fontsize=12, fontweight='bold')
    ax.set_title('Climate Biotech Funding by Agency\n(Top 10)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.xaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.grid(True, axis='x', alpha=0.3)
    ax.invert_yaxis()
    
    # Add value labels
    for i, (idx, val) in enumerate(top_10_funders.items()):
        ax.text(val, i, f' {format_currency(val)}', 
               va='center', fontsize=9, fontweight='bold')
    
    save_plot('11_funding_by_top_funders.png')

# =============================================================================
# 8. COMPREHENSIVE BREAKDOWN PLOT
# =============================================================================
print("Creating comprehensive breakdown visualization...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Climate Biotech Funding Comprehensive Breakdown', 
             fontsize=16, fontweight='bold', y=0.995)

# Grant Type
ax = axes[0, 0]
grant_type_top = grant_type_funding.head(4)
bars = ax.bar(range(len(grant_type_top)), grant_type_top.values,
              color=[COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['success']])
ax.set_xticks(range(len(grant_type_top)))
ax.set_xticklabels(grant_type_top.index, rotation=45, ha='right', fontsize=10)
ax.set_ylabel('Total Funding', fontsize=11, fontweight='bold')
ax.set_title('By Grant Type', fontsize=12, fontweight='bold')
ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='y', alpha=0.3)

# Orientation
ax = axes[0, 1]
bars = ax.bar(range(len(orientation_funding)), orientation_funding.values,
              color=[COLORS['primary'], COLORS['accent']])
ax.set_xticks(range(len(orientation_funding)))
ax.set_xticklabels(orientation_funding.index, rotation=45, ha='right', fontsize=10)
ax.set_ylabel('Total Funding', fontsize=11, fontweight='bold')
ax.set_title('By Orientation', fontsize=12, fontweight='bold')
ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='y', alpha=0.3)

# Research Stage (if available)
ax = axes[1, 0]
if len(research_grants) > 0 and 's2_research_stage' in research_grants.columns:
    stage_funding_plot = stage_funding.head(3)
    bars = ax.bar(range(len(stage_funding_plot)), stage_funding_plot.values,
                  color=[COLORS['success'], COLORS['warning'], COLORS['secondary']])
    ax.set_xticks(range(len(stage_funding_plot)))
    ax.set_xticklabels([x.replace(' ', '\n') for x in stage_funding_plot.index], 
                       rotation=0, ha='center', fontsize=9)
    ax.set_ylabel('Total Funding', fontsize=11, fontweight='bold')
    ax.set_title('By Research Stage\n(Research Grants)', fontsize=12, fontweight='bold')
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.grid(True, axis='y', alpha=0.3)
else:
    ax.text(0.5, 0.5, 'No Research Stage Data', ha='center', va='center', 
           fontsize=12, transform=ax.transAxes)
    ax.axis('off')

# Application Area (Top 5)
ax = axes[1, 1]
app_area_top5 = app_area_funding.head(5)
bars = ax.barh(range(len(app_area_top5)), app_area_top5.values,
               color=sns.color_palette("coolwarm", len(app_area_top5)))
ax.set_yticks(range(len(app_area_top5)))
app_labels = [label[:30] + '...' if len(label) > 30 else label for label in app_area_top5.index]
ax.set_yticklabels(app_labels, fontsize=9)
ax.set_xlabel('Total Funding', fontsize=11, fontweight='bold')
ax.set_title('By Application Area (Top 5)', fontsize=12, fontweight='bold')
ax.xaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.grid(True, axis='x', alpha=0.3)
ax.invert_yaxis()

plt.tight_layout()
save_plot('12_comprehensive_breakdown.png', dpi=200)

# =============================================================================
# 9. SPECIAL ANALYSIS: USE-INSPIRED & BENCH SCALE CHARACTERISTICS
# =============================================================================
print("\nAnalyzing Use-Inspired Research and Bench Scale Tech Development...")

# Filter to Use-Inspired Research and Bench Scale Tech Development
target_stages = ['Use Inspired Research', 'Bench Scale Tech Development']
target_grants = df[df['s2_research_stage'].isin(target_stages)].copy()

print(f"\nUse-Inspired Research & Bench Scale Tech Development:")
print(f"  Total grants: {len(target_grants):,}")
print(f"  Total funding: {format_currency(target_grants['award_amount'].sum())}")

# Analysis 1: Collaborative approach breakdown
print("\n--- ANALYSIS 1: COLLABORATIVE APPROACH ---")

# Filter to public_facing research (where research_approach is classified)
target_public = target_grants[
    (target_grants['s2_orientation'] == 'public_facing') &
    (target_grants['s2_research_approach'].notna())
].copy()

print(f"\nPublic-facing grants with research_approach classified: {len(target_public):,}")

for stage in target_stages:
    stage_grants = target_public[target_public['s2_research_stage'] == stage].copy()
    
    if len(stage_grants) == 0:
        continue
    
    print(f"\n{stage}:")
    print(f"  Total: {len(stage_grants):,} grants, {format_currency(stage_grants['award_amount'].sum())}")
    
    collab_count = (stage_grants['s2_research_approach'] == 'collaborative_interdisciplinary').sum()
    single_count = (stage_grants['s2_research_approach'] == 'single_focus').sum()
    
    collab_funding = stage_grants[stage_grants['s2_research_approach'] == 'collaborative_interdisciplinary']['award_amount'].sum()
    single_funding = stage_grants[stage_grants['s2_research_approach'] == 'single_focus']['award_amount'].sum()
    
    total_stage = len(stage_grants)
    total_stage_funding = stage_grants['award_amount'].sum()
    
    print(f"  Collaborative Interdisciplinary: {collab_count:,} ({collab_count/total_stage*100:.1f}%)")
    print(f"    Funding: {format_currency(collab_funding)} ({collab_funding/total_stage_funding*100:.1f}%)")
    print(f"  Single Focus: {single_count:,} ({single_count/total_stage*100:.1f}%)")
    print(f"    Funding: {format_currency(single_funding)} ({single_funding/total_stage_funding*100:.1f}%)")

# Analysis 2: Industry Framing (TEA/LCA translational research)
print("\n--- ANALYSIS 2: INDUSTRY FRAMING (TEA/LCA-INFORMED) ---")

# Check if industry_framing column exists
if 'industry_framing' not in target_grants.columns:
    print("⚠️  WARNING: 'industry_framing' column not found!")
    print("   Run add_industry_framing.py first to add this column.")
    print("   Skipping industry framing analysis...")
else:
    for stage in target_stages:
        stage_grants = target_grants[target_grants['s2_research_stage'] == stage].copy()
        
        if len(stage_grants) == 0:
            continue
        
        total_stage = len(stage_grants)
        total_stage_funding = stage_grants['award_amount'].sum()
        
        # Count grants with industry framing
        industry_framing_count = (stage_grants['industry_framing'] == True).sum()
        no_framing_count = (stage_grants['industry_framing'] == False).sum()
        
        # Calculate funding
        industry_framing_funding = stage_grants[stage_grants['industry_framing'] == True]['award_amount'].sum()
        no_framing_funding = stage_grants[stage_grants['industry_framing'] == False]['award_amount'].sum()
        
        print(f"\n{stage}:")
        print(f"  Total: {total_stage:,} grants, {format_currency(total_stage_funding)}")
        print(f"  Industry Framing (TEA/LCA/etc.): {industry_framing_count:,} ({industry_framing_count/total_stage*100:.1f}%)")
        print(f"    Funding: {format_currency(industry_framing_funding)} ({industry_framing_funding/total_stage_funding*100 if total_stage_funding > 0 else 0:.1f}%)")
        print(f"  No Industry Framing: {no_framing_count:,} ({no_framing_count/total_stage*100:.1f}%)")
        print(f"    Funding: {format_currency(no_framing_funding)} ({no_framing_funding/total_stage_funding*100 if total_stage_funding > 0 else 0:.1f}%)")

# Create visualization for these analyses
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('Use-Inspired Research & Bench Scale Tech Development\nSpecial Characteristics', 
             fontsize=16, fontweight='bold', y=0.995)

# Plot 1: Collaborative approach by stage
ax = axes[0, 0]
stage_names = []
collab_pcts = []
single_pcts = []

for stage in target_stages:
    stage_grants = target_public[target_public['s2_research_stage'] == stage].copy()
    if len(stage_grants) > 0:
        stage_names.append(stage.replace(' ', '\n'))
        collab_pct = (stage_grants['s2_research_approach'] == 'collaborative_interdisciplinary').sum() / len(stage_grants) * 100
        single_pct = (stage_grants['s2_research_approach'] == 'single_focus').sum() / len(stage_grants) * 100
        collab_pcts.append(collab_pct)
        single_pcts.append(single_pct)

x = np.arange(len(stage_names))
width = 0.35

bars1 = ax.bar(x - width/2, collab_pcts, width, label='Collaborative\nInterdisciplinary', 
               color=COLORS['primary'])
bars2 = ax.bar(x + width/2, single_pcts, width, label='Single Focus', 
               color=COLORS['accent'])

ax.set_ylabel('Percentage of Grants (%)', fontsize=11, fontweight='bold')
ax.set_title('Research Approach Distribution\n(Public-Facing Grants)', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(stage_names, fontsize=9)
ax.legend(loc='upper right')
ax.grid(True, axis='y', alpha=0.3)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

# Plot 2: Industry Framing by stage
ax = axes[0, 1]

if 'industry_framing' in target_grants.columns:
    stage_names_framing = []
    framing_pcts = []
    no_framing_pcts = []
    
    for stage in target_stages:
        stage_grants = target_grants[target_grants['s2_research_stage'] == stage].copy()
        if len(stage_grants) > 0:
            stage_names_framing.append(stage.replace(' ', '\n'))
            framing_pct = (stage_grants['industry_framing'] == True).sum() / len(stage_grants) * 100
            no_framing_pct = (stage_grants['industry_framing'] == False).sum() / len(stage_grants) * 100
            framing_pcts.append(framing_pct)
            no_framing_pcts.append(no_framing_pct)
    
    x = np.arange(len(stage_names_framing))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, framing_pcts, width, label='Industry Framing\n(TEA/LCA/etc.)', 
                   color=COLORS['success'])
    bars2 = ax.bar(x + width/2, no_framing_pcts, width, label='No Industry Framing', 
                   color=COLORS['neutral'])
    
    ax.set_ylabel('Percentage of Grants (%)', fontsize=11, fontweight='bold')
    ax.set_title('Industry Framing Indicators\n(18 Approved Keywords)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(stage_names_framing, fontsize=9)
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
else:
    ax.text(0.5, 0.5, 'Run add_industry_framing.py first', 
            ha='center', va='center', transform=ax.transAxes, fontsize=12)
    ax.set_title('Industry Framing - Column Not Found', fontsize=12, fontweight='bold')

# Plot 3: Funding by collaborative approach
ax = axes[1, 0]
stage_names_fund = []
collab_funds = []
single_funds = []

for stage in target_stages:
    stage_grants = target_public[target_public['s2_research_stage'] == stage].copy()
    if len(stage_grants) > 0:
        stage_names_fund.append(stage.replace(' ', '\n'))
        collab_fund = stage_grants[stage_grants['s2_research_approach'] == 'collaborative_interdisciplinary']['award_amount'].sum()
        single_fund = stage_grants[stage_grants['s2_research_approach'] == 'single_focus']['award_amount'].sum()
        collab_funds.append(collab_fund)
        single_funds.append(single_fund)

x = np.arange(len(stage_names_fund))
width = 0.35

bars1 = ax.bar(x - width/2, collab_funds, width, label='Collaborative\nInterdisciplinary', 
               color=COLORS['primary'])
bars2 = ax.bar(x + width/2, single_funds, width, label='Single Focus', 
               color=COLORS['accent'])

ax.set_ylabel('Total Funding', fontsize=11, fontweight='bold')
ax.set_title('Funding by Research Approach\n(Public-Facing Grants)', fontsize=12, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(stage_names_fund, fontsize=9)
ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
ax.legend(loc='upper right')
ax.grid(True, axis='y', alpha=0.3)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    format_currency(height), ha='center', va='bottom', 
                    fontsize=8, rotation=0)

# Plot 4: Funding by Industry Framing
ax = axes[1, 1]

if 'industry_framing' in target_grants.columns:
    stage_names_framing_fund = []
    framing_funds = []
    no_framing_funds = []
    
    for stage in target_stages:
        stage_grants = target_grants[target_grants['s2_research_stage'] == stage].copy()
        if len(stage_grants) > 0:
            stage_names_framing_fund.append(stage.replace(' ', '\n'))
            framing_fund = stage_grants[stage_grants['industry_framing'] == True]['award_amount'].sum()
            no_framing_fund = stage_grants[stage_grants['industry_framing'] == False]['award_amount'].sum()
            framing_funds.append(framing_fund)
            no_framing_funds.append(no_framing_fund)
    
    x = np.arange(len(stage_names_framing_fund))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, framing_funds, width, label='Industry Framing', 
                   color=COLORS['success'])
    bars2 = ax.bar(x + width/2, no_framing_funds, width, label='No Industry Framing', 
                   color=COLORS['neutral'])
    
    ax.set_ylabel('Total Funding', fontsize=11, fontweight='bold')
    ax.set_title('Funding by Industry Framing\n(TEA/LCA/Cost Analysis/etc.)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(stage_names_framing_fund, fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(millions_formatter))
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        format_currency(height), ha='center', va='bottom', 
                        fontsize=8, rotation=0)
else:
    ax.text(0.5, 0.5, 'Run add_industry_framing.py first', 
            ha='center', va='center', transform=ax.transAxes, fontsize=12)
    ax.set_title('Industry Framing Funding - Column Not Found', fontsize=12, fontweight='bold')

plt.tight_layout()
save_plot('13_use_inspired_bench_scale_characteristics.png', dpi=200)

# =============================================================================
# 10. EXPORT SUMMARY STATISTICS
# =============================================================================
print("\nExporting summary statistics...")

summary_stats = []

# Overall
summary_stats.append({
    'Category': 'OVERALL',
    'Subcategory': 'All Grants',
    'Grant_Count': total_grants,
    'Total_Funding': total_funding,
    'Average_Grant': avg_grant
})

# By Grant Type
for grant_type in grant_type_funding.index:
    if pd.notna(grant_type):
        subset = df[df['s2_grant_type'] == grant_type]
        summary_stats.append({
            'Category': 'Grant Type',
            'Subcategory': grant_type,
            'Grant_Count': len(subset),
            'Total_Funding': subset['award_amount'].sum(),
            'Average_Grant': subset['award_amount'].mean()
        })

# By Orientation
for orientation in orientation_funding.index:
    if pd.notna(orientation):
        subset = df[df['s2_orientation'] == orientation]
        summary_stats.append({
            'Category': 'Orientation',
            'Subcategory': orientation,
            'Grant_Count': len(subset),
            'Total_Funding': subset['award_amount'].sum(),
            'Average_Grant': subset['award_amount'].mean()
        })

# By Research Stage
if len(research_grants) > 0:
    for stage in stage_funding.index:
        if pd.notna(stage):
            subset = research_grants[research_grants['s2_research_stage'] == stage]
            summary_stats.append({
                'Category': 'Research Stage',
                'Subcategory': stage,
                'Grant_Count': len(subset),
                'Total_Funding': subset['award_amount'].sum(),
                'Average_Grant': subset['award_amount'].mean()
            })

# By Research Approach
if len(public_research) > 0:
    for approach in approach_funding.index:
        if pd.notna(approach):
            subset = public_research[public_research['s2_research_approach'] == approach]
            summary_stats.append({
                'Category': 'Research Approach',
                'Subcategory': approach,
                'Grant_Count': len(subset),
                'Total_Funding': subset['award_amount'].sum(),
                'Average_Grant': subset['award_amount'].mean()
            })

summary_df = pd.DataFrame(summary_stats)
summary_file = os.path.join(OUTPUT_DIR, 'funding_summary_statistics.csv')
summary_df.to_csv(summary_file, index=False)
print(f"✓ Saved: funding_summary_statistics.csv")

# =============================================================================
# COMPLETION
# =============================================================================
print()
print("="*80)
print("VISUALIZATION COMPLETE")
print("="*80)
print(f"\nAll visualizations saved to: {OUTPUT_DIR}")
print("\nGenerated plots:")
print("  01. Overall funding trends (time series)")
print("  02. Funding by grant type (bar chart)")
print("  03. Funding trends by grant type (time series)")
print("  04. Funding by orientation (bar chart)")
print("  05. Funding trends by orientation (time series)")
print("  06. Funding by research stage (bar chart)")
print("  07. Funding trends by research stage (time series)")
print("  08. Funding by research approach (bar chart)")
print("  09. Funding trends by research approach (time series)")
print("  10. Funding by application area - Top 10 (horizontal bar)")
print("  11. Funding by top funders - Top 10 (horizontal bar)")
print("  12. Comprehensive breakdown (4-panel)")
print("  13. Use-Inspired & Bench Scale characteristics (4-panel) **NEW**")
print("\nSummary statistics:")
print("  - funding_summary_statistics.csv")
print()
