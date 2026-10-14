"""Synthetic readiness-adapter tests for EDGEiQ selection gate V2.

No real odds, no outcomes, no execution.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


READINESS = Path(__file__).with_name("run_edgeiq_selection_gate_v2_readiness.py")
GATE = Path(__file__).with_name("run_edgeiq_selection_gate_v2.py")
MODEL_SHA = "a" * 64


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path) -> None:
    manifest = {
        "status": "RESEARCH_ONLY_UNVALIDATED",
        "training_year_max": 2024,
        "training_rows": 91434,
        "features": ["f1", "f2"],
        "stage011_sha256": MODEL_SHA,
        "no_market": True,
        "no_production_promotion": True,
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def run_readiness(model_rows: list[dict], quote_rows: list[dict]):
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        manifest = temp / "manifest.json"
        model = temp / "stage011.csv"
        quotes = temp / "quotes.csv"
        v2 = temp / "v2.csv"
        audit = temp / "audit.json"
        write_manifest(manifest)
        write_csv(model, model_rows)
        write_csv(quotes, quote_rows)
        run = subprocess.run(
            [
                sys.executable,
                str(READINESS),
                "--stage011-output",
                str(model),
                "--quote-snapshots",
                str(quotes),
                "--artifact-manifest",
                str(manifest),
                "--v2-input-output",
                str(v2),
                "--audit",
                str(audit),
            ],
            capture_output=True,
            text=True,
        )
        if run.returncode:
            raise AssertionError(run.stdout + "\n" + run.stderr)
        audit_obj = json.loads(audit.read_text(encoding="utf-8"))
        rows = []
        if v2.read_text(encoding="utf-8").strip():
            with v2.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        return rows, audit_obj


def model_rows() -> list[dict]:
    return [
        {
            "race_id": "R1",
            "runner_id": "H1",
            "scoring_timestamp": "2026-10-14T01:00:00Z",
            "scheduled_start_time": "2026-10-14T02:00:00Z",
            "stage011_probability": "0.4",
            "champion_model_sha256": MODEL_SHA,
        },
        {
            "race_id": "R1",
            "runner_id": "H2",
            "scoring_timestamp": "2026-10-14T01:00:00Z",
            "scheduled_start_time": "2026-10-14T02:00:00Z",
            "stage011_probability": "0.6",
            "champion_model_sha256": MODEL_SHA,
        },
    ]


def quote_rows() -> list[dict]:
    base = {
        "quote_timestamp": "2026-10-14T01:00:20Z",
        "scheduled_start_time": "2026-10-14T02:00:00Z",
        "market_status": "OPEN",
        "in_play": "false",
        "suspended": "false",
        "commission_rate": "0.05",
    }
    return [
        {
            **base,
            "race_id": "R1",
            "runner_id": "H1",
            "quote_snapshot_id": "Q1",
            "market_source": "BOOKMAKER_FIXED_WIN",
            "provider": "BOOKMAKER_X",
            "quote_side": "BACK",
            "quote_type": "BOOKMAKER_FIXED_WIN",
            "odds": "4.0",
            "available_amount": "100",
        },
        {
            **base,
            "race_id": "R1",
            "runner_id": "H2",
            "quote_snapshot_id": "Q2",
            "market_source": "BETFAIR_EXCHANGE",
            "provider": "BETFAIR",
            "quote_side": "BACK",
            "quote_type": "BETFAIR_BACK",
            "odds": "1.8",
            "available_amount": "100",
        },
        {
            **base,
            "race_id": "R1",
            "runner_id": "H2",
            "quote_snapshot_id": "Q2",
            "market_source": "BETFAIR_EXCHANGE",
            "provider": "BETFAIR",
            "quote_side": "LAY",
            "quote_type": "BETFAIR_LAY",
            "odds": "1.9",
            "available_amount": "100",
        },
    ]


def test_readiness_builds_v2_contract_and_gate_accepts_partial_sides() -> None:
    rows, audit = run_readiness(model_rows(), quote_rows())
    assert audit["joined_v2_rows"] == 2, audit
    assert audit["blocker_count"] == 0, audit
    assert len(rows) == 2
    by_runner = {row["runner_id"]: row for row in rows}
    assert by_runner["H1"]["back_quote_type"] == "BOOKMAKER_FIXED_WIN"
    assert by_runner["H1"]["lay_quote_type"] == ""
    assert by_runner["H1"]["probability_certified"] == "True"

    with tempfile.TemporaryDirectory() as td:
        v2 = Path(td) / "v2.csv"
        write_csv(v2, rows)
        out = Path(td) / "classified.csv"
        run = subprocess.run(
            [
                sys.executable,
                str(GATE),
                "--input",
                str(v2),
                "--output",
                str(out),
                "--min-depth",
                "30",
                "--max-lay-liability",
                "100",
                "--max-quote-age-seconds",
                "60",
            ],
            capture_output=True,
            text=True,
        )
        if run.returncode:
            raise AssertionError(run.stdout + "\n" + run.stderr)
        with out.open(newline="", encoding="utf-8") as handle:
            classified = {row["runner_id"]: row for row in csv.DictReader(handle)}
        assert classified["H1"]["back_status"] == "RESEARCH_CANDIDATE"
        assert classified["H1"]["lay_status"] == "FAIL_CLOSED"
        assert "LAY_QUOTE_INVALID" in classified["H1"]["lay_reason_codes"]


def test_blockers_for_mismatched_ids_suspended_market_and_duplicate_quotes() -> None:
    quotes = quote_rows()
    quotes[0]["runner_id"] = "H9"
    quotes[1]["suspended"] = "true"
    quotes.append(dict(quotes[2]))
    rows, audit = run_readiness(model_rows(), quotes)
    assert rows == []
    reasons = audit["blocker_reason_counts"]
    assert reasons["quote_snapshot:QUOTE_SUSPENDED"] == 1, reasons
    assert reasons["quote_snapshot:DUPLICATE_QUOTE_SIDE"] == 2, reasons
    assert reasons["join:MISSING_QUOTE_FOR_MODEL_RUNNER"] >= 1, reasons
    assert reasons["join:QUOTE_WITHOUT_MODEL_RUNNER"] >= 1, reasons


def test_missing_required_model_field_blocks_without_exception() -> None:
    rows = model_rows()
    for row in rows:
        row.pop("champion_model_sha256")
    out, audit = run_readiness(rows, quote_rows())
    assert out == []
    assert audit["blocker_reason_counts"]["model_output:MISSING_REQUIRED_FIELDS"] == 1, audit


def main() -> None:
    test_readiness_builds_v2_contract_and_gate_accepts_partial_sides()
    test_blockers_for_mismatched_ids_suspended_market_and_duplicate_quotes()
    test_missing_required_model_field_blocks_without_exception()
    print("EDGEIQ SELECTION GATE V2 READINESS: PASS")
    print("NO_REAL_ODDS; NO_OUTCOMES; NO_EXECUTION")


if __name__ == "__main__":
    main()
