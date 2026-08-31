"""Runnable Outbox polling worker with graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import signal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from personal_pm_worker.outbox_worker import OutboxExecutor, run_once

LOGGER = logging.getLogger("personal_pm_worker")


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    environment: str = Field(default="local", validation_alias="APP_ENVIRONMENT")
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm"
        ),
        validation_alias="DATABASE_URL",
    )
    poll_interval_seconds: float = Field(
        default=5.0,
        gt=0,
        validation_alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    batch_size: int = Field(default=50, gt=0, validation_alias="WORKER_BATCH_SIZE")


def build_worker_identity(environment: str) -> str:
    normalized = environment.strip().lower()
    if not normalized:
        raise ValueError("environment must not be empty")
    return f"personal-pm-worker:{normalized}"


async def poll(
    settings: WorkerSettings,
    *,
    executor: OutboxExecutor | None = None,
    stop: asyncio.Event | None = None,
) -> None:
    stop_event = stop or asyncio.Event()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        while not stop_event.is_set():
            result = await run_once(factory, executor, settings.batch_size)
            if result.claimed:
                LOGGER.info(
                    "outbox batch claimed=%d succeeded=%d failed=%d",
                    result.claimed,
                    result.succeeded,
                    result.failed,
                )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.poll_interval_seconds)
            except TimeoutError:
                pass
    finally:
        await engine.dispose()


async def _main() -> None:
    settings = WorkerSettings()
    build_worker_identity(settings.environment)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    await poll(settings, stop=stop)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()


__all__ = ["WorkerSettings", "build_worker_identity", "main", "poll"]
