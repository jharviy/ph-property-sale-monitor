# 🏠 PH Property Sale Monitor

> A personal data engineering project that automatically tracks BSP foreclosed property listings daily — built for scouting undervalued real estate in the Philippines.

[![Daily Monitor](https://github.com/jharviy/ph-property-sale-monitor/actions/workflows/monitor.yml/badge.svg)](https://github.com/jharviy/ph-property-sale-monitor/actions/workflows/monitor.yml)

---

## 📊 Live Analysis

The pipeline runs automatically every day via GitHub Actions and publishes an interactive report here:

**👉 [View Latest Property Report](https://jharviy.github.io/ph-property-sale-monitor/data/processed/analysis.html)**

---

## What it does

Data from the **BSP (Bangko Sentral ng Pilipinas)** Asset Properties portal is downloaded, cleaned, stored, and analyzed — automatically, every day, with no manual steps.

The pipeline follows the standard **ETL** (Extract → Transform → Load) pattern used in data engineering:

| Step | What happens |
|---|---|
| **Extract** | Downloads the daily BSP property listing (XLS file) via direct URL — no browser automation needed |
| **Transform** | Cleans the messy XLS structure, parses addresses into city/province/region, validates every row with Pydantic |
| **Load** | Saves to SQLite for queries + Parquet snapshots for analytics. Duplicate-safe — re-running the same day is safe |
| **Analyze** | Generates an interactive HTML report with price distributions, deal rankings, and regional breakdowns |

---

## How it runs automatically

The pipeline is scheduled via **GitHub Actions** — no server or cron job needed.

```
Every day (GitHub-hosted runner)
    │
    ▼
monitor.yml triggers
    │
    ├── pip install -r requirements.txt
    ├── python main.py          ← ETL + analysis
    └── git commit & push       ← saves DB + HTML report back to repo
                                   (GitHub Pages picks it up automatically)
```

The green/red badge at the top of this README updates after every run. If it's green, yesterday's data was collected successfully.

---

## Architecture

```
BSP Website  (daily XLS snapshot)
    │
    ▼
BSPExtractor            → data/raw/bsp_properties_YYYY-MM-DD.xls
    │
    ▼
BSPTransformer          → validates, cleans, enriches addresses
    │
    ├──► DatabaseLoader ──► SQLite   (data/realestate_listing.db)
    │                  └──► Parquet  (data/processed/properties_YYYY-MM-DD.parquet)
    │
    └──► PropertyAnalyzer ──► data/processed/analysis.html
                              (published via GitHub Pages)
```

**Designed to scale** — adding a new data source (Pag-IBIG, SSS, etc.) only requires:
- A new `Extractor` + `Transformer` subclass
- One entry in `config/settings.py`
- Zero changes to the pipeline, loader, or analyzer

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Data validation | Pydantic v2 | Schema enforcement + auto type coercion |
| Database | SQLAlchemy + SQLite | Zero-setup, file-based, portable |
| Analytics storage | Parquet + PyArrow | Columnar format — fast aggregations, upgradeable to DuckDB |
| Logging | Loguru | Structured rotating logs, zero config |
| Visualization | Plotly | Interactive charts exported as self-contained HTML |
| Automation | GitHub Actions | Free hosted runner, scheduled daily, no server needed |

---

## Analysis Report Includes

- **Category breakdown** — pie chart of Agricultural / Residential / Commercial split
- **Price distribution** — log-scale histogram showing the full price range per category
- **Top provinces** — ranked by number of listings, shaded by median price
- **Price per sqm boxplot** — compare value across categories at a glance
- **Regional treemap** — across all individual regions distribution
- **Deal score ranking** — top 25 properties priced furthest below their category median (higher = bigger discount vs comparable properties)

---

## Project Structure

```
ph-property-sale-monitor/
├── .github/workflows/
│   └── monitor.yml          # daily scheduled run on GitHub
├── config/
│   └── settings.py          # source registry, paths, config
├── src/
│   ├── extractors/          # download logic (one file per source)
│   ├── transformers/        # parsing + cleaning (one file per source)
│   ├── loaders/             # SQLite upsert + Parquet export
│   ├── models/
│   │   ├── schemas.py       # Pydantic validation models
│   │   └── db_models.py     # SQLAlchemy ORM models
│   ├── pipeline/            # ETL orchestrator — source-agnostic
│   ├── analysis/            # chart generation + HTML report
│   └── utils/
│       ├── address_parser.py   # extract city/province from raw address
│       └── ph_regions.py       # province → region lookup (all 18 regions)
├── data/
│   ├── raw/                    # downloaded XLS files
│   ├── processed/              # Parquet snapshots + HTML reports
│   └── realestate_listing.db   # SQLite database
├── main.py                     # CLI entry point
├── Makefile                    # dev shortcuts
└── requirements.txt
```

---

## Database Schema

**`properties`** table — one row per listing

| Column | Type | Notes |
|---|---|---|
| property_acct_no | TEXT | BSP account number |
| category | TEXT | Agricultural, Residential, Commercial… |
| classification | TEXT | Sub-type (e.g. Cocoland, House and Lot) |
| tct_number | TEXT | Transfer Certificate of Title |
| address | TEXT | Raw BSP address string |
| city / province / region | TEXT | Parsed and enriched from address field |
| lot_area_sqm | FLOAT | |
| floor_area_sqm | FLOAT | NULL when BSP reports 0 (no structure on lot) |
| price_php | FLOAT | |
| price_per_sqm | FLOAT | Pre-computed: price ÷ lot_area |
| source | TEXT | `"BSP"` — extensible for future sources |
| date_scraped | DATE | Date of the snapshot |

**`scrape_runs`** — audit log of every pipeline execution: source, date, record counts, status, duration.

---

## Running Locally

```bash
# Clone
git clone https://github.com/jharviy/ph-property-sale-monitor.git
cd ph-property-sale-monitor

# Install
pip install -r requirements.txt

# Run full pipeline (download → clean → store → report)
python main.py

# Options
python main.py --mode etl             # ETL only, skip analysis
python main.py --mode analyze         # generate report from existing data
```



---

## Extensibility
The pipeline is source-agnostic — the extractor, transformer, loader, and analyzer are fully decoupled. Adding a new property source (e.g. Pag-IBIG, SSS) only requires implementing two classes (`BaseExtractor`, `BaseTransformer`) and registering the source in `config/settings.py`. No changes needed to the pipeline or storage layer.

---

## Upgrade Paths

| Concern | Current | When you need to scale |
|---|---|---|
| Database | SQLite | Switch to PostgreSQL — just change `DATABASE_URL` in `.env` |
| Analytics queries | Parquet files | DuckDB (queries Parquet directly) or Apache Spark |
| Scheduling | GitHub Actions | Apache Airflow or Prefect for complex DAGs |
| Deployment | Single runner | Docker + Kubernetes CronJob |

---

## License

MIT — free to use, fork, and extend.
