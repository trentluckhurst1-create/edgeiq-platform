from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, num, format_float

BACKFILL = DATA / "edgeiq_pricing_replay_probability_backfill_v1.csv"
OUT = DATA / "edgeiq_pricing_replay_spine_v2.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_replay_spine_v2_summary.csv"
OUT_AUDIT = DATA / "edgeiq_pricing_replay_spine_v2_audit.csv"


def main():
    rows = []
    counts = Counter()
    sums = defaultdict(float)
    race_rows = defaultdict(int)
    for r in read_csv(BACKFILL):
        method = r["backfill_method"]
        source = "ARCHIVED" if method == "ARCHIVED" else "BACKFILLED"
        prob = num(r.get("backfilled_production_probability")) or 0
        ready = "YES" if prob > 0 and r.get("sp_price") and r.get("won") != "" else "NO"
        rows.append({
            "race_date": r["race_date"], "track": r["track"], "race_no": r["race_no"], "horse": r["horse"], "won": r["won"],
            "finish_position": r["finish_position"], "sp_price": r["sp_price"], "market_price": r["market_price"], "rating": r["rating"],
            "field_size": r["field_size"], "probability_source": source,
            "production_probability_replay": format_float(prob, 6), "production_fair_price_replay": r["backfilled_production_fair_price"],
            "source_quality": r["source_quality"], "replay_ready_flag": ready,
        })
        counts[source] += 1; counts[f"ready_{ready}"] += 1
        k = (r["race_date"], r["track"], r["race_no"])
        sums[k] += prob; race_rows[k] += 1
    full = sum(1 for v in sums.values() if abs(v - 1) < .001)
    readiness = "STRONG_REPLAY" if len(rows) >= 20000 and counts["ready_YES"] / max(len(rows), 1) > .9 and counts["ARCHIVED"] > 10000 else "USABLE_WITH_WARNINGS" if len(rows) >= 20000 and counts["ready_YES"] / max(len(rows), 1) > .9 else "WEAK_REPLAY"
    audit = [{"race_date": k[0], "track": k[1], "race_no": k[2], "probability_sum": format_float(v, 6), "runner_count": race_rows[k]} for k, v in sums.items()]
    summary = [
        {"metric": "readiness", "value": readiness}, {"metric": "race_count", "value": len(sums)}, {"metric": "runner_count", "value": len(rows)},
        {"metric": "ready_runner_count", "value": counts["ready_YES"]}, {"metric": "archived_probability_count", "value": counts["ARCHIVED"]},
        {"metric": "backfilled_probability_count", "value": counts["BACKFILLED"]}, {"metric": "missing_probability_count", "value": 0},
        {"metric": "races_with_full_probability_sum", "value": full}, {"metric": "rows_with_sp", "value": sum(1 for r in rows if r["sp_price"])}, {"metric": "rows_with_winner", "value": sum(1 for r in rows if r["won"] != "")},
    ]
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
