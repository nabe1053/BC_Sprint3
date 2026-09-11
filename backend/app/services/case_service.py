"""CaseService（Business Logic層）。02-requirement.md FUNC-01 案件の作成。

Repository は interface 経由で呼ぶ（clean-architecture.md）。ORM/SQL は直接触らない。
UNIQUE 違反（sqlalchemy.exc.IntegrityError）の翻訳は Repository 側の責務とし、
Service は SQLAlchemy を import しない（中-D: services が ORM を直接参照しない）。
"""

from __future__ import annotations

from typing import Protocol

from app.models.cases import Case
from app.services.exceptions import DuplicateCaseCodeError, NotFoundError

# T-102 時点の進捗ステータス（05-api-ipo.md 0.4・5章）。版（versions）を作る手段が
# まだ無いため、①資料投入（'intake'）のみを返す。②③④の導出は versions の
# Repository ができる T-201 以降で追加する（orchestrator 指示・memory.md T-102 行）。
_PROGRESS_STATUS_INTAKE = "intake"


class CaseRepositoryProtocol(Protocol):
    async def get_by_code(self, case_code: str) -> Case | None:
        ...

    async def get_by_id(self, case_id: int) -> Case | None:
        ...

    async def list(self) -> list[Case]:
        ...

    async def create(self, case: Case) -> Case:
        ...


class CaseService:
    """案件の作成・重複チェックを担うビジネスロジック。"""

    def __init__(self, case_repository: CaseRepositoryProtocol) -> None:
        self.case_repository = case_repository

    async def create_case(
        self,
        case_code: str,
        customer_name: str | None,
        title: str | None,
    ) -> Case:
        """案件を作成する。

        case_code は入力契約上の必須項目（05-api-ipo.md に該当エラーコードが
        無いため新設しない。T-102 で Pydantic の必須・最小長バリデーションとして
        表現し、ここでは ValueError を投げる）。

        軽微3: 空文字・空白のみの case_code は、API 経由では前段の DTO
        （`StringConstraints(strip_whitespace=True, min_length=1)`）が 422 として
        弾く前提であり、この bare `ValueError` は API 経由では到達不能（この
        Service を直接呼ぶ経路——例えば将来のバッチ処理や別 API——でのみ
        到達しうるガード）。05-api-ipo.md 6章に対応するエラーコードが無いため、
        ここで新しいドメインエラーコードを作らずそのまま `ValueError` を送出する。
        """
        if not case_code or not case_code.strip():
            raise ValueError("case_code は必須です")

        existing = await self.case_repository.get_by_code(case_code)
        if existing is not None:
            raise DuplicateCaseCodeError(
                f"case_code '{case_code}' は既に使用されています",
                details={"caseCode": case_code},
            )

        # get_by_code をすり抜けた並行投入の競合（UNIQUE 違反）は Repository 側で
        # DuplicateCaseCodeError に翻訳済みのものがそのまま伝播する（中-D）。
        case = Case(case_code=case_code, customer_name=customer_name, title=title)
        return await self.case_repository.create(case)

    async def list_cases(self) -> list[tuple[Case, str]]:
        """案件一覧を進捗ステータス付きで返す（05-api-ipo.md #1）。

        T-102 時点では版が無いため、全件 'intake' を返す（②③④は T-201 以降）。
        """
        cases = await self.case_repository.list()
        return [(case, _PROGRESS_STATUS_INTAKE) for case in cases]

    async def get_case(self, case_id: int) -> Case:
        """案件詳細を取得する（05-api-ipo.md #3）。存在しなければ E_NOT_FOUND。"""
        case = await self.case_repository.get_by_id(case_id)
        if case is None:
            raise NotFoundError(
                f"case_id {case_id} は存在しません", details={"caseId": case_id}
            )
        return case
