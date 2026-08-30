"""Job manager singleton — schedules analysis runs and dataset processing."""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.engine.llm import LLMClient
from app.jobs.worker import JobManager

_job_manager: JobManager | None = None


def init_job_manager(concurrency: int | None = None, llm: LLMClient | None = None) -> JobManager:
    global _job_manager
    _job_manager = JobManager(
        concurrency=concurrency or get_settings().job_concurrency,
        llm=llm or LLMClient(),
    )
    return _job_manager


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager(
            concurrency=get_settings().job_concurrency,
            llm=LLMClient(),
        )
    return _job_manager