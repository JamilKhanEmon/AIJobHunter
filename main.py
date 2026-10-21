"""
Main Entry Point for the Multi-Agent AI Job Hunter Platform.
"""

import sys
import argparse
import uvicorn
from config.logger import logger
from config.settings import settings


def run_server():
    """Starts the FastAPI backend and serves the modern Web Dashboard."""
    logger.info(f"Starting Multi-Agent AI Job Hunter Server on {settings.host}:{settings.port}...")
    logger.info(f"Dashboard available at: http://localhost:{settings.port}")
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )


def main():
    parser = argparse.ArgumentParser(
        description="⚡ JobHunter AI - Autonomous Multi-Agent Career Copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  server       Launch the full-stack Web Dashboard and API server (default)
  seed         Populate database with sample jobs and evaluations
  crawl        Run ATS or LinkedIn crawlers
  evaluate     Run AI ATS evaluation on discovered jobs
  apply        Launch automated job application bot
        """
    )
    parser.add_argument("command", nargs="?", default="server", choices=["server", "seed", "crawl", "evaluate", "apply"], help="Command to execute")
    parser.add_argument("--source", type=str, help="Crawler source (greenhouse, lever, ashby, workday, linkedin)")
    parser.add_argument("--target", type=str, help="Company board or search query")
    parser.add_argument("--job-id", type=int, help="Target Job ID")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run application bot in dry-run mode")
    parser.add_argument("--live", action="store_true", help="Run application bot with live submission")

    args = parser.parse_args()

    if args.command == "server":
        run_server()
    elif args.command == "seed":
        from scripts.seed_demo_data import seed
        seed()
    elif args.command == "crawl":
        if not args.source or not args.target:
            logger.error("Usage for crawl: python3 main.py crawl --source <greenhouse|lever|ashby|linkedin> --target <company_board>")
            sys.exit(1)
        from scripts.run_crawler import main as crawl_main
        sys.argv = ["run_crawler.py", "--source", args.source, "--target", args.target]
        crawl_main()
    elif args.command == "evaluate":
        from scripts.run_evaluation import main as eval_main
        sys.argv = ["run_evaluation.py", "--all"]
        eval_main()
    elif args.command == "apply":
        if not args.job_id:
            logger.error("Usage for apply: python3 main.py apply --job-id <id>")
            sys.exit(1)
        from scripts.run_apply import main as apply_main
        sys.argv = ["run_apply.py", "--job-id", str(args.job_id)]
        if args.live:
            sys.argv.append("--live")
        apply_main()


if __name__ == "__main__":
    main()
