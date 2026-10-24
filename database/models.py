"""
Database models representing Jobs, Evaluations, Applications, and Activity Logs.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user")
    applications = relationship("ApplicationRecord", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name or "",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "has_profile": self.profile is not None
        }


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    headline = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), default="Bangladesh")
    github_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    screening_answers = Column(JSON, nullable=True)
    resume_filename = Column(String(255), nullable=True)
    search_preferences = Column(JSON, nullable=True)
    api_keys = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

    def to_candidate_schema(self):
        full_name = self.user.full_name if self.user and self.user.full_name else "Candidate"
        name_parts = full_name.strip().split(" ", 1)
        first_name = name_parts[0] if name_parts else "Candidate"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        return {
            "personal_information": {
                "first_name": first_name,
                "last_name": last_name,
                "headline": self.headline or "Software Professional",
                "email": self.user.email if self.user else "",
                "phone_number": self.phone or "",
                "city": self.city or "",
                "country": self.country or "Bangladesh",
                "github_url": self.github_url or "",
                "linkedin_url": self.linkedin_url or "",
                "portfolio_url": self.portfolio_url or ""
            },
            "summary": self.summary or "",
            "skills": self.skills or {},
            "experience": self.experience or [],
            "education": self.education or [],
            "screening_answers": self.screening_answers or {},
            "api_keys": self.api_keys or {},
            "search_preferences": self.search_preferences or {}
        }


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    external_id = Column(String(255), index=True, nullable=True)
    source = Column(String(50), default="crawler") # greenhouse, lever, ashby, workday, linkedin
    company = Column(String(255), index=True, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    location = Column(String(255), default="Remote")
    remote = Column(Boolean, default=True)
    url = Column(Text, nullable=False, unique=True)
    ats_type = Column(String(50), default="generic")
    department = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    salary_raw = Column(String(255), nullable=True)
    status = Column(String(50), default="DISCOVERED") # DISCOVERED, EVALUATED, APPLIED, SKIPPED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="jobs")
    evaluation = relationship("JobEvaluation", back_populates="job", uselist=False, cascade="all, delete-orphan")
    application = relationship("ApplicationRecord", back_populates="job", uselist=False, cascade="all, delete-orphan")
    def to_dict(self):
        from scrapers.ghost_detector import GhostDetector
        from ai_engine.cv_matcher import CVMatcher

        ghost_data = GhostDetector.evaluate(
            title=self.title or "",
            company=self.company or "",
            description=self.description or "",
            created_at=self.created_at
        )

        cv_fit = CVMatcher.calculate_match(
            title=self.title or "",
            description=self.description or "",
            company=self.company or "",
            location=self.location or "Remote",
            remote=bool(self.remote),
            evaluation=self.evaluation
        )

        return {
            "id": self.id,
            "external_id": self.external_id,
            "source": self.source,
            "company": self.company,
            "title": self.title,
            "location": self.location,
            "remote": self.remote,
            "url": self.url,
            "ats_type": self.ats_type,
            "department": self.department,
            "description": self.description,
            "salary_raw": self.salary_raw,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "application": self.application.to_dict() if self.application else None,
            "ghost_analysis": ghost_data,
            "cv_match": cv_fit
        }


class JobEvaluation(Base):
    __tablename__ = "job_evaluations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    score = Column(Integer, nullable=False) # 0 - 100
    verdict = Column(String(50), nullable=False) # APPLY, SKIP, REVIEW
    pros = Column(JSON, default=list) # List of matching strengths
    cons = Column(JSON, default=list) # Potential concerns
    missing_skills = Column(JSON, default=list) # Skill gaps
    dealbreaker_triggered = Column(Boolean, default=False)
    dealbreaker_reason = Column(Text, nullable=True)
    full_rationale = Column(Text, nullable=True)
    model_used = Column(String(100), default="ollama/llama3.3")
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="evaluation")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "score": self.score,
            "verdict": self.verdict,
            "pros": self.pros or [],
            "cons": self.cons or [],
            "missing_skills": self.missing_skills or [],
            "dealbreaker_triggered": self.dealbreaker_triggered,
            "dealbreaker_reason": self.dealbreaker_reason,
            "full_rationale": self.full_rationale,
            "model_used": self.model_used,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None
        }


class ApplicationRecord(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String(50), default="PENDING") # PENDING, IN_PROGRESS, SUBMITTED, FAILED
    cover_letter = Column(Text, nullable=True)
    tailored_headline = Column(String(255), nullable=True)
    error_log = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="application")
    logs = relationship("AutomationLog", back_populates="application", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "status": self.status,
            "cover_letter": self.cover_letter,
            "tailored_headline": self.tailored_headline,
            "error_log": self.error_log,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)
    level = Column(String(20), default="INFO") # INFO, WARNING, ERROR, SUCCESS
    message = Column(Text, nullable=False)
    step = Column(String(100), nullable=True)
    screenshot_path = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    application = relationship("ApplicationRecord", back_populates="logs")

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "step": self.step,
            "screenshot_path": self.screenshot_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
