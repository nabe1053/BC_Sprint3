"""カスタムツール群: docs/requirements/agent-plan.md「ツール一覧」（13点）と1対1で対応する。

登録するのはこの13本だけ（05-api-ipo.md 7章）。人の記録 API（29〜37）・出力 API（38〜40）・
案件作成／資料投入／起動／監視（1・2・3・5・10・12・13・14）は**登録しない**。
これが「AI が確認者名や日時を作らない」（02-requirement.md 7章）の構造的な担保になる。

Foundation（Slice 0-7）では、各ツールは `/agent/*` API 実装前のためダミー応答を返す
スタブとして実装する（D05 未承認: 初版はローカル読取＋ダミー応答。CLAUDE.md 決定事項3）。
build-loop のエージェントスライスが、各スタブの中身を repository/service 経由の実装に
差し替える（tools は決定的関数として単体テストの対象にする）。
"""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


def _stub(message: str, **data: Any) -> dict[str, Any]:
    payload = {"stub": True, "message": message, **data}
    return {"content": [{"type": "text", "text": str(payload)}]}


# --- read ツール（05-api-ipo.md 4・6・7・8・11 に対応） ---


@tool(
    "list_case_documents",
    "案件の資料一覧と読取状態を得る（API 4: GET /cases/{id}/documents）",
    {"case_id": str},
)
async def list_case_documents(args: dict[str, Any]) -> dict[str, Any]:
    return _stub(
        "list_case_documents は未実装（build-loop で /agent/... に接続）", **args
    )


@tool(
    "read_document",
    "テキストPDF・.xlsx の本文・表・注記を読む（API 6: GET /documents/{id}/content）",
    {"document_id": str, "range": str},
)
async def read_document(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("read_document は未実装", **args)


@tool(
    "read_email",
    ".eml の構造を保持して読む（API 7: GET /documents/{id}/email）",
    {"document_id": str},
)
async def read_email(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("read_email は未実装", **args)


@tool(
    "search_documents",
    "案件内の参照解決（本文3.2項による等）（API 8: GET /cases/{id}/search）",
    {"case_id": str, "query": str},
)
async def search_documents(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("search_documents は未実装", **args)


@tool(
    "get_rules",
    "表記・単位・分割規則 R01〜R08 と論理項目定義を取得（API 11: GET /rule-sets/{v}）",
    {"rule_version": str},
)
async def get_rules(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("get_rules は未実装", **args)


# --- write ツール（05-api-ipo.md 15〜19・21 に対応。当該版への追記のみ） ---


@tool(
    "record_case_header",
    "案件情報を原文の粒度で登録する（API 15: POST /versions/{id}/header）",
    {"version_id": str, "header": dict},
)
async def record_case_header(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("record_case_header は未実装", **args)


@tool(
    "propose_items",
    "明細行を登録する。原項番・出典・状態が必須（API 16: POST /versions/{id}/items）",
    {"version_id": str, "rows": list},
)
async def propose_items(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("propose_items は未実装", **args)


@tool(
    "record_evidence",
    "項目ごとの根拠を登録する（API 17: POST /versions/{id}/items/{itemId}/evidence）",
    {"version_id": str, "item_id": str, "evidence": dict},
)
async def record_evidence(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("record_evidence は未実装", **args)


@tool(
    "record_question",
    "確認事項を対象つきで登録する（API 18: POST /versions/{id}/questions）",
    {"version_id": str, "question": dict},
)
async def record_question(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("record_question は未実装", **args)


@tool(
    "record_source_inventory",
    "原明細インベントリと対応関係を登録する（API 19: POST /versions/{id}/inventory）",
    {"version_id": str, "entries": list},
)
async def record_source_inventory(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("record_source_inventory は未実装", **args)


@tool(
    "report_unreadable",
    "読取不能・未走査の範囲を記録する（API 9: POST /documents/{id}/issues）",
    {"document_id": str, "range": str, "reason": str},
)
async def report_unreadable(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("report_unreadable は未実装", **args)


@tool(
    "validate_draft",
    "完了条件の機械判定を実行し違反一覧を得る（API 20: GET /versions/{id}/validation）",
    {"version_id": str},
)
async def validate_draft(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("validate_draft は未実装", violations=[], **args)


@tool(
    "finalize_draft",
    "版を作成案として確定する（API 21: POST /versions/{id}/finalize）",
    {"version_id": str},
)
async def finalize_draft(args: dict[str, Any]) -> dict[str, Any]:
    return _stub("finalize_draft は未実装", **args)


# 疎通確認専用（build-loop が実ツールを揃えるまでの smoke test 用）。
# 13ツールには数えない。
@tool("ping", "疎通確認用。メッセージをそのまま返す", {"message": str})
async def ping(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"pong: {args['message']}"}]}


# agent-plan.md ツール一覧の13点。
AGENT_TOOLS = [
    list_case_documents,
    read_document,
    read_email,
    search_documents,
    get_rules,
    record_case_header,
    propose_items,
    record_evidence,
    record_question,
    record_source_inventory,
    report_unreadable,
    validate_draft,
    finalize_draft,
]

# ping は疎通テスト専用（本番のツール一覧には含めない）。
ALL_TOOLS = [*AGENT_TOOLS, ping]

agent_server = create_sdk_mcp_server(name="app", version="1.0.0", tools=ALL_TOOLS)

# allowed_tools に渡す名前（mcp__{server}__{tool}）。
AGENT_TOOL_NAMES = [f"mcp__app__{t.name}" for t in AGENT_TOOLS]
ALLOWED_TOOL_NAMES = [*AGENT_TOOL_NAMES, "mcp__app__ping"]
