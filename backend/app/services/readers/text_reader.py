"""本文テキスト（.txt）読取。1レコード・locator="body:1"。

この reader の「読めた単位」は本文全体（1ファイル = 1単位）。
page_count（軽微-5・決定2）: text は常に 1（Service 層が設定する。本 reader
自体は page_count を持たない `DocumentReadResult` を返す）。
"""

from __future__ import annotations

from app.services.readers.types import DocumentReadResult, PageReadResult, ReadIssue

_ENCODINGS = ("utf-8", "cp932")


def _decode_text(data: bytes) -> str | None:
    """utf-8 → cp932 の順にデコードを試す（中-4）。どちらも失敗したら None。"""
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def read_text(data: bytes) -> DocumentReadResult:
    """テキストのバイト列を1レコードとして読み取る。

    空の本文は成功扱いにしない（明細0件の材料を成功と誤認させない。N03）。
    utf-8 でデコードできない場合は cp932 でフォールバックする。どちらでも
    デコードできない場合は unreadable とし、理由を issues に残す（捏造しない）。
    """
    decoded = _decode_text(data)
    if decoded is None:
        return DocumentReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="文字コードを判定できない（utf-8・cp932 のいずれでもデコード不能）",
                )
            ],
        )

    text = decoded.strip()
    if not text:
        return DocumentReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="本文が空である",
                )
            ],
        )

    return DocumentReadResult(
        read_status="success",
        pages=[PageReadResult(locator="body:1", seq=1, text=text)],
    )
