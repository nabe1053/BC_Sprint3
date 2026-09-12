"""Pure draft input and snapshot builders shared across test layers."""
from types import SimpleNamespace as N


def item_data():
    return dict(
        row_code="1",
        source_no="1",
        seq=1,
        kind="casing",
        kind_raw="CSG",
        od_state="stated",
        od_value="13.375",
        od_unit="in",
        od_raw='13-3/8"',
        wall_state="not_stated",
        weight_state="not_stated",
        grade="K55",
        grade_raw="K55",
        grade_state="stated",
        connection_state="tba",
        length_state="not_stated",
        qty_state="numeric",
        qty_value="150",
        qty_unit="MT",
        qty_raw="150 MT",
        due_state="not_stated",
        place_state="not_stated",
    )


def header_data():
    return dict(
        inquiry_no_state="not_stated",
        customer_name_state="not_stated",
        due_state="not_stated",
        place_state="not_stated",
        incoterms_state="not_stated",
        quote_deadline_tz_state="missing",
    )


def item():
    return dict(
        rowCode="1",
        sourceNo="1",
        seq=1,
        kind="casing",
        kindRaw="CSG",
        odState="not_stated",
        wallState="not_stated",
        weightState="not_stated",
        gradeRaw="記載なし",
        gradeState="not_stated",
        connectionState="not_stated",
        lengthState="not_stated",
        qtyState="numeric",
        qtyValue="150",
        qtyUnit="MT",
        qtyRaw="150 MT",
        dueState="not_stated",
        placeState="not_stated",
    )


def header():
    return dict(
        inquiryNoState="not_stated",
        customerNameState="not_stated",
        dueState="not_stated",
        placeState="not_stated",
        incotermsState="not_stated",
        quoteDeadlineTzState="missing",
    )


def snapshot():
    return N(
        items=[
            N(
                id=1,
                source_no="1",
                group_code=None,
                od_value=None,
                wall_value=None,
                weight_value=None,
                length_value=None,
                qty_value=150,
                qty_unit="MT",
                kind="casing",
                grade=None,
                connection=None,
                range_class=None,
                due_raw=None,
                place_raw=None,
                usage_note=None,
                qty_reference_note=None,
                note=None,
            )
        ],
        header=N(
            inquiry_no=None,
            customer_name=None,
            due_raw=None,
            place_raw=None,
            incoterms=None,
            quote_deadline_raw=None,
        ),
        evidences=[
            N(
                item_id=1,
                field=f,
                document_id=1,
                locator="p.1",
                quote="original",
                raw_value="original",
                adopted_value="original",
            )
            for f in ("kind", "qty")
        ],
        questions=[],
        inventory=[N(id=1, status="mapped", basis=None)],
        readable_ranges={(1, "p.1")},
        scanned_ranges={(1, "p.1")},
        excused_ranges=set(),
        has_issues=False,
        ends=[],
    )
