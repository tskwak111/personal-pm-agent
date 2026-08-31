"""FastAPI application factory for the Personal PM Agent API."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.responses import Response

from personal_pm_api.security.rate_limit import RATE_LIMITS, RateLimit, RateLimiter
from personal_pm_api.settings import ApiSettings
from personal_pm_api.shared.db import get_engine
from personal_pm_api.telemetry.logging import StructuredLogger
from personal_pm_api.telemetry.tracing import resolve_correlation_id

REQUEST_LOGGER = logging.getLogger("personal_pm_api.requests")


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def check_database(settings: ApiSettings | None = None) -> None:
    async with get_engine(settings).connect() as connection:
        await connection.execute(text("SELECT 1"))


def _rate_bucket(request: Request) -> str | None:
    path = request.url.path
    if not path.startswith("/api/v1/"):
        return None
    if path == "/api/v1/identity/test-session":
        return "auth"
    if path == "/api/v1/inbox/sources" and request.method == "POST":
        return "upload"
    if path.startswith("/api/v1/calendar/") or request.method not in {"GET", "HEAD", "OPTIONS"}:
        return "external-write"
    return "read-api"


def _rate_actor(request: Request, bucket_name: str) -> str:
    client_address = request.client.host if request.client is not None else "unknown"
    if bucket_name == "auth":
        return f"client:{client_address}"
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        raw_token = authorization.removeprefix("Bearer ").strip()
        if raw_token:
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            return f"session:{token_hash}"
    return f"client:{client_address}"


def create_app(
    settings: ApiSettings | None = None,
    *,
    rate_limits: Mapping[str, RateLimit] | None = None,
    rate_limit_clock: Callable[[], datetime] = _utc_now,
) -> FastAPI:
    app_settings = settings if settings is not None else ApiSettings()
    app = FastAPI(title="Personal PM Agent API", version="0.1.0")
    app.state.settings = app_settings
    limiter = RateLimiter()
    limits = RATE_LIMITS if rate_limits is None else rate_limits

    @app.middleware("http")
    async def enforce_rate_limit(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        bucket_name = _rate_bucket(request)
        if bucket_name is not None:
            bucket = limits.get(bucket_name)
            if bucket is not None and not limiter.allow(
                _rate_actor(request, bucket_name),
                bucket_name=bucket_name,
                bucket=bucket,
                now_utc=rate_limit_clock(),
            ):
                return JSONResponse(
                    status_code=429,
                    content={"code": "RATE_LIMITED", "bucket": bucket_name},
                    headers={"Retry-After": str(max(1, int(bucket.window.total_seconds())))},
                )
        return await call_next(request)

    @app.middleware("http")
    async def log_request_result(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = resolve_correlation_id(request.headers.get("X-Correlation-ID"))
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            fields: dict[str, object] = {
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": max(0, round((time.perf_counter() - started) * 1000)),
            }
            workspace_id = getattr(request.state, "workspace_id", None)
            if workspace_id is not None:
                fields["workspace_id"] = workspace_id
            event = StructuredLogger().bind(**fields).capture("request.completed")
            REQUEST_LOGGER.info(json.dumps(event, sort_keys=True, separators=(",", ":")))

    from personal_pm_api.approvals.router import router as approvals_router
    from personal_pm_api.calendar.router import router as calendar_router
    from personal_pm_api.identity.router import router as identity_router
    from personal_pm_api.inbox.router import router as inbox_router
    from personal_pm_api.planning.router import router as planning_router
    from personal_pm_api.shared.errors import install_error_handlers
    from personal_pm_api.workspaces.router import router as workspaces_router

    app.include_router(identity_router)
    app.include_router(workspaces_router)
    app.include_router(planning_router)
    app.include_router(approvals_router)
    app.include_router(inbox_router)
    app.include_router(calendar_router)
    install_error_handlers(app)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> JSONResponse:
        try:
            await check_database(app_settings)
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "environment": app_settings.environment},
        )

    return app


app = create_app()
