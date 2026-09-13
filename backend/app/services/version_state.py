"""Pure state-transition rules and summaries; no clock, ORM or HTTP."""
from app.domain.draft_errors import DraftError
from app.domain.record_types import (
    Transition,
    unresolved_question_ids as unresolved_question_ids,
)


def decide_transition(
    current_state, to_state, item_ids, matched_item_ids, coverage_confirmed, rows
):
    if (current_state, to_state) not in {
        ("draft", "staff_checked"),
        ("staff_checked", "review_checked"),
    }:
        raise DraftError("E_STATE_ORDER", "状態遷移の順序を確認してください")
    if current_state == "draft":
        unmatched = sorted(item_ids - matched_item_ids)
        if unmatched:
            raise DraftError(
                "E_STAFF_CHECK_INCOMPLETE",
                "未照合の明細があります",
                {
                    "unmatchedItemIds": unmatched,
                    "unmatchedRowCodes": [rows[item_id] for item_id in unmatched],
                    "coverageRecorded": coverage_confirmed,
                },
            )
        if not coverage_confirmed:
            raise DraftError("E_COVERAGE_NOT_RECORDED", "網羅性確認を記録してください")
    return Transition(current_state, to_state)


def unresolved_count(rows):
    return len(unresolved_question_ids(rows))


def bounce_reason(comments, rows):
    if not comments:
        raise DraftError(
            "E_NO_BOUNCE_COMMENT", "差し戻す行にコメントを記録してください"
        )
    return "\n".join(
        f"{rows[row.item_id]}: {row.comment}"
        for row in sorted(comments, key=lambda row: (row.recorded_at, row.id))
    )


def bounced(latest_bounce_at, latest_review_checked_at):
    return latest_bounce_at is not None and (
        latest_review_checked_at is None or latest_review_checked_at < latest_bounce_at
    )


def needs_recheck(latest_event):
    """Only correction emits review→staff; draft→staff can precede the first review.

    With the permitted transition sequence, a latest review→staff event is exactly
    a staff event after the latest review. A later staff→review ends that condition.
    """
    return latest_event is not None and (
        latest_event.from_state == "review_checked"
        and latest_event.to_state == "staff_checked"
    )
