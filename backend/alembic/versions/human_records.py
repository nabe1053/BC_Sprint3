"""Create append-only human records and active-confirmation constraints."""
from alembic import op
import sqlalchemy as sa

revision = "human_records"
down_revision = "add_run_step_locator_index"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_edits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True)),
        sa.Column("undone_by", sa.Text()),
        sa.Column("version_id", sa.BigInteger(), sa.ForeignKey('versions.id', name='fk_item_edits_version'), nullable=False),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey('items.id', name='fk_item_edits_item'), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("old_state", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("new_state", sa.Text()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['version_id', 'item_id'], ['items.version_id', 'items.id'], name='fk_item_edits_version_item'),
        sa.CheckConstraint("trim(reason) <> ''", name='ck_item_edits_reason'),
        sa.CheckConstraint("trim(recorded_by) <> ''", name='ck_item_edits_recorder'),
        sa.CheckConstraint('new_value IS NOT NULL OR new_state IS NOT NULL', name='ck_item_edits_value_or_state'),
        sa.CheckConstraint("new_state IN ('stated','tba','not_stated','not_applicable','numeric')", name='ck_item_edits_state'),
        sa.CheckConstraint("field IN ('kind','usage_note','od_value','od_unit','wall_value','wall_unit','weight_value','weight_unit','grade','connection','range_class','length_value','length_unit','qty_value','qty_unit','note')", name='ck_item_edits_field'),
        sa.CheckConstraint("undone_at IS NULL OR (undone_by IS NOT NULL AND trim(undone_by) <> '')", name='ck_item_edits_undo_recorder'),
    )
    op.create_index('ix_item_edits_version_id', 'item_edits', ['version_id'])
    op.create_index('ix_item_edits_item_id', 'item_edits', ['item_id'])
    op.create_table(
        "confirmations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True)),
        sa.Column("undone_by", sa.Text()),
        sa.Column("version_id", sa.BigInteger(), sa.ForeignKey('versions.id', name='fk_confirmations_version'), nullable=False),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey('items.id', name='fk_confirmations_item')),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['version_id', 'item_id'], ['items.version_id', 'items.id'], name='fk_confirmations_version_item'),
        sa.CheckConstraint("kind IN ('row_match','coverage')", name='ck_confirmations_kind'),
        sa.CheckConstraint("(kind='row_match' AND item_id IS NOT NULL) OR (kind='coverage' AND item_id IS NULL)", name='ck_confirmations_target'),
        sa.CheckConstraint("trim(recorded_by) <> ''", name='ck_confirmations_recorder'),
        sa.CheckConstraint("undone_at IS NULL OR (undone_by IS NOT NULL AND trim(undone_by) <> '')", name='ck_confirmations_undo_recorder'),
    )
    op.create_index('uq_confirmations_row_match_active', 'confirmations', ['version_id', 'item_id'], unique=True, postgresql_where=sa.text("kind='row_match' AND undone_at IS NULL"))
    op.create_index('uq_confirmations_coverage_active', 'confirmations', ['version_id'], unique=True, postgresql_where=sa.text("kind='coverage' AND undone_at IS NULL"))
    op.create_index('ix_confirmations_version_id', 'confirmations', ['version_id'])
    op.create_index('ix_confirmations_item_id', 'confirmations', ['item_id'])
    op.create_table(
        "question_judgements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("question_id", sa.BigInteger(), sa.ForeignKey('questions.id', name='fk_question_judgements_question'), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.CheckConstraint("status IN ('open','in_progress','judged')", name='ck_question_judgements_status'),
        sa.CheckConstraint("resolution IN ('unresolved','resolved')", name='ck_question_judgements_resolution'),
        sa.CheckConstraint("trim(recorded_by) <> ''", name='ck_question_judgements_recorder'),
    )
    op.create_index('ix_question_judgements_question_id', 'question_judgements', ['question_id'])


def downgrade():
    op.drop_table("question_judgements")
    op.drop_table("confirmations")
    op.drop_table("item_edits")
