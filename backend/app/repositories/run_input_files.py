"""Read original size through the shared managed-storage validator."""
from pathlib import Path
from app.repositories.document_storage import DocumentStorageGateway


class RunInputFiles:
    def __init__(self, root):
        self.storage = DocumentStorageGateway(str(Path(root).resolve()))

    def size(self, document):
        try:
            resolved = self.storage.resolve_readable_path(document.storage_path)
            if resolved is None:
                return None
            path = Path(resolved)
            # Extra run policy: the file must belong to this case, not a sibling.
            case_root = Path(self.storage.storage_root) / str(document.case_id)
            if not path.is_relative_to(case_root):
                return None
            return path.stat().st_size
        except OSError:
            return None
