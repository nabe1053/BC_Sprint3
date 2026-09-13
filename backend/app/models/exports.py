"""Append-only metadata for exported workbook snapshots."""
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import TimestampedBase


class Export(TimestampedBase):
    __tablename__ = "exports"
    __table_args__ = (
        CheckConstraint(
            "state_at_export IN ('draft','staff_checked','review_checked')",
            name="ck_exports_state_at_export",
        ),
        CheckConstraint(
            "sendoff_at_export IN ('undecided','hold','approved')",
            name="ck_exports_sendoff_at_export",
        ),
        CheckConstraint(
            "unresolved_at_export >= 0", name="ck_exports_unresolved_nonneg"
        ),
        CheckConstraint("trim(file_name) <> ''", name="ck_exports_file_name"),
        CheckConstraint("trim(storage_path) <> ''", name="ck_exports_storage_path"),
        CheckConstraint("trim(content_hash) <> ''", name="ck_exports_content_hash"),
        Index(
            "uq_exports_initial_per_version",
            "version_id",
            unique=True,
            postgresql_where=text("is_initial"),
        ),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("versions.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    exported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    state_at_export: Mapped[str] = mapped_column(Text, nullable=False)
    sendoff_at_export: Mapped[str] = mapped_column(Text, nullable=False)
    unresolved_at_export: Mapped[int] = mapped_column(Integer, nullable=False)
    is_initial: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
