"""
ATS Scoring & Evaluation Agent.
Calculates job match score, dealbreaker checks, and STAR alignment.
"""

from typing import Dict, Any, Optional
import yaml
from config.logger import logger
from config.settings import settings
from ai_engine.llm_router import LLMRouter
from ai_engine.prompts import JOB_EVALUATION_SYSTEM_PROMPT, JOB_EVALUATION_USER_TEMPLATE


class ATSEvaluator:
    def __init__(self, router: Optional[LLMRouter] = None):
        self.router = router or LLMRouter()
        self.profile = settings.get_candidate_profile()

    def evaluate_job(self, title: str, company: str, description: str, location: str = "Remote", remote: bool = True, profile: Optional[dict] = None) -> Dict[str, Any]:
        """
        Evaluates a job posting against candidate resume profile.
        Returns match score (0-100), verdict, pros, cons, missing skills, and rationale.
        """
        logger.info(f"Evaluating job '{title}' at '{company}'...")

        active_profile = profile or self.profile
        profile_str = yaml.dump(active_profile, default_flow_style=False)
        system_prompt = JOB_EVALUATION_SYSTEM_PROMPT.replace(
            "{home_country}", settings.home_country
        )
        user_prompt = JOB_EVALUATION_USER_TEMPLATE.format(
            home_country=settings.home_country,
            home_city=settings.home_city,
            candidate_profile=profile_str,
            company=company,
            title=title,
            location=location,
            remote="Yes" if remote else "No",
            job_description=description[:4000] # Cap context window safely
        )

        evaluation_result = self.router.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # Enforce score bounds and types
        score = int(evaluation_result.get("score", 70))
        score = max(0, min(100, score))
        evaluation_result["score"] = score

        verdict = evaluation_result.get("verdict", "REVIEW").upper()
        if verdict not in ["APPLY", "REVIEW", "SKIP"]:
            verdict = "APPLY" if score >= settings.min_match_score else "REVIEW"
        evaluation_result["verdict"] = verdict

        logger.info(f"Job evaluated: {company} - {title} => Score: {score}/100, Verdict: {verdict}")
        return evaluation_result
