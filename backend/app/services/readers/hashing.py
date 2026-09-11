"""資料内容のハッシュ計算。二重投入検知（X03）の材料。

同一内容のファイルが複数回投入されても記録上は両方保持する（N03・X03）。
ハッシュは重複の「検知」材料であって、投入自体をブロックしない。
"""

from __future__ import annotations

import hashlib


def compute_content_hash(data: bytes) -> str:
    """資料のバイト列から content_hash（sha256 の16進文字列）を計算する。"""
    return hashlib.sha256(data).hexdigest()
