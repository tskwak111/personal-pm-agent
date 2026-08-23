"""Stable API error contracts."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """The object either does not exist or belongs to another workspace."""


class StaleObjectVersionError(Exception):
    def __init__(self, object_id: str, expected_version: int) -> None:
        self.object_id = object_id
        self.expected_version = expected_version
        super().__init__(f"stale version {expected_version} for {object_id}")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND"})

    @app.exception_handler(StaleObjectVersionError)
    async def _stale(_: Request, exc: StaleObjectVersionError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "STALE_OBJECT_VERSION",
                "detail": {
                    "object_id": exc.object_id,
                    "expected_version": exc.expected_version,
                },
            },
        )
