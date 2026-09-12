"""Check RV-016 regression sensitivity; mutate functions in memory, never files/DB.

Run from backend: .venv/bin/python -B scripts/check_g2_mutations_isolated.py MODE
MODE: scanned / excused / explicit / refresh. Expected pytest failure means detected.
"""
import inspect
import sys
import textwrap
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


class Mutation:
    def __init__(self, mode):
        self.mode = mode

    def pytest_collection_modifyitems(self, items):
        # Collection has already loaded only tests/t201/conftest.py's dummy DB.
        from app.repositories.draft_repository import DraftRepository
        from app.services import draft_validation

        if self.mode == "explicit":
            target = draft_validation.validate_snapshot
            before, after = '("tba", "not_applicable")', '("mutation_disabled",)'
        elif self.mode == "refresh":
            target = DraftRepository.edit
            before, after = "populate_existing=True", "populate_existing=False"
        else:
            target = DraftRepository.snapshot
            before = f"snapshot.{self.mode}_ranges.add"
            after = "set().add"
        original = inspect.unwrap(target)
        source = textwrap.dedent(inspect.getsource(target))
        assert before in source
        namespace = dict(original.__globals__)
        exec(source.replace(before, after), namespace)
        replacement = namespace[original.__name__]
        if self.mode == "explicit":
            # Tests import the function directly, so replace its code in place.
            original.__code__ = replacement.__code__
        else:
            setattr(DraftRepository, original.__name__, replacement)


if __name__ == "__main__":
    mode = sys.argv[1]
    names = {
        "scanned": "test_successful_read_marks_only_requested_range",
        "excused": "test_scoped_issue_excuses_only_matching_range",
        "explicit": "test_every_item_explicit_state_requires_own_evidence",
        "refresh": "test_edit_refreshes_finalization_from_database",
    }
    result = pytest.main(
        [
            "-p",
            "no:cacheprovider",
            "--confcutdir=tests/t201",
            "tests/t201",
            "-k",
            names[mode],
            "-q",
            "--tb=no",
            "--disable-warnings",
        ],
        plugins=[Mutation(mode)],
    )
    print(f"Mutation {mode}: {'DETECTED' if result == 1 else 'NOT VERIFIED'}")
    sys.exit(0 if result == 1 else 1)
