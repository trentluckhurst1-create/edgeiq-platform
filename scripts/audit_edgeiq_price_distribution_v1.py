import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
OUT = DATA / "edgeiq_price_distribution_audit_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_price_distribution_summary_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text(value: object) -> str:
    return str(value or "").strip()


def clean(value: object) -> str:
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def num(value: object) -> float | None:
    raw = text(value).replace("$", "").replace("%", "").replace(",", "")
    if not raw or raw.upper() in {"NA", "N/A", "--", "NULL"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def race_date(row: dict[str, str]) -> str:
    return text(row.get("race_date") or row.get("current_race_date") or row.get("date") or row.get("_date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number") or row.get("_race"))


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (race_date(row), clean(row.get("track") or row.get("_track")), race_no(row))


def is_scratched(row: dict[str, str]) -> bool:
    blob = " ".join(text(row.get(key)).upper() for key in ["display_decision", "runner_status", "scratch_status", "is_scratched"])
    return "SCRATCH" in blob or text(row.get("is_scratched")).upper() in {"YES", "TRUE", "1", "Y"}


def first_num(row: dict[str, str], keys: list[str]) -> float | None:
    for key in keys:
        value = num(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def prob_value(row: dict[str, str]) -> float | None:
    value = first_num(
        row,
        [
            "win_pct",
            "V6_1_RESEARCH_probability",
            "probability_normalised_v1",
            "rated_probability",
        ],
    )
    if value is None:
        price = fair_price(row)
        return 1 / price if price and price > 0 else None
    if value > 1:
        value = value / 100
    return max(0.0, min(1.0, value))


def fair_price(row: dict[str, str]) -> float | None:
    return first_num(
        row,
        [
            "display_fair_price",
            "ui_fair_price",
            "fair_price",
            "rated_price",
            "V6_1_RESEARCH_fair_price",
        ],
    )


def rating_value(row: dict[str, str]) -> float | None:
    return first_num(
        row,
        [
            "total_rating_points",
            "projected_rating_V6_1_RESEARCH",
            "projected_rating_v5_2",
            "adjusted_rating",
            "latest_flat_rating",
        ],
    )


def confidence_value(row: dict[str, str]) -> float | None:
    raw = text(row.get("projection_confidence_v5_2") or row.get("projection_band_v5_2") or row.get("projection_band_V6_1_RESEARCH")).upper()
    mapped = {
        "ELITE": 95,
        "HIGH": 85,
        "STRONG": 80,
        "POSITIVE": 70,
        "MEDIUM": 60,
        "MODERATE": 55,
        "NEUTRAL": 50,
        "LOW": 35,
        "LIMITED": 30,
        "WEAK": 25,
    }
    for token, value in mapped.items():
        if token in raw:
            return float(value)
    return first_num(row, ["confidence_score", "projection_confidence_v5_2", "map_confidence"])


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return (sum((value - avg) ** 2 for value in values) / len(values)) ** 0.5


def concentration(probs: list[float]) -> float:
    total = sum(probs)
    if total <= 0:
        return 0.0
    normalised = [value / total for value in probs if value > 0]
    return sum(value * value for value in normalised)


def entropy_ratio(probs: list[float]) -> float:
    total = sum(probs)
    if total <= 0 or len(probs) < 2:
        return 0.0
    normalised = [value / total for value in probs if value > 0]
    entropy = -sum(value * math.log(value) for value in normalised)
    return entropy / math.log(len(probs))


def likelihoods(field_size: int, top_prob: float, prob_gap: float, rating_gap: float, conf_avg: float, conf_sd: float, price_spread: float) -> dict[str, int]:
    scores = {
        "probability_flattening": 0,
        "rank_gap_translation": 0,
        "confidence_multipliers": 0,
        "field_size_normalisation": 0,
    }
    if top_prob < 0.24:
        scores["probability_flattening"] += 3
    if prob_gap < 0.035:
        scores["probability_flattening"] += 2
    if price_spread < 4:
        scores["probability_flattening"] += 1
    if rating_gap >= 8 and prob_gap < 0.05:
        scores["rank_gap_translation"] += 4
    elif rating_gap >= 5 and prob_gap < 0.04:
        scores["rank_gap_translation"] += 2
    if conf_avg < 55 or conf_sd < 6:
        scores["confidence_multipliers"] += 2
    if conf_avg < 45:
        scores["confidence_multipliers"] += 1
    if field_size >= 12 and top_prob < 0.22:
        scores["field_size_normalisation"] += 3
    elif field_size >= 10 and top_prob < 0.24:
        scores["field_size_normalisation"] += 2
    return scores


def rank_likelihood(scores: dict[str, int]) -> str:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(f"{name.upper()}={score}" for name, score in ranked)


def main() -> None:
    rows = [row for row in read_csv(RUNNER_BOARD) if not is_scratched(row)]
    by_race: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_race[race_key(row)].append(row)

    audit: list[dict[str, object]] = []
    class_counts: Counter[str] = Counter()
    no_under_counts: Counter[str] = Counter()
    root_totals: Counter[str] = Counter()

    for key, field in sorted(by_race.items()):
        prices = [fair_price(row) for row in field]
        prices = [value for value in prices if value is not None and value > 0]
        probs = [prob_value(row) for row in field]
        probs = [value for value in probs if value is not None and value > 0]
        ratings = sorted([rating_value(row) for row in field if rating_value(row) is not None], reverse=True)
        confidences = [confidence_value(row) for row in field if confidence_value(row) is not None]

        field_size = len(field)
        top_price = min(prices) if prices else 0.0
        second_price = sorted(prices)[1] if len(prices) > 1 else 0.0
        price_spread = max(prices) - min(prices) if len(prices) > 1 else 0.0
        probs_sorted = sorted(probs, reverse=True)
        top_prob = probs_sorted[0] if probs_sorted else (1 / top_price if top_price else 0.0)
        second_prob = probs_sorted[1] if len(probs_sorted) > 1 else 0.0
        top2_prob = top_prob + second_prob
        prob_gap = top_prob - second_prob
        rating_gap = ratings[0] - ratings[1] if len(ratings) > 1 else 0.0
        conf_avg = mean(confidences)
        conf_sd = stdev(confidences)
        hhi = concentration(probs)
        entropy = entropy_ratio(probs)

        flags = {
            "no_under_3": all(price >= 3 for price in prices) if prices else True,
            "no_under_4": all(price >= 4 for price in prices) if prices else True,
            "no_under_5": all(price >= 5 for price in prices) if prices else True,
            "no_under_6": all(price >= 6 for price in prices) if prices else True,
        }
        for name, flagged in flags.items():
            if flagged:
                no_under_counts[name] += 1

        if flags["no_under_5"] or (top_prob < 0.22 and entropy > 0.88):
            race_class = "COMPRESSED"
        elif top_price < 2.5 or top_prob > 0.38 or hhi > 0.22:
            race_class = "OVER_DISPERSED"
        else:
            race_class = "HEALTHY"
        class_counts[race_class] += 1

        causes = likelihoods(field_size, top_prob, prob_gap, rating_gap, conf_avg, conf_sd, price_spread)
        for cause, score in causes.items():
            root_totals[cause] += score

        audit.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": field_size,
                "top_fair_price": f"{top_price:.2f}" if top_price else "",
                "second_fair_price": f"{second_price:.2f}" if second_price else "",
                "price_spread": f"{price_spread:.2f}",
                "no_horse_under_3": "YES" if flags["no_under_3"] else "NO",
                "no_horse_under_4": "YES" if flags["no_under_4"] else "NO",
                "no_horse_under_5": "YES" if flags["no_under_5"] else "NO",
                "no_horse_under_6": "YES" if flags["no_under_6"] else "NO",
                "top_probability": f"{top_prob:.4f}",
                "second_probability": f"{second_prob:.4f}",
                "top2_probability": f"{top2_prob:.4f}",
                "probability_gap_top2": f"{prob_gap:.4f}",
                "probability_concentration_hhi": f"{hhi:.4f}",
                "probability_entropy_ratio": f"{entropy:.4f}",
                "top_rating_gap": f"{rating_gap:.2f}",
                "confidence_avg": f"{conf_avg:.2f}",
                "confidence_sd": f"{conf_sd:.2f}",
                "price_distribution_class": race_class,
                "root_cause_likelihood_ranking": rank_likelihood(causes),
            }
        )

    root_ranking = sorted(root_totals.items(), key=lambda item: (-item[1], item[0]))
    summary = [
        {"metric": "race_rows", "value": len(audit)},
        {"metric": "active_runner_rows", "value": len(rows)},
        {"metric": "races_no_horse_under_3", "value": no_under_counts["no_under_3"]},
        {"metric": "races_no_horse_under_4", "value": no_under_counts["no_under_4"]},
        {"metric": "races_no_horse_under_5", "value": no_under_counts["no_under_5"]},
        {"metric": "races_no_horse_under_6", "value": no_under_counts["no_under_6"]},
        {"metric": "compressed_races", "value": class_counts["COMPRESSED"]},
        {"metric": "over_dispersed_races", "value": class_counts["OVER_DISPERSED"]},
        {"metric": "healthy_races", "value": class_counts["HEALTHY"]},
        {"metric": "root_cause_likelihood_ranking", "value": "; ".join(f"{name.upper()}={score}" for name, score in root_ranking)},
    ]

    write_csv(
        OUT,
        audit,
        [
            "race_date",
            "track",
            "race_no",
            "field_size",
            "top_fair_price",
            "second_fair_price",
            "price_spread",
            "no_horse_under_3",
            "no_horse_under_4",
            "no_horse_under_5",
            "no_horse_under_6",
            "top_probability",
            "second_probability",
            "top2_probability",
            "probability_gap_top2",
            "probability_concentration_hhi",
            "probability_entropy_ratio",
            "top_rating_gap",
            "confidence_avg",
            "confidence_sd",
            "price_distribution_class",
            "root_cause_likelihood_ranking",
        ],
    )
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(audit)} rows)")


if __name__ == "__main__":
    main()
