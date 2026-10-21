"""
Crawlers API Endpoints.
Triggers Greenhouse, Lever, Ashby, Workday, and LinkedIn crawlers.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.connection import get_db, SessionLocal
from database.repository import JobRepository
from scrapers.greenhouse_crawler import GreenhouseCrawler
from scrapers.lever_crawler import LeverCrawler
from scrapers.ashby_crawler import AshbyCrawler
from scrapers.workday_crawler import WorkdayCrawler
from scrapers.linkedin_scraper import LinkedInScraper
from config.settings import settings
from backend.websocket import manager

from scrapers.autonomous_discovery import AutonomousDiscoveryEngine

router = APIRouter(prefix="/api/crawlers", tags=["Crawlers"])


class CrawlRequest(BaseModel):
    source: str # greenhouse, lever, ashby, workday, linkedin
    target: str # company token or keyword (e.g. 'stripe', 'palantir', or 'AI Engineer')
    location: Optional[str] = "Remote"


class AutoDiscoveryRequest(BaseModel):
    roles: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    limit_per_source: Optional[int] = 10


def run_crawler_task(source: str, target: str, location: str):
    db = SessionLocal()
    repo = JobRepository(db)
    source_lower = source.lower()

    manager.broadcast_sync({
        "type": "CRAWLER_STARTED",
        "message": f"Starting crawler for {source.upper()}: '{target}'..."
    })

    try:
        scraped_jobs = []
        if source_lower == "greenhouse":
            crawler = GreenhouseCrawler()
            scraped_jobs = crawler.fetch_jobs(target)
        elif source_lower == "lever":
            crawler = LeverCrawler()
            scraped_jobs = crawler.fetch_jobs(target)
        elif source_lower == "ashby":
            crawler = AshbyCrawler()
            scraped_jobs = crawler.fetch_jobs(target)
        elif source_lower == "workday":
            crawler = WorkdayCrawler()
            scraped_jobs = crawler.fetch_jobs(target)
        elif source_lower == "linkedin":
            crawler = LinkedInScraper()
            scraped_jobs = crawler.fetch_jobs(keywords=target, location=location)

        saved_count = 0
        for s_job in scraped_jobs:
            repo.create_or_update_job(s_job.to_dict())
            saved_count += 1

        manager.broadcast_sync({
            "type": "CRAWLER_FINISHED",
            "message": f"Crawler finished: Discovered & saved {saved_count} jobs from {target}."
        })
    except Exception as e:
        manager.broadcast_sync({
            "type": "CRAWLER_ERROR",
            "message": f"Crawler failed for {target}: {str(e)}"
        })
    finally:
        db.close()


def run_autonomous_discovery_task(roles: Optional[List[str]], locations: Optional[List[str]], limit: int):
    db = SessionLocal()
    repo = JobRepository(db)
    manager.broadcast_sync({
        "type": "AUTO_DISCOVERY_STARTED",
        "message": "Autonomous Web Discovery initiated: Scanning LinkedIn, global remote boards & visa feeds..."
    })

    try:
        engine = AutonomousDiscoveryEngine()
        jobs = engine.discover(roles=roles, locations=locations, limit_per_source=limit)
        saved = 0
        for j in jobs:
            repo.create_or_update_job(j.to_dict())
            saved += 1

        manager.broadcast_sync({
            "type": "AUTO_DISCOVERY_FINISHED",
            "count": saved,
            "message": f"Autonomous Discovery Completed: {saved} fresh live jobs indexed into pipeline."
        })
    except Exception as e:
        manager.broadcast_sync({
            "type": "AUTO_DISCOVERY_ERROR",
            "message": f"Autonomous discovery error: {e}"
        })
    finally:
        db.close()


@router.post("/run")
def trigger_crawler(payload: CrawlRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_crawler_task, payload.source, payload.target, payload.location or "Remote")
    return {
        "success": True,
        "message": f"Crawl job initiated for {payload.source} with target '{payload.target}'."
    }


@router.post("/autonomous-discover")
def trigger_autonomous_discover(payload: AutoDiscoveryRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_autonomous_discovery_task,
        payload.roles,
        payload.locations,
        payload.limit_per_source or 10
    )
    return {
        "success": True,
        "message": "Autonomous Web Discovery launched in background. Monitoring live feeds for Bangladesh, Remote, and Visa Sponsorship jobs."
    }


@router.get("/targets")
def get_configured_targets():
    return {
        "ats_targets": settings.ats_targets,
        "search_preferences": {
            "positions": settings.target_positions,
            "locations": settings.target_locations,
            "remote_only": settings.remote_only
        }
    }

