"""
Resume Tailorer & Cover Letter Generator Agent.
Synthesizes customized cover letters and highlights specific experience relevant to each job.
"""

from typing import Optional
import yaml
from config.logger import logger
from config.settings import settings
from ai_engine.llm_router import LLMRouter
from ai_engine.prompts import COVER_LETTER_SYSTEM_PROMPT, COVER_LETTER_USER_TEMPLATE


class ResumeTailorer:
    def __init__(self, router: Optional[LLMRouter] = None):
        self.router = router or LLMRouter()
        self.profile = settings.get_candidate_profile()

    def generate_cover_letter(self, company: str, title: str, job_description: str) -> str:
        """Generates a tailored 3-paragraph cover letter for the given job."""
        personal = self.profile.get("personal_information", {})
        candidate_name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip() or "Candidate"

        profile_str = yaml.dump(self.profile, default_flow_style=False)
        user_prompt = COVER_LETTER_USER_TEMPLATE.format(
            candidate_name=candidate_name,
            company=company,
            title=title,
            candidate_profile=profile_str,
            job_description=job_description[:3000]
        )

        return self.router.generate(
            system_prompt=COVER_LETTER_SYSTEM_PROMPT,
            user_prompt=user_prompt
        ).strip()
