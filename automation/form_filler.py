"""
Form Filler Component.
Handles interacting with HTML inputs, selects, radios, checkboxes, and file uploads.
"""

import time
import random
from typing import List, Optional
from config.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class FormFiller:
    def __init__(self, driver):
        self.driver = driver

    def human_type(self, element, text: str, delay_range: tuple = (0.04, 0.12)):
        """Types text character-by-character to simulate natural human typing."""
        element.click()
        # Clear existing text
        element.send_keys(Keys.COMMAND + "a" if "mac" in self.driver.capabilities.get("platformName", "").lower() else Keys.CONTROL + "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.1)

        for char in str(text):
            element.send_keys(char)
            time.sleep(random.uniform(*delay_range))

    def select_dropdown_option(self, select_element, option_text: str) -> bool:
        """Selects an option in a standard HTML select element."""
        try:
            select = Select(select_element)
            # Try exact text match
            for opt in select.options:
                if option_text.lower() in opt.text.lower():
                    select.select_by_visible_text(opt.text)
                    return True
            # Fallback to first non-empty option
            if len(select.options) > 1:
                select.select_by_index(1)
                return True
        except Exception as e:
            logger.warning(f"Failed to select dropdown option: {e}")
        return False

    def check_radio_or_checkbox(self, element, desired_state: bool = True):
        """Clicks a radio button or checkbox if not already in desired state."""
        try:
            is_selected = element.is_selected()
            if is_selected != desired_state:
                self.driver.execute_script("arguments[0].click();", element)
        except Exception as e:
            logger.warning(f"Error clicking radio/checkbox: {e}")

    def upload_file(self, input_element, file_path: str):
        """Uploads a file to a file input element."""
        try:
            input_element.send_keys(file_path)
            time.sleep(1.0)
            logger.info(f"Uploaded file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to upload file to {input_element}: {e}")
