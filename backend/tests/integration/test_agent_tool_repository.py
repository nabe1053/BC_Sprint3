"""Real PostgreSQL tool persistence, scope, coverage and cancellation contracts."""
import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.definition import default_run_limits
from app.agent.tools import ToolExecutor
from app.domain.run_types import InputLimits, RunContext, RunResult
from app.models import Case, RuleSet, Document, DocumentPage, EmailPart, AgentRunStep
from app.models.drafts import CaseHeader
from app.repositories.agent_tool_repository import AgentToolGateway
from app.repositories.run_repository import RunRepository
from app.services.run_service import RunService


@pytest.fixture
async def tool_run(db_session):
    case = Case(case_code="LOCAL-TOOLS")
    rule = RuleSet(rule_version="local-tools", rules={}, is_current=False)
    db_session.add_all([case, rule])
    await db_session.flush()
    doc = Document(
        case_id=case.id,
        file_name="synthetic.txt",
        storage_path="unused",
        kind="text",
        read_status="success",
        received_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()
    db_session.add_all(
        [
            DocumentPage(
                document_id=doc.id,
                seq=i,
                locator=f"body:{i}",
                text=f"synthetic-source-{i}",
            )
            for i in (1, 2)
        ]
    )
    await db_session.commit()
    limits = default_run_limits()
    repository = RunRepository(db_session, file_size=lambda d: 1)
    run = await RunService(
        repository, limits=limits, input_limits=InputLimits(), scheduler=lambda r: None
    ).start(case.id, rule.rule_version)
    context = RunContext(run.id, case.id, run.version_id, rule.id, limits)
    gateway = AgentToolGateway(
        async_sessionmaker(db_session.bind, expire_on_commit=False)
    )
    return context, doc, gateway


async def test_read_success_records_exact_coverage_without_source_text(
    db_session, tool_run
):
    context, doc, gateway = tool_run
    reply = await ToolExecutor(context, gateway).invoke(
        "read_document", {"document_id": doc.id, "from_seq": 2}
    )
    assert not reply.is_error and reply.data["pages"][0]["text"] == "synthetic-source-2"
    snapshot = await RunRepository(db_session, file_size=lambda d: 1).snapshot(
        context.version_id
    )
    assert snapshot.scanned_ranges == {(doc.id, "body:2")}
    steps = list(
        (
            await db_session.execute(
                select(AgentRunStep).where(AgentRunStep.agent_run_id == context.run_id)
            )
        ).scalars()
    )
    assert all(
        "synthetic-source" not in str(s.trace_event) + str(s.args_summary)
        for s in steps
    )
    assert steps[-1].trace_event["observation"]["status"] == "ok"


async def test_other_case_document_is_rejected_before_read(db_session, tool_run):
    context, doc, gateway = tool_run
    other = Case(case_code="OTHER-TOOLS")
    db_session.add(other)
    await db_session.flush()
    doc.case_id = other.id
    await db_session.commit()
    reply = await ToolExecutor(context, gateway).invoke(
        "read_document", {"document_id": doc.id}
    )
    assert reply.is_error and reply.data["code"] == "E_NOT_FOUND"


async def test_duplicate_email_locator_cannot_mark_scanned(db_session, tool_run):
    context, doc, gateway = tool_run
    doc.kind = "eml"
    db_session.add_all(
        [
            EmailPart(
                document_id=doc.id, part_role="latest_body", seq=1, body="synthetic"
            )
            for _ in range(2)
        ]
    )
    await db_session.commit()
    reply = await ToolExecutor(context, gateway).invoke(
        "read_email", {"document_id": doc.id}
    )
    assert reply.is_error
    assert not (
        await RunRepository(db_session, file_size=lambda d: 1).snapshot(
            context.version_id
        )
    ).scanned_ranges


async def test_parallel_steps_are_serialized_by_run_lock(db_session, tool_run):
    context, doc, gateway = tool_run
    executors = [ToolExecutor(context, gateway) for _ in range(4)]
    replies = await asyncio.gather(
        *(
            e.invoke(
                "read_document", {"document_id": doc.id, "from_seq": 1, "to_seq": 1}
            )
            for e in executors
        )
    )
    assert all(not r.is_error for r in replies)
    steps = list(
        (
            await db_session.execute(
                select(AgentRunStep)
                .where(AgentRunStep.agent_run_id == context.run_id)
                .order_by(AgentRunStep.seq)
            )
        ).scalars()
    )
    assert [s.seq for s in steps] == [1, 2, 3, 4, 5]


async def test_closed_operation_rolls_back_artifact(db_session, tool_run):
    context, doc, gateway = tool_run
    executor = ToolExecutor(context, gateway)
    step = await gateway.begin_step(
        context, "record_case_header", "safe-digest", "extracting", executor.closed
    )
    with pytest.raises(asyncio.CancelledError):
        async with gateway.operation(context, step, executor.closed) as repo:
            repo.session.add(
                CaseHeader(
                    version_id=context.version_id,
                    inquiry_no_state="not_stated",
                    customer_name_state="not_stated",
                    due_state="not_stated",
                    place_state="not_stated",
                    incoterms_state="not_stated",
                    quote_deadline_tz_state="missing",
                )
            )
            await repo.session.flush()
            executor.close()
    assert (await db_session.execute(select(CaseHeader))).scalars().all() == []


async def test_terminated_run_rejects_new_tool(db_session, tool_run):
    context, doc, gateway = tool_run
    await RunRepository(db_session, file_size=lambda d: 1).finish(
        context.run_id, RunResult("outer_timeout")
    )
    from app.domain.draft_errors import DraftError

    with pytest.raises(DraftError) as exc:
        await ToolExecutor(context, gateway).invoke(
            "read_email", {"document_id": doc.id}
        )
    assert exc.value.code == "E_RUN_NOT_ACTIVE"


async def test_interruption_records_remaining_ranges_once(db_session, tool_run):
    from app.agent.runner import LocalAgentWorker
    from app.models.documents import DocumentIssue
    from app.models import AgentRun

    context, doc, gateway = tool_run
    await ToolExecutor(context, gateway).invoke(
        "read_document", {"document_id": doc.id, "from_seq": 1, "to_seq": 1}
    )
    worker = LocalAgentWorker(gateway)
    result = RunResult("max_turns", 1)
    await worker.prepare_finish(context, result)
    await worker.prepare_finish(context, result)
    issues = list(
        (
            await db_session.execute(
                select(DocumentIssue).where(
                    DocumentIssue.agent_run_id == context.run_id
                )
            )
        ).scalars()
    )
    assert [(i.document_id, i.locator, i.issue_type) for i in issues] == [
        (doc.id, "body:2", "not_scanned")
    ]
    run = await db_session.get(AgentRun, context.run_id)
    assert run.validation_result is not None


async def test_local_implementation_version_is_saved(db_session, tool_run):
    from app.models import AgentRun

    context, doc, gateway = tool_run
    run = await db_session.get(AgentRun, context.run_id)
    assert run.impl_version == "local-agent-tools-v1"


@pytest.mark.parametrize(
    "name,key,model_name",
    [
        ("record_evidence", "evidences", "Evidence"),
        ("record_question", "questions", "Question"),
    ],
)
@pytest.mark.parametrize("size", [1, 3])
async def test_batch_tool_persists_all_rows_and_exact_observation_count(
    db_session, tool_run, name, key, model_name, size
):
    from app.models import drafts

    context, doc, gateway = tool_run
    rows = [
        {
            "field": f"field-{i}",
            "raw_value": "synthetic-source",
            "adopted_value": "synthetic-source",
            "document_id": doc.id,
            "locator": "body:1",
            "quote": "synthetic-source",
        }
        if key == "evidences"
        else {
            "question_code": f"Q{i}",
            "target_field": "qty",
            "reason": "synthetic-source",
        }
        for i in range(size)
    ]
    reply = await ToolExecutor(context, gateway).call(name, {key: rows})
    assert not reply.is_error
    model = getattr(drafts, model_name)
    saved = (
        (
            await db_session.execute(
                select(model)
                .where(model.version_id == context.version_id)
                .order_by(model.id)
            )
        )
        .scalars()
        .all()
    )
    assert [row.id for row in saved] == [
        row[key[:-1] + "_id"] for row in reply.data[key]
    ]
    assert len(saved) == size
    step = (
        await db_session.execute(
            select(AgentRunStep).where(
                AgentRunStep.agent_run_id == context.run_id,
                AgentRunStep.tool_name == name,
            )
        )
    ).scalar_one()
    assert step.trace_event["observation"] == {
        "status": "ok",
        "count": size,
        "code": None,
    }
    assert "synthetic-source" not in str(step.trace_event) + step.args_summary


@pytest.mark.parametrize(
    "name,key,model_name",
    [
        ("record_evidence", "evidences", "Evidence"),
        ("record_question", "questions", "Question"),
    ],
)
async def test_invalid_later_batch_row_rolls_back_every_row(
    db_session, tool_run, name, key, model_name
):
    from app.models import drafts

    context, doc, gateway = tool_run
    first = (
        {
            "field": "qty",
            "raw_value": "150 MT",
            "adopted_value": "150 MT",
            "document_id": doc.id,
            "locator": "body:1",
            "quote": "150 MT",
        }
        if key == "evidences"
        else {"question_code": "Q1", "target_field": "qty", "reason": "synthetic"}
    )
    reply = await ToolExecutor(context, gateway).call(
        name, {key: [first, {**first, "item_id": 999999}]}
    )
    assert reply.is_error and reply.data == {
        "code": "E_NOT_FOUND" if key == "evidences" else "E_TARGET_INVALID"
    }
    model = getattr(drafts, model_name)
    assert (
        await db_session.execute(
            select(model).where(model.version_id == context.version_id)
        )
    ).scalars().all() == []


@pytest.mark.parametrize("reason", ["inactivity_timeout", "inner_timeout"])
async def test_interruption_diagnostics_reach_trace_and_http_stop_reason_once(
    db_session, tool_run, reason, tmp_path
):
    import json
    import httpx
    from fastapi import FastAPI
    from types import SimpleNamespace
    from app.agent.runner import LocalAgentWorker
    from app.domain.run_types import HeartbeatDiagnostics
    from app.api.dependencies import get_run_service
    from app.api.ui.endpoints.agent_runs import router
    from app.repositories.run_trace_store import RunTraceStore

    context, _, gateway = tool_run
    result = RunResult(reason, 1, heartbeat_diagnostics=HeartbeatDiagnostics(12.5, 7))
    worker = LocalAgentWorker(gateway)
    await worker.prepare_finish(context, result)
    await worker.prepare_finish(context, result)
    repository = RunRepository(
        db_session, file_size=lambda d: 1, trace=RunTraceStore(tmp_path)
    )
    await repository.finish(context.run_id, result)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/ui")
    app.dependency_overrides[get_run_service] = lambda: SimpleNamespace(
        progress=repository.progress
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/ui/agent-runs/{context.run_id}")
    assert response.status_code == 200
    assert response.json()["stopReason"] == reason
    events = list(
        (
            await db_session.execute(
                select(AgentRunStep.trace_event).where(
                    AgentRunStep.agent_run_id == context.run_id,
                    AgentRunStep.trace_event.is_not(None),
                )
            )
        ).scalars()
    )
    interrupted = [event for event in events if event["tool"] == "job_interrupted"]
    assert len(interrupted) == 1
    observation = interrupted[0]["observation"]
    assert observation == {
        "status": "error",
        "count": 2,
        "code": reason,
        "sinceLastHeartbeatS": 12.5,
        "heartbeats": 7,
    }
    assert all(
        type(observation[key]) in (int, float)
        for key in ("sinceLastHeartbeatS", "heartbeats")
    )
    assert "synthetic-source" not in json.dumps(events)
    stored = [
        json.loads(line)
        for line in (tmp_path / f"{context.run_id}.jsonl").read_text().splitlines()
    ]
    assert (
        next(event for event in stored if event["tool"] == "job_interrupted")[
            "observation"
        ]
        == observation
    )


async def test_document_progress_uses_unique_fully_read_documents(db_session, tool_run):
    import json
    from app.models import AgentRun

    context, doc, gateway = tool_run
    executor = ToolExecutor(context, gateway)
    run = await db_session.get(AgentRun, context.run_id)
    run.stage_detail = "trace_write_failed"
    await db_session.commit()

    async def progress():
        await db_session.refresh(run)
        return json.loads(run.stage_detail)

    await executor.call("list_case_documents", {})
    assert await progress() == {"documentsRead": 0, "documentsTotal": 1}
    step = (
        await db_session.execute(
            select(AgentRunStep).where(
                AgentRunStep.agent_run_id == context.run_id,
                AgentRunStep.tool_name == "list_case_documents",
            )
        )
    ).scalar_one()
    assert step.trace_event["observation"]["code"] == "trace_write_failed"
    await executor.call(
        "read_document", {"document_id": doc.id, "from_seq": 1, "to_seq": 1}
    )
    assert await progress() == {"documentsRead": 0, "documentsTotal": 1}
    await executor.call(
        "read_document", {"document_id": doc.id, "from_seq": 2, "to_seq": 2}
    )
    assert await progress() == {"documentsRead": 1, "documentsTotal": 1}
    await executor.call("read_document", {"document_id": doc.id})
    await executor.call("list_case_documents", {})
    assert await progress() == {"documentsRead": 1, "documentsTotal": 1}


async def test_failed_or_empty_reads_do_not_increment_document_progress(
    db_session, tool_run
):
    import json
    from app.models import AgentRun
    from sqlalchemy import update

    context, doc, gateway = tool_run
    await db_session.execute(
        update(DocumentPage).where(DocumentPage.document_id == doc.id).values(text=None)
    )
    await db_session.commit()
    executor = ToolExecutor(context, gateway)
    await executor.call("list_case_documents", {})
    await executor.call("read_document", {"document_id": doc.id})
    await executor.call("read_document", {"document_id": doc.id + 999})
    run = await db_session.get(AgentRun, context.run_id)
    assert json.loads(run.stage_detail) == {"documentsRead": 0, "documentsTotal": 1}


async def test_reading_progress_is_exposed_by_http(db_session, tool_run):
    import json
    import httpx
    from fastapi import FastAPI
    from types import SimpleNamespace
    from app.api.dependencies import get_run_service
    from app.api.ui.endpoints.agent_runs import router

    context, doc, gateway = tool_run
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/ui")
    repository = RunRepository(db_session, file_size=lambda d: 1)
    app.dependency_overrides[get_run_service] = lambda: SimpleNamespace(
        progress=repository.progress
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for tool, arguments, read in [
            ("list_case_documents", {}, 0),
            ("read_document", {"document_id": doc.id}, 1),
        ]:
            await ToolExecutor(context, gateway).call(tool, arguments)
            response = await client.get(f"/api/v1/ui/agent-runs/{context.run_id}")
            assert response.status_code == 200
            body = response.json()
            assert body["outcome"] == "running" and body["stage"] == "reading"
            assert body["versionId"] is None and body["isComplete"] is False
            assert json.loads(body["stageDetail"]) == {
                "documentsRead": read,
                "documentsTotal": 1,
            }


@pytest.mark.parametrize(
    "tool_name,arguments,code",
    [
        ("Bash", {"command": "synthetic-private-input"}, "E_TOOL_NOT_REGISTERED"),
        (
            "mcp__app__search_documents",
            {"query": "https://synthetic-private-input.invalid"},
            "E_EXTERNAL_LINK_BLOCKED",
        ),
    ],
)
async def test_sdk_permission_denial_is_one_sanitized_management_event(
    db_session,
    tool_run,
    monkeypatch,
    tmp_path,
    tool_name,
    arguments,
    code,
):
    from functools import partial
    from claude_agent_sdk import ResultMessage
    from pydantic import SecretStr
    from app.agent import claude_policy
    from app.agent.runner import LocalAgentWorker
    from app.repositories.run_trace_store import RunTraceStore

    context, _, gateway = tool_run

    async def query(**kwargs):
        yield ResultMessage(
            subtype="success",
            duration_ms=0,
            duration_api_ms=0,
            is_error=False,
            num_turns=0,
            session_id="synthetic",
            permission_denials=[
                {
                    "tool_name": tool_name,
                    "tool_input": arguments,
                    "reason": "synthetic-private-input",
                    "tool_use_id": "synthetic-private-input",
                }
            ],
        )

    monkeypatch.setattr(claude_policy, "query", query)
    outcome = await LocalAgentWorker(
        gateway,
        partial(
            claude_policy.claude_policy,
            api_key=SecretStr("synthetic-key"),
        ),
    )(context)
    assert outcome.turns == 0
    steps = list(
        (
            await db_session.execute(
                select(AgentRunStep).where(
                    AgentRunStep.agent_run_id == context.run_id,
                    AgentRunStep.tool_name == "guardrail_denied",
                )
            )
        ).scalars()
    )
    assert len(steps) == 1
    event = steps[0].trace_event
    assert event["observation"]["code"] == code
    assert event["tool_use"]["deniedTool"] == tool_name
    assert "synthetic-private-input" not in repr(event) + steps[0].args_summary
    store = RunTraceStore(tmp_path)
    store.sync(context.run_id, [event])
    assert (
        "synthetic-private-input"
        not in (tmp_path / f"{context.run_id}.jsonl").read_text()
    )
