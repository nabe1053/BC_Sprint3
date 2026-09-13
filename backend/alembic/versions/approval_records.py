"""Create state events, bounce records and independent sendoff decisions."""
from alembic import op
import sqlalchemy as sa

revision = "approval_records"
down_revision = "human_records"
branch_labels = None
depends_on = None


def recorded_columns(table):
    return [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version_id", sa.BigInteger(), sa.ForeignKey("versions.id", name=f"fk_{table}_version"), nullable=False),
        sa.CheckConstraint("trim(recorded_by) <> ''", name=f"ck_{table}_recorder"),
    ]


def upgrade():
    op.create_table("version_state_events", *recorded_columns("version_state_events"),
        sa.Column("from_state", sa.Text(), nullable=False),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("to_state IN ('staff_checked','review_checked')", name="ck_version_state_events_to_state"),
        sa.CheckConstraint("from_state IN ('draft','staff_checked','review_checked')", name="ck_version_state_events_from_state"),
        sa.CheckConstraint("from_state <> to_state", name="ck_version_state_events_transition"),
    )
    op.create_table("bounces", *recorded_columns("bounces"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.CheckConstraint("trim(reason) <> ''", name="ck_bounces_reason"),
    )
    op.create_table("bounce_comments", *recorded_columns("bounce_comments"),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("items.id", name="fk_bounce_comments_item"), nullable=False),
        sa.Column("bounce_id", sa.BigInteger(), sa.ForeignKey("bounces.id", name="fk_bounce_comments_bounce")),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["version_id","item_id"], ["items.version_id","items.id"], name="fk_bounce_comments_version_item"),
        sa.CheckConstraint("trim(comment) <> ''", name="ck_bounce_comments_comment"),
    )
    op.create_table("sendoff_decisions", *recorded_columns("sendoff_decisions"),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.CheckConstraint("decision IN ('undecided','hold','approved')", name="ck_sendoff_decisions_decision"),
        sa.CheckConstraint("decision='undecided' OR (reason IS NOT NULL AND trim(reason)<>'')", name="ck_sendoff_decisions_reason"),
    )
    for table in ("version_state_events", "bounces", "bounce_comments", "sendoff_decisions"):
        op.create_index(f"ix_{table}_version_id", table, ["version_id"])
    op.create_index("ix_bounce_comments_item_id", "bounce_comments", ["item_id"])
    op.create_index("ix_bounce_comments_bounce_id", "bounce_comments", ["bounce_id"])


def downgrade():
    op.drop_table("sendoff_decisions")
    op.drop_table("bounce_comments")
    op.drop_table("bounces")
    op.drop_table("version_state_events")
