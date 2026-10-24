"""
Repository for database access operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import Job, JobEvaluation, ApplicationRecord, AutomationLog


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_job_by_url(self, url: str) -> Optional[Job]:
        return self.db.query(Job).filter(Job.url == url).first()

    def get_job_by_id(self, job_id: int) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == job_id).first()

    def create_or_update_job(self, data: Dict[str, Any]) -> Job:
        url = data.get("url")
        job = self.get_job_by_url(url)
        if not job:
            job = Job(**data)
            self.db.add(job)
        else:
            for key, val in data.items():
                if val is not None:
                    setattr(job, key, val)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self, limit: int = 100, status: Optional[str] = None, search: Optional[str] = None) -> List[Job]:
        q = self.db.query(Job)
        if status:
            q = q.filter(Job.status == status)
        if search:
            search_fmt = f"%{search}%"
            q = q.filter((Job.title.ilike(search_fmt)) | (Job.company.ilike(search_fmt)))
        return q.order_by(Job.id.desc()).limit(limit).all()

    def prune_expired_jobs(self, max_age_days: int = 5) -> int:
        """
        Prunes outdated job listings older than max_age_days (Default: 5 days).
        Preserves active applications so historical records are intact.
        """
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        expired_jobs = self.db.query(Job).filter(
            Job.created_at < cutoff_date,
            Job.status != "APPLIED"
        ).all()

        count = len(expired_jobs)
        for j in expired_jobs:
            self.db.delete(j)
        if count > 0:
            self.db.commit()
        return count

    def purge_all_jobs(self) -> int:
        """Completely purges all job listings, evaluations, applications, and logs."""
        from database.models import JobEvaluation, ApplicationRecord, AutomationLog
        self.db.query(ApplicationRecord).delete()
        self.db.query(JobEvaluation).delete()
        self.db.query(AutomationLog).delete()
        deleted = self.db.query(Job).delete()
        self.db.commit()
        return deleted

    def get_unscored_jobs(self, limit: int = 50) -> List[Job]:
        return self.db.query(Job).filter(Job.evaluation == None).limit(limit).all()

    def save_evaluation(self, job_id: int, eval_data: Dict[str, Any]) -> JobEvaluation:
        job = self.get_job_by_id(job_id)
        if not job:
            raise ValueError(f"Job with id {job_id} not found")

        evaluation = self.db.query(JobEvaluation).filter(JobEvaluation.job_id == job_id).first()
        if not evaluation:
            evaluation = JobEvaluation(job_id=job_id, **eval_data)
            self.db.add(evaluation)
        else:
            for k, v in eval_data.items():
                setattr(evaluation, k, v)

        # Update job status based on evaluation
        job.status = "EVALUATED"
        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def create_application(self, job_id: int, cover_letter: Optional[str] = None) -> ApplicationRecord:
        app = self.db.query(ApplicationRecord).filter(ApplicationRecord.job_id == job_id).first()
        if not app:
            app = ApplicationRecord(job_id=job_id, cover_letter=cover_letter, status="PENDING")
            self.db.add(app)
            self.db.commit()
            self.db.refresh(app)
        return app

    def add_automation_log(self, application_id: Optional[int], level: str, message: str, step: str = "", screenshot_path: str = ""):
        log_entry = AutomationLog(
            application_id=application_id,
            level=level,
            message=message,
            step=step,
            screenshot_path=screenshot_path
        )
        self.db.add(log_entry)
        self.db.commit()
        return log_entry

    def get_stats(self) -> Dict[str, Any]:
        total_jobs = self.db.query(Job).count()
        evaluated_jobs = self.db.query(JobEvaluation).count()
        applied_jobs = self.db.query(ApplicationRecord).filter(ApplicationRecord.status == "SUBMITTED").count()
        high_matches = self.db.query(JobEvaluation).filter(JobEvaluation.score >= 80).count()

        return {
            "total_jobs": total_jobs,
            "evaluated_jobs": evaluated_jobs,
            "high_matches": high_matches,
            "applied_jobs": applied_jobs,
            "pending_evaluation": total_jobs - evaluated_jobs
        }
