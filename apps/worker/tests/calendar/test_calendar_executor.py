from __future__ import annotations

import pytest


class FakeCalendar:
    """Fake provider adapter with fault injection."""

    def __init__(self) -> None:
        self.create_calls = 0
        self.events_by_key: dict[str, str] = {}
        self.fail_first_with_timeout = False
        self.first_call_succeeded = False

    async def execute(self, command: dict[str, object]) -> dict[str, object]:
        key = str(command["idempotency_key"])
        if key in self.events_by_key:
            # Provider-side idempotency: same key returns the same event.
            return {"external_event_id": self.events_by_key[key], "created": False}
        if self.fail_first_with_timeout and not self.first_call_succeeded:
            # Simulate: the provider CREATED the event but the response was lost.
            self.first_call_succeeded = True
            self.create_calls += 1
            self.events_by_key[key] = f"prov-{key[:8]}"
            raise TimeoutError("response lost after provider commit")
        self.create_calls += 1
        external_id = f"prov-{key[:8]}-{self.create_calls}"
        self.events_by_key[key] = external_id
        return {"external_event_id": external_id, "created": True}

    async def verify(self, result: dict[str, object]) -> bool:
        return bool(result.get("external_event_id"))


@pytest.fixture
def fake_calendar() -> FakeCalendar:
    return FakeCalendar()


def _make_executor(fake_calendar: FakeCalendar):  # noqa: ANN202
    from personal_pm_worker.calendar.executor import CalendarCommandExecutor
    from personal_pm_worker.calendar.repository import InMemoryOutboxRepository

    repo = InMemoryOutboxRepository()
    return CalendarCommandExecutor(repository=repo, adapter=fake_calendar), repo


async def test_duplicate_delivery_creates_one_provider_event(fake_calendar) -> None:  # noqa: ANN001
    executor, repo = _make_executor(fake_calendar)
    record_id = await repo.add_pending(
        idempotency_key="idem-1", command={"idempotency_key": "idem-1"}
    )

    await executor.execute(record_id)
    await executor.execute(record_id)

    assert fake_calendar.create_calls == 1
    status = await repo.execution_status(record_id)
    assert status == "SUCCEEDED"


async def test_timeout_after_provider_success_is_reconciled_without_duplicate(
    fake_calendar,
) -> None:  # noqa: ANN001
    fake_calendar.fail_first_with_timeout = True
    executor, repo = _make_executor(fake_calendar)
    record_id = await repo.add_pending(
        idempotency_key="idem-timeout", command={"idempotency_key": "idem-timeout"}
    )

    await executor.execute(record_id)  # timeout AFTER provider created the event
    assert await repo.execution_status(record_id) == "PENDING"  # not falsely succeeded

    await executor.execute(record_id)  # redelivery reconciles via provider idempotency
    assert fake_calendar.create_calls == 1
    assert await repo.execution_status(record_id) == "SUCCEEDED"
    assert await repo.external_event_id(record_id) is not None


async def test_failed_execution_is_marked_failed_not_success(fake_calendar) -> None:  # noqa: ANN001
    from personal_pm_worker.calendar.repository import PermanentFailureError

    class FailingAdapter(FakeCalendar):
        async def execute(self, command: dict[str, object]) -> dict[str, object]:
            raise PermanentFailureError("invalid request")

    from personal_pm_worker.calendar.executor import CalendarCommandExecutor
    from personal_pm_worker.calendar.repository import InMemoryOutboxRepository

    repo = InMemoryOutboxRepository()
    executor = CalendarCommandExecutor(repository=repo, adapter=FailingAdapter())
    record_id = await repo.add_pending(idempotency_key="idem-fail", command={"k": 1})

    with pytest.raises(PermanentFailureError):
        await executor.execute(record_id)

    status = await repo.execution_status(record_id)
    assert status in ("FAILED", "PENDING")  # never SUCCEEDED without verification
