"""documents / document_pages / email_parts / document_issues（A層 入力）。04-db.md 3.1。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class Document(TimestampedBase):
    """投入資料1件。原本は改変しない。N01。"""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('pdf','xlsx','eml','text','unsupported')",
            name="ck_documents_kind",
        ),
        CheckConstraint(
            "read_status IN ('success','partial','unreadable','encrypted','unsupported')",
            name="ck_documents_read_status",
        ),
    )

    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cases.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    read_status: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DocumentPage(TimestampedBase):
    """ページ／シート単位の抽出テキスト。search_documents の対象。"""

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "locator", name="uq_document_pages_document_locator"
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id"), nullable=False, index=True
    )
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    cells: Mapped[dict | None] = mapped_column(JSONB)


class EmailPart(TimestampedBase):
    """.eml の構造保持。FUNC-02。"""

    __tablename__ = "email_parts"
    __table_args__ = (
        CheckConstraint(
            "part_role IN ('latest_body','quoted_body','postscript','forward_note','attachment')",
            name="ck_email_parts_part_role",
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id"), nullable=False, index=True
    )
    part_role: Mapped[str] = mapped_column(Text, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    from_addr: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    attachment_name: Mapped[str | None] = mapped_column(Text)


class DocumentIssue(TimestampedBase):
    """読取不能・未走査の範囲。N03。report_unreadable が書く。"""

    __tablename__ = "document_issues"
    __table_args__ = (
        CheckConstraint(
            "issue_type IN "
            "('unreadable_page','encrypted','unsupported','reference_missing','not_scanned')",
            name="ck_document_issues_issue_type",
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id"), nullable=False, index=True
    )
    agent_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_runs.id")
    )
    locator: Mapped[str | None] = mapped_column(Text)
    issue_type: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
