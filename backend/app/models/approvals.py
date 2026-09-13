"""Append-only approval records; cached state changes are event-backed."""
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.records import RecordedBase


class VersionStateEvent(RecordedBase):
    __tablename__ = "version_state_events"
    __table_args__ = (
        CheckConstraint(
            "to_state IN ('staff_checked','review_checked')",
            name="ck_version_state_events_to_state",
        ),
        CheckConstraint(
            "from_state IN ('draft','staff_checked','review_checked')",
            name="ck_version_state_events_from_state",
        ),
        CheckConstraint(
            "from_state <> to_state", name="ck_version_state_events_transition"
        ),
        CheckConstraint(
            "trim(recorded_by) <> ''", name="ck_version_state_events_recorder"
        ),
        Index("ix_version_state_events_version_id", "version_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("versions.id", name="fk_version_state_events_version"),
        nullable=False,
    )
    from_state: Mapped[str] = mapped_column(Text, nullable=False)
    to_state: Mapped[str] = mapped_column(Text, nullable=False)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False)


class Bounce(RecordedBase):
    __tablename__ = "bounces"
    __table_args__ = (
        CheckConstraint("trim(reason) <> ''", name="ck_bounces_reason"),
        CheckConstraint("trim(recorded_by) <> ''", name="ck_bounces_recorder"),
        Index("ix_bounces_version_id", "version_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("versions.id", name="fk_bounces_version"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class BounceComment(RecordedBase):
    __tablename__ = "bounce_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["version_id", "item_id"],
            ["items.version_id", "items.id"],
            name="fk_bounce_comments_version_item",
        ),
        CheckConstraint("trim(comment) <> ''", name="ck_bounce_comments_comment"),
        CheckConstraint("trim(recorded_by) <> ''", name="ck_bounce_comments_recorder"),
        Index("ix_bounce_comments_version_id", "version_id"),
        Index("ix_bounce_comments_item_id", "item_id"),
        Index("ix_bounce_comments_bounce_id", "bounce_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("versions.id", name="fk_bounce_comments_version"),
        nullable=False,
    )
    item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("items.id", name="fk_bounce_comments_item"),
        nullable=False,
    )
    bounce_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("bounces.id", name="fk_bounce_comments_bounce")
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)


class SendoffDecision(RecordedBase):
    __tablename__ = "sendoff_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('undecided','hold','approved')",
            name="ck_sendoff_decisions_decision",
        ),
        CheckConstraint(
            "decision='undecided' OR (reason IS NOT NULL AND trim(reason)<>'')",
            name="ck_sendoff_decisions_reason",
        ),
        CheckConstraint(
            "trim(recorded_by) <> ''", name="ck_sendoff_decisions_recorder"
        ),
        Index("ix_sendoff_decisions_version_id", "version_id"),
    )
    version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("versions.id", name="fk_sendoff_decisions_version"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
