import pytest
from app.services.inventory_reconciliation import reconcile
from tests.fixtures.inventory_data import entry, output_item, link, s06


def test_s06_sets_match_eight_to_eleven_three_splits_four_excluded():
    result = reconcile(*s06(), version_id=1)
    summary = result.summary
    assert (
        summary.source_entry_count,
        summary.source_item_count,
        summary.output_row_count,
    ) == (12, 8, 11)
    assert summary.split_entry_ids == {6, 7, 8}
    assert summary.excluded_entry_ids == {9, 10, 11, 12}
    assert (
        summary.unmapped_entry_ids
        == summary.orphan_item_ids
        == summary.multi_mapped_item_ids
        == summary.inconsistent_entry_ids
        == set()
    )
    assert [item.item_id for item in result.entries[5].linked_items] == [106, 107]
    assert result.entries[5].judgement == "split" and result.entries[5].link_count == 2


def test_unmapped_without_links_is_missing_but_linked_unmapped_is_only_inconsistent():
    result = reconcile(
        [entry(1, "unmapped"), entry(2, "unmapped")],
        [link(2, 101)],
        [output_item()],
        version_id=1,
    )
    assert result.summary.unmapped_entry_ids == {1}
    assert result.summary.inconsistent_entry_ids == {2}
    assert [row.judgement for row in result.entries] == ["missing", "inconsistent"]


def test_output_without_link_is_orphan():
    result = reconcile(
        [entry()], [link(1, 101)], [output_item(), output_item(102)], version_id=1
    )
    assert result.summary.orphan_item_ids == {102}
    assert [item.has_source for item in result.items] == [True, False]


def test_two_entries_mapped_to_one_item_are_multi_mapped():
    result = reconcile(
        [entry(1), entry(2)],
        [link(1, 101), link(2, 101)],
        [output_item()],
        version_id=1,
    )
    assert result.summary.multi_mapped_item_ids == {101}
    assert {ref.entry_id for ref in result.items[0].source_entries} == {1, 2}


@pytest.mark.parametrize(
    "status,links",
    [("mapped", []), ("split", [link(1, 101)]), ("excluded", [link(1, 101)])],
)
def test_saved_status_conflicting_with_structure_is_inconsistent(status, links):
    result = reconcile([entry(1, status)], links, [output_item()], version_id=1)
    assert result.summary.inconsistent_entry_ids == {1}
    assert (
        result.entries[0].status == status
        and result.entries[0].judgement == "inconsistent"
    )


def test_outside_version_links_are_inconsistent_without_importing_foreign_items():
    result = reconcile(
        [entry()],
        [link(1, 201)],
        [output_item(), output_item(201, version_id=2)],
        version_id=1,
    )
    assert result.summary.inconsistent_entry_ids == {1}
    assert {item.item_id for item in result.items} == {101}
    assert result.entries[0].linked_items == ()


def test_reverse_input_is_sorted_by_seq_then_id_on_both_sides():
    entries, links, items = s06()
    entries[0].seq = entries[1].seq
    items[0].seq = items[1].seq
    result = reconcile(
        list(reversed(entries)),
        list(reversed(links)),
        list(reversed(items)),
        version_id=1,
    )
    assert [row.entry_id for row in result.entries] == list(range(1, 13))
    assert [row.item_id for row in result.items] == list(range(101, 112))


def test_empty_inputs_return_zero_counts_and_empty_sets():
    result = reconcile([], [], [], version_id=1)
    assert (
        result.summary.source_entry_count,
        result.summary.source_item_count,
        result.summary.output_row_count,
    ) == (0, 0, 0)
    assert result.entries == result.items == ()
    assert (
        result.summary.split_entry_ids
        == result.summary.excluded_entry_ids
        == result.summary.unmapped_entry_ids
        == result.summary.orphan_item_ids
        == result.summary.multi_mapped_item_ids
        == result.summary.inconsistent_entry_ids
        == set()
    )


def test_s02_totals_and_headings_are_excluded_not_missing():
    entries = [entry(i, "mapped" if i <= 6 else "excluded") for i in range(1, 11)]
    result = reconcile(
        entries,
        [link(i, 100 + i) for i in range(1, 7)],
        [output_item(i) for i in range(101, 107)],
        version_id=1,
    )
    assert result.summary.source_item_count == result.summary.output_row_count == 6
    assert result.summary.excluded_entry_ids == {7, 8, 9, 10}
    assert (
        result.summary.unmapped_entry_ids
        == result.summary.inconsistent_entry_ids
        == set()
    )


def test_unknown_entry_link_is_reported_without_fabricating_a_source():
    result = reconcile([], [link(999, 101)], [output_item()], version_id=1)
    assert result.summary.inconsistent_entry_ids == {999}
    assert result.items[0].source_entries == ()
    assert result.items[0].has_source
