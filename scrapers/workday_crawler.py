"""
Workday ATS Crawler.
Uses Workday CXS endpoint: https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
"""

from typing import List
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class WorkdayCrawler(BaseScraper):
    def fetch_jobs(self, target: str) -> List[ScrapedJob]:
        """
        target format: "{tenant}/{site}"
        e.g. "ringcentral/RingCentral_Careers" or "nvidia/NVIDIAExternalCareerSite"
        """
        parts = target.strip().split("/")
        if len(parts) < 2:
            logger.warning(f"Invalid Workday target '{target}'. Expected 'tenant/site'.")
            return []

        tenant, site = parts[0], parts[1]
        url = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
        logger.info(f"WorkdayCrawler: Querying {url}")

        results: List[ScrapedJob] = []
        payload = {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": ""
        }

        try:
            with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Workday returned status {resp.status_code}")
                    return []
                data = resp.json()

            postings = data.get("jobPostings", [])
            for item in postings:
                title = item.get("title", "")
                ext_path = item.get("externalPath", "")
                full_url = f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}{ext_path}"
                location = item.get("locationsText", "Remote") or "Remote"
                is_remote = "remote" in location.lower() or "remote" in title.lower()

                results.append(ScrapedJob(
                    title=title,
                    company=tenant.capitalize(),
                    url=full_url,
                    source="workday",
                    external_id=item.get("bulletFields", [""])[0] if item.get("bulletFields") else None,
                    location=location,
                    remote=is_remote,
                    ats_type="workday",
                    description=f"Job posting on Workday for {tenant.capitalize()}: {title}"
                ))

            logger.info(f"WorkdayCrawler: Found {len(results)} jobs for {tenant}")
            return results
        except Exception as e:
            logger.error(f"Error crawling Workday target '{target}': {e}")
            return []
