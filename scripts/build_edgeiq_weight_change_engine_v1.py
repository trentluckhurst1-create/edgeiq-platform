from edgeiq_interaction_signal_common_v1 import DATA, evaluate_module, parse_num, fmt

MODULE = "EDGEIQ_WEIGHT_CHANGE_ENGINE_V1"
SLUG = "edgeiq_weight_change_engine_v1"


def race_filter(row):
    return parse_num(row.get("weight_change_vs_previous_start_kg")) is not None


def context_band(race, original_top, adjusted_top, rows):
    delta = parse_num(original_top.get("weight_change_vs_previous_start_kg"))
    if delta is None:
        return "ORIGINAL_TOP_UNKNOWN_WEIGHT_CHANGE"
    if delta >= 2:
        return "ORIGINAL_TOP_WEIGHT_UP_2KG_PLUS"
    if delta > 0:
        return "ORIGINAL_TOP_WEIGHT_UP_LT2KG"
    if delta <= -2:
        return "ORIGINAL_TOP_WEIGHT_DOWN_2KG_PLUS"
    if delta < 0:
        return "ORIGINAL_TOP_WEIGHT_DOWN_LT2KG"
    return "ORIGINAL_TOP_SAME_WEIGHT"


def adjustment(row, race):
    delta = parse_num(row.get("weight_change_vs_previous_start_kg"))
    if delta is None:
        return 0.0, "missing previous-start carried weight; no adjustment"
    return -delta * 1.0, f"previous_start_weight_change_delta_kg={fmt(delta, 3)}; per_kg=1.0; cap=+/-4"


if __name__ == "__main__":
    paths = evaluate_module(
        module_name=MODULE,
        module_slug=SLUG,
        adjustment_fn=adjustment,
        context_band_fn=context_band,
        race_filter_fn=race_filter,
        output_prefix=SLUG,
        report_title=MODULE,
        method_notes="Weight-change interaction: adjusted prior rating by today's carried weight change versus previous start, 1.0 point per kg, capped +/-4.",
    )
    for path in paths:
        print(path)
