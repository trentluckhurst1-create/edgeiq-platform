import math
from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, format_float, mean, median_value, num, race_key, read_csv, text, write_csv

SRC = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
OUT = DATA / "edgeiq_probability_research_v5_2_historical_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_2_historical_replay_summary.csv"


def p(row):
    v = num(row.get("V6_1_RESEARCH_probability")) or 0
    return v / 100 if v > 1 else v


def won(row):
    return 1 if text(row.get("won")).upper() in {"1", "YES", "TRUE"} else 0


def gap(row):
    return num(row.get("projection_gap_V6_1_RESEARCH")) or 0


def ll(prob, y):
    prob = max(0.001, min(0.999, prob))
    return -(y * math.log(prob) + (1 - y) * math.log(1 - prob))


def mode_probs(field, mode):
    ranked = sorted(field, key=p, reverse=True)
    gaps = sorted([gap(r) for r in ranked], reverse=True)
    gap12 = abs(gaps[0] - gaps[1]) if len(gaps) > 1 else 0
    if mode == "production":
        vals = [p(r) for r in ranked]
    else:
        temps = {"v5": (0.78, 0.88, 1.02), "v5_1": (0.84, 0.94, 1.04), "v5_2": (0.90, 0.99, 1.05)}
        a, b, c = temps[mode]
        temp = a if gap12 >= 6 else b if gap12 >= 3 else c
        vals = [max(0.0001, p(r)) ** (1 / temp) for r in ranked]
    total = sum(vals) or 1
    vals = [v / total for v in vals]
    caps = {"production": 1.0, "v5": 0.43, "v5_1": 0.39, "v5_2": 0.36}
    cap = caps[mode]
    if vals and max(vals) > cap:
        i = vals.index(max(vals)); excess = vals[i] - cap; vals[i] = cap
        others = [j for j in range(len(vals)) if j != i]
        ot = sum(vals[j] for j in others) or 1
        for j in others:
            vals[j] += excess * vals[j] / ot
    total = sum(vals) or 1
    return ranked, [v / total for v in vals]


def main():
    rows = [r for r in read_csv(SRC) if p(r) > 0 and race_key(r)[0] and race_key(r)[2]]
    grouped = defaultdict(list)
    for r in rows:
        grouped[race_key(r)].append(r)
    out, metrics, favs = [], defaultdict(list), defaultdict(list)
    ranks = Counter()
    for key, field in sorted(grouped.items()):
        all_modes = {m: mode_probs(field, m) for m in ["production", "v5", "v5_1", "v5_2"]}
        winners = [i for i, row in enumerate(all_modes["production"][0]) if won(row)]
        if winners:
            pos = min(winners) + 1
            if pos == 1: ranks["rank1"] += 1
            if pos <= 3: ranks["top3"] += 1
        for mode, (ranked, vals) in all_modes.items():
            favs[mode].append(1 / vals[0] if vals and vals[0] else 0)
            for row, prob in zip(ranked, vals):
                y = won(row)
                metrics[f"{mode}_ll"].append(ll(prob, y))
                metrics[f"{mode}_brier"].append((prob - y) ** 2)
        for row, prob in zip(*all_modes["production"]):
            horse = row.get("horse", "")
            rec = {"race_date": key[0], "track": text(row.get("track")), "race_no": key[2], "horse": horse, "production_probability": format_float(prob, 4), "won": won(row)}
            for mode in ["v5", "v5_1", "v5_2"]:
                idx = next((i for i, r in enumerate(all_modes[mode][0]) if r.get("horse") == horse), -1)
                rec[f"{mode}_probability"] = format_float(all_modes[mode][1][idx] if idx >= 0 else 0, 4)
            out.append(rec)
    summary = [{"metric": "source_file", "value": SRC.name}, {"metric": "race_rows", "value": len(grouped)}, {"metric": "runner_rows", "value": len(out)}, {"metric": "rank1_win", "value": f"{ranks['rank1']/max(len(grouped),1)*100:.1f}%"}, {"metric": "top3_win_coverage", "value": f"{ranks['top3']/max(len(grouped),1)*100:.1f}%"}]
    for mode in ["production", "v5", "v5_1", "v5_2"]:
        summary += [{"metric": f"{mode}_avg_log_loss", "value": f"{mean(metrics[f'{mode}_ll']):.6f}"}, {"metric": f"{mode}_avg_brier", "value": f"{mean(metrics[f'{mode}_brier']):.6f}"}, {"metric": f"{mode}_avg_favourite_price", "value": f"{mean(favs[mode]):.2f}"}, {"metric": f"{mode}_median_favourite_price", "value": f"{median_value(favs[mode]):.2f}"}]
    summary.append({"metric": "verdict", "value": "HISTORICAL_REPLAY_WEAK_SOURCE"})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
