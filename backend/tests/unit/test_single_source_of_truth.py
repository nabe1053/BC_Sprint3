"""「1箇所に集約する」と決めた資産が複製されていないことを機械的に検査する（memory CV-015）。

同じ指摘（二重化）が T-102 → T-202 で 2 度出た。レビュアーが目視で探すのではなく、
規約をテストで固定する（`test_api_path_separation.py` と同じ方針）。

集約先の正:
- 停止閾値・モデル識別子 … `app/agent/definition.py`（agent-development.md §1: definition は
  agent-plan.md の写し。片方だけ変えない）
- DomainError.code → HTTP status … `app/api/errors.py`（T-102 決定8）
- 保管ファイルのパス検証 … `app/repositories/document_storage.py` の `resolve_readable_path()`
"""

import re
import tokenize
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"

DEFINITION = APP_DIR / "agent" / "definition.py"
ERRORS = APP_DIR / "api" / "errors.py"
STORAGE = APP_DIR / "repositories" / "document_storage.py"


def _source_without_comments(path: Path) -> str:
    """コメント・docstring を空白で潰した実コードを返す。

    解説文を違反と誤検出しないために消す。**トークンを連結し直さず、元の行・桁のまま
    空白で潰す**（連結すると `document.storage_path` のような属性アクセスが分断され、
    検査が素通りする）。
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    blanked = [list(line) for line in lines]
    prev_type = tokenize.INDENT
    with path.open(encoding="utf-8") as fh:
        for tok in tokenize.generate_tokens(fh.readline):
            is_docstring = tok.type == tokenize.STRING and prev_type in (
                tokenize.INDENT,
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.DEDENT,
            )
            if tok.type == tokenize.COMMENT or is_docstring:
                (r1, c1), (r2, c2) = tok.start, tok.end
                for row in range(r1 - 1, r2):
                    line = blanked[row]
                    lo = c1 if row == r1 - 1 else 0
                    hi = c2 if row == r2 - 1 else len(line)
                    for col in range(lo, min(hi, len(line))):
                        if line[col] != "\n":
                            line[col] = " "
            if tok.type not in (tokenize.NL, tokenize.NEWLINE):
                prev_type = tok.type
    return "".join("".join(line) for line in blanked)


def _app_modules(exclude: Path) -> list[tuple[Path, str]]:
    return [
        (p, _source_without_comments(p))
        for p in sorted(APP_DIR.rglob("*.py"))
        if p != exclude and "__pycache__" not in p.parts
    ]


def test_dummy_model_id_is_only_defined_in_definition() -> None:
    """ダミー応答のモデル識別子を definition.py の外に直書きしない（RV-015 P1-2）。"""
    for path, source in _app_modules(exclude=DEFINITION):
        assert "mock-fixed" not in source, (
            f"モデル識別子が {path.relative_to(APP_DIR.parent)} に複製されている。"
            "`app.agent.definition.DUMMY_MODEL_ID` を注入して使うこと（CV-015）"
        )


def test_real_model_id_is_only_defined_in_definition() -> None:
    from app.agent import definition

    assert definition.MODEL_ID == "claude-sonnet-5"
    for path, source in _app_modules(exclude=DEFINITION):
        assert not re.search(r"claude-(?:sonnet|opus|haiku)-", source), path


def test_stop_thresholds_are_only_defined_in_definition() -> None:
    """停止閾値（max_turns / 各タイムアウト）を definition.py の外で数値リテラル指定しない。

    `RunLimits(...)` を数値リテラルで組み立てているモジュールを検出する。既定値は
    `definition.default_run_limits()` から取り、service 経由で注入する（RV-015 P1-2）。
    """
    from app.agent import definition

    plan = APP_DIR.parents[1] / "docs/requirements/agent-plan.md"
    approved = re.search(r"最大ターン数 \*\*(\d+)\*\*", plan.read_text())
    assert approved is not None
    assert definition.MAX_TURNS == int(approved.group(1))
    assert definition.default_run_limits().max_turns == definition.MAX_TURNS
    call = re.compile(r"RunLimits\s*\(([^)]*)\)", re.S)
    for path, source in _app_modules(exclude=DEFINITION):
        for args in call.findall(source):
            assert not re.search(r"=\s*\d+", args), (
                f"停止閾値が {path.relative_to(APP_DIR.parent)} で数値リテラル指定されている: "
                f"RunLimits({args.strip()})。"
                "`app.agent.definition.default_run_limits()` を使うこと（CV-015）"
            )


def test_domain_error_status_table_is_not_duplicated() -> None:
    """E_* → HTTP status の対応表を errors.py の外に作らない（RV-015 P2-3）。"""
    entry = re.compile(r"""["']E_[A-Z_]+["']\s*:\s*\d{3}""")
    for path, source in _app_modules(exclude=ERRORS):
        assert not entry.search(source), (
            f"エラーコード→HTTP status の対応が {path.relative_to(APP_DIR.parent)} にある。"
            "`app.api.errors.DOMAIN_ERROR_STATUS_BY_CODE` に集約すること（CV-015）"
        )


def test_cancel_grace_and_argument_digest_are_not_duplicated() -> None:
    definitions = []
    for path, source in _app_modules(exclude=DEFINITION):
        assert not re.search(r"CANCEL_[A-Z_]+\s*=\s*[0-9]", source), path
        if re.search(r"def digest_args\(", source):
            definitions.append(path.relative_to(APP_DIR).as_posix())
    assert definitions == ["agent/tools.py"]


def test_storage_path_validation_goes_through_the_gateway() -> None:
    """`storage_path` は `resolve_readable_path()` の引数としてしか現れない（RV-015 P2-5）。

    独自にパスを組み立てると `realpath` による脱出検査が抜け、
    `STORAGE_ROOT` の相対パス既定と合わさって CWD 依存で壊れる。
    「同じファイルのどこかで gateway も呼んでいる」では不十分なので、
    `.storage_path` の出現箇所そのものを検査する。
    """
    use = re.compile(r"[\w.]*\.storage_path\b")
    wrapped = re.compile(r"resolve_readable_path\s*\(\s*[\w.]*\.storage_path\b")
    for path, source in _app_modules(exclude=STORAGE):
        total = len(use.findall(source))
        if not total:
            continue
        assert total == len(wrapped.findall(source)), (
            f"{path.relative_to(APP_DIR.parent)} が storage_path を "
            "`resolve_readable_path()` を通さずに扱っている（CV-015）"
        )


def test_recovery_grace_and_predicate_are_shared() -> None:
    import ast
    from app.agent import definition
    from app.domain import run_types

    assert run_types.RECOVERY_GRACE_S == definition.RECOVERY_GRACE_S == 16
    for path, source in _app_modules(exclude=APP_DIR / "domain" / "run_types.py"):
        assert not re.search(r"RECOVERY_GRACE_S\s*=", source), path
    path = APP_DIR / "repositories" / "run_repository.py"
    tree = ast.parse(path.read_text())
    predicates = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_is_recoverable"
    ]
    assert len(predicates) == 1
    for name in ("recover_interrupted", "recover_expired"):
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == name
        )
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_is_recoverable"
            for node in ast.walk(method)
        )
        assert not any(
            isinstance(node, ast.Constant) and node.value == 16
            for node in ast.walk(method)
        )


