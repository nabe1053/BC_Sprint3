"""#8・#9 エージェント専用の DTO（05-api-ipo.md 5章 #8・#9・0.4）。"""

from typing import Literal

from app.api.schemas_base import CamelModel, CamelRequestModel

# 04-db.md ck_document_issues_issue_type（reviewer 指摘 重-3: 05-api-ipo.md に
# 該当するエラーコードが無いため、DB の CHECK 違反（500）に到達させず
# Pydantic の 422 で拒否する）。
IssueType = Literal[
    "unreadable_page",
    "encrypted",
    "unsupported",
    "reference_missing",
    "not_scanned",
]


class SearchResultItem(CamelModel):
    document_id: int
    locator: str
    excerpt: str


class SearchResponse(CamelModel):
    results: list[SearchResultItem]


class IssueCreateRequest(CamelRequestModel):
    """#9 のリクエスト本文（05-api-ipo.md 0.4）。

    `locator` は省略可（省略＝資料全体）。`detail` は空不可（Service 層で
    `E_DETAIL_REQUIRED` を判定する。空文字と空白のみを拒否対象とし、
    Pydantic の 422 ではなく業務エラーの 400 として返すため min_length は付けない）。
    `issue_type` は 04-db.md の CHECK 制約の語彙に `Literal` で縛る（重-3:
    未知の値が DB まで到達して IntegrityError（500）にならないようにする）。
    """

    locator: str | None = None
    issue_type: IssueType
    detail: str


class IssueCreateResponse(CamelModel):
    issue_id: int
