"""
Autonomous Web Discovery Engine.
Automatically scans search engines, aggregators, and ATS networks by role and location (Bangladesh, Remote, Visa Sponsorship).
Zero manual link entry required.
"""

from typing import List, Dict, Any, Optional
import httpx
from config.logger import logger
from config.settings import settings
from scrapers.base_scraper import ScrapedJob
from scrapers.linkedin_scraper import LinkedInScraper


class AutonomousDiscoveryEngine:
    def __init__(self):
        self.linkedin_scraper = LinkedInScraper()

    def discover(self, roles: Optional[List[str]] = None, locations: Optional[List[str]] = None, limit_per_source: int = 15) -> List[ScrapedJob]:
        """
        Runs multi-channel autonomous web search for target roles and sub-areas.
        Discovers jobs without requiring manual company links.
        """
        target_roles = roles or settings.target_positions or ["Software Engineer", "AI Engineer", "Full Stack Developer"]
        target_locations = locations or ["Bangladesh", "Dhaka", "Remote"]

        discovered_jobs: List[ScrapedJob] = []
        seen_urls = set()

        logger.info(f"Starting Autonomous Discovery for roles: {target_roles} in locations: {target_locations}")

        # 1. Multi-location LinkedIn Public Discovery (Bangladesh Sub-areas & Remote)
        for role in target_roles[:3]: # Top 3 active roles
            for loc in target_locations:
                try:
                    logger.info(f"Auto-discovering '{role}' in '{loc}'...")
                    found = self.linkedin_scraper.fetch_jobs(keywords=role, location=loc, limit=limit_per_source)
                    for j in found:
                        if j.url and j.url not in seen_urls:
                            seen_urls.add(j.url)
                            discovered_jobs.append(j)
                except Exception as e:
                    logger.warning(f"Error discovering LinkedIn jobs for {role} in {loc}: {e}")

        # 2. Arbeitnow Discovery (Worldwide Remote & Visa Sponsorship roles)
        try:
            logger.info("Auto-discovering global tech jobs with Visa Sponsorship / Remote on Arbeitnow...")
            arbeitnow_jobs = self._fetch_arbeitnow_jobs(target_roles, limit=limit_per_source)
            for j in arbeitnow_jobs:
                if j.url and j.url not in seen_urls:
                    seen_urls.add(j.url)
                    discovered_jobs.append(j)
        except Exception as e:
            logger.warning(f"Error querying Arbeitnow feed: {e}")

        # 3. RemoteOK Worldwide Engineering Discovery
        try:
            logger.info("Auto-discovering global remote developer listings on RemoteOK...")
            remoteok_jobs = self._fetch_remoteok_jobs(target_roles, limit=limit_per_source)
            for j in remoteok_jobs:
                if j.url and j.url not in seen_urls:
                    seen_urls.add(j.url)
                    discovered_jobs.append(j)
        except Exception as e:
            logger.warning(f"Error querying RemoteOK feed: {e}")

        logger.info(f"Autonomous Discovery finished: Found {len(discovered_jobs)} total new jobs.")
        return discovered_jobs

    def _fetch_arbeitnow_jobs(self, target_roles: List[str], limit: int = 15, max_age_days: int = 7) -> List[ScrapedJob]:
        """Fetches live tech jobs with visa sponsorship / remote support and strict date freshness."""
        import time
        url = "https://www.arbeitnow.com/api/job-board-api"
        results = []
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", [])
            for item in data:
                # 1. Date Freshness Check
                created_at = item.get("created_at")
                if created_at and isinstance(created_at, (int, float)):
                    age_days = (time.time() - created_at) / 86400.0
                    if age_days > max_age_days:
                        continue # Skip stale job older than max_age_days

                title = item.get("title", "")
                title_lower = title.lower()
                desc_lower = item.get("description", "").lower()

                # 2. Rejection of Closed / Expired Postings
                if any(phrase in desc_lower for phrase in ["position filled", "applications closed", "no longer accepting", "deadline passed"]):
                    continue

                # Check role relevance
                matches_role = any(r.lower() in title_lower or r.lower() in desc_lower for r in target_roles) or "engineer" in title_lower or "developer" in title_lower
                if not matches_role:
                    continue

                is_remote = bool(item.get("remote"))
                has_visa = bool(item.get("visa_sponsorship")) or ("visa" in desc_lower and "sponsor" in desc_lower)
                
                loc = "Remote" if is_remote else item.get("location", "Global")
                if has_visa:
                    loc += " (Visa Sponsorship Supported)"

                results.append(ScrapedJob(
                    title=title,
                    company=item.get("company_name", "Global Tech"),
                    url=item.get("url", ""),
                    source="arbeitnow",
                    external_id=str(item.get("slug", "")),
                    location=loc,
                    remote=is_remote,
                    ats_type="arbeitnow",
                    description=item.get("description", "")
                ))
                if len(results) >= limit:
                    break
        return results

    def _fetch_remoteok_jobs(self, target_roles: List[str], limit: int = 15, max_age_days: int = 7) -> List[ScrapedJob]:
        """Fetches remote-first global software & AI jobs with date validation."""
        from datetime import datetime
        url = "https://remoteok.com/api"
        headers = {"User-Agent": "AutonomousJobHunterBot/1.0"}
        results = []
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data[1:] if len(data) > 1 else [] # first item is legal notice

            for item in items:
                # 1. Date Freshness Check
                raw_date = item.get("date")
                if raw_date:
                    try:
                        clean_date = raw_date.split("T")[0]
                        dt = datetime.strptime(clean_date, "%Y-%m-%d")
                        age_days = (datetime.utcnow() - dt).days
                        if age_days > max_age_days:
                            continue # Ignore jobs older than 7 days
                    except Exception:
                        pass

                pos = item.get("position", "")
                pos_lower = pos.lower()
                desc_lower = item.get("description", "").lower()

                # 2. Rejection of Closed / Expired Postings
                if any(phrase in desc_lower for phrase in ["position filled", "applications closed", "no longer accepting", "deadline passed"]):
                    continue

                matches_role = any(r.lower() in pos_lower for r in target_roles) or "engineer" in pos_lower or "developer" in pos_lower
                if not matches_role:
                    continue

                results.append(ScrapedJob(
                    title=pos,
                    company=item.get("company", "Remote Tech Co"),
                    url=item.get("url", ""),
                    source="remoteok",
                    external_id=str(item.get("id", "")),
                    location="Worldwide Remote",
                    remote=True,
                    ats_type="remoteok",
                    description=item.get("description", "")
                ))
                if len(results) >= limit:
                    break
        return results
