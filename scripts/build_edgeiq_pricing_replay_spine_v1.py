from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, text, clean, num, race_key, bucket_field_size

OUT = DATA / "edgeiq_pricing_replay_spine_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_replay_spine_v1_summary.csv"
OUT_AUDIT = DATA / "edgeiq_pricing_replay_spine_v1_audit.csv"
SOURCES = [
    DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv",
    DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv",
    DATA / "edgeiq_v6_1_settled_gap_replay_v1.csv",
    DATA / "model_result_review.csv",
]


def n(row, keys):
    for key in keys:
        value = num(row.get(key))
        if value is not None:
            return value
    return None


def won(row):
    raw = text(row.get("won")).upper()
    return 1 if raw in {"1", "YES", "TRUE", "Y"} or n(row, ["finish_position", "finish_pos", "finish_pos_num"]) == 1 else 0


def main():
    chosen, raw = "", []
    for source in SOURCES:
        rows = read_csv(source)
        usable = [r for r in rows if race_key(r)[0] and race_key(r)[2] and n(r, ["sp", "market_price", "closing_price"])]
        if len(usable) > len(raw):
            chosen, raw = source.name, usable
    by_race = defaultdict(list)
    for row in raw:
        by_race[race_key(row)].append(row)
    out, seen, dupes = [], set(), 0
    for key, field in sorted(by_race.items()):
        field_size = len(field)
        for row in field:
            rkey = (*key, clean(row.get("horse")))
            if rkey in seen:
                dupes += 1
            seen.add(rkey)
            prob = n(row, ["V6_1_RESEARCH_probability", "rated_probability"])
            if prob and prob > 1:
                prob = prob / 100
            out.append({
                "race_date": key[0],
                "track": text(row.get("track")),
                "race_no": key[2],
                "horse": text(row.get("horse")),
                "finished_position": n(row, ["finish_position", "finish_pos", "finish_pos_num"]) or "",
                "won": won(row),
                "sp_price": n(row, ["sp"]) or "",
                "market_price": n(row, ["market_price", "closing_price", "sp"]) or "",
                "rating": n(row, ["projected_rating_V6_1_RESEARCH", "adjusted_rating", "latest_flat_rating"]) or "",
                "production_probability": prob or "",
                "production_fair_price": n(row, ["V6_1_RESEARCH_fair_price", "rated_price", "fair_price"]) or "",
                "field_size": field_size,
                "field_size_bucket": bucket_field_size(field_size),
                "race_class": text(row.get("race_class") or row.get("race_conditions")),
                "distance": text(row.get("distance")),
                "condition": text(row.get("track_condition") or row.get("condition")),
                "source_file": chosen,
            })
    dates = [r["race_date"] for r in out if r["race_date"]]
    race_count = len(by_race)
    runners = len(out)
    with_winner = sum(1 for _, f in by_race.items() if any(won(r) for r in f))
    with_sp = sum(1 for r in out if r["sp_price"] or r["market_price"])
    with_prob = sum(1 for r in out if r["production_probability"])
    with_rating = sum(1 for r in out if r["rating"])
    with_field = sum(1 for r in out if r["field_size"])
    missing_context = sum(1 for r in out if not r["race_class"] or not r["distance"] or not r["condition"])
    if race_count >= 500 and with_sp / max(runners, 1) > .9 and with_prob / max(runners, 1) > .9 and missing_context == 0:
        ready = "STRONG_REPLAY"
    elif race_count >= 100 and with_sp / max(runners, 1) > .8 and with_prob / max(runners, 1) > .8 and with_rating / max(runners, 1) > .8:
        ready = "USABLE_WITH_WARNINGS"
    elif race_count >= 25:
        ready = "WEAK_REPLAY"
    else:
        ready = "NOT_READY"
    audit = [{"check": "source_file", "value": chosen}, {"check": "duplicate_runner_keys", "value": dupes}, {"check": "missing_context_rows", "value": missing_context}]
    summary = [
        {"metric": "readiness", "value": ready},
        {"metric": "source_file", "value": chosen},
        {"metric": "races", "value": race_count},
        {"metric": "runners", "value": runners},
        {"metric": "with_winner_races", "value": with_winner},
        {"metric": "with_sp_or_market", "value": with_sp},
        {"metric": "with_production_probability", "value": with_prob},
        {"metric": "with_rating", "value": with_rating},
        {"metric": "with_field_size", "value": with_field},
        {"metric": "duplicate_runner_keys", "value": dupes},
        {"metric": "date_min", "value": min(dates) if dates else ""},
        {"metric": "date_max", "value": max(dates) if dates else ""},
    ]
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_AUDIT, audit, ["check", "value"])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
