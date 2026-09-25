"""Record document exclusions without deleting documents (04-db document_exclusions)."""
from alembic import op
import sqlalchemy as sa

revision = "document_exclusions"
down_revision = "export_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "document_exclusions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("recorded_by", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", name="fk_document_exclusions_document"),
            nullable=False,
        ),
        sa.UniqueConstraint("document_id", name="uq_document_exclusions_document_id"),
        sa.CheckConstraint(
            "trim(recorded_by) <> ''", name="ck_document_exclusions_recorder"
        ),
    )


def downgrade():
    op.drop_table("document_exclusions")
