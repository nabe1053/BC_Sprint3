"""Human approval records: evaluate under the version lock and stamp once."""
from datetime import UTC, datetime

from app.domain.record_types import (
    BounceCommentInput,
    BounceInput,
    SendoffInput,
    StateEventInput,
)
from app.repositories.draft_repository import require
from app.services.record_service import parse_input
from app.services.version_state import (
    bounced,
    needs_recheck,
    bounce_reason,
    decide_transition,
    unresolved_count,
)


class ApprovalService:
    def __init__(self, repository):
        self.repository = repository

    async def transition(self, version_id, data):
        data = parse_input(StateEventInput, data)
        repo = self.repository
        async with repo.record(version_id) as version:
            rows = await repo.item_rows(version_id)
            transition = decide_transition(
                version.current_state,
                data.to_state,
                set(rows),
                await repo.matched_item_ids(version_id),
                await repo.coverage_confirmed(version_id),
                rows,
            )
            count = unresolved_count(await repo.list_questions_with_latest(version_id))
            return await repo.save_state_event(
                version,
                from_state=transition.from_state,
                to_state=transition.to_state,
                recorded_by=data.recorded_by,
                recorded_at=datetime.now(UTC),
                unresolved_count=count,
            )

    async def comment(self, version_id, data):
        data = parse_input(BounceCommentInput, data)
        repo = self.repository
        async with repo.record(version_id):
            await repo.item(version_id, data.item_id)
            return await repo.save_bounce_comment(
                version_id, {**data.model_dump(), "recorded_at": datetime.now(UTC)}
            )

    async def bounce(self, version_id, data):
        data = parse_input(BounceInput, data)
        repo = self.repository
        async with repo.record(version_id) as version:
            require(
                version.current_state != "draft",
                "E_STAFF_CHECK_INCOMPLETE",
                "担当者確認が必要です",
            )
            require(
                version.current_state == "staff_checked",
                "E_STATE_ORDER",
                "状態遷移の順序を確認してください",
            )
            comments = await repo.unlinked_bounce_comments(version_id)
            reason = bounce_reason(comments, await repo.item_rows(version_id))
            return await repo.save_bounce(
                version_id,
                {
                    "reason": reason,
                    "recorded_by": data.recorded_by,
                    "recorded_at": datetime.now(UTC),
                },
                comments,
            )

    async def decide_sendoff(self, version_id, data):
        data = parse_input(SendoffInput, data)
        async with self.repository.record(version_id):
            return await self.repository.save_sendoff(
                version_id, {**data.model_dump(), "recorded_at": datetime.now(UTC)}
            )

    async def list_records(self, version_id):
        return await self.repository.list_records(version_id)

    async def list_versions_with_records(self, case_id):
        rows = await self.repository.list_versions_with_records(case_id)
        return [
            {
                **row,
                "bounced": bounced(
                    row["latest_bounce"].recorded_at if row["latest_bounce"] else None,
                    row["latest_review_checked_at"],
                ),
                "needs_recheck": needs_recheck(row["latest_state_event"]),
            }
            for row in rows
        ]
