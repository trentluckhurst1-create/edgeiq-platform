from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "public" / "data"

LIVE_FEED_PATH = DATA_DIR / "edgeiq_vic_live_terminal_feed_v1.csv"
RACE_SHAPE_FIT_PATH = DATA_DIR / "edgeiq_race_shape_fit_v4.csv"
CLEAN_OVERLAY_PATH = DATA_DIR / "edgeiq_clean_overlay_review_board_v5_2.csv"
OVERLAY_QUALITY_PATH = DATA_DIR / "edgeiq_overlay_quality_audit_v5_2.csv"

OUTPUT_PATH = DATA_DIR / "edgeiq_top_opportunities_race_shape_fit_v4.csv"
SUMMARY_PATH = DATA_DIR / "edgeiq_top_opportunities_race_shape_fit_v4_summary.csv"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "edgeiq_price",
    "market_price",
    "edge_pct",
    "decision",
    "is_top_3_opportunity_in_race",
    "race_shape_fit_score",
    "fit_grade",
    "fit_confidence",
    "fit_reason",
    "risk_reason",
    "has_usable_fit",
    "ui_recommendation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def canonical_horse_key(value: str | None) -> str:
    raw = text(value).upper()
    pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({pattern})\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"[^A-Z0-9]+", "", raw)
    for suffix in COUNTRY_SUFFIXES:
        if raw.endswith(suffix) and len(raw) > len(suffix) + 3:
            return raw[: -len(suffix)]
    return raw


def normalise_track(value: str | None) -> str:
    raw = text(value).upper()
    raw = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", raw).strip()
    raw = re.sub(r"[^A-Z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def normalise_race_no(value: str | None) -> str:
    raw = text(value).upper()
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def runner_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        text(row.get("race_date")),
        normalise_track(row.get("track")),
        normalise_race_no(row.get("race_no")),
        canonical_horse_key(row.get("horse_key") or row.get("horse")),
    )


def race_key(row: dict[str, str]) -> tuple[str, str, str]:
    return runner_key(row)[:3]


