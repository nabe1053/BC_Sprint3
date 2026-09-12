"""agent_runs / agent_run_steps（B層 規則・実行）。04-db.md 3.2。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Index,
    text,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class AgentRun(TimestampedBase):
    """AGENT-01 の1実行。N04・N06 の根拠。"""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index(
            "uq_agent_runs_running_case",
            "case_id",
            unique=True,
            postgresql_where=text("outcome = 'running'"),
        ),
        CheckConstraint(
            "stop_reason IS NULL OR stop_reason IN ('completed','failed','max_turns','inner_timeout','inactivity_timeout','outer_timeout','repeated_call','no_readable_document','validation_loop')",
            name="ck_agent_runs_stop_reason",
        ),
        CheckConstraint(
            "stage IN ('reading','extracting','self_checking','done')",
            name="ck_agent_runs_stage",
        ),
        CheckConstraint(
            "outcome IN ('running','success','failed','stopped')",
            name="ck_agent_runs_outcome",
        ),
    )

    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cases.id"), nullable=False, index=True
    )
    rule_set_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rule_sets.id"), nullable=False
    )
    # 1実行1版。起動に失敗して版を作れなかった場合のみ NULL。
    version_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("versions.id"), unique=True
    )
    # D05 未承認のため初版はダミー応答の識別子（例 mock-fixed-v2）。
    model: Mapped[str] = mapped_column(Text, nullable=False)
    impl_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="legacy-unrecorded"
    )
    limits: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_sec: Mapped[Decimal | None] = mapped_column(Numeric)
    turns: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stage: Mapped[str | None] = mapped_column(Text)
    stage_detail: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    stop_reason: Mapped[str | None] = mapped_column(Text)
    validation_result: Mapped[dict | None] = mapped_column(JSONB)


class AgentRunStep(TimestampedBase):
    """ツール呼び出しトレース。外部送信を行っていない証跡。N02・N04・AE06。"""

    __tablename__ = "agent_run_steps"
    __table_args__ = (
        Index("ix_agent_run_steps_document_locator", "document_id", "locator"),
        CheckConstraint(
            "result_status IN ('ok','error','unreadable')",
            name="ck_agent_run_steps_result_status",
        ),
        UniqueConstraint("agent_run_id", "seq", name="uq_agent_run_steps_run_seq"),
    )

    agent_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_runs.id"), nullable=False, index=True
    )
    parent_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_run_steps.id")
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    args_digest: Mapped[str] = mapped_column(Text, nullable=False)
    # 要約のみ。資料全文・認証情報は残さない（N02）。
    args_summary: Mapped[str | None] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("documents.id")
    )
    result_status: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Durable outbox event; JSONL is rebuilt only after this row commits.
    trace_event: Mapped[dict | None] = mapped_column(JSONB)
