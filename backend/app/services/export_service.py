"""Export a version under its lock and preserve file integrity metadata."""
from dataclasses import fields
from datetime import UTC, datetime
import logging
from app.domain.export_types import (
    ExportResult,
    ExportWithIntegrity,
    export_file_name,
    sha256_hex,
)
from app.repositories.document_storage import DocumentStorageProtocol
from app.services.export_workbook import build_workbook
from app.services.version_state import unresolved_count

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, repository, storage: DocumentStorageProtocol):
        self.repository = repository
        self.storage = storage

    async def export(self, version_id):
        saved_path = None
        try:
            async with self.repository.lock_version(version_id):
                snapshot = await self.repository.snapshot(version_id)
                at = datetime.now(UTC)
                file_name = export_file_name(
                    snapshot.case.case_code,
                    snapshot.version.version_no,
                    snapshot.version.current_state,
                    at,
                    case_id=snapshot.case.id,
                )
                content = build_workbook(snapshot, at)
                digest = sha256_hex(content)
                initial = await self.repository.count_exports(version_id) == 0
                decisions = snapshot.records["sendoff_decisions"]
                latest = (
                    max(decisions, key=lambda row: (row.recorded_at, row.id))
                    if decisions
                    else None
                )
                saved_path = self.storage.save(snapshot.case.id, file_name, content)
                record = await self.repository.save_export(
                    dict(
                        version_id=version_id,
                        file_name=file_name,
                        storage_path=saved_path,
                        content_hash=digest,
                        exported_at=at,
                        state_at_export=snapshot.version.current_state,
                        sendoff_at_export=latest.decision if latest else "undecided",
                        unresolved_at_export=unresolved_count(snapshot.questions),
                        is_initial=initial,
                    )
                )
            return ExportResult(record, content)
        except BaseException:
            if saved_path is not None:
                try:
                    self.storage.remove(saved_path)
                except OSError:
                    logger.warning("EXPORT_CLEANUP_FAILED")
            raise

    async def list_exports(self, version_id):
        result = []
        for row in await self.repository.list_exports(version_id):
            path = self.storage.resolve_readable_path(row.storage_path)
            content = self.storage.read(path) if path is not None else None
            integrity = (
                "missing"
                if content is None
                else (
                    "intact" if sha256_hex(content) == row.content_hash else "modified"
                )
            )
            # Explicit DTO allowlist; paths are validated above before file access.
            values = {
                field.name: getattr(row, field.name)
                for field in fields(ExportWithIntegrity)
                if field.name not in {"export_id", "integrity"}
            }
            result.append(
                ExportWithIntegrity(export_id=row.id, integrity=integrity, **values)
            )
        return result

    async def list_evidence(self, version_id):
        return await self.repository.list_evidence(version_id)
