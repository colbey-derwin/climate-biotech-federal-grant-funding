#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_sankey_FUNDING_VERSION.py

Funding-based version of the Sankey diagram.
Shows % of FUNDING AMOUNT instead of % of grant count.

Usage:
  python generate_sankey_FUNDING_VERSION.py

Output:
  climate_biotech_sankey_funding.html
"""

import os
import json
import re
import pandas as pd
from pathlib import Path

# =============================================================================
# PATHS - CONFIGURED FOR PROJECT STRUCTURE
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent  # visualization/
PROJECT_ROOT = SCRIPT_DIR.parent              # climate_biotech_federal_grant_funding/

OUTPUT_DIR = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

INFILE = OUTPUT_DIR / "stage2_characterized_all_years_with_industry_framing.csv"
OUTFILE = SCRIPT_DIR / "climate_biotech_sankey_funding.html"

# =============================================================================
# LOAD AND PROCESS DATA
# =============================================================================

# Open Access / Sharing Keywords
SHARING_KEYWORDS = [
    # Open access
    "open access",
    "open-access",
    "openly available",
    "publicly available",
    "public access",
    "free access",
    
    # Shared resources
    "shared facility",
    "shared platform",
    "shared resource",
    "shared database",
    "shared infrastructure",
    "community resource",
    "community facility",
    "community platform",
    
    # Data sharing
    "data sharing",
    "data repository",
    "open data",
    "open source",
    "open-source",
    
    # Availability language
    "available to researchers",
    "available to the community",
    "available to the public",
    "made available",
    "will be shared",
    "will be made available",
    
    # Collaborative access
    "collaborative facility",
    "multi-user facility",
    "user facility",
    "shared access",
]

def get_grant_category(row: pd.Series) -> str:
    """
    Determine the grant category for LEFT side of Sankey.
    """
    grant_type = row.get('s2_grant_type')
    orientation = row.get('s2_orientation')
    research_stage = row.get('s2_research_stage')
    
    if grant_type == 'research':
        if orientation == 'public_facing':
            stage_mapping = {
                'Use Inspired Research': 'Use Inspired Research',
                'Bench Scale Tech Development': 'Bench Scale Tech Development',
                'Piloting': 'Piloting'
            }
            return stage_mapping.get(research_stage, 'Public Research (Other)')
        else:
            return 'Industry-Facing Research'
    elif grant_type == 'deployment':
        return 'Deployment'
    elif grant_type == 'infrastructure':
        return 'Infrastructure'
    elif grant_type == 'other':
        return 'Other'
    else:
        return 'Other'

def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    return text

def has_sharing_keyword(abstract: str, keywords: list) -> bool:
    """
    Check if abstract contains any sharing/open access keyword.
    Case-insensitive matching with word boundaries.
    """
    if pd.isna(abstract):
        return False
    
    normalized = normalize_text(abstract)
    
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        # Use word boundaries to prevent matching within words
        pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
        
        if re.search(pattern, normalized):
            return True
    
    return False

print("Loading data...")
df = pd.read_csv(INFILE, low_memory=False)
print(f"✓ Loaded {len(df):,} grants")

# Create grant_category column
print("\nCreating grant_category column...")
df['grant_category'] = df.apply(get_grant_category, axis=1)
print("✓ grant_category created")

# Define nodes in order
left_nodes = [
    'Use Inspired Research',
    'Bench Scale Tech Development',
    'Piloting',
    'Deployment',
    'Industry-Facing Research',
    'Infrastructure',
    'Other'
]

right_nodes = [
    'Industry-Relevant Language',
    'Collaborative Interdisciplinary',
    'Single-Discipline',
    'Open Access/Sharing'
]

print("\nCreating right_side_categories (grants can have MULTIPLE characteristics)...")

# Initialize columns for each characteristic
for node in right_nodes:
    df[f'has_{node.replace(" ", "_").replace("-", "_").replace("/", "_").lower()}'] = False

# Tag grants with ALL applicable characteristics
for idx, row in df.iterrows():
    # Industry-Relevant Language
    # Deployment grants are ALWAYS industry-relevant (100%)
    is_deployment = (row.get('s2_grant_type') == 'deployment')
    is_industry = (row.get('industry_framing') == True) or (row.get('s2_orientation') == 'industry_facing')
    
    if is_deployment or is_industry:
        df.at[idx, 'has_industry_relevant_language'] = True
    
    # Collaborative Interdisciplinary
    if row.get('s2_research_approach') == 'collaborative_interdisciplinary':
        df.at[idx, 'has_collaborative_interdisciplinary'] = True
    
    # Single-Discipline
    if row.get('s2_research_approach') == 'single_focus':
        df.at[idx, 'has_single_discipline'] = True
    
    # Open Access/Sharing
    if has_sharing_keyword(row.get('abstract', ''), SHARING_KEYWORDS):
        df.at[idx, 'has_open_access_sharing'] = True

print("✓ Characteristic tagging complete")
print("\nCharacteristic distribution (grants can have multiple):")
print(f"  Industry-Relevant Language: {df['has_industry_relevant_language'].sum()} grants")
print(f"  Collaborative Interdisciplinary: {df['has_collaborative_interdisciplinary'].sum()} grants")
print(f"  Single-Discipline: {df['has_single_discipline'].sum()} grants")
print(f"  Open Access/Sharing: {df['has_open_access_sharing'].sum()} grants")
print()

# Colors
left_colors = {
    'Use Inspired Research': '#4472C4',
    'Bench Scale Tech Development': '#5B9BD5',
    'Piloting': '#70AD47',
    'Deployment': '#ED7D31',
    'Industry-Facing Research': '#FFC000',
    'Infrastructure': '#A5A5A5',
    'Other': '#7F7F7F'
}

right_colors = {
    'Industry-Relevant Language': '#C5E0B4',
    'Collaborative Interdisciplinary': '#9DC3E6',
    'Single-Discipline': '#D5A6BD',
    'Open Access/Sharing': '#F4B183'
}

# Build links - FUNDING VERSION (sum award amounts)
print("Processing links (grants can flow to multiple categories)...")
link_map = {}

for _, row in df.iterrows():
    source = row.get('grant_category')
    funding = row.get('award_amount', 0)
    
    if pd.isna(funding) or funding <= 0 or source not in left_nodes:
        continue
    
    # Check each characteristic and create flow if present
    # FUNDING: Each grant adds its award_amount to the flow
    if row.get('has_industry_relevant_language'):
        key = f"{source}→Industry-Relevant Language"
        link_map[key] = link_map.get(key, 0) + funding
    
    if row.get('has_collaborative_interdisciplinary'):
        key = f"{source}→Collaborative Interdisciplinary"
        link_map[key] = link_map.get(key, 0) + funding
    
    if row.get('has_single_discipline'):
        key = f"{source}→Single-Discipline"
        link_map[key] = link_map.get(key, 0) + funding
    
    if row.get('has_open_access_sharing'):
        key = f"{source}→Open Access/Sharing"
        link_map[key] = link_map.get(key, 0) + funding

links = [{'source': k.split('→')[0], 'target': k.split('→')[1], 'value': v} 
         for k, v in link_map.items()]

print(f"✓ Created {len(links)} links")

# Calculate actual funding totals for each left-side category
# IMPORTANT: Match flow calculation - only count positive amounts
left_node_totals = {}
for node_name in left_nodes:
    # Only sum positive amounts (matching the flow calculation logic)
    node_data = df[(df['grant_category'] == node_name) & 
                   (df['award_amount'].notna()) & 
                   (df['award_amount'] > 0)]
    total = node_data['award_amount'].sum()
    left_node_totals[node_name] = total
    print(f"  {node_name}: ${total:,.0f} actual funding")

# Verify flows
print("\n" + "="*80)
print("FLOW VERIFICATION (FUNDING):")
print("="*80)
for source_name in left_nodes:
    source_total = left_node_totals[source_name]
    if source_total == 0:
        continue
    
    source_links = [l for l in links if l['source'] == source_name]
    total_outflow = sum(l['value'] for l in source_links)
    pct = (total_outflow / source_total) * 100
    
    print(f"\n{source_name}:")
    print(f"  Total funding: ${source_total:,.0f}")
    print(f"  Total flows: ${total_outflow:,.0f} ({pct:.1f}%)")
    
    for link in source_links:
        link_amount = link['value']
        print(f"    → {link['target']}: ${link_amount:,.0f}")

# Build nodes WITH actualTotal property
nodes = []
for name in left_nodes + right_nodes:
    color = left_colors.get(name, right_colors.get(name, '#999'))
    node = {'name': name, 'color': color}
    if name in left_node_totals:
        node['actualTotal'] = left_node_totals[name]
    nodes.append(node)

# =============================================================================
# GENERATE HTML
# =============================================================================

html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Climate Biotech Funding Flow</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
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
            max-width: 1400px;
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
        
        .section-title {
            font-size: 16px;
            font-weight: bold;
            fill: #333;
        }
        
        .link {
            fill: none;
            stroke-opacity: 0.3;
        }
        
        .link:hover {
            stroke-opacity: 0.7;
        }
        
        .node rect {
            cursor: pointer;
            stroke: none;
        }
        
        .node text {
            font-size: 13px;
            fill: #333;
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
        
        .bracket {
            fill: none;
            stroke: #666;
            stroke-width: 2;
        }
        
        .bracket-label {
            font-size: 14px;
            font-weight: bold;
            fill: #666;
        }
    </style>
</head>
<body>
    <div id="chart">
        <div class="chart-title">Climate Biotech Federal Grant Flow by Funding (2019-2025)</div>
        <div class="chart-subtitle">Shows distribution of funding amount across grant types and characteristics</div>
        <svg id="sankey"></svg>
    </div>
    <div id="tooltip"></div>
    
    <script>
        const nodesData = {{NODES_DATA}};
        const linksData = {{LINKS_DATA}};
        
        const margin = {top: 60, right: 250, bottom: 20, left: 350};
        const width = 1200 - margin.left - margin.right;
        const height = 700 - margin.top - margin.bottom;
        
        const svg = d3.select("#sankey")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
        
        // Add section titles
        svg.append("text")
            .attr("class", "section-title")
            .attr("x", -40)
            .attr("y", -30)
            .attr("text-anchor", "middle")
            .text("Grant Type");
        
        svg.append("text")
            .attr("class", "section-title")
            .attr("x", width + 40)
            .attr("y", -30)
            .attr("text-anchor", "middle")
            .text("Grant Characteristic");
        
        // Tooltip
        const tooltip = d3.select("#tooltip");
        
        // Create Sankey generator
        const sankey = d3.sankey()
            .nodeId(d => d.name)
            .nodeWidth(18)
            .nodePadding(60)
            .extent([[0, 0], [width, height]]);
        
        const {nodes, links} = sankey({
            nodes: nodesData.map(d => Object.assign({}, d)),
            links: linksData.map(d => Object.assign({}, d))
        });
        
        // FORCE correct vertical order
        const leftNodeNames = [
            'Use Inspired Research',
            'Bench Scale Tech Development',
            'Piloting',
            'Deployment',
            'Industry-Facing Research',
            'Infrastructure',
            'Other'
        ];
        
        const rightNodeNames = [
            'Industry-Relevant Language',
            'Collaborative Interdisciplinary',
            'Single-Discipline',
            'Open Access/Sharing'
        ];
        
        // Research group (first 3 nodes)
        const researchGroup = ['Use Inspired Research', 'Bench Scale Tech Development', 'Piloting'];
        
        nodes.sort((a, b) => {
            const aIsLeft = leftNodeNames.includes(a.name);
            const bIsLeft = leftNodeNames.includes(b.name);
            
            if (aIsLeft && bIsLeft) {
                return leftNodeNames.indexOf(a.name) - leftNodeNames.indexOf(b.name);
            }
            if (!aIsLeft && !bIsLeft) {
                return rightNodeNames.indexOf(a.name) - rightNodeNames.indexOf(b.name);
            }
            return aIsLeft ? -1 : 1;
        });
        
        // Reposition nodes vertically
        const leftNodes = nodes.filter(n => leftNodeNames.includes(n.name));
        const rightNodes = nodes.filter(n => rightNodeNames.includes(n.name));
        
        let currentY = 0;
        leftNodes.forEach(node => {
            const nodeHeight = node.y1 - node.y0;
            node.y0 = currentY;
            node.y1 = currentY + nodeHeight;
            currentY = node.y1 + 60;
        });
        
        currentY = 0;
        rightNodes.forEach(node => {
            const nodeHeight = node.y1 - node.y0;
            node.y0 = currentY;
            node.y1 = currentY + nodeHeight;
            currentY = node.y1 + 60;
        });
        
        // Recalculate link paths
        sankey.update({nodes, links});
        
        // Draw bracket for Research group
        const researchNodes = leftNodes.filter(n => researchGroup.includes(n.name));
        if (researchNodes.length > 0) {
            const topY = researchNodes[0].y0;
            const bottomY = researchNodes[researchNodes.length - 1].y1;
            
            // Position bracket to the LEFT of the labels
            const labelMaxX = Math.min(...researchNodes.map(n => n.x0)) - 9;
            const bracketX = labelMaxX - 200;
            const bracketWidth = 15;
            
            // Draw bracket path
            const bracketPath = `
                M ${bracketX + bracketWidth} ${topY}
                L ${bracketX} ${topY}
                L ${bracketX} ${bottomY}
                L ${bracketX + bracketWidth} ${bottomY}
            `;
            
            svg.append("path")
                .attr("class", "bracket")
                .attr("d", bracketPath);
            
            // Add "Public-Facing Research" label (two lines)
            svg.append("text")
                .attr("class", "bracket-label")
                .attr("x", bracketX - 10)
                .attr("y", (topY + bottomY) / 2 - 10)
                .attr("text-anchor", "end")
                .attr("dominant-baseline", "middle")
                .text("Public-Facing");
            
            svg.append("text")
                .attr("class", "bracket-label")
                .attr("x", bracketX - 10)
                .attr("y", (topY + bottomY) / 2 + 10)
                .attr("text-anchor", "end")
                .attr("dominant-baseline", "middle")
                .text("Research");
        }
        
        // Draw links
        svg.append("g")
            .selectAll(".link")
            .data(links)
            .join("path")
            .attr("class", "link")
            .attr("d", d3.sankeyLinkHorizontal())
            .attr("stroke", d => d.source.color || "#999")
            .attr("stroke-width", d => Math.max(1, d.width))
            .on("mouseover", function(event, d) {
                const value = d.value;
                const formattedValue = value >= 1e9 ? `$${(value/1e9).toFixed(1)}B` :
                                      value >= 1e6 ? `$${(value/1e6).toFixed(1)}M` :
                                      `$${(value/1e3).toFixed(1)}K`;
                
                const sourceTotal = d.source.actualTotal || d.source.sourceLinks.reduce((sum, l) => sum + l.value, 0);
                const pct = ((d.value / sourceTotal) * 100).toFixed(1);
                
                tooltip.style("opacity", 1)
                    .html(`${d.source.name} → ${d.target.name}<br>${formattedValue} (${pct}% of ${d.source.name})`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 20) + "px");
            })
            .on("mouseout", () => tooltip.style("opacity", 0));
        
       // Draw nodes
        const node = svg.append("g")
            .selectAll(".node")
            .data(nodes)
            .join("g")
            .attr("class", "node");
        
        node.append("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("height", d => d.y1 - d.y0)
            .attr("width", d => d.x1 - d.x0)
            .attr("fill", d => d.color)
            .on("mouseover", function(event, d) {
                // Show tooltip with total funding for this node
                if (d.actualTotal !== undefined) {
                    const formattedValue = d.actualTotal >= 1e9 ? `$${(d.actualTotal/1e9).toFixed(1)}B` :
                                          d.actualTotal >= 1e6 ? `$${(d.actualTotal/1e6).toFixed(1)}M` :
                                          `$${(d.actualTotal/1e3).toFixed(1)}K`;
                    
                    tooltip.style("opacity", 1)
                        .html(`${d.name}<br>${formattedValue} total funding`)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 20) + "px");
                }
            })
            .on("mouseout", () => tooltip.style("opacity", 0));
        
        // Add labels OUTSIDE the bars
        node.append("text")
            .attr("x", d => d.x0 < width / 2 ? d.x0 - 8 : d.x1 + 8)
            .attr("y", d => (d.y1 + d.y0) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", d => d.x0 < width / 2 ? "end" : "start")
            .text(d => d.name)
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                // Show tooltip with total funding for this node
                if (d.actualTotal !== undefined) {
                    const formattedValue = d.actualTotal >= 1e9 ? `$${(d.actualTotal/1e9).toFixed(1)}B` :
                                          d.actualTotal >= 1e6 ? `$${(d.actualTotal/1e6).toFixed(1)}M` :
                                          `$${(d.actualTotal/1e3).toFixed(1)}K`;
                    
                    tooltip.style("opacity", 1)
                        .html(`${d.name}<br>${formattedValue} total funding`)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 20) + "px");
                }
            })
            .on("mouseout", () => tooltip.style("opacity", 0));
    </script>
</body>
</html>
"""

# Embed data
html = html_template.replace('{{NODES_DATA}}', json.dumps(nodes))
html = html.replace('{{LINKS_DATA}}', json.dumps(links))

# Save
print(f"\nSaving: {OUTFILE}")
os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
with open(OUTFILE, 'w') as f:
    f.write(html)

print(f"✓ Saved: {OUTFILE}")
print("\n" + "="*80)
print("FUNDING-BASED SANKEY GENERATED")
print("="*80)
print("\nChanges from count version:")
print("  ✓ Shows FUNDING AMOUNT instead of grant count")
print("  ✓ Percentages reflect % of funding amount")
print("  ✓ Tooltips show '$N' instead of 'N grants'")
print("  ✓ Title indicates 'by Funding'")
print()
