"""Deterministic approval rules independent of persistence and clocks."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace as N

import pytest
from app.domain.draft_errors import DraftError


def transition(
    current="draft",
    target="staff_checked",
    items=frozenset({3, 1}),
    matched=frozenset({3, 1}),
    coverage=True,
):
    from app.services.version_state import decide_transition

    return decide_transition(
        current, target, set(items), set(matched), coverage, {1: "R1", 3: "R3"}
    )


def test_complete_matches_and_coverage_allow_staff_check():
    from app.domain.record_types import Transition

    assert transition() == Transition("draft", "staff_checked")
    with pytest.raises(FrozenInstanceError):
        transition().to_state = "review_checked"


def test_review_check_requires_only_staff_state():
    assert (
        transition(
            "staff_checked", "review_checked", matched=set(), coverage=False
        ).to_state
        == "review_checked"
    )


@pytest.mark.parametrize(
    "current,target",
    [
        ("draft", "review_checked"),
        ("draft", "draft"),
        ("staff_checked", "staff_checked"),
        ("review_checked", "review_checked"),
        ("review_checked", "staff_checked"),
    ],
)
def test_out_of_order_or_repeated_transition(current, target):
    with pytest.raises(DraftError) as error:
        transition(current, target)
    assert error.value.code == "E_STATE_ORDER"


def test_unmatched_error_includes_ordered_ids_rows_and_missing_coverage():
    with pytest.raises(DraftError) as error:
        transition(matched=set(), coverage=False)
    assert error.value.code == "E_STAFF_CHECK_INCOMPLETE"
    assert error.value.details == {
        "unmatchedItemIds": [1, 3],
        "unmatchedRowCodes": ["R1", "R3"],
        "coverageRecorded": False,
    }


def test_coverage_is_checked_after_all_matches():
    with pytest.raises(DraftError) as error:
        transition(coverage=False)
    assert error.value.code == "E_COVERAGE_NOT_RECORDED"


def test_empty_inventory_has_no_unmatched_rows_and_still_requires_coverage():
    assert transition(items=set(), matched=set()).to_state == "staff_checked"
    with pytest.raises(DraftError) as error:
        transition(items=set(), matched=set(), coverage=False)
    assert error.value.code == "E_COVERAGE_NOT_RECORDED"


def test_unresolved_count_is_latest_resolution_not_judged_status():
    from app.services.version_state import unresolved_count, unresolved_question_ids

    rows = [
        {"question": N(id=1), "latest": None},
        {"question": N(id=2), "latest": N(status="judged", resolution="unresolved")},
        {"question": N(id=3), "latest": N(status="judged", resolution="resolved")},
    ]
    assert unresolved_question_ids(rows) == {1, 2}
    assert unresolved_count(rows) == 2
    assert unresolved_count([]) == 0


def test_bounce_reason_is_ordered_by_server_time_and_id():
    from app.services.version_state import bounce_reason

    comments = [
        N(id=3, item_id=1, recorded_at=2, comment="後"),
        N(id=2, item_id=3, recorded_at=1, comment="同時刻後"),
        N(id=1, item_id=1, recorded_at=1, comment="先"),
    ]
    assert bounce_reason(comments, {1: "R1", 3: "R3"}) == "R1: 先\nR3: 同時刻後\nR1: 後"
    assert [row.id for row in comments] == [3, 2, 1]
    with pytest.raises(DraftError) as error:
        bounce_reason([], {})
    assert error.value.code == "E_NO_BOUNCE_COMMENT"


@pytest.mark.parametrize(
    "bounce_at,review_at,expected",
    [
        (None, None, False),
        (None, 2, False),
        (2, None, True),
        (1, 2, False),
        (2, 1, True),
        (2, 2, False),
    ],
)
def test_bounced_compares_latest_bounce_and_last_review(bounce_at, review_at, expected):
    from app.services.version_state import bounced

    assert bounced(bounce_at, review_at) is expected


@pytest.mark.parametrize(
    "event,expected",
    [
        (None, False),
        (N(from_state="draft", to_state="staff_checked"), False),
        (N(from_state="staff_checked", to_state="review_checked"), False),
        (N(from_state="review_checked", to_state="staff_checked"), True),
    ],
)
def test_needs_recheck_requires_corrective_transition(event, expected):
    from app.services.version_state import needs_recheck

    assert needs_recheck(event) is expected
