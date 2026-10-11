import unittest
from datetime import date

from scripts.research.build_issue10_pre2022_pit_partition import (
    compute_strict_prior_features,
    is_market_column,
    race_reason,
)


def row(race_date, race_key, runner_key, horse_key, winner=0, finish=2, trainer_key="T1", jockey_key="J1"):
    return {
        "race_date_obj": date.fromisoformat(race_date),
        "race_date": race_date,
        "year": int(race_date[:4]),
        "race_key": race_key,
        "runner_key": runner_key,
        "horse_key": horse_key,
        "trainer_key": trainer_key,
        "jockey_key": jockey_key,
        "winner": winner,
        "top3": int(finish <= 3),
        "finish_position": float(finish),
        "field_size": 2,
        "barrier": 1.0,
        "distance_metres": 1200.0,
        "weight": 57.0,
        "scratched": 0,
        "race_type_classification": "FLAT_PROVISIONAL",
    }


class Issue10PartitionTests(unittest.TestCase):
    def test_market_column_detection(self):
        self.assertTrue(is_market_column("starting_price_decimal"))
        self.assertTrue(is_market_column("final_SP"))
        self.assertFalse(is_market_column("race_date"))

    def test_same_date_rows_do_not_feed_prior_history(self):
        rows = [
            row("2020-01-01", "R1", "A", "H1", winner=1, finish=1),
            row("2020-01-01", "R2", "B", "H1", winner=0, finish=2),
            row("2020-01-02", "R3", "C", "H1", winner=0, finish=3),
        ]
        features = compute_strict_prior_features(rows)
        by_runner = {r["runner_key"]: r for r in features}
        self.assertEqual(by_runner["A"]["horse_prior_starts"], 0)
        self.assertEqual(by_runner["B"]["horse_prior_starts"], 0)
        self.assertEqual(by_runner["C"]["horse_prior_starts"], 2)
        self.assertEqual(by_runner["C"]["horse_prior_wins"], 1)

    def test_missing_jockey_id_is_distinct_from_no_prior_history(self):
        rows = [row("2020-01-01", "R1", "A", "H1", jockey_key="")]
        features = compute_strict_prior_features(rows)
        self.assertEqual(features[0]["jockey_id_missing"], 1)
        self.assertEqual(features[0]["jockey_prior_starts"], 0)
        self.assertEqual(features[0]["jockey_no_prior_history"], 0)

    def test_race_reason_detects_duplicate_and_bad_winner_count(self):
        rows = [
            row("2020-01-01", "R1", "A", "H1", winner=0, finish=2),
            row("2020-01-01", "R1", "A", "H2", winner=0, finish=3),
        ]
        reasons = race_reason(rows)
        self.assertIn("DUPLICATE_RUNNER_KEY_IN_RACE", reasons)
        self.assertIn("NOT_EXACTLY_ONE_WINNER", reasons)


if __name__ == "__main__":
    unittest.main()
