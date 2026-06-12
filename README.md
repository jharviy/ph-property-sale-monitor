# 🏠 PH Foreclosed Properties ETL

> A personal data engineering project that daily-ingests BSP foreclosed property listings, stores them in SQLite + Parquet, and generates interactive price/deal analysis — useful for hunting undervalued properties in the Philippines.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![CI](https://github.com/yourusername/ph-foreclosed-properties/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What it does

1. **Extracts** — Downloads the daily XLS snapshot from the BSP Asset Properties portal (no browser needed; direct download endpoint).
2. **Transforms** — Parses the messy XLS structure, splits category fields, coerces numerics, enriches addresses with city/province/region, validates every row with Pydantic.
3. **Loads** — Upserts into SQLite (operational queries) and saves a Parquet snapshot (analytical queries). Duplicate-safe via `(property_acct_no, date_scraped)` unique constraint.
4. **Analyzes** — Generates a self-contained interactive HTML report with Plotly charts: price distributions, top provinces, price-per-sqm boxplots, regional treemaps, and a **deal score** ranking properties below their category median.

---

## Architecture

```
BSP Website
    │  (HTTP GET — stable daily URL)
    ▼
BSPExtractor        ← data/raw/bsp_properties_YYYY-MM-DD.xls
    │
    ▼
BSPTransformer      ← Pydantic validation, address enrichment, price/sqm calc
    │
    ├──► DatabaseLoader ──► SQLite  (data/foreclosed_properties.db)
    │                  └──► Parquet (data/processed/properties_YYYY-MM-DD.parquet)
    │
    └──► PropertyAnalyzer ──► HTML report (data/processed/analysis_YYYY-MM-DD.html)
```

**Extensible by design** — adding a new source (Pag-IBIG, SSS, etc.) means:
- Subclass `BaseExtractor` + `BaseTransformer`
- Register in `config/settings.py → SOURCES`
- No changes to pipeline or loader logic

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Validation | Pydantic v2 | Schema enforcement, auto type coercion |
| Storage (operational) | SQLAlchemy + SQLite | Zero-setup, portable |
| Storage (analytical) | Parquet + PyArrow | Columnar, fast aggregations, upgradeable to DuckDB/Spark |
| Logging | Loguru | Structured, rotating logs with zero config |
| Visualisation | Plotly | Interactive HTML charts, no server needed |
| Scheduling | schedule | Simple, readable; swap for Airflow/Prefect at scale |
| Testing | pytest + pytest-cov | Unit tests with mocked HTTP |
| CI | GitHub Actions | Automated lint + test on every push |

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/yourusername/ph-foreclosed-properties.git
cd ph-foreclosed-properties

# 2. Install
pip install -r requirements.txt

# 3. Run full pipeline (ETL + analysis) for today
python main.py
```

That's it. On first run it:
- Creates `data/foreclosed_properties.db`
- Downloads today's BSP XLS to `data/raw/`
- Saves a Parquet snapshot to `data/processed/`
- Writes an HTML report to `data/processed/analysis_YYYY-MM-DD.html`

---

## Usage

```bash
python main.py                          # full run (default)
python main.py --mode etl               # ETL only, skip analysis
python main.py --mode analyze           # analysis on existing data
python main.py --date 2026-06-01        # reprocess a specific date
python main.py --source BSP             # specific source only

python scheduler.py                     # start daily scheduler (09:00 PHT)
python scheduler.py --now               # run once immediately
```

Or use the Makefile shortcuts:

```bash
make install       # pip install -r requirements.txt
make run           # full pipeline today
make etl           # ETL only
make analyze       # analysis only
make test          # run tests
make test-cov      # tests + coverage report
make fmt           # auto-format with black + isort
```

---

## Project structure

```
ph-foreclosed-properties/
├── config/
│   └── settings.py          # all config, source registry
├── src/
│   ├── extractors/          # HTTP download logic per source
│   ├── transformers/        # XLS parsing + data cleaning per source
│   ├── loaders/             # SQLite upsert + Parquet export
│   ├── models/
│   │   ├── schemas.py       # Pydantic validation models
│   │   └── db_models.py     # SQLAlchemy ORM
│   ├── pipeline/            # ETL orchestrator (source-agnostic)
│   ├── analysis/            # Plotly charts + HTML report
│   └── utils/
│       ├── address_parser.py
│       └── ph_regions.py    # province → region lookup (all 18 regions)
├── data/
│   ├── raw/                 # downloaded XLS files (gitignored)
│   └── processed/           # Parquet snapshots + HTML reports (gitignored)
├── tests/
│   ├── conftest.py          # shared fixtures (sample XLS, sample DataFrames)
│   ├── test_transformer.py
│   └── test_extractor.py
├── .github/workflows/ci.yml
├── main.py                  # CLI entry point
├── scheduler.py             # daily runner
├── Makefile
└── requirements.txt
```

---

## Database schema

**`properties`**

| Column | Type | Notes |
|---|---|---|
| property_acct_no | TEXT | BSP account number |
| category | TEXT | Agricultural, Residential, Commercial… |
| classification | TEXT | Sub-type (e.g. Cocoland, House and Lot) |
| tct_number | TEXT | Transfer Certificate of Title number |
| address | TEXT | Raw BSP address string |
| city / province / region | TEXT | Parsed + enriched from address |
| lot_area_sqm | FLOAT | |
| floor_area_sqm | FLOAT | NULL when BSP reports 0 (no structure) |
| price_php | FLOAT | |
| price_per_sqm | FLOAT | Pre-computed: price ÷ lot_area |
| source | TEXT | "BSP" (extensible) |
| date_scraped | DATE | Logical scrape date (daily snapshot key) |

**`scrape_runs`** — audit log of every pipeline execution (status, duration, record counts).

---

## Analysis outputs

The HTML report includes:

- **Category pie** — breakdown by property type
- **Price histogram** — log-scale, colour-coded by category
- **Top 15 provinces** — by listing count, shaded by median price
- **Price per sqm boxplot** — compare categories at a glance
- **Regional treemap** — NCR vs Visayas vs Mindanao distribution
- **Deal score ranking** — top 20 properties priced below their category median (higher score = bigger discount vs peers)
- **Availability trend** — properties listed per scrape date (accumulates over daily runs)

---

## Upgrading to production

| Concern | Current | Drop-in upgrade |
|---|---|---|
| Database | SQLite | PostgreSQL (change `DATABASE_URL` in `.env`) |
| Analytical queries | Parquet files | DuckDB or Apache Spark |
| Scheduling | `schedule` loop | Apache Airflow / Prefect |
| Orchestration | single machine | Docker + cron / Kubernetes CronJob |

---

## Adding a new property source

```python
# 1. config/settings.py
SOURCES["PAG_IBIG"] = {
    "name": "Pag-IBIG Fund",
    "download_url": "https://...",
    "file_extension": ".xlsx",
    "enabled": True,
}

# 2. src/extractors/pagibig_extractor.py
class PagIbigExtractor(BaseExtractor):
    source_name = "PAG_IBIG"
    def extract(self, save_dir, run_date): ...
    def validate_source(self): ...

# 3. src/transformers/pagibig_transformer.py
class PagIbigTransformer(BaseTransformer):
    source_name = "PAG_IBIG"
    def transform(self, raw_file, run_date): ...

# 4. main.py — add to EXTRACTOR_MAP and TRANSFORMER_MAP
```

The pipeline, loader, and analyzer require **zero changes**.

---

## License

MIT — free to use, fork, and extend.
