"""CaseService（Business Logic層）。02-requirement.md FUNC-01 案件の作成。

Repository は interface 経由で呼ぶ（clean-architecture.md）。ORM/SQL は直接触らない。
UNIQUE 違反（sqlalchemy.exc.IntegrityError）の翻訳は Repository 側の責務とし、
Service は SQLAlchemy を import しない（中-D: services が ORM を直接参照しない）。
"""

from __future__ import annotations

from typing import Protocol

from app.models.cases import Case
from app.services.exceptions import DuplicateCaseCodeError


class CaseRepositoryProtocol(Protocol):
    async def get_by_code(self, case_code: str) -> Case | None:
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
        """
        if not case_code or not case_code.strip():
            raise ValueError("case_code は必須です")

        existing = await self.case_repository.get_by_code(case_code)
        if existing is not None:
            raise DuplicateCaseCodeError(
                f"case_code '{case_code}' は既に使用されています",
                details={"case_code": case_code},
            )

        # get_by_code をすり抜けた並行投入の競合（UNIQUE 違反）は Repository 側で
        # DuplicateCaseCodeError に翻訳済みのものがそのまま伝播する（中-D）。
        case = Case(case_code=case_code, customer_name=customer_name, title=title)
        return await self.case_repository.create(case)
