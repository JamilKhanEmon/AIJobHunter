"""
Pipeline & Autonomous Auto-Pilot API Endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from database.connection import get_db, SessionLocal
from database.repository import JobRepository
from backend.services.autopilot import autopilot_service

from backend.auth import get_current_user
from database.models import User

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


@router.post("/autopilot")
def trigger_autopilot(
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_current_user)
):
    """
    Triggers the 1-Click Master Auto-Pilot Pipeline on-demand:
    1. Prunes expired/stale leads from database.
    2. Autonomously discovers fresh jobs (Bangladesh & Remote) with ZERO manual inputs.
    3. Strictly enforces posting date freshness (<= 5 days).
    4. Evaluates all new jobs with LLM for match score against active user profile.
    """
    candidate_profile = user.profile.to_candidate_schema() if user and user.profile else None
    user_id = user.id if user else None

    background_tasks.add_task(
        autopilot_service.execute_full_cycle,
        profile=candidate_profile,
        user_id=user_id
    )
    return {
        "success": True,
        "message": "Auto-Pilot Pipeline activated! Pruning expired leads, discovering fresh jobs, and running AI evaluation..."
    }


@router.post("/instant-run")
def trigger_instant_run(
    background_tasks: BackgroundTasks,
    payload: Optional[dict] = None,
    user: Optional[User] = Depends(get_current_user)
):
    """
    ⚡ Instant Run Now:
    Runs an immediate on-demand autonomous discovery with user-specified roles & locations,
    strictly filters freshness (<= 5 days), and auto-evaluates against the active user's CV.
    """
    from config.settings import settings
    roles = None
    locations = None
    max_age = 5
    if payload:
        roles = payload.get("roles")
        locations = payload.get("locations")
        max_age = int(payload.get("max_age_days", 5))

    candidate_profile = user.profile.to_candidate_schema() if user and user.profile else None
    user_id = user.id if user else None

    background_tasks.add_task(
        autopilot_service.execute_full_cycle,
        max_posting_age_days=max_age,
        roles=roles,
        locations=locations,
        profile=candidate_profile,
        user_id=user_id
    )
    return {
        "success": True,
        "message": "⚡ Instant Search Pipeline launched! Scanning live web feeds & running Groq AI evaluation...",
        "target_roles": roles or settings.target_positions,
        "target_locations": locations or settings.target_locations
    }


@router.post("/prune")
def trigger_prune(max_age_days: int = 5, db: Session = Depends(get_db)):
    """Prunes expired job leads older than max_age_days."""
    repo = JobRepository(db)
    pruned_count = repo.prune_expired_jobs(max_age_days=max_age_days)
    return {
        "success": True,
        "pruned_count": pruned_count,
        "message": f"Successfully pruned {pruned_count} expired listings."
    }


@router.post("/reset-all")
def reset_all_data(db: Session = Depends(get_db)):
    """Purges all dummy, mock, and stale data completely from database."""
    from backend.websocket import manager
    repo = JobRepository(db)
    deleted_count = repo.purge_all_jobs()
    manager.broadcast_sync({
        "type": "PIPELINE_RESET",
        "message": f"All dummy/stale data purged completely ({deleted_count} records removed)."
    })
    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Successfully purged all {deleted_count} dummy/stale job records from database."
    }


@router.get("/status")
def get_pipeline_status(db: Session = Depends(get_db)):
    """Returns current auto-pilot health, stats, and last run metadata."""
    repo = JobRepository(db)
    stats = repo.get_stats()
    return {
        "is_scheduler_running": autopilot_service.is_running,
        "last_run_time": autopilot_service.last_run_time.isoformat() if autopilot_service.last_run_time else None,
        "last_run_stats": autopilot_service.last_run_stats,
        "current_stats": stats
    }
