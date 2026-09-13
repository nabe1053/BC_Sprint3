"""Approval policy exercised through a locked repository double."""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest

from app.domain.draft_errors import DraftError
from tests.fixtures.record_data import approval_questions


@pytest.fixture
def repository():
    version = N(id=7, current_state="draft")
    active = []

    @asynccontextmanager
    async def record(version_id):
        active.append(version_id)
        try:
            yield version
        finally:
            active.pop()

    async def save(*args, **kwargs):
        assert active == [7]
        return N(args=args, **kwargs)

    return N(
        version=version,
        active=active,
        record=record,
        item_rows=AsyncMock(return_value={2: "R2", 1: "R1"}),
        matched_item_ids=AsyncMock(return_value={1, 2}),
        coverage_confirmed=AsyncMock(return_value=True),
        list_questions_with_latest=AsyncMock(return_value=approval_questions()),
        item=AsyncMock(),
        unlinked_bounce_comments=AsyncMock(return_value=[]),
        save_state_event=AsyncMock(side_effect=save),
        save_bounce_comment=AsyncMock(side_effect=save),
        save_bounce=AsyncMock(side_effect=save),
        save_sendoff=AsyncMock(side_effect=save),
        list_records=AsyncMock(return_value={"edits": []}),
        list_versions_with_records=AsyncMock(return_value=[]),
    )


@pytest.mark.parametrize(
    "state,target,by,matched,coverage,code",
    [
        ("draft", "draft", " ", set(), False, "E_RECORDER_REQUIRED"),
        ("draft", "draft", "人", set(), False, "E_STATE_ROLLBACK_FORBIDDEN"),
        ("draft", "review_checked", "人", set(), False, "E_STATE_ORDER"),
        ("draft", "staff_checked", "人", set(), False, "E_STAFF_CHECK_INCOMPLETE"),
        ("draft", "staff_checked", "人", {1, 2}, False, "E_COVERAGE_NOT_RECORDED"),
    ],
)
async def test_transition_error_priority(
    repository, state, target, by, matched, coverage, code
):
    from app.services.approval_service import ApprovalService

    repository.version.current_state = state
    repository.matched_item_ids.return_value = matched
    repository.coverage_confirmed.return_value = coverage
    with pytest.raises(DraftError) as error:
        await ApprovalService(repository).transition(
            7, {"to_state": target, "recorded_by": by}
        )
    assert error.value.code == code
    if code == "E_STAFF_CHECK_INCOMPLETE":
        assert error.value.details == {
            "unmatchedItemIds": [1, 2],
            "unmatchedRowCodes": ["R1", "R2"],
            "coverageRecorded": False,
        }
    repository.save_state_event.assert_not_awaited()


@pytest.mark.parametrize(
    "state,target", [("draft", "staff_checked"), ("staff_checked", "review_checked")]
)
async def test_transition_records_current_unresolved_and_server_time(
    repository, state, target
):
    from app.services.approval_service import ApprovalService

    repository.version.current_state = state
    before = datetime.now(UTC)
    result = await ApprovalService(repository).transition(
        7, {"to_state": target, "recorded_by": " 人 "}
    )
    after = datetime.now(UTC)
    repository.save_state_event.assert_awaited_once()
    assert result.args == (repository.version,)
    assert (
        result.from_state,
        result.to_state,
        result.recorded_by,
        result.unresolved_count,
    ) == (state, target, "人", 2)
    assert before <= result.recorded_at <= after and result.recorded_at.tzinfo is UTC


@pytest.mark.parametrize(
    "state,code",
    [
        ("draft", "E_STAFF_CHECK_INCOMPLETE"),
        ("review_checked", "E_STATE_ORDER"),
        ("staff_checked", "E_NO_BOUNCE_COMMENT"),
    ],
)
async def test_bounce_requires_staff_state_then_unlinked_comment(
    repository, state, code
):
    from app.services.approval_service import ApprovalService

    repository.version.current_state = state
    with pytest.raises(DraftError) as error:
        await ApprovalService(repository).bounce(7, {"recorded_by": "人"})
    assert error.value.code == code
    repository.save_bounce.assert_not_awaited()
    repository.save_state_event.assert_not_awaited()


async def test_bounce_builds_reason_and_links_exact_comments_under_lock(repository):
    from app.services.approval_service import ApprovalService

    repository.version.current_state = "staff_checked"
    at = datetime.now(UTC)
    comments = [
        N(id=2, item_id=2, comment="後", recorded_at=at),
        N(id=1, item_id=1, comment="先", recorded_at=at),
    ]
    repository.unlinked_bounce_comments.return_value = comments
    before = datetime.now(UTC)
    result = await ApprovalService(repository).bounce(7, {"recorded_by": " 人 "})
    version_id, data, linked = result.args
    assert version_id == 7 and linked is comments
    assert data["reason"] == "R1: 先\nR2: 後" and data["recorded_by"] == "人"
    assert before <= data["recorded_at"] <= datetime.now(UTC)
    assert repository.version.current_state == "staff_checked"
    repository.save_state_event.assert_not_awaited()


@pytest.mark.parametrize("state", ["draft", "staff_checked", "review_checked"])
async def test_comment_and_sendoff_accept_any_finalized_state_with_server_time(
    repository, state
):
    from app.services.approval_service import ApprovalService

    repository.version.current_state = state
    service = ApprovalService(repository)
    before = datetime.now(UTC)
    comment = await service.comment(
        7, {"item_id": 1, "comment": " 修正 ", "recorded_by": " 人 "}
    )
    sendoff = await service.decide_sendoff(
        7, {"decision": "approved", "reason": " 可 ", "recorded_by": " 人 "}
    )
    repository.item.assert_awaited_once_with(7, 1)
    assert comment.args[1]["comment"] == "修正"
    assert (
        sendoff.args[1]["decision"] == "approved" and sendoff.args[1]["reason"] == "可"
    )
    for result in (comment, sendoff):
        assert result.args[0] == 7
        assert result.args[1]["recorded_by"] == "人"
        assert before <= result.args[1]["recorded_at"] <= datetime.now(UTC)
    repository.save_state_event.assert_not_awaited()


async def test_reads_delegate_materials_without_transforming(repository):
    from app.services.approval_service import ApprovalService

    service = ApprovalService(repository)
    assert await service.list_records(7) is repository.list_records.return_value
    assert (
        await service.list_versions_with_records(4)
        == repository.list_versions_with_records.return_value
    )
    repository.list_records.assert_awaited_once_with(7)
    repository.list_versions_with_records.assert_awaited_once_with(4)


async def test_version_list_derives_flags_without_mutating_repository_material(
    repository
):
    from app.services.approval_service import ApprovalService

    rows = [
        {
            "latest_bounce": N(recorded_at=2),
            "latest_review_checked_at": 1,
            "latest_state_event": N(
                from_state="review_checked", to_state="staff_checked"
            ),
        },
        {
            "latest_bounce": N(recorded_at=1),
            "latest_review_checked_at": 2,
            "latest_state_event": N(
                from_state="staff_checked", to_state="review_checked"
            ),
        },
        {
            "latest_bounce": None,
            "latest_review_checked_at": None,
            "latest_state_event": None,
        },
    ]
    repository.list_versions_with_records.return_value = rows
    result = await ApprovalService(repository).list_versions_with_records(4)
    assert [(row["bounced"], row["needs_recheck"]) for row in result] == [
        (True, True),
        (False, False),
        (False, False),
    ]
    assert all("bounced" not in row and "needs_recheck" not in row for row in rows)
    repository.list_versions_with_records.assert_awaited_once_with(4)
