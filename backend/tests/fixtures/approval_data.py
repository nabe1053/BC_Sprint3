"""Synthetic approval records shared by API tests; no test-module imports."""
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace as N
from app.domain.record_types import CarryOver
from tests.fixtures.record_data import edit

AT = datetime(2026, 9, 14, tzinfo=UTC)


def approval_material():
    actor = dict(
        recorded_by="記録者",
        recorded_at=AT,
        created_at=AT,
        version_id=7,
        private_column="private",
    )
    state = N(
        id=11,
        from_state="review_checked",
        to_state="staff_checked",
        unresolved_count=2,
        elapsed_sec=Decimal("631.5"),
        **actor,
    )
    comment = N(id=21, item_id=9, bounce_id=31, comment="確認 <script>", **actor)
    bounce = N(id=31, reason="R1: 確認", **actor)
    sendoff = N(id=41, decision="approved", reason="可", **actor)
    confirmation = N(
        id=51, kind="coverage", item_id=None, undone_at=AT, undone_by="取消者", **actor
    )
    judgement = N(
        id=61,
        question_id=71,
        status="judged",
        resolution="unresolved",
        note=None,
        **actor,
    )
    version = N(
        id=7,
        version_no=1,
        current_state="staff_checked",
        finalized_at=AT,
        is_complete=True,
        created_at=AT,
    )
    records = dict(
        edits=[edit(id=81, item_id=9, reason="照合", recorded_by="人", undone_by=None)],
        confirmations=[confirmation],
        judgements=[judgement],
        state_events=[state],
        bounces=[dict(bounce=bounce, comments=[comment])],
        unlinked_comments=[N(**{**vars(comment), "id": 22, "bounce_id": None})],
        sendoff_decisions=[sendoff],
    )
    material = dict(
        version=version,
        carry_over=CarryOver(1, 1, 1, True, 1),
        unresolved_count=2,
        elapsed_sec=Decimal("631.5"),
        latest_state_event=state,
        latest_review_checked_at=AT,
        latest_bounce=bounce,
        latest_sendoff_decision=sendoff,
        bounced=True,
        needs_recheck=True,
    )
    return N(
        state=state,
        comment=comment,
        bounce=bounce,
        sendoff=sendoff,
        records=records,
        material=material,
    )
