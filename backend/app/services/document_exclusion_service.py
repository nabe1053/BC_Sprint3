"""DocumentExclusionService（Business Logic層）。F-16・05-api-ipo #5a/#5b。

資料は物理削除しない。除外者（画面の入力値・AI は補完しない）と日時を D層に追記し、
以後の受付一覧・案の作成・エージェントの読取から外す（04-db `document_exclusions`）。
"""
from datetime import UTC, datetime

from app.domain.record_types import UndoInput
from app.services.exceptions import NotFoundError
from app.services.record_service import parse_input


class DocumentExclusionService:
    def __init__(self, document_repository, case_repository):
        self.documents = document_repository
        self.cases = case_repository

    async def exclude(self, case_id, document_id, data):
        recorder = parse_input(UndoInput, data).recorded_by
        return await self.documents.exclude(
            case_id, document_id, recorder, datetime.now(UTC)
        )

    async def list_exclusions(self, case_id):
        if await self.cases.get_by_id(case_id) is None:
            raise NotFoundError("案件が存在しません", details={"caseId": case_id})
        return await self.documents.list_exclusions(case_id)
