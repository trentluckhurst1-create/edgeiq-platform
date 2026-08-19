from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

INPUT = DATA / "edgeiq_official_run_context_bridge_v1.csv"
OUT = DATA / "edgeiq_historical_performance_rating_v3.csv"
AUDIT_OUT = DATA / "edgeiq_historical_performance_rating_v3_audit.csv"

OUTPUT_FIELDS = [
    "horse",
    "race_date",
    "track",
    "distance",
    "race_class_clean",
    "condition_recovered",
    "source_file",
    "finish_pos_raw",
    "finish_position",
    "real_field_size",
    "real_field_size_source",
    "margin_raw",
    "margin",
    "performance_rating_v3",
    "performance_band_v3",
    "performance_reason_v3",
    "recovery_confidence",
]

AUDIT_FIELDS = [
    "section",
    "group_key",
    "metric",
    "value",
    "count",
    "avg_rating",
    "notes",
]

CLASS_CHECKS = ["BM58", "BM64", "BM70", "BM78", "BM84", "LISTED", "GROUP 1", "GROUP 2", "GROUP 3"]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    if upper(text) in {"NSE", "NOSE"}:
        return 0.05
    if upper(text) in {"SH", "SHORT HEAD"}:
        return 0.1
    if upper(text) in {"HD", "HEAD"}:
        return 0.2
    if "NK" in upper(text):
        return 0.3
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_int(value: object) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    rounded = int(round(number))
    return rounded if abs(number - rounded) < 0.001 else None


def parse_finish_position(value: object) -> int | None:
    text = upper(value)
    if not text:
        return None
    if any(flag in text for flag in ["SCR", "DNS", "DID NOT START", "ABANDON", "VOID", "FELL", "FAILED", "PULLED", "LOST RIDER"]):
        return None
    if re.match(r"^[TJ]\s+", text):
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    finish = int(match.group(0))
    return finish if finish >= 1 else None


