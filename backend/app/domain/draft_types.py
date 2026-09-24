"""T-201 input contracts. Conversion and total fields are intentionally absent (D03/R07)."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, ClassVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
    ValidationError,
    WithJsonSchema,
)
from pydantic_core import PydanticCustomError
from pydantic.alias_generators import to_camel


def exact_decimal(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Numeric input must be an exact decimal string or integer")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Numeric input must be a valid decimal") from exc
    if not result.is_finite():
        raise ValueError("Numeric input must be finite")
    return result


# The schema must advertise only what exact_decimal accepts: JSON floats are rejected.
Number = Annotated[
    Decimal,
    BeforeValidator(exact_decimal),
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "string", "pattern": r"^[+-]?(\d+\.?\d*|\.\d+)$"},
                {"type": "integer"},
            ],
            "description": '10進数の文字列（例 "13.375"）または整数。小数を JSON の数値で渡さない',
        }
    ),
]
State = Literal["stated", "tba", "not_stated", "not_applicable"]
Nonblank = Annotated[str, Field(min_length=1)]


class Input(BaseModel):
    # Schema-owned contracts, including missing fields (field validators do not run then).
    field_error_codes: ClassVar[dict[str, str | dict[str, str]]] = {}

    @model_validator(mode="wrap")
    @classmethod
    def business_field_errors(cls, data, handler):
        try:
            result = handler(data)
        except ValidationError as exc:
            errors = exc.errors(include_url=False)
            for error in errors:
                loc = error["loc"]
                if error["type"].startswith("E_"):
                    error["type"] = PydanticCustomError(error["type"], error["type"])
                    continue
                if len(loc) != 1:
                    continue
                field = next(
                    (
                        name
                        for name, info in cls.model_fields.items()
                        if loc[0] in (name, info.alias)
                    ),
                    None,
                )
                code = cls.field_error_codes.get(field)
                if isinstance(code, dict):
                    code = code.get(error["type"], code.get("default"))
                if code and error["type"] != "extra_forbidden":
                    error["type"] = PydanticCustomError(code, code)
            raise ValidationError.from_exception_data(cls.__name__, errors) from None
        # Report every cross-field violation at once so one retry can fix them all.
        violations = result.consistency_errors()
        if violations:
            raise ValidationError.from_exception_data(
                cls.__name__,
                [
                    {
                        "type": PydanticCustomError(code, message),
                        "loc": (cls.model_fields[field].alias or field,),
                        "input": data,
                    }
                    for field, code, message in violations
                ],
            )
        return result

    def consistency_errors(self) -> list[tuple[str, str, str]]:
        """(field, code, fixed message) in check order; messages never echo input."""
        return []

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
        alias_generator=to_camel,
        revalidate_instances="always",
    )


class EndInput(Input):
    field_error_codes = {"od_unit": "E_UNIT_REQUIRED", "od_raw": "E_RAW_REQUIRED"}

    side: Literal["end_a", "end_b"]
    od_value: Number | None = None
    od_unit: Nonblank | None = None
    od_raw: Nonblank | None = None
    connection: Nonblank | None = None
    thread_end: Literal["BOX", "PIN"] | None = None

    @model_validator(mode="after")
    def unit_required(self):
        if self.od_value is not None and not self.od_unit:
            raise PydanticCustomError("E_UNIT_REQUIRED", "E_UNIT_REQUIRED")
        return self


def _state_hint(state, value, detail=""):
    # Both directions: a value with tba/not_stated must not be "fixed" to stated.
    return (
        f"{state}=stated なら {value}{detail} が必要。"
        f"{state} が tba / not_stated / not_applicable なら {value} を渡さない"
    )


STATE_VALUE_HINTS = {
    "od": _state_hint("odState", "odValue", "（odUnit つき）"),
    "wall": _state_hint("wallState", "wallValue", "（wallUnit つき）"),
    "weight": _state_hint("weightState", "weightValue", "（weightUnit つき）"),
    "grade": _state_hint("gradeState", "grade", "（gradeRaw とは別の正規化値）"),
    "connection": _state_hint(
        "connectionState", "connection", "（connectionRaw とは別の正規化値）"
    ),
    "length": "rangeClass か lengthValue（lengthUnit つき）を渡すなら lengthState=stated。"
    "lengthState が tba / not_stated / not_applicable なら rangeClass も lengthValue も渡さない",
    "due": _state_hint("dueState", "dueRaw"),
    "place": _state_hint("placeState", "placeRaw"),
}


class ItemInput(Input):
    field_error_codes = {
        **{
            name + "_state": "E_STATE_REQUIRED"
            for name in (
                "od",
                "wall",
                "weight",
                "grade",
                "connection",
                "length",
                "due",
                "place",
            )
        },
        **{
            name + "_unit": "E_UNIT_REQUIRED"
            for name in ("od", "wall", "weight", "length")
        },
        "qty_state": {"missing": "E_STATE_REQUIRED", "default": "E_QTY_STATE_INVALID"},
        "qty_unit": "E_QTY_UNIT_REQUIRED",
        "qty_raw": "E_RAW_REQUIRED",
        "grade_raw": "E_RAW_REQUIRED",
        "source_no": "E_SOURCE_REF_REQUIRED",
        "row_code": "E_SOURCE_REF_REQUIRED",
        "seq": "E_SOURCE_REF_REQUIRED",
    }

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

    def consistency_errors(self):
        errors = []
        numeric = self.qty_state == "numeric"
        if numeric != (self.qty_value is not None):
            errors.append(
                (
                    "qty_state",
                    "E_QTY_STATE_INVALID",
                    "E_QTY_STATE_INVALID: qtyState=numeric のときだけ qtyValue を渡す。"
                    "tba / not_stated / not_applicable では qtyValue を省略する",
                )
            )
        if numeric and not self.qty_unit:
            errors.append(
                (
                    "qty_unit",
                    "E_QTY_UNIT_REQUIRED",
                    "E_QTY_UNIT_REQUIRED: qtyValue には qtyUnit（原文の単位）が必要",
                )
            )
        for field in ("od", "wall", "weight", "length"):
            value = getattr(self, field + "_value")
            if value is not None and not getattr(self, field + "_unit"):
                errors.append(
                    (
                        field + "_unit",
                        "E_UNIT_REQUIRED",
                        f"E_UNIT_REQUIRED: {to_camel(field)}Value には "
                        f"{to_camel(field)}Unit が必要",
                    )
                )
        values = dict(
            od=self.od_value,
            wall=self.wall_value,
            weight=self.weight_value,
            grade=self.grade,
            connection=self.connection,
            length=self.range_class
            if self.range_class is not None
            else self.length_value,
            due=self.due_raw,
            place=self.place_raw,
        )
        for field, value in values.items():
            if (getattr(self, field + "_state") == "stated") != (value is not None):
                errors.append(
                    (
                        field + "_state",
                        "E_STATE_VALUE_CONFLICT",
                        "E_STATE_VALUE_CONFLICT: " + STATE_VALUE_HINTS[field],
                    )
                )
        if self.candidate_label and not self.group_code:
            errors.append(
                (
                    "group_code",
                    "E_GROUP_REQUIRED",
                    "E_GROUP_REQUIRED: candidateLabel には groupCode が必要",
                )
            )
        if len({end.side for end in self.ends}) != len(self.ends):
            errors.append(
                ("ends", "E_REQUEST_INVALID", "E_REQUEST_INVALID: ends の side が重複")
            )
        return errors


class HeaderInput(Input):
    field_error_codes = {
        name: "E_STATE_REQUIRED"
        for name in (
            "inquiry_no_state",
            "customer_name_state",
            "due_state",
            "place_state",
            "incoterms_state",
            "quote_deadline_tz_state",
        )
    }

    inquiry_no: Nonblank | None = None
    inquiry_no_state: Literal["stated", "not_stated"]
    customer_name: Nonblank | None = None
    customer_name_state: Literal["stated", "not_stated"]
    due_raw: Nonblank | None = None
    due_state: Literal["stated", "tba", "not_stated"]
    due_granularity: Literal[
        "date", "month", "quarter", "period", "month_end", "unknown"
    ] | None = None
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
        for field, attr in (
            ("inquiry_no", "inquiry_no"),
            ("customer_name", "customer_name"),
            ("due", "due_raw"),
            ("place", "place_raw"),
            ("incoterms", "incoterms"),
        ):
            if (getattr(self, field + "_state") == "stated") != (
                getattr(self, attr) is not None
            ):
                raise PydanticCustomError(
                    "E_RAW_REQUIRED",
                    "E_STATE_VALUE_CONFLICT: {field}",
                    {"field": field},
                )
        if self.quote_deadline_at is not None:
            if (
                self.quote_deadline_tz_state != "stated"
                or not self.quote_deadline_raw
                or self.quote_deadline_at.utcoffset() is None
            ):
                raise PydanticCustomError(
                    "E_RAW_REQUIRED",
                    "Quote deadline requires an explicit source and timezone",
                )
        return self


class EvidenceInput(Input):
    field_error_codes = {
        "document_id": "E_SOURCE_REF_REQUIRED",
        "locator": "E_SOURCE_REF_REQUIRED",
        "quote": "E_SOURCE_REF_REQUIRED",
        "raw_value": "E_RAW_REQUIRED",
    }

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
    category: Literal[
        "unknown",
        "conflict",
        "reference_missing",
        "alternative",
        "condition_missing",
        "inherit_candidate",
    ] | None = None


class InventoryInput(Input):
    field_error_codes = {"seq": "E_SOURCE_REF_REQUIRED", "basis": "E_BASIS_REQUIRED"}

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
            raise PydanticCustomError(
                "E_BASIS_REQUIRED", "Excluded entries require a basis"
            )
        if len(set(self.item_ids)) != len(self.item_ids):
            raise ValueError("Duplicate item link")
        count = len(self.item_ids)
        if (
            (self.status in ("excluded", "unmapped") and count != 0)
            or (self.status == "mapped" and count != 1)
            or (self.status == "split" and count < 2)
        ):
            raise ValueError("Inventory status and links conflict")
        return self
