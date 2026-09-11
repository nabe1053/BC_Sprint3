"""読取結果の共通型（FUNC-01・FUNC-02）。

各 reader（pdf_reader / xlsx_reader / eml_reader / text_reader）はここで定義する
値オブジェクトを返す。DB モデル（`app.models.documents`）とは別物（readers は純粋
関数であり DB に触れない。clean-architecture.md）。Service 層がこれらを
`DocumentPage` / `EmailPart` / `DocumentIssue` に詰め替えて Repository に渡す。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReadIssue:
    """読取不能・未走査の範囲（04-db.md `document_issues`）。"""

    locator: str | None
    issue_type: str
    detail: str


@dataclass
class PageReadResult:
    """ページ／シート単位の抽出結果（04-db.md `document_pages`）。

    locator は PDF は "p.N"、xlsx はシート名、text は本文（.txt）は "body:1"。
    """

    locator: str
    seq: int
    text: str | None = None
    cells: dict[str, object] | None = None


@dataclass
class DocumentReadResult:
    """資料1件の読取結果（04-db.md `documents.read_status` 他）。"""

    read_status: str
    page_count: int | None = None
    pages: list[PageReadResult] = field(default_factory=list)
    issues: list[ReadIssue] = field(default_factory=list)


@dataclass
class EmailPartResult:
    """.eml のパート単位の抽出結果（04-db.md `email_parts`）。"""

    part_role: str
    seq: int
    sent_at: datetime | None = None
    from_addr: str | None = None
    subject: str | None = None
    body: str | None = None
    attachment_name: str | None = None


@dataclass
class EmailReadResult:
    """.eml 1件の読取結果。

    read_status: "success" | "partial"（本文は読めたが添付一覧等の一部単位が
    読めない） | "unreadable"（本文が読めない。空・非メール・文字コード不明等）。
    """

    read_status: str
    parts: list[EmailPartResult] = field(default_factory=list)
    issues: list[ReadIssue] = field(default_factory=list)
