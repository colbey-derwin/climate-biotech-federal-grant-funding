#!/usr/bin/env python3
"""
Simple Climate Biotech Report Generator

Just needs two CSV files:
1. stage2_characterized_all_years_with_industry_framing.csv (climate biotech grants)
2. merged_all_years.csv (ALL grants for comparison)

Generates a vertical-scroll report with:
- % of federal funding going to climate biotech
- Timeline trends by grant type
- Top funding agencies
- Links to your existing HTML visualizations
"""

import pandas as pd
import json
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent  # visualization/
PROJECT_ROOT = SCRIPT_DIR.parent              # climate_biotech_federal_grant_funding/

OUTPUT_DIR_CLASSIFIER = PROJECT_ROOT / "scripts" / "grant_classifier" / "output"

# Input files
CLASSIFIED_FILE = OUTPUT_DIR_CLASSIFIER / "stage2_characterized_all_years_with_industry_framing.csv"
ALL_GRANTS_FILE = OUTPUT_DIR_CLASSIFIER / "merged_all_years.csv"

# Output
OUTPUT_FILE = SCRIPT_DIR / "climate_biotech_report.html"

# Existing HTML visualizations (in same directory as this script)
VIZ_FILES = {
    'sankey_funding': 'climate_biotech_sankey_funding.html',
    'sankey_count': 'climate_biotech_sankey_count.html',
    'research_flow': 'research_stage_funding_flow.html',
    'derisked': 'derisked_categories_scatter.html'
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def format_currency(value):
    """Format currency values"""
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.1f}M"
    elif value >= 1e3:
        return f"${value/1e3:.0f}K"
    else:
        return f"${value:.0f}"

# =============================================================================
# LOAD AND ANALYZE DATA
# =============================================================================
print("Loading data...")
df_climate = pd.read_csv(CLASSIFIED_FILE, low_memory=False)
df_all = pd.read_csv(ALL_GRANTS_FILE, low_memory=False)

print(f"✓ Climate biotech grants: {len(df_climate):,}")
print(f"✓ Total grants: {len(df_all):,}")
print()

# Calculate summary stats
total_climate_funding = df_climate['award_amount'].sum()
total_all_funding = df_all['award_amount'].sum()
climate_share_pct = (total_climate_funding / total_all_funding * 100)

print("Summary Statistics:")
print(f"  Climate biotech funding: {format_currency(total_climate_funding)}")
print(f"  Total federal funding: {format_currency(total_all_funding)}")
print(f"  Climate biotech share: {climate_share_pct:.2f}%")
print()

# Year-by-year climate share
years = sorted(df_climate['year'].unique())
climate_by_year = df_climate.groupby('year')['award_amount'].sum()
all_by_year = df_all.groupby('year')['award_amount'].sum()
share_by_year = (climate_by_year / all_by_year * 100)

climate_share_data = {
    'years': [int(y) for y in years],
    'climate_funding': [float(climate_by_year[y]) for y in years],
    'all_funding': [float(all_by_year[y]) for y in years],
    'share_pct': [float(share_by_year[y]) for y in years]
}

# Timeline by grant type
timeline_data = {}
for grant_type in ['research', 'infrastructure', 'deployment', 'other']:
    type_by_year = df_climate[df_climate['s2_grant_type'] == grant_type].groupby('year')['award_amount'].sum()
    timeline_data[grant_type] = [float(type_by_year.get(y, 0)) for y in years]
timeline_data['years'] = [int(y) for y in years]

# Grant type breakdowns for Section 2 key finding
grant_type_totals = df_climate.groupby('s2_grant_type')['award_amount'].sum()
grant_type_pcts = (grant_type_totals / total_climate_funding * 100)

research_total = grant_type_totals.get('research', 0)
research_pct = grant_type_pcts.get('research', 0)
deployment_total = grant_type_totals.get('deployment', 0)
deployment_pct = grant_type_pcts.get('deployment', 0)
infrastructure_total = grant_type_totals.get('infrastructure', 0)
infrastructure_pct = grant_type_pcts.get('infrastructure', 0)
other_total = grant_type_totals.get('other', 0)
other_pct = grant_type_pcts.get('other', 0)

# Top 10 funding agencies (using correct column name from viz script)
top_agencies = df_climate.groupby('funder')['award_amount'].sum().sort_values(ascending=False).head(10)
agencies_data = {
    'agencies': list(top_agencies.index),
    'funding': [float(v) for v in top_agencies.values]
}

print("Generating report...")

