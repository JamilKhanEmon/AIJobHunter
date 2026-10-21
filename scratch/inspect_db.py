from database.connection import SessionLocal
from database.models import Job, JobEvaluation, ApplicationRecord, AutomationLog

db = SessionLocal()
total_jobs = db.query(Job).count()
print(f"Total jobs currently in DB: {total_jobs}")

sources = db.query(Job.source).distinct().all()
print(f"Distinct sources: {[s[0] for s in sources]}")

# Sample job titles and companies
sample = db.query(Job.id, Job.company, Job.title, Job.source, Job.url).limit(10).all()
for s in sample:
    print(f"#{s[0]} [{s[3]}] {s[1]} - {s[2]} ({s[4][:50]}...)")

db.close()
