"""
PH Real Estate Listings ETL — CLI Entry Point

Usage:
    python main.py                        # full ETL + analysis for today
    python main.py --mode etl             # ETL only
    python main.py --mode analyze         # analysis on existing data
"""
import argparse
import sys
from datetime import date, datetime

from loguru import logger

# ── Logging setup (must precede any project imports that use logger) ──────────
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    colorize=True,
)
logger.add(
    "logs/etl_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

# ── Project imports ───────────────────────────────────────────────────────────
from config.settings import SOURCES
from src.analysis.analyzer import PropertyAnalyzer
from src.analysis.analyzer_interactive import InteractiveReportGenerator
from src.extractors.bsp_extractor import BSPExtractor
from src.loaders.db_loader import DatabaseLoader
from src.pipeline.etl_pipeline import ETLPipeline
from src.transformers.bsp_transformer import BSPTransformer

# ── Source registry —- add new extractors/transformers here ──────────────────
EXTRACTOR_MAP = {
    "BSP": BSPExtractor,
    # "PAG_IBIG": PagIbigExtractor,   # future source
}
TRANSFORMER_MAP = {
    "BSP": BSPTransformer,
    # "PAG_IBIG": PagIbigTransformer,
}


def run_etl(run_date: date) -> None:
    """Run the full ETL for one source."""
    extractor = EXTRACTOR_MAP["BSP"]()
    transformer = TRANSFORMER_MAP["BSP"]()
    loader = DatabaseLoader()

    pipeline = ETLPipeline(extractor, transformer, loader)
    pipeline.run(run_date)


def run_analysis(run_date: date | None) -> None:
    """Generate analysis report from existing DB data."""
    # analyzer = PropertyAnalyzer()
    analyzer = InteractiveReportGenerator()
    path = analyzer.export_report(run_date)   #func()Analyze All
    # path = InteractiveReportGenerator.export_report(run_date)
    if path:
        logger.success(f"Open your report: {path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="PH Properties for Sale — ETL + Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                         # full run, today\n"
            "  python main.py --mode etl              # ETL only\n"
            "  python main.py --mode analyze          # analysis only\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["full", "etl", "analyze"],
        default="full",
        help="Pipeline mode (default: full)",
    )

    args = parser.parse_args()
    run_date: date = date.today()
    # run_date: date = args.date or date.today()

    if args.mode in ("full", "etl"):
        run_etl(run_date)
    if args.mode in ("full", "analyze"):
        run_analysis(run_date)


if __name__ == "__main__":
    logger.info("Running pipeline directly from command line...")
    main()
