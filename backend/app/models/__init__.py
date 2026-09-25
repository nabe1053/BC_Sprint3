"""ORM モデル集約。

Foundation（Slice 0-3）で作るのは9テーブルのみ（CLAUDE.md 指示）。
残り（C層の他テーブル・D層の人の記録）は build-loop のスライスで積み上げる。
"""

from app.models.approvals import (
    VersionStateEvent,
    Bounce,
    BounceComment,
    SendoffDecision,
)
from app.models.exports import Export
from app.models.agent_runs import AgentRun, AgentRunStep
from app.models.base import TimestampedBase
from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.models.rule_sets import RuleSet
from app.models.records import (
    ItemEdit,
    Confirmation,
    QuestionJudgement,
    DocumentExclusion,
)
from app.models.versions import Version

__all__ = [
    "ItemEdit",
    "Confirmation",
    "QuestionJudgement",
    "DocumentExclusion",
    "TimestampedBase",
    "Case",
    "Document",
    "DocumentPage",
    "EmailPart",
    "DocumentIssue",
    "RuleSet",
    "AgentRun",
    "AgentRunStep",
    "Version",
]

from app.models.drafts import (
    CaseHeader,
    Item,
    ItemEnd,
    Evidence,
    Question,
    InventoryEntry,
    InventoryLink,
)

__all__ += [
    "CaseHeader",
    "Item",
    "ItemEnd",
    "Evidence",
    "Question",
    "InventoryEntry",
    "InventoryLink",
]

__all__ += ["VersionStateEvent", "Bounce", "BounceComment", "SendoffDecision"]


__all__ += ["Export"]
