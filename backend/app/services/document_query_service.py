"""DocumentQueryService（Business Logic層）。

05-api-ipo.md #4（資料一覧）・#6（本文取得）・#7（メール構造取得）・#8（検索）・
#9（読取不能記録）・#10（原ファイル取得のパス検証）を担う。

Repository は interface（Protocol）経由で呼ぶ（clean-architecture.md）。
ORM/SQL・ファイルパスの生成規則は Repository/Service の責務であり、endpoints
（Presentation 層）には業務判断を書かない（T-102 orchestrator 指示）。
"""

from __future__ import annotations

from typing import Protocol

from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.repositories.document_storage import (
    DocumentStorageGateway,
    DocumentStorageProtocol,
)
from app.services.exceptions import (
    DetailRequiredError,
    NotEmailError,
    NotFoundError,
    QueryRequiredError,
    UnreadableError,
)

# 全体として読取不能とみなす read_status（05-api-ipo.md 6章 `E_UNREADABLE`）。
_UNREADABLE_DOCUMENT_STATUSES = {"unreadable", "encrypted", "unsupported"}

_EXCERPT_WINDOW = 40


def _page_read_status(text: str | None, cells: dict | None) -> str:
    """ページ単位の readStatus（N03: 読めた単位が1つ以上あれば success）。

    reviewer 指摘 中-1: Presentation（endpoints）にあった業務判断を Service へ
    移した。軽-4: 空 dict `{}` は「読めた単位」に数えない（CV-001）。
    """
    has_text = text is not None
    has_cells = bool(cells)
    return "success" if (has_text or has_cells) else "unreadable"


class CaseRepositoryProtocol(Protocol):
    async def get_by_id(self, case_id: int) -> Case | None:
        ...


class DocumentRepositoryProtocol(Protocol):
    async def get_by_id(self, document_id: int) -> Document | None:
        ...

    async def list_by_case(self, case_id: int) -> list[Document]:
        ...

    async def list_intake_unreadable_locators(
        self, document_ids: list[int]
    ) -> dict[int, list[str]]:
        ...

    async def list_pages(
        self, document_id: int, from_seq: int | None = None, to_seq: int | None = None
    ) -> list[DocumentPage]:
        ...

    async def list_email_parts(self, document_id: int) -> list[EmailPart]:
        ...

    async def search_pages(
        self, case_id: int, query: str, limit: int
    ) -> list[tuple[Document, DocumentPage]]:
        ...

    async def add_issue(self, issue: DocumentIssue) -> DocumentIssue:
        ...


def _build_excerpt(text: str, query: str, window: int = _EXCERPT_WINDOW) -> str:
    """検索語の周辺を抜粋する（見つからない場合は先頭を返す）。"""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[: window * 2]
    start = max(0, idx - window)
    end = min(len(text), idx + len(query) + window)
    return text[start:end]


