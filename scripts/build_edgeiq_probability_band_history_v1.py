from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORY = DATA / "edgeiq_price_truth_history_v1.csv"

OUT = DATA / "edgeiq_probability_band_history_v1.csv"
AUDIT = DATA / "edgeiq_probability_band_history_v1_audit.csv"

OUT_COLUMNS = [
    "meeting_date",
    "track",
    "snapshot_timestamp",
    "probability_band",
    "runners",
    "expected_winners",
    "actual_winners",
    "actual_minus_expected",
    "actual_to_expected_ratio",
    "avg_probability",
    "avg_price",
    "created_at",
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
    if not path.exists():
        return []
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
        text = str(value).strip()
        if not text:
            return 0.0
        return float(text)
    except Exception:
        return 0.0


def is_true(value: object) -> bool:
    return str(value).strip().upper() in {"TRUE", "YES", "Y", "1", "WON", "WINNER"}


def probability_band(probability: float) -> str:
    pct = probability * 100.0
    if pct < 5:
        return "0_TO_5"
    if pct < 10:
        return "5_TO_10"
    if pct < 20:
        return "10_TO_20"
    if pct < 30:
        return "20_TO_30"
    return "30_PLUS"


def audit(section: str, metric: str, value: object, notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "notes": notes,
        "built_at": now_utc(),
    }


def main() -> None:
    rows = read_csv(HISTORY)
    if not rows:
        raise RuntimeError(f"Missing or empty input: {HISTORY}")

    snapshots = sorted({txt(r, "snapshot_timestamp") for r in rows if txt(r, "snapshot_timestamp")})
    latest_snapshot = snapshots[-1] if snapshots else ""

    latest_rows = [r for r in rows if txt(r, "snapshot_timestamp") == latest_snapshot]
    starters = [r for r in latest_rows if txt(r, "result_status").upper() in {"FINAL", "FAILED_TO_FINISH"}]
    scratched = [r for r in latest_rows if txt(r, "result_status").upper() == "CONFIRMED_SCRATCHED"]

    race_dates = sorted({txt(r, "race_date", "date") for r in starters if txt(r, "race_date", "date")})
    tracks = sorted({txt(r, "track") for r in starters if txt(r, "track")})
    meeting_date = race_dates[0] if race_dates else "UNKNOWN"
    track = tracks[0] if tracks else "UNKNOWN"

    by_band: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in starters:
        probability = num(txt(row, "edgeiq_probability", "rated_probability"))
        band = probability_band(probability)
        by_band[band].append(row)

    output_rows: list[dict[str, object]] = []
    expected_total = 0.0
    actual_total = 0
    created_at = now_utc()

    for band in ["0_TO_5", "5_TO_10", "10_TO_20", "20_TO_30", "30_PLUS"]:
        band_rows = by_band.get(band, [])
        runners = len(band_rows)
        expected = sum(num(txt(r, "edgeiq_probability", "rated_probability")) for r in band_rows)
        actual = sum(1 for r in band_rows if is_true(txt(r, "won")))
        prices = [num(txt(r, "edgeiq_price", "rated_price")) for r in band_rows]
        prices = [p for p in prices if p > 0]
        avg_prob = expected / runners if runners else 0.0
        avg_price = sum(prices) / len(prices) if prices else 0.0
        ratio = actual / expected if expected else 0.0

        expected_total += expected
        actual_total += actual

        output_rows.append(
            {
                "meeting_date": meeting_date,
                "track": track,
                "snapshot_timestamp": latest_snapshot,
                "probability_band": band,
                "runners": runners,
                "expected_winners": round(expected, 6),
                "actual_winners": actual,
                "actual_minus_expected": round(actual - expected, 6),
                "actual_to_expected_ratio": round(ratio, 6),
                "avg_probability": round(avg_prob, 8),
                "avg_price": round(avg_price, 6) if avg_price else "",
                "created_at": created_at,
            }
        )

    bands_populated = sum(1 for row in output_rows if int(row["runners"]) > 0)

    audit_rows = [
        audit("input", "history_rows_loaded", len(rows), str(HISTORY)),
        audit("input", "latest_snapshot_timestamp", latest_snapshot),
        audit("input", "latest_snapshot_rows", len(latest_rows)),
        audit("calibration", "starters_included", len(starters)),
        audit("calibration", "scratchings_excluded", len(scratched)),
        audit("calibration", "bands_populated", bands_populated),
        audit("calibration", "expected_winners_total", round(expected_total, 6)),
        audit("calibration", "actual_winners_total", actual_total),
        audit("status", "status", "PROBABILITY_BAND_HISTORY_READY"),
        audit("status", "sample_warning", "SAMPLE_TOO_SMALL_ONE_MEETING_ONLY"),
    ]

    write_csv(OUT, output_rows, OUT_COLUMNS)
    write_csv(AUDIT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ PROBABILITY BAND HISTORY V1")
    print("=" * 96)
    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print("")
    for row in audit_rows:
        print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print("=" * 96)


if __name__ == "__main__":
    main()