def to_float(value: Any) -> float | None:
    raw = text(value)
    if not raw or raw.upper() in {"-", "NA", "N/A", "NULL", "NONE"}:
        return None
    cleaned = raw.replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_price(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else ""


def format_pct(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else ""


def first_number(row: dict[str, str], columns: list[str]) -> float | None:
    for column in columns:
        value = to_float(row.get(column))
        if value is not None and value > 0:
            return value
    return None


def edgeiq_price(row: dict[str, str]) -> float | None:
    return first_number(
        row,
        [
            "edgeiq_price",
            "rated_price",
            "ui_fair_price",
            "fair_price",
            "rated_price_v5_2_review",
            "current_rated_price",
        ],
    )


def market_price(row: dict[str, str]) -> float | None:
    return first_number(
        row,
        [
            "sportsbet_price",
            "market_price",
            "live_price",
            "ui_price",
            "fixed_win",
            "current_price",
        ],
    )


def edge_pct(row: dict[str, str], edgeiq: float | None, market: float | None) -> float | None:
    for column in ["edge_pct", "ui_edge_pct", "overlay_pct", "overlay_percentage_v5_2"]:
        value = to_float(row.get(column))
        if value is not None:
            return value
    if edgeiq is not None and market is not None and edgeiq > 0:
        return ((market / edgeiq) - 1.0) * 100.0
    return None


def is_active_runner(row: dict[str, str]) -> bool:
    fields = [
        text(row.get("is_scratched")).upper(),
        text(row.get("scratch_status")).upper(),
        text(row.get("runner_status")).upper(),
        text(row.get("ui_status")).upper(),
    ]
    scratched_tokens = {"TRUE", "YES", "Y", "SCR", "SCRATCHED", "CONFIRMED_SCRATCHED"}
    if any(value in scratched_tokens for value in fields):
        return False
    if any("SCRATCH" in value for value in fields if value):
        return False
    return True


def decision(row: dict[str, str], edge: float | None) -> str:
    existing = text(row.get("decision")) or text(row.get("execution_action")) or text(row.get("truth_grade"))
    if existing and existing not in {"-", "NO LIVE"}:
        return existing
    if edge is None:
        return existing or ""
    if edge >= 100:
        return "STRONG VALUE"
    if edge >= 25:
        return "VALUE"
    if edge >= 10:
        return "WATCH"
    if edge > -10:
        return "NEUTRAL"
    if edge > -25:
        return "UNDERLAY"
    return "AVOID"


def has_usable_fit(row: dict[str, str]) -> bool:
    confidence = text(row.get("fit_confidence")).upper()
    return confidence in {"HIGH", "MEDIUM"} and bool(text(row.get("fit_grade")))


def ui_recommendation(row: dict[str, str]) -> str:
    confidence = text(row.get("fit_confidence")).upper()
    score = text(row.get("race_shape_fit_score"))
    grade = text(row.get("fit_grade"))
    if confidence in {"HIGH", "MEDIUM"} and grade:
        return "SHOW_RACE_FIT"
    if confidence == "LOW":
        return "REVIEW_RACE_FIT"
    if confidence == "INSUFFICIENT" or not score:
        return "HIDE_RACE_FIT"
    return "HIDE_RACE_FIT"


def build_fit_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    lookup: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = runner_key(row)
        if key[-1]:
            lookup[key] = row
    return lookup


def build_top_opportunity_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    live_rows = read_csv(LIVE_FEED_PATH)
    fit_rows = read_csv(RACE_SHAPE_FIT_PATH)
    clean_overlay_rows = read_csv(CLEAN_OVERLAY_PATH)
    overlay_quality_rows = read_csv(OVERLAY_QUALITY_PATH)

    fit_lookup = build_fit_lookup(fit_rows)

    enriched_rows: list[dict[str, Any]] = []
    candidates_by_race: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for live_row in live_rows:
        key = runner_key(live_row)
        if not key[-1]:
            continue

        edgeiq = edgeiq_price(live_row)
        market = market_price(live_row)
        edge = edge_pct(live_row, edgeiq, market)
        active = is_active_runner(live_row)
        is_candidate = bool(active and market is not None and edgeiq is not None and edge is not None and edge > 0)

        fit = fit_lookup.get(key, {})
        usable_fit = has_usable_fit(fit)
        output_row = {
            "race_date": text(live_row.get("race_date")),
            "track": text(live_row.get("track")),
            "race_no": text(live_row.get("race_no")),
            "horse": text(live_row.get("horse")),
            "horse_key": key[-1],
            "edgeiq_price": format_price(edgeiq),
            "market_price": format_price(market),
            "edge_pct": format_pct(edge),
            "decision": decision(live_row, edge),
            "is_top_3_opportunity_in_race": "FALSE",
            "race_shape_fit_score": text(fit.get("race_shape_fit_score")),
            "fit_grade": text(fit.get("fit_grade")),
            "fit_confidence": text(fit.get("fit_confidence")) or "MISSING_FIT_ROW",
            "fit_reason": text(fit.get("fit_reason")),
            "risk_reason": text(fit.get("risk_reason")),
            "has_usable_fit": "TRUE" if usable_fit else "FALSE",
            "ui_recommendation": ui_recommendation(fit),
            "_race_key": race_key(live_row),
            "_edge": edge if edge is not None else -999999.0,
            "_is_candidate": is_candidate,
        }
        enriched_rows.append(output_row)
        if is_candidate:
            candidates_by_race[output_row["_race_key"]].append(output_row)

    for rows in candidates_by_race.values():
        rows.sort(key=lambda row: row["_edge"], reverse=True)
        for row in rows[:3]:
            row["is_top_3_opportunity_in_race"] = "TRUE"

    output_rows = [
        {column: row.get(column, "") for column in OUTPUT_COLUMNS}
        for row in enriched_rows
    ]

    positive_edge_count = sum(1 for row in enriched_rows if row["_is_candidate"])
    top_rows = [row for row in enriched_rows if row["is_top_3_opportunity_in_race"] == "TRUE"]
    top_usable_count = sum(1 for row in top_rows if row["has_usable_fit"] == "TRUE")
    all_usable_count = sum(1 for row in enriched_rows if row["has_usable_fit"] == "TRUE")
    top_coverage_pct = (top_usable_count / len(top_rows) * 100.0) if top_rows else 0.0
    all_coverage_pct = (all_usable_count / len(enriched_rows) * 100.0) if enriched_rows else 0.0
    top_grade_counts = Counter(row["fit_grade"] or "BLANK" for row in top_rows)
    top_confidence_counts = Counter(row["fit_confidence"] or "BLANK" for row in top_rows)

    summary = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "current_runners": len(enriched_rows),
        "live_feed_rows_loaded": len(live_rows),
        "race_shape_fit_v4_rows_loaded": len(fit_rows),
        "clean_overlay_review_rows_loaded_optional": len(clean_overlay_rows),
        "overlay_quality_rows_loaded_optional": len(overlay_quality_rows),
        "runners_with_positive_edge": positive_edge_count,
        "top_3_opportunity_rows_by_race": len(top_rows),
        "top_opportunity_rows_with_usable_Race_Shape_Fit": top_usable_count,
        "top_opportunity_usable_fit_coverage_pct": f"{top_coverage_pct:.2f}",
        "all_runner_usable_fit_coverage_pct": f"{all_coverage_pct:.2f}",
        "fit_grade_counts_among_top_opportunities": "; ".join(f"{name}:{count}" for name, count in sorted(top_grade_counts.items())),
        "fit_confidence_counts_among_top_opportunities": "; ".join(f"{name}:{count}" for name, count in sorted(top_confidence_counts.items())),
        "recommendation": "READY_FOR_SELECTIVE_UI" if top_coverage_pct >= 25.0 else "HOLD_UI_LOW_TOP_OPPORTUNITY_COVERAGE",
        "status": "TOP_OPPORTUNITY_RACE_SHAPE_FIT_V4_AUDITED",
    }

    return output_rows, summary


def main() -> None:
    output_rows, summary = build_top_opportunity_audit()
    write_csv(OUTPUT_PATH, output_rows, OUTPUT_COLUMNS)
    write_csv(SUMMARY_PATH, [summary], list(summary.keys()))

    print(f"Top opportunity race-shape fit rows written: {len(output_rows)}")
    print(f"Summary written: {SUMMARY_PATH}")
    print(f"Status: {summary['status']}")
    print(f"Top opportunity fit coverage: {summary['top_opportunity_usable_fit_coverage_pct']}%")
    print(f"Recommendation: {summary['recommendation']}")


if __name__ == "__main__":
    main()
