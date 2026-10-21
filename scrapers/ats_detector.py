"""
ATS Detector & Career Page Resolver.
Determines which ATS system a company uses and extracts the board token.
"""

import re
from typing import Tuple, Optional
import httpx
from bs4 import BeautifulSoup
from config.logger import logger


class ATSDetector:
    @staticmethod
    def detect_ats_from_url(url: str) -> Tuple[str, Optional[str]]:
        """
        Detects ATS type and token from URL.
        Returns: (ats_type, board_token)
        """
        url_lower = url.lower()

        # Greenhouse
        gh_match = re.search(r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([^/?#]+)", url_lower)
        if gh_match:
            return "greenhouse", gh_match.group(1)

        # Lever
        lever_match = re.search(r"jobs\.lever\.co/([^/?#]+)", url_lower)
        if lever_match:
            return "lever", lever_match.group(1)

        # Ashby
        ashby_match = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", url_lower)
        if ashby_match:
            return "ashby", ashby_match.group(1)

        # Workday
        wd_match = re.search(r"([^/?#]+)\.wd\d*\.myworkdayjobs\.com/([^/?#]+)", url_lower)
        if wd_match:
            return "workday", f"{wd_match.group(1)}/{wd_match.group(2)}"

        # LinkedIn
        if "linkedin.com/jobs" in url_lower:
            return "linkedin", None

        return "generic", None

    @classmethod
    def scan_career_page(cls, career_url: str) -> Tuple[str, Optional[str]]:
        """
        Fetches the company's career page HTML to inspect links and iframes for ATS embeds.
        """
        ats_type, token = cls.detect_ats_from_url(career_url)
        if ats_type != "generic":
            return ats_type, token

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.get(career_url)
                if resp.status_code != 200:
                    return "generic", None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Check iframes
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "")
                t, tok = cls.detect_ats_from_url(src)
                if t != "generic":
                    return t, tok

            # Check links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                t, tok = cls.detect_ats_from_url(href)
                if t != "generic":
                    return t, tok

            return "generic", None
        except Exception as e:
            logger.warning(f"Error inspecting career page {career_url}: {e}")
            return "generic", None
