"""Converge existing databases on the document/locator scan index.

The historical artifacts revision was changed after octg_test had applied it.
Some databases therefore already have the index; preserve it when present.
"""
from alembic import op

revision = "add_run_step_locator_index"
down_revision = "t202_run_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_agent_run_steps_document_locator",
        "agent_run_steps",
        ["document_id", "locator"],
        schema="public",
        if_not_exists=True,
    )


def downgrade():
    # This revision may have adopted an existing index, so do not remove it.
    raise RuntimeError("Removing the scan index requires explicit approval.")
