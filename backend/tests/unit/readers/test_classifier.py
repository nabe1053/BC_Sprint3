"""形式判定（FUNC-01）。app.services.readers.classifier.detect_document_kind の単体テスト。

期待インタフェース:
    detect_document_kind(file_name: str) -> str
    戻り値は "pdf" / "xlsx" / "eml" / "text" / "unsupported" のいずれか。
"""

from app.services.readers.classifier import detect_document_kind


def test_pdf_extension_is_classified_as_pdf() -> None:
    """.pdf は pdf と判定される。"""
    assert detect_document_kind("sample-03-nihonkai-gas-mitsumori-irai.pdf") == "pdf"


def test_xlsx_extension_is_classified_as_xlsx() -> None:
    """.xlsx は xlsx と判定される。"""
    assert detect_document_kind("sample-01-tozai-sekiyu-order-list.xlsx") == "xlsx"


def test_eml_extension_is_classified_as_eml() -> None:
    """.eml は eml と判定される。"""
    assert detect_document_kind("sample-04-nanpo-sekiyu-hikiai-mail.eml") == "eml"


def test_txt_extension_is_classified_as_text() -> None:
    """.txt は text と判定される（本文テキスト投入）。"""
    assert detect_document_kind("inquiry-body.txt") == "text"


def test_unknown_extension_is_unsupported() -> None:
    """.pptx など未対応形式は unsupported と判定される（未対応として記録するため）。"""
    assert detect_document_kind("proposal.pptx") == "unsupported"


def test_no_extension_is_unsupported() -> None:
    """拡張子が無いファイル名も unsupported として扱う。"""
    assert detect_document_kind("no_extension_file") == "unsupported"


def test_extension_matching_is_case_insensitive() -> None:
    """拡張子の大文字小文字を区別しない（.PDF も pdf と判定）。"""
    assert detect_document_kind("SCAN.PDF") == "pdf"
