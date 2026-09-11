"""資料の形式判定（FUNC-01）。拡張子のみで判定する純粋関数。"""

from __future__ import annotations

from pathlib import Path

_EXTENSION_TO_KIND: dict[str, str] = {
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".eml": "eml",
    ".txt": "text",
}


def detect_document_kind(file_name: str) -> str:
    """ファイル名の拡張子から資料の種類を判定する。

    戻り値: "pdf" / "xlsx" / "eml" / "text" / "unsupported"。

    04-db.md `documents.kind` CHECK 制約は pdf/xlsx/eml/text/unsupported を許す
    （軽微-F: 対応外の拡張子は kind="unsupported" を返す。呼び出し側で
    read_status も "unsupported" とし、抽出は行わない）。
    """
    suffix = Path(file_name).suffix.lower()
    return _EXTENSION_TO_KIND.get(suffix, "unsupported")
