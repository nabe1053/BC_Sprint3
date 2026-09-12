"""Startup must neither terminate live work nor touch the development database."""
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from app.agent.definition import RECOVERY_GRACE_S, default_run_limits
from app.domain.run_types import InputLimits
from app.models import Document, DocumentPage
from app.repositories import run_repository
from app.repositories.run_repository import RunRepository
from app.services.run_service import RunService
from tests.fixtures.record_data import seed_record_version


@pytest.mark.parametrize(
    "elapsed_offset,expected", [(-1, "running"), (0, "running"), (1, "failed")]
)
async def test_startup_recovers_only_expired_running_runs_and_their_traces(
    db_session, monkeypatch, elapsed_offset, expected
):
    seed = await seed_record_version(db_session)
    doc = Document(
        case_id=seed.case.id,
        file_name="synthetic.txt",
        storage_path="unused",
        kind="text",
        read_status="success",
        received_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()
    db_session.add(
        DocumentPage(document_id=doc.id, seq=1, locator="body:1", text="synthetic")
    )
    await db_session.commit()
    trace = Mock()
    repository = RunRepository(db_session, file_size=lambda doc: 1, trace=trace)
    limits = default_run_limits()
    service = RunService(
        repository,
        limits=limits,
        input_limits=InputLimits(),
        scheduler=lambda run: None,
    )
    run = await service.start(seed.case.id, seed.rule.rule_version)
    now = datetime.now(UTC)
    run.started_at = now - timedelta(
        seconds=limits.outer_timeout_s + RECOVERY_GRACE_S + elapsed_offset
    )
    await db_session.commit()
    trace.reset_mock()

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(run_repository, "datetime", Clock)
    await repository.recover_interrupted()
    await db_session.refresh(run)
    assert run.outcome == expected
    if expected == "running":
        assert run.ended_at is None
        trace.sync.assert_not_called()
    else:
        assert run.stage_detail == "process_interrupted" and run.stop_reason == "failed"
        trace.sync.assert_called_once()
        assert trace.sync.call_args.args[0] == run.id


def test_testclient_lifespan_uses_only_test_database(client):
    # client fixture rejects any construction of the development session maker.
    response = client.get("/api/v1/ui/cases")
    assert response.status_code == 200 and response.json() == {"cases": []}
