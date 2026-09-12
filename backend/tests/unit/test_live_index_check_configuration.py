"""Live checker uses make-supplied connection targets without settings imports."""
from pathlib import Path
import runpy
from types import SimpleNamespace


def test_live_checker_uses_supplied_targets(monkeypatch):
    monkeypatch.setenv("INDEX_CONTAINER", "synthetic-container")
    monkeypatch.setenv("INDEX_USER", "synthetic-user")
    monkeypatch.setenv("INDEX_DEV_DATABASE", "synthetic-dev")
    monkeypatch.setenv(
        "INDEX_TEST_URL", "postgresql+psycopg://user:secret@localhost/synthetic-test"
    )
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["input"].startswith("BEGIN READ ONLY;")
        return SimpleNamespace(returncode=0, stdout="synthetic", stderr="")

    monkeypatch.setattr("subprocess.run", run)
    script = Path(__file__).resolve().parents[2] / "scripts/check_scan_index.py"
    runpy.run_path(str(script))["check_live_scan_index"]()
    assert [c[c.index("-d") + 1] for c in calls] == ["synthetic-dev", "synthetic-test"]
    assert all(
        c[3] == "synthetic-container" and c[c.index("-U") + 1] == "synthetic-user"
        for c in calls
    )
    assert all("secret" not in " ".join(c) for c in calls)
