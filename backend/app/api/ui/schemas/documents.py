"""#5 資料投入の DTO（UI 専用。05-api-ipo.md 5章 #5）。

#10（原ファイル取得）はバイナリ応答（`FileResponse`）のため専用スキーマは無い。
"""

from datetime import datetime
from typing import Literal

from app.api.common.schemas.drafts import StrictRequest
from app.api.schemas_base import CamelModel
from app.domain.record_types import UndoInput

# 04-db.md ck_documents_read_status（reviewer 指摘 中-4: Literal で表現する）。
ReadStatus = Literal["success", "partial", "unreadable", "encrypted", "unsupported"]


class DocumentIntakeResponse(CamelModel):
    """#5 応答。`storagePath` はサーバ内部パスのため含めない
    （reviewer 指摘 軽-6: UI にサーバ内部パスを露出しない）。"""

    document_id: int
    read_status: ReadStatus


class DocumentExclusionRequest(UndoInput, StrictRequest):
    """#5a: 除外者名（必須・空白のみは E_RECORDER_REQUIRED）。F-16。"""


class DocumentExclusionRecord(CamelModel):
    """#5a 応答。"""

    document_id: int
    recorded_by: str
    recorded_at: datetime


class ExcludedDocument(DocumentExclusionRecord):
    """#5b の1件。"""

    file_name: str


class DocumentExclusionsResponse(CamelModel):
    exclusions: list[ExcludedDocument]
