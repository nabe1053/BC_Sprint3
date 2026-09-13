"""Workbook vocabulary, timezone and safe download filenames."""
from datetime import UTC, datetime
from typing import get_args


def test_sheet_names_and_label_domains_are_complete():
    from app.domain import export_types as e
    from app.domain.record_types import (
        EditState,
        VersionState,
        SendoffState,
        JudgementInput,
    )
    from app.domain.draft_types import QuestionInput

    assert e.SHEET_NAMES == (
        "案件情報",
        "Item List",
        "根拠",
        "確認事項",
        "変更・確認記録",
    )
    for labels, vocabulary in [
        (e.ITEM_STATE_LABELS, EditState),
        (e.VERSION_STATE_LABELS, VersionState),
        (e.SENDOFF_LABELS, SendoffState),
        (e.STATUS_LABELS, JudgementInput.model_fields["status"].annotation),
        (e.RESOLUTION_LABELS, JudgementInput.model_fields["resolution"].annotation),
        (
            e.CATEGORY_LABELS,
            get_args(QuestionInput.model_fields["category"].annotation)[0],
        ),
    ]:
        assert set(labels) == set(get_args(vocabulary))


def test_timestamp_is_jst_to_seconds_and_none_is_empty():
    from app.domain.export_types import format_ts

    assert (
        format_ts(datetime(2026, 9, 13, 5, 3, 5, 123456, tzinfo=UTC))
        == "2026-09-13 14:03:05+09:00"
    )
    assert format_ts(None) == ""


def test_export_filename_uses_ascii_safe_code_and_jst():
    from app.domain.export_types import export_file_name

    at = datetime(2026, 9, 13, 5, 3, 5, tzinfo=UTC)
    assert (
        export_file_name("S-01/α", 2, "staff_checked", at)
        == "S-01__v2_staff_checked_20260913-140305.xlsx"
    )
    assert (
        export_file_name("", 2, "draft", at, case_id=7)
        == "case7_v2_draft_20260913-140305.xlsx"
    )


def test_content_hash_is_sha256_hex_of_exact_bytes():
    from app.domain.export_types import sha256_hex

    assert (
        sha256_hex(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
