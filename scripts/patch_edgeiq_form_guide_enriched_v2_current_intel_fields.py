import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "build_edgeiq_form_guide_enriched_v2.py"


REPLACEMENTS = [
    (
        '    current_price = load_exact_current(FAIR_PRICE, current_runner_keys, "horse", "race_date", "track", "race_no")\n'
        '    current_speed = load_exact_current(SPEED_MAP, current_runner_keys, "horse_key", "race_date", "track", "race_no")\n',
        '    current_price = load_exact_current(FAIR_PRICE, current_runner_keys, "horse", "race_date", "track", "race_no")\n'
        '    current_speed = load_exact_current(SPEED_MAP, current_runner_keys, "horse_key", "race_date", "track", "race_no")\n',
    ),
    (
        '            early_speed_value = num(live_row.get("early_speed_rating") if live_row else None)\n'
        '            edgeiq_price_value = num((price_row or {}).get("display_fair_price") or (price_row or {}).get("ui_fair_price") or (price_row or {}).get("fair_price"))\n'
        '            suitability_value = num((dna_row or {}).get("runner_dna_v6_1_score") or (dna_row or {}).get("dna_score"))\n'
        '            race_shape_value = clean_text((speed_row or {}).get("tempo_fit") or (speed_row or {}).get("speed_map_bucket"))\n',
        '            early_speed_value = num((live_row or {}).get("early_speed_rating") or (live_row or {}).get("projected_spd") or (speed_row or {}).get("projected_spd") or (speed_row or {}).get("early_speed_rating"))\n'
        '            edgeiq_price_value = num((price_row or {}).get("display_fair_price") or (price_row or {}).get("ui_fair_price") or (price_row or {}).get("fair_price") or (price_row or {}).get("fair_price_v7_2") or (live_row or {}).get("display_fair_price_governed") or (live_row or {}).get("fair_price_display") or (live_row or {}).get("fair_price"))\n'
        '            suitability_value = num((dna_row or {}).get("runner_dna_v6_1_score") or (dna_row or {}).get("dna_score"))\n'
        '            race_shape_value = clean_text((speed_row or {}).get("tempo_fit") or (speed_row or {}).get("speed_map_bucket") or (live_row or {}).get("settling_band"))\n'
        '            late_speed_value = num((live_row or {}).get("late_power_index") or (live_row or {}).get("late_power_score") or (speed_row or {}).get("late_power_index") or (speed_row or {}).get("late_power_score"))\n',
    ),
    (
        '            runner["earlySpeed"] = source_value(early_speed_value, "edgeiq_live_runner_board_governed_v1.csv:early_speed_rating", "live_runner_board_v1", None)\n'
        '            runner["edgeiqPrice"] = source_value(edgeiq_price_value, "edgeiq_fair_price_v7_2.csv:display_fair_price/ui_fair_price", "v7_2", None)\n',
        '            runner["earlySpeed"] = source_value(early_speed_value, "edgeiq_live_runner_board_governed_v1.csv:projected_spd/early_speed_rating", "live_runner_board_v1", None)\n'
        '            runner["edgeiqPrice"] = source_value(edgeiq_price_value, "edgeiq_fair_price_v7_2.csv:display_fair_price/ui_fair_price OR edgeiq_live_runner_board_governed_v1.csv:fair_price", "v7_2_or_governed_v3", None)\n',
    ),
    (
        '            runner["raceShape"] = source_value(race_shape_value or None, "live_speed_map_v3.csv:tempo_fit/speed_map_bucket", "v3", None)\n'
        '            runner["lateSpeed"] = source_value(None, None, None, None)\n',
        '            runner["raceShape"] = source_value(race_shape_value or None, "live_speed_map_v3.csv:tempo_fit/speed_map_bucket", "v3", None)\n'
        '            runner["lateSpeed"] = source_value(late_speed_value, "live_speed_map_v3.csv:late_power_index OR edgeiq_live_runner_board_governed_v1.csv:late_power_index", "v3", None)\n',
    ),
    (
        '            metrics["race_shape"] += 1 if race_shape_value else 0\n'
        '            metrics["preparation"] += 1 if runner.get("preparationProfile") else 0\n',
        '            metrics["race_shape"] += 1 if race_shape_value else 0\n'
        '            metrics["late_speed"] += 1 if late_speed_value is not None else 0\n'
        '            metrics["preparation"] += 1 if runner.get("preparationProfile") else 0\n',
    ),
    (
        '                    "late_speed_match": "NO",\n',
        '                    "late_speed_match": "YES" if late_speed_value is not None else "NO",\n',
    ),
    (
        '                    "raceShape": race_shape_value,\n'
        '                    "preparationProfile": "YES" if runner.get("preparationProfile") else "",\n',
        '                    "raceShape": race_shape_value,\n'
        '                    "lateSpeed": late_speed_value if late_speed_value is not None else "",\n'
        '                    "preparationProfile": "YES" if runner.get("preparationProfile") else "",\n',
    ),
    (
        '                "Race Shape": metrics["race_shape"],\n'
        '                "Preparation Profile": metrics["preparation"],\n',
        '                "Race Shape": metrics["race_shape"],\n'
        '                "Late Speed": metrics["late_speed"],\n'
        '                "Preparation Profile": metrics["preparation"],\n',
    ),
    (
        '            "pricing": "edgeiq_fair_price_v7_2.csv selected only on exact current race date/track/race/runner; no historical or market fallback.",\n'
        '            "earlySpeed": "current early_speed_rating only from exact current live board; historical early speed from edgeiq_speed_master_v1.",\n',
        '            "pricing": "edgeiq_fair_price_v7_2.csv selected only on exact current race date/track/race/runner; when V7.2 rows are stale, exact current governed live-board fair_price is used with governed V3 provenance; no historical or market fallback.",\n'
        '            "earlySpeed": "current projected_spd/early_speed_rating only from exact current live board or current speed map; historical early speed from edgeiq_speed_master_v1.",\n',
    ),
    (
        '    write_csv(OUT_CSV, csv_rows, ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "rating", "epi", "marketPrice", "edgeiqPrice", "earlySpeed", "suitability", "raceShape", "preparationProfile", "sectionalRunMatches", "benchmarkRunMatches"])\n',
        '    write_csv(OUT_CSV, csv_rows, ["raceDate", "meeting", "raceNumber", "runnerNumber", "runnerName", "rating", "epi", "marketPrice", "edgeiqPrice", "earlySpeed", "suitability", "raceShape", "lateSpeed", "preparationProfile", "sectionalRunMatches", "benchmarkRunMatches"])\n',
    ),
    (
        '    write_csv(COVERAGE_CSV, race_coverage_rows, ["race_date", "meeting", "race_number", "runners", "Weather by race", "Weather runner rows", "EPI", "EDGEiQ Price", "Early Speed", "Suitability", "Race Shape", "Preparation Profile", "Career Profile", "Recent Form"])\n',
        '    write_csv(COVERAGE_CSV, race_coverage_rows, ["race_date", "meeting", "race_number", "runners", "Weather by race", "Weather runner rows", "EPI", "EDGEiQ Price", "Early Speed", "Suitability", "Race Shape", "Late Speed", "Preparation Profile", "Career Profile", "Recent Form"])\n',
    ),
    (
        '        f"Late Speed: 0/{total_runners} -> 0/{total_runners}",\n',
        '        f"Late Speed: 0/{total_runners} -> {totals[\'late_speed\']}/{total_runners}",\n',
    ),
]


def main():
    if not TARGET.exists():
        raise FileNotFoundError(TARGET)
    text = TARGET.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}_CHECKPOINT_BEFORE_CURRENT_INTEL_FIELD_PATCH_{stamp}{TARGET.suffix}")
    shutil.copy2(TARGET, backup)
    changed = 0
    for old, new in REPLACEMENTS:
        if old not in text:
            raise RuntimeError(f"Patch anchor not found after {changed} replacements:\n{old}")
        text = text.replace(old, new, 1)
        changed += 1
    TARGET.write_text(text, encoding="utf-8")
    print("EDGEIQ_FORM_GUIDE_ENRICHED_V2_CURRENT_INTEL_FIELD_PATCH_COMPLETE")
    print(f"checkpoint={backup}")
    print(f"replacements={changed}")


if __name__ == "__main__":
    main()
