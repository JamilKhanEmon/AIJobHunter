"""
CV-to-Job Match Engine.

Pure deterministic and intelligent scoring of an uploaded Candidate CV against vacancy postings:
1. Requirements & Core Qualification Coverage (Weight 40%)
2. Technical Skills & Keyword Overlap (Weight 30%)
3. Job Title & Role Alignment (Weight 20%)
4. Seniority & Experience Fit (Weight 10%)

Computes matched skills chips, missing skill gaps, dealbreaker warnings, and personalized match scores (0-100%).
"""

import re
from typing import Dict, Any, List, Set, Optional
from config.settings import settings


class CVMatcher:
    """
    Computes precise, deterministic alignment between candidate's parsed CV and job vacancy postings.
    """

    @classmethod
    def get_candidate_flat_skills(cls, profile: Optional[Dict[str, Any]] = None) -> Set[str]:
        prof = profile or settings.get_candidate_profile()
        skills_dict = prof.get("skills", {})
        flat = set()
        if isinstance(skills_dict, dict):
            for category, skill_list in skills_dict.items():
                if isinstance(skill_list, list):
                    for s in skill_list:
                        if isinstance(s, str) and s.strip():
                            flat.add(s.strip().lower())
        elif isinstance(skills_dict, list):
            for s in skills_dict:
                if isinstance(s, str) and s.strip():
                    flat.add(s.strip().lower())
        return flat

    @classmethod
    def extract_job_skills(cls, text: str, candidate_skills: Optional[Set[str]] = None) -> Set[str]:
        if not text:
            return set()
        lower_text = text.lower()
        
        # Universal multi-profession skills catalog (Tech, Design, Product, Data, Marketing, QA, DevOps)
        BROAD_SKILL_CATALOG = [
            # Software & Web
            "python", "javascript", "typescript", "go", "golang", "rust", "java", "c++", "c#", ".net", "ruby", "php",
            "react", "react.js", "next.js", "vue", "vue.js", "angular", "svelte", "node.js", "express",
            "fastapi", "django", "flask", "spring", "ruby on rails", "laravel", "tailwind", "css3", "html5", "graphql", "rest api", "rest",
            # Cloud & DevOps
            "docker", "kubernetes", "k8s", "terraform", "ansible", "aws", "gcp", "azure", "linux", "ci/cd", "nginx", "microservices",
            # Databases
            "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "sql", "sqlite", "supabase", "sqlalchemy",
            # AI & Data Science
            "llm", "llms", "rag", "langchain", "langgraph", "crewai", "openai", "gpt-4o", "gemini", "ollama", "hugging face",
            "pytorch", "tensorflow", "keras", "deep learning", "machine learning", "nlp", "computer vision", "yolo", "opencv",
            "scikit-learn", "xgboost", "lightgbm", "pandas", "numpy", "power bi", "tableau", "statistics", "data analysis",
            # Design & Creative
            "figma", "ui/ux", "ui design", "ux design", "user research", "wireframing", "prototyping", "adobe xd", "photoshop", "illustrator",
            # Product, Agile & Management
            "product management", "scrum", "agile", "jira", "sprint planning", "product roadmap", "stakeholder management", "project management",
            # Automation & Testing
            "n8n", "workflow automation", "selenium", "playwright", "cypress", "jest", "pytest", "qa", "test automation", "manual testing",
            # Marketing & Growth
            "seo", "sem", "content marketing", "copywriting", "growth marketing", "social media", "google analytics", "hubspot", "crm",
            # Healthcare, Medical & Clinical
            "clinical diagnosis", "patient care", "surgery", "pharmacology", "internal medicine", "pediatrics", "pathology", "nursing",
            "healthcare management", "emergency medicine", "medical research", "radiology", "icu", "public health", "mbbs", "bds", "telemedicine",
            # Core Engineering (Civil, Mechanical, Electrical)
            "autocad", "cad", "solidworks", "matlab", "structural engineering", "construction management", "hvac", "plc", "revit", "mep",
            "circuit design", "power systems", "quality control", "industrial automation", "site supervision",
            # Finance, Accounting & Banking
            "auditing", "taxation", "financial reporting", "quickbooks", "ifrs", "gaap", "cost accounting", "general ledger",
            "financial analysis", "banking operations", "credit underwriting", "risk management", "payroll", "budgeting",
            # Education, Legal & Operations
            "curriculum development", "classroom management", "pedagogy", "academic research", "tutoring", "legal compliance",
            "contract negotiation", "talent acquisition", "hr management", "employee relations", "operations management", "supply chain"
        ]

        found = set()
        for kw in BROAD_SKILL_CATALOG:
            pattern = r"(?:\b|_)" + re.escape(kw) + r"(?:\b|_)"
            if re.search(pattern, lower_text):
                found.add(kw)

        # Dynamic Candidate-Specific Skills: Check if ANY skill from candidate's CV is in the job text
        if candidate_skills:
            for cand_skill in candidate_skills:
                if len(cand_skill) >= 3 and cand_skill not in found:
                    pattern = r"(?:\b|_)" + re.escape(cand_skill) + r"(?:\b|_)"
                    if re.search(pattern, lower_text):
                        found.add(cand_skill)

        return found

    @classmethod
    def calculate_match(
        cls,
        title: str,
        description: str,
        company: str = "",
        location: str = "Remote",
        remote: bool = True,
        profile: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Calculates 4-category weighted fit of candidate CV against vacancy.
        Prioritizes LLM evaluation when available, falling back to deterministic matrix.
        """
        prof = profile or settings.get_candidate_profile()
        candidate_skills = cls.get_candidate_flat_skills(prof)
        job_skills = cls.extract_job_skills(f"{title} {description}", candidate_skills=candidate_skills)

        # Category 1: Skills & Keyword Match (Weight 30%)
        if job_skills:
            matched_set = candidate_skills.intersection(job_skills)
            missing_set = job_skills.difference(candidate_skills)
            skills_score = int((len(matched_set) / max(1, len(job_skills))) * 100)
            matched_skills = sorted(list(matched_set))
            missing_skills = sorted(list(missing_set))
        else:
            matched_skills = sorted(list(candidate_skills))[:5]
            missing_skills = []
            skills_score = 75

        # Category 2: Requirements & Domain Alignment (Weight 40%)
        summary = (prof.get("summary") or "").lower()
        title_lower = title.lower()
        desc_lower = description.lower()
        candidate_headline = (prof.get("personal_information", {}).get("headline") or "").lower()

        req_score = 60 # baseline
        if any(term in desc_lower for term in candidate_skills):
            req_score += 20

        # Dynamically extract key profession words from candidate's headline and check in job title/desc
        headline_tokens = [t for t in re.findall(r"[a-zA-Z]{3,}", candidate_headline) if t not in ["and", "the", "for", "with"]]
        if any(tok in title_lower or tok in desc_lower for tok in headline_tokens):
            req_score += 20

        req_score = min(100, max(40, req_score))

        # Category 3: Title & Role Alignment (Weight 20%)
        target_positions = [p.lower() for p in settings.target_positions]
        title_score = 50

        # 1. Check against headline tokens
        matched_headline_tokens = [tok for tok in headline_tokens if tok in title_lower]
        if matched_headline_tokens:
            title_score = min(98, 65 + (len(matched_headline_tokens) * 15))

        # 2. Check against target positions
        for target in target_positions:
            words = target.split()
            if any(w in title_lower for w in words if len(w) > 3):
                title_score = max(title_score, 90)
                break

        # Category 4: Seniority Fit (Weight 10%)
        seniority_score = 80
        if "senior" in title_lower or "staff" in title_lower or "lead" in title_lower or "principal" in title_lower or "manager" in title_lower:
            if any(k in candidate_headline or k in summary for k in ["senior", "lead", "staff", "manager", "5+", "4+"]):
                seniority_score = 100
            else:
                seniority_score = 65
        elif "junior" in title_lower or "entry" in title_lower or "associate" in title_lower:
            seniority_score = 80

        # Weighted aggregate score (4-tier 40/30/20/10 formula)
        overall = int(
            (req_score * 0.40) +
            (skills_score * 0.30) +
            (title_score * 0.20) +
            (seniority_score * 0.10)
        )
        overall = max(10, min(99, overall))

        is_llm = False
        highlights = []

        # Check if this job has an existing rich LLM Evaluation stored in DB
        if evaluation:
            llm_score = getattr(evaluation, "score", None)
            if llm_score is not None and int(llm_score) > 0:
                overall = int(llm_score)
                is_llm = True
                llm_pros = getattr(evaluation, "pros", []) or []
                llm_missing = getattr(evaluation, "missing_skills", []) or []
                if llm_pros:
                    highlights = [str(p) for p in llm_pros[:3]]
                if llm_missing:
                    missing_skills = [str(m).title() for m in llm_missing]

        # Verdict
        if overall >= 80:
            verdict = "STRONG_MATCH"
            verdict_label = "🌟 Top Match (AI)" if is_llm else "🌟 Top Match"
            badge_class = "score-high"
        elif overall >= 65:
            verdict = "GOOD_FIT"
            verdict_label = "🎯 Good Fit (AI)" if is_llm else "🎯 Good Fit"
            badge_class = "score-mid"
        else:
            verdict = "LOW_FIT"
            verdict_label = "Skill Gap"
            badge_class = "score-low"

        # Fallback highlights if not already supplied by LLM
        if not highlights:
            if matched_skills:
                highlights.append(f"Direct match: {', '.join(matched_skills[:4])}")
            if remote and prof.get("personal_information", {}).get("country"):
                highlights.append("Remote / Global candidate compatibility")
            if title_score >= 80:
                highlights.append(f"Strong role alignment with target career profile")

        return {
            "score": overall,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "badge_class": badge_class,
            "is_llm_evaluated": is_llm,
            "matched_skills": [s.title() for s in matched_skills],
            "missing_skills": [s.title() for s in missing_skills],
            "breakdown": {
                "requirements_coverage": req_score,
                "skills_match": skills_score,
                "title_alignment": title_score,
                "seniority_fit": seniority_score
            },
            "highlights": highlights
        }
