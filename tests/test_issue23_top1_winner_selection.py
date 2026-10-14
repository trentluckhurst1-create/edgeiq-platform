from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "research"))

from run_issue23_top1_winner_selection import (  # noqa: E402
    BASELINE,
    STAGE016,
    apply_router,
    learn_router_policy,
    race_view,
    validate_scores,
)


def sample_scores():
    rows = []
    for model, probs in [(BASELINE, [0.6, 0.4]), (STAGE016, [0.4, 0.6])]:
        for horse, p, y in zip(["A", "B"], probs, [0, 1]):
            rows.append(
                {
                    "_race": "R1",
                    "_horse": horse,
                    "race_date": "2022-01-01",
                    "year": 2022,
                    "y": y,
                    "p": p,
                    "model_id": model,
                    "evidence_class": "TEST",
                }
            )
    return pd.DataFrame(rows)


def test_validate_scores_checks_probability_mass_and_winner_count():
    checks = validate_scores(sample_scores())
    assert checks[BASELINE]["single_winner_races"]
    assert checks[STAGE016]["max_probability_mass_error"] == 0.0


def test_race_view_uses_deterministic_horse_tie_break():
    scores = sample_scores()
    scores.loc[scores["model_id"].eq(BASELINE), "p"] = 0.5
    view = race_view(scores)
    selected = view[view["model_id"].eq(BASELINE)]["selected_horse"].iloc[0]
    assert selected == "A"


def test_router_defaults_to_stage011_when_slice_too_small():
    scores = sample_scores()
    view = race_view(scores)
    ctx = pd.DataFrame(
        {
            "_race": ["R1"],
            "year": [2022],
            "field_size_band": ["small_<=8"],
            "distance_band": ["sprint_<=1200"],
            "history_band": ["deep_hist_8+"],
        }
    )
    policy = learn_router_policy(view, ctx)
    routed = apply_router(scores, ctx, policy)
    assert len(routed) == 2
    np.testing.assert_allclose(
        routed.sort_values("_horse")["p"].to_numpy(),
        scores[scores["model_id"].eq(BASELINE)].sort_values("_horse")["p"].to_numpy(),
    )


if __name__ == "__main__":
    test_validate_scores_checks_probability_mass_and_winner_count()
    test_race_view_uses_deterministic_horse_tie_break()
    test_router_defaults_to_stage011_when_slice_too_small()
    print("ISSUE23_TESTS_PASS")
