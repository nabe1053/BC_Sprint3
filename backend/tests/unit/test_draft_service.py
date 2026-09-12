from contextlib import asynccontextmanager
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.domain.draft_errors import DraftError
from app.services.draft_service import DraftService
from tests.unit.test_draft_inputs import item_data
from tests.unit.test_draft_validation import snapshot


def repository():
    repo = N(
        snapshot=AsyncMock(return_value=snapshot()),
        complete=AsyncMock(),
        add_items=AsyncMock(),
        create_version=AsyncMock(),
    )
    repo.locked = False

    @asynccontextmanager
    async def edit(version_id):
        repo.locked = True
        try:
            yield N(id=version_id)
        finally:
            repo.locked = False

    repo.edit = edit
    return repo


async def test_validation_is_readonly():
    repo = repository()
    service = DraftService(repo)
    result = await service.validate(1)
    assert not result.violations
    repo.complete.assert_not_called()


async def test_finalize_rechecks_under_lock_and_persists_empty_violations():
    repo = repository()

    async def complete(version, validation, is_complete, finalized_at):
        assert repo.locked
        assert validation == []
        assert is_complete
        assert finalized_at.utcoffset() is not None
        return version

    repo.complete.side_effect = complete
    assert (await DraftService(repo).finalize(1)).id == 1
    assert not repo.locked


@pytest.mark.parametrize(
    "cause,code",
    [
        ("no_items", "E_NO_ITEMS"),
        ("unscanned", "E_VALIDATION_FAILED"),
        ("no_header", "E_VALIDATION_FAILED"),
        ("no_inventory", "E_VALIDATION_FAILED"),
    ],
)
async def test_finalize_refuses_incomplete_artifacts(cause, code):
    repo = repository()
    s = repo.snapshot.return_value
    if cause == "no_items":
        s.items.clear()
    elif cause == "unscanned":
        s.scanned_ranges.clear()
    elif cause == "no_header":
        s.header = None
    else:
        s.inventory.clear()
    with pytest.raises(DraftError) as exc:
        await DraftService(repo).finalize(1)
    assert exc.value.code == code
    repo.complete.assert_not_called()


async def test_partial_input_is_finalized_with_incomplete_flag():
    repo = repository()
    repo.snapshot.return_value.has_issues = True
    await DraftService(repo).finalize(1)
    assert repo.complete.call_args.args[2] is False


async def test_service_rejects_conversion_before_repository_write():
    repo = repository()
    with pytest.raises(ValidationError):
        await DraftService(repo).add_items(1, [item_data() | {"convertedValue": "100"}])
    repo.add_items.assert_not_called()


async def test_finalize_error_details_follow_shared_camel_case_contract():
    repo = repository()
    repo.snapshot.return_value.scanned_ranges.clear()
    with pytest.raises(DraftError) as exc:
        await DraftService(repo).finalize(1)
    assert "inventoryRequired" in exc.value.details
    violation = exc.value.details["violations"][0]
    assert "documentId" in violation and "itemId" in violation
    assert not any("_" in key for key in violation)
