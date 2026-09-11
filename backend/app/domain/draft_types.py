"""T-201 input contracts. Conversion and total fields are intentionally absent (D03/R07)."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


def exact_decimal(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Numeric input must be an exact decimal string or integer")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Numeric input must be finite")
    return result


Number = Annotated[Decimal, BeforeValidator(exact_decimal)]
State = Literal["stated", "tba", "not_stated", "not_applicable"]
Nonblank = Annotated[str, Field(min_length=1)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True,
                              populate_by_name=True, alias_generator=to_camel)


class EndInput(Input):
    side: Literal["end_a", "end_b"]
    od_value: Number | None = None
    od_unit: Nonblank | None = None
    od_raw: Nonblank | None = None
    connection: Nonblank | None = None
    thread_end: Literal["BOX", "PIN"] | None = None

    @model_validator(mode="after")
    def unit_required(self):
        if self.od_value is not None and not self.od_unit:
            raise ValueError("E_UNIT_REQUIRED")
        return self


class ItemInput(Input):
    row_code: Nonblank
    source_no: Nonblank
    seq: int = Field(ge=1)
    kind: Nonblank
    kind_raw: Nonblank
    usage_note: Nonblank | None = None
    od_value: Number | None = None
    od_unit: Nonblank | None = None
    od_raw: Nonblank | None = None
    od_state: State
    wall_value: Number | None = None
    wall_unit: Nonblank | None = None
    wall_raw: Nonblank | None = None
    wall_state: State
    weight_value: Number | None = None
    weight_unit: Nonblank | None = None
    weight_raw: Nonblank | None = None
    weight_state: State
    grade: Nonblank | None = None
    grade_raw: Nonblank
    grade_state: State
    connection: Nonblank | None = None
    connection_raw: Nonblank | None = None
    connection_state: State
    range_class: Nonblank | None = None
    length_value: Number | None = None
    length_unit: Nonblank | None = None
    length_raw: Nonblank | None = None
    length_state: State
    qty_value: Number | None = None
    qty_unit: Nonblank | None = None
    qty_state: Literal["numeric", "tba", "not_stated", "not_applicable"]
    qty_raw: Nonblank
    qty_reference_note: Nonblank | None = None
    due_raw: Nonblank | None = None
    due_state: State
    place_raw: Nonblank | None = None
    place_state: State
    note: Nonblank | None = None
    group_code: Nonblank | None = None
    candidate_label: Nonblank | None = None
    is_inherit_candidate: bool = False
    ends: list[EndInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_values(self):
        numeric = self.qty_state == "numeric"
        if numeric != (self.qty_value is not None):
            raise ValueError("E_QTY_STATE_INVALID")
        if numeric and not self.qty_unit:
            raise ValueError("E_QTY_UNIT_REQUIRED")
        for field in ("od", "wall", "weight", "length"):
            value = getattr(self, field + "_value")
            if value is not None and not getattr(self, field + "_unit"):
                raise ValueError("E_UNIT_REQUIRED")
        values = dict(od=self.od_value, wall=self.wall_value, weight=self.weight_value,
                      grade=self.grade, connection=self.connection,
                      length=self.range_class if self.range_class is not None else self.length_value,
                      due=self.due_raw, place=self.place_raw)
        for field, value in values.items():
            if (getattr(self, field + "_state") == "stated") != (value is not None):
                raise ValueError("E_STATE_VALUE_CONFLICT: " + field)
        if self.candidate_label and not self.group_code:
            raise ValueError("E_GROUP_REQUIRED")
        if len({end.side for end in self.ends}) != len(self.ends):
            raise ValueError("Duplicate end side")
        return self


class HeaderInput(Input):
    inquiry_no: Nonblank | None = None
    inquiry_no_state: Literal["stated", "not_stated"]
    customer_name: Nonblank | None = None
    customer_name_state: Literal["stated", "not_stated"]
    due_raw: Nonblank | None = None
    due_state: Literal["stated", "tba", "not_stated"]
    due_granularity: Literal["date", "month", "quarter", "period", "month_end", "unknown"] | None = None
    due_basis: Literal["shipment", "arrival", "unknown"] | None = None
    place_raw: Nonblank | None = None
    place_state: Literal["stated", "not_stated", "not_applicable"]
    incoterms: Nonblank | None = None
    incoterms_state: Literal["stated", "not_stated", "not_applicable"]
    quote_deadline_raw: Nonblank | None = None
    quote_deadline_at: datetime | None = None
    quote_deadline_tz_state: Literal["stated", "missing"]

    @model_validator(mode="after")
    def consistent_values(self):
        for field, attr in (("inquiry_no", "inquiry_no"), ("customer_name", "customer_name"),
                            ("due", "due_raw"), ("place", "place_raw"), ("incoterms", "incoterms")):
            if (getattr(self, field+"_state") == "stated") != (getattr(self, attr) is not None):
                raise ValueError("E_STATE_VALUE_CONFLICT: "+field)
        if self.quote_deadline_at is not None:
            if (self.quote_deadline_tz_state != "stated" or not self.quote_deadline_raw
                    or self.quote_deadline_at.utcoffset() is None):
                raise ValueError("Quote deadline requires an explicit source and timezone")
        return self


class EvidenceInput(Input):
    item_id: int | None = Field(default=None, gt=0)
    field: Nonblank
    raw_value: Nonblank
    adopted_value: Nonblank
    document_id: int = Field(gt=0)
    locator: Nonblank
    quote: Nonblank
    applied_condition: Nonblank | None = None
    change_reason: Nonblank | None = None
    prior_value: Nonblank | None = None


class QuestionInput(Input):
    question_code: Nonblank
    item_id: int | None = Field(default=None, gt=0)
    target_field: Nonblank
    reason: Nonblank
    candidates: Nonblank | None = None
    category: Literal["unknown", "conflict", "reference_missing", "alternative",
                      "condition_missing", "inherit_candidate"] | None = None


class InventoryInput(Input):
    document_id: int = Field(gt=0)
    position: Nonblank
    source_no: Nonblank | None = None
    seq: int = Field(ge=1)
    excerpt: Nonblank
    status: Literal["mapped", "split", "excluded", "unmapped"]
    status_detail: Nonblank | None = None
    basis: Nonblank | None = None
    item_ids: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_mapping(self):
        if self.status == "excluded" and not self.basis:
            raise ValueError("Excluded entries require a basis")
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError("Duplicate item link")
        count = len(self.item_ids)
        if ((self.status in ("excluded", "unmapped") and count != 0)
                or (self.status == "mapped" and count != 1)
                or (self.status == "split" and count < 2)):
            raise ValueError("Inventory status and links conflict")
        return self
