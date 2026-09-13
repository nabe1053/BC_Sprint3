"""Preserve metadata for exported workbooks."""
from alembic import op
import sqlalchemy as sa

revision = 'export_records'
down_revision = 'approval_records'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('exports',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('version_id', sa.BigInteger(), sa.ForeignKey('versions.id'), nullable=False),
        sa.Column('file_name', sa.Text(), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=False),
        sa.Column('exported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('state_at_export', sa.Text(), nullable=False),
        sa.Column('sendoff_at_export', sa.Text(), nullable=False),
        sa.Column('unresolved_at_export', sa.Integer(), nullable=False),
        sa.Column('is_initial', sa.Boolean(), nullable=False, server_default='false'),
        sa.CheckConstraint("state_at_export IN ('draft','staff_checked','review_checked')", name='ck_exports_state_at_export'),
        sa.CheckConstraint("sendoff_at_export IN ('undecided','hold','approved')", name='ck_exports_sendoff_at_export'),
        sa.CheckConstraint('unresolved_at_export >= 0', name='ck_exports_unresolved_nonneg'),
        sa.CheckConstraint("trim(file_name) <> ''", name='ck_exports_file_name'),
        sa.CheckConstraint("trim(storage_path) <> ''", name='ck_exports_storage_path'),
        sa.CheckConstraint("trim(content_hash) <> ''", name='ck_exports_content_hash'),
    )
    op.create_index('ix_exports_version_id', 'exports', ['version_id'])
    op.create_index('uq_exports_initial_per_version', 'exports', ['version_id'], unique=True, postgresql_where=sa.text('is_initial'))


def downgrade():
    op.drop_table('exports')
