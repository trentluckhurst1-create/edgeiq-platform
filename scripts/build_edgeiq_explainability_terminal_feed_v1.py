from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
RACE_SHAPE = DATA / "edgeiq_race_shape_story_v1.csv"
EXPLAIN = DATA / "edgeiq_runner_explainability_v1.csv"
CONF = DATA / "edgeiq_confidence_breakdown_v1.csv"
TREND = DATA / "edgeiq_runner_trend_engine_v1.csv"

OUT = DATA / "edgeiq_explainability_terminal_feed_v1.csv"
SUMMARY = DATA / "edgeiq_explainability_terminal_feed_v1_summary.csv"


def clean(v):
    return "" if v is None else str(v).strip()


def upper(v):
    return clean(v).upper()


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def horse(row):
    return clean(row.get("horse")) or clean(row.get("_horse"))


def horse_key(row):
    return upper(row.get("horse_key")) or upper(horse(row))


def race_date(row):
    return clean(row.get("race_date")) or clean(row.get("_date"))


def track(row):
    return upper(row.get("track")) or upper(row.get("_track"))


def race_no(row):
    return clean(row.get("race_no")) or clean(row.get("_race"))


def runner_key(row):
    return (race_date(row), track(row), race_no(row), horse_key(row))


def race_key(row):
    return (race_date(row), track(row), race_no(row))


def is_scratched(row):
    vals = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(v in {"TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for v in vals)


def main():
    built_at = datetime.now(timezone.utc).isoformat()

    live_rows_all = read_csv(LIVE)
    live_rows = [r for r in live_rows_all if not is_scratched(r)]

    race_shape_rows = read_csv(RACE_SHAPE)
    explain_rows = read_csv(EXPLAIN)
    conf_rows = read_csv(CONF)
    trend_rows = read_csv(TREND)

    race_shape_index = {race_key(r): r for r in race_shape_rows}
    explain_index = {runner_key(r): r for r in explain_rows}
    conf_index = {runner_key(r): r for r in conf_rows}
    trend_index = {runner_key(r): r for r in trend_rows}

    out_rows = []
    missing_explain = 0
    missing_conf = 0
    missing_trend = 0
    missing_shape = 0

    for r in live_rows:
        rk = runner_key(r)
        racerk = race_key(r)

        sh = race_shape_index.get(racerk, {})
        ex = explain_index.get(rk, {})
        cf = conf_index.get(rk, {})
        tr = trend_index.get(rk, {})

        if not sh:
            missing_shape += 1
        if not ex:
            missing_explain += 1
        if not cf:
            missing_conf += 1
        if not tr:
            missing_trend += 1

        out_rows.append({
            "race_date": race_date(r),
            "track": track(r),
            "race_no": race_no(r),
            "race_key": clean(r.get("race_key")),
            "runner_key": clean(r.get("runner_key")),
            "horse": horse(r),
            "horse_key": horse_key(r),
            "saddlecloth": clean(r.get("saddlecloth")) or clean(r.get("horse_no")),
            "barrier": clean(r.get("barrier")),
            "jockey": clean(r.get("jockey")),
            "trainer": clean(r.get("trainer")),

            "model_rank": clean(ex.get("model_rank")),
            "win_pct": clean(ex.get("win_pct")),
            "fair_price": clean(ex.get("fair_price")),
            "live_price": clean(ex.get("live_price")),
            "edge_pct": clean(ex.get("edge_pct")),

            "positive_1": clean(ex.get("positive_1")),
            "positive_1_value": clean(ex.get("positive_1_value")),
            "positive_2": clean(ex.get("positive_2")),
            "positive_2_value": clean(ex.get("positive_2_value")),
            "positive_3": clean(ex.get("positive_3")),
            "positive_3_value": clean(ex.get("positive_3_value")),
            "risk_1": clean(ex.get("risk_1")),
            "risk_1_value": clean(ex.get("risk_1_value")),
            "risk_2": clean(ex.get("risk_2")),
            "risk_2_value": clean(ex.get("risk_2_value")),
            "risk_3": clean(ex.get("risk_3")),
            "risk_3_value": clean(ex.get("risk_3_value")),
            "why_ranked_here": clean(ex.get("why_ranked_here")),
            "runner_profile_summary": clean(ex.get("runner_profile_summary")),

            "projection_confidence_score": clean(cf.get("projection_confidence_score")),
            "profile_confidence_score": clean(cf.get("profile_confidence_score")),
            "market_confidence_score": clean(cf.get("market_confidence_score")),
            "data_quality_score": clean(cf.get("data_quality_score")),
            "connection_confidence_score": clean(cf.get("connection_confidence_score")),
            "final_confidence_score": clean(cf.get("final_confidence_score")),
            "confidence_band": clean(cf.get("confidence_band")),
            "confidence_explanation": clean(cf.get("confidence_explanation")),

            "last_5_ratings": clean(tr.get("last_5_ratings")),
            "last_5_rating_dates": clean(tr.get("last_5_rating_dates")),
            "rating_trend": clean(tr.get("rating_trend")),
            "rating_trend_delta": clean(tr.get("rating_trend_delta")),
            "last_5_finish_positions": clean(tr.get("last_5_finish_positions")),
            "last_5_tracks": clean(tr.get("last_5_tracks")),
            "trend_label": clean(tr.get("trend_label")),
            "trend_summary": clean(tr.get("trend_summary")),
            "rating_source_method": clean(tr.get("rating_source_method")),

            "race_tempo": clean(sh.get("tempo")),
            "race_shape_label": clean(sh.get("race_shape_label")),
            "race_shape_story": clean(sh.get("race_shape_story")),
            "pace_advantage_runner": clean(sh.get("pace_advantage_runner")),
            "late_power_beneficiary": clean(sh.get("late_power_beneficiary")),
            "pressure_risk_runner": clean(sh.get("pressure_risk_runner")),
            "leader_count": clean(sh.get("leader_count")),
            "on_pace_count": clean(sh.get("on_pace_count")),
            "midfield_count": clean(sh.get("midfield_count")),
            "backmarker_count": clean(sh.get("backmarker_count")),

            "explainability_feed_status": "COMPLETE" if sh and ex and cf and tr else "PARTIAL",
            "built_at": built_at,
        })

    fields = list(out_rows[0].keys()) if out_rows else []

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    complete = sum(1 for r in out_rows if r["explainability_feed_status"] == "COMPLETE")

    summary_rows = [
        {"metric": "status", "value": "EXPLAINABILITY_TERMINAL_FEED_V1_BUILT"},
        {"metric": "live_rows_all", "value": len(live_rows_all)},
        {"metric": "live_active_rows", "value": len(live_rows)},
        {"metric": "output_rows", "value": len(out_rows)},
        {"metric": "complete_rows", "value": complete},
        {"metric": "partial_rows", "value": len(out_rows) - complete},
        {"metric": "missing_race_shape", "value": missing_shape},
        {"metric": "missing_runner_explainability", "value": missing_explain},
        {"metric": "missing_confidence_breakdown", "value": missing_conf},
        {"metric": "missing_runner_trend", "value": missing_trend},
        {"metric": "built_at", "value": built_at},
    ]

    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary_rows)

    print("[EXPLAINABILITY_TERMINAL_FEED_V1] COMPLETE")
    print(f"rows={len(out_rows)}")
    print(f"complete={complete}")
    print(f"output={OUT}")
    print(f"summary={SUMMARY}")


if __name__ == "__main__":
    main()
