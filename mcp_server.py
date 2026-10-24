"""
JobHunter AI - Model Context Protocol (MCP) Server.
Enables AI chatbots (Claude Desktop, Cursor, Antigravity, ChatGPT) to:
1. Search live official ATS jobs (Greenhouse, Lever, Ashby, Workday, LinkedIn).
2. Dynamically manage candidate CV profiles (zero manual token required).
3. Deterministically match vacancies to candidate CVs (ATS 0-100% fit score).
4. Run Ghost Job & Link Vitality verification.
5. Generate bespoke tailored cover letters.
6. Track application lifecycle stages.

Supports:
- Local stdio transport (Claude Desktop / Cursor with ZERO tokens)
- Remote SSE transport (Cloud deployment / Webhook / Multi-user)
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from config.settings import settings
from config.logger import logger
from database.connection import SessionLocal
from database.repository import JobRepository
from scrapers.greenhouse_crawler import GreenhouseCrawler
from scrapers.lever_crawler import LeverCrawler
from scrapers.ashby_crawler import AshbyCrawler
from scrapers.workday_crawler import WorkdayCrawler
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.autonomous_discovery import AutonomousDiscoveryEngine
from scrapers.ghost_detector import GhostDetector
from scrapers.liveness_verifier import LivenessVerifier
from ai_engine.cv_matcher import CVMatcher
from ai_engine.ats_evaluator import ATSEvaluator
from ai_engine.resume_tailorer import ResumeTailorer
from ai_engine.resume_parser import resume_parser

# In-memory active profile cache for the active session (Multi-user / Custom CV support)
_active_profile_override: Optional[Dict[str, Any]] = None


def get_current_active_profile() -> Dict[str, Any]:
    global _active_profile_override
    if _active_profile_override:
        return _active_profile_override
    return settings.get_candidate_profile()


# Initialize FastMCP Server
mcp = FastMCP(
    name="JobHunter AI",
    instructions="Autonomous Multi-Agent Career Intelligence & ATS Application Platform"
)


# ==========================================
# 1. CANDIDATE PROFILE & CV MANAGEMENT TOOLS
# ==========================================

@mcp.tool()
def get_my_profile() -> str:
    """
    Returns the current candidate's active profile, including contact details,
    professional headline, skills list, and summary.
    """
    prof = get_current_active_profile()
    info = prof.get("personal_information", {})
    name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip() or "Anonymous Candidate"
    skills = prof.get("skills", {})
    summary = prof.get("summary", "No summary provided.")

    return json.dumps({
        "candidate_name": name,
        "headline": info.get("headline", ""),
        "email": info.get("email", ""),
        "location": f"{info.get('city', '')}, {info.get('country', '')}",
        "summary": summary,
        "skills": skills,
        "source": "Session Override" if _active_profile_override else "profile_resume.yaml"
    }, indent=2)


@mcp.tool()
def set_my_resume_text(resume_text: str, candidate_name: Optional[str] = None, headline: Optional[str] = None, save_as_default: bool = False) -> str:
    """
    Parses and sets a new candidate CV directly from raw text (Multi-user support).
    Anyone can paste their CV text here to instantly calibrate ATS matching to their skills.
    If save_as_default is True, updates the local profile_resume.yaml file.
    """
    global _active_profile_override
    if not resume_text.strip():
        return "Error: Resume text cannot be empty."

    # Parse resume text using the AI engine
    parsed = resume_parser.parse_resume(file_bytes=resume_text.encode("utf-8"), filename="chat_resume.txt", persist=save_as_default)

    if candidate_name:
        parts = candidate_name.strip().split(" ", 1)
        parsed.setdefault("personal_information", {})["first_name"] = parts[0]
        parsed["personal_information"]["last_name"] = parts[1] if len(parts) > 1 else ""

    if headline:
        parsed.setdefault("personal_information", {})["headline"] = headline

    _active_profile_override = parsed

    first_n = parsed.get("personal_information", {}).get("first_name", "Candidate")
    skills_found = sum(len(v) for v in parsed.get("skills", {}).values() if isinstance(v, list))

    return json.dumps({
        "status": "success",
        "message": f"Active profile updated for {first_n}! Detected {skills_found} tech skills.",
        "headline": parsed.get("personal_information", {}).get("headline", ""),
        "extracted_skills": parsed.get("skills", {})
    }, indent=2)


@mcp.tool()
def reset_to_default_profile() -> str:
    """Resets the active profile back to the project's default profile_resume.yaml."""
    global _active_profile_override
    _active_profile_override = None
    return "Profile reset to default profile_resume.yaml configuration."


# ==========================================
# 2. OFFICIAL ATS & WEB JOB SEARCH TOOLS
# ==========================================

