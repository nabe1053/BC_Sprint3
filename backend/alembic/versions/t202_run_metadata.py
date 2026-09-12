"""T-202: durable run configuration and single-current/single-running invariants."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "t202_run_metadata"
down_revision = "t201_artifacts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "agent_run_steps", sa.Column("trace_event", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "rule_sets",
        sa.Column(
            "is_current", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        "uq_rule_sets_current",
        "rule_sets",
        ["is_current"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "impl_version",
            sa.Text(),
            nullable=False,
            server_default="legacy-unrecorded",
        ),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "limits",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("agent_runs", "impl_version", server_default=None)
    op.alter_column("agent_runs", "limits", server_default=None)
    op.create_index(
        "uq_agent_runs_running_case",
        "agent_runs",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("outcome='running'"),
    )
    op.create_check_constraint(
        "ck_agent_runs_stop_reason",
        "agent_runs",
        "stop_reason IS NULL OR stop_reason IN ('completed','failed','max_turns','inner_timeout','inactivity_timeout','outer_timeout','repeated_call','no_readable_document','validation_loop')",
    )


def downgrade():
    raise RuntimeError("Destructive downgrade requires explicit user approval")
