import math
from collections import Counter, defaultdict
from edgeiq_pricing_research_common import DATA, read_csv, write_csv, num, mean, median_value, format_float

SPINE = DATA / "edgeiq_pricing_replay_spine_v2.csv"
SUMMARY = DATA / "edgeiq_pricing_replay_spine_v2_summary.csv"
OUT = DATA / "edgeiq_probability_v6_expanded_replay_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_v6_expanded_replay_summary_v1.csv"


def ll(p, y):
    p = max(.001, min(.999, p)); return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def mode_probs(rows, mode):
    base = [num(r["production_probability_replay"]) or .0001 for r in rows]
    temps = {"production": 1, "v5": .88, "v5_1": .94, "v5_2": .99, "v6": .96}
    vals = [b ** (1 / temps[mode]) for b in base]
    total = sum(vals) or 1
    vals = [v / total for v in vals]
    cap = {"production": 1, "v5": .43, "v5_1": .39, "v5_2": .36, "v6": .36}[mode]
    if vals and max(vals) > cap:
        i = vals.index(max(vals)); excess = vals[i] - cap; vals[i] = cap
        rest = [j for j in range(len(vals)) if j != i]; rt = sum(vals[j] for j in rest) or 1
        for j in rest: vals[j] += excess * vals[j] / rt
    total = sum(vals) or 1
    return [v / total for v in vals]


def main():
    spine_summary = {r["metric"]: r["value"] for r in read_csv(SUMMARY)}
    grouped = defaultdict(list)
    for r in read_csv(SPINE):
        if r["replay_ready_flag"] == "YES":
            grouped[(r["race_date"], r["track"], r["race_no"])].append(r)
    out, metrics, favs, ranks = [], defaultdict(list), defaultdict(list), Counter()
    for key, rows in sorted(grouped.items()):
        modes = {m: mode_probs(rows, m) for m in ["production", "v5", "v5_1", "v5_2", "v6"]}
        order = sorted(range(len(rows)), key=lambda i: modes["production"][i], reverse=True)
        winner_positions = [order.index(i) + 1 for i, r in enumerate(rows) if str(r["won"]) == "1" and i in order]
        if winner_positions:
            pos = min(winner_positions)
            if pos <= 1: ranks["rank1"] += 1
            if pos <= 2: ranks["top2"] += 1
            if pos <= 3: ranks["top3"] += 1
        for m, probs in modes.items():
            favs[m].append(1 / max(probs) if probs else 0)
            for r, p in zip(rows, probs):
                y = 1 if str(r["won"]) == "1" else 0
                split = r["probability_source"].lower()
                metrics[f"{m}_ll"].append(ll(p, y)); metrics[f"{m}_brier"].append((p - y) ** 2)
                metrics[f"{split}_{m}_ll"].append(ll(p, y)); metrics[f"{split}_{m}_brier"].append((p - y) ** 2)
        for r, p in zip(rows, modes["production"]):
            out.append({"race_date": key[0], "track": key[1], "race_no": key[2], "horse": r["horse"], "probability_source": r["probability_source"], "production_probability": format_float(p, 6), "v6_probability": format_float(modes["v6"][rows.index(r)], 6), "won": r["won"]})
    summary = [{"metric": "spine_readiness", "value": spine_summary.get("readiness", "")}, {"metric": "race_rows", "value": len(grouped)}, {"metric": "runner_rows", "value": len(out)}, {"metric": "rank1_win_rate", "value": f"{ranks['rank1']/max(len(grouped),1)*100:.1f}%"}, {"metric": "top2_win_rate", "value": f"{ranks['top2']/max(len(grouped),1)*100:.1f}%"}, {"metric": "top3_win_rate", "value": f"{ranks['top3']/max(len(grouped),1)*100:.1f}%"}]
    for m in ["production", "v5", "v5_1", "v5_2", "v6"]:
        summary += [{"metric": f"{m}_log_loss", "value": f"{mean(metrics[f'{m}_ll']):.6f}"}, {"metric": f"{m}_brier", "value": f"{mean(metrics[f'{m}_brier']):.6f}"}, {"metric": f"{m}_avg_fav_price", "value": f"{mean(favs[m]):.2f}"}, {"metric": f"{m}_median_fav_price", "value": f"{median_value(favs[m]):.2f}"}]
        for split in ["archived", "backfilled"]:
            summary += [{"metric": f"{split}_{m}_log_loss", "value": f"{mean(metrics[f'{split}_{m}_ll']):.6f}"}, {"metric": f"{split}_{m}_brier", "value": f"{mean(metrics[f'{split}_{m}_brier']):.6f}"}]
    ready = spine_summary.get("readiness", "")
    verdict = "REPLAY_STILL_WEAK" if ready == "WEAK_REPLAY" else "V6_REPLAY_PASS" if mean(metrics["v6_ll"]) <= mean(metrics["production_ll"]) and mean(metrics["v6_brier"]) <= mean(metrics["production_brier"]) else "V6_REPLAY_MIXED"
    summary.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