def clean_class(value: object) -> str:
    text = upper(value)
    if not text:
        return "UNKNOWN"
    text = re.sub(r"\s+", " ", text)
    if "GROUP 1" in text or re.search(r"\bG1\b", text):
        return "GROUP 1"
    if "GROUP 2" in text or re.search(r"\bG2\b", text):
        return "GROUP 2"
    if "GROUP 3" in text or re.search(r"\bG3\b", text):
        return "GROUP 3"
    if "LISTED" in text or re.search(r"\bLR\b", text):
        return "LISTED"
    bm = re.search(r"\bBM\s?(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"
    if "MAIDEN" in text or re.search(r"\bMDN\b", text):
        return "MAIDEN"
    if "HANDICAP" in text or re.search(r"\bHCP\b", text):
        return "HANDICAP"
    if "OPEN" in text:
        return "OPEN"
    return text[:32]


def margin_scale(distance: float | None) -> float:
    if distance is None or not math.isfinite(distance):
        return 1.30
    if distance <= 1200:
        return 1.45
    if distance <= 1600:
        return 1.35
    if distance <= 2200:
        return 1.25
    if distance <= 3200:
        return 1.10
    return 0.95


def performance_band(rating: float) -> str:
    if rating >= 95:
        return "TOP_WINNING_RUN"
    if rating >= 85:
        return "STRONG_RUN"
    if rating >= 75:
        return "COMPETITIVE_RUN"
    if rating >= 65:
        return "FAIR_RUN"
    if rating >= 50:
        return "WEAK_RUN"
    return "POOR_RUN"


def performance_rating(finish: int, field_size: int, margin: float, distance: float | None) -> tuple[float, str]:
    rank_share = 0.0 if field_size <= 1 else (finish - 1) / (field_size - 1)
    rank_share = min(1.0, max(0.0, rank_share))

    position_penalty = 43.0 * (rank_share ** 0.72)
    field_size_context = max(-1.25, min(2.25, (field_size - 10) * 0.18))
    beaten_margin = 0.0 if finish == 1 else margin
    margin_points = min(30.0, beaten_margin * margin_scale(distance))

    raw = 94.0 + field_size_context - position_penalty - margin_points
    rating = max(12.0, min(109.0, raw))
    reason = (
        f"base=94.00 | field_size_context={field_size_context:.2f} | "
        f"rank_share={rank_share:.4f} | position_penalty={position_penalty:.2f} | "
        f"margin={beaten_margin:.2f} | margin_scale={margin_scale(distance):.2f} | "
        f"margin_points={margin_points:.2f}"
    )
    return round(rating, 2), reason


def audit_row(section: str, group_key: str, metric: str, value: object = "", count: object = "", avg_rating: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "group_key": group_key,
        "metric": metric,
        "value": value,
        "count": count,
        "avg_rating": avg_rating,
        "notes": notes,
    }


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows_loaded = 0
    dropped_invalid_finish = 0
    dropped_invalid_margin = 0
    dropped_invalid_field_size = 0
    output_rows: list[dict[str, object]] = []

    ratings_by_finish: dict[int, list[float]] = defaultdict(list)
    ratings_by_class: dict[str, list[float]] = defaultdict(list)
    field_size_counts: Counter[str] = Counter()

    with INPUT.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_loaded += 1
            finish_raw = clean(row.get("finish_pos"))
            finish = parse_finish_position(finish_raw)
            if finish is None:
                dropped_invalid_finish += 1
                continue

            field_size = parse_int(row.get("real_field_size"))
            if field_size is None or field_size < 2 or field_size > 30 or finish > field_size:
                dropped_invalid_field_size += 1
                continue

            margin_raw = clean(row.get("margin"))
            margin = parse_float(margin_raw)
            if finish == 1 and margin is None:
                margin = 0.0
            if margin is None or margin < 0:
                dropped_invalid_margin += 1
                continue

            distance = parse_float(row.get("distance"))
            rating, reason = performance_rating(finish, field_size, margin, distance)
            race_class_clean = clean_class(row.get("race_class"))

            output_rows.append(
                {
                    "horse": clean(row.get("horse")),
                    "race_date": clean(row.get("race_date")),
                    "track": clean(row.get("track")),
                    "distance": clean(row.get("distance")),
                    "race_class_clean": race_class_clean,
                    "condition_recovered": clean(row.get("track_condition")),
                    "source_file": clean(row.get("source_file")),
                    "finish_pos_raw": finish_raw,
                    "finish_position": finish,
                    "real_field_size": field_size,
                    "real_field_size_source": clean(row.get("real_field_size_source")),
                    "margin_raw": margin_raw,
                    "margin": round(0.0 if finish == 1 else margin, 2),
                    "performance_rating_v3": rating,
                    "performance_band_v3": performance_band(rating),
                    "performance_reason_v3": reason,
                    "recovery_confidence": clean(row.get("recovery_confidence")),
                }
            )
            ratings_by_finish[finish].append(rating)
            ratings_by_class[race_class_clean].append(rating)
            field_size_counts[str(field_size)] += 1

    audit_rows: list[dict[str, object]] = [
        audit_row("summary", "ALL", "rows_loaded", rows_loaded),
        audit_row("summary", "ALL", "rows_written", len(output_rows)),
        audit_row("summary", "ALL", "rows_dropped_invalid_finish", dropped_invalid_finish),
        audit_row("summary", "ALL", "rows_dropped_invalid_margin", dropped_invalid_margin),
        audit_row("summary", "ALL", "rows_dropped_invalid_field_size", dropped_invalid_field_size),
        audit_row("summary", "ALL", "ratings_ge_105", sum(1 for row in output_rows if float(row["performance_rating_v3"]) >= 105)),
        audit_row("summary", "ALL", "ratings_le_30", sum(1 for row in output_rows if float(row["performance_rating_v3"]) <= 30)),
    ]

    for finish in sorted(ratings_by_finish):
        values = ratings_by_finish[finish]
        audit_rows.append(
            audit_row("avg_by_finish_position", str(finish), "performance_rating_v3", "", len(values), round(average(values), 4))
        )

    for field_size in sorted(field_size_counts, key=lambda value: int(value)):
        audit_rows.append(audit_row("field_size_distribution", field_size, "runs", "", field_size_counts[field_size]))

    for klass in CLASS_CHECKS:
        values = ratings_by_class.get(klass, [])
        audit_rows.append(
            audit_row(
                "class_hierarchy_check",
                klass,
                "performance_rating_v3",
                "",
                len(values),
                round(average(values), 4) if values else "",
                "Class carried for audit only; not used in V3 formula.",
            )
        )

    output_rows.sort(key=lambda item: (str(item["race_date"]), str(item["track"]), str(item["horse"]), int(item["finish_position"])))
    write_csv(OUT, output_rows, OUTPUT_FIELDS)
    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("=" * 100)
    print("EDGEIQ HISTORICAL PERFORMANCE RATING V3")
    print("=" * 100)
    print(f"rows_loaded={rows_loaded}")
    print(f"rows_written={len(output_rows)}")
    print(f"rows_dropped_invalid_finish={dropped_invalid_finish}")
    print(f"rows_dropped_invalid_margin={dropped_invalid_margin}")
    print(f"rows_dropped_invalid_field_size={dropped_invalid_field_size}")
    print(f"ratings_ge_105={sum(1 for row in output_rows if float(row['performance_rating_v3']) >= 105)}")
    print(f"ratings_le_30={sum(1 for row in output_rows if float(row['performance_rating_v3']) <= 30)}")
    print()
    print("AVG BY FINISH POSITION")
    for finish in sorted(ratings_by_finish)[:15]:
        values = ratings_by_finish[finish]
        print(f"{finish}: count={len(values)} avg={average(values):.4f}")
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
