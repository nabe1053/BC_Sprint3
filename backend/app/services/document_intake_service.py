"""DocumentIntakeService（Business Logic層）。02-requirement.md FUNC-01。

流れ: 上限判定（件数／サイズ／PDFページ数／xlsxシート数）→ 形式判定 → 抽出
→ read_status 決定 → repository への保存呼び出し（1回）。

上限判定に使う「案件内の既存資料件数」は本 Service が
`document_repository.count_by_case()` で取得する（呼び出し側に数え上げをさせない。
上限判定は業務ルールであり Business Logic の責務のため）。

`storage_path`（原本の保存先パス）は本 Service が `DocumentStorageGateway`
（Data Access層）を呼んで決定する。ファイル名を流用しない（reviewer 指摘 中-3）。
保存は上限判定（件数・サイズ・PDFページ数・xlsxシート数）をすべて通過した後にのみ
行う（reviewer 指摘 重-1・中-3: 413 でディスクに孤児ファイルを残さない）。

サイズ上限の判定述語 `assert_within_size_limit()` は呼び出し側（API層・
チャンク読取ループ）からも呼べるように公開している（reviewer 指摘 重-1:
サイズ上限の判定はここに集約し、endpoints には算術を書かせない）。

未対応形式（kind="unsupported"）は 05-api-ipo.md 5章 #5 のとおり、投入の事実を
先に保存してから `UnsupportedFormatError`（E_UNSUPPORTED_FORMAT）を送出する
（413 の `LimitExceededError` は記録を残さないのと対照的）。

m-4: 上限値は `settings` を直接参照せず、コンストラクタで注入できるようにする
（既定値は `settings` から取る）。テストで境界値を差し替えられるようにするため。
m-5: PDF のページ数上限は全ページ抽出後ではなく、ページ数だけを先に取得して
判定する（`get_pdf_page_count`。受付拒否は抽出前に行う）。
軽微-2: xlsx のシート数上限も同様に、全セル抽出前に `get_xlsx_sheet_count`
（軽量関数。セル抽出をしない）で判定する。

page_count（決定2・軽微-5）: 判定できない値は None のまま 0 等で埋めない。
    - pdf:  reader が返す値（encrypted 等で判定不能なら None）
    - xlsx: reader が返す値（開けなかった場合は None。シート数は
      `read_xlsx` の結果を使う。抽出前の上限判定には
      `get_xlsx_sheet_count` を別途使う）
    - text: 常に 1（ページの概念は無いが本文=1単位として扱う）
    - eml:  常に None（ページの概念が無い）
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from app.core.config import settings
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.repositories.document_storage import (
    DocumentStorageGateway,
    DocumentStorageProtocol,
)
from app.services.exceptions import LimitExceededError, UnsupportedFormatError
from app.services.readers.classifier import detect_document_kind
from app.services.readers.eml_reader import read_eml
from app.services.readers.hashing import compute_content_hash
from app.services.readers.pdf_reader import get_pdf_page_count, read_pdf
from app.services.readers.text_reader import read_text
from app.services.readers.types import PageReadResult, ReadIssue
from app.services.readers.xlsx_reader import get_xlsx_sheet_count, read_xlsx

_BYTES_PER_MB = 1024 * 1024


class DocumentRepositoryProtocol(Protocol):
    async def count_by_case(self, case_id: int) -> int:
        ...

    async def create_with_details(
        self,
        document: Document,
        pages: list[DocumentPage] | None = None,
        email_parts: list[EmailPart] | None = None,
        issues: list[DocumentIssue] | None = None,
    ) -> Document:
        ...


def _issues_to_models(issues: list[ReadIssue]) -> list[DocumentIssue]:
    return [
        DocumentIssue(
            agent_run_id=None,
            locator=issue.locator,
            issue_type=issue.issue_type,
            detail=issue.detail,
        )
        for issue in issues
    ]


def _pages_to_models(pages: list[PageReadResult]) -> list[DocumentPage]:
    return [
        DocumentPage(locator=p.locator, seq=p.seq, text=p.text, cells=p.cells)
        for p in pages
    ]


class DocumentIntakeService:
    """資料投入（上限判定 → 形式判定 → 抽出 → 保存）を担うビジネスロジック。

    上限値（D02: 件数・サイズ・PDFページ数・xlsxシート数）はコンストラクタで
    注入できる（未指定時は `settings` の既定値を使う。m-4: テストでグローバル
    設定を差し替えずに境界値を検証できるようにするため）。
    """

    def __init__(
        self,
        document_repository: DocumentRepositoryProtocol,
        storage_gateway: DocumentStorageProtocol | None = None,
        max_documents_per_case: int | None = None,
        max_file_size_mb: int | None = None,
        max_pdf_pages: int | None = None,
        max_xlsx_sheets: int | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.storage_gateway = (
            storage_gateway if storage_gateway is not None else DocumentStorageGateway()
        )
        self.max_documents_per_case = (
            max_documents_per_case
            if max_documents_per_case is not None
            else settings.MAX_DOCUMENTS_PER_CASE
        )
        self.max_file_size_mb = (
            max_file_size_mb
            if max_file_size_mb is not None
            else settings.MAX_FILE_SIZE_MB
        )
        self.max_pdf_pages = (
            max_pdf_pages if max_pdf_pages is not None else settings.MAX_PDF_PAGES
        )
        self.max_xlsx_sheets = (
            max_xlsx_sheets if max_xlsx_sheets is not None else settings.MAX_XLSX_SHEETS
        )

    def assert_within_size_limit(self, total_bytes: int) -> None:
        """アップロード中の累積バイト数がサイズ上限内かを判定する（reviewer 指摘 重-1）。

        endpoints のチャンク読取ループから呼ばれる想定（全部メモリに載せる前に
        打ち切れるよう、都度この述語を呼ぶ）。上限超過なら `LimitExceededError`
        （413）を送出する。算術（上限バイト数の計算）は endpoints に持たせない。
        """
        max_file_size_bytes = self.max_file_size_mb * _BYTES_PER_MB
        if total_bytes > max_file_size_bytes:
            raise LimitExceededError(
                "ファイルサイズの上限を超えています",
                details={
                    "limit": "file_size",
                    "max": self.max_file_size_mb,
                    "actual": round(total_bytes / _BYTES_PER_MB, 2),
                },
            )

    async def intake_document(
        self,
        case_id: int,
        file_name: str,
        file_bytes: bytes,
        received_at: datetime | None = None,
    ) -> Document:
        existing_count = await self.document_repository.count_by_case(case_id)
        if existing_count + 1 > self.max_documents_per_case:
            raise LimitExceededError(
                "案件あたりの資料件数の上限を超えています",
                details={
                    "limit": "document_count",
                    "max": self.max_documents_per_case,
                    "actual": existing_count + 1,
                },
            )

        self.assert_within_size_limit(len(file_bytes))

        kind = detect_document_kind(file_name)
        content_hash = compute_content_hash(file_bytes)

        pages: list[DocumentPage] = []
        email_parts: list[EmailPart] = []
        issues: list[DocumentIssue] = []
        page_count: int | None = None

        if kind == "pdf":
            # m-5: ページ数だけを先に取得して判定する（受付拒否は抽出前に行う）。
            page_count_hint = get_pdf_page_count(file_bytes)
            if page_count_hint is not None and page_count_hint > self.max_pdf_pages:
                raise LimitExceededError(
                    "PDF のページ数の上限を超えています",
                    details={
                        "limit": "pdf_pages",
                        "max": self.max_pdf_pages,
                        "actual": page_count_hint,
                    },
                )
            result = read_pdf(file_bytes)
            page_count = result.page_count
            read_status = result.read_status
            pages = _pages_to_models(result.pages)
            issues = _issues_to_models(result.issues)
        elif kind == "xlsx":
            # 軽微-2: シート数だけを先に取得して判定する（PDF と同様、
            # 受付拒否は全セル抽出前に行う）。
            sheet_count_hint = get_xlsx_sheet_count(file_bytes)
            if sheet_count_hint is not None and sheet_count_hint > self.max_xlsx_sheets:
                raise LimitExceededError(
                    "xlsx のシート数の上限を超えています",
                    details={
                        "limit": "xlsx_sheets",
                        "max": self.max_xlsx_sheets,
                        "actual": sheet_count_hint,
                    },
                )
            result = read_xlsx(file_bytes)
            # 中-2: page_count は reader が返す値をそのまま使う（開けなかった
            # 場合は None のまま。len(result.pages) で 0 埋めしない）。
            page_count = result.page_count
            read_status = result.read_status
            pages = _pages_to_models(result.pages)
            issues = _issues_to_models(result.issues)
        elif kind == "eml":
            eml_result = read_eml(file_bytes)
            # 決定2・軽微-5: eml にページの概念は無いため page_count は
            # None のまま（既定値を上書きしない）。
            read_status = eml_result.read_status
            email_parts = [
                EmailPart(
                    part_role=p.part_role,
                    seq=p.seq,
                    sent_at=p.sent_at,
                    from_addr=p.from_addr,
                    subject=p.subject,
                    body=p.body,
                    attachment_name=p.attachment_name,
                )
                for p in eml_result.parts
            ]
            issues = _issues_to_models(eml_result.issues)
        elif kind == "text":
            result = read_text(file_bytes)
            # 決定2・軽微-5: text の page_count は常に 1（ページの概念は無いが
            # 本文=1単位として扱う）。
            page_count = 1
            read_status = result.read_status
            pages = _pages_to_models(result.pages)
            issues = _issues_to_models(result.issues)
        else:
            # 未対応形式（拡張子が pdf/xlsx/eml/text のいずれでもない）。
            # 投入の事実は記録するが抽出は行わない（明細抽出の成功にしない）。
            read_status = "unsupported"
            issues = [
                DocumentIssue(
                    agent_run_id=None,
                    locator=None,
                    issue_type="unsupported",
                    detail=f"未対応形式のため抽出を行わない（file_name={file_name}）",
                )
            ]

        # 保存（ディスク書き込み）は上限判定（件数・サイズ・PDFページ数・xlsxシート数）
        # をすべて通過した後にだけ行う（reviewer 指摘 重-1・中-3: 413 時の孤児
        # ファイルを残さない）。
        storage_path = self.storage_gateway.save(case_id, file_name, file_bytes)

        document = Document(
            case_id=case_id,
            file_name=file_name,
            storage_path=storage_path,
            kind=kind,
            page_count=page_count,
            read_status=read_status,
            content_hash=content_hash,
            received_at=received_at if received_at is not None else datetime.now(UTC),
        )

        saved = await self.document_repository.create_with_details(
            document,
            pages=pages or None,
            email_parts=email_parts or None,
            issues=issues or None,
        )

        if kind == "unsupported":
            # 05-api-ipo.md 5章 #5: 投入の事実は記録したうえで 415 を返す
            # （413 の LimitExceededError とは異なり、記録は残す）。
            raise UnsupportedFormatError(
                "未対応の資料形式です",
                details={"documentId": saved.id},
            )

        return saved
