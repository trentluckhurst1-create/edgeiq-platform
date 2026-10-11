import unittest

from scripts.research.run_issue12_grok_readiness_gates import (
    cohort_for_year,
    is_missing,
    norm,
)


class Issue12ReadinessGateTests(unittest.TestCase):
    def test_cohort_protocol_years_are_frozen(self):
        self.assertEqual(cohort_for_year(2018), "TRAIN_ELIGIBLE_COMPLETE_YEARS_LE_2018")
        self.assertEqual(cohort_for_year(2016), "SPARSE_HISTORY_ONLY_EXCLUDED_FROM_TRAIN_EVAL")
        self.assertEqual(cohort_for_year(2019), "EVAL_2019")
        self.assertEqual(cohort_for_year(2020), "EVAL_2020")
        self.assertEqual(cohort_for_year(2021), "REUSED_DEVELOPMENT_NOT_INDEPENDENT")

    def test_missing_numeric_detection(self):
        self.assertTrue(is_missing(""))
        self.assertTrue(is_missing("NaN"))
        self.assertFalse(is_missing("0"))
        self.assertFalse(is_missing("57.5"))

    def test_normalisation_is_stable(self):
        self.assertEqual(norm("  A. Horse's Name  "), "A_HORSE_S_NAME")


if __name__ == "__main__":
    unittest.main()
