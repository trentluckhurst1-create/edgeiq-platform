from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, race_key, clean, num

SPINE = DATA / "edgeiq_pricing_replay_spine_v1.csv"
SOURCES = [
    ("v6_1_detail", DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"),
    ("settled_v2", DATA / "edgeiq_v6_1_settled_gap_replay_v2_expanded.csv"),
    ("fair_replay", DATA / "edgeiq_fair_price_replay_v1.csv"),
    ("model_review", DATA / "model_result_review.csv"),
]
OUT = DATA / "edgeiq_pricing_replay_join_map_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_pricing_replay_join_map_summary_v1.csv"


def rkey(r):
    return (*race_key(r), clean(r.get("horse")))


def main():
    base = read_csv(SPINE)
    source_maps = {name: {rkey(r): r for r in read_csv(path)} for name, path in SOURCES}
    rows, counts = [], Counter()
    for b in base:
        key = rkey(b)
        rec = {"race_date": b["race_date"], "track": b["track"], "race_no": b["race_no"], "horse": b["horse"]}
        any_prob = False
        any_rating = bool(b.get("rating"))
        reasons = []
        for name, mp in source_maps.items():
            hit = mp.get(key)
            rec[f"{name}_exact_match"] = "YES" if hit else "NO"
            if hit:
                counts[f"{name}_matched"] += 1
                any_prob = any_prob or any("prob" in k.lower() and num(v) is not None for k, v in hit.items())
                any_rating = any_rating or any("rating" in k.lower() and num(v) is not None for k, v in hit.items())
            else:
                counts[f"{name}_unmatched"] += 1
        if not any_prob:
            reasons.append("NO_PROBABILITY_HISTORY")
        if not any_rating:
            reasons.append("NO_RATING_HISTORY")
        if not key[0]:
            reasons.append("DATE_MISMATCH")
        if not key[1]:
            reasons.append("TRACK_MISMATCH")
        if not key[2]:
            reasons.append("RACE_NO_MISMATCH")
        if not key[3]:
            reasons.append("HORSE_NAME_MISMATCH")
        rec["join_failure_reason"] = ";".join(reasons) if reasons else "MATCHED_USABLE"
        counts[rec["join_failure_reason"]] += 1
        rows.append(rec)
    write_csv(OUT, rows, list(rows[0].keys()) if rows else [])
    summary = [{"metric": k, "value": v} for k, v in counts.most_common()]
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
