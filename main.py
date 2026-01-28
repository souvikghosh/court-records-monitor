#!/usr/bin/env python3
"""
Court Records Monitor - Main Entry Point

Monitors public court records for new filings and sends notifications.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from src.config import SEARCH_TERMS, DATABASE_PATH, SCREENSHOT_ON_NEW
from src.database import Database
from src.scrapers import SCRAPERS
from src.notifiers import notify_all

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/monitor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def run_scraper(scraper_class, search_terms: list[str], db: Database, dry_run: bool = False):
    """Run a single scraper for all search terms."""
    new_records = []

    async with scraper_class() as scraper:
        for term in search_terms:
            logger.info(f"Searching '{term}' on {scraper.name}...")

            try:
                results = await scraper.search(term)

                for result in results:
                    record = scraper.to_court_record(result, term)
                    record_id, is_new = await db.add_record(record)

                    if is_new:
                        logger.info(f"NEW: {record.case_number} - {record.case_title[:50]}...")
                        record.id = record_id
                        new_records.append(record)

                        # Take screenshot if enabled
                        if SCREENSHOT_ON_NEW and not dry_run:
                            page = await scraper.new_page()
                            try:
                                await page.goto(record.url, wait_until="networkidle", timeout=30000)
                                await scraper.screenshot(page, record.case_number.replace("/", "-"))
                            except Exception as e:
                                logger.warning(f"Failed to screenshot {record.url}: {e}")
                            finally:
                                await page.close()

            except Exception as e:
                logger.error(f"Error searching '{term}' on {scraper.name}: {e}")

    return new_records


async def main(courts: list[str] | None = None, dry_run: bool = False):
    """Main entry point."""
    logger.info("=" * 60)
    logger.info(f"Court Records Monitor - Starting at {datetime.now().isoformat()}")
    logger.info("=" * 60)

    if not SEARCH_TERMS:
        logger.error("No search terms configured. Set SEARCH_TERMS in .env")
        return 1

    logger.info(f"Search terms: {SEARCH_TERMS}")

    # Determine which scrapers to run
    if courts:
        scrapers_to_run = {k: v for k, v in SCRAPERS.items() if k in courts}
        if not scrapers_to_run:
            logger.error(f"No valid courts specified. Available: {list(SCRAPERS.keys())}")
            return 1
    else:
        scrapers_to_run = SCRAPERS

    logger.info(f"Courts to search: {list(scrapers_to_run.keys())}")

    # Initialize database
    db = Database(DATABASE_PATH)
    await db.connect()

    try:
        all_new_records = []

        # Run each scraper
        for name, scraper_class in scrapers_to_run.items():
            logger.info(f"\n--- Running {name} scraper ---")
            new_records = await run_scraper(scraper_class, SEARCH_TERMS, db, dry_run)
            all_new_records.extend(new_records)

        # Report results
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Found {len(all_new_records)} new records")

        if all_new_records:
            for record in all_new_records:
                logger.info(f"  - [{record.court}] {record.case_number}: {record.case_title[:50]}...")

            # Send notifications
            if not dry_run:
                logger.info("\nSending notifications...")
                results = await notify_all(all_new_records)

                for notifier, success in results.items():
                    status = "sent" if success else "failed"
                    logger.info(f"  - {notifier}: {status}")

                # Mark as notified
                for record in all_new_records:
                    if record.id:
                        await db.mark_notified(record.id)
            else:
                logger.info("\n[DRY RUN] Skipping notifications")

        # Print stats
        stats = await db.get_stats()
        logger.info(f"\nDatabase stats:")
        logger.info(f"  Total records: {stats['total_records']}")
        logger.info(f"  By court: {stats['by_court']}")

        logger.info(f"\n{'=' * 60}")
        logger.info("Done")
        return 0

    finally:
        await db.close()


def cli():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Monitor public court records for new filings"
    )
    parser.add_argument(
        "--court", "-c",
        action="append",
        choices=list(SCRAPERS.keys()),
        help="Specific court(s) to search (can be repeated). Default: all"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Don't send notifications or take screenshots"
    )
    parser.add_argument(
        "--list-courts",
        action="store_true",
        help="List available courts and exit"
    )

    args = parser.parse_args()

    if args.list_courts:
        print("Available courts:")
        for name in SCRAPERS.keys():
            print(f"  - {name}")
        return 0

    return asyncio.run(main(courts=args.court, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(cli())
