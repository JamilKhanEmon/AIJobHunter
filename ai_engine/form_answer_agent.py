"""
Form Answer Agent.
Answers application questions intelligently using candidate profile and LLM.
"""

from typing import Optional, List, Dict, Any
import yaml
from config.logger import logger
from config.settings import settings
from ai_engine.llm_router import LLMRouter
from ai_engine.prompts import FORM_ANSWER_SYSTEM_PROMPT, FORM_ANSWER_USER_TEMPLATE


class FormAnswerAgent:
    def __init__(self, router: Optional[LLMRouter] = None):
        self.router = router or LLMRouter()
        self.profile = settings.get_candidate_profile()
        self.screening_answers = self.profile.get("screening_answers", {})

    def answer_question(self, question: str, options: Optional[List[str]] = None, company: str = "", title: str = "") -> str:
        """
        Finds the best answer for an application form question.
        Checks pre-defined answers first; falls back to LLM reasoning if needed.
        """
        q_clean = question.strip().lower()

        # 1. Quick heuristic cache for common ATS fields
        if "authorized to work" in q_clean or "legally authorized" in q_clean:
            return self.screening_answers.get("legally_authorized_to_work", "Yes")

        if "sponsorship" in q_clean or "visa" in q_clean:
            return self.screening_answers.get("requires_visa_sponsorship", "No")

        if "salary" in q_clean or "compensation" in q_clean:
            return str(self.screening_answers.get("target_annual_salary_usd", "85000"))

        if "notice period" in q_clean or "how soon can you start" in q_clean:
            return self.screening_answers.get("current_notice_period", "2 weeks")

        if "years of experience" in q_clean:
            return str(self.screening_answers.get("years_of_experience", 5))

        if "gender" in q_clean:
            return self.screening_answers.get("gender_preference", "Decline to self-identify")

        if "disability" in q_clean:
            return self.screening_answers.get("disability_status", "No, I don't have a disability")

        if "veteran" in q_clean:
            return self.screening_answers.get("veteran_status", "I am not a protected veteran")

        # 2. LLM Prompting for complex or custom questions
        profile_str = yaml.dump(self.profile, default_flow_style=False)
        options_str = ", ".join(options) if options else "None (Free text field)"

        user_prompt = FORM_ANSWER_USER_TEMPLATE.format(
            candidate_profile=profile_str,
            company=company,
            title=title,
            question=question,
            options=options_str
        )

        answer = self.router.generate(
            system_prompt=FORM_ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt
        ).strip()

        # If options are provided, match the closest option
        if options:
            for opt in options:
                if opt.lower() in answer.lower():
                    return opt

        return answer
