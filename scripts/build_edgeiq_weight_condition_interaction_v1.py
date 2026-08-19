from edgeiq_interaction_signal_common_v1 import evaluate_module, standard_race_relative_adjustment

MODULE = "EDGEIQ_WEIGHT_CONDITION_INTERACTION_V1"
SLUG = "edgeiq_weight_condition_interaction_v1"
PER_KG = {
    "FIRM_GOOD": 0.85,
    "SOFT": 1.10,
    "HEAVY": 1.35,
    "UNKNOWN": 1.00,
}


def context_band(race, original_top, adjusted_top, rows):
    return race.get("condition_band") or "UNKNOWN"


def adjustment(row, race):
    band = row.get("condition_band") or "UNKNOWN"
    per_kg = PER_KG.get(band, 1.0)
    return standard_race_relative_adjustment(row, per_kg, f"condition_band={band}")


if __name__ == "__main__":
    paths = evaluate_module(
        module_name=MODULE,
        module_slug=SLUG,
        adjustment_fn=adjustment,
        context_band_fn=context_band,
        output_prefix=SLUG,
        report_title=MODULE,
        method_notes="Condition interaction: race-relative carried weight adjustment scaled by track condition band: FIRM_GOOD 0.85, SOFT 1.10, HEAVY 1.35, UNKNOWN 1.00; capped +/-4.",
    )
    for path in paths:
        print(path)
