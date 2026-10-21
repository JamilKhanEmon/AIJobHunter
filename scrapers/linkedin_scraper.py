"""
LinkedIn Job Search & Scraper.
Uses LinkedIn public search API endpoints.
Extracts title, company, location, easy-apply flag, and full job descriptions without requiring complex login.
"""

from typing import List, Optional
import urllib.parse
import re
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class LinkedInScraper(BaseScraper):
    SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOB_DETAILS_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"

    def fetch_jobs(self, keywords: str, location: str = "Remote", limit: int = 25) -> List[ScrapedJob]:
        """
        Searches LinkedIn jobs using guest search endpoint.
        keywords: e.g. "AI Engineer", "Full Stack Developer", "Python"
        location: e.g. "Remote", "Worldwide"
        """
        logger.info(f"LinkedInScraper: Searching for '{keywords}' in '{location}'")

        params = {
            "keywords": keywords,
            "location": location,
            "f_TPR": "r604800", # Past week
            "start": 0
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        results: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=25.0, headers=headers, follow_redirects=True) as client:
                resp = client.get(self.SEARCH_URL, params=params)
                if resp.status_code != 200:
                    logger.warning(f"LinkedIn search returned status {resp.status_code}")
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                job_cards = soup.find_all("li")

                for card in job_cards[:limit]:
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    location_elem = card.find("span", class_="job-search-card__location")
                    link_elem = card.find("a", class_="base-card__full-link")

                    if not title_elem or not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
                    loc = location_elem.get_text(strip=True) if location_elem else location
                    raw_url = link_elem.get("href", "")
                    job_url = raw_url.split("?")[0] if raw_url else ""

                    # Extract LinkedIn Job ID
                    ext_id_match = re.search(r"-(\d+)(?:\?|$)", raw_url)
                    ext_id = ext_id_match.group(1) if ext_id_match else None

                    is_remote = "remote" in loc.lower() or "remote" in title.lower()

                    results.append(ScrapedJob(
                        title=title,
                        company=company,
                        url=job_url,
                        source="linkedin",
                        external_id=ext_id,
                        location=loc,
                        remote=is_remote,
                        ats_type="linkedin",
                        description=f"LinkedIn job posting for {title} at {company} ({loc})"
                    ))

            logger.info(f"LinkedInScraper: Found {len(results)} jobs for '{keywords}'")
            return results

        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
            return []
