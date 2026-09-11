"""依存注入。

認証は実装しない（CLAUDE.md 決定事項1）。get_db 以外の共通依存はここに追加する。
"""

from app.core.database import get_db

__all__ = ["get_db"]
