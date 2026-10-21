"""
Dashboard Statistics & Metrics Endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.connection import get_db
from database.models import Job, JobEvaluation, ApplicationRecord
from database.repository import JobRepository

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("")
def get_dashboard_stats(db: Session = Depends(get_db)):
    repo = JobRepository(db)
    base_stats = repo.get_stats()

    # ATS Source distribution
    sources = db.query(Job.source, func.count(Job.id)).group_by(Job.source).all()
    source_dist = {s: count for s, count in sources}

    # Status distribution
    statuses = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    status_dist = {st: count for st, count in statuses}

    # Recommendation breakdown
    eval_breakdown = db.query(JobEvaluation.verdict, func.count(JobEvaluation.id)).group_by(JobEvaluation.verdict).all()
    verdict_dist = {v: count for v, count in eval_breakdown}

    return {
        **base_stats,
        "source_distribution": source_dist,
        "status_distribution": status_dist,
        "verdict_distribution": verdict_dist
    }
