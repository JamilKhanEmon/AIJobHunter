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
        prof = settings.get_candidate_profile()
        headline = (prof.get("personal_information", {}).get("headline") or "").strip()
        user_country = (prof.get("personal_information", {}).get("country") or "Bangladesh").strip()
        user_city = (prof.get("personal_information", {}).get("city") or "Dhaka").strip()

        # Dynamic target roles derived from uploaded CV headline + mission preferences
        dynamic_roles = []
        if roles:
            dynamic_roles.extend(roles)
        elif headline:
            dynamic_roles.append(headline)
            # Add complimentary search terms
            if any(k in headline.lower() for k in ["doctor", "physician", "medical", "surgeon", "clinic", "mbbs"]):
                dynamic_roles.extend(["Doctor", "Medical Officer", "General Physician"])
            elif any(k in headline.lower() for k in ["civil", "mechanical", "electrical", "structural", "architect"]):
                dynamic_roles.extend(["Civil Engineer", "Project Engineer", "Site Engineer"])
            elif any(k in headline.lower() for k in ["accountant", "audit", "finance", "banking", "tax"]):
                dynamic_roles.extend(["Accountant", "Senior Accountant", "Financial Analyst"])
            elif any(k in headline.lower() for k in ["nurse", "nursing"]):
                dynamic_roles.extend(["Staff Nurse", "Registered Nurse"])
            elif any(k in headline.lower() for k in ["teacher", "lecturer", "professor", "faculty"]):
                dynamic_roles.extend(["Lecturer", "Teacher", "Instructor"])
            elif "ai" in headline.lower() or "machine learning" in headline.lower():
                dynamic_roles.extend(["AI Engineer", "Machine Learning Engineer"])
            elif "design" in headline.lower() or "ux" in headline.lower():
                dynamic_roles.extend(["Product Designer", "UI/UX Designer"])
            elif "data" in headline.lower() or "analyst" in headline.lower():
                dynamic_roles.extend(["Data Analyst", "Data Engineer"])
            elif "full" in headline.lower() or "stack" in headline.lower() or "software" in headline.lower():
                dynamic_roles.extend(["Full Stack Developer", "Software Engineer"])
            elif settings.target_positions:
                dynamic_roles.extend(settings.target_positions)
        elif settings.target_positions:
            dynamic_roles.extend(settings.target_positions)
        else:
            dynamic_roles.extend(["Software Engineer", "AI Engineer", "Product Designer", "Data Analyst"])

        target_roles = list(dict.fromkeys([r.strip() for r in dynamic_roles if r and r.strip()]))

        # Dynamic target locations (Local candidate home city & country + Remote)
        dynamic_locs = []
        if locations:
            dynamic_locs.extend(locations)
        else:
            if user_country:
                dynamic_locs.append(user_country)
            if user_city and user_city != user_country:
                dynamic_locs.append(user_city)
            dynamic_locs.extend(["Remote", "Worldwide"])
        target_locations = list(dict.fromkeys([l.strip() for l in dynamic_locs if l and l.strip()]))

        discovered_jobs: List[ScrapedJob] = []
        seen_urls = set()

        logger.info(f"Starting Multi-Profession Autonomous Discovery for roles: {target_roles[:4]} in locations: {target_locations}")

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

        # 4. Remotive Worldwide Developer Hub
        try:
            logger.info("Auto-discovering software engineering roles on Remotive...")
            remotive_jobs = self._fetch_remotive_jobs(target_roles, limit=limit_per_source)
            for j in remotive_jobs:
                if j.url and j.url not in seen_urls:
                    seen_urls.add(j.url)
                    discovered_jobs.append(j)
        except Exception as e:
            logger.warning(f"Error querying Remotive feed: {e}")

        # 5. Jobicy Global Engineering Feeds
        try:
            logger.info("Auto-discovering developer listings on Jobicy...")
            jobicy_jobs = self._fetch_jobicy_jobs(target_roles, limit=limit_per_source)
            for j in jobicy_jobs:
                if j.url and j.url not in seen_urls:
                    seen_urls.add(j.url)
                    discovered_jobs.append(j)
        except Exception as e:
            logger.warning(f"Error querying Jobicy feed: {e}")

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

    def _fetch_remotive_jobs(self, target_roles: List[str], limit: int = 20, max_age_days: int = 14) -> List[ScrapedJob]:
        """Fetches developer and AI roles from Remotive's live public API."""
        from datetime import datetime
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
        results = []
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json().get("jobs", [])
                for item in data:
                    raw_date = item.get("publication_date")
                    if raw_date:
                        try:
                            clean_date = raw_date.split("T")[0]
                            dt = datetime.strptime(clean_date, "%Y-%m-%d")
                            age_days = (datetime.utcnow() - dt).days
                            if age_days > max_age_days:
                                continue
                        except Exception:
                            pass

                    title = item.get("title", "")
                    title_lower = title.lower()
                    desc = item.get("description", "")

                    matches_role = any(r.lower() in title_lower for r in target_roles) or "engineer" in title_lower or "developer" in title_lower
                    if not matches_role:
                        continue

                    candidate_loc = item.get("candidate_required_location", "Worldwide Remote")

                    results.append(ScrapedJob(
                        title=title,
                        company=item.get("company_name", "Remote Tech"),
                        url=item.get("url", ""),
                        source="remotive",
                        external_id=str(item.get("id", "")),
                        location=candidate_loc if candidate_loc else "Worldwide Remote",
                        remote=True,
                        ats_type="remotive",
                        description=desc
                    ))
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"Error querying Remotive feed: {e}")
        return results

    def _fetch_jobicy_jobs(self, target_roles: List[str], limit: int = 20, max_age_days: int = 14) -> List[ScrapedJob]:
        """Fetches developer and engineering roles from Jobicy's live public API."""
        from datetime import datetime
        url = "https://jobicy.com/api/v2/remote-jobs?count=40&tag=dev"
        results = []
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json().get("jobs", [])
                for item in data:
                    pub_date = item.get("pubDate")
                    if pub_date:
                        try:
                            clean_date = pub_date.split("T")[0].split(" ")[0]
                            dt = datetime.strptime(clean_date, "%Y-%m-%d")
                            age_days = (datetime.utcnow() - dt).days
                            if age_days > max_age_days:
                                continue
                        except Exception:
                            pass

                    title = item.get("jobTitle", "")
                    title_lower = title.lower()
                    desc = item.get("jobDescription", "")

                    matches_role = any(r.lower() in title_lower for r in target_roles) or "engineer" in title_lower or "developer" in title_lower
                    if not matches_role:
                        continue

                    geo = item.get("jobGeo", "Anywhere")
                    results.append(ScrapedJob(
                        title=title,
                        company=item.get("companyName", "Tech Corp"),
                        url=item.get("url", ""),
                        source="jobicy",
                        external_id=str(item.get("id", "")),
                        location=f"Remote ({geo})",
                        remote=True,
                        ats_type="jobicy",
                        description=desc
                    ))
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"Error querying Jobicy feed: {e}")
        return results