@mcp.tool()
def search_live_jobs(source: str, target: str, location: str = "Remote") -> str:
    """
    Fetches real-time, live jobs from official ATS endpoints and indexes them.
    
    Args:
        source: 'greenhouse', 'lever', 'ashby', 'workday', or 'linkedin'
        target: Company token or search keyword (e.g. 'stripe', 'figma', 'spotify', 'openai', or 'Python Engineer')
        location: Target location (e.g. 'Remote', 'Worldwide', 'Dhaka')
    """
    src = source.strip().lower()
    tgt = target.strip()

    scraped = []
    try:
        if src == "greenhouse":
            crawler = GreenhouseCrawler()
            scraped = crawler.fetch_jobs(tgt)
        elif src == "lever":
            crawler = LeverCrawler()
            scraped = crawler.fetch_jobs(tgt)
        elif src == "ashby":
            crawler = AshbyCrawler()
            scraped = crawler.fetch_jobs(tgt)
        elif src == "workday":
            crawler = WorkdayCrawler()
            scraped = crawler.fetch_jobs(tgt)
        elif src == "linkedin":
            crawler = LinkedInScraper()
            scraped = crawler.fetch_jobs(keywords=tgt, location=location)
        else:
            return f"Error: Unknown source '{source}'. Supported: greenhouse, lever, ashby, workday, linkedin."
    except Exception as e:
        return f"Error fetching from {source}: {str(e)}"

    if not scraped:
        return f"No jobs found for {target} on {source}."

    # Persist newly discovered jobs into database
    db = SessionLocal()
    repo = JobRepository(db)
    saved_count = 0
    results_summary = []
    try:
        for job in scraped:
            saved = repo.create_or_update_job(job.to_dict())
            saved_count += 1
            if len(results_summary) < 10:
                results_summary.append({
                    "id": saved.id,
                    "title": saved.title,
                    "company": saved.company,
                    "location": saved.location,
                    "remote": saved.remote,
                    "url": saved.url
                })
    finally:
        db.close()

    return json.dumps({
        "status": "success",
        "source": source,
        "target": target,
        "total_discovered": len(scraped),
        "saved_to_db": saved_count,
        "sample_jobs": results_summary
    }, indent=2)


@mcp.tool()
def autonomous_web_discovery(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None, limit: int = 10) -> str:
    """
    Automatically scans public web boards and ATS networks for candidate roles.
    Zero manual company token needed.
    """
    engine = AutonomousDiscoveryEngine()
    discovered = engine.discover(roles=roles, locations=locations, limit_per_source=limit)

    db = SessionLocal()
    repo = JobRepository(db)
    saved_jobs = []
    try:
        for j in discovered:
            saved = repo.create_or_update_job(j.to_dict())
            saved_jobs.append({
                "id": saved.id,
                "title": saved.title,
                "company": saved.company,
                "location": saved.location,
                "url": saved.url
            })
    finally:
        db.close()

    return json.dumps({
        "total_indexed": len(saved_jobs),
        "jobs": saved_jobs[:15]
    }, indent=2)


# ==========================================
# 3. ATS FIT SCORING & CV MATCHING TOOLS
# ==========================================

@mcp.tool()
def match_jobs_with_my_cv(keyword: Optional[str] = None, min_score: int = 50, limit: int = 15) -> str:
    """
    Evaluates indexed jobs against the active candidate CV profile.
    Can filter by keyword (e.g. 'python', 'ai', 'backend').
    Returns ranked jobs with fit score (0-100%), matched skills, and missing skills.
    """
    prof = get_current_active_profile()
    db = SessionLocal()
    repo = JobRepository(db)
    matches = []

    try:
        jobs = repo.list_jobs(limit=200, search=keyword)
        for job in jobs:
            fit = CVMatcher.calculate_match(
                title=job.title or "",
                description=job.description or "",
                company=job.company or "",
                location=job.location or "Remote",
                remote=bool(job.remote),
                profile=prof,
                evaluation=job.evaluation
            )
            score = fit.get("score", 0)
            if score >= min_score:
                matches.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "fit_score": score,
                    "verdict": fit.get("verdict", "REVIEW"),
                    "matched_skills": fit.get("matched_skills", []),
                    "missing_skills": fit.get("missing_skills", []),
                    "highlights": fit.get("highlights", []),
                    "url": job.url
                })
    finally:
        db.close()

    matches.sort(key=lambda x: x["fit_score"], reverse=True)
    return json.dumps({
        "candidate_evaluated": prof.get("personal_information", {}).get("first_name", "Candidate"),
        "total_matches_above_threshold": len(matches),
        "top_matches": matches[:limit]
    }, indent=2)


