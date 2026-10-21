"""
Automation Logger & Screenshot Tracker.
Captures trace logs and screenshots during automated application runs.
"""

import os
from datetime import datetime
from typing import Optional
from config.logger import logger
from database.connection import SessionLocal
from database.repository import JobRepository
from config.settings import DATA_DIR

SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ApplicationLogger:
    def __init__(self, application_id: Optional[int] = None):
        self.application_id = application_id

    def log(self, level: str, message: str, step: str = "", driver=None) -> str:
        """Logs message to console and database, saving screenshot if driver is provided and level is ERROR."""
        logger.log(level if level in ["INFO", "WARNING", "ERROR"] else "INFO", f"[{step or 'Automation'}] {message}")

        screenshot_path = ""
        if driver and (level == "ERROR" or level == "SUCCESS"):
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"app_{self.application_id or 'run'}_{step}_{timestamp}.png"
            full_path = SCREENSHOTS_DIR / filename
            try:
                driver.save_screenshot(str(full_path))
                screenshot_path = str(full_path)
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

        # Persist to DB
        try:
            db = SessionLocal()
            repo = JobRepository(db)
            repo.add_automation_log(
                application_id=self.application_id,
                level=level,
                message=message,
                step=step,
                screenshot_path=screenshot_path
            )
            db.close()
        except Exception:
            pass

        return screenshot_path
