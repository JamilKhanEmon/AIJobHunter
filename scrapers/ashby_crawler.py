"""
Ashby ATS Crawler.
Uses Ashby public job board API: https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true
"""

from typing import List
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class AshbyCrawler(BaseScraper):
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    def fetch_jobs(self, board_token: str) -> List[ScrapedJob]:
        """
        Fetches all active jobs for an Ashby job board.
        e.g. board_token = 'retool', 'openai', 'ramp', 'cursor', etc.
        """
        clean_token = board_token.strip().lower()
        url = f"{self.BASE_URL}/{clean_token}?includeCompensation=true"
        logger.info(f"AshbyCrawler: Fetching jobs from {url}")

        results: List[ScrapedJob] = []
        try:
            with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    logger.warning(f"Ashby board '{clean_token}' not found.")
                    return []
                resp.raise_for_status()
                data = resp.json()

            jobs_raw = data.get("jobs", [])
            company_name = clean_token.capitalize()

            for item in jobs_raw:
                title = item.get("title", "")
                external_id = item.get("id", "")
                job_url = item.get("jobUrl", "")
                location = item.get("location", "Remote") or "Remote"
                is_remote = bool(item.get("isRemote", False)) or "remote" in location.lower() or "remote" in title.lower()

                raw_desc = item.get("descriptionHtml", "")
                text_content = ""
                if raw_desc:
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    text_content = soup.get_text(separator="\n", strip=True)

                department = item.get("department")

                salary_raw = None
                comp = item.get("compensation")
                if comp and isinstance(comp, dict):
                    comp_summary = comp.get("compensationSummary")
                    if comp_summary:
                        salary_raw = comp_summary

                results.append(ScrapedJob(
                    title=title,
                    company=company_name,
                    url=job_url,
                    source="ashby",
                    external_id=external_id,
                    location=location,
                    remote=is_remote,
                    ats_type="ashby",
                    department=department,
                    description=text_content,
                    salary_raw=salary_raw
                ))

            logger.info(f"AshbyCrawler: Found {len(results)} jobs for '{company_name}'")
            return results
        except Exception as e:
            logger.error(f"Error crawling Ashby board '{clean_token}': {e}")
            return []
