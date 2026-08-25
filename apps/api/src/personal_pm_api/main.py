"""FastAPI application factory for the Personal PM Agent API."""

from fastapi import FastAPI

from personal_pm_api.settings import ApiSettings


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    app_settings = settings if settings is not None else ApiSettings()
    app = FastAPI(title="Personal PM Agent API", version="0.1.0")

    from personal_pm_api.approvals.router import router as approvals_router
    from personal_pm_api.identity.router import router as identity_router
    from personal_pm_api.planning.router import router as planning_router
    from personal_pm_api.shared.errors import install_error_handlers
    from personal_pm_api.workspaces.router import router as workspaces_router

    app.include_router(identity_router)
    app.include_router(workspaces_router)
    app.include_router(planning_router)
    app.include_router(approvals_router)
    install_error_handlers(app)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> dict[str, str]:
        return {"status": "ok", "environment": app_settings.environment}

    return app


app = create_app()
