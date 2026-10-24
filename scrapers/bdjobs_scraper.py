"""
Bdjobs.com Job Search & Scraper.
Scrapes local Bangladesh jobs (Dhaka, Chittagong, Sylhet, Anywhere in Bangladesh)
using the Bdjobs official Gateway API endpoints.
"""

from typing import List, Optional
import urllib.parse
import re
import httpx
from bs4 import BeautifulSoup
from config.logger import logger
from scrapers.base_scraper import BaseScraper, ScrapedJob


class BdjobsScraper(BaseScraper):
    SEARCH_API = "https://gateway.bdjobs.com/ActtivejobsTest/api/JobSubsystem/search"
    DETAILS_API = "https://gateway.bdjobs.com/ActtivejobsTest/api/JobSubsystem/jobDetails"
    BASE_WEB_URL = "https://bdjobs.com/h/details/{jobid}?ln=1"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bdjobs.com/h/jobs",
            "Origin": "https://bdjobs.com",
        }

    def fetch_jobs(self, keywords: str, limit: int = 20, fetch_full_details: bool = True) -> List[ScrapedJob]:
        """
        Fetch active jobs from Bdjobs matching keywords (e.g. 'Software Engineer', 'Python', 'Full Stack').
        """
        logger.info(f"BdjobsScraper: Querying jobs for '{keywords}' (limit: {limit})")

        params = {
            "keyword": keywords,
            "page": 1,
            "itemsPerPage": limit
        }

        results: List[ScrapedJob] = []

        try:
            with httpx.Client(timeout=15.0, headers=self.headers, follow_redirects=True) as client:
                resp = client.get(self.SEARCH_API, params=params)
                if resp.status_code != 200:
                    logger.warning(f"Bdjobs search API returned status {resp.status_code}")
                    return []

                data = resp.json()
                job_list = data.get("data", [])
                if not isinstance(job_list, list):
                    logger.info("Bdjobs returned no job list in response data.")
                    return []

                logger.info(f"Bdjobs returned {len(job_list)} jobs for '{keywords}'")

                for item in job_list[:limit]:
                    job_id = str(item.get("jobid", "")).strip()
                    if not job_id:
                        continue

                    title = item.get("jobTitle", "Software Engineer").strip()
                    company = item.get("companyName", "Confidential / Bdjobs Employer").strip()
                    location = item.get("location", "Bangladesh").strip()
                    experience = item.get("experience", "").strip()
                    deadline = item.get("deadline", "").strip()

                    job_url = self.BASE_WEB_URL.format(jobid=job_id)
                    description = f"Job Title: {title}\nCompany: {company}\nLocation: {location}\nExperience: {experience}\nApplication Deadline: {deadline}\nSource: Bdjobs.com\nJob URL: {job_url}"
                    salary_raw = "Negotiable"

                    # Fetch full details if enabled (caps at top 5 to keep search snappy)
                    if fetch_full_details and len(results) < 5:
                        try:
                            detail_resp = client.get(self.DETAILS_API, params={"jobid": job_id, "ln": 1}, timeout=5.0)
                            if detail_resp.status_code == 200:
                                ddata = detail_resp.json().get("data", [])
                                if isinstance(ddata, list) and ddata:
                                    d = ddata[0]
                                    salary_raw = d.get("JobSalaryRange") or d.get("JobSalaryRangeText") or salary_raw
                                    raw_html_desc = d.get("JobDescription", "") or ""
                                    raw_html_reqs = d.get("AdditionJobRequirements", "") or ""
                                    skills_req = d.get("SkillsRequired", "") or ""
                                    suggested_skills = d.get("SuggestedSkills", "") or ""
                                    apply_email = d.get("ApplyEmail", "") or ""

                                    soup_desc = BeautifulSoup(raw_html_desc, "html.parser").get_text("\n", strip=True)
                                    soup_reqs = BeautifulSoup(raw_html_reqs, "html.parser").get_text("\n", strip=True)

                                    description = f"""Job Title: {title}
Company: {company}
Location: {location}
Experience: {experience}
Salary: {salary_raw}
Deadline: {deadline}
Key Skills: {skills_req} | {suggested_skills}
Apply Instruction / Email: {apply_email}

--- Job Description ---
{soup_desc}

--- Requirements ---
{soup_reqs}

Apply on Bdjobs: {job_url}"""
                        except Exception as de:
                            logger.debug(f"Bdjobs details fetch failed for job {job_id}: {de}")

                    is_remote = any(w in (location + title + description).lower() for w in ["remote", "work from home"])

                    results.append(ScrapedJob(
                        title=title,
                        company=company,
                        url=job_url,
                        source="bdjobs",
                        external_id=f"bdjobs_{job_id}",
                        location=location or "Bangladesh",
                        remote=is_remote,
                        ats_type="bdjobs",
                        description=description,
                        salary_raw=salary_raw
                    ))

        except Exception as e:
            logger.error(f"Error fetching Bdjobs jobs for '{keywords}': {e}")

        return results
