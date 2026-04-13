#!/usr/bin/env python3
"""
Generate research stage funding flow visualization.
Flowing streams with space between each category.

Usage:
    python generate_research_stage_flow.py
"""

import pandas as pd
import json
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent  # visualization/
PROJECT_ROOT = SCRIPT_DIR.parent              # climate_biotech_federal_grant_funding/

OUTPUT_DIR_CLASSIFIER = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

DATA_FILE = OUTPUT_DIR_CLASSIFIER / "stage2_characterized_all_years_with_industry_framing.csv"
OUTPUT_FILE = SCRIPT_DIR / "research_stage_funding_flow.html"

# Category mapping for legacy/incorrect category names
CATEGORY_MAPPING = {
    'sustainable_agriculture': 'crop_productivity_traditional',
    'bioenergy': 'biogas_gaseous_energy',
    'biochemicals': 'platform_biochemicals',
    'biomaterials': 'biopolymers_materials',
    'alternative_protein': 'specialty_bioproducts',
    'carbon_capture_sequestration': 'biological_carbon_capture',
    'environmental_monitoring': 'ecosystem_monitoring',
    'pollution_remediation': 'pollution_degradation_remediation',
}

# Stage order - EXACT names from CSV
STAGE_ORDER = [
    'Use Inspired Research',
    'Bench Scale Tech Development',
    'Piloting',
    'Deployment'
]

def process_data(filepath):
    """Load and process data."""
    df = pd.read_csv(filepath)
    
    # Fix legacy/incorrect category names
    df['s2_application_area'] = df['s2_application_area'].replace(CATEGORY_MAPPING)
    
    # Filter to match Sankey logic: ALL research OR deployment
    # AND exclude negative/zero amounts
    df = df[
        (
            (df['s2_grant_type'] == 'research') |
            (df['s2_grant_type'] == 'deployment')
        ) &
        (df['award_amount'].notna()) &
        (df['award_amount'] > 0)
    ].copy()
    
    # Create unified stage
    def get_unified_stage(row):
        if row['s2_grant_type'] == 'deployment':
            return 'Deployment'
        elif row['s2_grant_type'] == 'research':
            return row['s2_research_stage']
        return None
    
    df['unified_stage'] = df.apply(get_unified_stage, axis=1)
    df = df[df['unified_stage'].notna()].copy()
    
    # Group by stage and category - KEEP ORIGINAL NAMES
    grouped = df.groupby(['unified_stage', 's2_application_area'])['award_amount'].sum().reset_index()
    grouped.columns = ['stage', 'category', 'amount']
    
    return grouped

