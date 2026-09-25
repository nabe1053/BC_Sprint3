"""Append-only human records (04-db §3.4); cancellation retains the actor."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class RecordedBase(TimestampedBase):
    __abstract__ = True
    recorded_by: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class UndoableRecord(RecordedBase):
    __abstract__ = True
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    undone_by: Mapped[str | None] = mapped_column(Text)


class ItemEdit(UndoableRecord):
    __tablename__ = "item_edits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["version_id", "item_id"],
            ["items.version_id", "items.id"],
            name="fk_item_edits_version_item",
        ),
        CheckConstraint("trim(reason) <> ''", name="ck_item_edits_reason"),
        CheckConstraint("trim(recorded_by) <> ''", name="ck_item_edits_recorder"),
        CheckConstraint(
            "new_value IS NOT NULL OR new_state IS NOT NULL",
            name="ck_item_edits_value_or_state",
        ),
        CheckConstraint(
            "new_state IN ('stated','tba','not_stated','not_applicable','numeric')",
            name="ck_item_edits_state",
        ),
        CheckConstraint(
            "field IN ('kind','usage_note','od_value','od_unit','wall_value','wall_unit','weight_value','weight_unit','grade','connection','range_class','length_value','length_unit','qty_value','qty_unit','note')",
            name="ck_item_edits_field",
        ),
        CheckConstraint(
            "undone_at IS NULL OR (undone_by IS NOT NULL AND trim(undone_by) <> '')",
            name="ck_item_edits_undo_recorder",
        ),
        Index("ix_item_edits_version_id", "version_id"),
        Index("ix_item_edits_item_id", "item_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("versions.id", name="fk_item_edits_version"),
        nullable=False,
    )
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("items.id", name="fk_item_edits_item"), nullable=False
    )
    field: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    old_state: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    new_state: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class Confirmation(UndoableRecord):
    __tablename__ = "confirmations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["version_id", "item_id"],
            ["items.version_id", "items.id"],
            name="fk_confirmations_version_item",
        ),
        CheckConstraint(
            "kind IN ('row_match','coverage')", name="ck_confirmations_kind"
        ),
        CheckConstraint(
            "(kind='row_match' AND item_id IS NOT NULL) OR (kind='coverage' AND item_id IS NULL)",
            name="ck_confirmations_target",
        ),
        CheckConstraint("trim(recorded_by) <> ''", name="ck_confirmations_recorder"),
        CheckConstraint(
            "undone_at IS NULL OR (undone_by IS NOT NULL AND trim(undone_by) <> '')",
            name="ck_confirmations_undo_recorder",
        ),
        Index(
            "uq_confirmations_row_match_active",
            "version_id",
            "item_id",
            unique=True,
            postgresql_where=text("kind='row_match' AND undone_at IS NULL"),
        ),
        Index(
            "uq_confirmations_coverage_active",
            "version_id",
            unique=True,
            postgresql_where=text("kind='coverage' AND undone_at IS NULL"),
        ),
        Index("ix_confirmations_version_id", "version_id"),
        Index("ix_confirmations_item_id", "item_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("versions.id", name="fk_confirmations_version"),
        nullable=False,
    )
    item_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("items.id", name="fk_confirmations_item")
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)


class QuestionJudgement(RecordedBase):
    __tablename__ = "question_judgements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','judged')",
            name="ck_question_judgements_status",
        ),
        CheckConstraint(
            "resolution IN ('unresolved','resolved')",
            name="ck_question_judgements_resolution",
        ),
        CheckConstraint(
            "trim(recorded_by) <> ''", name="ck_question_judgements_recorder"
        ),
        Index("ix_question_judgements_question_id", "question_id"),
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("questions.id", name="fk_question_judgements_question"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class DocumentExclusion(RecordedBase):
    """資料の除外（F-16・04-db `document_exclusions`）。資料・抽出結果は消さず追記だけ行う。"""

    __tablename__ = "document_exclusions"
    __table_args__ = (
        CheckConstraint(
            "trim(recorded_by) <> ''", name="ck_document_exclusions_recorder"
        ),
        UniqueConstraint("document_id", name="uq_document_exclusions_document_id"),
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", name="fk_document_exclusions_document"),
        nullable=False,
    )
