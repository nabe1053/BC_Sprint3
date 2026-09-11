"""UI/AGENT 両方から使う共有 DTO（05-api-ipo.md 0.3 参照系 #4・#6・#7）。

これらの API は `/ui/*` と `/agent/*` の両方に同一ハンドラを登録する
（`app/api/common/endpoints_reference.py`）。スキーマも重複させず、ここに
1つだけ定義する。
"""

from datetime import datetime
from typing import Literal

from app.api.schemas_base import CamelModel

# reviewer 指摘 中-4: 04-db.md の CHECK 制約の語彙を Literal で表現する
# （フロントが5値/2値を網羅処理できるように型で示す）。

# ck_documents_kind
DocumentKind = Literal["pdf", "xlsx", "eml", "text", "unsupported"]

# ck_documents_read_status（資料全体の readStatus）
DocumentReadStatus = Literal[
    "success", "partial", "unreadable", "encrypted", "unsupported"
]

# ページ単位の readStatus（05-api-ipo.md 5章 #6。`_page_read_status` が
# 「読めた単位が1つ以上あれば success・無ければ unreadable」の2値だけを返す）。
PageReadStatus = Literal["success", "unreadable"]

# ck_email_parts_part_role
PartRole = Literal[
    "latest_body", "quoted_body", "postscript", "forward_note", "attachment"
]

# --------------------------------------------------------------------------
# #4 資料一覧
# --------------------------------------------------------------------------


class DocumentSummary(CamelModel):
    document_id: int
    file_name: str
    kind: DocumentKind
    read_status: DocumentReadStatus


class DocumentsListResponse(CamelModel):
    case_id: int
    case_name: str | None
    documents: list[DocumentSummary]


# --------------------------------------------------------------------------
# #6 本文取得
# --------------------------------------------------------------------------


class PageContent(CamelModel):
    locator: str
    text: str | None
    cells: dict | None = None
    read_status: PageReadStatus


class ContentResponse(CamelModel):
    pages: list[PageContent]


# --------------------------------------------------------------------------
# #7 メール構造
# --------------------------------------------------------------------------


class EmailPartResponse(CamelModel):
    part_role: PartRole
    seq: int
    sent_at: datetime | None
    from_addr: str | None
    subject: str | None
    body: str | None
    attachment_name: str | None


class EmailResponse(CamelModel):
    parts: list[EmailPartResponse]
