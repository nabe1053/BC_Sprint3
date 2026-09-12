"""Business operations for T-201; HTTP and SQL remain outside this module."""
from dataclasses import asdict
from datetime import UTC, datetime

from pydantic.alias_generators import to_camel

from app.domain.draft_errors import DraftError
from app.domain.draft_types import (
    EvidenceInput,
    HeaderInput,
    InventoryInput,
    ItemInput,
    QuestionInput,
)
from app.services.draft_validation import validate_snapshot


class DraftService:
    def __init__(self, repository):
        self.repository = repository

    async def create_version(self, case_id, rule_set_id, prev_version_id=None):
        return await self.repository.create_version(
            case_id, rule_set_id, prev_version_id
        )

    async def save_header(self, version_id, payload):
        return await self.repository.save_header(
            version_id, HeaderInput.model_validate(payload)
        )

    async def add_items(self, version_id, rows):
        return await self.repository.add_items(
            version_id, [ItemInput.model_validate(row) for row in rows]
        )

    async def add_evidences(self, version_id, rows):
        return await self.repository.add_evidences(
            version_id, [EvidenceInput.model_validate(row) for row in rows]
        )

    async def add_questions(self, version_id, rows):
        return await self.repository.add_questions(
            version_id, [QuestionInput.model_validate(row) for row in rows]
        )

    async def add_inventory(self, version_id, rows):
        return await self.repository.add_inventory(
            version_id, [InventoryInput.model_validate(row) for row in rows]
        )

    async def validate(self, version_id):
        return validate_snapshot(await self.repository.snapshot(version_id))

    async def finalize(self, version_id):
        # Hold the same lock as all artifact writes until the validation and finalize commit.
        async with self.repository.edit(version_id) as version:
            snapshot = await self.repository.snapshot(version_id)
            if not snapshot.items:
                raise DraftError("E_NO_ITEMS", "明細0件の作成案は確定できません")
            result = validate_snapshot(snapshot)
            if result.violations or not snapshot.inventory:
                raise DraftError(
                    "E_VALIDATION_FAILED",
                    "完了条件を満たしていません",
                    {
                        "violations": [
                            {to_camel(key): value for key, value in asdict(v).items()}
                            for v in result.violations
                        ],
                        "inventoryRequired": not snapshot.inventory,
                    },
                )
            return await self.repository.complete(
                version, [], not snapshot.has_issues, datetime.now(UTC)
            )
