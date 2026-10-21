"""
CLI script to run autonomous job application bot.
Usage:
    python3 scripts/run_apply.py --job-id 1 --dry-run
    python3 scripts/run_apply.py --url "https://www.linkedin.com/jobs/view/..." --dry-run
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from config.logger import logger
from database.connection import init_db, SessionLocal
from database.repository import JobRepository
from automation.browser_manager import BrowserManager
from automation.linkedin_easy_applier import LinkedInEasyApplier


def main():
    parser = argparse.ArgumentParser(description="Launch autonomous job application bot")
    parser.add_argument("--job-id", type=int, help="Job ID from database to apply to")
    parser.add_argument("--url", type=str, help="Direct job URL to apply to")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in dry-run mode (default: True)")
    parser.add_argument("--live", action="store_true", help="Perform real live submission")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()
    dry_run = not args.live

    target_url = args.url
    if not target_url and args.job_id:
        init_db()
        db = SessionLocal()
        repo = JobRepository(db)
        job = repo.get_job_by_id(args.job_id)
        if not job:
            logger.error(f"Job {args.job_id} not found in database")
            db.close()
            return
        target_url = job.url
        db.close()

    if not target_url:
        logger.error("Please provide either --job-id or --url")
        return

    logger.info(f"Target URL: {target_url} (Dry-Run: {dry_run}, Headless: {args.headless})")

    browser = BrowserManager(headless=args.headless)
    try:
        driver = browser.start_driver()
        applier = LinkedInEasyApplier(driver=driver)
        result = applier.apply(target_url, dry_run=dry_run)
        logger.info(f"Application finished with result: {result}")
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
