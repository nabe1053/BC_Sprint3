"""Export orchestration, failed-transaction cleanup and file preservation."""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, Mock
import pytest
from tests.fixtures.export_data import snapshot
from app.domain.export_types import sha256_hex
from app.repositories.document_storage import DocumentStorageGateway


@pytest.mark.parametrize("missing", [False, True])
async def test_version_evidence_delegates_once_and_preserves_order_or_error(missing):
    from app.services.export_service import ExportService
    from app.domain.draft_errors import DraftError

    rows = [N(item_id=None), N(item_id=9)]
    repo = N(list_evidence=AsyncMock(return_value=rows))
    if missing:
        repo.list_evidence.side_effect = DraftError("E_NOT_FOUND", "版なし")
    service = ExportService(repo, Mock())
    if missing:
        with pytest.raises(DraftError, match="版なし"):
            await service.list_evidence(7)
    else:
        assert await service.list_evidence(7) is rows
    repo.list_evidence.assert_awaited_once_with(7)


def setup_service(*, count=0, commit_error=False, with_sendoff=True):
    from app.services.export_service import ExportService

    data = snapshot()
    if not with_sendoff:
        data.records["sendoff_decisions"] = []
    order = []

    @asynccontextmanager
    async def lock(version_id):
        assert version_id == data.version.id
        order.append("lock")
        yield data.version
        order.append("commit")
        if commit_error:
            raise RuntimeError("commit")

    async def read(version_id):
        assert order == ["lock"]
        order.append("snapshot")
        return data

    async def save(values):
        assert order[-1] == "storage"
        order.append("insert")
        return N(id=5, **values)

    repo = N(
        lock_version=lock,
        snapshot=AsyncMock(side_effect=read),
        count_exports=AsyncMock(return_value=count),
        save_export=AsyncMock(side_effect=save),
    )

    def save_bytes(case_id, file_name, content):
        order.append("storage")
        return "saved.xlsx"

    storage = Mock(save=Mock(side_effect=save_bytes))
    return ExportService(repo, storage), repo, storage, data, order


@pytest.mark.parametrize("count,initial", [(0, True), (1, False)])
@pytest.mark.parametrize("sendoff", [False, True])
async def test_export_locks_stamps_saves_exact_bytes_and_metadata(
    count, initial, sendoff
):
    from openpyxl import load_workbook
    from io import BytesIO
    from app.domain.export_types import SHEET_NAMES, format_ts

    service, repo, storage, data, order = setup_service(
        count=count, with_sendoff=sendoff
    )
    before = datetime.now(UTC)
    result = await service.export(data.version.id)
    after = datetime.now(UTC)
    assert order == ["lock", "snapshot", "storage", "insert", "commit"]
    row = result.record
    assert before <= row.exported_at <= after
    assert row.is_initial is initial and row.state_at_export == "draft"
    assert row.sendoff_at_export == ("approved" if sendoff else "undecided")
    assert row.unresolved_at_export == 1
    assert row.content_hash == sha256_hex(result.content)
    storage.save.assert_called_once_with(data.case.id, row.file_name, result.content)
    assert row.file_name.endswith(".xlsx") and row.file_name.isascii()
    assert row.storage_path == "saved.xlsx"
    wb = load_workbook(BytesIO(result.content))
    values = {r[0].value: r[1].value for r in wb[SHEET_NAMES[0]]}
    assert values["出力日時"] == format_ts(row.exported_at)
    storage.remove.assert_not_called()


@pytest.mark.parametrize("commit_error", [False, True])
async def test_insert_or_commit_failure_removes_saved_file_and_reraises(commit_error):
    service, repo, storage, data, _ = setup_service(commit_error=commit_error)
    if not commit_error:
        repo.save_export.side_effect = RuntimeError("insert")
    with pytest.raises(RuntimeError, match="commit" if commit_error else "insert"):
        await service.export(data.version.id)
    storage.remove.assert_called_once_with("saved.xlsx")


async def test_cleanup_failure_does_not_mask_original_or_log_paths(caplog):
    service, repo, storage, data, _ = setup_service()
    repo.save_export.side_effect = RuntimeError("original")
    storage.remove.side_effect = OSError("private path synthetic")
    with pytest.raises(RuntimeError, match="original"):
        await service.export(data.version.id)
    assert "EXPORT_CLEANUP_FAILED" in caplog.text
    assert "private path" not in caplog.text


async def test_integrity_reads_real_saved_bytes_and_rejects_outside_root(tmp_path):
    from app.services.export_service import ExportService
    from tests.fixtures.export_data import export_values

    storage = DocumentStorageGateway(str(tmp_path / "exports"))
    path = storage.save(7, "x.xlsx", b"original")
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"original")
    row = N(
        id=1,
        **{
            **export_values(7),
            "storage_path": path,
            "content_hash": sha256_hex(b"original"),
        },
    )
    escaped = N(**{**vars(row), "id": 2, "storage_path": str(outside)})
    service = ExportService(
        N(list_exports=AsyncMock(return_value=[row, escaped])), storage
    )
    result = await service.list_exports(7)
    assert [r.integrity for r in result] == ["intact", "missing"]
    assert result[0].export_id == 1 and result[0].content_hash == row.content_hash
    Path(path).write_bytes(b"changed")
    assert (await service.list_exports(7))[0].integrity == "modified"
    Path(path).unlink()
    assert (await service.list_exports(7))[0].integrity == "missing"
