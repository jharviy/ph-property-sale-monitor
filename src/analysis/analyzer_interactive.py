"""
Interactive HTML report generator with in-browser filtering.

Embeds the full dataset as JSON and uses Plotly.js to build/update
charts dynamically — no server required, fully self-contained HTML file.

Output: data/processed/analysis_interactive.html
Usage:  python -m src.analysis.analyzer_interactive
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL, PROCESSED_DIR


class InteractiveReportGenerator:
    """Generates a self-contained HTML report with in-browser region/city filters."""

    def __init__(self, db_url: str = DATABASE_URL) -> None:
        self.engine = create_engine(db_url)

    def load_properties(self, run_date: Optional[date] = None) -> pd.DataFrame:
        query = "SELECT * FROM properties WHERE 1=1"
        params: dict = {}
        if run_date:
            query += " AND date_scraped = :date"
            params["date"] = run_date.isoformat()
        df = pd.read_sql(text(query), self.engine, params=params)
        logger.info(f"Loaded {len(df)} records (date={run_date})")
        return df

    def export_report(
        self,
        run_date: Optional[date] = None,
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        output_dir = output_dir or PROCESSED_DIR
        df = self.load_properties(run_date)
        if df.empty:
            logger.warning("No data — report not generated.")
            return None

        df = df.copy()
        df["date_scraped"] = df["date_scraped"].astype(str)
        # to_json handles NaN → null automatically
        records_json = df.to_json(orient="records")
        regions = sorted(df["region"].dropna().unique().tolist())
        date_label = run_date.isoformat() if run_date else "all dates"

        html = _build_html(records_json, json.dumps(regions), date_label)
        output_path = output_dir / "analysis_interactive.html"
        output_path.write_text(html, encoding="utf-8")
        logger.success(f"Interactive report saved: {output_path}")
        return output_path


def _build_html(records_json: str, regions_json: str, date_label: str) -> str:
    today = date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PH Real Estate — Interactive Report</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', sans-serif; max-width: 1300px; margin: 0 auto; padding: 24px; background: #f7f8fa; }}
    h1 {{ color: #1a2e44; margin-bottom: 4px; }}
    h2 {{ color: #2c5f8a; border-bottom: 2px solid #2c5f8a; padding-bottom: 4px; margin-top: 32px; }}
    .meta {{ color: #555; margin-bottom: 20px; }}
    .filters {{
      display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
      background: white; padding: 14px 20px; border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,.1); margin-bottom: 24px;
    }}
    .filters label {{ font-weight: 600; color: #1a2e44; white-space: nowrap; }}
    .filters select {{
      padding: 6px 12px; border: 1px solid #ccd; border-radius: 4px;
      font-size: 14px; min-width: 220px; background: white; cursor: pointer;
    }}
    .filters button {{
      padding: 6px 16px; background: #2c5f8a; color: white; border: none;
      border-radius: 4px; cursor: pointer; font-size: 14px;
    }}
    .filters button:hover {{ background: #1a3d5c; }}
    #stats-table {{ border-collapse: collapse; margin: 12px 0; }}
    #stats-table td {{ padding: 6px 18px; border: 1px solid #ddd; }}
    #stats-table tr:nth-child(even) {{ background: #f0f4f8; }}
    .chart-wrap {{ background: white; border-radius: 8px; padding: 12px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
    #record-count {{ font-weight: bold; color: #2c5f8a; }}
    .cat-filters {{
      background: white; padding: 14px 20px; border-radius: 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,.1); margin-bottom: 24px;
    }}
    .cat-filters .cat-header {{
      display: flex; align-items: center; gap: 16px; margin-bottom: 10px;
    }}
    .cat-filters .cat-header span {{ font-weight: 600; color: #1a2e44; }}
    .cat-filters .cat-header button {{
      padding: 3px 10px; font-size: 12px; background: #e8edf2; color: #1a2e44;
      border: 1px solid #ccd; border-radius: 4px; cursor: pointer;
    }}
    .cat-filters .cat-header button:hover {{ background: #d0d8e4; }}
    .cat-checkboxes {{ display: flex; flex-wrap: wrap; gap: 10px 20px; }}
    .cat-checkboxes label {{
      display: flex; align-items: center; gap: 6px; cursor: pointer;
      font-size: 14px; color: #333; user-select: none;
    }}
    .cat-checkboxes input[type=checkbox] {{ width: 15px; height: 15px; cursor: pointer; accent-color: #2c5f8a; }}
  </style>
</head>
<body>
  <h1>&#127968; PH Real Estate Listings &mdash; Interactive Report</h1>
  <p class="meta">
    <b>Source:</b> Bangko Sentral ng Pilipinas (BSP) &nbsp;|&nbsp;
    <b>Generated:</b> {today} &nbsp;|&nbsp;
    Showing <span id="record-count">&mdash;</span> listings
  </p>

  <div class="filters">
    <label for="sel-region">Region:</label>
    <select id="sel-region"><option value="">All Regions</option></select>
    <label for="sel-city">City / Municipality:</label>
    <select id="sel-city"><option value="">All Cities</option></select>
    <button onclick="resetFilters()">Reset All</button>
  </div>

  <div class="cat-filters">
    <div class="cat-header">
      <span>Category:</span>
      <button onclick="setCatAll(true)">Select All</button>
      <button onclick="setCatAll(false)">Deselect All</button>
    </div>
    <div class="cat-checkboxes" id="cat-checkboxes"></div>
  </div>

  <h2>Summary Statistics</h2>
  <table id="stats-table"><tbody id="stats-body"></tbody></table>

  <h2>Charts</h2>
  <div class="chart-wrap"><div id="chart-pie"></div></div>
  <div class="chart-wrap"><div id="chart-hist"></div></div>
  <div class="chart-wrap"><div id="chart-provinces"></div></div>
  <div class="chart-wrap"><div id="chart-boxplot"></div></div>
  <div class="chart-wrap"><div id="chart-treemap"></div></div>
  <div class="chart-wrap"><div id="chart-deals"></div></div>

<script>
const ALL_DATA    = {records_json};
const ALL_REGIONS = {regions_json};

const selRegion = document.getElementById('sel-region');
const selCity   = document.getElementById('sel-city');

// ── Populate region dropdown ──────────────────────────────────────────────────
ALL_REGIONS.forEach(r => {{
  const o = document.createElement('option');
  o.value = o.textContent = r;
  selRegion.appendChild(o);
}});

// ── Cascade: region → city ────────────────────────────────────────────────────
function buildCityDropdown(regionFilter) {{
  const cities = [...new Set(
    ALL_DATA
      .filter(d => !regionFilter || d.region === regionFilter)
      .map(d => d.city)
      .filter(Boolean)
  )].sort();
  selCity.innerHTML = '<option value="">All Cities</option>';
  cities.forEach(c => {{
    const o = document.createElement('option');
    o.value = o.textContent = c;
    selCity.appendChild(o);
  }});
}}

selRegion.addEventListener('change', () => {{
  buildCityDropdown(selRegion.value);
  render();
}});
selCity.addEventListener('change', render);

function resetFilters() {{
  selRegion.value = '';
  buildCityDropdown('');
  setCatAll(true);
}}

// ── Category checkboxes ───────────────────────────────────────────────────────
const ALL_CATS = [...new Set(ALL_DATA.map(d => d.category).filter(Boolean))].sort();

function buildCatCheckboxes() {{
  const wrap = document.getElementById('cat-checkboxes');
  wrap.innerHTML = '';
  ALL_CATS.forEach((cat, i) => {{
    const color = PALETTE[i % PALETTE.length];
    const id = 'chk-' + i;
    wrap.insertAdjacentHTML('beforeend',
      `<label for="${{id}}">` +
      `<input type="checkbox" id="${{id}}" value="${{cat}}" checked onchange="render()">` +
      `<span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:${{color}};flex-shrink:0"></span>` +
      `${{cat}}</label>`
    );
  }});
}}

function getSelectedCats() {{
  return [...document.querySelectorAll('#cat-checkboxes input:checked')].map(el => el.value);
}}

function setCatAll(checked) {{
  document.querySelectorAll('#cat-checkboxes input').forEach(el => el.checked = checked);
  render();
}}

// ── Filter ────────────────────────────────────────────────────────────────────
function getFiltered() {{
  const region   = selRegion.value;
  const city     = selCity.value;
  const selCats  = new Set(getSelectedCats());
  return ALL_DATA.filter(d =>
    (!region || d.region === region) &&
    (!city   || d.city   === city)   &&
    (selCats.size === ALL_CATS.length || selCats.has(d.category))
  );
}}

// ── Math helpers ──────────────────────────────────────────────────────────────
function median(arr) {{
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}}
function mean(arr) {{
  return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
}}

// ── Stats table ───────────────────────────────────────────────────────────────
function renderStats(data) {{
  const prices   = data.map(d => d.price_php).filter(v => v > 0);
  const areas    = data.map(d => d.lot_area_sqm).filter(v => v > 0);
  const psqm     = data.map(d => d.price_per_sqm).filter(v => v > 0);
  const fmtNum   = n => n == null ? 'N/A' : n.toLocaleString('en-PH', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
  const fmtPHP   = n => n == null ? 'N/A' : '₱' + n.toLocaleString('en-PH', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
  const regions  = new Set(data.map(d => d.region).filter(Boolean));
  const provs    = new Set(data.map(d => d.province).filter(Boolean));
  const rows = [
    ['Total Properties',    data.length.toLocaleString()],
    ['Average Price',       fmtPHP(mean(prices))],
    ['Median Price',        fmtPHP(median(prices))],
    ['Total Value',         fmtPHP(prices.reduce((a, b) => a + b, 0))],
    ['Avg Lot Area (sqm)',  fmtNum(mean(areas))],
    ['Median Price / sqm',  fmtPHP(median(psqm))],
    ['Unique Regions',      regions.size],
    ['Unique Provinces',    provs.size],
  ];
  document.getElementById('stats-body').innerHTML =
    rows.map(([k, v]) => `<tr><td>${{k}}</td><td><b>${{v}}</b></td></tr>`).join('');
  document.getElementById('record-count').textContent = data.length.toLocaleString();
}}

// ── Deal score (mirrors Python logic) ─────────────────────────────────────────
function computeDealScores(data) {{
  const catMedians = {{}};
  [...new Set(data.map(d => d.category).filter(Boolean))].forEach(cat => {{
    const vals = data.filter(d => d.category === cat && d.price_per_sqm > 0).map(d => d.price_per_sqm);
    catMedians[cat] = median(vals);
  }});
  return data.map(d => {{
    const med = catMedians[d.category];
    const score = med && d.price_per_sqm > 0
      ? Math.min(100, Math.max(0, (med - d.price_per_sqm) / med * 100))
      : 0;
    return {{ ...d, deal_score: score }};
  }});
}}

// ── Layout base ───────────────────────────────────────────────────────────────
const BASE = {{
  paper_bgcolor: 'white',
  plot_bgcolor: '#fafafa',
  font: {{ family: 'Segoe UI, sans-serif' }},
  margin: {{ t: 50, r: 20, b: 50, l: 60 }},
}};

// Plotly's default qualitative palette — same as Python plotly express
const PALETTE = ['#636EFA','#EF553B','#00CC96','#AB63FA','#FFA15A','#19D3F3','#FF6692','#B6E880','#FF97FF','#FECB52'];
function catColor(cat, cats) {{ return PALETTE[cats.indexOf(cat) % PALETTE.length]; }}

// ── Chart renderers ───────────────────────────────────────────────────────────
function renderPie(data) {{
  const counts = {{}};
  data.forEach(d => {{ if (d.category) counts[d.category] = (counts[d.category] || 0) + 1; }});
  Plotly.react('chart-pie',
    [{{ type: 'pie', values: Object.values(counts), labels: Object.keys(counts), hole: 0.35, textinfo: 'label+percent' }}],
    {{ ...BASE, title: 'Property Breakdown by Category' }}
  );
}}

function renderHist(data) {{
  const cats = [...new Set(data.map(d => d.category).filter(Boolean))];
  const traces = cats.map(cat => ({{
    type: 'histogram', name: cat, opacity: 0.75, nbinsx: 50,
    x: data.filter(d => d.category === cat && d.price_php > 0).map(d => Math.log10(d.price_php)),
  }}));
  Plotly.react('chart-hist', traces, {{
    ...BASE, barmode: 'overlay',
    title: 'Price Distribution by Category (log scale)',
    xaxis: {{
      title: 'Price (PHP)',
      tickvals: [4.7, 5, 5.3, 5.7, 6, 6.7, 7, 7.7, 8],
      ticktext: ['₱50K', '₱100K', '₱200K', '₱500K', '₱1M', '₱5M', '₱10M', '₱50M', '₱100M'],
    }},
    yaxis: {{ title: '# Properties' }},
  }});
}}

function renderProvinces(data, topN = 15) {{
  const prov = {{}};
  data.forEach(d => {{
    if (!d.province) return;
    if (!prov[d.province]) prov[d.province] = {{ count: 0, prices: [] }};
    prov[d.province].count++;
    if (d.price_php > 0) prov[d.province].prices.push(d.price_php);
  }});
  const sorted   = Object.entries(prov).sort((a, b) => b[1].count - a[1].count).slice(0, topN);
  const names    = sorted.map(([k]) => k);
  const counts   = sorted.map(([, v]) => v.count);
  const medians  = sorted.map(([, v]) => median(v.prices) || 0);
  Plotly.react('chart-provinces',
    [{{ type: 'bar', orientation: 'h', x: counts, y: names,
        marker: {{ color: medians, colorscale: 'Blues', showscale: true, colorbar: {{ title: 'Median Price' }} }} }}],
    {{ ...BASE, title: `Top ${{topN}} Provinces by Number of Listings`,
       xaxis: {{ title: '# Properties' }},
       yaxis: {{ categoryorder: 'total ascending', automargin: true }},
       margin: {{ ...BASE.margin, l: 160 }},
    }}
  );
}}

function renderBoxplot(data) {{
  const cats   = [...new Set(data.map(d => d.category).filter(Boolean))];
  const sorted = data.map(d => d.price_per_sqm).filter(v => v > 0).sort((a, b) => a - b);
  const cutoff = sorted[Math.floor(sorted.length * 0.99)] ?? Infinity;
  const traces = cats.map(cat => ({{
    type: 'box', name: cat, boxpoints: false,
    marker: {{ color: catColor(cat, cats) }},
    y: data.filter(d => d.category === cat && d.price_per_sqm > 0 && d.price_per_sqm < cutoff)
           .map(d => d.price_per_sqm),
  }}));
  Plotly.react('chart-boxplot', traces, {{
    ...BASE,
    title: 'Price per sqm by Category (99th-pct cutoff)',
    yaxis: {{ title: 'PHP / sqm' }},
  }});
}}

function renderTreemap(data) {{
  const agg = {{}};
  data.forEach(d => {{
    if (!d.region || !d.category) return;
    const k = d.region + '||' + d.category;
    agg[k] = (agg[k] || 0) + 1;
  }});
  const labels = [], parents = [], values = [];
  [...new Set(data.map(d => d.region).filter(Boolean))].forEach(r => {{
    labels.push(r); parents.push(''); values.push(0);
  }});
  Object.entries(agg).forEach(([k, v]) => {{
    const [r, c] = k.split('||');
    labels.push(c); parents.push(r); values.push(v);
  }});
  Plotly.react('chart-treemap',
    [{{ type: 'treemap', labels, parents, values, branchvalues: 'remainder', marker: {{ colorscale: 'Teal' }} }}],
    {{ ...BASE, title: 'Property Distribution — Region → Category' }}
  );
}}

function renderDeals(data, topN = 25) {{
  const scored = computeDealScores(data).filter(d => d.deal_score > 0);
  scored.sort((a, b) => b.deal_score - a.deal_score);
  const top    = scored.slice(0, topN);
  const labels = top.map(d => (d.city || '?') + ', ' + (d.province || '?') + '|' + d.property_acct_no);
  const allCats = [...new Set(top.map(d => d.category).filter(Boolean))];
  // One trace per category so the legend + colors match the other charts
  const traces = allCats.map(cat => {{
    const rows = top.filter(d => d.category === cat);
    return {{
      type: 'bar', orientation: 'h', name: cat,
      marker: {{ color: catColor(cat, allCats) }},
      x: rows.map(d => d.deal_score),
      y: rows.map(d => d.property_acct_no),
    }};
  }});
  Plotly.react('chart-deals', traces,
    {{ ...BASE,
       barmode: 'overlay',
       height: Math.max(400, 300 + top.length * 22),
       title: `Top ${{topN}} Potential Deals (vs Category Median Price/sqm)`,
       xaxis: {{ title: 'Deal Score (0–100, higher = cheaper vs peers)' }},
       yaxis: {{
         categoryorder: 'total ascending', automargin: true, dtick: 1,
         tickmode: 'array',
         tickvals: top.map(d => d.property_acct_no),
         ticktext: labels,
         tickfont: {{ size: 11 }},
         title: 'Address | Property Acct. No.',
       }},
       margin: {{ ...BASE.margin, l: 320 }},
    }}
  );
}}

// ── Main render ───────────────────────────────────────────────────────────────
function render() {{
  const data = getFiltered();
  renderStats(data);
  renderPie(data);
  renderHist(data);
  renderProvinces(data);
  renderBoxplot(data);
  renderTreemap(data);
  renderDeals(data);
}}

// ── Init ──────────────────────────────────────────────────────────────────────
buildCityDropdown('');
buildCatCheckboxes();
render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    gen = InteractiveReportGenerator()
    path = gen.export_report()
    if path:
        print(f"Open: {path.resolve()}")
