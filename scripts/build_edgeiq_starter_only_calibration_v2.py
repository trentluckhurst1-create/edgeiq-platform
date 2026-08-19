from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"

OUT_MAIN = DATA / "edgeiq_starter_only_calibration_v2.csv"
OUT_PRICE_BAND = DATA / "edgeiq_starter_only_calibration_by_price_band_v2.csv"
OUT_PROB_BAND = DATA / "edgeiq_starter_only_calibration_by_probability_band_v2.csv"
OUT_AUDIT = DATA / "edgeiq_starter_only_calibration_v2_audit.csv"

MAIN_COLUMNS = [
    "scope",
    "runners",
    "races",
    "expected_winners",
    "actual_winners",
    "actual_minus_expected",
    "actual_to_expected_ratio",
    "avg_original_probability",
    "avg_starter_only_probability",
    "avg_original_price",
    "avg_starter_only_price",
]

BAND_COLUMNS = [
    "band",
    "runners",
    "expected_winners",
    "actual_winners",
    "actual_minus_expected",
    "actual_to_expected_ratio",
    "avg_starter_only_probability",
    "avg_starter_only_price",
]

AUDIT_COLUMNS = [
    "section",
    "metric",
    "value",
    "notes",
    "built_at",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def txt(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = str(row.get(name, "")).strip()
        if value:
            return value
    return ""


def num(value: object) -> float:
    try:
        if value is None:
            return 0.0
        s = str(value).strip()
        if not s:
            return 0.0
        return float(s)
    except ValueError:
        return 0.0


def is_true(value: object) -> bool:
    return str(value).strip().upper() in {"TRUE", "YES", "Y", "1", "WINNER", "WON"}


def audit(section: str, metric: str, value: object, notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "notes": notes,
        "built_at": now_utc(),
    }


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        txt(row, "race_date", "date"),
        txt(row, "track"),
        txt(row, "race_no", "race_number"),
    )


def price_band(price: float) -> str:
    if price < 2:
        return "FAV_UNDER_2"
    if price < 4:
        return "2_TO_4"
    if price < 8:
        return "4_TO_8"
    if price < 15:
        return "8_TO_15"
    if price < 30:
        return "15_TO_30"
    return "30_PLUS"


def probability_band(prob: float) -> str:
    pct = prob * 100
    if pct < 5:
        return "0_TO_5"
    if pct < 10:
        return "5_TO_10"
    if pct < 20:
        return "10_TO_20"
    if pct < 30:
        return "20_TO_30"
    return "30_PLUS"


def summarise(scope: str, rows: list[dict[str, object]]) -> dict[str, object]:
    runners = len(rows)
    races = len({r["race_key"] for r in rows})
    expected = sum(float(r["starter_only_probability"]) for r in rows)
    actual = sum(1 for r in rows if r["won"] == "TRUE")
    ratio = actual / expected if expected else 0.0
    avg_original_prob = sum(float(r["original_probability"]) for r in rows) / runners if runners else 0.0
    avg_starter_prob = expected / runners if runners else 0.0
    original_prices = [float(r["original_price"]) for r in rows if float(r["original_price"]) > 0]
    starter_prices = [float(r["starter_only_price"]) for r in rows if float(r["starter_only_price"]) > 0]

    return {
        "scope": scope,
        "runners": runners,
        "races": races,
        "expected_winners": round(expected, 6),
        "actual_winners": actual,
        "actual_minus_expected": round(actual - expected, 6),
        "actual_to_expected_ratio": round(ratio, 6),
        "avg_original_probability": round(avg_original_prob, 8),
        "avg_starter_only_probability": round(avg_starter_prob, 8),
        "avg_original_price": round(sum(original_prices) / len(original_prices), 6) if original_prices else "",
        "avg_starter_only_price": round(sum(starter_prices) / len(starter_prices), 6) if starter_prices else "",
    }


def summarise_band(band: str, rows: list[dict[str, object]]) -> dict[str, object]:
    runners = len(rows)
    expected = sum(float(r["starter_only_probability"]) for r in rows)
    actual = sum(1 for r in rows if r["won"] == "TRUE")
    ratio = actual / expected if expected else 0.0
    prices = [float(r["starter_only_price"]) for r in rows if float(r["starter_only_price"]) > 0]

    return {
        "band": band,
        "runners": runners,
        "expected_winners": round(expected, 6),
        "actual_winners": actual,
        "actual_minus_expected": round(actual - expected, 6),
        "actual_to_expected_ratio": round(ratio, 6),
        "avg_starter_only_probability": round(expected / runners, 8) if runners else "",
        "avg_starter_only_price": round(sum(prices) / len(prices), 6) if prices else "",
    }


def main() -> None:
    history = read_csv(HISTORY)
    snapshots = sorted({txt(r, "snapshot_timestamp") for r in history if txt(r, "snapshot_timestamp")})
    latest_snapshot = snapshots[-1] if snapshots else ""

    latest_rows = [r for r in history if txt(r, "snapshot_timestamp") == latest_snapshot]
    starters = [r for r in latest_rows if txt(r, "result_status").upper() in {"FINAL", "FAILED_TO_FINISH"}]
    scratched = [r for r in latest_rows if txt(r, "result_status").upper() == "CONFIRMED_SCRATCHED"]

    by_race: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in starters:
        by_race[race_key(row)].append(row)

    calibrated: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []

    for rk, race_rows in sorted(by_race.items()):
        starter_prob_sum = sum(num(txt(r, "edgeiq_probability", "rated_probability")) for r in race_rows)
        audit_rows.append(
            audit(
                "race_probability",
                "|".join(rk),
                round(starter_prob_sum, 8),
                "Starter-only original probability sum before renormalisation.",
            )
        )

        for row in race_rows:
            original_prob = num(txt(row, "edgeiq_probability", "rated_probability"))
            original_price = num(txt(row, "edgeiq_price", "rated_price"))
            starter_prob = original_prob / starter_prob_sum if starter_prob_sum else 0.0
            starter_price = 1 / starter_prob if starter_prob > 0 else 0.0
            calibrated.append(
                {
                    "snapshot_timestamp": latest_snapshot,
                    "race_key": "|".join(rk),
                    "race_date": rk[0],
                    "track": rk[1],
                    "race_no": rk[2],
                    "horse": txt(row, "horse"),
                    "horse_key": txt(row, "horse_key"),
                    "result_status": txt(row, "result_status"),
                    "won": "TRUE" if is_true(txt(row, "won")) else "FALSE",
                    "original_probability": original_prob,
                    "original_price": original_price,
                    "starter_only_probability": starter_prob,
                    "starter_only_price": starter_price,
                    "price_band": price_band(starter_price),
                    "probability_band": probability_band(starter_prob),
                }
            )

    main_rows = [summarise("LATEST_SNAPSHOT_STARTERS_ONLY", calibrated)]

    price_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    prob_groups: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in calibrated:
        price_groups[str(row["price_band"])].append(row)
        prob_groups[str(row["probability_band"])].append(row)

    price_band_rows = [summarise_band(band, price_groups.get(band, [])) for band in ["FAV_UNDER_2", "2_TO_4", "4_TO_8", "8_TO_15", "15_TO_30", "30_PLUS"]]
    prob_band_rows = [summarise_band(band, prob_groups.get(band, [])) for band in ["0_TO_5", "5_TO_10", "10_TO_20", "20_TO_30", "30_PLUS"]]

    audit_rows.extend(
        [
            audit("input", "history_rows_loaded", len(history)),
            audit("input", "latest_snapshot_timestamp", latest_snapshot),
            audit("input", "latest_snapshot_rows", len(latest_rows)),
            audit("calibration", "starters_included", len(starters)),
            audit("calibration", "scratchings_excluded", len(scratched)),
            audit("calibration", "races", len(by_race)),
            audit("calibration", "winners", sum(1 for r in calibrated if r["won"] == "TRUE")),
            audit("calibration", "expected_winners", main_rows[0]["expected_winners"]),
            audit("calibration", "actual_winners", main_rows[0]["actual_winners"]),
            audit("calibration", "actual_to_expected_ratio", main_rows[0]["actual_to_expected_ratio"]),
            audit("status", "calibration_status", "STARTER_ONLY_CALIBRATION_READY"),
            audit("status", "sample_warning", "SAMPLE_TOO_SMALL_ONE_MEETING_ONLY"),
        ]
    )

    write_csv(OUT_MAIN, main_rows, MAIN_COLUMNS)
    write_csv(OUT_PRICE_BAND, price_band_rows, BAND_COLUMNS)
    write_csv(OUT_PROB_BAND, prob_band_rows, BAND_COLUMNS)
    write_csv(OUT_AUDIT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ STARTER-ONLY CALIBRATION V2")
    print("=" * 96)
    print(f"wrote: {OUT_MAIN}")
    print(f"wrote: {OUT_PRICE_BAND}")
    print(f"wrote: {OUT_PROB_BAND}")
    print(f"wrote: {OUT_AUDIT}")
    print("")
    for row in audit_rows:
        if row["section"] in {"input", "calibration", "status"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
