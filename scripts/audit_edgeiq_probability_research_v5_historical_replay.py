import math
from collections import Counter, defaultdict

from edgeiq_pricing_research_common import DATA, entropy_ratio, format_float, hhi, mean, median_value, num, race_key, read_csv, text, write_csv


SOURCE = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
OUT = DATA / "edgeiq_probability_research_v5_historical_replay.csv"
OUT_SUMMARY = DATA / "edgeiq_probability_research_v5_historical_replay_summary.csv"


def probability(row: dict[str, str]) -> float:
    value = num(row.get("V6_1_RESEARCH_probability")) or 0
    return value / 100 if value > 1 else value


def fair_price(row: dict[str, str]) -> float:
    return num(row.get("V6_1_RESEARCH_fair_price")) or (1 / probability(row) if probability(row) > 0 else 0)


def rating_gap(row: dict[str, str]) -> float:
    return num(row.get("projection_gap_V6_1_RESEARCH")) or 0


def won(row: dict[str, str]) -> int:
    return 1 if text(row.get("won")).upper() in {"1", "YES", "TRUE"} else 0


def sp(row: dict[str, str]) -> float:
    return num(row.get("sp")) or 0


def log_loss(p: float, y: int) -> float:
    p = max(0.001, min(0.999, p))
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def bucket(p: float) -> str:
    if p < 0.05:
        return "0_5"
    if p < 0.10:
        return "5_10"
    if p < 0.15:
        return "10_15"
    if p < 0.20:
        return "15_20"
    if p < 0.30:
        return "20_30"
    return "30_PLUS"


def main() -> None:
    source = [row for row in read_csv(SOURCE) if probability(row) > 0 and fair_price(row) > 0 and race_key(row)[0] and race_key(row)[2]]
    grouped: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in source:
        grouped[race_key(row)].append(row)

    if len(grouped) < 25:
        write_csv(OUT, [], [])
        write_csv(OUT_SUMMARY, [{"metric": "verdict", "value": "SOURCE_NOT_TRUSTWORTHY_OR_TOO_SMALL"}, {"metric": "race_rows", "value": len(grouped)}], ["metric", "value"])
        print("Historical replay source not trustworthy enough")
        return

    out = []
    bucket_rows: defaultdict[str, list[tuple[float, int]]] = defaultdict(list)
    prod_ll = []
    cand_ll = []
    prod_brier = []
    cand_brier = []
    prod_favs = []
    cand_favs = []
    rank_counts = Counter()
    for key, field in sorted(grouped.items()):
        ranked = sorted(field, key=lambda row: probability(row), reverse=True)
        gaps = sorted([rating_gap(row) for row in field], reverse=True)
        gap12 = abs(gaps[0] - gaps[1]) if len(gaps) > 1 else 0
        temp = 0.78 if gap12 >= 6 else 0.88 if gap12 >= 3 else 1.02
        scores = [(max(0.0001, probability(row)) ** (1 / temp)) for row in ranked]
        total = sum(scores) or 1
        cand_probs = [score / total for score in scores]
        if cand_probs and max(cand_probs) > 0.43:
            top_idx = cand_probs.index(max(cand_probs))
            excess = cand_probs[top_idx] - 0.43
            cand_probs[top_idx] = 0.43
            others = [i for i in range(len(cand_probs)) if i != top_idx]
            other_total = sum(cand_probs[i] for i in others) or 1
            for i in others:
                cand_probs[i] += excess * (cand_probs[i] / other_total)
        prod_favs.append(fair_price(ranked[0]))
        cand_favs.append(1 / cand_probs[0] if cand_probs[0] > 0 else 0)
        winners = [idx for idx, row in enumerate(ranked) if won(row)]
        if winners:
            pos = min(winners) + 1
            if pos <= 1:
                rank_counts["rank1_win"] += 1
            if pos <= 2:
                rank_counts["top2_win"] += 1
            if pos <= 3:
                rank_counts["top3_win"] += 1
        for idx, (row, cand_prob) in enumerate(zip(ranked, cand_probs), start=1):
            y = won(row)
            prod_prob = probability(row)
            prod_ll.append(log_loss(prod_prob, y))
            cand_ll.append(log_loss(cand_prob, y))
            prod_brier.append((prod_prob - y) ** 2)
            cand_brier.append((cand_prob - y) ** 2)
            bucket_rows[bucket(cand_prob)].append((cand_prob, y))
            out.append(
                {
                    "race_date": key[0],
                    "track": text(row.get("track")),
                    "race_no": key[2],
                    "horse": text(row.get("horse")),
                    "production_probability": format_float(prod_prob, 4),
                    "candidate_probability_v5": format_float(cand_prob, 4),
                    "production_fair_price": format_float(fair_price(row), 2),
                    "candidate_fair_price_v5": format_float(1 / cand_prob if cand_prob > 0 else 0, 2),
                    "sp": format_float(sp(row), 2),
                    "rank": idx,
                    "won": y,
                    "production_log_loss": format_float(log_loss(prod_prob, y), 6),
                    "candidate_log_loss": format_float(log_loss(cand_prob, y), 6),
                    "production_brier": format_float((prod_prob - y) ** 2, 6),
                    "candidate_brier": format_float((cand_prob - y) ** 2, 6),
                }
            )

    warnings = []
    avg_sp = mean([sp(row) for row in source if sp(row) > 0])
    if avg_sp <= 0:
        warnings.append("NO_SP_FOR_ROI_AE")
    summary = [
        {"metric": "source_file", "value": SOURCE.name},
        {"metric": "race_rows", "value": len(grouped)},
        {"metric": "runner_rows", "value": len(out)},
        {"metric": "rank1_win_rate", "value": f"{rank_counts['rank1_win'] / len(grouped) * 100:.1f}%"},
        {"metric": "top2_win_rate", "value": f"{rank_counts['top2_win'] / len(grouped) * 100:.1f}%"},
        {"metric": "top3_win_rate", "value": f"{rank_counts['top3_win'] / len(grouped) * 100:.1f}%"},
        {"metric": "production_avg_log_loss", "value": f"{mean(prod_ll):.6f}"},
        {"metric": "candidate_avg_log_loss", "value": f"{mean(cand_ll):.6f}"},
        {"metric": "production_avg_brier", "value": f"{mean(prod_brier):.6f}"},
        {"metric": "candidate_avg_brier", "value": f"{mean(cand_brier):.6f}"},
        {"metric": "production_favourite_avg_price", "value": f"{mean(prod_favs):.2f}"},
        {"metric": "candidate_favourite_avg_price", "value": f"{mean(cand_favs):.2f}"},
        {"metric": "production_favourite_median_price", "value": f"{median_value(prod_favs):.2f}"},
        {"metric": "candidate_favourite_median_price", "value": f"{median_value(cand_favs):.2f}"},
        {"metric": "candidate_entropy_average", "value": f"{mean([entropy_ratio([float(row['candidate_probability_v5']) for row in out])]) if out else 0:.4f}"},
        {"metric": "warnings", "value": "; ".join(warnings) or "NONE"},
    ]
    for key, values in sorted(bucket_rows.items()):
        summary.append({"metric": f"candidate_calibration_bucket::{key}", "value": f"n={len(values)} avg_p={mean([p for p, _ in values]):.3f} win_rate={mean([y for _, y in values]) * 100:.1f}%"})
    write_csv(OUT, out, list(out[0].keys()) if out else [])
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
