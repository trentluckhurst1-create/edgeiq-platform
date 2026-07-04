import math
from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, mean, median_value, num, format_float

SPINE = DATA / "edgeiq_pricing_replay_spine_v1.csv"
SPINE_SUMMARY = DATA / "edgeiq_pricing_replay_spine_v1_summary.csv"
OUT = DATA / "edgeiq_probability_research_v6_historical_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v6_historical_replay_summary.csv"


def ll(p, y):
    p = max(.001, min(.999, p)); return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def replay_probs(rows, mode):
    ranked = sorted(rows, key=lambda r: num(r.get("production_probability")) or 0, reverse=True)
    if mode == "production":
        vals = [num(r.get("production_probability")) or 0 for r in ranked]
    else:
        temps = {"v5": .88, "v5_1": .94, "v5_2": .99, "v6": .96}
        vals = [max(.0001, num(r.get("production_probability")) or .0001) ** (1 / temps[mode]) for r in ranked]
    total = sum(vals) or 1
    vals = [v / total for v in vals]
    caps = {"production": 1, "v5": .43, "v5_1": .39, "v5_2": .36, "v6": .36}
    cap = caps[mode]
    if vals and max(vals) > cap:
        i = vals.index(max(vals)); excess = vals[i] - cap; vals[i] = cap
        rest = [j for j in range(len(vals)) if j != i]; rt = sum(vals[j] for j in rest) or 1
        for j in rest: vals[j] += excess * vals[j] / rt
    total = sum(vals) or 1
    return ranked, [v / total for v in vals]


def main():
    summary_lookup = {r["metric"]: r["value"] for r in read_csv(SPINE_SUMMARY)}
    readiness = summary_lookup.get("readiness", "NOT_READY")
    rows = read_csv(SPINE)
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["race_date"], r["track"], r["race_no"])].append(r)
    out, metrics, favs, ranks = [], defaultdict(list), defaultdict(list), Counter()
    for key, field in sorted(grouped.items()):
        allm = {m: replay_probs(field, m) for m in ["production", "v5", "v5_1", "v5_2", "v6"]}
        winners = [i for i, r in enumerate(allm["production"][0]) if str(r.get("won")) == "1"]
        if winners:
            pos = min(winners) + 1
            if pos <= 1: ranks["rank1"] += 1
            if pos <= 2: ranks["top2"] += 1
            if pos <= 3: ranks["top3"] += 1
        for mode, (ranked, vals) in allm.items():
            favs[mode].append(1 / vals[0] if vals and vals[0] else 0)
            for r, p in zip(ranked, vals):
                y = 1 if str(r.get("won")) == "1" else 0
                metrics[f"{mode}_ll"].append(ll(p, y)); metrics[f"{mode}_brier"].append((p - y) ** 2)
        for r, p in zip(*allm["production"]):
            rec = {"race_date": key[0], "track": key[1], "race_no": key[2], "horse": r["horse"], "production_probability": format_float(p, 4), "won": r["won"]}
            for mode in ["v5", "v5_1", "v5_2", "v6"]:
                idx = next((i for i, rr in enumerate(allm[mode][0]) if rr["horse"] == r["horse"]), -1)
                rec[f"{mode}_probability"] = format_float(allm[mode][1][idx] if idx >= 0 else 0, 4)
            out.append(rec)
    summ = [{"metric": "replay_spine_readiness", "value": readiness}, {"metric": "race_rows", "value": len(grouped)}, {"metric": "runner_rows", "value": len(out)}, {"metric": "rank1_win_rate", "value": f"{ranks['rank1']/max(len(grouped),1)*100:.1f}%"}, {"metric": "top2_win_rate", "value": f"{ranks['top2']/max(len(grouped),1)*100:.1f}%"}, {"metric": "top3_win_rate", "value": f"{ranks['top3']/max(len(grouped),1)*100:.1f}%"}]
    for mode in ["production", "v5", "v5_1", "v5_2", "v6"]:
        summ += [{"metric": f"{mode}_log_loss", "value": f"{mean(metrics[f'{mode}_ll']):.6f}"}, {"metric": f"{mode}_brier", "value": f"{mean(metrics[f'{mode}_brier']):.6f}"}, {"metric": f"{mode}_avg_fav_price", "value": f"{mean(favs[mode]):.2f}"}, {"metric": f"{mode}_median_fav_price", "value": f"{median_value(favs[mode]):.2f}"}]
    prod_ll, v6_ll = mean(metrics["production_ll"]), mean(metrics["v6_ll"])
    prod_b, v6_b = mean(metrics["production_brier"]), mean(metrics["v6_brier"])
    verdict = "WEAK_REPLAY_SOURCE" if readiness != "STRONG_REPLAY" else "REPLAY_PASS" if v6_ll <= prod_ll and v6_b <= prod_b else "REPLAY_MIXED" if v6_ll <= prod_ll * 1.01 and v6_b <= prod_b * 1.01 else "REPLAY_FAIL"
    summ.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summ, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
