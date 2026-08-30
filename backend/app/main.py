"""FastAPI application entrypoint.

Secrets live in the environment (see .env.example). Only publishable values are
ever returned to the Android client.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import artifacts, audit, auth, datasets, files, projects, runs, sql_connectors
from app.config import get_settings
from app.jobs.manager import get_job_manager, init_job_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.app_env != "test":
        init_job_manager()
    yield
    # Graceful shutdown: cancel queued tasks.
    try:
        manager = get_job_manager()
        for task in list(manager._tasks):
            task.cancel()
    except Exception:
        pass


app = FastAPI(
    title="Analytics Agent API",
    version="1.0.0",
    description="Admin-only enterprise data analytics workspace backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(files.router)
app.include_router(runs.router)
app.include_router(artifacts.router)
app.include_router(audit.router)
app.include_router(sql_connectors.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "analytics-agent-backend"}


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"service": "analytics-agent-backend", "docs": "/docs"}