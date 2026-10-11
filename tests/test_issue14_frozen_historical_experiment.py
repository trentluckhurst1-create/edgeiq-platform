import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.research.run_issue14_frozen_historical_experiment import (
    assert_probability_mass,
    stable_logit_softmax_by_race,
    validate_attestation,
    validate_execution_approval,
)


class Issue14FrozenExperimentTests(unittest.TestCase):
    def test_logit_softmax_mass(self):
        rows = [
            {"race_key": "r1", "runner_key": "a", "logit": 0.0},
            {"race_key": "r1", "runner_key": "b", "logit": 1.0},
            {"race_key": "r2", "runner_key": "c", "logit": -1.0},
        ]
        out = stable_logit_softmax_by_race(rows)
        assert_probability_mass(out)
        self.assertAlmostEqual(sum(r["p_model"] for r in out if r["race_key"] == "r1"), 1.0, places=15)
        self.assertEqual([r for r in out if r["race_key"] == "r2"][0]["p_model"], 1.0)

    def test_logit_softmax_monotonic_rank(self):
        rows = [
            {"race_key": "r1", "runner_key": "low", "logit": -2.0},
            {"race_key": "r1", "runner_key": "mid", "logit": 0.0},
            {"race_key": "r1", "runner_key": "high", "logit": 3.0},
        ]
        out = {r["runner_key"]: r["p_model"] for r in stable_logit_softmax_by_race(rows)}
        self.assertGreater(out["high"], out["mid"])
        self.assertGreater(out["mid"], out["low"])

    def test_logit_softmax_numerical_stability(self):
        rows = [
            {"race_key": "r1", "runner_key": "a", "logit": 1000.0},
            {"race_key": "r1", "runner_key": "b", "logit": 999.0},
            {"race_key": "r1", "runner_key": "c", "logit": -1000.0},
        ]
        out = stable_logit_softmax_by_race(rows)
        assert_probability_mass(out)
        self.assertTrue(all(math.isfinite(r["p_model"]) for r in out))

    def test_attestation_fails_closed_without_file(self):
        approved, reasons, data = validate_attestation(None)
        self.assertFalse(approved)
        self.assertIn("NO_ATTESTATION_PATH_SUPPLIED", reasons)
        self.assertEqual(data, {})

    def test_attestation_accepts_complete_approved_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "attestation.json"
            path.write_text(
                json.dumps(
                    {
                        "decision": "APPROVED",
                        "authorising_rights_holder_or_owner_role": "Owner",
                        "basis_or_terms": "Internal research authorisation",
                        "source_scope": "pre-2022 GraphQL monthly racing result files",
                        "approval_date": date.today().isoformat(),
                        "permitted_purpose": "historical research modelling",
                        "approval_evidence_reference": "signed-local-record-001",
                        "approval_evidence_sha256": "a" * 64,
                    }
                ),
                encoding="utf-8",
            )
            approved, reasons, _ = validate_attestation(path)
        self.assertTrue(approved)
        self.assertEqual(reasons, [])

    def test_execution_approval_requires_single_frozen_scope(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "execution.json"
            path.write_text(
                json.dumps(
                    {
                        "decision": "APPROVED_ONE_FROZEN_EXPERIMENT",
                        "approval_date": date.today().isoformat(),
                        "approval_reference": "https://github.example/pr#comment",
                        "scope": "single frozen experiment evaluating 2019 and 2020 separately",
                        "constraints": [
                            "no tuning",
                            "no market/SP/BSP data",
                            "no 2025-2026 access",
                            "no Stage011 changes",
                            "no production changes",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            approved, reasons, _ = validate_execution_approval(path)
        self.assertTrue(approved)
        self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
