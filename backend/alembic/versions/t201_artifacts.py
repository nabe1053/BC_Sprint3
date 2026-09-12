"""T-201: C-layer artifact storage.

Revision ID: t201_artifacts
Revises: 540727e02dcb
"""
from alembic import op
from sqlalchemy import (
    Column,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)

revision = "t201_artifacts"
down_revision = "540727e02dcb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_agent_run_steps_document_locator",
        "agent_run_steps",
        ["document_id", "locator"],
    )
    op.create_table(
        "case_headers",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("version_id", BigInteger, ForeignKey("versions.id"), nullable=False),
        Column("inquiry_no", Text, nullable=True),
        Column("customer_name", Text, nullable=True),
        Column("due_raw", Text, nullable=True),
        Column("place_raw", Text, nullable=True),
        Column("incoterms", Text, nullable=True),
        Column("quote_deadline_raw", Text, nullable=True),
        Column("inquiry_no_state", Text, nullable=False),
        Column("customer_name_state", Text, nullable=False),
        Column("due_state", Text, nullable=False),
        Column("place_state", Text, nullable=False),
        Column("incoterms_state", Text, nullable=False),
        Column("due_granularity", Text, nullable=True),
        Column("due_basis", Text, nullable=True),
        Column("quote_deadline_at", DateTime(timezone=True), nullable=True),
        Column("quote_deadline_tz_state", Text, nullable=False),
        UniqueConstraint("version_id", name="uq_case_headers_version_id"),
        CheckConstraint(
            "inquiry_no IS NULL OR length(trim(inquiry_no)) > 0",
            name="ck_case_headers_inquiry_no_nonblank",
        ),
        CheckConstraint(
            "customer_name IS NULL OR length(trim(customer_name)) > 0",
            name="ck_case_headers_customer_name_nonblank",
        ),
        CheckConstraint(
            "due_raw IS NULL OR length(trim(due_raw)) > 0",
            name="ck_case_headers_due_raw_nonblank",
        ),
        CheckConstraint(
            "place_raw IS NULL OR length(trim(place_raw)) > 0",
            name="ck_case_headers_place_raw_nonblank",
        ),
        CheckConstraint(
            "incoterms IS NULL OR length(trim(incoterms)) > 0",
            name="ck_case_headers_incoterms_nonblank",
        ),
        CheckConstraint(
            "quote_deadline_raw IS NULL OR length(trim(quote_deadline_raw)) > 0",
            name="ck_case_headers_quote_deadline_raw_nonblank",
        ),
        CheckConstraint(
            "inquiry_no_state IN ('stated','not_stated')",
            name="ck_case_headers_inquiry_no_state",
        ),
        CheckConstraint(
            "(inquiry_no_state='stated') = (inquiry_no IS NOT NULL)",
            name="ck_case_headers_inquiry_no_pair",
        ),
        CheckConstraint(
            "customer_name_state IN ('stated','not_stated')",
            name="ck_case_headers_customer_name_state",
        ),
        CheckConstraint(
            "(customer_name_state='stated') = (customer_name IS NOT NULL)",
            name="ck_case_headers_customer_name_pair",
        ),
        CheckConstraint(
            "due_state IN ('stated','tba','not_stated')",
            name="ck_case_headers_due_state",
        ),
        CheckConstraint(
            "(due_state='stated') = (due_raw IS NOT NULL)",
            name="ck_case_headers_due_pair",
        ),
        CheckConstraint(
            "place_state IN ('stated','not_stated','not_applicable')",
            name="ck_case_headers_place_state",
        ),
        CheckConstraint(
            "(place_state='stated') = (place_raw IS NOT NULL)",
            name="ck_case_headers_place_pair",
        ),
        CheckConstraint(
            "incoterms_state IN ('stated','not_stated','not_applicable')",
            name="ck_case_headers_incoterms_state",
        ),
        CheckConstraint(
            "(incoterms_state='stated') = (incoterms IS NOT NULL)",
            name="ck_case_headers_incoterms_pair",
        ),
        CheckConstraint(
            "due_granularity IN ('date','month','quarter','period','month_end','unknown')",
            name="ck_case_headers_due_granularity",
        ),
        CheckConstraint(
            "due_basis IN ('shipment','arrival','unknown')",
            name="ck_case_headers_due_basis",
        ),
        CheckConstraint(
            "quote_deadline_tz_state IN ('stated','missing')",
            name="ck_case_headers_quote_deadline_tz_state",
        ),
        CheckConstraint(
            "quote_deadline_at IS NULL OR (quote_deadline_tz_state='stated' AND quote_deadline_raw IS NOT NULL)",
            name="ck_case_headers_deadline_source",
        ),
    )
    op.create_table(
        "items",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("version_id", BigInteger, ForeignKey("versions.id"), nullable=False),
        Column("row_code", Text, nullable=False),
        Column("source_no", Text, nullable=False),
        Column("kind", Text, nullable=False),
        Column("kind_raw", Text, nullable=False),
        Column("grade_raw", Text, nullable=False),
        Column("qty_raw", Text, nullable=False),
        Column("seq", Integer, nullable=False),
        Column("usage_note", Text, nullable=True),
        Column("grade", Text, nullable=True),
        Column("connection", Text, nullable=True),
        Column("connection_raw", Text, nullable=True),
        Column("range_class", Text, nullable=True),
        Column("qty_reference_note", Text, nullable=True),
        Column("due_raw", Text, nullable=True),
        Column("place_raw", Text, nullable=True),
        Column("note", Text, nullable=True),
        Column("group_code", Text, nullable=True),
        Column("candidate_label", Text, nullable=True),
        Column("od_value", Numeric, nullable=True),
        Column("od_unit", Text, nullable=True),
        Column("od_raw", Text, nullable=True),
        Column("wall_value", Numeric, nullable=True),
        Column("wall_unit", Text, nullable=True),
        Column("wall_raw", Text, nullable=True),
        Column("weight_value", Numeric, nullable=True),
        Column("weight_unit", Text, nullable=True),
        Column("weight_raw", Text, nullable=True),
        Column("length_value", Numeric, nullable=True),
        Column("length_unit", Text, nullable=True),
        Column("length_raw", Text, nullable=True),
        Column("qty_value", Numeric, nullable=True),
        Column("qty_unit", Text, nullable=True),
        Column("od_state", Text, nullable=False),
        Column("wall_state", Text, nullable=False),
        Column("weight_state", Text, nullable=False),
        Column("grade_state", Text, nullable=False),
        Column("connection_state", Text, nullable=False),
        Column("due_state", Text, nullable=False),
        Column("place_state", Text, nullable=False),
        Column("length_state", Text, nullable=False),
        Column("qty_state", Text, nullable=False),
        Column("is_inherit_candidate", Boolean, server_default="false", nullable=False),
        UniqueConstraint("version_id", "id", name="uq_items_version_id_id"),
        UniqueConstraint("version_id", "row_code", name="uq_items_version_id_row_code"),
        CheckConstraint(
            "row_code IS NULL OR length(trim(row_code)) > 0",
            name="ck_items_row_code_nonblank",
        ),
        CheckConstraint(
            "source_no IS NULL OR length(trim(source_no)) > 0",
            name="ck_items_source_no_nonblank",
        ),
        CheckConstraint(
            "kind IS NULL OR length(trim(kind)) > 0", name="ck_items_kind_nonblank"
        ),
        CheckConstraint(
            "kind_raw IS NULL OR length(trim(kind_raw)) > 0",
            name="ck_items_kind_raw_nonblank",
        ),
        CheckConstraint(
            "grade_raw IS NULL OR length(trim(grade_raw)) > 0",
            name="ck_items_grade_raw_nonblank",
        ),
        CheckConstraint(
            "qty_raw IS NULL OR length(trim(qty_raw)) > 0",
            name="ck_items_qty_raw_nonblank",
        ),
        CheckConstraint("seq > 0", name="ck_items_seq"),
        CheckConstraint(
            "usage_note IS NULL OR length(trim(usage_note)) > 0",
            name="ck_items_usage_note_nonblank",
        ),
        CheckConstraint(
            "grade IS NULL OR length(trim(grade)) > 0", name="ck_items_grade_nonblank"
        ),
        CheckConstraint(
            "connection IS NULL OR length(trim(connection)) > 0",
            name="ck_items_connection_nonblank",
        ),
        CheckConstraint(
            "connection_raw IS NULL OR length(trim(connection_raw)) > 0",
            name="ck_items_connection_raw_nonblank",
        ),
        CheckConstraint(
            "range_class IS NULL OR length(trim(range_class)) > 0",
            name="ck_items_range_class_nonblank",
        ),
        CheckConstraint(
            "qty_reference_note IS NULL OR length(trim(qty_reference_note)) > 0",
            name="ck_items_qty_reference_note_nonblank",
        ),
        CheckConstraint(
            "due_raw IS NULL OR length(trim(due_raw)) > 0",
            name="ck_items_due_raw_nonblank",
        ),
        CheckConstraint(
            "place_raw IS NULL OR length(trim(place_raw)) > 0",
            name="ck_items_place_raw_nonblank",
        ),
        CheckConstraint(
            "note IS NULL OR length(trim(note)) > 0", name="ck_items_note_nonblank"
        ),
        CheckConstraint(
            "group_code IS NULL OR length(trim(group_code)) > 0",
            name="ck_items_group_code_nonblank",
        ),
        CheckConstraint(
            "candidate_label IS NULL OR length(trim(candidate_label)) > 0",
            name="ck_items_candidate_label_nonblank",
        ),
        CheckConstraint(
            "od_unit IS NULL OR length(trim(od_unit)) > 0",
            name="ck_items_od_unit_nonblank",
        ),
        CheckConstraint(
            "od_raw IS NULL OR length(trim(od_raw)) > 0",
            name="ck_items_od_raw_nonblank",
        ),
        CheckConstraint(
            "od_value IS NULL OR od_unit IS NOT NULL", name="ck_items_od_unit"
        ),
        CheckConstraint(
            "wall_unit IS NULL OR length(trim(wall_unit)) > 0",
            name="ck_items_wall_unit_nonblank",
        ),
        CheckConstraint(
            "wall_raw IS NULL OR length(trim(wall_raw)) > 0",
            name="ck_items_wall_raw_nonblank",
        ),
        CheckConstraint(
            "wall_value IS NULL OR wall_unit IS NOT NULL", name="ck_items_wall_unit"
        ),
        CheckConstraint(
            "weight_unit IS NULL OR length(trim(weight_unit)) > 0",
            name="ck_items_weight_unit_nonblank",
        ),
        CheckConstraint(
            "weight_raw IS NULL OR length(trim(weight_raw)) > 0",
            name="ck_items_weight_raw_nonblank",
        ),
        CheckConstraint(
            "weight_value IS NULL OR weight_unit IS NOT NULL",
            name="ck_items_weight_unit",
        ),
        CheckConstraint(
            "length_unit IS NULL OR length(trim(length_unit)) > 0",
            name="ck_items_length_unit_nonblank",
        ),
        CheckConstraint(
            "length_raw IS NULL OR length(trim(length_raw)) > 0",
            name="ck_items_length_raw_nonblank",
        ),
        CheckConstraint(
            "length_value IS NULL OR length_unit IS NOT NULL",
            name="ck_items_length_unit",
        ),
        CheckConstraint(
            "qty_unit IS NULL OR length(trim(qty_unit)) > 0",
            name="ck_items_qty_unit_nonblank",
        ),
        CheckConstraint(
            "qty_value IS NULL OR qty_unit IS NOT NULL", name="ck_items_qty_unit"
        ),
        CheckConstraint(
            "od_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_od_state",
        ),
        CheckConstraint(
            "(od_state='stated') = (od_value IS NOT NULL)", name="ck_items_od_pair"
        ),
        CheckConstraint(
            "wall_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_wall_state",
        ),
        CheckConstraint(
            "(wall_state='stated') = (wall_value IS NOT NULL)",
            name="ck_items_wall_pair",
        ),
        CheckConstraint(
            "weight_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_weight_state",
        ),
        CheckConstraint(
            "(weight_state='stated') = (weight_value IS NOT NULL)",
            name="ck_items_weight_pair",
        ),
        CheckConstraint(
            "grade_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_grade_state",
        ),
        CheckConstraint(
            "(grade_state='stated') = (grade IS NOT NULL)", name="ck_items_grade_pair"
        ),
        CheckConstraint(
            "connection_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_connection_state",
        ),
        CheckConstraint(
            "(connection_state='stated') = (connection IS NOT NULL)",
            name="ck_items_connection_pair",
        ),
        CheckConstraint(
            "due_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_due_state",
        ),
        CheckConstraint(
            "(due_state='stated') = (due_raw IS NOT NULL)", name="ck_items_due_pair"
        ),
        CheckConstraint(
            "place_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_place_state",
        ),
        CheckConstraint(
            "(place_state='stated') = (place_raw IS NOT NULL)",
            name="ck_items_place_pair",
        ),
        CheckConstraint(
            "length_state IN ('stated','tba','not_stated','not_applicable')",
            name="ck_items_length_state",
        ),
        CheckConstraint(
            "(length_state='stated') = (range_class IS NOT NULL OR length_value IS NOT NULL)",
            name="ck_items_length_pair",
        ),
        CheckConstraint(
            "qty_state IN ('numeric','tba','not_stated','not_applicable')",
            name="ck_items_qty_state",
        ),
        CheckConstraint(
            "(qty_state='numeric') = (qty_value IS NOT NULL)", name="ck_items_qty_pair"
        ),
        CheckConstraint(
            "candidate_label IS NULL OR group_code IS NOT NULL",
            name="ck_items_candidate_group",
        ),
    )
    op.create_index("ix_items_version_seq", "items", ["version_id", "seq"])
    op.create_table(
        "item_ends",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("item_id", BigInteger, ForeignKey("items.id"), nullable=False),
        Column("side", Text, nullable=False),
        Column("od_value", Numeric, nullable=True),
        Column("od_unit", Text, nullable=True),
        Column("od_raw", Text, nullable=True),
        Column("connection", Text, nullable=True),
        Column("thread_end", Text, nullable=True),
        CheckConstraint("side IN ('end_a','end_b')", name="ck_item_ends_side"),
        UniqueConstraint("item_id", "side", name="uq_item_ends_item_id_side"),
        CheckConstraint(
            "od_unit IS NULL OR length(trim(od_unit)) > 0",
            name="ck_item_ends_od_unit_nonblank",
        ),
        CheckConstraint(
            "od_raw IS NULL OR length(trim(od_raw)) > 0",
            name="ck_item_ends_od_raw_nonblank",
        ),
        CheckConstraint(
            "connection IS NULL OR length(trim(connection)) > 0",
            name="ck_item_ends_connection_nonblank",
        ),
        CheckConstraint("thread_end IN ('BOX','PIN')", name="ck_item_ends_thread_end"),
        CheckConstraint(
            "od_value IS NULL OR od_unit IS NOT NULL", name="ck_item_ends_od_unit"
        ),
    )
    op.create_table(
        "evidences",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("version_id", BigInteger, ForeignKey("versions.id"), nullable=False),
        Column("item_id", BigInteger, ForeignKey("items.id"), nullable=True),
        Column("field", Text, nullable=False),
        Column("raw_value", Text, nullable=False),
        Column("adopted_value", Text, nullable=False),
        Column("locator", Text, nullable=False),
        Column("quote", Text, nullable=False),
        Column("document_id", BigInteger, ForeignKey("documents.id"), nullable=False),
        Column("applied_condition", Text, nullable=True),
        Column("conversion_note", Text, nullable=True),
        Column("change_reason", Text, nullable=True),
        Column("prior_value", Text, nullable=True),
        ForeignKeyConstraint(
            ["version_id", "item_id"],
            ["items.version_id", "items.id"],
            name="fk_evidences_version_item",
        ),
        CheckConstraint(
            "field IS NULL OR length(trim(field)) > 0",
            name="ck_evidences_field_nonblank",
        ),
        CheckConstraint(
            "raw_value IS NULL OR length(trim(raw_value)) > 0",
            name="ck_evidences_raw_value_nonblank",
        ),
        CheckConstraint(
            "adopted_value IS NULL OR length(trim(adopted_value)) > 0",
            name="ck_evidences_adopted_value_nonblank",
        ),
        CheckConstraint(
            "locator IS NULL OR length(trim(locator)) > 0",
            name="ck_evidences_locator_nonblank",
        ),
        CheckConstraint(
            "quote IS NULL OR length(trim(quote)) > 0",
            name="ck_evidences_quote_nonblank",
        ),
        CheckConstraint(
            "applied_condition IS NULL OR length(trim(applied_condition)) > 0",
            name="ck_evidences_applied_condition_nonblank",
        ),
        CheckConstraint(
            "conversion_note IS NULL OR length(trim(conversion_note)) > 0",
            name="ck_evidences_conversion_note_nonblank",
        ),
        CheckConstraint(
            "change_reason IS NULL OR length(trim(change_reason)) > 0",
            name="ck_evidences_change_reason_nonblank",
        ),
        CheckConstraint(
            "prior_value IS NULL OR length(trim(prior_value)) > 0",
            name="ck_evidences_prior_value_nonblank",
        ),
        CheckConstraint(
            "conversion_note IS NULL OR conversion_note='換算：未実施（不足条件）'",
            name="ck_evidences_conversion_disabled",
        ),
    )
    op.create_index(
        "uq_evidences_item_field",
        "evidences",
        ["item_id", "field"],
        unique=True,
        postgresql_where=text("item_id IS NOT NULL"),
    )
    op.create_index(
        "uq_evidences_header_field",
        "evidences",
        ["version_id", "field"],
        unique=True,
        postgresql_where=text("item_id IS NULL"),
    )
    op.create_index("ix_evidences_version_id", "evidences", ["version_id"])
    op.create_table(
        "questions",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("version_id", BigInteger, ForeignKey("versions.id"), nullable=False),
        Column("item_id", BigInteger, ForeignKey("items.id"), nullable=True),
        Column("question_code", Text, nullable=False),
        Column("target_field", Text, nullable=False),
        Column("reason", Text, nullable=False),
        Column("candidates", Text, nullable=True),
        Column("category", Text, nullable=True),
        ForeignKeyConstraint(
            ["version_id", "item_id"],
            ["items.version_id", "items.id"],
            name="fk_questions_version_item",
        ),
        CheckConstraint(
            "question_code IS NULL OR length(trim(question_code)) > 0",
            name="ck_questions_question_code_nonblank",
        ),
        CheckConstraint(
            "target_field IS NULL OR length(trim(target_field)) > 0",
            name="ck_questions_target_field_nonblank",
        ),
        CheckConstraint(
            "reason IS NULL OR length(trim(reason)) > 0",
            name="ck_questions_reason_nonblank",
        ),
        CheckConstraint(
            "candidates IS NULL OR length(trim(candidates)) > 0",
            name="ck_questions_candidates_nonblank",
        ),
        CheckConstraint(
            "category IN ('unknown','conflict','reference_missing','alternative','condition_missing','inherit_candidate')",
            name="ck_questions_category",
        ),
        UniqueConstraint(
            "version_id", "question_code", name="uq_questions_version_id_question_code"
        ),
    )
    op.create_index("ix_questions_version_id", "questions", ["version_id"])
    op.create_table(
        "source_inventory_entries",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column("version_id", BigInteger, ForeignKey("versions.id"), nullable=False),
        Column("document_id", BigInteger, ForeignKey("documents.id"), nullable=False),
        Column("position", Text, nullable=False),
        Column("excerpt", Text, nullable=False),
        Column("source_no", Text, nullable=True),
        Column("status_detail", Text, nullable=True),
        Column("basis", Text, nullable=True),
        Column("seq", Integer, nullable=False),
        Column("status", Text, nullable=False),
        CheckConstraint(
            "position IS NULL OR length(trim(position)) > 0",
            name="ck_source_inventory_entries_position_nonblank",
        ),
        CheckConstraint(
            "excerpt IS NULL OR length(trim(excerpt)) > 0",
            name="ck_source_inventory_entries_excerpt_nonblank",
        ),
        CheckConstraint(
            "source_no IS NULL OR length(trim(source_no)) > 0",
            name="ck_source_inventory_entries_source_no_nonblank",
        ),
        CheckConstraint(
            "status_detail IS NULL OR length(trim(status_detail)) > 0",
            name="ck_source_inventory_entries_status_detail_nonblank",
        ),
        CheckConstraint(
            "basis IS NULL OR length(trim(basis)) > 0",
            name="ck_source_inventory_entries_basis_nonblank",
        ),
        CheckConstraint("seq > 0", name="ck_source_inventory_entries_seq"),
        CheckConstraint(
            "status IN ('mapped','split','excluded','unmapped')",
            name="ck_source_inventory_entries_status",
        ),
        CheckConstraint(
            "status<>'excluded' OR basis IS NOT NULL",
            name="ck_source_inventory_entries_excluded_basis",
        ),
    )
    op.create_table(
        "inventory_links",
        Column("id", BigInteger, primary_key=True, autoincrement=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        Column(
            "entry_id",
            BigInteger,
            ForeignKey("source_inventory_entries.id"),
            nullable=False,
        ),
        Column("item_id", BigInteger, ForeignKey("items.id"), nullable=False),
        UniqueConstraint(
            "entry_id", "item_id", name="uq_inventory_links_entry_id_item_id"
        ),
    )


def downgrade():
    raise RuntimeError(
        "Artifact deletion requires explicit approval; no destructive downgrade is provided."
    )
