"""Unit of Work protocol and SQLAlchemy implementation.

Repositories attach to one session; ``commit`` is explicit so domain state,
audit events and outbox records share a single transaction boundary.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

if TYPE_CHECKING:
    from personal_pm_api.audit.repository import AuditRepository
    from personal_pm_api.execution.repository import (
        ExternalExecutionRepository,
        OutboxRepository,
    )
    from personal_pm_api.planning.repository import PlanningRepository
    from personal_pm_api.workspaces.repository import WorkstreamRepository


class UnitOfWork:
    """Protocol shape for application services (structural typing)."""

    session: AsyncSession

    async def commit(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def rollback(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.workstreams: WorkstreamRepository | None = None
        self.planning: PlanningRepository | None = None
        self.outbox: OutboxRepository | None = None
        self.external_state: ExternalExecutionRepository | None = None
        self.audit: AuditRepository | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        # Late imports keep repository modules free of circular dependencies.
        from personal_pm_api.audit.repository import AuditRepository
        from personal_pm_api.execution.repository import (
            ExternalExecutionRepository,
            OutboxRepository,
        )
        from personal_pm_api.planning.repository import PlanningRepository
        from personal_pm_api.workspaces.repository import WorkstreamRepository

        self.workstreams = WorkstreamRepository(self.session)
        self.planning = PlanningRepository(self.session)
        self.outbox = OutboxRepository(self.session)
        self.external_state = ExternalExecutionRepository(self.session)
        self.audit = AuditRepository(self.session)
        return self

    @property
    def typed_session(self) -> AsyncSession:
        assert self.session is not None, "unit of work not entered"
        return self.session

    async def commit(self) -> None:
        await self.typed_session.commit()

    async def rollback(self) -> None:
        await self.typed_session.rollback()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is not None and self.session is not None:
            await self.session.rollback()
        if self.session is not None:
            await self.session.close()


def uow_context(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AbstractAsyncContextManager[SqlAlchemyUnitOfWork]]:
    """Context helper returning the UoW for ``async with`` usage."""

    @asynccontextmanager
    async def factory() -> AsyncIterator[SqlAlchemyUnitOfWork]:
        unit = SqlAlchemyUnitOfWork(session_factory)
        async with unit:
            yield unit

    return factory
