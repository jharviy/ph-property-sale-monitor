"""
ETL pipeline orchestrator.

Wires together an Extractor, Transformer, and Loader into a single
run() call. Stateless — instantiate once per source per run.
"""
from __future__ import annotations

import time
from datetime import date

from loguru import logger

from config.settings import RAW_DIR
from src.extractors.base_extractor import BaseExtractor
from src.loaders.db_loader import DatabaseLoader
from src.models.schemas import ScrapeRunRecord
from src.transformers.base_transformer import BaseTransformer


class ETLPipeline:
    """
    Orchestrates Extract → Transform → Load for one source.

    Adding support for a new data source:
        extractor  = MyNewExtractor()
        transformer = MyNewTransformer()
        ETLPipeline(extractor, transformer, loader).run()

    No changes needed inside this class.
    """

    def __init__(
        self,
        extractor: BaseExtractor,
        transformer: BaseTransformer,
        loader: DatabaseLoader,
    ) -> None:
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    def run(self, run_date: date | None = None) -> ScrapeRunRecord:
        """
        Execute the full ETL pipeline for one source and one date.

        Args:
            run_date: Logical scrape date (defaults to today).

        Returns:
            ScrapeRunRecord populated with outcome metrics.

        Raises:
            Any exception from Extract or Transform phases after logging.
        """
        run_date = run_date or date.today()
        source = self.extractor.source_name
        run_record = ScrapeRunRecord(source=source, date_scraped=run_date)
        t0 = time.perf_counter()

        logger.info("=" * 60)
        logger.info(f"Pipeline start  |  source={source}  |  date={run_date}")
        logger.info("=" * 60)

        try:
            # ── 1. EXTRACT ────────────────────────────────────────────────────
            logger.info("[1/3] EXTRACT")
            raw_file = self.extractor.extract(RAW_DIR, run_date)

            # ── 2. TRANSFORM ──────────────────────────────────────────────────
            logger.info("[2/3] TRANSFORM")
            records = self.transformer.transform(raw_file, run_date)
            run_record.records_extracted = len(records)

            # ── 3. LOAD ───────────────────────────────────────────────────────
            logger.info("[3/3] LOAD")
            inserted = self.loader.upsert_properties(records)
            self.loader.save_parquet(records, run_date)
            run_record.records_loaded = inserted

            run_record.status = "success"
            logger.success(
                f"Pipeline complete  |  "
                f"extracted={run_record.records_extracted}  "
                f"loaded={run_record.records_loaded}"
            )

        except Exception as exc:
            run_record.status = "failed"
            run_record.error_message = str(exc)
            logger.error(f"Pipeline failed: {exc}")
            raise

        finally:
            run_record.duration_seconds = round(time.perf_counter() - t0, 2)
            self.loader.log_scrape_run(run_record)
            logger.info(
                f"Run logged  |  duration={run_record.duration_seconds}s  "
                f"|  status={run_record.status}"
            )

        return run_record
