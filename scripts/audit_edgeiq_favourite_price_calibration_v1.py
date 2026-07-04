import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V6_1_CALIBRATION_DETAIL = DATA / "edgeiq_v6_1_probability_calibration_replay_v1_detail.csv"
MODEL_REVIEW = DATA / "model_result_review.csv"
RESULTS_MASTER = DATA / "edgeiq_results_master.csv"
OUT = DATA / "edgeiq_favourite_price_calibration_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_favourite_price_calibration_v1_summary.csv"


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
    return text(row.get("race_date") or row.get("meeting_date") or row.get("date"))


def race_no(row: dict[str, str]) -> str:
    return text(row.get("race_no") or row.get("race_number"))


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (race_date(row), clean(row.get("track")), race_no(row))


def first_num(row: dict[str, str], keys: list[str]) -> float | None:
    for key in keys:
        value = num(row.get(key))
        if value is not None and value > 0:
            return value
    return None


def market_price(row: dict[str, str]) -> float | None:
    return first_num(row, ["sp", "closing_price", "market_price", "fixed_odds", "win_odds"])


def edgeiq_price(row: dict[str, str]) -> float | None:
    return first_num(row, ["V6_1_RESEARCH_fair_price", "rated_price", "fair_price", "ui_fair_price", "display_fair_price"])


def won(row: dict[str, str]) -> bool:
    if text(row.get("won")).upper() in {"1", "YES", "TRUE", "Y"}:
        return True
    if text(row.get("result")).upper() in {"WIN", "WON", "1"}:
        return True
    return num(row.get("finish_pos")) == 1 or num(row.get("finish_pos_num")) == 1


def source_rows() -> tuple[str, list[dict[str, str]]]:
    calibration = read_csv(V6_1_CALIBRATION_DETAIL)
    usable_calibration = [row for row in calibration if market_price(row) and edgeiq_price(row) and race_key(row)[0] and race_key(row)[2]]
    if usable_calibration:
        return ("edgeiq_v6_1_probability_calibration_replay_v1_detail.csv", usable_calibration)
    review = read_csv(MODEL_REVIEW)
    usable_review = [row for row in review if market_price(row) and edgeiq_price(row) and race_key(row)[0] and race_key(row)[2]]
    if usable_review:
        return ("model_result_review.csv", usable_review)
    master = read_csv(RESULTS_MASTER)
    usable_master = [row for row in master if market_price(row) and edgeiq_price(row) and race_key(row)[0] and race_key(row)[2]]
    return ("edgeiq_results_master.csv", usable_master)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    source_name, rows = source_rows()
    by_race: defaultdict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_race[race_key(row)].append(row)

    out: list[dict[str, object]] = []
    for key, field in sorted(by_race.items()):
        market_candidates = [row for row in field if market_price(row)]
        edgeiq_candidates = [row for row in field if edgeiq_price(row)]
        if not market_candidates or not edgeiq_candidates:
            continue
        market_fav = min(market_candidates, key=lambda row: market_price(row) or 9999)
        edgeiq_fav = min(edgeiq_candidates, key=lambda row: edgeiq_price(row) or 9999)
        market_fav_market = market_price(market_fav) or 0.0
        market_fav_edgeiq = edgeiq_price(market_fav) or 0.0
        edgeiq_fav_market = market_price(edgeiq_fav) or 0.0
        edgeiq_fav_edgeiq = edgeiq_price(edgeiq_fav) or 0.0
        delta = market_fav_edgeiq - market_fav_market
        if delta >= 0.5:
            verdict = "EDGEIQ_TOO_LONG"
        elif delta <= -0.5:
            verdict = "EDGEIQ_TOO_SHORT"
        else:
            verdict = "ABOUT_RIGHT"
        out.append(
            {
                "race_date": key[0],
                "track": text(field[0].get("track")),
                "race_no": key[2],
                "field_size": len(field),
                "market_favourite": text(market_fav.get("horse")),
                "market_favourite_market_price": f"{market_fav_market:.2f}",
                "market_favourite_edgeiq_price": f"{market_fav_edgeiq:.2f}",
                "market_favourite_edgeiq_minus_market": f"{delta:.2f}",
                "market_favourite_won": "YES" if won(market_fav) else "NO",
                "edgeiq_favourite": text(edgeiq_fav.get("horse")),
                "edgeiq_favourite_edgeiq_price": f"{edgeiq_fav_edgeiq:.2f}",
                "edgeiq_favourite_market_price": f"{edgeiq_fav_market:.2f}",
                "edgeiq_favourite_won": "YES" if won(edgeiq_fav) else "NO",
                "same_favourite": "YES" if clean(market_fav.get("horse")) == clean(edgeiq_fav.get("horse")) else "NO",
                "calibration_verdict": verdict,
            }
        )

    market_prices = [float(row["market_favourite_market_price"]) for row in out]
    edgeiq_prices = [float(row["market_favourite_edgeiq_price"]) for row in out]
    deltas = [float(row["market_favourite_edgeiq_minus_market"]) for row in out]
    market_wins = sum(1 for row in out if row["market_favourite_won"] == "YES")
    edgeiq_wins = sum(1 for row in out if row["edgeiq_favourite_won"] == "YES")
    same_count = sum(1 for row in out if row["same_favourite"] == "YES")
    avg_delta = mean(deltas)
    if avg_delta >= 0.35:
        overall = "FAVOURITES_TOO_LONG"
    elif avg_delta <= -0.35:
        overall = "FAVOURITES_TOO_SHORT"
    else:
        overall = "ABOUT_RIGHT"

    summary = [
        {"metric": "source_file", "value": source_name},
        {"metric": "race_rows", "value": len(out)},
        {"metric": "avg_market_favourite_market_price", "value": f"{mean(market_prices):.2f}"},
        {"metric": "avg_market_favourite_edgeiq_price", "value": f"{mean(edgeiq_prices):.2f}"},
        {"metric": "avg_edgeiq_minus_market_price", "value": f"{avg_delta:.2f}"},
        {"metric": "market_favourite_win_rate", "value": f"{(market_wins / len(out) * 100) if out else 0:.1f}%"},
        {"metric": "edgeiq_favourite_win_rate", "value": f"{(edgeiq_wins / len(out) * 100) if out else 0:.1f}%"},
        {"metric": "same_market_and_edgeiq_favourite_rate", "value": f"{(same_count / len(out) * 100) if out else 0:.1f}%"},
        {"metric": "overall_favourite_calibration", "value": overall},
        {"metric": "verdict::EDGEIQ_TOO_LONG", "value": sum(1 for row in out if row["calibration_verdict"] == "EDGEIQ_TOO_LONG")},
        {"metric": "verdict::EDGEIQ_TOO_SHORT", "value": sum(1 for row in out if row["calibration_verdict"] == "EDGEIQ_TOO_SHORT")},
        {"metric": "verdict::ABOUT_RIGHT", "value": sum(1 for row in out if row["calibration_verdict"] == "ABOUT_RIGHT")},
    ]

    write_csv(
        OUT,
        out,
        [
            "race_date",
            "track",
            "race_no",
            "field_size",
            "market_favourite",
            "market_favourite_market_price",
            "market_favourite_edgeiq_price",
            "market_favourite_edgeiq_minus_market",
            "market_favourite_won",
            "edgeiq_favourite",
            "edgeiq_favourite_edgeiq_price",
            "edgeiq_favourite_market_price",
            "edgeiq_favourite_won",
            "same_favourite",
            "calibration_verdict",
        ],
    )
    write_csv(OUT_SUMMARY, summary, ["metric", "value"])
    print(f"Wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
