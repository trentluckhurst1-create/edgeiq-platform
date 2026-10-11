import unittest

import pandas as pd

from scripts.research.run_issue16_predictive_diagnostics import race_metrics


class Issue16PredictiveDiagnosticsTests(unittest.TestCase):
    def test_race_metrics_uniform_comparison(self):
        df = pd.DataFrame(
            [
                {"race_key": "r1", "runner_key": "a", "y": 1, "p_model": 0.8},
                {"race_key": "r1", "runner_key": "b", "y": 0, "p_model": 0.2},
                {"race_key": "r2", "runner_key": "c", "y": 0, "p_model": 0.4},
                {"race_key": "r2", "runner_key": "d", "y": 1, "p_model": 0.6},
            ]
        )
        m = race_metrics(df)
        self.assertEqual(m["races"], 2)
        self.assertGreater(m["race_log_loss_gain_vs_uniform"], 0)
        self.assertEqual(m["top1"], 1.0)


if __name__ == "__main__":
    unittest.main()
