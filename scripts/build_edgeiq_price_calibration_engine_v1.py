from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_price_truth_history_v1.csv"
OVERALL_OUT = DATA / "edgeiq_price_calibration_engine_v1.csv"
PRICE_BAND_OUT = DATA / "edgeiq_price_calibration_by_price_band_v1.csv"
PROBABILITY_BAND_OUT = DATA / "edgeiq_price_calibration_by_probability_band_v1.csv"
QUALITY_CLASS_OUT = DATA / "edgeiq_price_calibration_by_quality_class_v1.csv"
DISCIPLINE_CLASS_OUT = DATA / "edgeiq_price_calibration_by_discipline_class_v1.csv"
AUDIT_OUT = DATA / "edgeiq_price_calibration_engine_v1_audit.csv"

STARTER_STATUSES = {"FINAL", "FAILED_TO_FINISH"}
SCRATCHED_STATUS = "CONFIRMED_SCRATCHED"
CALIBRATION_STATUS = "CALIBRATION_SAMPLE_TOO_SMALL"
CALIBRATION_NOTE = "Only four snapshots of one Sandown meeting are available; research output only, no price adjustment."

CALIBRATION_COLUMNS = [
    "segment_type",
    "segment",
    "runners",
    "expected_winners",
    "actual_winners",
    "calibration_delta",
    "actual_minus_expected",
    "actual_to_expected_ratio",
    "avg_edgeiq_price",
    "avg_sportsbet_price",
    "avg_overlay_pct",
    "calibration_status",
    "notes",
]

