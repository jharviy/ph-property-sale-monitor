"""
PH Foreclosed Properties ETL — CLI Entry Point

Usage:
    python main.py                        # full ETL + analysis for today
    python main.py --mode etl             # ETL only
    python main.py --mode analyze         # analysis on existing data
    python main.py --date 2026-06-12      # specific date
    python main.py --source BSP           # specific source (default: all enabled)
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


def run_etl(source_name: str, run_date: date) -> None:
    """Run the full ETL for one source."""
    extractor = EXTRACTOR_MAP[source_name]()
    transformer = TRANSFORMER_MAP[source_name]()
    loader = DatabaseLoader()

    pipeline = ETLPipeline(extractor, transformer, loader)
    pipeline.run(run_date)


def run_analysis(run_date: date | None) -> None:
    """Generate analysis report from existing DB data."""
    analyzer = PropertyAnalyzer()
    # path = analyzer.export_report(run_date)   
    path = analyzer.export_report(date.today())     #Analyze only today
    if path:
        logger.success(f"Open your report: {path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="PH Foreclosed Properties — ETL + Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                         # full run, today\n"
            "  python main.py --mode etl              # ETL only\n"
            "  python main.py --mode analyze          # analysis only\n"
            "  python main.py --date 2026-06-01       # specific date\n"
            "  python main.py --source BSP            # specific source\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["full", "etl", "analyze"],
        default="full",
        help="Pipeline mode (default: full)",
    )
    parser.add_argument(
        "--date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Run date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--source",
        choices=list(SOURCES.keys()),
        default=None,
        help="Which source to run (default: all enabled sources)",
    )

    args = parser.parse_args()
    run_date: date = args.date or date.today()

    enabled_sources = (
        [args.source] if args.source else [k for k, v in SOURCES.items() if v["enabled"]]
    )

    if args.mode in ("full", "etl"):
        for src in enabled_sources:
            run_etl(src, run_date)

    if args.mode in ("full", "analyze"):
        run_analysis(run_date if args.mode != "analyze" or args.date else None)


if __name__ == "__main__":
    logger.info("Running pipeline directly from command line...")
    main()
