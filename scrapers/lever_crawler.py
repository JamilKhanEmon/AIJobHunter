"""
Lever ATS Crawler.
Uses Lever public API: https://api.lever.co/v0/postings/{board}?mode=json
"""

from typing import List
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class LeverCrawler(BaseScraper):
    BASE_URL = "https://api.lever.co/v0/postings"

    def fetch_jobs(self, board_token: str) -> List[ScrapedJob]:
        """
        Fetches all active jobs for a company's Lever board.
        e.g. board_token = 'spotify', 'netflix', 'palantir', etc.
        """
        clean_token = board_token.strip().lower()
        url = f"{self.BASE_URL}/{clean_token}?mode=json"
        logger.info(f"LeverCrawler: Fetching jobs from {url}")

        results: List[ScrapedJob] = []
        try:
            with httpx.Client(timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    # Try EU host
                    eu_url = f"https://api.eu.lever.co/v0/postings/{clean_token}?mode=json"
                    resp = client.get(eu_url)
                    if resp.status_code == 404:
                        logger.warning(f"Lever board '{clean_token}' not found.")
                        return []
                resp.raise_for_status()
                postings = resp.json()

            company_name = clean_token.capitalize()

            for item in postings:
                title = item.get("text", "")
                external_id = item.get("id", "")
                job_url = item.get("hostedUrl", "")

                categories = item.get("categories", {})
                location = categories.get("location", "Remote") or "Remote"
                dept = categories.get("department") or categories.get("team")
                workplace_type = (item.get("workplaceType") or "").lower()

                is_remote = (
                    workplace_type == "remote" or
                    "remote" in location.lower() or
                    "remote" in title.lower()
                )

                # Assemble description from description + lists
                desc_parts = []
                raw_desc = item.get("description", "")
                if raw_desc:
                    soup = BeautifulSoup(raw_desc, "html.parser")
                    desc_parts.append(soup.get_text(separator="\n", strip=True))

                for lst in item.get("lists", []):
                    header = lst.get("text", "")
                    content = lst.get("content", "")
                    if header:
                        desc_parts.append(f"\n{header}:")
                    if content:
                        soup = BeautifulSoup(content, "html.parser")
                        desc_parts.append(soup.get_text(separator="\n", strip=True))

                full_desc = "\n".join(desc_parts)

                # Salary range
                salary_raw = None
                salary_data = item.get("salaryRange")
                if salary_data and isinstance(salary_data, dict):
                    min_val = salary_data.get("min")
                    max_val = salary_data.get("max")
                    currency = salary_data.get("currency", "USD")
                    if min_val and max_val:
                        salary_raw = f"{currency} {min_val:,.0f} - {max_val:,.0f}"

                results.append(ScrapedJob(
                    title=title,
                    company=company_name,
                    url=job_url,
                    source="lever",
                    external_id=external_id,
                    location=location,
                    remote=is_remote,
                    ats_type="lever",
                    department=dept,
                    description=full_desc,
                    salary_raw=salary_raw
                ))

            logger.info(f"LeverCrawler: Found {len(results)} jobs for '{company_name}'")
            return results
        except Exception as e:
            logger.error(f"Error crawling Lever board '{clean_token}': {e}")
            return []