AUDIT_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def to_float(value: object) -> float | None:
    text = clean(value).replace("$", "").replace("%", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_bool(value: object) -> bool:
    return clean(value).upper() in {"TRUE", "YES", "Y", "1"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def price_band(edgeiq_price: float | None) -> str:
    if edgeiq_price is None:
        return "UNKNOWN_PRICE"
    if edgeiq_price < 2:
        return "FAV_UNDER_2"
    if edgeiq_price < 4:
        return "2_TO_4"
    if edgeiq_price < 8:
        return "4_TO_8"
    if edgeiq_price < 15:
        return "8_TO_15"
    if edgeiq_price < 30:
        return "15_TO_30"
    return "30_PLUS"


def probability_band(probability: float | None) -> str:
    if probability is None:
        return "UNKNOWN_PROBABILITY"
    if probability < 0.05:
        return "0_TO_5"
    if probability < 0.10:
        return "5_TO_10"
    if probability < 0.20:
        return "10_TO_20"
    if probability < 0.30:
        return "20_TO_30"
    return "30_PLUS"


def starter_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if clean(row.get("result_status")) in STARTER_STATUSES]


def calibration_row(segment_type: str, segment: str, rows: list[dict[str, str]]) -> dict[str, object]:
    runners = len(rows)
    probabilities = [to_float(row.get("edgeiq_probability")) or 0.0 for row in rows]
    expected_winners = sum(probabilities)
    actual_winners = sum(1 for row in rows if to_bool(row.get("won")))
    actual_minus_expected = actual_winners - expected_winners
    ratio = actual_winners / expected_winners if expected_winners > 0 else None
    edgeiq_prices = [value for value in (to_float(row.get("edgeiq_price")) for row in rows) if value is not None]
    sportsbet_prices = [value for value in (to_float(row.get("sportsbet_price")) for row in rows) if value is not None]
    overlays = [value for value in (to_float(row.get("overlay_pct")) for row in rows) if value is not None]

    return {
        "segment_type": segment_type,
        "segment": segment,
        "runners": runners,
        "expected_winners": fmt(expected_winners),
        "actual_winners": actual_winners,
        "calibration_delta": fmt(actual_minus_expected),
        "actual_minus_expected": fmt(actual_minus_expected),
        "actual_to_expected_ratio": fmt(ratio),
        "avg_edgeiq_price": fmt(avg(edgeiq_prices)),
        "avg_sportsbet_price": fmt(avg(sportsbet_prices)),
        "avg_overlay_pct": fmt(avg(overlays)),
        "calibration_status": CALIBRATION_STATUS,
        "notes": CALIBRATION_NOTE,
    }


def grouped_calibration_rows(segment_type: str, groups: dict[str, list[dict[str, str]]], order: list[str] | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    if order:
        for segment in order:
            rows.append(calibration_row(segment_type, segment, groups.get(segment, [])))
            seen.add(segment)
    for segment in sorted(groups):
        if segment not in seen:
            rows.append(calibration_row(segment_type, segment, groups[segment]))
    return rows


def race_key(row: dict[str, str]) -> str:
    return "|".join([clean(row.get("race_date")), clean(row.get("track")).upper(), clean(row.get("race_no"))])


def audit_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_outputs(history_rows: list[dict[str, str]]) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    starters = starter_rows(history_rows)
    status_counts = Counter(clean(row.get("result_status")) for row in history_rows)

    price_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    probability_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    quality_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    discipline_groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in starters:
        price_groups[price_band(to_float(row.get("edgeiq_price")))].append(row)
        probability_groups[probability_band(to_float(row.get("edgeiq_probability")))].append(row)
        quality_groups[clean(row.get("quality_class")) or "UNKNOWN_QUALITY_CLASS"].append(row)
        discipline_groups[clean(row.get("discipline_class")) or "UNKNOWN_DISCIPLINE_CLASS"].append(row)

    overall_rows = [calibration_row("OVERALL", "ALL_STARTERS_EXCLUDING_SCRATCHED", starters)]
    price_rows = grouped_calibration_rows(
        "EDGEIQ_PRICE_BAND",
        price_groups,
        ["FAV_UNDER_2", "2_TO_4", "4_TO_8", "8_TO_15", "15_TO_30", "30_PLUS"],
    )
    probability_rows = grouped_calibration_rows(
        "EDGEIQ_PROBABILITY_BAND",
        probability_groups,
        ["0_TO_5", "5_TO_10", "10_TO_20", "20_TO_30", "30_PLUS"],
    )
    quality_rows = grouped_calibration_rows("QUALITY_CLASS", quality_groups)
    discipline_rows = grouped_calibration_rows("DISCIPLINE_CLASS", discipline_groups)

    expected_winners = sum(to_float(row.get("edgeiq_probability")) or 0.0 for row in starters)
    actual_winners = sum(1 for row in starters if to_bool(row.get("won")))
    audit_rows = [
        audit_row("input", "history_rows_loaded", len(history_rows), INPUT),
        audit_row("calibration", "starters_included", len(starters), INPUT, "Includes FINAL and FAILED_TO_FINISH rows."),
        audit_row("calibration", "scratched_excluded", status_counts.get(SCRATCHED_STATUS, 0), INPUT),
        audit_row("calibration", "final_rows_included", status_counts.get("FINAL", 0), INPUT),
        audit_row("calibration", "failed_to_finish_rows_included", status_counts.get("FAILED_TO_FINISH", 0), INPUT),
        audit_row("scope", "snapshots", len({clean(row.get("snapshot_timestamp")) for row in history_rows if clean(row.get("snapshot_timestamp"))}), INPUT),
        audit_row("scope", "races", len({race_key(row) for row in history_rows}), INPUT),
        audit_row("calibration", "winners", actual_winners, INPUT),
        audit_row("calibration", "expected_winners", fmt(expected_winners), INPUT),
        audit_row("status", "calibration_status", CALIBRATION_STATUS, AUDIT_OUT, CALIBRATION_NOTE),
        audit_row("output", "overall_rows", len(overall_rows), OVERALL_OUT),
        audit_row("output", "price_band_rows", len(price_rows), PRICE_BAND_OUT),
        audit_row("output", "probability_band_rows", len(probability_rows), PROBABILITY_BAND_OUT),
        audit_row("output", "quality_class_rows", len(quality_rows), QUALITY_CLASS_OUT),
        audit_row("output", "discipline_class_rows", len(discipline_rows), DISCIPLINE_CLASS_OUT),
    ]
    return overall_rows, price_rows, probability_rows, quality_rows, discipline_rows, audit_rows


def main() -> None:
    fieldnames, history_rows = read_csv(INPUT)
    required = {
        "snapshot_timestamp",
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "edgeiq_price",
        "edgeiq_probability",
        "sportsbet_price",
        "overlay_pct",
        "quality_class",
        "discipline_class",
        "result_status",
        "won",
    }
    missing = sorted(required.difference(fieldnames))
    if missing:
        raise ValueError(f"{INPUT} missing required columns: {missing}")

    overall_rows, price_rows, probability_rows, quality_rows, discipline_rows, audit_rows = build_outputs(history_rows)

    write_csv(OVERALL_OUT, overall_rows, CALIBRATION_COLUMNS)
    write_csv(PRICE_BAND_OUT, price_rows, CALIBRATION_COLUMNS)
    write_csv(PROBABILITY_BAND_OUT, probability_rows, CALIBRATION_COLUMNS)
    write_csv(QUALITY_CLASS_OUT, quality_rows, CALIBRATION_COLUMNS)
    write_csv(DISCIPLINE_CLASS_OUT, discipline_rows, CALIBRATION_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_COLUMNS)

    print("=" * 96)
    print("EDGEIQ PRICE CALIBRATION ENGINE V1 - RESEARCH ONLY")
    print("=" * 96)
    for row in audit_rows:
        if row["section"] in {"input", "calibration", "scope", "status"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {OVERALL_OUT}")
    print(f"wrote: {PRICE_BAND_OUT}")
    print(f"wrote: {PROBABILITY_BAND_OUT}")
    print(f"wrote: {QUALITY_CLASS_OUT}")
    print(f"wrote: {DISCIPLINE_CLASS_OUT}")
    print(f"wrote: {AUDIT_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
