"""Derive current display values without altering source items or edit history."""
from app.domain.record_types import CurrentItem, EDITABLE_FIELDS, STATE_FIELDS
from app.domain.draft_types import exact_decimal


def apply_edits(item, edits):
    values = {
        key: value
        for key, value in (item if isinstance(item, dict) else vars(item)).items()
        if not key.startswith("_")
    }
    history = sorted(edits, key=lambda edit: (edit.recorded_at, edit.id))
    for edit in history:
        if edit.undone_at is not None or edit.field not in EDITABLE_FIELDS:
            continue
        state_field = STATE_FIELDS.get(edit.field)
        state = edit.new_state
        if state_field and state is None and edit.new_value is not None:
            state = "numeric" if state_field == "qty_state" else "stated"
        if state_field:
            values[state_field] = state
        if state is not None and state not in ("stated", "numeric"):
            for field, related in STATE_FIELDS.items():
                if related == state_field:
                    values[field] = None
        else:
            values[edit.field] = (
                exact_decimal(edit.new_value)
                if edit.field.endswith("_value") and edit.new_value is not None
                else edit.new_value
            )
    return CurrentItem(values, history)
