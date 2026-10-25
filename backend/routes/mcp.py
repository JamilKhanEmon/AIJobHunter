"""
MCP Management & Info Endpoints.
Allows the frontend dashboard and remote clients to inspect registered MCP tools and config.
"""

import sys
from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


@router.get("/status")
def get_mcp_status():
    """Returns the operational status and registered tools of the JobHunter MCP server."""
    tools = [
        {"name": "get_my_profile", "description": "Returns candidate active skills, headline, and summary."},
        {"name": "set_my_resume_text", "description": "Parses and dynamically sets a new candidate CV from raw text."},
        {"name": "reset_to_default_profile", "description": "Resets the candidate profile back to default configuration."},
        {"name": "search_live_jobs", "description": "Fetches real-time jobs from Greenhouse, Lever, Ashby, Workday, or LinkedIn."},
        {"name": "autonomous_web_discovery", "description": "Scans public web and ATS networks for candidate roles."},
        {"name": "match_jobs_with_my_cv", "description": "Calculates 0-100% ATS fit against candidate CV and highlights matched/missing skills."},
        {"name": "deep_evaluate_job", "description": "Runs full multi-agent LLM reasoning on a job (STAR alignment, pros, cons)."},
        {"name": "verify_job_authenticity", "description": "Probes HTTP link vitality and evaluates Ghost Job indicators."},
        {"name": "generate_tailored_cover_letter", "description": "Synthesizes a bespoke 3-paragraph tailored cover letter."},
        {"name": "update_application_stage", "description": "Updates application stage (Saved, Applied, Interview, Offer)."},
        {"name": "get_application_pipeline", "description": "Returns full overview of tracked job applications."}
    ]

    base_dir = Path(__file__).resolve().parent.parent.parent
    mcp_script = str(base_dir / "mcp_server.py")
    python_exe = sys.executable or "python3"

    return {
        "status": "ready",
        "server_name": "JobHunter AI",
        "transport_support": ["stdio", "sse"],
        "total_tools": len(tools),
        "tools": tools,
        "config_example": {
            "mcpServers": {
                "jobhunter-ai": {
                    "command": python_exe,
                    "args": [mcp_script],
                    "env": {"PYTHONPATH": str(base_dir)}
                }
            }
        }
    }
