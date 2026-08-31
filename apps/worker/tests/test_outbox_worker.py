from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4


class _Result:
    def __init__(self, *, rows=(), one=None) -> None:  # noqa: ANN001
        self._rows = rows
        self._one = one

    def scalars(self):  # noqa: ANN201
        return self._rows

    def scalar_one_or_none(self):  # noqa: ANN201
        return self._one


class _Session:
    def __init__(self, state) -> None:  # noqa: ANN001
        self.state = state
        self.current = None
        self.calls = 0

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_args) -> None:  # noqa: ANN002
        return None

    async def execute(self, _statement):  # noqa: ANN001, ANN201
        self.calls += 1
        if self.calls == 1:
            pending = next((row for row in self.state.events if row.status == "pending"), None)
            self.current = pending
            return _Result(rows=[] if pending is None else [pending])
        return _Result(one=self.state.executions.get(self.current.id))

    async def commit(self) -> None:
        return None


class _Factory:
    def __init__(self, events) -> None:  # noqa: ANN001
        self.state = SimpleNamespace(
            events=events,
            executions={
                event.id: SimpleNamespace(
                    external_id=None,
                    result_status="Pending",
                    verified=False,
                )
                for event in events
            },
        )

    def __call__(self):  # noqa: ANN204
        return _Session(self.state)


def _events(count: int):  # noqa: ANN201
    return [
        SimpleNamespace(
            id=uuid4(),
            workspace_id=uuid4(),
            idempotency_key=f"outbox-{index}",
            command_type="CREATE_FOCUS_BLOCK",
            payload={"index": index},
            status="pending",
            attempts=0,
            last_error=None,
        )
        for index in range(count)
    ]


async def test_run_once_processes_pending_outbox_and_counts_failures() -> None:
    from personal_pm_worker.outbox_worker import VerifiedExecution, run_once

    factory = _Factory(_events(2))

    class Executor:
        async def execute(self, command):  # noqa: ANN001, ANN201
            if command.idempotency_key == "outbox-0":
                return VerifiedExecution(external_id="provider-1", verified=True)
            return VerifiedExecution(external_id=None, verified=False)

    result = await run_once(factory, Executor(), batch_size=10)

    assert result.claimed == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert [event.status for event in factory.state.events] == ["succeeded", "failed"]
    assert factory.state.executions[factory.state.events[0].id].verified is True


async def test_run_once_without_executor_fails_closed() -> None:
    from personal_pm_worker.outbox_worker import run_once

    factory = _Factory(_events(2))
    result = await run_once(factory, None, batch_size=10)

    assert result.succeeded == 0
    assert result.failed == result.claimed == 2
    assert all(event.status == "failed" for event in factory.state.events)
