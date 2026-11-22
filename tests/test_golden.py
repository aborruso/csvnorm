"""Golden tests: run csvnorm as a subprocess and compare outputs byte for byte."""

import csv
import io
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "fixtures" / "golden"
REJECT_COLUMNS = ("line", "column_idx", "column_name", "error_type")

CASES = tomllib.loads((GOLDEN / "cases.toml").read_text(encoding="utf-8"))["case"]


def run_case(case: dict, out_dir: Path) -> subprocess.CompletedProcess:
    """Run csvnorm on a golden case, writing into out_dir."""
    return subprocess.run(
        [
            sys.executable, "-m", "csvnorm",
            str(REPO / case["input"]),
            "-o", str(out_dir / f"{case['name']}.csv"),
            *case["args"],
        ],
        cwd=out_dir,
        capture_output=True,
    )


def reject_rows(path: Path) -> list[tuple[str, ...]]:
    """Reject file rows reduced to the columns that must not change."""
    reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    return [tuple(row[c] for c in REJECT_COLUMNS) for row in reader]


def _param(case: dict):
    marks = []
    if "xfail_until" in case:
        marks.append(
            pytest.mark.xfail(
                strict=True, reason=f"fixed in phase {case['xfail_until']}"
            )
        )
    return pytest.param(case, id=case["name"], marks=marks)


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_golden_case(case: dict, tmp_path: Path) -> None:
    result = run_case(case, tmp_path)
    assert result.returncode == case["exit_code"], result.stderr.decode()

    name = case["name"]
    output = tmp_path / f"{name}.csv"
    if case["output"]:
        expected = (GOLDEN / "expected" / f"{name}.csv").read_bytes()
        assert output.read_bytes() == expected
    else:
        assert not output.exists()

    rejects = tmp_path / f"{name}_reject_errors.csv"
    if case["rejects"]:
        expected_rejects = GOLDEN / "expected" / f"{name}_reject_errors.csv"
        assert reject_rows(rejects) == reject_rows(expected_rejects)
    else:
        assert not rejects.exists()
