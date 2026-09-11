"""PDF 読取（FUNC-01・N03）。pypdf でテキスト抽出のみ行う（AD-004: OCR は範囲外）。

この reader の「読めた単位」はページ（1ページ = 1単位。document_pages の
1レコード）。

原本は改変しない（読取専用で開く。N01）。マクロ・外部リンクを実行しない
（pypdf のテキスト抽出は静的解析でありスクリプト実行を伴わない）。
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from app.services.readers.types import DocumentReadResult, PageReadResult, ReadIssue


def get_pdf_page_count(data: bytes) -> int | None:
    """PDF のページ数のみを取得する（テキスト抽出はしない）。

    上限判定（D02: PDF ページ数上限）に使う。m-5: ページ数だけを先に取得し、
    上限超過なら全ページのテキスト抽出をせずに受付拒否できるようにする。
    暗号化・破損等でページ数を判定できない場合は None を返す（例外を投げない）。
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            return None
        return len(reader.pages)
    except Exception:
        return None


def read_pdf(data: bytes) -> DocumentReadResult:
    """PDF のバイト列からページごとのテキストを抽出する。

    read_status:
        - "encrypted":  パスワード保護等で復号できない（ページを読めたことにしない）
        - "unreadable": PDF として解釈できない破損ファイル
        - "partial":    一部ページで文字が抽出できない（画像のみ等。N03: 成功と表示しない）
        - "success":    全ページで文字が抽出できた

    page_count（軽微-5・決定2）: PDF のページ数。判定できない場合（encrypted・
    ページ数取得前の破損）は None のまま（0 で埋めない）。
    """
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        return DocumentReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="PDF として解釈できない（破損ファイルの可能性）",
                )
            ],
        )

    if reader.is_encrypted:
        return DocumentReadResult(
            read_status="encrypted",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="encrypted",
                    detail="パスワード保護等により復号できない",
                )
            ],
        )

    try:
        num_pages = len(reader.pages)
    except Exception:
        return DocumentReadResult(
            read_status="unreadable",
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="PDF として解釈できない（破損ファイルの可能性）",
                )
            ],
        )

    if num_pages == 0:
        # 契約1: 読めた単位（ページ）が0個 → unreadable（中-C）。
        return DocumentReadResult(
            read_status="unreadable",
            page_count=0,
            issues=[
                ReadIssue(
                    locator=None,
                    issue_type="unreadable_page",
                    detail="PDF にページが1件も無い",
                )
            ],
        )

    pages: list[PageReadResult] = []
    issues: list[ReadIssue] = []
    unreadable_page_count = 0

    for i, page in enumerate(reader.pages, start=1):
        locator = f"p.{i}"
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""

        if text:
            pages.append(PageReadResult(locator=locator, seq=i, text=text))
        else:
            pages.append(PageReadResult(locator=locator, seq=i, text=None))
            issues.append(
                ReadIssue(
                    locator=locator,
                    issue_type="unreadable_page",
                    detail="ページから文字を抽出できない（画像のみ等の可能性）",
                )
            )
            unreadable_page_count += 1

    if unreadable_page_count == 0:
        read_status = "success"
    elif unreadable_page_count == num_pages:
        # 全ページで文字が取れない場合は unreadable（中-1: partial と区別する）
        read_status = "unreadable"
    else:
        read_status = "partial"

    return DocumentReadResult(
        read_status=read_status, page_count=num_pages, pages=pages, issues=issues
    )
