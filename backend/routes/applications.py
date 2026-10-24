"""
Application Lifecycle & Portal Tracking Endpoints.
Replaces robotic Selenium auto-applying with structured career stage management,
direct career portal linking, real-time link liveness checks, and Ghost Job radar.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.connection import get_db
from database.repository import JobRepository
from database.models import Job, ApplicationRecord
from scrapers.ghost_detector import GhostDetector
from scrapers.liveness_verifier import LivenessVerifier
from backend.websocket import manager

router = APIRouter(prefix="/api/applications", tags=["Applications"])


class TrackApplicationPayload(BaseModel):
    status: str = "APPLIED" # SAVED, APPLIED, INTERVIEWING, OFFER, REJECTED, ARCHIVED
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    cover_letter: Optional[str] = None


@router.post("/track/{job_id}")
def track_job_application(job_id: int, payload: TrackApplicationPayload, db: Session = Depends(get_db)):
    """
    Updates or creates an application record when the user applies on the company's portal.
    """
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found")

    app = db.query(ApplicationRecord).filter(ApplicationRecord.job_id == job_id).first()
    new_status = payload.status.upper()

    applied_time = datetime.utcnow()
    if payload.applied_at:
        try:
            applied_time = datetime.fromisoformat(payload.applied_at)
        except Exception:
            pass

    if not app:
        app = ApplicationRecord(
            job_id=job_id,
            status=new_status,
            cover_letter=payload.cover_letter,
            error_log=payload.notes,
            applied_at=applied_time
        )
        db.add(app)
    else:
        app.status = new_status
        if payload.notes is not None:
            app.error_log = payload.notes
        if payload.cover_letter is not None:
            app.cover_letter = payload.cover_letter
        if new_status == "APPLIED" and not app.applied_at:
            app.applied_at = applied_time

    job.status = new_status
    db.commit()
    db.refresh(app)
    db.refresh(job)

    manager.broadcast_sync({
        "type": "APPLICATION_UPDATED",
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "status": new_status,
        "message": f"Updated application status for {job.company} to {new_status}."
    })

    return {
        "success": True,
        "job_id": job.id,
        "status": new_status,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "application": app.to_dict()
    }


@router.post("/verify-liveness/{job_id}")
def verify_job_liveness(job_id: int, db: Session = Depends(get_db)):
    """
    Probes the real company job posting URL to verify whether it is alive (HTTP 200) or closed/expired (404/filled).
    """
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = LivenessVerifier.verify(job.url)
    if result["verdict"] == "EXPIRED":
        job.status = "EXPIRED"
        db.commit()

    return {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "liveness": result
    }


@router.get("/ghost-radar/{job_id}")
def check_ghost_radar(job_id: int, db: Session = Depends(get_db)):
    """
    Evaluates the Ghost Job & Evergreen reality signals for a specific listing.
    """
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check repost count for same company & title
    repost_count = db.query(Job).filter(
        Job.company == job.company,
        Job.title == job.title
    ).count()

    evaluation = GhostDetector.evaluate(
        title=job.title,
        company=job.company,
        description=job.description or "",
        created_at=job.created_at,
        repost_count=max(1, repost_count)
    )

    return {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "ghost_analysis": evaluation
    }


@router.get("/summary")
def get_applications_summary(db: Session = Depends(get_db)):
    """
    Returns counts by application stage for the tracking board.
    """
    total = db.query(Job).count()
    applied = db.query(ApplicationRecord).filter(ApplicationRecord.status == "APPLIED").count()
    interviewing = db.query(ApplicationRecord).filter(ApplicationRecord.status == "INTERVIEWING").count()
    offers = db.query(ApplicationRecord).filter(ApplicationRecord.status == "OFFER").count()
    rejected = db.query(ApplicationRecord).filter(ApplicationRecord.status == "REJECTED").count()
    saved = db.query(ApplicationRecord).filter(ApplicationRecord.status == "SAVED").count()

    return {
        "total_jobs": total,
        "saved": saved,
        "applied": applied,
        "interviewing": interviewing,
        "offers": offers,
        "rejected": rejected
    }