def generate_html(data):
    """Generate HTML visualization."""
    
    data_json = data.to_json(orient='records')
    stages_json = json.dumps(STAGE_ORDER)
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Federal Climate Biotech Research Stage Funding Flow</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        
        #chart {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .chart-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
            text-align: center;
        }
        
        .chart-subtitle {
            font-size: 14px;
            color: #666;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .stream {
            opacity: 0.7;
            transition: opacity 0.3s ease;
            cursor: pointer;
        }
        
        .stream:hover {
            opacity: 1;
        }
        
        .stage-label {
            font-size: 14px;
            font-weight: bold;
            fill: #333;
            text-anchor: middle;
        }
        
        .stage-amount {
            font-size: 12px;
            fill: #666;
            text-anchor: middle;
        }
        
        .stage-line {
            stroke: #ddd;
            stroke-width: 1;
            stroke-dasharray: 3, 3;
        }
        
        #tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 10px 14px;
            border-radius: 4px;
            font-size: 13px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div id="chart">
        <div class="chart-title">Federal Climate Biotech Research Stage Funding Flow (2019-2025)</div>
        <div class="chart-subtitle">Federal grants (public-facing and industry-facing research) showing funding distribution across research stages</div>
        <svg id="sankey"></svg>
    </div>
    <div id="tooltip"></div>
    
    <script>
        const rawData = ''' + data_json + ''';
        const stages = ''' + stages_json + ''';
        
        // Get categories and sort by total funding (largest first)
        const categoryTotals = d3.rollup(rawData, v => d3.sum(v, d => d.amount), d => d.category);
        const categories = Array.from(categoryTotals.keys()).sort((a, b) => categoryTotals.get(b) - categoryTotals.get(a));
        
        // Color palette
        const colors = [
            '#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5',
            '#70AD47', '#264478', '#9E480E', '#636363', '#997300',
            '#255E91', '#43682B', '#698ED0', '#F1975A', '#B7B7B7',
            '#FFCD33'
        ];
        
        const colorScale = d3.scaleOrdinal()
            .domain(categories)
            .range(colors);
        
        // Calculate stage totals
        const stageTotals = {};
        stages.forEach(stage => {
            stageTotals[stage] = d3.sum(rawData.filter(d => d.stage === stage), d => d.amount);
        });
        
        // SVG setup
        const width = 1400;
        const height = 900;
        const margin = { top: 100, right: 200, bottom: 60, left: 250 };
        
        const svg = d3.select('#sankey')
            .attr('width', width)
            .attr('height', height);
        
        const tooltip = d3.select('#tooltip');
        
        // X scale for stages
        const xScale = d3.scalePoint()
            .domain(stages)
            .range([margin.left, width - margin.right])
            .padding(0.5);
        
        // Calculate max funding amount to scale thickness
        const maxAmount = d3.max(rawData, d => d.amount);
        
        // Height scale - each category gets equal vertical space
        const categoryHeight = (height - margin.top - margin.bottom) / categories.length;
        
        // Draw stage lines
        stages.forEach(stage => {
            const x = xScale(stage);
            svg.append('line')
                .attr('class', 'stage-line')
                .attr('x1', x)
                .attr('x2', x)
                .attr('y1', margin.top - 20)
                .attr('y2', height - margin.bottom + 20);
        });
        
        // Draw stage labels
        stages.forEach(stage => {
            const x = xScale(stage);
            const total = stageTotals[stage];
            const formattedTotal = total >= 1e9 ? '$' + (total/1e9).toFixed(1) + 'B' :
                                  total >= 1e6 ? '$' + (total/1e6).toFixed(1) + 'M' :
                                  '$' + (total/1e3).toFixed(1) + 'K';
            
            svg.append('text')
                .attr('class', 'stage-label')
                .attr('x', x)
                .attr('y', 40)
                .text(stage);
            
            svg.append('text')
                .attr('class', 'stage-amount')
                .attr('x', x)
                .attr('y', 60)
                .text(formattedTotal);
        });
        
        // Draw streams for each category - WITH SPACE BETWEEN
        categories.forEach((category, catIdx) => {
            const points = [];
            
            // Each category gets its own vertical position
            const baseY = margin.top + (catIdx * categoryHeight) + (categoryHeight / 2);
            
            stages.forEach(stage => {
                const x = xScale(stage);
                const dataPoint = rawData.find(d => d.category === category && d.stage === stage);
                const amount = dataPoint ? dataPoint.amount : 0;
                
                // Scale thickness based on amount - INCREASED for better visibility
                const thickness = (amount / maxAmount) * (categoryHeight * 1.2); // Increased from 0.8 to 1.2
                
                const y0 = baseY - thickness / 2;
                const y1 = baseY + thickness / 2;
                
                points.push({ x, y0, y1, amount, stage });
            });
            
            // Create smooth area path
            const area = d3.area()
                .x(d => d.x)
                .y0(d => d.y0)
                .y1(d => d.y1)
                .curve(d3.curveCatmullRom.alpha(0.5));
            
            svg.append('path')
                .datum(points)
                .attr('class', 'stream')
                .attr('fill', colorScale(category))
                .attr('d', area)
                .on('mouseover', function(event, d) {
                    const totalAmount = d3.sum(d, p => p.amount);
                    
                    let html = '<strong>' + category.replace(/_/g, ' ') + '</strong><br>';
                    d.forEach(p => {
                        if (p.amount > 0) {
                            const formattedValue = p.amount >= 1e9 ? '$' + (p.amount/1e9).toFixed(2) + 'B' :
                                                  p.amount >= 1e6 ? '$' + (p.amount/1e6).toFixed(1) + 'M' :
                                                  '$' + (p.amount/1e3).toFixed(1) + 'K';
                            html += p.stage + ': ' + formattedValue + '<br>';
                        }
                    });
                    const formattedTotal = totalAmount >= 1e9 ? '$' + (totalAmount/1e9).toFixed(2) + 'B' :
                                          totalAmount >= 1e6 ? '$' + (totalAmount/1e6).toFixed(1) + 'M' :
                                          '$' + (totalAmount/1e3).toFixed(1) + 'K';
                    html += '<br><strong>Total: ' + formattedTotal + '</strong>';
                    
                    tooltip.html(html)
                        .style('opacity', 1)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 10) + 'px');
                })
                .on('mouseout', function() {
                    tooltip.style('opacity', 0);
                });
            
            // Add category label on the left
            svg.append('text')
                .attr('x', 10)
                .attr('y', baseY)
                .attr('dominant-baseline', 'middle')
                .style('font-size', '12px')
                .style('fill', '#333')
                .style('font-weight', '500')
                .text(category.replace(/_/g, ' '));
        });
    </script>
</body>
</html>''';
    
    return html

def main():
    print(f"✓ Using data file: {DATA_FILE}")
    
    if not DATA_FILE.exists():
        print(f"\nERROR: Data file not found: {DATA_FILE}")
        return
    
    print("Processing data...")
    data = process_data(DATA_FILE)
    
    print(f"✓ Found {len(data['category'].unique())} categories across {len(STAGE_ORDER)} stages")
    print(f"✓ Total funding: ${data['amount'].sum() / 1e9:.2f}B")
    
    print("\nGenerating visualization...")
    html = generate_html(data)
    
    
   # Create output directory if it doesn't exist
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_FILE
    output_path.write_text(html)
    
    print(f"\n✓ Success!")
    print(f"  Saved: {output_path}")
    print(f"  Open in browser to view\n")

if __name__ == "__main__":
    main()
