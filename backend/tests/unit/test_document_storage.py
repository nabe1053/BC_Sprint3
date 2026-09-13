"""DocumentStorageGateway（Data Access層）の単体テスト。

reviewer 指摘 重-1: 保存パス生成（uuid4）とファイル書き込みは
endpoints ではなくここ（Data Access層）が担う。05-api-ipo.md 0.4:
保存パス = {storage_root}/{caseId}/{uuid4}{拡張子}。元のファイル名を使わない。
"""

import os

from app.repositories.document_storage import DocumentStorageGateway


def test_save_writes_file_under_storage_root_case_dir_with_uuid_name(tmp_path) -> None:
    gateway = DocumentStorageGateway(storage_root=str(tmp_path))

    path = gateway.save(case_id=42, file_name="original-name.pdf", file_bytes=b"hello")

    assert path.startswith(str(tmp_path / "42"))
    assert path.endswith(".pdf")
    assert "original-name" not in os.path.basename(path)
    assert os.path.isfile(path)
    with open(path, "rb") as f:
        assert f.read() == b"hello"


def test_save_uses_default_storage_root_from_settings(monkeypatch, tmp_path) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))
    gateway = DocumentStorageGateway()

    path = gateway.save(case_id=1, file_name="a.txt", file_bytes=b"x")

    assert path.startswith(str(tmp_path / "1"))


def test_save_returns_distinct_paths_for_repeated_calls(tmp_path) -> None:
    gateway = DocumentStorageGateway(storage_root=str(tmp_path))

    path1 = gateway.save(case_id=1, file_name="a.txt", file_bytes=b"x")
    path2 = gateway.save(case_id=1, file_name="a.txt", file_bytes=b"y")

    assert path1 != path2


def test_export_root_and_validated_read_remove(monkeypatch, tmp_path):
    from pathlib import Path
    from uuid import UUID
    from app.core.config import settings

    monkeypatch.setattr(settings, "EXPORT_ROOT", str(tmp_path / "exports"))
    gateway = DocumentStorageGateway(settings.EXPORT_ROOT)
    path = gateway.save(7, "x.xlsx", b"workbook")
    assert Path(path).parent == tmp_path / "exports" / "7"
    assert UUID(Path(path).stem) and Path(path).suffix == ".xlsx"
    assert gateway.read(path) == b"workbook"
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"private")
    assert gateway.read(str(outside)) is None
    gateway.remove(str(outside))
    assert outside.exists()
    gateway.remove(path)
    assert gateway.read(path) is None
