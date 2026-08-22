"""FastAPI application factory for the Personal PM Agent API."""

from fastapi import FastAPI

from personal_pm_api.settings import ApiSettings


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    app_settings = settings if settings is not None else ApiSettings()
    app = FastAPI(title="Personal PM Agent API", version="0.1.0")

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> dict[str, str]:
        return {"status": "ok", "environment": app_settings.environment}

    return app


app = create_app()
