"""Strict tool arguments and local decision protocol, independent of SDK/DB."""
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.draft_types import (
    HeaderInput,
    ItemInput,
    EvidenceInput,
    QuestionInput,
    InventoryInput,
)


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CaseArguments(Arguments):
    case_id: int | None = Field(default=None, gt=0)


class DocumentArguments(Arguments):
    document_id: int = Field(gt=0)


class ContentArguments(DocumentArguments):
    from_seq: int | None = Field(default=None, ge=1)
    to_seq: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if (
            self.from_seq is not None
            and self.to_seq is not None
            and self.from_seq > self.to_seq
        ):
            raise ValueError("Invalid sequence range")
        return self


class SearchArguments(CaseArguments):
    query: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class RuleArguments(Arguments):
    rule_set_id: int | None = Field(default=None, gt=0)


class VersionArguments(Arguments):
    version_id: int | None = Field(default=None, gt=0)


class HeaderArguments(VersionArguments):
    header: HeaderInput


class ItemArguments(VersionArguments):
    """明細行をrows配列で一括登録する（1件以上）。各項目は「状態」と「値」の組で渡す。
    状態と値は両方向で一致させる（stated なら値あり、stated 以外では値を渡さない）。
    - odState/wallState/weightState=stated なら odValue/wallValue/weightValue と単位（odUnit 等）が必須。
      stated 以外では値を渡さない。原表記は odRaw 等に別途残す
    - gradeState/connectionState=stated なら grade/connection（正規化値）が必須。stated 以外では渡さない。
      gradeRaw は原表記で常に必須
    - rangeClass（R1/R2/R3 等）または lengthValue を渡したら lengthState は stated。
      stated 以外では rangeClass も lengthValue も渡さない
    - dueState/placeState=stated なら dueRaw/placeRaw が必須。stated 以外では dueRaw/placeRaw を渡さない
    - qtyState=numeric のときだけ qtyValue と qtyUnit を渡す。qtyRaw は原表記で常に必須
    - 数値（odValue・qtyValue 等）は10進の文字列（"13.375"）か整数で渡す。小数を JSON の数値で渡さない
    - candidateLabel を付ける行（択一候補）には groupCode が必要
    検証エラーは各行の状態と値の違反をまとめて返す（loc が該当項目）。一度に全部直して再登録する。
    ただし型・必須の誤りがある行は、それを直した後に状態と値の違反が見つかることがある。
    """

    rows: list[ItemInput] = Field(min_length=1)


class EvidenceArguments(VersionArguments):
    """根拠をevidences配列で一括登録する（1件以上）。1件でも配列を使い、項目ごとの出典を残す。"""

    evidences: list[EvidenceInput] = Field(min_length=1)


class QuestionArguments(VersionArguments):
    """確認事項をquestions配列で一括登録する（1件以上）。各要素に対象行itemId（案件なら省略）と対象項目targetFieldを指定する。"""

    questions: list[QuestionInput] = Field(min_length=1)


class InventoryArguments(VersionArguments):
    """原資料の全要素をentries配列で登録する。各要素にdocumentId・position・正整数seqを渡す。
    statusはmapped（itemIdsが1件）、split（2件以上）、excluded・unmapped（空配列）のいずれか。
    excludedではbasisに除外理由を必ず記入する。excerptは原文の短い抜粋であり、要約に置換しない。
    sourceNoは資料にある原項番（無ければ省略）。明細にしない注記・署名等も根拠つきで棚卸しする。
    """

    entries: list[InventoryInput] = Field(min_length=1)


class IssueArguments(DocumentArguments):
    locator: str | None = None
    issue_type: Literal[
        "unreadable_page",
        "encrypted",
        "unsupported",
        "reference_missing",
        "not_scanned",
    ]
    detail: str = Field(min_length=1)


TOOL_ARGUMENTS = {
    "list_case_documents": CaseArguments,
    "read_document": ContentArguments,
    "read_email": DocumentArguments,
    "search_documents": SearchArguments,
    "get_rules": RuleArguments,
    "record_case_header": HeaderArguments,
    "propose_items": ItemArguments,
    "record_evidence": EvidenceArguments,
    "record_question": QuestionArguments,
    "record_source_inventory": InventoryArguments,
    "report_unreadable": IssueArguments,
    "validate_draft": VersionArguments,
    "finalize_draft": VersionArguments,
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyHeartbeat:
    received_at: float


@dataclass(frozen=True)
class ToolReply:
    data: dict
    is_error: bool = False


class LocalPolicyStop(Exception):
    """A local policy cannot proceed; only fixed reason codes cross this boundary."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)
