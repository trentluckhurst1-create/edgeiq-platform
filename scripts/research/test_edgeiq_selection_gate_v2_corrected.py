"""Parameterized synthetic contract tests for EDGEiQ selection gate V2.

No real odds, no outcomes, no execution.
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


ENGINE = Path(__file__).with_name("run_edgeiq_selection_gate_v2.py")
COLUMNS = [
    "race_id",
    "runner_id",
    "snapshot_id",
    "snapshot_time",
    "scheduled_start_time",
    "quote_timestamp",
    "market_source",
    "provider",
    "quote_certified",
    "model_id",
    "model_version",
    "model_snapshot_id",
    "model_snapshot_sha256",
    "feature_manifest_sha256",
    "model_probability",
    "probability_certified",
    "data_certified",
    "commission_rate",
    "back_quote_type",
    "back_odds",
    "back_available",
    "lay_quote_type",
    "lay_odds",
    "lay_available",
]

BASE = {
    "race_id": "R1",
    "snapshot_time": "2026-10-14T01:00:00Z",
    "scheduled_start_time": "2026-10-14T02:00:00Z",
    "quote_timestamp": "2026-10-14T00:59:30Z",
    "market_source": "BETFAIR_EXCHANGE",
    "provider": "BETFAIR",
    "quote_certified": "true",
    "model_id": "stage011",
    "model_version": "research",
    "model_snapshot_id": "MODEL_SNAPSHOT_001",
    "model_snapshot_sha256": "a" * 64,
    "feature_manifest_sha256": "b" * 64,
    "model_probability": ".4",
    "probability_certified": "true",
    "data_certified": "true",
    "commission_rate": ".05",
    "back_quote_type": "BETFAIR_BACK",
    "back_odds": "4.0",
    "back_available": "100",
    "lay_quote_type": "BETFAIR_LAY",
    "lay_odds": "4.2",
    "lay_available": "100",
}


def case(name: str, **overrides: str) -> dict[str, str]:
    row = {**BASE, "runner_id": name, "snapshot_id": f"SNAP_{name}", **overrides}
    return row


CASES = [
    (
        case("BACK_VALUE", model_probability=".4", back_odds="4.0", lay_odds="4.2"),
        "RESEARCH_CANDIDATE",
        "NO_VALUE",
        "PASS",
        "PASS",
    ),
    (
        case("LAY_VALUE", model_probability=".2", back_odds="3.0", lay_odds="3.5"),
        "NO_VALUE",
        "RESEARCH_CANDIDATE",
        "PASS",
        "PASS",
    ),
    (
        case("NO_VALUE", model_probability=".3", back_odds="2.0", lay_odds="4.0"),
        "NO_VALUE",
        "NO_VALUE",
        "PASS",
        "PASS",
    ),
    (
        case("UNCERTIFIED", probability_certified="false"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "CERTIFICATION_FAIL",
        "CERTIFICATION_FAIL",
    ),
    (
        case("MISSING_ODDS", back_odds="", lay_odds=""),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "BACK_QUOTE_INVALID",
        "LAY_QUOTE_INVALID",
    ),
    (
        case("INVALID_DEPTH", back_available="-1", lay_available="-1"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "BACK_QUOTE_INVALID",
        "LAY_QUOTE_INVALID",
    ),
    (
        case("LOW_LIQUIDITY", back_available="1", lay_available="1"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "BACK_LIQUIDITY_FAIL",
        "LAY_LIQUIDITY_FAIL",
    ),
    (
        case("LAY_LIABILITY_FAIL", model_probability=".2", back_odds="2.0", lay_odds="6.0"),
        "NO_VALUE",
        "FAIL_CLOSED",
        "PASS",
        "LAY_LIABILITY_FAIL",
    ),
    (
        case("STALE_QUOTE", quote_timestamp="2026-10-14T00:55:00Z"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "TIMESTAMP_FAIL",
        "TIMESTAMP_FAIL",
    ),
    (
        case("INVALID_TIMESTAMP", snapshot_time="2026-10-14T02:00:00Z"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "TIMESTAMP_FAIL",
        "TIMESTAMP_FAIL",
    ),
    (
        case("CROSSED_EXCHANGE", back_odds="4.3", lay_odds="4.2"),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "CROSSED_EXCHANGE_QUOTE",
        "CROSSED_EXCHANGE_QUOTE",
    ),
    (
        case(
            "BOOKMAKER_BACK_ONLY",
            market_source="BOOKMAKER_FIXED_WIN",
            provider="BOOKMAKER_X",
            back_quote_type="BOOKMAKER_FIXED_WIN",
            lay_quote_type="",
            lay_odds="",
            lay_available="",
        ),
        "RESEARCH_CANDIDATE",
        "FAIL_CLOSED",
        "PASS",
        "LAY_REQUIRES_BETFAIR_EXCHANGE",
    ),
    (
        case("MISSING_PROVIDER", provider=""),
        "FAIL_CLOSED",
        "FAIL_CLOSED",
        "SOURCE_PROVIDER_FAIL",
        "SOURCE_PROVIDER_FAIL",
    ),
]


def run_gate(rows: list[dict[str, str]], extra_args: list[str] | None = None):
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        inp = temp / "synthetic.csv"
        out = temp / "classified.csv"
        audit = temp / "audit.json"
        paper = temp / "paper_log.csv"
        with inp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        cmd = [
            sys.executable,
            str(ENGINE),
            "--input",
            str(inp),
            "--output",
            str(out),
            "--audit",
            str(audit),
            "--paper-log",
            str(paper),
            "--min-depth",
            "30",
            "--max-lay-liability",
            "100",
            "--max-quote-age-seconds",
            "60",
        ]
        if extra_args:
            cmd.extend(extra_args)
        run = subprocess.run(cmd, capture_output=True, text=True)
        if run.returncode:
            raise AssertionError(run.stdout + "\n" + run.stderr)
        with out.open(newline="", encoding="utf-8") as handle:
            classified = {row["runner_id"]: row for row in csv.DictReader(handle)}
        with paper.open(newline="", encoding="utf-8") as handle:
            paper_rows = list(csv.DictReader(handle))
        return classified, paper_rows


def assert_contains(value: str, expected: str) -> None:
    if expected == "PASS":
        assert value == "PASS", value
    else:
        assert expected in value.split("|"), value


def test_parameterized_cases() -> None:
    rows = [row for row, *_ in CASES]
    classified, paper_rows = run_gate(rows)
    assert len(paper_rows) == len(rows)
    assert len({r["paper_event_id"] for r in paper_rows}) == len(rows)
    for row, back_status, lay_status, back_reason, lay_reason in CASES:
        result = classified[row["runner_id"]]
        assert result["back_status"] == back_status, (row["runner_id"], result)
        assert result["lay_status"] == lay_status, (row["runner_id"], result)
        assert_contains(result["back_reason_codes"], back_reason)
        assert_contains(result["lay_reason_codes"], lay_reason)
        assert result["execution_authorized"] == "False"
        assert result["research_only"] == "True"
    assert abs(float(classified["BACK_VALUE"]["back_ev_per_stake"]) - 0.54) < 1e-10
    assert abs(float(classified["LAY_VALUE"]["lay_ev_per_liability"]) - 0.104) < 1e-10


def test_duplicate_snapshot_fails_closed() -> None:
    first = case("DUP_A", snapshot_id="DUP")
    second = case("DUP_B", snapshot_id="DUP")
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "dups.csv"
        out = Path(td) / "out.csv"
        with inp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows([first, second])
        run = subprocess.run(
            [sys.executable, str(ENGINE), "--input", str(inp), "--output", str(out)],
            capture_output=True,
            text=True,
        )
        assert run.returncode != 0
        assert "duplicate snapshot_id" in run.stderr


def test_forbidden_outcome_column_fails_closed() -> None:
    row = case("FORBIDDEN")
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "forbidden.csv"
        out = Path(td) / "out.csv"
        columns = COLUMNS + ["winner"]
        with inp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerow({**row, "winner": "1"})
        run = subprocess.run(
            [sys.executable, str(ENGINE), "--input", str(inp), "--output", str(out)],
            capture_output=True,
            text=True,
        )
        assert run.returncode != 0
        assert "outcomes" in run.stderr


def main() -> None:
    test_parameterized_cases()
    test_duplicate_snapshot_fails_closed()
    test_forbidden_outcome_column_fails_closed()
    print("EDGEIQ SELECTION GATE V2: PASS")
    print("SYNTHETIC_CASES", len(CASES))
    print("NO_REAL_ODDS; NO_OUTCOMES; NO_EXECUTION")


if __name__ == "__main__":
    main()