def test_repositories_do_not_import_agent_layer() -> None:
    import ast

    for path in sorted((APP_DIR / "repositories").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not (
                    node.module == "app.agent"
                    or (node.module or "").startswith("app.agent.")
                ), path
                assert not (
                    node.module == "app"
                    and any(alias.name == "agent" for alias in node.names)
                ), path
            elif isinstance(node, ast.Import):
                assert not any(
                    alias.name == "app.agent" or alias.name.startswith("app.agent.")
                    for alias in node.names
                ), path


def test_recovery_grace_covers_terminal_persistence() -> None:
    from app.agent.definition import CANCEL_CLEANUP_S, RECOVERY_GRACE_S
    from app.agent.jobs import FINISH_TIMEOUT_S

    assert RECOVERY_GRACE_S > FINISH_TIMEOUT_S * 3 + 0.3 + CANCEL_CLEANUP_S


def test_current_state_has_only_initialization_and_event_writers():
    import ast

    writers = []
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        parents = {
            child: node
            for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        for node in ast.walk(tree):
            is_write = (
                isinstance(node, ast.Attribute)
                and node.attr == "current_state"
                and isinstance(node.ctx, ast.Store)
            )
            is_setattr = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "current_state"
            )
            if not (is_write or is_setattr):
                continue
            owner = parents.get(node)
            while owner is not None and not isinstance(
                owner, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                owner = parents.get(owner)
            writers.append(
                (str(path.relative_to(APP_DIR)), owner.name if owner else None)
            )
    assert sorted(writers) == [
        ("repositories/draft_repository.py", "complete"),
        ("repositories/record_repository.py", "save_state_event"),
    ]


def test_export_projection_has_no_float_round_or_duplicate_vocabulary():
    import ast

    for relative in (
        "domain/export_types.py",
        "services/export_workbook.py",
        "services/export_service.py",
    ):
        tree = ast.parse((APP_DIR / relative).read_text())
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls & {"float", "round"}, relative
    owners = []
    counters = []
    for path in APP_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "変更・確認記録":
                owners.append(str(path.relative_to(APP_DIR)))
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "unresolved_count"
            ):
                counters.append(str(path.relative_to(APP_DIR)))
    assert owners == ["domain/export_types.py"]
    assert counters == ["services/version_state.py"]
