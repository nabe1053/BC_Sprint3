"""Recovery waits for terminal persistence without accessing a database."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories import run_repository
from app.repositories.run_repository import RunRepository


@pytest.mark.parametrize("method", ["recover_interrupted", "recover_expired"])
@pytest.mark.parametrize("offset,recovers", [(-1, False), (0, False), (1, True)])
async def test_both_recovery_paths_wait_for_terminal_grace(
    monkeypatch, method, offset, recovers
):
    now = datetime.now(UTC)
    run = SimpleNamespace(
        id=42,
        outcome="running",
        limits={"outerTimeoutS": 120},
        started_at=now - timedelta(seconds=120 + 16 + offset),
        turns=7,
    )
    session = AsyncMock()
    from unittest.mock import Mock

    session.execute.return_value = Mock()
    session.execute.return_value.scalars.return_value = [run]
    repository = RunRepository(session, file_size=lambda doc: 1)
    repository.finish = AsyncMock()

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(run_repository, "datetime", Clock)
    await getattr(repository, method)()
    if recovers:
        repository.finish.assert_awaited_once()
        run_id, result = repository.finish.call_args.args
        assert run_id == run.id
        if method == "recover_interrupted":
            assert (
                result.stop_reason == "failed"
                and result.detail == "process_interrupted"
            )
        else:
            assert (
                result.stop_reason == "outer_timeout"
                and result.detail == "terminal_recovery"
            )
            assert result.turns == 7
    else:
        repository.finish.assert_not_awaited()
