"""F-16: 資料の除外（論理削除）。04-db `document_exclusions`・05-api-ipo #4/#5a/#5b/#12・agent-plan ツール権限。

除外は物理削除でも UPDATE でもなく D層の追記。除外済みの資料は受付一覧・件数上限・
案の作成の入力・エージェントの読取ツールから外れる。
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.definition import default_run_limits
from app.agent.tools import ToolExecutor
from app.domain.draft_errors import DraftError
from app.domain.run_types import InputLimits, RunContext
from app.models import AgentRun, Case, Document, DocumentPage, RuleSet
from app.repositories.agent_tool_repository import AgentToolGateway
from app.repositories.document_repository import DocumentRepository
from app.repositories.run_repository import RunRepository
from app.services.run_service import RunService


async def _case_with_docs(session, *names):
    case = Case(case_code="EXCL-" + "-".join(names))
    rule = RuleSet(rule_version="excl-" + "-".join(names), rules={}, is_current=False)
    session.add_all([case, rule])
    await session.flush()
    docs = []
    for name in names:
        doc = Document(
            case_id=case.id,
            file_name=f"{name}.txt",
            storage_path="unused",
            kind="text",
            read_status="success",
            received_at=datetime.now(UTC),
        )
        session.add(doc)
        await session.flush()
        session.add(
            DocumentPage(
                document_id=doc.id, seq=1, locator="body:1", text=f"needle {name}"
            )
        )
        docs.append(doc)
    await session.commit()
    return case, rule, docs


def _service(session):
    return RunService(
        RunRepository(session, file_size=lambda d: 1),
        limits=default_run_limits(),
        input_limits=InputLimits(),
        scheduler=lambda r: None,
    )


async def test_excluded_document_leaves_list_count_and_search(db_session):
    case, _, (keep, drop) = await _case_with_docs(db_session, "keep", "drop")
    repo = DocumentRepository(db_session)

    record = await repo.exclude(case.id, drop.id, "担当", datetime.now(UTC))

    assert (record.document_id, record.recorded_by) == (drop.id, "担当")
    assert [d.id for d in await repo.list_by_case(case.id)] == [keep.id]
    assert await repo.count_by_case(case.id) == 1
    assert [d.id for d, _ in await repo.search_pages(case.id, "needle", 10)] == [
        keep.id
    ]
    excluded = await repo.list_exclusions(case.id)
    assert [(d.id, e.recorded_by) for d, e in excluded] == [(drop.id, "担当")]
    # 資料そのもの・抽出結果は消さない（既存版の根拠から参照できる）。
    assert await repo.get_by_id(drop.id) is not None
    assert await repo.list_pages(drop.id)


@pytest.mark.parametrize(
    "setup, code",
    [
        ("twice", "E_ALREADY_EXCLUDED"),
        ("other_case", "E_NOT_FOUND"),
        ("running", "E_RUN_IN_PROGRESS"),
    ],
)
async def test_exclude_rejects_repeat_other_case_and_running_run(
    db_session, setup, code
):
    case, rule, (doc,) = await _case_with_docs(db_session, setup)
    other, _, _ = await _case_with_docs(db_session, setup + "-other")
    repo = DocumentRepository(db_session)
    target_case = case.id
    if setup == "twice":
        await repo.exclude(case.id, doc.id, "担当", datetime.now(UTC))
    if setup == "other_case":
        target_case = other.id
    if setup == "running":
        await _service(db_session).start(case.id, rule.rule_version)

    with pytest.raises(DraftError) as raised:
        await repo.exclude(target_case, doc.id, "担当", datetime.now(UTC))

    assert raised.value.code == code


async def test_run_start_ignores_excluded_documents(db_session):
    case, rule, (keep, drop) = await _case_with_docs(db_session, "in", "out")
    await DocumentRepository(db_session).exclude(
        case.id, drop.id, "担当", datetime.now(UTC)
    )

    run = await _service(db_session).start(case.id, rule.rule_version)

    context = RunContext(run.id, case.id, run.version_id, rule.id, default_run_limits())
    gateway = AgentToolGateway(
        async_sessionmaker(db_session.bind, expire_on_commit=False)
    )
    tools = ToolExecutor(context, gateway)
    listed = await tools.invoke("list_case_documents", {"case_id": case.id})
    assert [d["document_id"] for d in listed.data["documents"]] == [keep.id]
    found = await tools.invoke(
        "search_documents", {"case_id": case.id, "query": "needle"}
    )
    assert {r["document_id"] for r in found.data["results"]} == {keep.id}
    denied = await tools.invoke("read_document", {"document_id": drop.id})
    assert denied.is_error
    assert (
        await tools.invoke("read_document", {"document_id": keep.id})
    ).is_error is False


async def test_run_start_fails_when_only_excluded_documents_are_readable(db_session):
    case, rule, (doc,) = await _case_with_docs(db_session, "only")
    await DocumentRepository(db_session).exclude(
        case.id, doc.id, "担当", datetime.now(UTC)
    )

    with pytest.raises(DraftError) as raised:
        await _service(db_session).start(case.id, rule.rule_version)

    assert raised.value.code == "E_NO_READABLE_DOCUMENT"
    assert (await db_session.execute(select(AgentRun))).first() is None


async def _excluded_run(session):
    """keep だけが入力の run（drop は起動前に除外）と、そのツール実行器。"""
    case, rule, (keep, drop) = await _case_with_docs(session, "k2", "d2")
    await DocumentRepository(session).exclude(
        case.id, drop.id, "担当", datetime.now(UTC)
    )
    run = await _service(session).start(case.id, rule.rule_version)
    context = RunContext(run.id, case.id, run.version_id, rule.id, default_run_limits())
    gateway = AgentToolGateway(async_sessionmaker(session.bind, expire_on_commit=False))
    return ToolExecutor(context, gateway), keep, drop


async def test_excluded_document_does_not_block_completion_check(db_session):
    """RV-058 P1: 除外済み資料の範囲を「未走査」に数えない（読めない範囲を完了条件に残さない）。"""
    tools, keep, drop = await _excluded_run(db_session)
    assert not (await tools.invoke("read_document", {"document_id": keep.id})).is_error

    result = await tools.invoke("validate_draft", {})

    unscanned = [
        v for v in result.data["violations"] if v.get("kind") == "unscanned_range"
    ]
    assert all(v.get("document_id") != drop.id for v in unscanned)


async def test_agent_cannot_record_evidence_against_excluded_document(db_session):
    """RV-058 P2: 書込系ツールも除外済み資料を出典にできない（同じ引数で除外していない資料は通る）。"""
    tools, keep, drop = await _excluded_run(db_session)

    def evidence(document, quote):
        return {
            "evidences": [
                {
                    "field": "inquiry_no",
                    "raw_value": "X",
                    "adopted_value": "X",
                    "document_id": document.id,
                    "locator": "body:1",
                    "quote": quote,
                }
            ]
        }

    denied = await tools.invoke("record_evidence", evidence(drop, "needle d2"))
    assert denied.is_error and denied.data["code"] == "E_NOT_FOUND"
    allowed = await tools.invoke("record_evidence", evidence(keep, "needle k2"))
    assert not allowed.is_error, allowed.data
