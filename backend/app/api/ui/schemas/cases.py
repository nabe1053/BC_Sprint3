"""#1・#2・#3 案件の DTO（UI 専用。05-api-ipo.md 1章 A・5章の要約）。"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.api.schemas_base import CamelModel, CamelRequestModel
from app.domain.record_types import SendoffState
from app.api.ui.schemas.approvals import StateEventRecord

ProgressStatus = Literal["intake", "draft_review", "staff_checked", "review_checked"]

# 空文字だけでなく空白のみ（"   "）も拒否する（reviewer 指摘 重-2。
# 500（Service の ValueError）ではなく 422 に寄せる・決定5と整合）。
_NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CaseCreateRequest(CamelRequestModel):
    """#2: 案件作成のリクエスト。

    `case_code` は空文字・空白のみを Pydantic で拒否する（422・orchestrator 決定5・
    reviewer 指摘 重-2）。
    """

    case_code: _NonBlankStr
    customer_name: str | None = None
    title: str | None = None


class CaseResponse(CamelModel):
    """#2 レスポンス・#3 案件詳細。"""

    case_id: int
    case_code: str
    customer_name: str | None
    title: str | None
    created_at: datetime


class CaseListItem(CamelModel):
    """#1 案件一覧の1件。"""

    case_id: int
    case_code: str
    customer_name: str | None
    title: str | None
    created_at: datetime
    progress_status: ProgressStatus
    latest_version_id: int | None
    latest_sendoff: SendoffState | None
    # F-15: 最新の状態イベント（記録者・日時）と確認事項の残数・母数。版が無い案件は null。
    latest_state_event: StateEventRecord | None
    question_total: int | None = Field(ge=0)
    unresolved_count: int | None = Field(ge=0)


class CaseListResponse(CamelModel):
    cases: list[CaseListItem]
