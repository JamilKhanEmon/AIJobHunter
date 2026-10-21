"""
CLI script to run crawlers directly from the terminal.
Usage:
    python3 scripts/run_crawler.py --source greenhouse --target stripe
    python3 scripts/run_crawler.py --source lever --target spotify
    python3 scripts/run_crawler.py --source ashby --target openai
    python3 scripts/run_crawler.py --source linkedin --target "AI Engineer"
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from config.logger import logger
from database.connection import init_db, SessionLocal
from database.repository import JobRepository
from scrapers.greenhouse_crawler import GreenhouseCrawler
from scrapers.lever_crawler import LeverCrawler
from scrapers.ashby_crawler import AshbyCrawler
from scrapers.workday_crawler import WorkdayCrawler
from scrapers.linkedin_scraper import LinkedInScraper


def main():
    parser = argparse.ArgumentParser(description="Run ATS & LinkedIn job crawlers")
    parser.add_argument("--source", type=str, required=True, choices=["greenhouse", "lever", "ashby", "workday", "linkedin"], help="Source type")
    parser.add_argument("--target", type=str, required=True, help="Company board name or search keyword")
    parser.add_argument("--location", type=str, default="Remote", help="Job location filter")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    repo = JobRepository(db)

    logger.info(f"Starting {args.source.upper()} crawler for target '{args.target}'...")

    if args.source == "greenhouse":
        crawler = GreenhouseCrawler()
        jobs = crawler.fetch_jobs(args.target)
    elif args.source == "lever":
        crawler = LeverCrawler()
        jobs = crawler.fetch_jobs(args.target)
    elif args.source == "ashby":
        crawler = AshbyCrawler()
        jobs = crawler.fetch_jobs(args.target)
    elif args.source == "workday":
        crawler = WorkdayCrawler()
        jobs = crawler.fetch_jobs(args.target)
    elif args.source == "linkedin":
        crawler = LinkedInScraper()
        jobs = crawler.fetch_jobs(keywords=args.target, location=args.location)

    logger.info(f"Fetched {len(jobs)} jobs. Saving to database...")
    saved_count = 0
    for j in jobs:
        repo.create_or_update_job(j.to_dict())
        saved_count += 1

    db.close()
    logger.info(f"Successfully saved {saved_count} jobs from {args.target} into database.")


if __name__ == "__main__":
    main()
