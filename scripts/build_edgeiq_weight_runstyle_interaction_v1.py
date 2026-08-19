from edgeiq_interaction_signal_common_v1 import evaluate_module, standard_race_relative_adjustment

MODULE = "EDGEIQ_WEIGHT_RUNSTYLE_INTERACTION_V1"
SLUG = "edgeiq_weight_runstyle_interaction_v1"
PER_KG = {
    "LEADER": 1.10,
    "ON_PACE": 1.00,
    "MIDFIELD": 0.90,
    "BACKMARKER": 0.85,
    "UNKNOWN": 0.75,
}


def context_band(race, original_top, adjusted_top, rows):
    return original_top.get("prior_run_style_band") or "UNKNOWN"


def adjustment(row, race):
    band = row.get("prior_run_style_band") or "UNKNOWN"
    per_kg = PER_KG.get(band, 0.75)
    return standard_race_relative_adjustment(row, per_kg, f"prior_run_style_band={band}")


if __name__ == "__main__":
    paths = evaluate_module(
        module_name=MODULE,
        module_slug=SLUG,
        adjustment_fn=adjustment,
        context_band_fn=context_band,
        output_prefix=SLUG,
        report_title=MODULE,
        method_notes="Run-style interaction: race-relative carried weight adjustment scaled by latest prior run-style band: LEADER 1.10, ON_PACE 1.00, MIDFIELD 0.90, BACKMARKER 0.85, UNKNOWN 0.75; capped +/-4. Prior run style only, no target-race in-running leakage.",
    )
    for path in paths:
        print(path)
