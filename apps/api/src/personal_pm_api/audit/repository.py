"""Audit event append-only repository."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.audit.models import AuditEventModel


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        workspace_id: UUID,
        actor_user_id: UUID | None,
        entity_kind: str,
        entity_id: str,
        reason: str,
        rule_basis: tuple[str, ...],
        trace_id: str,
        reversible: bool,
        occurred_at: datetime,
        before_state: Mapping[str, object] | None = None,
        after_state: Mapping[str, object] | None = None,
        approval_id: UUID | None = None,
    ) -> AuditEventModel:
        model = AuditEventModel(
            id=uuid4(),
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            entity_kind=entity_kind,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            rule_basis=list(rule_basis),
            approval_id=approval_id,
            trace_id=trace_id,
            reversible=reversible,
            occurred_at=occurred_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_for_entity(
        self, workspace_id: UUID, entity_kind: str, entity_id: str
    ) -> list[AuditEventModel]:
        statement = (
            select(AuditEventModel)
            .where(
                AuditEventModel.workspace_id == workspace_id,
                AuditEventModel.entity_kind == entity_kind,
                AuditEventModel.entity_id == entity_id,
            )
            .order_by(AuditEventModel.occurred_at)
        )
        return list((await self._session.execute(statement)).scalars())
