"""
CLI script to evaluate jobs using AI ATS Evaluator.
Usage:
    python3 scripts/run_evaluation.py --all
    python3 scripts/run_evaluation.py --job-id 1
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from config.logger import logger
from database.connection import init_db, SessionLocal
from database.repository import JobRepository
from ai_engine.ats_evaluator import ATSEvaluator


def main():
    parser = argparse.ArgumentParser(description="Evaluate jobs against candidate profile")
    parser.add_argument("--job-id", type=int, help="Specific Job ID to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all unscored jobs")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    repo = JobRepository(db)
    evaluator = ATSEvaluator()

    if args.job_id:
        job = repo.get_job_by_id(args.job_id)
        if not job:
            logger.error(f"Job {args.job_id} not found")
            return
        logger.info(f"Evaluating Job #{job.id}: {job.company} - {job.title}")
        res = evaluator.evaluate_job(job.title, job.company, job.description or "", job.location, job.remote)
        repo.save_evaluation(job.id, res)
        logger.info(f"Result: Score {res.get('score')}/100, Verdict: {res.get('verdict')}")
    else:
        unscored = repo.get_unscored_jobs(limit=50)
        logger.info(f"Found {len(unscored)} unscored jobs. Starting batch evaluation...")
        for j in unscored:
            try:
                res = evaluator.evaluate_job(j.title, j.company, j.description or "", j.location, j.remote)
                repo.save_evaluation(j.id, res)
                logger.info(f"Job #{j.id} ({j.company}): Score {res.get('score')}/100 - {res.get('verdict')}")
            except Exception as e:
                logger.error(f"Failed to evaluate job {j.id}: {e}")

    db.close()
    logger.info("Evaluation process finished.")


if __name__ == "__main__":
    main()
