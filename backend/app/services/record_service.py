"""Human record policy and server timestamps; no ORM or HTTP dependencies."""
from datetime import UTC, datetime
from types import SimpleNamespace

from pydantic import ValidationError

from app.domain.draft_errors import DraftError
from app.domain.draft_types import ItemInput
from app.domain.record_types import (
    ConfirmationInput,
    ItemEditInput,
    JudgementInput,
    STATE_FIELDS,
    UndoInput,
)
from app.repositories.draft_repository import require
from app.services.item_current_values import apply_edits


def parse_input(schema, data):
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        code = exc.errors()[0]["type"]
        raise DraftError(
            code if code.startswith("E_") else "E_REQUEST_INVALID",
            "入力を確認してください",
        ) from exc


class RecordService:
    def __init__(self, repository):
        self.repository = repository

    async def edit(self, version_id, data):
        data = parse_input(ItemEditInput, data)
        repo = self.repository
        async with repo.record(version_id):
            item = await repo.item(version_id, data.item_id)
            current = apply_edits(
                item, await repo.edits(version_id, data.item_id)
            ).values
            state_field = STATE_FIELDS.get(data.field)
            state = data.new_state
            if state_field and state is None:
                state = "numeric" if state_field == "qty_state" else "stated"
            changes = [(data.field, data.new_value)]
            if state_field == "qty_state":
                number = (
                    data.new_value
                    if data.field == "qty_value"
                    else current.get("qty_value")
                )
                unit = data.qty_unit if data.field == "qty_value" else data.new_value
                if state != "numeric":
                    number, unit = None, None
                require(
                    state != "numeric" or unit,
                    "E_QTY_UNIT_REQUIRED",
                    "数量の単位が必要です",
                )
                changes = [("qty_value", number), ("qty_unit", unit)]
            at = datetime.now(UTC)
            rows = [
                dict(
                    item_id=data.item_id,
                    field=field,
                    old_value=None
                    if current.get(field) is None
                    else str(current[field]),
                    old_state=current.get(STATE_FIELDS.get(field)),
                    new_value=None if value is None else str(value),
                    new_state=state,
                    reason=data.reason,
                    recorded_by=data.recorded_by,
                    recorded_at=at,
                )
                for field, value in changes
            ]
            candidate = apply_edits(
                current,
                [
                    SimpleNamespace(**row, id=i, undone_at=None)
                    for i, row in enumerate(rows)
                ],
            ).values
            try:
                ItemInput.model_validate(
                    {
                        key: value
                        for key, value in candidate.items()
                        if key in ItemInput.model_fields
                    }
                )
            except ValidationError as exc:
                raise DraftError(
                    "E_STATE_VALUE_CONFLICT", "値と状態が一致しません"
                ) from exc
            return await repo.save_edits(version_id, rows)

    async def _undo(self, version_id, record_id, data, getter):
        async with self.repository.record(version_id):
            row = await getter(version_id, record_id)
            require(
                row.undone_at is None, "E_ALREADY_UNDONE", "すでに取り消されています"
            )
            actor = parse_input(UndoInput, data)
            return await self.repository.undo(row, datetime.now(UTC), actor.recorded_by)

    async def undo_edit(self, version_id, edit_id, data):
        return await self._undo(version_id, edit_id, data, self.repository.get_edit)

    async def confirm(self, version_id, data):
        data = parse_input(ConfirmationInput, data)
        repo = self.repository
        async with repo.record(version_id):
            if data.item_id is not None:
                await repo.item(version_id, data.item_id, code="E_TARGET_INVALID")
            require(
                await repo.active_confirmation(version_id, data.kind, data.item_id)
                is None,
                "E_ALREADY_CONFIRMED",
                "未取消の確認が存在します",
            )
            return await repo.save_confirmation(
                version_id, {**data.model_dump(), "recorded_at": datetime.now(UTC)}
            )

    async def undo_confirmation(self, version_id, confirmation_id, data):
        return await self._undo(
            version_id, confirmation_id, data, self.repository.get_confirmation
        )

    async def judge(self, version_id, question_id, data):
        data = parse_input(JudgementInput, data)
        async with self.repository.record(version_id):
            await self.repository.question(version_id, question_id)
            return await self.repository.save_judgement(
                question_id, {**data.model_dump(), "recorded_at": datetime.now(UTC)}
            )

    async def list_items_with_edits(self, version_id):
        return [
            apply_edits(item, edits)
            for item, edits in await self.repository.list_items_with_edits(version_id)
        ]

    async def list_questions_with_latest(self, version_id):
        return await self.repository.list_questions_with_latest(version_id)

    async def list_item_evidence(self, version_id, item_id):
        return await self.repository.list_item_evidence(version_id, item_id)

    async def summary(self, version_id):
        data = await self.repository.summary(version_id)
        items = [apply_edits(item, edits) for item, edits in data["items"]]
        active_edits = [
            edit for item in items for edit in item.history if edit.undone_at is None
        ]
        result = {
            "item_ids": {item.values["id"] for item in items},
            "matched_item_ids": {
                row.item_id for row in data["confirmations"] if row.kind == "row_match"
            },
            "edited_item_ids": {edit.item_id for edit in active_edits},
            "question_item_ids": {
                row["question"].item_id
                for row in data["questions"]
                if row["question"].item_id is not None
            },
            "tba_item_ids": {
                item.values["id"] for item in items if item.values["qty_state"] == "tba"
            },
            "unresolved_question_ids": {
                row["question"].id
                for row in data["questions"]
                if row["latest"] is None or row["latest"].resolution == "unresolved"
            },
            "choice_groups": {},
            "edit_count": len(active_edits),
            "coverage_confirmed": any(
                row.kind == "coverage" for row in data["confirmations"]
            ),
        }
        for item in items:
            if item.values.get("group_code"):
                result["choice_groups"].setdefault(
                    item.values["group_code"], set()
                ).add(item.values["id"])
        for count, ids in (
            ("item_count", "item_ids"),
            ("matched_count", "matched_item_ids"),
            ("edited_item_count", "edited_item_ids"),
            ("question_item_count", "question_item_ids"),
            ("tba_item_count", "tba_item_ids"),
            ("unresolved_count", "unresolved_question_ids"),
            ("choice_group_count", "choice_groups"),
        ):
            result[count] = len(result[ids])
        return result