@mcp.tool()
def deep_evaluate_job(job_id: int) -> str:
    """
    Runs full multi-agent LLM reasoning on a specific job.
    Evaluates dealbreakers, STAR behavioral alignment, and generates fit recommendation.
    """
    prof = get_current_active_profile()
    db = SessionLocal()
    repo = JobRepository(db)

    try:
        job = repo.get_job_by_id(job_id)
        if not job:
            return f"Error: Job with ID {job_id} not found."

        evaluator = ATSEvaluator()
        result = evaluator.evaluate_job(
            title=job.title,
            company=job.company,
            description=job.description or "",
            location=job.location,
            remote=bool(job.remote),
            profile=prof
        )

        # Save to database
        repo.save_evaluation(job_id, result)

        return json.dumps({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "ats_score": result.get("score"),
            "verdict": result.get("verdict"),
            "pros": result.get("pros", []),
            "cons": result.get("cons", []),
            "missing_skills": result.get("missing_skills", []),
            "rationale": result.get("rationale", "")
        }, indent=2)
    finally:
        db.close()


# ==========================================
# 4. GHOST JOB & LINK VITALITY RADAR
# ==========================================

@mcp.tool()
def verify_job_authenticity(job_id: int) -> str:
    """
    Checks if a job is a real active opening or a Ghost Job / Evergreen talent pool.
    Also verifies HTTP link vitality (probes if the requisition is closed or 404).
    """
    db = SessionLocal()
    repo = JobRepository(db)
    try:
        job = repo.get_job_by_id(job_id)
        if not job:
            return f"Error: Job with ID {job_id} not found."

        ghost_report = GhostDetector.evaluate(
            title=job.title or "",
            company=job.company or "",
            description=job.description or "",
            created_at=job.created_at
        )

        liveness_report = LivenessVerifier.verify(job.url)

        return json.dumps({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "is_ghost_job": ghost_report.get("is_ghost", False),
            "is_evergreen": ghost_report.get("is_evergreen", False),
            "authenticity_score": ghost_report.get("authenticity_score", 100),
            "ghost_markers_found": ghost_report.get("markers_found", []),
            "link_is_alive": liveness_report.get("is_live", True),
            "liveness_verdict": liveness_report.get("verdict", "LIVE"),
            "liveness_reason": liveness_report.get("reason", "ok"),
            "http_status": liveness_report.get("http_status", 200),
            "apply_url": job.url
        }, indent=2)
    finally:
        db.close()


# ==========================================
# 5. COVER LETTER GENERATOR & TRACKER
# ==========================================

@mcp.tool()
def generate_tailored_cover_letter(job_id: int) -> str:
    """
    Synthesizes a tailored, 3-paragraph professional cover letter
    mapped directly to the job requirements using the candidate's actual projects.
    """
    prof = get_current_active_profile()
    db = SessionLocal()
    repo = JobRepository(db)

    try:
        job = repo.get_job_by_id(job_id)
        if not job:
            return f"Error: Job with ID {job_id} not found."

        tailorer = ResumeTailorer()
        letter = tailorer.generate_cover_letter(
            company=job.company,
            title=job.title,
            job_description=job.description or f"{job.title} at {job.company}",
            profile=prof
        )

        # Store draft into application record
        repo.create_application(job_id=job.id, cover_letter=letter)

        return letter
    finally:
        db.close()


@mcp.tool()
def update_application_stage(job_id: int, status: str) -> str:
    """
    Updates the candidate's application stage in the database.
    Supported statuses: 'SAVED', 'PENDING', 'APPLIED', 'INTERVIEWING', 'OFFER', 'REJECTED'.
    """
    stat = status.strip().upper()
    db = SessionLocal()
    repo = JobRepository(db)
    try:
        job = repo.get_job_by_id(job_id)
        if not job:
            return f"Error: Job with ID {job_id} not found."

        job.status = stat
        app = repo.create_application(job_id=job_id)
        app.status = stat
        db.commit()

        return f"Successfully updated Job #{job_id} ({job.title} at {job.company}) status to '{stat}'."
    finally:
        db.close()


@mcp.tool()
def get_application_pipeline() -> str:
    """
    Returns a full overview of all tracked job applications categorized by stage.
    """
    db = SessionLocal()
    repo = JobRepository(db)
    try:
        stats = repo.get_stats()
        active_apps = repo.list_jobs(limit=50)

        pipeline = {
            "stats": stats,
            "jobs_summary": [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "status": j.status,
                    "url": j.url
                }
                for j in active_apps
            ]
        }
        return json.dumps(pipeline, indent=2)
    finally:
        db.close()


# ==========================================
# RUNNER: Supports CLI, stdio, and SSE
# ==========================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JobHunter AI MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="Transport mode")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        logger.info(f"Starting JobHunter MCP Server over SSE on port {args.port}...")
        mcp.run(transport="sse")
    else:
        # Default: stdio transport (Claude Desktop / Cursor)
        mcp.run(transport="stdio")
