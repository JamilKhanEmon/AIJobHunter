"""
Job Liveness & Dead-Link Verification Engine.

Probes real company posting URLs with fast HTTP checks (no headless browser overhead)
to detect 404s, expired postings, filled positions, and closed requisitions.
"""

import re
import urllib.parse
from typing import Dict, Any, Tuple
import requests

# Curated phrases indicating a vacancy is closed or filled
HARD_EXPIRED_PATTERNS = [
    r"job (is )?no longer available",
    r"job.*no longer open",
    r"position has been filled",
    r"this job has expired",
    r"job posting has expired",
    r"no longer accepting applications",
    r"this (position|role|job) (is )?no longer",
    r"this job (listing )?is closed",
    r"this job post is closed",
    r"job (listing )?not found",
    r"page you are looking for doesn.?t exist",
    r"applications?\s+(?:(?:have|are|is)\s+)?closed",
    r"this position is closed",
    r"requisition has been closed",
    r"posting has closed",
    r"role has been filled",
]

HARD_EXPIRED_REGEX = re.compile("|".join(HARD_EXPIRED_PATTERNS), re.IGNORECASE)
EXPIRED_URL_PARAM = re.compile(r"[?&](error=true|status=expired|closed=1)", re.IGNORECASE)
LISTING_FALLBACK_REGEX = re.compile(r"\b\d+\s+jobs?\s+found\b", re.IGNORECASE)


class LivenessVerifier:
    """
    Lightweight HTTP prober to classify job URL vitality without Selenium/browser overhead.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    @classmethod
    def verify(cls, url: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Classifies the liveness of a job posting URL.
        Returns:
            verdict: 'LIVE' | 'EXPIRED' | 'UNCERTAIN'
            is_live: bool
            reason: str ('ok', 'http_gone', 'expired_body', 'expired_url', 'fallback_page', 'fetch_error')
            status_code: int
            final_url: str
        """
        if not url or not url.startswith("http"):
            return {
                "verdict": "UNCERTAIN",
                "is_live": False,
                "reason": "invalid_url",
                "status_code": 0,
                "final_url": url,
                "message": "URL is missing or invalid"
            }

        try:
            resp = requests.get(
                url,
                headers=cls.HEADERS,
                timeout=timeout,
                allow_redirects=True,
                stream=True
            )
            status = resp.status_code
            final_url = resp.url

            # HTTP gone
            if status in (404, 410):
                return {
                    "verdict": "EXPIRED",
                    "is_live": False,
                    "reason": "http_gone",
                    "status_code": status,
                    "final_url": final_url,
                    "message": f"Career portal returned HTTP {status} (Page Not Found / Expired)"
                }

            # Non-2xx and non-404 (e.g. 500, 403, Cloudflare challenge) -> Uncertain
            if status < 200 or status >= 300:
                return {
                    "verdict": "UNCERTAIN",
                    "is_live": True, # don't close prematurely on transient 403/500
                    "reason": "transient_status",
                    "status_code": status,
                    "final_url": final_url,
                    "message": f"Server returned status {status}; link may still be valid or protected"
                }

            # Check redirect to expired indicator
            if EXPIRED_URL_PARAM.search(final_url):
                return {
                    "verdict": "EXPIRED",
                    "is_live": False,
                    "reason": "expired_url",
                    "status_code": status,
                    "final_url": final_url,
                    "message": "Redirected to career error/expiration landing"
                }

            # Read partial content (first 50KB is sufficient to detect closure banner)
            raw_content = resp.raw.read(50000).decode("utf-8", errors="ignore")

            # Check hard-expired patterns in HTML body
            if HARD_EXPIRED_REGEX.search(raw_content):
                return {
                    "verdict": "EXPIRED",
                    "is_live": False,
                    "reason": "expired_body",
                    "status_code": status,
                    "final_url": final_url,
                    "message": "Posting body states role is closed, filled, or no longer accepting applications"
                }

            # Check generic fallback list
            if LISTING_FALLBACK_REGEX.search(raw_content):
                return {
                    "verdict": "EXPIRED",
                    "is_live": False,
                    "reason": "fallback_page",
                    "status_code": status,
                    "final_url": final_url,
                    "message": "URL redirected to general search index; original posting is gone"
                }

            # Healthy 200
            return {
                "verdict": "LIVE",
                "is_live": True,
                "reason": "ok",
                "status_code": status,
                "final_url": final_url,
                "message": "Job posting verified active on company career portal (HTTP 200)"
            }

        except requests.exceptions.Timeout:
            return {
                "verdict": "UNCERTAIN",
                "is_live": True,
                "reason": "timeout",
                "status_code": 0,
                "final_url": url,
                "message": "Connection timed out during liveness check"
            }
        except Exception as e:
            return {
                "verdict": "UNCERTAIN",
                "is_live": True,
                "reason": "fetch_error",
                "status_code": 0,
                "final_url": url,
                "message": f"Could not probe portal: {str(e)}"
            }
