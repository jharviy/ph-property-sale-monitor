"""
Central configuration for the PH Property Listings ETL pipeline.
Override any setting via environment variable or .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Directory Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"        # Downloaded source files
PROCESSED_DIR = DATA_DIR / "processed"  # Parquet snapshots + HTML reports
LOG_DIR = BASE_DIR / "logs"

for _dir in (RAW_DIR, PROCESSED_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/realestate_listing.db")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

# ── Scheduler ────────────────────────────────────────────────────────────────
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "09:00")  # Daily run (PHT)

# ── HTTP Request Defaults ─────────────────────────────────────────────────────
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
REQUEST_RETRY_COUNT = int(os.getenv("REQUEST_RETRY_COUNT", "3"))
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://apfs.bsp.gov.ph/BSP/asset_properties.asp",
    "Accept": "text/html,application/xhtml+xml,application/vnd.ms-excel",
}

# ── Data Source Registry ──────────────────────────────────────────────────────
# Each source entry drives its Extractor + Transformer instantiation.
# Add new sources here without touching pipeline logic.
SOURCES: dict = {
    "BSP": {
        "name": "Bangko Sentral ng Pilipinas",
        "download_url": (
            "https://apfs.bsp.gov.ph/BSP/lib/downloadExcel.asp"
            "?parameter=%20WHERE%20prop_type%20=%20%271%27%20and%20sales_status%20=%20%27200%27%20"
            "&txnname=properties"
        ),
        "file_extension": ".xls",
        "metadata_rows": 13,   # rows before the column header row
        "enabled": True,
    },
    # Future sources (example placeholders):
    # "PAG_IBIG": { "name": "Pag-IBIG Fund", "download_url": "...", ... },
    # "SSS": { "name": "Social Security System", "download_url": "...", ... },
}
