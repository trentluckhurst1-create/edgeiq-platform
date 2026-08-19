from edgeiq_interaction_signal_common_v1 import evaluate_module, standard_race_relative_adjustment

MODULE = "EDGEIQ_WEIGHT_DISTANCE_INTERACTION_V1"
SLUG = "edgeiq_weight_distance_interaction_v1"
PER_KG = {
    "SPRINT": 0.75,
    "MILE": 1.00,
    "MIDDLE": 1.15,
    "STAYING": 1.35,
    "UNKNOWN": 1.00,
}


def context_band(race, original_top, adjusted_top, rows):
    return race.get("distance_band") or "UNKNOWN"


def adjustment(row, race):
    band = row.get("distance_band") or "UNKNOWN"
    per_kg = PER_KG.get(band, 1.0)
    return standard_race_relative_adjustment(row, per_kg, f"distance_band={band}")


if __name__ == "__main__":
    paths = evaluate_module(
        module_name=MODULE,
        module_slug=SLUG,
        adjustment_fn=adjustment,
        context_band_fn=context_band,
        output_prefix=SLUG,
        report_title=MODULE,
        method_notes="Distance interaction: race-relative carried weight adjustment scaled by distance band: SPRINT 0.75, MILE 1.00, MIDDLE 1.15, STAYING 1.35, UNKNOWN 1.00; capped +/-4.",
    )
    for path in paths:
        print(path)
