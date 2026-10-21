"""
AI Evaluation & ATS Scoring API Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database.connection import get_db, SessionLocal
from database.repository import JobRepository
from ai_engine.ats_evaluator import ATSEvaluator
from ai_engine.resume_tailorer import ResumeTailorer
from backend.websocket import manager

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])


def evaluate_job_task(job_id: int):
    db = SessionLocal()
    repo = JobRepository(db)
    try:
        job = repo.get_job_by_id(job_id)
        if not job:
            return

        manager.broadcast_sync({
            "type": "EVALUATION_STARTED",
            "message": f"Evaluating '{job.title}' at '{job.company}'..."
        })

        evaluator = ATSEvaluator()
        result = evaluator.evaluate_job(
            title=job.title,
            company=job.company,
            description=job.description or "",
            location=job.location,
            remote=job.remote
        )

        saved_eval = repo.save_evaluation(job_id, result)

        manager.broadcast_sync({
            "type": "EVALUATION_COMPLETED",
            "job_id": job_id,
            "score": saved_eval.score,
            "verdict": saved_eval.verdict,
            "message": f"Evaluation Complete for {job.company}: Score {saved_eval.score}/100 ({saved_eval.verdict})"
        })
    except Exception as e:
        manager.broadcast_sync({
            "type": "EVALUATION_ERROR",
            "job_id": job_id,
            "message": f"Evaluation error on job {job_id}: {str(e)}"
        })
    finally:
        db.close()


def evaluate_all_pending_task():
    db = SessionLocal()
    repo = JobRepository(db)
    try:
        unscored = repo.get_unscored_jobs(limit=25)
        manager.broadcast_sync({
            "type": "BATCH_EVAL_STARTED",
            "message": f"Batch evaluation started for {len(unscored)} pending jobs."
        })

        evaluator = ATSEvaluator()
        for job in unscored:
            try:
                res = evaluator.evaluate_job(
                    title=job.title,
                    company=job.company,
                    description=job.description or "",
                    location=job.location,
                    remote=job.remote
                )
                repo.save_evaluation(job.id, res)
                manager.broadcast_sync({
                    "type": "EVALUATION_COMPLETED",
                    "job_id": job.id,
                    "score": res.get("score"),
                    "verdict": res.get("verdict"),
                    "message": f"Score {res.get('score')}/100: {job.company} - {job.title}"
                })
            except Exception as e:
                manager.broadcast_sync({
                    "type": "EVALUATION_ERROR",
                    "job_id": job.id,
                    "message": f"Skipped job {job.id} due to error: {e}"
                })

        manager.broadcast_sync({
            "type": "BATCH_EVAL_FINISHED",
            "message": "Batch evaluation completed!"
        })
    finally:
        db.close()


@router.post("/{job_id}")
def evaluate_single_job(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    background_tasks.add_task(evaluate_job_task, job_id)
    return {"success": True, "message": f"Evaluation scheduled for job {job_id}"}


@router.post("/all-pending/run")
def evaluate_all_pending(background_tasks: BackgroundTasks):
    background_tasks.add_task(evaluate_all_pending_task)
    return {"success": True, "message": "Batch evaluation started for all pending jobs"}


@router.post("/cover-letter/{job_id}")
def generate_cover_letter(job_id: int, db: Session = Depends(get_db)):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tailorer = ResumeTailorer()
    letter = tailorer.generate_cover_letter(
        company=job.company,
        title=job.title,
        job_description=job.description or ""
    )

    # Save to application record
    app = repo.create_application(job_id=job.id, cover_letter=letter)

    return {
        "success": True,
        "job_id": job_id,
        "cover_letter": letter,
        "application_id": app.id
    }
