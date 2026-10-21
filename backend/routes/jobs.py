"""
Jobs API Endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.connection import get_db
from database.repository import JobRepository
from database.models import Job

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class JobCreatePayload(BaseModel):
    title: str
    company: str
    url: str
    location: Optional[str] = "Remote"
    remote: Optional[bool] = True
    ats_type: Optional[str] = "generic"
    description: Optional[str] = ""
    source: Optional[str] = "manual"


@router.get("")
def list_jobs(
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    repo = JobRepository(db)
    jobs = repo.list_jobs(limit=limit, status=status, search=search)
    return [job.to_dict() for job in jobs]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.post("")
def create_job(payload: JobCreatePayload, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.create_or_update_job(payload.dict())
    return job.to_dict()


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"success": True, "message": f"Job {job_id} deleted"}
