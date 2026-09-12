"""`/api/v1/agent/*` と `/api/v1/ui/*` のパス分離を検査する（05-api-ipo.md 7.1）。

認証を実装しないため（CLAUDE.md 決定事項1）、「AGENT-01 が人の記録 API を呼べない」境界は
ツール登録とパス分離だけで守られる。分離が崩れたことを機械的に検出する。
"""

from app.main import API_V1, app

# 人の記録・出力（05-api-ipo.md F群 29〜37・G群 38〜40）を示す語。
# これらが /agent/* 配下に現れたら、認可の無い本構成では AI が人の記録を書ける状態になる。
UI_ONLY_SEGMENTS = (
    "agent-runs",
    "edits",
    "confirmations",
    "judgements",
    "state-events",
    "bounces",
    "bounce-comments",
    "sendoff-decisions",
    "exports",
)


def _paths() -> list[str]:
    return [r.path for r in app.routes if hasattr(r, "methods")]


def test_all_api_paths_are_versioned() -> None:
    """/agent /ui /health はすべて /api/v1 配下にある（版プレフィックスの一元化）。"""
    for p in _paths():
        if p in ("/", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
            continue
        assert p.startswith(f"{API_V1}/"), f"版プレフィックスが無い: {p}"


def test_agent_and_ui_are_separated() -> None:
    """業務 API は /api/v1/agent/* か /api/v1/ui/* のどちらかに属する。"""
    for p in _paths():
        if not p.startswith(f"{API_V1}/") or p == f"{API_V1}/health":
            continue
        assert p.startswith(f"{API_V1}/agent/") or p.startswith(
            f"{API_V1}/ui/"
        ), f"agent/ui のどちらにも属さない業務 API: {p}"


def test_human_record_apis_are_not_under_agent() -> None:
    """人の記録・出力の API が /agent/* 配下に無い（05-api-ipo.md 7.1・02 7章）。"""
    agent_paths = [p for p in _paths() if p.startswith(f"{API_V1}/agent/")]
    for p in agent_paths:
        for seg in UI_ONLY_SEGMENTS:
            assert seg not in p, f"人の記録 API が /agent/* に置かれている: {p}"
