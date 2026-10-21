"""
Greenhouse ATS Crawler.
Uses Greenhouse public boards API: https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
"""

from typing import List
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class GreenhouseCrawler(BaseScraper):
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def fetch_jobs(self, board_token: str) -> List[ScrapedJob]:
        """
        Fetches all active jobs for a company's Greenhouse board.
        e.g. board_token = 'stripe', 'figma', 'anthropic', etc.
        """
        clean_token = board_token.strip().lower()
        url = f"{self.BASE_URL}/{clean_token}/jobs?content=true"
        logger.info(f"GreenhouseCrawler: Fetching jobs from {url}")

        results: List[ScrapedJob] = []
        try:
            with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    logger.warning(f"Greenhouse board '{clean_token}' not found.")
                    return []
                resp.raise_for_status()
                data = resp.json()

            jobs_raw = data.get("jobs", [])
            company_name = clean_token.capitalize()

            for item in jobs_raw:
                title = item.get("title", "")
                external_id = str(item.get("id", ""))
                job_url = item.get("absolute_url", "")
                location = item.get("location", {}).get("name", "Remote") or "Remote"

                raw_content = item.get("content", "")
                text_content = ""
                if raw_content:
                    soup = BeautifulSoup(raw_content, "html.parser")
                    text_content = soup.get_text(separator="\n", strip=True)

                is_remote = "remote" in location.lower() or "remote" in title.lower() or "anywhere" in location.lower()

                departments = [d.get("name") for d in item.get("departments", []) if d.get("name")]
                dept = departments[0] if departments else None

                results.append(ScrapedJob(
                    title=title,
                    company=company_name,
                    url=job_url,
                    source="greenhouse",
                    external_id=external_id,
                    location=location,
                    remote=is_remote,
                    ats_type="greenhouse",
                    department=dept,
                    description=text_content
                ))

            logger.info(f"GreenhouseCrawler: Found {len(results)} jobs for '{company_name}'")
            return results
        except Exception as e:
            logger.error(f"Error crawling Greenhouse board '{clean_token}': {e}")
            return []
