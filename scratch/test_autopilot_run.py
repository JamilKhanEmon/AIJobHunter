"""
Direct test script to run AutoPilot full cycle and verify live real jobs are fetched from web feeds.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.autopilot import autopilot_service
from database.connection import SessionLocal
from database.repository import JobRepository
from database.models import Job

print("Starting AutoPilot full cycle...")
stats = autopilot_service.execute_full_cycle(max_posting_age_days=7)
print("AutoPilot result:", stats)

db = SessionLocal()
jobs = db.query(Job).all()
print(f"Total live jobs in database now: {len(jobs)}")
for j in jobs[:8]:
    score_str = f"[{j.evaluation.score}%]" if j.evaluation else "[Pending]"
    print(f" - #{j.id} {score_str} {j.company} - {j.title} ({j.location}) | {j.url[:45]}...")
db.close()
