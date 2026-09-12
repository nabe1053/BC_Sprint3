"""The public make gate must fail before pytest can hide a missing live index."""
from pathlib import Path
import subprocess


def test_missing_live_index_blocks_backend_gate_before_pytest(tmp_path):
    root = Path(__file__).resolve().parents[3]
    override = tmp_path / "probe.mk"
    override.write_text(
        "db migrate be-lint:\n\t@true\n"
        "be-test:\n\t@echo PYTEST_MUST_NOT_RUN\n"
        "check-run-step-index:\n\t@echo synthetic-index-missing\n\t@exit 17\n"
    )
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            str(root / "Makefile"),
            "-f",
            str(override),
            "check-be",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, result.stdout
    assert "synthetic-index-missing" in result.stdout
    assert "PYTEST_MUST_NOT_RUN" not in result.stdout
