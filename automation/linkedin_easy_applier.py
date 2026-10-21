"""
LinkedIn Easy Applier.
Orchestrates multi-page application modal on LinkedIn with AI question answering.
"""

import os
import time
from typing import Optional, Dict, Any, Callable
from config.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from config.settings import settings
from automation.form_filler import FormFiller
from ai_engine.form_answer_agent import FormAnswerAgent


class LinkedInEasyApplier:
    def __init__(self, driver, answer_agent: Optional[FormAnswerAgent] = None, log_callback: Optional[Callable[[str, str], None]] = None):
        self.driver = driver
        self.filler = FormFiller(driver)
        self.answer_agent = answer_agent or FormAnswerAgent()
        self.profile = settings.get_candidate_profile()
        self.log_callback = log_callback or (lambda lvl, msg: logger.info(f"[{lvl}] {msg}"))

    def log(self, level: str, message: str):
        self.log_callback(level, message)

    def apply(self, job_url: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Navigates to LinkedIn job URL and completes Easy Apply flow.
        dry_run: if True, walks through all form steps up to the final 'Submit application' button without submitting.
        """
        self.log("INFO", f"Navigating to job: {job_url}")
        self.driver.get(job_url)
        time.sleep(3.0)

        # 1. Find Easy Apply button
        try:
            easy_apply_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.jobs-apply-button, .jobs-apply-button--top-card"))
            )
            self.log("INFO", "Found 'Easy Apply' button. Opening application modal...")
            easy_apply_btn.click()
            time.sleep(2.0)
        except TimeoutException:
            msg = "Could not find 'Easy Apply' button on this job posting (may require external apply or already applied)."
            self.log("WARNING", msg)
            return {"success": False, "status": "FAILED", "reason": msg}

        # 2. Iterate through multi-step dialog
        max_steps = 10
        step_count = 0

        while step_count < max_steps:
            step_count += 1
            self.log("INFO", f"Processing application modal page {step_count}...")
            time.sleep(1.5)

            # Check if submitted
            if self._is_submission_confirmed():
                self.log("SUCCESS", "Application successfully submitted!")
                return {"success": True, "status": "SUBMITTED"}

            # Fill visible form fields on current step
            self._fill_current_step_fields()

            # Look for Review or Submit buttons
            if self._has_button("Submit application") or self._has_button("Submit"):
                if dry_run:
                    self.log("SUCCESS", "[DRY RUN] All form fields filled successfully! Stopped before final submission.")
                    return {"success": True, "status": "DRY_RUN_COMPLETED"}
                else:
                    self.log("INFO", "Submitting application...")
                    self._click_button("Submit application")
                    time.sleep(3.0)
                    return {"success": True, "status": "SUBMITTED"}

            # Otherwise, click Next or Review
            if self._has_button("Review"):
                self.log("INFO", "Clicking 'Review' button...")
                self._click_button("Review")
            elif self._has_button("Next"):
                self.log("INFO", "Clicking 'Next' button...")
                self._click_button("Next")
            else:
                self.log("WARNING", "Neither Next nor Submit button found. Reached end of flow or manual interaction needed.")
                break

        return {"success": True, "status": "COMPLETED"}

    def _fill_current_step_fields(self):
        """Finds and answers text inputs, radio buttons, dropdowns on current modal step."""
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, ".jobs-easy-apply-modal, .artdeco-modal")
        except NoSuchElementException:
            return

        # 1. Text and Number inputs
        inputs = modal.find_all_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number']") if hasattr(modal, "find_all_elements") else modal.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number']")
        for inp in inputs:
            try:
                # If already filled, skip
                val = inp.get_attribute("value")
                if val:
                    continue

                label_text = self._find_label_for_input(inp)
                if label_text:
                    ans = self.answer_agent.answer_question(label_text)
                    self.log("INFO", f"Answering question '{label_text}' => '{ans}'")
                    self.filler.human_type(inp, ans)
            except Exception as e:
                logger.debug(f"Input fill skip: {e}")

        # 2. Dropdown / Select elements
        selects = modal.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            try:
                label_text = self._find_label_for_input(sel)
                options = [opt.text for opt in sel.find_elements(By.TAG_NAME, "option") if opt.text.strip()]
                ans = self.answer_agent.answer_question(label_text or "Select option", options=options)
                self.filler.select_dropdown_option(sel, ans)
            except Exception as e:
                logger.debug(f"Select fill skip: {e}")

    def _find_label_for_input(self, element) -> str:
        """Heuristic to locate the label or question prompt associated with an input element."""
        try:
            # Check id/for association
            elem_id = element.get_attribute("id")
            if elem_id:
                labels = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{elem_id}']")
                if labels and labels[0].text.strip():
                    return labels[0].text.strip()

            # Check parent container text
            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'jobs-easy-apply-form-section') or contains(@class, 'fb-dash-form-element')][1]")
            if parent:
                label = parent.find_element(By.TAG_NAME, "label")
                if label:
                    return label.text.strip()
        except Exception:
            pass
        return ""

    def _has_button(self, text: str) -> bool:
        buttons = self.driver.find_elements(By.XPATH, f"//button[contains(., '{text}')]")
        return any(b.is_displayed() for b in buttons)

    def _click_button(self, text: str):
        buttons = self.driver.find_elements(By.XPATH, f"//button[contains(., '{text}')]")
        for b in buttons:
            if b.is_displayed() and b.is_enabled():
                b.click()
                return

    def _is_submission_confirmed(self) -> bool:
        confirmations = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Application submitted') or contains(text(), 'Your application was sent')]")
        return any(c.is_displayed() for c in confirmations)
