"""本文テキスト（.txt）読取の単体テスト。

期待インタフェース:
    app.services.readers.text_reader.read_text(data: bytes) -> DocumentReadResult
    - 1レコード。locator は "body:1"、seq=1
"""

from app.services.readers.text_reader import read_text


def test_text_body_is_single_record_with_body_locator() -> None:
    """本文テキストは locator 'body:1' で1レコードとして読める。"""
    data = "見積のご依頼です。数量は100本でお願いします。".encode("utf-8")

    result = read_text(data)

    assert result.read_status == "success"
    assert len(result.pages) == 1
    assert result.pages[0].locator == "body:1"
    assert result.pages[0].seq == 1
    assert "見積のご依頼です" in result.pages[0].text


def test_empty_text_body_is_not_success() -> None:
    """空の本文テキストは成功扱いにしない（明細0件の材料を成功と誤認させない）。
    軽微-6: 他3 reader（pdf/xlsx/eml）と同じ強さで unreadable + issue の
    存在をアサートする（`!= "success"` 止まりにしない）。"""
    result = read_text(b"")

    assert result.read_status == "unreadable"
    assert len(result.issues) >= 1
    assert result.issues[0].locator is None
    assert result.issues[0].detail


def test_cp932_encoded_body_is_read_via_fallback() -> None:
    """utf-8 でデコードできない場合は cp932 でフォールバックして読む
    （reviewer 指摘 中-4）。"""
    data = "見積のご依頼です。数量は100本でお願いします。".encode("cp932")

    result = read_text(data)

    assert result.read_status == "success"
    assert "見積のご依頼です" in result.pages[0].text


def test_undecodable_body_is_unreadable_with_issue() -> None:
    """utf-8・cp932 のどちらでもデコードできない場合は unreadable とし、
    document_issues 相当の理由（文字コードを判定できない）を残す（reviewer 指摘 中-4）。"""
    # 有効な utf-8 でも cp932 でもないバイト列
    data = b"\x81\x00\x81\x00"

    result = read_text(data)

    assert result.read_status == "unreadable"
    assert len(result.issues) == 1
    assert "文字コード" in result.issues[0].detail
