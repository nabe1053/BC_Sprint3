"""共通基底。

04-db.md 3章: 「すべてのテーブルに id bigserial PK と created_at timestamptz NOT NULL
DEFAULT now() を置く。D層には updated_at を置かない（追記型のため更新しない）」。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampedBase(Base):
    """id + created_at のみを持つ基底（D層・多くのA/B/C層で使う）。"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
