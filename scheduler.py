"""
Daily scheduler — runs the ETL pipeline automatically at a set time.

Usage:
    python scheduler.py          # runs forever, triggers at SCHEDULE_TIME daily
    python scheduler.py --now    # run once immediately then exit

Keep this running as a background process (screen, tmux, or systemd service).
"""
import argparse
import sys
from datetime import date

import schedule
import time
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | {level} | {message}")
logger.add("logs/scheduler.log", rotation="1 week", retention="4 weeks", level="DEBUG")

from config.settings import SCHEDULE_TIME, SOURCES
from src.extractors.bsp_extractor import BSPExtractor
from src.transformers.bsp_transformer import BSPTransformer
from src.loaders.db_loader import DatabaseLoader
from src.pipeline.etl_pipeline import ETLPipeline
from src.analysis.analyzer import PropertyAnalyzer
from main import run_etl, run_analysis


# def run_all_sources() -> None:
#     """Run ETL + analysis for all enabled sources."""
#     run_date = date.today()
#     loader = DatabaseLoader()

#     for source_name, cfg in SOURCES.items():
#         if not cfg.get("enabled"):
#             continue
#         logger.info(f"Scheduler: starting {source_name}")
#         try:
#             # Wire components — extend this map as new sources are added
#             extractors = {"BSP": BSPExtractor}
#             transformers = {"BSP": BSPTransformer}

#             pipeline = ETLPipeline(
#                 extractor=extractors[source_name](),
#                 transformer=transformers[source_name](),
#                 loader=loader,
#             )
#             pipeline.run(run_date)
#         except Exception as exc:
#             logger.error(f"Scheduled run failed for {source_name}: {exc}")

#     # Analysis after all sources loaded
#     try:
#         PropertyAnalyzer().export_report(run_date)
#     except Exception as exc:
#         logger.error(f"Analysis failed: {exc}")



def run_all_sources() -> None:
    run_date = date.today() 
    run_etl("BSP", run_date)
    run_analysis(None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="Run once immediately and exit")
    args = parser.parse_args()

    if args.now:
        logger.info("Running immediately (--now flag)")
        run_all_sources()
    else:
        logger.info(f"Scheduler started — daily run at {SCHEDULE_TIME} PHT")
        schedule.every().day.at(SCHEDULE_TIME).do(run_all_sources)
        while True:
            schedule.run_pending()
            time.sleep(60)
