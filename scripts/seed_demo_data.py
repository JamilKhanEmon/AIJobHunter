"""
Seed demo data into the database.
Creates realistic sample jobs from top tech companies (Stripe, Anthropic, OpenAI, Figma, Spotify)
with complete job descriptions, ATS evaluations, and cover letters.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import init_db, SessionLocal
from database.repository import JobRepository
from ai_engine.ats_evaluator import ATSEvaluator
from ai_engine.resume_tailorer import ResumeTailorer
from config.logger import logger

SAMPLE_JOBS = [
    {
        "title": "Senior Full-Stack Engineer, AI Platform",
        "company": "Anthropic",
        "url": "https://boards.greenhouse.io/anthropic/jobs/4019283004",
        "source": "greenhouse",
        "external_id": "4019283004",
        "location": "Remote - US / Global",
        "remote": True,
        "ats_type": "greenhouse",
        "department": "Engineering - AI Systems",
        "salary_raw": "$185,000 - $240,000",
        "description": """Anthropic is an AI safety and research company. We're looking for a Senior Full-Stack Engineer to build reliable, high-throughput interfaces and backend services for our Claude developer platform.

Key Responsibilities:
- Build low-latency APIs in Python (FastAPI) and modern TypeScript (Next.js) frontends.
- Architect real-time streaming interfaces for LLM completions, token usage monitoring, and tool calling.
- Collaborate with AI researchers to deploy cutting-edge model evaluations and benchmarking pipelines.
- Ensure strict security, rate limiting, and multi-tenant isolation across distributed microservices.

Requirements:
- 4+ years of professional full-stack software development experience.
- Strong proficiency in Python, TypeScript, modern React, and PostgreSQL.
- Experience with Docker, distributed systems, and REST/WebSocket APIs.
- Familiarity with LLM prompt engineering, local model evaluation, or AI developer workflows.
"""
    },
    {
        "title": "Staff Software Engineer, Developer Infrastructure",
        "company": "Stripe",
        "url": "https://boards.greenhouse.io/stripe/jobs/5910283002",
        "source": "greenhouse",
        "external_id": "5910283002",
        "location": "Remote",
        "remote": True,
        "ats_type": "greenhouse",
        "department": "Developer Infrastructure",
        "salary_raw": "$190,000 - $260,000",
        "description": """Stripe builds economic infrastructure for the internet. Millions of companies use Stripe’s software and APIs to accept payments and manage their businesses online.

As an engineer on Developer Infrastructure, you will design the foundation that empowers thousands of engineers to build, test, and deploy services with high confidence.

What you will do:
- Design and scale distributed build and test automation systems.
- Build internal developer tools, CLI utilities, and observability dashboards.
- Optimize database queries, caching layers, and container orchestration workflows.

Qualifications:
- Solid background in backend systems, distributed architectures, and Python / Go.
- Passion for developer velocity, automated testing, and clean software craftsmanship.
"""
    },
    {
        "title": "AI Systems & Automation Engineer",
        "company": "Figma",
        "url": "https://boards.greenhouse.io/figma/jobs/4820194001",
        "source": "greenhouse",
        "external_id": "4820194001",
        "location": "Remote",
        "remote": True,
        "ats_type": "greenhouse",
        "department": "AI & Design Tools",
        "salary_raw": "$175,000 - $230,000",
        "description": """At Figma, we make design accessible to all teams. We are integrating autonomous AI capabilities and intelligent tooling into our collaborative canvas.

Responsibilities:
- Build backend pipelines that route prompts between frontier models and low-latency local endpoints.
- Integrate automated evaluation frameworks to measure generation quality and latency.
- Partner with product teams to build responsive web interfaces for generative workflows.

Requirements:
- Strong experience with Python, TypeScript, and modern web application frameworks.
- Experience working with LLM APIs, vector databases, or intelligent agent systems.
"""
    },
    {
        "title": "Backend Platform Engineer",
        "company": "Spotify",
        "url": "https://jobs.lever.co/spotify/839102-lever-posting",
        "source": "lever",
        "external_id": "839102",
        "location": "Remote - Americas / EMEA",
        "remote": True,
        "ats_type": "lever",
        "department": "Core Platform",
        "salary_raw": "$160,000 - $210,000",
        "description": """Spotify is looking for a Backend Platform Engineer to build scalable microservices and data pipelines that connect millions of creators to billions of listeners.

What you'll do:
- Develop resilient backend microservices in Python and Java/Go.
- Build automated data validation and ingestion crawlers.
- Ensure 99.99% service availability with robust CI/CD, metrics, and alerting.
"""
    },
    {
        "title": "Autonomous Agent & Workflow Engineer",
        "company": "Retool",
        "url": "https://jobs.ashbyhq.com/retool/928374-ashby-job",
        "source": "ashby",
        "external_id": "928374",
        "location": "Remote",
        "remote": True,
        "ats_type": "ashby",
        "department": "AI & Workflows",
        "salary_raw": "$170,000 - $225,000",
        "description": """Retool is the fast way to build internal tools and autonomous workflows. We are expanding Retool Workflows and AI Agents so teams can run complex operations without code.

Requirements:
- 3+ years experience with Python, Node.js/TypeScript, and database architecture.
- Demonstrated experience with headless browser automation, webhook handling, and asynchronous workers.
"""
    }
]


def seed():
    logger.info("Initializing database tables...")
    init_db()

    db = SessionLocal()
    repo = JobRepository(db)
    evaluator = ATSEvaluator()
    tailorer = ResumeTailorer()

    logger.info(f"Seeding {len(SAMPLE_JOBS)} real-world sample jobs...")
    for item in SAMPLE_JOBS:
        job = repo.create_or_update_job(item)
        logger.info(f"Saved job: {job.company} - {job.title}")

        # Compute evaluation
        eval_result = evaluator.evaluate_job(
            title=job.title,
            company=job.company,
            description=job.description,
            location=job.location,
            remote=job.remote
        )
        repo.save_evaluation(job.id, eval_result)

        # Generate sample cover letter for top match
        if eval_result.get("score", 0) >= 80:
            cover_letter = tailorer.generate_cover_letter(job.company, job.title, job.description)
            repo.create_application(job.id, cover_letter=cover_letter)

    db.close()
    logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    seed()
