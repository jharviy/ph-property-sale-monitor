"""
Database loader.

Responsibilities:
- Init the SQLite schema on first run
- Bulk-upsert PropertyRecord objects (INSERT OR IGNORE on duplicate key)
- Save a Parquet snapshot of each batch for downstream analytics
- Log ScrapeRun metadata for observability
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config.settings import DATABASE_URL, PROCESSED_DIR
from src.models.db_models import Base, Property, ScrapeRun
from src.models.schemas import PropertyRecord, ScrapeRunRecord


class DatabaseLoader:
    """Handles writing transformed data to SQLite and Parquet."""

    def __init__(self, db_url: str = DATABASE_URL) -> None:
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)   # idempotent — safe to call every run
        logger.info(f"Database ready: {db_url}")

    # ── Core load operations ──────────────────────────────────────────────────

    def upsert_properties(self, records: List[PropertyRecord]) -> int:
        """
        Bulk-insert records, ignoring rows that already exist for this
        (property_acct_no, date_scraped) pair.

        Returns:
            Number of rows actually inserted.
        """
        if not records:
            logger.warning("No records to load.")
            return 0
        rows = [
            {
                "property_acct_no": r.property_acct_no,
                "category": r.category,
                "classification": r.classification,
                "tct_number": r.tct_number,
                "address": r.address,
                "city": r.city,
                "province": r.province,
                "region": r.region,
                "lot_area_sqm": r.lot_area_sqm,
                "floor_area_sqm": r.floor_area_sqm,
                "price_php": r.price_php,
                "price_per_sqm": r.price_per_sqm,
                "other_remarks": r.other_remarks,
                "source": r.source,
                "date_scraped": r.date_scraped,
            }
            for r in records
        ]

        # SQLite INSERT OR IGNORE honours the unique constraint
        insert_sql = text(
            """
            INSERT INTO properties (
                property_acct_no, category, classification, tct_number,
                address, city, province, region,
                lot_area_sqm, floor_area_sqm, price_php, price_per_sqm,
                other_remarks, source, date_scraped
            ) VALUES (
                :property_acct_no, :category, :classification, :tct_number,
                :address, :city, :province, :region,
                :lot_area_sqm, :floor_area_sqm, :price_php, :price_per_sqm,
                :other_remarks, :source, :date_scraped
            )
            ON CONFLICT(property_acct_no, tct_number)
            DO UPDATE SET
                date_scraped = excluded.date_scraped,
                price_php = excluded.price_php,
                price_per_sqm = excluded.price_per_sqm
            """
        )

        # Count before + after to measure actual inserts
        with Session(self.engine) as session:
            before = session.query(Property).count()
            session.execute(insert_sql, rows)
            session.commit()
            after = session.query(Property).count()

        inserted = after - before
        logger.success(f"Loaded {inserted} new rows (of {len(records)} processed)")
        return inserted

    def save_parquet(self, records: List[PropertyRecord], run_date: date) -> Path:
        """
        Persist a Parquet snapshot of this batch.

        Parquet is the analytical store — queries over time use these files.
        The SQLite DB is the operational/lookup store.
        """
        if not records:
            logger.warning("No records — Parquet snapshot skipped.")
            return None

        df = pd.DataFrame([r.model_dump() for r in records])
        output_path = PROCESSED_DIR / f"properties_{run_date.isoformat()}.parquet"
        df.to_parquet(output_path, index=False, engine="pyarrow")
        logger.info(f"Parquet snapshot saved: {output_path.name} ({len(df)} rows)")
        return output_path

    def log_scrape_run(self, run: ScrapeRunRecord) -> None:
        """Append a ScrapeRun audit record to the database."""
        with Session(self.engine) as session:
            session.add(
                ScrapeRun(
                    source=run.source,
                    date_scraped=run.date_scraped,
                    records_extracted=run.records_extracted,
                    records_loaded=run.records_loaded,
                    status=run.status,
                    error_message=run.error_message,
                    duration_seconds=run.duration_seconds,
                )
            )
            session.commit()
        logger.debug(f"Run logged: {run.source} | {run.status}")

    # ── Query helpers (used by the analyzer) ─────────────────────────────────

    def get_latest_run_date(self, source: str) -> date | None:
        """Return date of the most recent successful scrape for a source."""
        with Session(self.engine) as session:
            row = (
                session.query(ScrapeRun.date_scraped)
                .filter_by(source=source, status="success")
                .order_by(ScrapeRun.date_scraped.desc())
                .first()
            )
        return row[0] if row else None
