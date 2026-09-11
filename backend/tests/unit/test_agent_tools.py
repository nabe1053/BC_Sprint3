"""agent-plan.md ツール一覧（13点）との対応を検査する。

これらは決定的関数であり、単体テストの対象にする（CLAUDE.md「エージェントループは
単体テストしない。ツール=決定的関数のみが対象」）。
"""

from app.agent import tools

EXPECTED_AGENT_TOOL_NAMES = {
    "list_case_documents",
    "read_document",
    "read_email",
    "search_documents",
    "get_rules",
    "record_case_header",
    "propose_items",
    "record_evidence",
    "record_question",
    "record_source_inventory",
    "report_unreadable",
    "validate_draft",
    "finalize_draft",
}

FORBIDDEN_TOOL_NAMES = {
    # 人の記録・出力・案件作成/資料投入/起動/監視は登録しない（05-api-ipo.md 7章）
    "record_edit",
    "record_confirmation",
    "record_judgement",
    "record_state_event",
    "record_bounce",
    "record_sendoff_decision",
    "export_xlsx",
    "create_case",
    "upload_documents",
    "start_agent_run",
}


def test_agent_tools_match_agent_plan_13() -> None:
    names = {t.name for t in tools.AGENT_TOOLS}
    assert names == EXPECTED_AGENT_TOOL_NAMES
    assert len(tools.AGENT_TOOLS) == 13


def test_no_forbidden_tools_registered() -> None:
    names = {t.name for t in tools.ALL_TOOLS}
    assert names.isdisjoint(FORBIDDEN_TOOL_NAMES)


def test_allowed_tool_names_are_namespaced() -> None:
    for name in tools.ALLOWED_TOOL_NAMES:
        assert name.startswith("mcp__app__")
