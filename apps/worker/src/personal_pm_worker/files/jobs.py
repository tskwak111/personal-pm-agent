"""Inbox processing jobs: idempotent by operation id."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4


class ProcessingJob:
    """Runs inbox item processing; duplicate delivery must not duplicate output."""

    def __init__(self, session_factory: Any, operation_id: UUID | None = None) -> None:
        self._factory = session_factory
        self.operation_id = operation_id or uuid4()
        self.parser_call_count = 0

    async def run(self, item_id: str) -> str:

        from personal_pm_api.inbox.models import (
            CandidateFactModel,
            InboxItemModel,
            transition_inbox,
        )
        from personal_pm_api.shared.idempotency import reserve_key
        from personal_pm_api.workspaces.models import WorkspaceModel

        async with self._factory() as session:
            model = await session.get(InboxItemModel, UUID(str(item_id)))
            if model is None:
                raise KeyError(item_id)

            workspace = await session.get(WorkspaceModel, model.workspace_id)
            assert workspace is not None

            # Capture status BEFORE the reserve attempt: a conflicting insert
            # poisons the session until rollback, so later attribute access on
            # an expired instance would raise PendingRollbackError.
            current_status: str = model.status

            # Idempotency gate: same operation id for the same item runs once.
            reserved = await reserve_key(session, str(self.operation_id), model.workspace_id)
            if not reserved:
                await session.rollback()
                return current_status

            if current_status != "NEW":
                # Re-delivery after completion: nothing to do.
                await session.rollback()
                return current_status

            model.status = transition_inbox(model.status, "PROCESSING")
            self.parser_call_count += 1

            candidates = self._extract_candidates(model)
            for kind, payload in candidates:
                session.add(
                    CandidateFactModel(
                        id=uuid4(),
                        inbox_item_id=model.id,
                        operation_id=self.operation_id,
                        kind=kind,
                        payload_json=payload,
                        evidence_score=0.0,
                        decision="HOLD",
                    )
                )

            target = "STRUCTURED" if candidates else "NEEDS_CONFIRMATION"
            model.status = transition_inbox("PROCESSING", target)
            await session.commit()
            return str(model.status)

    def _extract_candidates(self, model: Any) -> list[tuple[str, dict[str, object]]]:
        """Deterministic placeholder extraction (LLM gateway arrives in P4-T04)."""
        text = model.raw_text or ""
        if not text.strip():
            return []
        return [
            (
                "REFERENCE_NOTE",
                {"source": "inline-text", "preview": text[:120], "version": 1},
            )
        ]


class FailingProcessingJob(ProcessingJob):
    """Simulates a crash mid-processing; the source must survive."""

    async def run(self, item_id: str) -> str:  # noqa: ARG002
        from personal_pm_api.inbox.models import InboxItemModel
        from personal_pm_api.inbox.service import InboxService
        from sqlalchemy import select

        service = InboxService(self._factory)
        # Move to PROCESSING first (valid transition), then simulate the crash.
        async with self._factory() as session:
            statement = select(InboxItemModel).where(
                InboxItemModel.id == UUID(str(item_id))
            )
            model = (await session.execute(statement)).scalar_one()
            if model.status == "NEW":
                model.status = "PROCESSING"
                await session.commit()

        await service.mark_failed(item_id, "simulated processing failure")
        raise RuntimeError("simulated processing failure")


def serialize_job_state(operation_id: UUID, item_ids: list[str]) -> str:
    return json.dumps({"operation_id": str(operation_id), "items": item_ids})
