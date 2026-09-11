"""T-102 のパス分離契約（05-api-ipo.md 0.3・決定6）。

`tests/unit/test_api_path_separation.py` は汎用の機械検査（版プレフィックス一元化・
agent/ui のどちらかに属す・人の記録 API が /agent/* に無い）を行う。**そのテストは
変更しない。** 本ファイルは T-102 で実装する #1〜#10 の**個別エンドポイント**が
決定6のとおりに配置されていることを検査する。

決定6:
    UI のみ:    #1, #2, #3, #5, #10
    AGENT のみ: #8, #9
    両方:       #4, #6, #7
"""

from app.main import API_V1, app


def _paths() -> set[str]:
    return {r.path for r in app.routes if hasattr(r, "methods")}


def _routes() -> list[tuple[str, set[str]]]:
    return [(r.path, r.methods) for r in app.routes if hasattr(r, "methods")]


def test_case_and_intake_and_file_endpoints_are_ui_only() -> None:
    """#1,#2,#3,#5,#10 が /agent/* に存在しない。

    パラメータ名の揺れ（case_id / caseId 等）を吸収するため、固定パス文字列の
    完全一致ではなく prefix/suffix で判定する。#4（資料一覧）は UI/AGENT 両方に
    存在してよいためこの検査の対象外。
    """
    paths = _paths()

    assert (
        f"{API_V1}/agent/cases" not in paths
    ), "#1/#2（案件一覧・作成）が /agent/* に存在する"

    assert not any(
        p.startswith(f"{API_V1}/agent/cases/")
        and "/" not in p[len(f"{API_V1}/agent/cases/") :]
        for p in paths
    ), "#3（案件詳細）が /agent/* に存在する"

    assert not any(
        p.startswith(f"{API_V1}/agent/documents/") and p.endswith("/file")
        for p in paths
    ), "#10（原ファイル取得）が /agent/* 配下に存在してはならない（UI 専用）"

    assert not any(
        p.startswith(f"{API_V1}/agent/cases/")
        and p.endswith("/documents")
        and "POST" in methods
        for p, methods in _routes()
    ), "#5（資料投入 POST）が /agent/* 配下に存在してはならない（UI 専用）"


def test_search_and_issues_endpoints_are_agent_only() -> None:
    """#8,#9 が /ui/* に存在しない。"""
    paths = _paths()
    assert not any(
        p.startswith(f"{API_V1}/ui/cases/") and p.endswith("/search") for p in paths
    ), "#8（検索）が /ui/* 配下に存在してはならない（AGENT 専用）"
    assert not any(
        p.startswith(f"{API_V1}/ui/documents/") and p.endswith("/issues") for p in paths
    ), "#9（読取不能記録）が /ui/* 配下に存在してはならない（AGENT 専用）"


def test_reference_endpoints_exist_under_both_ui_and_agent() -> None:
    """#4,#6,#7 が /ui/* と /agent/* の両方に存在する。"""
    paths = _paths()

    documents_ui = any(
        p.startswith(f"{API_V1}/ui/cases/") and p.endswith("/documents") for p in paths
    )
    documents_agent = any(
        p.startswith(f"{API_V1}/agent/cases/") and p.endswith("/documents")
        for p in paths
    )
    assert documents_ui, "#4 資料一覧が /ui/* 配下に存在しない"
    assert documents_agent, "#4 資料一覧が /agent/* 配下に存在しない"

    content_ui = any(
        p.startswith(f"{API_V1}/ui/documents/") and p.endswith("/content")
        for p in paths
    )
    content_agent = any(
        p.startswith(f"{API_V1}/agent/documents/") and p.endswith("/content")
        for p in paths
    )
    assert content_ui, "#6 本文取得が /ui/* 配下に存在しない"
    assert content_agent, "#6 本文取得が /agent/* 配下に存在しない"

    email_ui = any(
        p.startswith(f"{API_V1}/ui/documents/") and p.endswith("/email") for p in paths
    )
    email_agent = any(
        p.startswith(f"{API_V1}/agent/documents/") and p.endswith("/email")
        for p in paths
    )
    assert email_ui, "#7 メール構造が /ui/* 配下に存在しない"
    assert email_agent, "#7 メール構造が /agent/* 配下に存在しない"
