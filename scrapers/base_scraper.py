"""
Base Scraper Class & Job Item Data Model.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ScrapedJob:
    title: str
    company: str
    url: str
    source: str # greenhouse, lever, ashby, workday, linkedin
    external_id: Optional[str] = None
    location: str = "Remote"
    remote: bool = True
    ats_type: str = "generic"
    department: Optional[str] = None
    description: Optional[str] = None
    salary_raw: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseScraper(ABC):
    @abstractmethod
    def fetch_jobs(self, target: str) -> List[ScrapedJob]:
        """Fetch jobs for a given company board identifier or search keyword."""
        pass
