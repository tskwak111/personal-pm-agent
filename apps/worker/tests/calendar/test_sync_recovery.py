from __future__ import annotations

import pytest


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    @property
    def now(self) -> float:
        return self._now

    def advance(self, minutes: float = 0.0, seconds: float = 0.0) -> None:
        self._now += minutes * 60 + seconds


class FakeSyncTarget:
    """Stands in for the delta sync against the provider."""

    def __init__(self) -> None:
        self.sync_calls = 0
        self.provider_version = 5
        self.last_external_id: str | None = None

    async def run_delta_sync(self, external_id: str) -> int:
        self.sync_calls += 1
        self.last_external_id = external_id
        return self.provider_version


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def target() -> FakeSyncTarget:
    return FakeSyncTarget()


def _make_scheduler(clock: FakeClock, target: FakeSyncTarget):  # noqa: ANN202
    from personal_pm_worker.calendar.scheduler import SyncScheduler
    from personal_pm_worker.calendar.sync_jobs import InMemorySyncOperationStore

    return SyncScheduler(
        operations=InMemorySyncOperationStore(),
        clock=clock,
        sync_target=target,
    )


async def test_duplicate_webhook_uses_same_operation(fake_clock, target) -> None:  # noqa: ANN001
    scheduler = _make_scheduler(fake_clock, target)
    payload = {
        "channel_id": "ch-1",
        "resource_state": "exists",
        "message_number": 1,
        "connection_id": "conn-1",
    }
    first = await scheduler.accept_webhook(payload)
    second = await scheduler.accept_webhook(payload)
    assert second.operation_id == first.operation_id


async def test_missed_webhook_is_recovered_within_periodic_window(fake_clock, target) -> None:  # noqa: ANN001
    scheduler = _make_scheduler(fake_clock, target)
    payload = {
        "channel_id": "ch-1",
        "resource_state": "exists",
        "message_number": 7,
        "connection_id": "conn-1",
        "external_event_id": "evt-lost",
    }
    operation = await scheduler.accept_webhook(payload)
    assert target.sync_calls == 1

    # A changed provider event arrives but the webhook is LOST.
    fake_clock.advance(seconds=60)
    await scheduler.register_pending_change("evt-changed", connection_id="conn-1")

    # Recovery poll runs at the 15-minute boundary and picks it up.
    fake_clock.advance(minutes=15)
    await scheduler.run_due()
    assert target.sync_calls >= 2
    assert target.last_external_id == "evt-changed"
    _ = operation
