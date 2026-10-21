"""
Automation & Browser Apply Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database.connection import get_db, SessionLocal
from database.repository import JobRepository
from database.models import AutomationLog, Job
from automation.browser_manager import BrowserManager
from automation.linkedin_easy_applier import LinkedInEasyApplier
from automation.universal_ats_applier import UniversalATSApplier
from automation.application_logger import ApplicationLogger
from backend.websocket import manager

router = APIRouter(prefix="/api/automation", tags=["Automation"])


class ApplyRequest(BaseModel):
    dry_run: Optional[bool] = True
    headless: Optional[bool] = False


def run_apply_task(job_id: int, dry_run: bool = True, headless: bool = False):
    db = SessionLocal()
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        db.close()
        return

    app_record = repo.create_application(job_id)
    app_logger = ApplicationLogger(application_id=app_record.id)

    def log_handler(level: str, msg: str):
        app_logger.log(level, msg)
        manager.broadcast_sync({
            "type": "AUTOMATION_LOG",
            "job_id": job_id,
            "level": level,
            "message": msg
        })

    browser = None
    try:
        url_lower = (job.url or "").lower()
        is_linkedin = "linkedin.com" in url_lower

        log_handler("INFO", f"Initializing stealth browser for {job.company} - {job.title} (Dry-Run: {dry_run})...")
        browser = BrowserManager(headless=headless)
        driver = browser.start_driver()

        if is_linkedin:
            log_handler("INFO", "Target is LinkedIn: Routing to LinkedIn Easy Applier...")
            applier = LinkedInEasyApplier(
                driver=driver,
                log_callback=log_handler
            )
        else:
            log_handler("INFO", "Target is External Career Site: Routing to Universal ATS Applier (Greenhouse/Lever/Ashby/Generic)...")
            applier = UniversalATSApplier(
                driver=driver,
                log_callback=log_handler
            )

        result = applier.apply(job.url, dry_run=dry_run)

        if result.get("success"):
            app_record.status = "SUBMITTED" if not dry_run else "DRY_RUN_COMPLETED"
            log_handler("SUCCESS", f"Application workflow completed successfully: {result.get('status')}")
        else:
            app_record.status = "FAILED"
            app_record.error_log = result.get("reason", "Unknown failure")
            log_handler("ERROR", f"Application did not complete: {result.get('reason')}")

        db.commit()

    except Exception as e:
        log_handler("ERROR", f"Fatal exception during application run: {str(e)}")
        app_record.status = "FAILED"
        app_record.error_log = str(e)
        db.commit()
    finally:
        if browser:
            browser.quit()
        db.close()


@router.post("/apply/{job_id}")
def trigger_application(
    job_id: int,
    payload: ApplyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    repo = JobRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    background_tasks.add_task(run_apply_task, job_id, payload.dry_run, payload.headless)
    return {
        "success": True,
        "message": f"Application bot launched for {job.company} (Dry Run: {payload.dry_run})"
    }


@router.get("/logs")
def get_recent_logs(limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    logs = db.query(AutomationLog).order_by(AutomationLog.id.desc()).limit(limit).all()
    return [l.to_dict() for l in reversed(logs)]
