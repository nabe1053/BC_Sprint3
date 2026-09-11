"""PDF 読取（FUNC-01・N03）の単体テスト。references/ の実データ + 実行時生成の異常系。

期待インタフェース:
    app.services.readers.pdf_reader.read_pdf(data: bytes) -> DocumentReadResult
    DocumentReadResult:
        read_status: "success" | "partial" | "unreadable" | "encrypted"
        page_count: int | None
        pages: list[PageReadResult]  # locator="p.N"（1始まり）, seq=N, text: str|None
        issues: list[ReadIssue]      # locator, issue_type, detail
"""

import io

from pypdf import PdfReader, PdfWriter

from app.services.readers.pdf_reader import get_pdf_page_count, read_pdf
from tests.fixtures.broken_files import (
    make_corrupt_pdf_bytes,
    make_encrypted_pdf_bytes,
    make_image_only_pdf_bytes,
)


def _make_zero_page_pdf_bytes() -> bytes:
    """0ページの PDF を生成する（中-C）。"""
    writer = PdfWriter()
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_all_image_only_pdf_bytes(num_pages: int) -> bytes:
    """全ページとも文字が取れない（画像のみ想定）の複数ページ PDF を生成する。"""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_text_pdf_extracts_text_per_page_with_p_locator(references_dir) -> None:
    """sample-03（2ページ・テキスト PDF）: 全ページのテキストが取れ、locator は p.1/p.2。"""
    data = (references_dir / "sample-03-nihonkai-gas-mitsumori-irai.pdf").read_bytes()

    result = read_pdf(data)

    assert result.read_status == "success"
    assert result.page_count == 2
    assert [p.locator for p in result.pages] == ["p.1", "p.2"]
    assert [p.seq for p in result.pages] == [1, 2]
    assert "見積" in result.pages[0].text
    assert "明細表" in result.pages[1].text
    assert result.issues == []


def test_text_pdf_sample09_three_pages(references_dir) -> None:
    """sample-09（3ページ・英文 PDF）: 全ページ読取成功・ページ数一致。"""
    data = (references_dir / "sample-09-northsea-petroleum-rfq.pdf").read_bytes()

    result = read_pdf(data)

    assert result.read_status == "success"
    assert result.page_count == 3
    assert [p.locator for p in result.pages] == ["p.1", "p.2", "p.3"]
    assert all(p.text for p in result.pages)


def test_image_only_single_page_pdf_is_unreadable_not_success() -> None:
    """1ページのみの PDF で、その唯一のページも文字が取得できない場合は
    unreadable（全ページ不可）。文書全体は成功と表示しない（N03。reviewer 指摘 中-1:
    1ページ＝全ページなので unreadable が正しく、partial ではない）。"""
    data = make_image_only_pdf_bytes()

    result = read_pdf(data)

    assert result.read_status == "unreadable"
    assert result.read_status != "success"
    assert result.pages[0].text is None
    assert len(result.issues) == 1
    assert result.issues[0].locator == "p.1"
    assert result.issues[0].issue_type == "unreadable_page"


def test_partial_when_some_pages_unreadable(references_dir) -> None:
    """一部ページのみ文字が取れない場合（1ページ画像のみ・1ページ文字あり）は
    partial（reviewer 指摘 中-1: 全ページ不可の unreadable と区別する）。"""
    text_data = (
        references_dir / "sample-03-nihonkai-gas-mitsumori-irai.pdf"
    ).read_bytes()
    image_only_data = make_image_only_pdf_bytes()

    text_reader = PdfReader(io.BytesIO(text_data))
    writer = PdfWriter()
    writer.add_page(text_reader.pages[0])
    image_only_reader = PdfReader(io.BytesIO(image_only_data))
    writer.add_page(image_only_reader.pages[0])
    buf = io.BytesIO()
    writer.write(buf)

    result = read_pdf(buf.getvalue())

    assert result.read_status == "partial"
    assert result.page_count == 2
    assert result.pages[0].text is not None
    assert result.pages[1].text is None


def test_all_pages_unreadable_is_unreadable_not_partial() -> None:
    """全ページで文字が取れない場合は unreadable（partial にしない。
    reviewer 指摘 中-1: X01・E_UNREADABLE の定義に合わせる）。"""
    data = _make_all_image_only_pdf_bytes(num_pages=2)

    result = read_pdf(data)

    assert result.read_status == "unreadable"
    assert result.read_status != "partial"


def test_encrypted_pdf_is_not_treated_as_readable() -> None:
    """暗号化 PDF は read_status=encrypted。ページを読めたことにしない。"""
    data = make_encrypted_pdf_bytes()

    result = read_pdf(data)

    assert result.read_status == "encrypted"
    assert result.pages == []


def test_corrupt_pdf_is_unreadable() -> None:
    """破損ファイルは read_status=unreadable。例外を投げずに結果として返す。"""
    data = make_corrupt_pdf_bytes()

    result = read_pdf(data)

    assert result.read_status == "unreadable"
    assert result.pages == []


def test_zero_page_pdf_is_unreadable_not_success() -> None:
    """0ページの PDF は読める単位が無いため unreadable（契約1・中-C）。"""
    data = _make_zero_page_pdf_bytes()

    result = read_pdf(data)

    assert result.read_status == "unreadable"
    assert result.page_count == 0
    assert result.pages == []
    assert len(result.issues) == 1
    assert result.issues[0].locator is None


def test_get_pdf_page_count_returns_count_without_extracting_text(
    references_dir,
) -> None:
    """m-5: ページ数のみを取得できる（テキスト抽出はしない軽量パス）。"""
    data = (references_dir / "sample-09-northsea-petroleum-rfq.pdf").read_bytes()

    assert get_pdf_page_count(data) == 3


def test_get_pdf_page_count_returns_none_for_encrypted_pdf() -> None:
    """暗号化 PDF はページ数を判定できないため None を返す。"""
    data = make_encrypted_pdf_bytes()

    assert get_pdf_page_count(data) is None


def test_get_pdf_page_count_returns_none_for_corrupt_pdf() -> None:
    """破損 PDF はページ数を判定できないため None を返す（例外を投げない）。"""
    data = make_corrupt_pdf_bytes()

    assert get_pdf_page_count(data) is None
