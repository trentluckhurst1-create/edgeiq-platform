import math
from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, format_float, mean, median_value, num, race_key, read_csv, text, write_csv

SRC = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
OUT = DATA / "edgeiq_probability_research_v5_1_historical_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_1_historical_replay_summary.csv"


def prob(row):
    value = num(row.get("V6_1_RESEARCH_probability")) or 0
    return value / 100 if value > 1 else value


def won(row):
    return 1 if text(row.get("won")).upper() in {"1", "YES", "TRUE"} else 0


def gap(row):
    return num(row.get("projection_gap_V6_1_RESEARCH")) or 0


def ll(p, y):
    p = max(0.001, min(0.999, p))
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def replay_probs(field, mode):
    ranked = sorted(field, key=prob, reverse=True)
    gaps = sorted([gap(r) for r in ranked], reverse=True)
    gap12 = abs(gaps[0] - gaps[1]) if len(gaps) > 1 else 0
    if mode == "production":
        vals = [prob(r) for r in ranked]
    else:
        temp = 0.78 if gap12 >= 6 else 0.88 if gap12 >= 3 else 1.02
        if mode == "v5_1":
            temp = 0.84 if gap12 >= 6 else 0.94 if gap12 >= 3 else 1.04
        vals = [max(0.0001, prob(r)) ** (1 / temp) for r in ranked]
    total = sum(vals) or 1
    vals = [v / total for v in vals]
    cap = 0.43 if mode == "v5" else 0.39 if mode == "v5_1" else 1.0
    if vals and max(vals) > cap:
        i = vals.index(max(vals)); excess = vals[i] - cap; vals[i] = cap
        others = [j for j in range(len(vals)) if j != i]
        ot = sum(vals[j] for j in others) or 1
        for j in others:
            vals[j] += excess * vals[j] / ot
    total = sum(vals) or 1
    return ranked, [v / total for v in vals]


def main():
    rows = [r for r in read_csv(SRC) if prob(r) > 0 and race_key(r)[0] and race_key(r)[2]]
    grouped = defaultdict(list)
    for r in rows:
        grouped[race_key(r)].append(r)
    if len(grouped) < 25:
        write_csv(OUT, [], [])
        write_csv(OUT_SUMMARY, [{"metric": "verdict", "value": "HISTORICAL_REPLAY_WEAK_SOURCE"}, {"metric": "race_rows", "value": len(grouped)}], ["metric", "value"])
        print("HISTORICAL_REPLAY_WEAK_SOURCE")
        return
    out, metrics, favs = [], defaultdict(list), defaultdict(list)
    rank = Counter()
    for key, field in sorted(grouped.items()):
        mode_probs = {m: replay_probs(field, m) for m in ["production", "v5", "v5_1"]}
        winners = [i for i, row in enumerate(mode_probs["production"][0]) if won(row)]
        if winners:
            pos = min(winners) + 1
            if pos == 1: rank["rank1"] += 1
            if pos <= 3: rank["top3"] += 1
        for mode, (ranked, vals) in mode_probs.items():
            favs[mode].append(1 / vals[0] if vals and vals[0] else 0)
            for row, p in zip(ranked, vals):
                y = won(row)
                metrics[f"{mode}_ll"].append(ll(p, y))
                metrics[f"{mode}_brier"].append((p - y) ** 2)
        for row, p_prod in zip(*mode_probs["production"]):
            horse = row.get("horse", "")
            idx_v5 = next((i for i, r in enumerate(mode_probs["v5"][0]) if r.get("horse") == horse), -1)
            idx_v51 = next((i for i, r in enumerate(mode_probs["v5_1"][0]) if r.get("horse") == horse), -1)
            out.append({"race_date": key[0], "track": text(row.get("track")), "race_no": key[2], "horse": horse, "production_probability": format_float(p_prod, 4), "v5_probability": format_float(mode_probs["v5"][1][idx_v5] if idx_v5 >= 0 else 0, 4), "v5_1_probability": format_float(mode_probs["v5_1"][1][idx_v51] if idx_v51 >= 0 else 0, 4), "won": won(row)})
    summary = [{"metric": "source_file", "value": SRC.name}, {"metric": "race_rows", "value": len(grouped)}, {"metric": "runner_rows", "value": len(out)}, {"metric": "rank1_win_rate", "value": f"{rank['rank1']/len(grouped)*100:.1f}%"}, {"metric": "top3_win_coverage", "value": f"{rank['top3']/len(grouped)*100:.1f}%"}]
    for mode in ["production", "v5", "v5_1"]:
        summary += [{"metric": f"{mode}_avg_log_loss", "value": f"{mean(metrics[f'{mode}_ll']):.6f}"}, {"metric": f"{mode}_avg_brier", "value": f"{mean(metrics[f'{mode}_brier']):.6f}"}, {"metric": f"{mode}_avg_favourite_price", "value": f"{mean(favs[mode]):.2f}"}, {"metric": f"{mode}_median_favourite_price", "value": f"{median_value(favs[mode]):.2f}"}]
    verdict = "V5_1_REPLAY_OK" if mean(metrics["v5_1_ll"]) <= mean(metrics["v5_ll"]) and mean(metrics["v5_1_brier"]) <= mean(metrics["v5_brier"]) else "HISTORICAL_REPLAY_WEAK_SOURCE"
    summary.append({"metric": "verdict", "value": verdict})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
