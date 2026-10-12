import unittest

import pandas as pd

from scripts.research.run_issue18_eight_race_sensitivity import race_frame


class Issue18SensitivityTests(unittest.TestCase):
    def test_race_frame_ll_gain(self):
        df = pd.DataFrame(
            [
                {"race_key": "1", "runner_key": "a", "y": 1, "p_model": 0.7},
                {"race_key": "1", "runner_key": "b", "y": 0, "p_model": 0.3},
            ]
        )
        out = race_frame(df)
        self.assertEqual(len(out), 1)
        self.assertGreater(float(out.loc[0, "ll_gain_vs_uniform"]), 0)


if __name__ == "__main__":
    unittest.main()
