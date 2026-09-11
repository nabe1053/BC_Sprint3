"""異常系テスト用ファイルを実行時に生成するヘルパー。

`references/`（sample-01〜10 の実データ）には書き込まない。異常系（画像のみ PDF・
暗号化 PDF・破損ファイル・未対応形式）は本モジュールでバイト列を都度生成する。
"""

from __future__ import annotations

import io

from pypdf import PdfWriter


def make_image_only_pdf_bytes() -> bytes:
    """テキストを一切含まない（画像のみを想定した）PDF を1ページ生成する。

    pypdf.extract_text() が空文字列を返すページを作ることが目的なので、実際に
    画像を貼り込む必要はない（「文字が取得できないページ」を再現できれば足りる）。
    """
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_encrypted_pdf_bytes(password: str = "s3cr3t") -> bytes:
    """パスワードで暗号化された PDF を生成する。"""
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_corrupt_pdf_bytes() -> bytes:
    """PDF として解釈できない壊れたバイト列。"""
    return b"%PDF-1.4\nnot a real pdf structure %%EOF-broken\x00\x01\x02"


def make_corrupt_xlsx_bytes() -> bytes:
    """.xlsx として解釈できない壊れたバイト列（zip 構造すら成していない）。"""
    return b"PK\x03\x04broken-not-a-real-zip-or-xlsx"


def make_encrypted_xlsx_bytes() -> bytes:
    """暗号化された .xlsx を模したバイト列（M-7）。

    パスワード保護された Office ファイルは OLE2 複合ドキュメント形式
    （CFBF）で保存され、先頭8バイトが固有の署名になる。実際に暗号化した
    ファイルを作らずとも、この署名を判定基準にできることを検証すれば足りる。
    """
    return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"dummy-encrypted-xlsx-body"


def make_unsupported_format_bytes() -> bytes:
    """未対応形式（.pptx）のダミーファイル。中身は解析されない想定。"""
    return b"dummy pptx content, not a real office document"
