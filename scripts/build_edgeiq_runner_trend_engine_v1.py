from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_RATINGS = DATA / "edgeiq_historical_performance_rating_v6_research.csv"
INPUT_RESULTS = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"

OUT = DATA / "edgeiq_runner_trend_engine_v1.csv"
SUMMARY = DATA / "edgeiq_runner_trend_engine_v1_summary.csv"


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def upper(v):
    return clean(v).upper()


def to_float(v, default=None):
    try:
        txt = clean(v)
        if txt == "":
            return default
        return float(txt)
    except Exception:
        return default


def csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm_date(v):
    txt = clean(v)
    if not txt:
        return ""
    return txt[:10]


def norm_track(row):
    return upper(row.get("track")) or upper(row.get("_track"))


def norm_race_no(row):
    return clean(row.get("race_no")) or clean(row.get("_race"))


def norm_race_date(row):
    return norm_date(row.get("race_date")) or norm_date(row.get("_date"))


def horse_name(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def canonical_horse(v):
    txt = upper(v)
    keep = []
    for ch in txt:
        if ch.isalnum() or ch.isspace():
            keep.append(ch)
    return " ".join("".join(keep).split())


def board_horse_key(row):
    return upper(row.get("horse_key")) or canonical_horse(horse_name(row))


def is_scratched(row):
    vals = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(v in {"TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for v in vals)


def rating_value(row):
    for col in [
        "performance_rating_v6_research",
        "performance_rating_v5_1",
        "performance_rating_v3",
        "performance_rating",
        "rating",
    ]:
        v = to_float(row.get(col), None)
        if v is not None:
            return v, col
    return None, ""


def finish_value(row):
    for col in ["finish_position", "finish_pos_raw", "finishPosition"]:
        v = clean(row.get(col))
        if v:
            return v
    return ""


def rating_history_key(row):
    return canonical_horse(row.get("horse"))


def result_history_key(row):
    return canonical_horse(row.get("horseName")) or canonical_horse(row.get("horse"))


def result_date(row):
    return norm_date(row.get("meeting_date")) or norm_date(row.get("race_date"))


def rating_date(row):
    return norm_date(row.get("race_date"))


def build_rating_history(rows):
    hist = defaultdict(list)
    source_cols = defaultdict(int)

    for r in rows:
        key = rating_history_key(r)
        dt = rating_date(r)
        rating, source = rating_value(r)

        if not key or not dt or rating is None:
            continue

        hist[key].append({
            "date": dt,
            "rating": rating,
            "track": upper(r.get("track")),
            "finish": finish_value(r),
            "source": source,
        })
        source_cols[source] += 1

    for key in hist:
        hist[key].sort(key=lambda x: x["date"], reverse=True)

    return hist, source_cols


def build_result_history(rows):
    hist = defaultdict(list)

    for r in rows:
        key = result_history_key(r)
        dt = result_date(r)

        if not key or not dt:
            continue

        hist[key].append({
            "date": dt,
            "rating": None,
            "track": upper(r.get("track")),
            "finish": finish_value(r),
            "source": "results_only_no_rating",
        })

    for key in hist:
        hist[key].sort(key=lambda x: x["date"], reverse=True)

    return hist


def trend_label(delta, count):
    if count < 2:
        return "INSUFFICIENT_HISTORY"
    if delta >= 5:
        return "IMPROVING"
    if delta <= -5:
        return "DECLINING"
    return "STABLE"


def trend_summary(label, delta, ratings, dates):
    if label == "INSUFFICIENT_HISTORY":
        if len(dates) == 0:
            return "No prior historical runs found."
        return "Only one prior historical run found; trend cannot be assessed."

    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return f"{label}: rating trend {direction} {round(delta, 2)} across last {len(ratings)} available runs."


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    board_rows = csv_rows(INPUT_BOARD)
    rating_rows = csv_rows(INPUT_RATINGS)
    result_rows = csv_rows(INPUT_RESULTS)

    rating_hist, source_cols = build_rating_history(rating_rows)
    result_hist = build_result_history(result_rows)

    active_board = [r for r in board_rows if not is_scratched(r)]

    out_rows = []
    label_counts = defaultdict(int)
    matched_rating_history = 0
    matched_result_history_only = 0

    for r in active_board:
        hname = horse_name(r)
        key = canonical_horse(hname)
        race_date = norm_race_date(r)

        prior_rating = [
            x for x in rating_hist.get(key, [])
            if x["date"] < race_date
        ]

        source_mode = "performance_rating_v6_research"

        if prior_rating:
            matched_rating_history += 1
            chosen = prior_rating[:5]
        else:
            prior_results = [
                x for x in result_hist.get(key, [])
                if x["date"] < race_date
            ]
            chosen = prior_results[:5]
            source_mode = "results_only_no_rating"
            if chosen:
                matched_result_history_only += 1

        ratings = [x["rating"] for x in chosen if x["rating"] is not None]
        dates = [x["date"] for x in chosen]
        finishes = [x["finish"] for x in chosen]
        tracks = [x["track"] for x in chosen]

        if len(ratings) >= 2:
            chronological = list(reversed(ratings))
            delta = chronological[-1] - chronological[0]
        else:
            delta = 0.0

        label = trend_label(delta, len(ratings))
        label_counts[label] += 1

        out_rows.append({
            "race_date": race_date,
            "track": norm_track(r),
            "race_no": norm_race_no(r),
            "horse": hname,
            "horse_key": board_horse_key(r),
            "last_5_ratings": " > ".join("" if v is None else str(round(v, 2)) for v in ratings),
            "last_5_rating_dates": " > ".join(dates),
            "rating_trend": label,
            "rating_trend_delta": round(delta, 2),
            "last_5_finish_positions": " > ".join(finishes),
            "last_5_tracks": " > ".join(tracks),
            "trend_label": label,
            "trend_summary": trend_summary(label, delta, ratings, dates),
            "rating_source_method": source_mode,
            "built_at": built_at,
        })

    fields = [
        "race_date", "track", "race_no", "horse", "horse_key",
        "last_5_ratings", "last_5_rating_dates", "rating_trend",
        "rating_trend_delta", "last_5_finish_positions", "last_5_tracks",
        "trend_label", "trend_summary", "rating_source_method", "built_at",
    ]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    summary_rows = [
        {"metric": "status", "value": "RUNNER_TREND_ENGINE_V1_BUILT"},
        {"metric": "input_board_rows", "value": len(board_rows)},
        {"metric": "input_rating_rows", "value": len(rating_rows)},
        {"metric": "input_result_rows", "value": len(result_rows)},
        {"metric": "active_runner_rows", "value": len(active_board)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "matched_rating_history_rows", "value": matched_rating_history},
        {"metric": "matched_result_history_only_rows", "value": matched_result_history_only},
        {"metric": "built_at", "value": built_at},
    ]

    for k, v in sorted(label_counts.items()):
        summary_rows.append({"metric": f"trend_{k}", "value": v})

    for k, v in sorted(source_cols.items()):
        summary_rows.append({"metric": f"rating_source_{k}", "value": v})

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[RUNNER_TREND_ENGINE_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
