"""content_hash の単体テスト。二重投入検知（X03）の材料。

期待インタフェース:
    app.services.readers.hashing.compute_content_hash(data: bytes) -> str
"""

from app.services.readers.hashing import compute_content_hash


def test_same_bytes_produce_same_hash() -> None:
    """同じ内容のファイルは同じ hash になる（二重投入の検知に使う）。"""
    data = b"identical file content for hashing"
    assert compute_content_hash(data) == compute_content_hash(data)


def test_different_bytes_produce_different_hash() -> None:
    """内容が異なれば hash も異なる。"""
    assert compute_content_hash(b"content A") != compute_content_hash(b"content B")


def test_hash_is_non_empty_string() -> None:
    """hash は空でない文字列（DB の text 列に保存できる形）。"""
    result = compute_content_hash(b"some bytes")
    assert isinstance(result, str)
    assert len(result) > 0
