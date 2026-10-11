import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.research.run_issue8_pre2022_source_admission import (
    audit_runner_rows,
    classify_source_name,
    flagged_market_columns,
)


class Issue8SourceAdmissionTests(unittest.TestCase):
    def test_first_starter_artifacts_are_not_all_runner(self):
        status, reason = classify_source_name("canonical_strict_date_first_starter_universe_075f2.csv")
        self.assertEqual(status, "NOT_ALL_RUNNER")
        self.assertIn("First-starter", reason)

    def test_market_columns_are_forbidden(self):
        flagged = flagged_market_columns(["canonical_race_id", "final_SP", "runner_name", "bsp"])
        self.assertEqual(flagged, ["final_SP", "bsp"])

    def test_synthetic_runner_audit_fails_closed_on_sealed_year(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["race_id", "runner_id", "race_date", "winner"])
                writer.writeheader()
                writer.writerow({"race_id": "r1", "runner_id": "h1", "race_date": "2025-01-01", "winner": "1"})
            result = audit_runner_rows(path, max_allowed_date=date(2024, 12, 31))
        self.assertEqual(result["status"], "STOP")
        self.assertIn("MIXED_OR_SEALED_YEAR_ROW", result["reasons"])

    def test_synthetic_runner_audit_detects_duplicate_key_and_bad_winner_count(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rows.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["race_id", "runner_id", "race_date", "winner"])
                writer.writeheader()
                writer.writerow({"race_id": "r1", "runner_id": "h1", "race_date": "2020-01-01", "winner": "0"})
                writer.writerow({"race_id": "r1", "runner_id": "h1", "race_date": "2020-01-01", "winner": "0"})
            result = audit_runner_rows(path)
        self.assertEqual(result["status"], "STOP")
        self.assertIn("DUPLICATE_RUNNER_KEY", result["reasons"])
        self.assertIn("MISSING_OR_MULTIPLE_WINNERS", result["reasons"])


if __name__ == "__main__":
    unittest.main()
