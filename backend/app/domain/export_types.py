"""Workbook snapshot contracts and pure display vocabulary."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import re
from typing import Literal
from zoneinfo import ZoneInfo
from app.domain.record_types import RowMatch, VersionState, SendoffState

SHEET_NAMES = ("案件情報", "Item List", "根拠", "確認事項", "変更・確認記録")
DISPLAY_TZ = ZoneInfo("Asia/Tokyo")
ITEM_STATE_LABELS = {
    "stated": "記載あり",
    "numeric": "数値",
    "tba": "未確定 TBA",
    "not_stated": "記載なし",
    "not_applicable": "適用なし",
}
VERSION_STATE_LABELS = {
    "draft": "作成案",
    "staff_checked": "担当者確認済み",
    "review_checked": "評価確認済み",
}
SENDOFF_LABELS = {"undecided": "未判断", "hold": "保留", "approved": "承認"}
RESOLUTION_LABELS = {"unresolved": "未解決", "resolved": "解決済み"}
STATUS_LABELS = {"open": "未対応", "in_progress": "対応中", "judged": "判断済み"}
CATEGORY_LABELS = {
    "unknown": "不明",
    "conflict": "矛盾",
    "reference_missing": "参照資料不足",
    "alternative": "代替候補",
    "condition_missing": "条件不足",
    "inherit_candidate": "継承候補",
}
CASE_HEADERS = ("項目", "値", "状態")
DOCUMENT_HEADERS = ("資料名", "形式", "読取状態", "受付日時", "ページ数")
ITEM_HEADERS = (
    "行ID",
    "原項番",
    "品種",
    "原品名",
    "用途",
    "外径",
    "外径単位",
    "外径原表記",
    "外径状態",
    "肉厚",
    "肉厚単位",
    "肉厚原表記",
    "肉厚状態",
    "単重",
    "単重単位",
    "単重原表記",
    "単重状態",
    "グレード",
    "グレード原表記",
    "グレード状態",
    "接続",
    "接続原表記",
    "接続状態",
    "レンジ",
    "定尺長",
    "定尺長単位",
    "定尺長原表記",
    "レンジ・定尺長状態",
    "数量",
    "数量単位",
    "数量原表記",
    "数量状態",
    "数量参考注記",
    "要求納期（原文）",
    "要求納期状態",
    "納地（原文）",
    "納地状態",
    "備考",
    "選択グループ",
    "候補区分",
    "継承候補",
    "両端A 外径",
    "両端A 単位",
    "両端A 原表記",
    "両端A 接続",
    "両端A BOX・PIN",
    "両端B 外径",
    "両端B 単位",
    "両端B 原表記",
    "両端B 接続",
    "両端B BOX・PIN",
    "一致確認",
    "確認者",
    "確認日時",
    "訂正件数",
)
EVIDENCE_HEADERS = (
    "行ID",
    "項目名",
    "原値",
    "採用値",
    "資料名",
    "位置",
    "引用",
    "共通条件・個別例外",
    "換算条件",
    "変更の採用理由",
    "資料上の変更前値",
)
QUESTION_HEADERS = (
    "確認ID",
    "行ID",
    "対象項目",
    "区分",
    "理由",
    "候補・不足条件",
    "対応状況",
    "解決状態",
    "判断内容",
    "判断者",
    "判断日時",
)
RECORD_HEADERS = (
    "種別",
    "行ID",
    "項目",
    "変更前の値",
    "変更前の状態",
    "変更後の値",
    "変更後の状態",
    "理由・内容",
    "補足",
    "記録者",
    "記録日時",
    "取消者",
    "取消日時",
)
RECORD_KINDS = (
    "訂正",
    "一致確認",
    "網羅性確認",
    "判断",
    "状態遷移",
    "差し戻し",
    "差し戻しコメント",
    "送付可否",
)


@dataclass(frozen=True)
class ItemRow:
    values: dict
    ends: list
    row_match: RowMatch | None
    edit_count: int


@dataclass(frozen=True)
class ExportSnapshot:
    case: object
    version: object
    header: object | None
    documents: list
    items: list[ItemRow]
    evidences: list
    questions: list
    records: dict
    elapsed_sec: Decimal | None
    rule_version: str
    conversion_enabled: bool
    unresolved_count: int
    matched_count: int
    coverage_confirmed: bool


@dataclass(frozen=True)
class ExportResult:
    record: object
    content: bytes


@dataclass(frozen=True)
class ExportWithIntegrity:
    export_id: int
    file_name: str
    storage_path: str
    content_hash: str
    exported_at: datetime
    state_at_export: VersionState
    sendoff_at_export: SendoffState
    unresolved_at_export: int
    is_initial: bool
    integrity: Literal["intact", "modified", "missing"]


def format_ts(value):
    return (
        ""
        if value is None
        else value.astimezone(DISPLAY_TZ).isoformat(sep=" ", timespec="seconds")
    )


def export_file_name(case_code, version_no, state, exported_at, *, case_id=0):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", case_code) or f"case{case_id}"
    stamp = exported_at.astimezone(DISPLAY_TZ).strftime("%Y%m%d-%H%M%S")
    return f"{safe}_v{version_no}_{state}_{stamp}.xlsx"


def sha256_hex(content):
    return sha256(content).hexdigest()
