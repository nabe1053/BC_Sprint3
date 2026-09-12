from datetime import UTC, datetime, timedelta

from tests.fixtures.record_data import current_item, edit


def test_current_values_use_ordered_active_edits_and_keep_all_history():
    from app.services.item_current_values import apply_edits

    original = current_item()
    early = edit(id=1, new_value="J55")
    later = edit(id=2, new_value="L80")
    undone = edit(id=3, new_value="N80", undone_at=datetime.now(UTC))
    current = apply_edits(original, [undone, later, early])
    assert current.values["grade"] == "L80"
    assert current.history == [early, later, undone]
    assert original.grade == "K55" and current.values["grade_raw"] == "K55"


def test_undo_restores_original_and_raw_fields_are_never_overwritten():
    from app.services.item_current_values import apply_edits

    current = apply_edits(
        current_item(),
        [
            edit(undone_at=datetime.now(UTC)),
            edit(id=2, field="grade_raw", new_value="changed"),
        ],
    )
    assert current.values["grade"] == "K55"
    assert current.values["grade_raw"] == "K55"


def test_state_only_removes_value_and_units_then_quantity_pair_restores_numeric():
    from app.services.item_current_values import apply_edits

    removed = edit(field="qty_value", new_value=None, new_state="tba")
    current = apply_edits(current_item(), [removed])
    assert (
        current.values["qty_value"],
        current.values["qty_unit"],
        current.values["qty_state"],
    ) == (None, None, "tba")
    number = edit(id=2, field="qty_value", new_value="250", new_state="numeric")
    unit = edit(id=3, field="qty_unit", new_value="本", new_state="numeric")
    current = apply_edits(current_item(), [removed, number, unit])
    assert (
        str(current.values["qty_value"]) == "250" and current.values["qty_unit"] == "本"
    )
    assert current.values["qty_state"] == "numeric"


def test_recorded_time_precedes_id_and_value_only_infers_stated_state():
    from app.services.item_current_values import apply_edits

    first = edit(id=9, recorded_at=datetime(2026, 1, 1, tzinfo=UTC))
    last = edit(
        id=1,
        new_value="N80",
        new_state=None,
        recorded_at=first.recorded_at + timedelta(seconds=1),
    )
    result = apply_edits(current_item(), [last, first])
    assert result.values["grade"] == "N80" and result.values["grade_state"] == "stated"
