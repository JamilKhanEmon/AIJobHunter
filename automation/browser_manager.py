"""
Browser Manager.
Spawns and configures Chrome WebDriver with stealth options, profile persistence, and humanized delays.
"""

import os
import random
import time
from typing import Optional
from config.logger import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config.settings import settings
from automation.stealth_patch import apply_stealth_evasion


class BrowserManager:
    def __init__(self, headless: Optional[bool] = None):
        self.headless = settings.headless if headless is None else headless
        self.driver: Optional[webdriver.Chrome] = None

    def start_driver(self) -> webdriver.Chrome:
        """Launches Chrome with anti-detection options."""
        logger.info(f"Starting Chrome WebDriver (headless={self.headless})...")

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("window-size=1400,900")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        # Persistent user data directory
        profile_dir = settings.user_data_dir
        options.add_argument(f"--user-data-dir={profile_dir}")

        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            # First try default system chromedriver
            self.driver = webdriver.Chrome(options=options)
        except Exception:
            # Fallback to ChromeDriverManager
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                logger.error(f"Failed to start Chrome driver: {e}")
                raise

        # Apply CDP stealth evasion
        apply_stealth_evasion(self.driver)
        logger.info("Chrome WebDriver started successfully with stealth patches.")
        return self.driver

    def human_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Randomized delay to emulate human reading and typing."""
        time.sleep(random.uniform(min_sec, max_sec))

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed cleanly.")
            except Exception as e:
                logger.warning(f"Error while quitting WebDriver: {e}")
            finally:
                self.driver = None
