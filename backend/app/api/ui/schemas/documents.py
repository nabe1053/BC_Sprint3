"""#5 資料投入の DTO（UI 専用。05-api-ipo.md 5章 #5）。

#10（原ファイル取得）はバイナリ応答（`FileResponse`）のため専用スキーマは無い。
"""

from typing import Literal

from app.api.schemas_base import CamelModel

# 04-db.md ck_documents_read_status（reviewer 指摘 中-4: Literal で表現する）。
ReadStatus = Literal["success", "partial", "unreadable", "encrypted", "unsupported"]


class DocumentIntakeResponse(CamelModel):
    """#5 応答。`storagePath` はサーバ内部パスのため含めない
    （reviewer 指摘 軽-6: UI にサーバ内部パスを露出しない）。"""

    document_id: int
    read_status: ReadStatus
