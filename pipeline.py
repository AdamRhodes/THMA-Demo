"""ETL pipeline orchestrator — extracts from Salesforce, transforms, loads to SQL."""

import argparse
import logging
import sys
import uuid

from config import get_settings
from etl.extract import SalesforceExtractor
from etl.transform import TransformEngine
from etl.load import DatabaseLoader

ALL_OBJECTS = ["accounts", "contacts", "opportunities"]

logger = logging.getLogger("pipeline")


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler("pipeline.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def run(objects: list[str], dry_run: bool = False) -> str:
    settings = get_settings()
    run_id = str(uuid.uuid4())

    logger.info("=== Pipeline run %s ===", run_id)
    logger.info("Mode: %s | Dry-run: %s", "demo (SQLite)" if settings.demo_mode else "Azure SQL", dry_run)
    logger.info("Objects: %s", ", ".join(objects))

    extractor = SalesforceExtractor()
    transformer = TransformEngine()

    loader: DatabaseLoader | None = None
    if not dry_run:
        loader = DatabaseLoader()
        loader.ensure_demo_tables()
        loader.log_sync(run_id, "running")

    total_extracted = 0
    total_loaded = 0
    all_stats: list[dict] = []

    try:
        for obj in objects:
            # Extract
            extract_fn = getattr(extractor, f"extract_{obj}")
            raw = extract_fn()
            total_extracted += len(raw)

            # Transform
            transform_fn = getattr(transformer, f"transform_{obj}")
            df, stats = transform_fn(raw)
            all_stats.append(stats)

            # Load
            if not dry_run and loader is not None:
                loaded = loader.upsert(obj, df)
                total_loaded += loaded

        logger.info("=== Summary ===")
        for s in all_stats:
            logger.info(
                "  %s: %d extracted → %d transformed (%d dupes removed)",
                s["object"], s["input_count"], s["output_count"], s["dedup_count"],
            )
        logger.info("  Total: %d extracted, %d loaded", total_extracted, total_loaded)

        if not dry_run and loader is not None:
            loader.log_sync(run_id, "success", total_extracted, total_loaded)

    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        if loader is not None:
            loader.log_sync(run_id, "failed", total_extracted, total_loaded, str(exc))
        raise

    logger.info("=== Pipeline run %s complete ===", run_id)
    return run_id


def main() -> None:
    parser = argparse.ArgumentParser(description="THMA Salesforce → SQL ETL pipeline")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and transform only — no database writes.",
    )
    parser.add_argument(
        "--objects",
        nargs="+",
        choices=ALL_OBJECTS,
        default=ALL_OBJECTS,
        help="Objects to sync (default: all).",
    )
    args = parser.parse_args()

    setup_logging()
    run(args.objects, args.dry_run)


if __name__ == "__main__":
    main()
