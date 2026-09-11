"""versions（C層 成果物・版スコープ）。04-db.md 3.3。

Foundation ではハブテーブルの versions のみを作る。case_headers / items 等は
build-loop のエージェントスライスで積み上げる（04-db.md 5章の対応どおり AGENT-01 のみが書く）。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class Version(TimestampedBase):
    """生成版。記録はすべてこの版に属し、版をまたいで引き継がない（FUNC-10・X12）。"""

    __tablename__ = "versions"
    __table_args__ = (
        UniqueConstraint("case_id", "version_no", name="uq_versions_case_version_no"),
        CheckConstraint(
            "current_state IN ('draft','staff_checked','review_checked')",
            name="ck_versions_current_state",
        ),
        CheckConstraint(
            "finalized_at IS NOT NULL OR current_state='draft'",
            name="ck_versions_finalized_or_draft",
        ),
    )

    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cases.id"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    prev_version_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("versions.id")
    )
    rule_set_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rule_sets.id"), nullable=False
    )
    # version_state_events の最新値のキャッシュ（04-db.md 3.6）。
    current_state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="draft"
    )
    is_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
