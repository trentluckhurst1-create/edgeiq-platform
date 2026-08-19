from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_tab_data_population_audit_v1.csv"


def read_rows(name: str) -> list[dict[str, str]]:
    path = DATA / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def columns(name: str) -> list[str]:
    path = DATA / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return next(csv.reader(handle), [])


def text(value: Any) -> str:
    return str(value or "").strip()


def nonblank(rows: list[dict[str, str]], names: list[str]) -> int:
    return sum(1 for row in rows if any(text(row.get(name)) and text(row.get(name)) not in {"-", "0"} for name in names))


def write(rows: list[dict[str, Any]]) -> None:
    fields = ["check", "status", "detail", "count"]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    race_list = read_rows("edgeiq_vic_three_day_race_list_v1.csv")
    governed = read_rows("edgeiq_live_runner_board_governed_v1.csv")
    live = read_rows("edgeiq_live_runner_board_v1.csv")
    heatmap = read_rows("edgeiq_ratings_intelligence_heatmap_v1.csv")
    form_clean = read_rows("edgeiq_form_display_clean_v2.csv")
    form_v2 = read_rows("edgeiq_form_intelligence_v2.csv")
    map_feed = read_rows("edgeiq_map_enrichment_feed_v3.csv")

    runner_rows = governed or live
    race_keys = {(text(r.get("race_date")), text(r.get("track")), text(r.get("race_no"))) for r in runner_rows if text(r.get("track")) and text(r.get("race_no"))}
    runner_counts: dict[tuple[str, str, str], int] = {}
    for row in runner_rows:
        key = (text(row.get("race_date")), text(row.get("track")), text(row.get("race_no")))
        if key[1] and key[2]:
            runner_counts[key] = runner_counts.get(key, 0) + 1

    weight_fields = ["weight", "allocated_weight", "handicap_weight", "weight_carried", "runner_weight", "weight_kg"]
    heatmap_required = ["runner_rating", "rating_gap", "distance_score", "condition_score", "class_score", "overall_heat_score", "heat_band"]
    map_required = ["map_x_pct_display_v3", "race_pressure_band_v3", "race_leader_count_v3", "race_midfield_count_v3", "race_backmarker_count_v3"]

    rows = [
        {"check": "race_list_rows", "status": "PASS" if race_list else "FAIL", "detail": "Racing.com race list loaded", "count": len(race_list)},
        {"check": "race_list_race_count", "status": "PASS" if len(race_list) > 0 else "FAIL", "detail": "Race-list fallback race rows", "count": len({(r.get("race_date"), r.get("normalised_track") or r.get("track"), r.get("race_no")) for r in race_list})},
        {"check": "current_runner_rows", "status": "PASS" if runner_rows else "FAIL", "detail": "Governed/live runner rows available", "count": len(runner_rows)},
        {"check": "runner_race_count", "status": "PASS" if race_keys else "FAIL", "detail": "Races with runner rows", "count": len(race_keys)},
        {"check": "races_with_runner_counts", "status": "PASS" if runner_counts else "FAIL", "detail": "Field sizes can be derived from runner count", "count": len(runner_counts)},
        {"check": "weight_columns_available", "status": "PASS" if any(any(name in columns(file_name) for name in weight_fields) for file_name in ["edgeiq_live_runner_board_governed_v1.csv", "edgeiq_live_runner_board_v1.csv", "edgeiq_form_display_clean_v2.csv", "edgeiq_form_intelligence_v2.csv"]) else "WARN", "detail": "UI supports requested weight fields; no active source column found" if not any(any(name in columns(file_name) for name in weight_fields) for file_name in ["edgeiq_live_runner_board_governed_v1.csv", "edgeiq_live_runner_board_v1.csv", "edgeiq_form_display_clean_v2.csv", "edgeiq_form_intelligence_v2.csv"]) else "weight source present", "count": nonblank(runner_rows + form_clean + form_v2, weight_fields)},
        {"check": "ratings_heatmap_file", "status": "PASS" if heatmap else "FAIL", "detail": "edgeiq_ratings_intelligence_heatmap_v1.csv", "count": len(heatmap)},
        {"check": "ratings_heatmap_columns", "status": "PASS" if all(name in columns("edgeiq_ratings_intelligence_heatmap_v1.csv") for name in heatmap_required) else "FAIL", "detail": ",".join([name for name in heatmap_required if name in columns("edgeiq_ratings_intelligence_heatmap_v1.csv")]), "count": len(heatmap_required)},
        {"check": "runner_profile_form_rows", "status": "PASS" if (form_clean or form_v2) else "FAIL", "detail": "Form rows available for quick expansion", "count": len(form_clean) + len(form_v2)},
        {"check": "map_data_columns", "status": "PASS" if all(name in columns("edgeiq_map_enrichment_feed_v3.csv") for name in map_required) else "FAIL", "detail": ",".join([name for name in map_required if name in columns("edgeiq_map_enrichment_feed_v3.csv")]), "count": len(map_feed)},
    ]
    write(rows)
    failures = [row for row in rows if row["status"] == "FAIL"]
    print(f"EDGEiQ tab data population audit: {len(rows) - len(failures)}/{len(rows)} PASS")
    if failures:
        for row in failures:
            print(f"FAIL {row['check']}: {row['detail']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

