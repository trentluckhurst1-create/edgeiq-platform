import math
from collections import defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, num, race_key, format_float

SPINE = DATA / "edgeiq_pricing_replay_spine_v1.csv"
OUT = DATA / "edgeiq_pricing_replay_probability_backfill_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_replay_probability_backfill_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_pricing_replay_probability_backfill_v1_audit.csv"


def main():
    grouped = defaultdict(list)
    for r in read_csv(SPINE):
        grouped[(r["race_date"], r["track"], r["race_no"])].append(r)
    out, audit = [], []
    archived = backfilled = missing_rating = 0
    for key, rows in grouped.items():
        ratings = [num(r.get("rating")) for r in rows if num(r.get("rating")) is not None]
        if ratings:
            max_rating = max(ratings)
            scores = [math.exp(((num(r.get("rating")) or min(ratings)) - max_rating) / 8.5) for r in rows]
        else:
            scores = [1 for _ in rows]
        total = sum(scores) or 1
        probs = [s / total for s in scores]
        for r, p in zip(rows, probs):
            archived_prob = num(r.get("production_probability"))
            if archived_prob and archived_prob > 0:
                prob, method, conf = archived_prob, "ARCHIVED", "HIGH"
                archived += 1
            elif ratings:
                prob, method, conf = p, "RATING_SOFTMAX_BACKFILL", "MEDIUM"
                backfilled += 1
            else:
                prob, method, conf = p, "EQUAL_FIELD_BACKFILL", "LOW"
                backfilled += 1; missing_rating += 1
            out.append({
                "race_date": r["race_date"], "track": r["track"], "race_no": r["race_no"], "horse": r["horse"],
                "won": r["won"], "finish_position": r["finished_position"], "sp_price": r["sp_price"], "market_price": r["market_price"],
                "rating": r["rating"], "field_size": r["field_size"],
                "backfilled_production_probability": format_float(prob, 6),
                "backfilled_production_fair_price": format_float(1 / prob if prob else 0, 2),
                "backfill_method": method, "backfill_confidence": conf,
                "source_quality": "ARCHIVED_PROBABILITY" if method == "ARCHIVED" else "RESEARCH_BACKFILL",
            })
        audit.append({"race_date": key[0], "track": key[1], "race_no": key[2], "probability_sum": format_float(sum(num(o["backfilled_production_probability"]) for o in out[-len(rows):]), 6), "field_size": len(rows)})
    summary = [{"metric": "runner_rows", "value": len(out)}, {"metric": "race_rows", "value": len(grouped)}, {"metric": "archived_probability_rows", "value": archived}, {"metric": "backfilled_probability_rows", "value": backfilled}, {"metric": "missing_rating_backfilled_equal_rows", "value": missing_rating}]
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_AUDIT, audit, list(audit[0].keys()) if audit else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