class DocumentQueryService:
    """資料の参照系（一覧・本文・メール構造・検索）と読取不能記録を担う。"""

    def __init__(
        self,
        document_repository: DocumentRepositoryProtocol,
        case_repository: CaseRepositoryProtocol,
        storage_gateway: DocumentStorageProtocol | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.case_repository = case_repository
        # 申し送り対応: STORAGE_ROOT の知識・パス検証（realpath）は
        # DocumentStorageGateway に集約する（DocumentIntakeService と同じ形）。
        self.storage_gateway = (
            storage_gateway if storage_gateway is not None else DocumentStorageGateway()
        )

    async def list_documents_for_case(
        self, case_id: int
    ) -> tuple[Case, list[tuple[Document, list[str]]]]:
        """#4: 案件配下の資料一覧（案件が無ければ E_NOT_FOUND）。

        各資料に受付時の読取不能範囲（locator 一覧）を添える。画面が「一部読取不能（p.2）」と
        対象範囲を示すための材料で、読めたと扱わない根拠になる（③SCR-02・AE04）。
        """
        case = await self._get_case(case_id)
        documents = await self.document_repository.list_by_case(case_id)
        unreadable = await self.document_repository.list_intake_unreadable_locators(
            [document.id for document in documents]
        )
        return case, [
            (document, unreadable.get(document.id, [])) for document in documents
        ]

    async def get_content(
        self, document_id: int, from_seq: int | None = None, to_seq: int | None = None
    ) -> list[tuple[DocumentPage, str]]:
        """#6: 本文取得。要求範囲が全体として読取不能なときのみ E_UNREADABLE（N03）。

        一部ページのみ読めない場合はエラーにせず、200 でページごとの
        readStatus を返す（読めたページまで落とさない）。

        ページ単位の readStatus の導出（reviewer 指摘 中-1）は本 Service が行い、
        `(page, read_status)` のタプル一覧として返す（endpoints には業務判断を
        書かせない）。
        """
        document = await self._get_document(document_id)
        pages = await self.document_repository.list_pages(document_id, from_seq, to_seq)

        statuses = [_page_read_status(p.text, p.cells) for p in pages]

        if pages:
            all_unreadable = all(status == "unreadable" for status in statuses)
            if all_unreadable:
                raise UnreadableError(
                    "要求範囲が全体として読取不能です",
                    details={"documentId": document_id},
                )
        elif document.read_status in _UNREADABLE_DOCUMENT_STATUSES:
            raise UnreadableError(
                "要求範囲が全体として読取不能です",
                details={"documentId": document_id},
            )

        return list(zip(pages, statuses, strict=True))

    async def get_email(self, document_id: int) -> list[EmailPart]:
        """#7: .eml の構造。.eml でない資料には E_NOT_EMAIL。"""
        document = await self._get_document(document_id)
        if document.kind != "eml":
            raise NotEmailError(
                "eml 資料ではありません", details={"documentId": document_id}
            )
        return await self.document_repository.list_email_parts(document_id)

    async def search(
        self, case_id: int, query: str, limit: int
    ) -> list[tuple[Document, DocumentPage, str]]:
        """#8: 案件内検索。検索語が空なら E_QUERY_REQUIRED。"""
        await self._get_case(case_id)
        if not query or not query.strip():
            raise QueryRequiredError("検索語が空です", details={"caseId": case_id})

        rows = await self.document_repository.search_pages(case_id, query, limit)
        return [
            (document, page, _build_excerpt(page.text or "", query))
            for document, page in rows
        ]

    async def report_issue(
        self, document_id: int, locator: str | None, issue_type: str, detail: str
    ) -> DocumentIssue:
        """#9: 読取不能・未走査範囲の記録。detail が空なら E_DETAIL_REQUIRED。"""
        document = await self._get_document(document_id)
        if not detail or not detail.strip():
            raise DetailRequiredError(
                "detail は必須です", details={"documentId": document_id}
            )
        issue = DocumentIssue(
            document_id=document.id,
            agent_run_id=None,
            locator=locator,
            issue_type=issue_type,
            detail=detail,
        )
        return await self.document_repository.add_issue(issue)

    async def get_file_path(self, document_id: int) -> str:
        """#10: 原ファイルの絶対パス。STORAGE_ROOT 配下でなければ E_NOT_FOUND
        （パストラバーサル防止・05-api-ipo.md 0.4）。

        検証（`realpath` + 前方一致）は `DocumentStorageGateway.
        resolve_readable_path()`（Data Access層）に委譲する（申し送り対応:
        STORAGE_ROOT の知識をこのゲートウェイ1箇所に集約する）。
        """
        document = await self._get_document(document_id)
        resolved = self.storage_gateway.resolve_readable_path(document.storage_path)
        if resolved is None:
            raise NotFoundError(
                "資料ファイルが見つかりません", details={"documentId": document_id}
            )
        return resolved

    async def _get_case(self, case_id: int) -> Case:
        case = await self.case_repository.get_by_id(case_id)
        if case is None:
            raise NotFoundError(
                f"case_id {case_id} は存在しません", details={"caseId": case_id}
            )
        return case

    async def _get_document(self, document_id: int) -> Document:
        document = await self.document_repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(
                f"document_id {document_id} は存在しません",
                details={"documentId": document_id},
            )
        return document