# =============================================================================
# GENERATE HTML REPORT
# =============================================================================
html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Climate Biotech Federal Funding Analysis (2019-2025)</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2C3E50 0%, #34495E 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 3em;
            margin-bottom: 20px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.4em;
            opacity: 0.9;
        }}
        
        .toc {{
            background: #f8f9fa;
            padding: 40px;
            border-bottom: 3px solid #e9ecef;
        }}
        
        .toc h2 {{
            font-size: 2em;
            margin-bottom: 25px;
            color: #2C3E50;
        }}
        
        .toc-links {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        
        .toc-link {{
            padding: 15px 20px;
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 6px;
            text-decoration: none;
            color: #2C3E50;
            transition: all 0.3s ease;
            display: block;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .toc-link:hover {{
            transform: translateX(5px);
            border-left-color: #764ba2;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .section {{
            padding: 60px 40px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .section-title {{
            font-size: 2.5em;
            margin-bottom: 15px;
            color: #2C3E50;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        .section-number {{
            color: #667eea;
            font-weight: 700;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        
        .stat-label {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .explanation {{
            background: #fff3cd;
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            border-left: 5px solid #ffc107;
            font-size: 1.1em;
        }}
        
        .key-finding {{
            background: #d1ecf1;
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            border-left: 5px solid #17a2b8;
            font-size: 1.1em;
        }}
        
        .chart-container {{
            margin: 40px 0;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            min-height: 400px;
        }}
        
        .viz-button {{
            display: block;
            text-align: center;
            padding: 60px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 1.5em;
            font-weight: 600;
            transition: transform 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        
        .viz-button:hover {{
            transform: scale(1.02);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }}
        
        .viz-note {{
            text-align: center;
            margin-top: 15px;
            color: #666;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2em; }}
            .section {{ padding: 40px 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Climate Biotech Federal Grant Funding Analysis</h1>
            <div class="subtitle">Multi-Year Analysis of U.S. Government Grant Investment (2019-2025)</div>
        </div>
        
        <!-- Table of Contents -->
        <div class="toc">
            <h2>Table of Contents</h2>
            <div class="toc-links">
                <a href="#overview" class="toc-link">Executive Summary</a>
                <a href="#climate-share" class="toc-link">1. Climate Biotech Share of Federal Funding</a>
                <a href="#timeline" class="toc-link">2. Funding Timeline by Grant Type</a>
                <a href="#agencies" class="toc-link">3. Top Funding Agencies</a>
                <a href="#sankey-funding" class="toc-link">4. Funding Flow (Sankey Diagram)</a>
                <a href="#sankey-count" class="toc-link">5. Grant Count Flow</a>
                <a href="#research-flow" class="toc-link">6. Research Stage Flow</a>
                <a href="#derisked" class="toc-link">7. De-risked Categories</a>
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div id="overview" class="section">
            <h2 class="section-title">Executive Summary</h2>
            
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">{format_currency(total_climate_funding)}</div>
                    <div class="stat-label">Total Climate Biotech Funding</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(df_climate):,}</div>
                    <div class="stat-label">Total Grants</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{climate_share_pct:.2f}%</div>
                    <div class="stat-label">Share of Total Federal Grants</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">2019-2025</div>
                    <div class="stat-label">Analysis Period</div>
                </div>
            </div>
            
            <p style="font-size: 1.2em; margin-top: 30px;">
                This report analyzes federal funding patterns in climate biotechnology using keyword filtering combined with 
                a two-stage LLM classification system. We first applied CLIMATE × BIO keyword filters to identify candidate grants, 
                then used a two-stage LLM classifier to refine the selection and characterize each grant. 
            </p>
            
            <p style="font-size: 1.2em; margin-top: 20px;">
                <strong>Data sources:</strong> Grant metadata from NSF award records combined with funding amounts from USASpending.gov 
                across all federal agencies (2019-2025). This methodology identified {len(df_climate):,} climate biotech grants 
                totaling {format_currency(total_climate_funding)}, representing {climate_share_pct:.2f}% of total federal grant funding 
                during that period. The analysis reveals critical insights about funding distribution, technology readiness levels, and 
                industry awareness across different climate biotech domains.
            </p>
        </div>
        
        <!-- Section 1: Climate Biotech Share -->
        <div id="climate-share" class="section">
            <h2 class="section-title"><span class="section-number">1.</span> Climate Biotech Share of Federal Funding</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> Total climate biotech funding compared to total federal grant funding (2019-2025 combined). 
                This metric reveals the overall allocation of federal resources to climate biotech.
            </div>
            
            <div class="chart-container" id="climate-share-chart"></div>
            
            <div class="key-finding">
                <strong>Key Finding:</strong> Climate biotech represents {format_currency(total_climate_funding)} out of 
                {format_currency(total_all_funding)} in total federal grant funding ({climate_share_pct:.2f}%), 
                highlighting the current federal commitment to climate biotech.
            </div>
        </div>
        
        <!-- Section 2: Timeline -->
        <div id="timeline" class="section">
            <h2 class="section-title"><span class="section-number">2.</span> Total Climate Biotech Funding Over Time</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> Total climate biotech funding trends from 2019 to 2025.
            </div>
            
            <div class="chart-container" id="timeline-chart"></div>
            
            <div class="key-finding">
                <strong>Key Finding:</strong> Total climate biotech funding has grown from 2019 to 2025, with research grants 
                consistently dominating the portfolio ({format_currency(research_total)}, {research_pct:.1f}%), followed by 
                deployment ({format_currency(deployment_total)}, {deployment_pct:.1f}%), infrastructure 
                ({format_currency(infrastructure_total)}, {infrastructure_pct:.1f}%), and other 
                ({format_currency(other_total)}, {other_pct:.1f}%).
            </div>
        </div>
        
        <!-- Section 3: Top Agencies -->
        <div id="agencies" class="section">
            <h2 class="section-title"><span class="section-number">3.</span> Top Funding Agencies</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> The top 10 federal agencies providing climate biotech funding. 
                This reveals which agencies are driving investment in climate biotechnology solutions.
            </div>
            
            <div class="chart-container" id="agencies-chart"></div>
            
            <div class="key-finding">
                <strong>Key Finding:</strong> Federal climate biotech funding is concentrated in a few major agencies, 
                reflecting their respective missions and priorities in addressing climate challenges through biotechnology.
            </div>
        </div>
        
        <!-- Section 4: Sankey Funding -->
        <div id="sankey-funding" class="section">
            <h2 class="section-title"><span class="section-number">4.</span> Climate Biotech Grant Flow by Funding Amount (2019-2025)</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> The flow of funding from grant types (left side) to grant characteristics (right side). 
                The thickness of each flow represents the amount of funding. We selected these characteristics based on what we at 
                Homeworld believe to be critical yet often lacking attributes in the research ecosystem that could help advance the field: 
                industry-relevant language, collaborative interdisciplinary approaches, and open access/sharing practices.
            </div>
            
            <div class="chart-container">
                <a href="{VIZ_FILES['sankey_funding']}" target="_blank" class="viz-button">
                    📊 Open Interactive Sankey Diagram (Funding)
                </a>
                <p class="viz-note">Opens in new tab</p>
            </div>
            
            <div class="key-finding">
                <strong>Key Findings:</strong> Among public-facing research grants, the proportion using industry-relevant language 
                is lower at earlier research stages. Use Inspired Research ($496M total) directs only $46M (9.2%) to 
                industry-relevant language, while Bench Scale directs $22M (8.7%). Piloting ($6M, 10.0%) reveals slightly more 
                industry-relevant language. For public-facing research grants overall, $244M (23.7%) goes to Collaborative 
                Interdisciplinary approaches versus $409M (39.7%) to Single-Discipline work, and $95M (9.2%) demonstrates open 
                access/sharing practices. We see higher than expected collaborative interdisciplinary grants, but still lower 
                than the majority when it comes to public research funding.
            </div>
        </div>
        
        <!-- Section 5: Sankey Count -->
        <div id="sankey-count" class="section">
            <h2 class="section-title"><span class="section-number">5.</span> Climate Biotech Grant Flow by Grant Count (2019-2025)</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> The same flow as Plot 4, but showing grant counts instead of funding amounts. 
                The thickness of each flow represents the number of individual grants. Comparing this to the funding flow reveals 
                whether resources are concentrated in a few large grants or distributed across many smaller awards, and highlights 
                differences in average grant sizes across categories. This also allows us to see grant distribution trends which 
                reveal more distinct differences between grant categories that may be obscured when looking at funding amounts alone.
            </div>
            
            <div class="chart-container">
                <a href="{VIZ_FILES['sankey_count']}" target="_blank" class="viz-button">
                    📊 Open Interactive Sankey Diagram (Count)
                </a>
                <p class="viz-note">Opens in new tab</p>
            </div>
            
            <div class="key-finding">
                <strong>Key Findings:</strong> When examining grant counts rather than funding amounts, different distribution patterns 
                emerge. Among public-facing research grants, Use Inspired Research (1,013 total grants) includes 43 grants (4.2%) using 
                industry-relevant language, while Bench Scale shows 39 grants (8.1%). Piloting reveals 8 grants (8.5%) with 
                industry-relevant language. For public-facing research grants overall, 494 grants (31.1%) demonstrate Collaborative 
                Interdisciplinary approaches versus 1,091 grants (68.7%) with Single-Discipline work, and 74 grants (4.7%) show open 
                access/sharing practices. The count-based view reveals there are relatively fewer grants with the characteristics we 
                believe are needed to accelerate climate biotech innovation.
            </div>
        </div>
        
        <!-- Section 6: Research Flow -->
        <div id="research-flow" class="section">
            <h2 class="section-title"><span class="section-number">6.</span> Research Stage Funding Flow (2019-2025)</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> For research grants only, this visualization shows how funding flows through research stages 
                (left: Use Inspired Research, Bench Scale Tech Development, Piloting, Deployment) to application areas (right: specific 
                climate biotech categories like biofuels, carbon capture, sustainable agriculture, etc.). Each colored stream represents 
                a specific application area tracked across all research stages. The vertical thickness of each stream at any stage represents 
                the funding amount that application area receives at that particular stage. Streams that are thick at early stages but thin 
                at later stages indicate areas still in foundational research, while streams that grow thicker toward the right indicate 
                areas maturing toward deployment.
            </div>
            
            <div class="chart-container">
                <a href="{VIZ_FILES['research_flow']}" target="_blank" class="viz-button">
                    📊 Open Interactive Research Flow Diagram
                </a>
                <p class="viz-note">Opens in new tab</p>
            </div>
            
            <div class="key-finding">
                <strong>Key Finding:</strong> The visualization reveals which climate biotech technologies receive sustained federal 
                investment across all research stages versus those concentrated at specific maturity levels. Categories like platform 
                biochemicals, pollution degradation/remediation, and biogas/gaseous energy show funding across all stages from early 
                research through deployment, indicating a clear federal pathway to commercialization. In contrast, emerging technologies 
                like ecosystem monitoring, soil microbiome/nitrogen fixation, and bio-mineral weathering receive substantial early-stage 
                funding but minimal support at piloting and deployment stages. Importantly, while the federal government actively supports 
                early-stage research, it does not support most technologies entirely through the de-risking process needed for commercial 
                deployment. Most streams show funding narrowing or disappearing during the piloting stage—the government initiates research 
                but withdraws during the high-risk piloting phase, relying on private investment or other funding sources to bridge the 
                gap and de-risk the technology. Only technologies that emerge already de-risked (often through private sector investment) 
                receive substantial federal deployment funding. This pattern creates a strategic gap where promising scientific discoveries 
                may stall without adequate support through the critical piloting phase, potentially limiting the translation of federally-funded 
                research into commercial climate solutions.
            </div>
        </div>
        
        <!-- Section 7: De-risked Categories -->
        <div id="derisked" class="section">
            <h2 class="section-title"><span class="section-number">7.</span> De-risked Climate Biotech Categories Analysis</h2>
            
            <div class="explanation">
                <strong>What this shows:</strong> A scatter plot analyzing which climate biotech application areas are considered mature 
                enough for deployment-stage government support. The X-axis shows total funding for each category, the Y-axis shows the 
                percentage of that funding going to deployment (versus research)—this deployment ratio normalizes for total funding amounts 
                to identify which technologies receive disproportionately high deployment support. The size of each bubble represents the 
                total funding amount for that category. A horizontal line marks the average deployment ratio (14.1%) across all categories. 
                Categories plotted significantly above this line (Z-score > 1.5 standard deviations) have "abnormally high" deployment funding 
                ratios, indicating these technologies are proven enough that the federal government is willing to fund full-scale implementation.
            </div>
            
            <div class="chart-container">
                <a href="{VIZ_FILES['derisked']}" target="_blank" class="viz-button">
                    📊 Open Interactive Scatter Plot
                </a>
                <p class="viz-note">Opens in new tab</p>
            </div>
            
            <div class="key-finding">
                <strong>Key Finding:</strong> By normalizing deployment funding as a percentage of total funding, this analysis identifies 
                which climate biotech technologies the federal government considers de-risked enough for commercial-scale implementation. Only 
                two categories qualify as fully de-risked (Z-score >1.5): **platform biochemicals** (73.9% deployment ratio) and **other 
                climate biotech** (60.4%). Semi-de-risked categories above the 14.1% mean include **biogas/gaseous energy** (46.7%), 
                **biological carbon capture** (26.8%), and **pollution degradation/remediation** (14.0%). A weak correlation exists between 
                total funding and deployment ratio (R²=0.23), likely driven by specific commercially-viable breakthrough technologies within 
                broader fields attracting concentrated government investment rather than broad category-level de-risking. By examining the 
                commercialization history of specific technologies within these de-risked fields, we found: (1) **Federal de-risking investment 
                is slow**—platform biochemicals (gas fermentation) took 36 years from initial research (1989) to major federal deployment funding 
                (2025), while biogas required 50+ years of commercial operation before receiving substantial deployment support; (2) **Outside 
                private investment preceded government deployment funding**—LanzaTech's commercial proof in China (2018) attracted private capital 
                from chemical giants like INEOS years before the $200M federal deployment grant (2025).
            </div>
        </div>
        
    </div>
    
    <script>
        // Data from Python
        const climateShareData = {json.dumps(climate_share_data)};
        const timelineData = {json.dumps(timeline_data)};
        const agenciesData = {json.dumps(agencies_data)};
        
        // Chart 1: Climate Biotech Share (Bar Chart - Total Comparison)
        const totalClimate = climateShareData.climate_funding.reduce((a, b) => a + b, 0);
        const totalAll = climateShareData.all_funding.reduce((a, b) => a + b, 0);
        
        Plotly.newPlot('climate-share-chart', [{{
            x: ['Climate Biotech Grants', 'All Other Federal Grants'],
            y: [totalClimate/1e9, (totalAll - totalClimate)/1e9],
            type: 'bar',
            marker: {{
                color: ['#667eea', '#cccccc'],
                line: {{color: '#34495E', width: 1.5}}
            }},
            text: ['$' + (totalClimate/1e9).toFixed(2) + 'B<br>(' + climateShareData.share_pct[0].toFixed(2) + '%)', 
                   '$' + ((totalAll - totalClimate)/1e9).toFixed(2) + 'B<br>(99.98%)'],
            textposition: 'auto',
            hovertemplate: '%{{x}}<br>$%{{y:.2f}}B<extra></extra>'
        }}], {{
            xaxis: {{title: ''}},
            yaxis: {{title: 'Total Funding ($B)', tickprefix: '$', ticksuffix: 'B'}},
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            margin: {{l: 60, r: 40, t: 20, b: 80}},
            showlegend: false
        }}, {{responsive: true}});
        
        // Chart 2: Total Funding Over Time (Single Line)
        const totalByYear = timelineData.years.map((year, i) => 
            (timelineData.research[i] + timelineData.infrastructure[i] + 
             timelineData.deployment[i] + timelineData.other[i]) / 1e6
        );
        
        Plotly.newPlot('timeline-chart', [{{
            x: timelineData.years,
            y: totalByYear,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Total Climate Biotech Funding',
            line: {{color: '#667eea', width: 3}},
            marker: {{size: 10, color: '#667eea'}},
            fill: 'tozeroy',
            fillcolor: 'rgba(102, 126, 234, 0.1)',
            hovertemplate: '%{{x}}: $%{{y:.1f}}M<extra></extra>'
        }}], {{
            xaxis: {{title: 'Year'}},
            yaxis: {{title: 'Total Funding ($M)'}},
            hovermode: 'closest',
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            margin: {{l: 60, r: 40, t: 20, b: 60}}
        }}, {{responsive: true}});
        
        // Chart 3: Top Agencies (Horizontal Bar)
        Plotly.newPlot('agencies-chart', [{{
            y: agenciesData.agencies,
            x: agenciesData.funding.map(v => v/1e6),
            type: 'bar',
            orientation: 'h',
            marker: {{
                color: '#667eea',
                line: {{color: '#34495E', width: 1}}
            }},
            hovertemplate: '%{{y}}: $%{{x:.1f}}M<extra></extra>'
        }}], {{
            xaxis: {{title: 'Total Funding ($M)'}},
            yaxis: {{automargin: true}},
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            margin: {{l: 200, r: 40, t: 20, b: 60}}
        }}, {{responsive: true}});
    </script>
</body>
</html>'''

# Save the report
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✓ Report saved to: {OUTPUT_FILE}")
print(f"\nTo view: open {OUTPUT_FILE}")
print("\nMake sure these HTML files are in the same directory:")
for name, filename in VIZ_FILES.items():
    print(f"  - {filename}")
