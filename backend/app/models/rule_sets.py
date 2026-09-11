"""rule_sets（B層 規則・実行）。04-db.md 3.2。"""

from sqlalchemy import Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class RuleSet(TimestampedBase):
    """R01〜R08 と論理項目定義。エージェントは読取のみ。N04。"""

    __tablename__ = "rule_sets"

    rule_version: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # D03 未承認のため既定 false。換算値を保持する列は作らない（CLAUDE.md 決定事項4）。
    conversion_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    note: Mapped[str | None] = mapped_column(Text)
