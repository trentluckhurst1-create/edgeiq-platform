from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_graphql_january_2025_results_v1.csv"
OUT = DATA / "edgeiq_graphql_results_warehouse_week1_2025_v1.csv"
SUMMARY = DATA / "edgeiq_graphql_results_warehouse_week1_2025_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def money_to_float(v):
    txt = clean(v).replace("$", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return ""


def margin_to_float(v):
    txt = clean(v).upper().replace("L", "")
    try:
        return float(txt)
    except Exception:
        return ""


def normalise_finish(raw, scratched):
    f = clean(raw)
    s = clean(scratched).lower()

    if f == "109" or s == "true":
        return "", "SCR"

    if f == "100":
        return "", "DNF_PENDING_REVIEW"

    if f.isdigit():
        n = int(f)
        if 1 <= n <= 99:
            return n, "FINISHED"

    return "", "UNKNOWN"


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    with INFILE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    out_rows = []

    for r in rows:
        finish_position, finish_status = normalise_finish(r.get("finish"), r.get("scratched"))

        race_date = clean(r.get("race_date"))
        track = clean(r.get("track"))
        race_no = clean(r.get("race_no"))
        horse = clean(r.get("horse"))

        out_rows.append({
            "race_key": f"{race_date}|{track.upper()}|R{race_no}",
            "runner_key": f"{race_date}|{track.upper()}|R{race_no}|{horse.upper()}",
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "race_name": clean(r.get("race_name")),
            "distance": clean(r.get("distance")),
            "race_class": clean(r.get("race_class")),
            "track_condition": clean(r.get("track_condition")),
            "track_rating": clean(r.get("track_rating")),
            "rail_position": clean(r.get("rail_position")),
            "weather": clean(r.get("weather")),
            "rainfall": clean(r.get("rainfall")),
            "penetrometer": clean(r.get("penetrometer")),
            "horse": horse,
            "horse_code": clean(r.get("horse_code")),
            "trainer": clean(r.get("trainer")),
            "trainer_code": clean(r.get("trainer_code")),
            "jockey": clean(r.get("jockey")),
            "jockey_code": clean(r.get("jockey_code")),
            "barrier": clean(r.get("barrier")),
            "weight": clean(r.get("weight")),
            "scratched": clean(r.get("scratched")),
            "finish_raw": clean(r.get("finish")),
            "finish_position": finish_position,
            "finish_status": finish_status,
            "margin": clean(r.get("margin")),
            "margin_l": margin_to_float(r.get("margin")),
            "starting_price": clean(r.get("starting_price")),
            "starting_price_decimal": money_to_float(r.get("starting_price")),
            "winning_time": clean(r.get("winning_time")),
            "comment_short": clean(r.get("comment_short")),
            "comment_stewards": clean(r.get("comment_stewards")),
            "gear_changes": clean(r.get("gear_changes")),
            "source": "EDGEIQ_GRAPHQL_WEEK1_2025_NORMALISED",
            "built_at": built_at,
        })

    fields = list(out_rows[0].keys()) if out_rows else []

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    summary = [
        {"metric": "status", "value": "EDGEIQ_GRAPHQL_RESULTS_WAREHOUSE_WEEK1_2025_V1_BUILT"},
        {"metric": "input_rows", "value": len(rows)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "finished_rows", "value": sum(1 for r in out_rows if r["finish_status"] == "FINISHED")},
        {"metric": "scratched_rows", "value": sum(1 for r in out_rows if r["finish_status"] == "SCR")},
        {"metric": "dnf_pending_review_rows", "value": sum(1 for r in out_rows if r["finish_status"] == "DNF_PENDING_REVIEW")},
        {"metric": "rows_with_sp", "value": sum(1 for r in out_rows if r["starting_price"])},
        {"metric": "rows_with_trainer", "value": sum(1 for r in out_rows if r["trainer"])},
        {"metric": "rows_with_jockey", "value": sum(1 for r in out_rows if r["jockey"])},
        {"metric": "rows_with_rail", "value": sum(1 for r in out_rows if r["rail_position"])},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("[EDGEIQ_GRAPHQL_RESULTS_WAREHOUSE_WEEK1_2025_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
