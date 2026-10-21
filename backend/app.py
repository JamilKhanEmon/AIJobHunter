"""
FastAPI Main Application.
Serves REST APIs, WebSockets, and mounts the Frontend Web Dashboard.
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config.logger import logger

from database.connection import init_db
import asyncio
from backend.routes.jobs import router as jobs_router
from backend.routes.crawlers import router as crawlers_router
from backend.routes.evaluation import router as eval_router
from backend.routes.automation import router as auto_router
from backend.routes.profile import router as profile_router, settings_router
from backend.routes.pipeline import router as pipeline_router
from backend.routes.stats import router as stats_router
from backend.services.autopilot import autopilot_service
from backend.websocket import manager

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database tables exist
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database initialized successfully.")
    
    # Launch autonomous daily background daemon (12-hour interval)
    logger.info("Launching autonomous daily Auto-Pilot background daemon...")
    scheduler_task = asyncio.create_task(autopilot_service.start_background_loop(interval_hours=12.0))
    yield
    # Shutdown
    logger.info("Shutting down Auto-Pilot daemon and application...")
    autopilot_service.stop()
    scheduler_task.cancel()


app = FastAPI(
    title="Multi-Agent AI Job Hunter",
    version="1.0.0",
    description="Autonomous Multi-Agent AI Job Hunter Platform for ATS crawling, AI evaluation, and automated applying.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(jobs_router)
app.include_router(crawlers_router)
app.include_router(eval_router)
app.include_router(auto_router)
app.include_router(profile_router)
app.include_router(settings_router)
app.include_router(pipeline_router)
app.include_router(stats_router)


# WebSocket endpoint for real-time live logs
@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & accept client ping messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Mount static assets for the frontend
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")


# Serve index.html on root
@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(index_path)


# Catch-all to support SPA refresh
@app.get("/{full_path:path}")
def catch_all(full_path: str):
    file_path = FRONTEND_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_DIR / "index.html")
