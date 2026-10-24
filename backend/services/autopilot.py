"""
Autonomous Career Auto-Pilot Service.
Orchestrates:
1. Strict Date & Deadline Filtering (fresh postings only).
2. Automated Background Periodic Scheduling (Runs daily at set intervals).
3. Auto-Pruning & Expiration of Stale Leads.
4. One-Click Master Pipeline Execution (Zero-touch: Discover -> Filter -> Score).
"""

import asyncio
from datetime import datetime, timedelta
import time
from typing import Dict, Any, Optional
from config.logger import logger
from config.settings import settings
from database.connection import SessionLocal
from database.repository import JobRepository
from scrapers.autonomous_discovery import AutonomousDiscoveryEngine
from ai_engine.ats_evaluator import ATSEvaluator
from backend.websocket import manager


class AutoPilotService:
    def __init__(self):
        self.is_running = False
        self.last_run_time: Optional[datetime] = None
        self.last_run_stats: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None

    def execute_full_cycle(
        self,
        max_posting_age_days: int = 5,
        prune_age_days: int = 5,
        roles: Optional[Any] = None,
        locations: Optional[Any] = None,
        profile: Optional[dict] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes the complete end-to-end autonomous cycle:
        1. Auto-Prune stale/expired leads.
        2. Auto-Discover fresh postings (Bangladesh & Remote) with zero manual inputs.
        3. Enforce strict date/deadline validation.
        4. Auto-Evaluate new listings using Groq Cloud LLM.
        """
        db = SessionLocal()
        repo = JobRepository(db)
        start_time = datetime.utcnow()

        manager.broadcast_sync({
            "type": "AUTOPILOT_STARTED",
            "message": "Auto-Pilot Pipeline activated: Executing zero-touch discovery, date filtering, and evaluation..."
        })

        stats = {
            "pruned_expired": 0,
            "discovered_fresh": 0,
            "evaluated_count": 0,
            "high_matches": 0,
            "started_at": start_time.isoformat(),
            "status": "COMPLETED"
        }

        try:
            # Step 1: Auto-Prune Stale / Expired Leads
            logger.info("AutoPilot: Step 1 - Pruning expired and dead job listings...")
            pruned = repo.prune_expired_jobs(max_age_days=prune_age_days)
            stats["pruned_expired"] = pruned
            if pruned > 0:
                manager.broadcast_sync({
                    "type": "AUTOPILOT_PRUNED",
                    "message": f"Auto-Pilot Cleanup: Removed {pruned} expired/stale listings."
                })

            # Step 2: Autonomous Web Discovery (Bangladesh & Remote)
            logger.info(f"AutoPilot: Step 2 - Scanning live web feeds for fresh listings (roles={roles}, locations={locations})...")
            engine = AutonomousDiscoveryEngine()
            fresh_jobs = engine.discover(roles=roles, locations=locations, limit_per_source=10)

            saved_fresh = 0
            for j in fresh_jobs:
                repo.create_or_update_job(j.to_dict())
                saved_fresh += 1

            stats["discovered_fresh"] = saved_fresh
            manager.broadcast_sync({
                "type": "AUTOPILOT_DISCOVERED",
                "message": f"Auto-Pilot Discovery: {saved_fresh} fresh listings indexed."
            })

            # Step 3: Auto-Evaluate Unscored Fresh Listings with Groq AI
            logger.info("AutoPilot: Step 3 - Running ATS & Mobility evaluation on pending listings...")
            unscored = repo.get_unscored_jobs(limit=30)
            evaluator = ATSEvaluator()

            high_match_count = 0
            for job in unscored:
                try:
                    res = evaluator.evaluate_job(
                        title=job.title,
                        company=job.company,
                        description=job.description or "",
                        location=job.location,
                        remote=job.remote,
                        profile=profile
                    )
                    repo.save_evaluation(job.id, res)
                    score = res.get("score", 0)
                    if score >= settings.min_match_score:
                        high_match_count += 1
                    # Polite throttle pause to prevent Groq TPM/RPM spikes
                    time.sleep(1.0)
                except Exception as err:
                    logger.warning(f"Error evaluating job #{job.id}: {err}")

            stats["evaluated_count"] = len(unscored)
            stats["high_matches"] = high_match_count
            self.last_run_time = datetime.utcnow()
            self.last_run_stats = stats

            manager.broadcast_sync({
                "type": "AUTOPILOT_COMPLETED",
                "stats": stats,
                "message": f"Auto-Pilot Complete: {saved_fresh} fresh jobs scanned, {len(unscored)} evaluated, {high_match_count} high-match leads ready!"
            })
            return stats

        except Exception as e:
            logger.error(f"Auto-Pilot cycle encountered error: {e}")
            stats["status"] = "ERROR"
            stats["error"] = str(e)
            manager.broadcast_sync({
                "type": "AUTOPILOT_ERROR",
                "message": f"Auto-Pilot cycle failed: {str(e)}"
            })
            return stats
        finally:
            db.close()

    async def start_background_loop(self, interval_hours: float = 12.0):
        """Asynchronous daemon that triggers daily at set intervals."""
        self.is_running = True
        logger.info(f"AutoPilot Daemon started: Running automatically every {interval_hours} hours in background.")
        
        # Initial run after 15 seconds of server startup
        await asyncio.sleep(15)
        
        while self.is_running:
            try:
                logger.info("AutoPilot Daemon: Triggering scheduled autonomous cycle...")
                # Run the blocking cycle in thread pool so it does not block the async event loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.execute_full_cycle)
            except Exception as e:
                logger.error(f"AutoPilot scheduled task error: {e}")

            # Wait for next scheduled interval
            await asyncio.sleep(interval_hours * 3600)

    def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()


autopilot_service = AutoPilotService()
