"""資料原本の保存先パス生成とディスク書き込み・読取検証（Data Access層）。

05-api-ipo.md 0.4「保存パス = {STORAGE_ROOT}/{caseId}/{uuid4}{拡張子}」。
元のファイル名をパスに使わない。

reviewer 指摘 重-1: 保存パス生成・ファイル書き込みは Presentation
（endpoints）ではなく、この Data Access 層のゲートウェイが担う。
Business Logic（DocumentIntakeService）はここを Protocol 経由で呼ぶだけで、
生ファイル I/O を直接行わない（clean-architecture.md）。

申し送り対応（T-102 修正2回目）: `STORAGE_ROOT` の知識をこのゲートウェイ1箇所に
集約する。読取側の検証（`realpath` + 前方一致によるパストラバーサル対策）も
`resolve_readable_path()` としてここに置き、`DocumentQueryService` はそれを
呼ぶだけにする（検証ロジックの二重管理・弱体化を防ぐ）。
"""

from __future__ import annotations

import os
import uuid
from typing import Protocol

from app.core.config import settings


class DocumentStorageProtocol(Protocol):
    def save(self, case_id: int, file_name: str, file_bytes: bytes) -> str:
        ...

    def resolve_readable_path(self, storage_path: str) -> str | None:
        ...

    def read(self, path: str) -> bytes | None:
        ...

    def remove(self, path: str) -> None:
        ...


class DocumentStorageGateway:
    """`STORAGE_ROOT` 配下の原本の保存・読取検証を担う（Data Access層）。"""

    def __init__(self, storage_root: str | None = None) -> None:
        self.storage_root = (
            storage_root if storage_root is not None else settings.STORAGE_ROOT
        )

    def save(self, case_id: int, file_name: str, file_bytes: bytes) -> str:
        """保存先パスを決定し（元のファイル名を使わない）、原本を書き込む。

        パスは常に `{storage_root}/{case_id}/{uuid4}{拡張子}` の形になる。
        """
        ext = os.path.splitext(file_name or "")[1]
        storage_dir = os.path.join(self.storage_root, str(case_id))
        os.makedirs(storage_dir, exist_ok=True)
        storage_path = os.path.join(storage_dir, f"{uuid.uuid4()}{ext}")
        with open(storage_path, "wb") as f:
            f.write(file_bytes)
        return storage_path

    def resolve_readable_path(self, storage_path: str) -> str | None:
        """`storage_path` が `STORAGE_ROOT` 配下の実ファイルであることを検証する。

        パストラバーサル対策として `os.path.realpath`（`abspath` ではない）で
        symlink 等も解決したうえで前方一致を確認する（軽微2: symlink で
        `STORAGE_ROOT` の外に逃げるケースも弾く）。条件を満たさなければ
        `None` を返す（呼び出し側で `E_NOT_FOUND` に変換する）。
        """
        storage_root = os.path.realpath(self.storage_root)
        resolved = os.path.realpath(storage_path)
        is_within_root = resolved == storage_root or resolved.startswith(
            storage_root + os.sep
        )
        if not is_within_root or not os.path.isfile(resolved):
            return None
        return resolved

    def read(self, path: str) -> bytes | None:
        resolved = self.resolve_readable_path(path)
        if resolved is None:
            return None
        try:
            with open(resolved, "rb") as stream:
                return stream.read()
        except FileNotFoundError:
            return None

    def remove(self, path: str) -> None:
        resolved = self.resolve_readable_path(path)
        if resolved is not None:
            try:
                os.remove(resolved)
            except FileNotFoundError:
                pass
