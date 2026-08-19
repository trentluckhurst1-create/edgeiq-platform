from __future__ import annotations

import csv
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "public" / "data"

PROJECTION_INPUT = DATA / "edgeiq_runner_projection_v3.csv"

PRICE_CANDIDATES = [
    DATA / "edgeiq_vic_live_terminal_feed_v1.csv",
    DATA / "edgeiq_execution_engine_v4.csv",
    DATA / "edgeiq_execution_board_v3.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_execution_board_terminal.csv",
    DATA / "edgeiq_vic_live_fields_synced.csv",
    DATA / "rated_market_v2.csv",
    DATA / "ratings_final_v2.csv",
    DATA / "model_odds_live.csv",
    DATA / "final_betting_board.csv",
]

AUDIT_OUT = DATA / "edgeiq_rated_price_rating_stack_audit_v3.csv"
RUNNER_REVIEW_OUT = DATA / "edgeiq_rated_price_rating_stack_runner_review_v3.csv"
SUMMARY_OUT = DATA / "edgeiq_rated_price_rating_stack_summary_v3.csv"

MARKET_FIELDS = [
    "sportsbet_price",
    "market_price",
    "live_price",
    "ui_price",
    "fixed_win",
    "fixed_win_price",
    "market_signal_price",
    "win_price",
    "price",
]

RATED_FIELDS = [
    "rated_price",
    "ui_fair_price",
    "fair_price",
    "elite_rated_price",
    "raw_model_rated_price",
    "model_price",
]

OVERLAY_FIELDS = [
    "edge_pct",
    "ui_edge_pct",
    "overlay_pct",
    "overlay",
    "compressed_edge",
    "edge",
]

RUNNER_REVIEW_FIELDS = [
    "horse",
    "track",
    "race_no",
    "race_time",
    "projected_rating_v3",
    "target_rating_v3",
    "rating_gap_v3",
    "gap_band",
    "projection_confidence",
    "target_confidence",
    "market_price",
    "market_price_source",
    "market_price_field",
    "current_rated_price",
    "current_rated_price_source",
    "current_rated_price_field",
    "current_overlay_pct",
    "current_overlay_source",
    "current_overlay_field",
    "implied_market_prob",
    "implied_rated_prob",
    "price_rating_alignment",
    "audit_flag",
    "audit_reason",
]

AUDIT_FIELDS = [
    "section",
    "file",
    "metric",
    "value",
    "count",
    "notes",
]

SUMMARY_FIELDS = [
    "section",
    "metric",
    "value",
    "count",
    "average",
    "notes",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def as_float(value: object) -> float | None:
    text = clean(value)
    if not text or text in {"-", "--"}:
        return None
    text = text.replace(",", "").replace("$", "").replace("%", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def as_price(value: object) -> float | None:
    number = as_float(value)
    if number is None or number <= 1.0:
        return None
    return number


def as_pct(value: object) -> float | None:
    number = as_float(value)
    if number is None:
        return None
    if abs(number) <= 1.0 and "%" not in clean(value):
        return number * 100.0
    return number


def fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def normalise_horse(value: object) -> str:
    text = clean(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def normalise_track(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", upper(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def projection_key(row: dict[str, str]) -> str:
    horse_key = normalise_horse(row.get("horse_key")) or normalise_horse(row.get("horse"))
    return "|".join(
        [
            clean(row.get("race_date")),
            normalise_track(row.get("track")),
            clean(row.get("race_no") or row.get("race_number")),
            horse_key,
        ]
    )


def row_key(row: dict[str, str]) -> str:
    horse_key = normalise_horse(row.get("horse_key")) or normalise_horse(row.get("horse"))
    race_date = clean(row.get("race_date") or row.get("date"))
    race_no = clean(row.get("race_no") or row.get("race_number"))
    return "|".join([race_date, normalise_track(row.get("track")), race_no, horse_key])


def row_columns(row: dict[str, str]) -> set[str]:
    return {str(column) for column in row.keys()}


def available_columns(columns: set[str], candidates: list[str]) -> list[str]:
    return [column for column in candidates if column in columns]


def first_value(row: dict[str, str], fields: list[str], value_kind: str) -> tuple[float | None, str]:
    for field in fields:
        if field not in row:
            continue
        value = as_price(row.get(field)) if value_kind == "price" else as_pct(row.get(field))
        if value is not None:
            return value, field
    return None, ""


def implied_prob(price: float | None) -> float | None:
    if price is None or price <= 1:
        return None
    return 100.0 / price


def computed_overlay_pct(market_price: float | None, rated_price: float | None) -> float | None:
    if market_price is None or rated_price is None or rated_price <= 0:
        return None
    return ((market_price / rated_price) - 1.0) * 100.0


def price_alignment(gap_band: str, overlay_pct: float | None, market_price: float | None, rated_price: float | None, projection_confidence: str) -> str:
    if projection_confidence == "NO_HISTORY" or gap_band == "NO_HISTORY":
        return "NO_HISTORY"
    if market_price is None or rated_price is None:
        return "NO_PRICE_CONTEXT"
    if overlay_pct is None:
        overlay_pct = computed_overlay_pct(market_price, rated_price)
    if overlay_pct is None:
        return "NO_OVERLAY_CONTEXT"
    if gap_band in {"STRONG_ABOVE_TARGET", "ABOVE_TARGET"}:
        return "RATING_POSITIVE_PRICE_POSITIVE" if overlay_pct > 0 else "RATING_POSITIVE_NO_OVERLAY"
    if gap_band in {"BELOW_TARGET", "WELL_BELOW_TARGET"}:
        return "RATING_NEGATIVE_PRICE_NEGATIVE" if overlay_pct <= 0 else "RATING_NEGATIVE_OVERLAY"
    if gap_band == "NEAR_TARGET":
        return "NEAR_TARGET_PRICE_NEUTRAL" if abs(overlay_pct) < 10 else "NEAR_TARGET_PRICE_AGGRESSIVE"
    if gap_band == "NO_TARGET":
        return "NO_TARGET"
    return "UNKNOWN"


def audit_flag_and_reason(
    gap_band: str,
    projection_confidence: str,
    target_confidence: str,
    market_price: float | None,
    rated_price: float | None,
    overlay_pct: float | None,
    alignment: str,
) -> tuple[str, str]:
    reasons: list[str] = []
    if target_confidence == "LOW":
        reasons.append("TARGET_UNCERTAIN")
    if projection_confidence == "LOW":
        reasons.append("LOW_PROJECTION_CONFIDENCE")
    if market_price is None:
        reasons.append("MISSING_MARKET_PRICE")
    if rated_price is None:
        reasons.append("MISSING_RATED_PRICE")

    effective_overlay = overlay_pct
    if effective_overlay is None:
        effective_overlay = computed_overlay_pct(market_price, rated_price)

    aggressive_overlay = effective_overlay is not None and effective_overlay >= 10.0

    if projection_confidence == "NO_HISTORY":
        if rated_price is not None:
            reasons.append("NO_HISTORY_HAS_RATED_PRICE")
            return "NO_HISTORY_PRICED", " | ".join(reasons)
        return "NO_HISTORY", " | ".join(reasons)

    if gap_band in {"BELOW_TARGET", "WELL_BELOW_TARGET"} and aggressive_overlay:
        reasons.append("NEGATIVE_RATING_GAP_WITH_AGGRESSIVE_OVERLAY")
        return "FAKE_OVERLAY_RISK", " | ".join(reasons)

    if projection_confidence == "LOW" and aggressive_overlay:
        reasons.append("LOW_CONFIDENCE_WITH_AGGRESSIVE_OVERLAY")
        return "LOW_CONFIDENCE_OVERLAY", " | ".join(reasons)

    if gap_band == "STRONG_ABOVE_TARGET" and rated_price is not None and rated_price >= 10.0:
        if market_price is None or market_price >= 4.0:
            reasons.append("STRONG_ABOVE_TARGET_BUT_LONG_RATED_PRICE")
            return "RATING_PRICE_MISMATCH", " | ".join(reasons)

    if gap_band in {"STRONG_ABOVE_TARGET", "ABOVE_TARGET"} and effective_overlay is not None and effective_overlay <= 0:
        if market_price is not None and rated_price is not None and market_price < rated_price:
            reasons.append("MARKET_PRICE_SHORTER_THAN_RATED_PRICE")
            return "PRICE_TOO_SHORT", " | ".join(reasons)
        reasons.append("STRONG_RATING_GAP_WITH_NO_OVERLAY")
        return "MARKET_ALREADY_PRICED", " | ".join(reasons)

    if market_price is None:
        return "MISSING_MARKET_PRICE", " | ".join(reasons)
    if rated_price is None:
        return "MISSING_RATED_PRICE", " | ".join(reasons)
    if target_confidence == "LOW":
        return "TARGET_UNCERTAIN", " | ".join(reasons)
    if alignment in {"RATING_POSITIVE_PRICE_POSITIVE", "RATING_NEGATIVE_PRICE_NEGATIVE", "NEAR_TARGET_PRICE_NEUTRAL"}:
        return "ALIGNED", "Rating direction and current price/overlay direction are coherent."

    reasons.append(alignment)
    return "NEEDS_REVIEW", " | ".join(reasons)


def audit_row(section: str, file: str, metric: str, value: object = "", count: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "file": file,
        "metric": metric,
        "value": value,
        "count": count,
        "notes": notes,
    }


def summary_row(section: str, metric: str, value: object = "", count: object = "", average: object = "", notes: object = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "average": average,
        "notes": notes,
    }


def main() -> None:
    projection_rows = read_csv(PROJECTION_INPUT)
    projection_keys = {projection_key(row) for row in projection_rows}

    candidate_indexes: list[tuple[Path, dict[str, list[dict[str, str]]]]] = []
    candidate_audit_rows: list[dict[str, object]] = []

    for path in PRICE_CANDIDATES:
        if not path.exists():
            candidate_audit_rows.append(audit_row("price_source_candidate", path.name, "missing_file", "", 0, "Candidate file not found."))
            continue

        rows = read_csv(path)
        columns = row_columns(rows[0]) if rows else set()
        market_columns = available_columns(columns, MARKET_FIELDS)
        rated_columns = available_columns(columns, RATED_FIELDS)
        overlay_columns = available_columns(columns, OVERLAY_FIELDS)
        index: dict[str, list[dict[str, str]]] = defaultdict(list)
        matched_rows = 0
        market_value_rows = 0
        rated_value_rows = 0
        overlay_value_rows = 0

        for row in rows:
            key = row_key(row)
            if key not in projection_keys:
                continue
            matched_rows += 1
            index[key].append(row)
            market_value, _ = first_value(row, MARKET_FIELDS, "price")
            rated_value, _ = first_value(row, RATED_FIELDS, "price")
            overlay_value, _ = first_value(row, OVERLAY_FIELDS, "pct")
            if market_value is not None:
                market_value_rows += 1
            if rated_value is not None:
                rated_value_rows += 1
            if overlay_value is not None:
                overlay_value_rows += 1

        candidate_indexes.append((path, index))
        candidate_audit_rows.extend(
            [
                audit_row("price_source_candidate", path.name, "rows", len(rows), len(rows), "Candidate scanned."),
                audit_row("price_source_candidate", path.name, "matched_projection_rows", matched_rows, matched_rows, "Matched by race_date, track, race_no, horse_key/horse."),
                audit_row("price_source_candidate", path.name, "market_value_rows", market_value_rows, market_value_rows, "Detected columns: " + ", ".join(market_columns)),
                audit_row("price_source_candidate", path.name, "rated_value_rows", rated_value_rows, rated_value_rows, "Detected columns: " + ", ".join(rated_columns)),
                audit_row("price_source_candidate", path.name, "overlay_value_rows", overlay_value_rows, overlay_value_rows, "Detected columns: " + ", ".join(overlay_columns)),
            ]
        )

    def selected_value(key: str, fields: list[str], value_kind: str) -> tuple[float | None, str, str]:
        for path, index in candidate_indexes:
            for row in index.get(key, []):
                value, field = first_value(row, fields, value_kind)
                if value is not None:
                    return value, path.name, field
        return None, "", ""

    review_rows: list[dict[str, object]] = []

    for projection in projection_rows:
        key = projection_key(projection)
        market_price, market_source, market_field = selected_value(key, MARKET_FIELDS, "price")
        rated_price, rated_source, rated_field = selected_value(key, RATED_FIELDS, "price")
        overlay_pct, overlay_source, overlay_field = selected_value(key, OVERLAY_FIELDS, "pct")
        overlay_method = overlay_field

        if overlay_pct is None:
            overlay_pct = computed_overlay_pct(market_price, rated_price)
            if overlay_pct is not None:
                overlay_source = "computed_from_market_and_rated_price"
                overlay_method = "market_price_vs_rated_price"

        market_prob = implied_prob(market_price)
        rated_prob = implied_prob(rated_price)
        gap_band = clean(projection.get("gap_band"))
        projection_confidence = upper(projection.get("projection_confidence"))
        target_confidence = upper(projection.get("target_confidence"))
        alignment = price_alignment(gap_band, overlay_pct, market_price, rated_price, projection_confidence)
        flag, reason = audit_flag_and_reason(
            gap_band,
            projection_confidence,
            target_confidence,
            market_price,
            rated_price,
            overlay_pct,
            alignment,
        )

        review_rows.append(
            {
                "horse": clean(projection.get("horse")),
                "track": clean(projection.get("track")),
                "race_no": clean(projection.get("race_no")),
                "race_time": clean(projection.get("race_time")),
                "projected_rating_v3": clean(projection.get("projected_rating_v3")),
                "target_rating_v3": clean(projection.get("target_rating_v3")),
                "rating_gap_v3": clean(projection.get("rating_gap_v3")),
                "gap_band": gap_band,
                "projection_confidence": projection_confidence,
                "target_confidence": target_confidence,
                "market_price": fmt(market_price),
                "market_price_source": market_source,
                "market_price_field": market_field,
                "current_rated_price": fmt(rated_price),
                "current_rated_price_source": rated_source,
                "current_rated_price_field": rated_field,
                "current_overlay_pct": fmt(overlay_pct),
                "current_overlay_source": overlay_source,
                "current_overlay_field": overlay_method,
                "implied_market_prob": fmt(market_prob),
                "implied_rated_prob": fmt(rated_prob),
                "price_rating_alignment": alignment,
                "audit_flag": flag,
                "audit_reason": reason,
            }
        )

    total_runners = len(review_rows)
    matched_rated = sum(1 for row in review_rows if clean(row["current_rated_price"]))
    missing_rated = total_runners - matched_rated
    missing_market = sum(1 for row in review_rows if not clean(row["market_price"]))
    fake_overlay_risk = sum(1 for row in review_rows if row["audit_flag"] == "FAKE_OVERLAY_RISK")
    aligned = sum(1 for row in review_rows if row["audit_flag"] == "ALIGNED")
    no_history_priced = sum(1 for row in review_rows if row["audit_flag"] == "NO_HISTORY_PRICED")
    low_confidence_overlay = sum(1 for row in review_rows if row["audit_flag"] == "LOW_CONFIDENCE_OVERLAY")

    summary_rows: list[dict[str, object]] = [
        summary_row("summary", "total_runners", total_runners, total_runners),
        summary_row("summary", "matched_rated_price_rows", matched_rated, matched_rated),
        summary_row("summary", "missing_rated_price_rows", missing_rated, missing_rated),
        summary_row("summary", "missing_market_price_rows", missing_market, missing_market),
        summary_row("summary", "fake_overlay_risk_count", fake_overlay_risk, fake_overlay_risk),
        summary_row("summary", "aligned_count", aligned, aligned),
        summary_row("summary", "no_history_but_priced_count", no_history_priced, no_history_priced),
        summary_row("summary", "low_confidence_overlay_count", low_confidence_overlay, low_confidence_overlay),
    ]

    def group_average(field: str, value_field: str) -> None:
        grouped: dict[str, list[float]] = defaultdict(list)
        counts: Counter[str] = Counter()
        for row in review_rows:
            group = clean(row.get(field)) or "UNKNOWN"
            counts[group] += 1
            value = as_float(row.get(value_field))
            if value is not None:
                grouped[group].append(value)
        for group in sorted(counts):
            values = grouped.get(group, [])
            summary_rows.append(
                summary_row(
                    f"{field}_average_{value_field}",
                    field,
                    group,
                    counts[group],
                    fmt(sum(values) / len(values) if values else None),
                    f"value_count={len(values)}",
                )
            )

    group_average("gap_band", "current_rated_price")
    group_average("gap_band", "market_price")
    group_average("gap_band", "current_overlay_pct")

    audit_rows: list[dict[str, object]] = []
    audit_rows.extend(candidate_audit_rows)
    for flag, count in sorted(Counter(row["audit_flag"] for row in review_rows).items()):
        audit_rows.append(audit_row("runner_audit_flag_counts", "", str(flag), count, count))
    for alignment, count in sorted(Counter(row["price_rating_alignment"] for row in review_rows).items()):
        audit_rows.append(audit_row("price_rating_alignment_counts", "", str(alignment), count, count))

    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)
    write_csv(RUNNER_REVIEW_OUT, review_rows, RUNNER_REVIEW_FIELDS)
    write_csv(SUMMARY_OUT, summary_rows, SUMMARY_FIELDS)

    print("=" * 100)
    print("EDGEIQ RATED PRICE VS RATING STACK V3 AUDIT")
    print("=" * 100)
    print(f"total_runners={total_runners}")
    print(f"matched_rated_price_rows={matched_rated}")
    print(f"missing_rated_price_rows={missing_rated}")
    print(f"missing_market_price_rows={missing_market}")
    print(f"fake_overlay_risk_count={fake_overlay_risk}")
    print(f"aligned_count={aligned}")
    print(f"no_history_but_priced_count={no_history_priced}")
    print(f"low_confidence_overlay_count={low_confidence_overlay}")
    print()
    print("SAVED:")
    print(AUDIT_OUT)
    print(RUNNER_REVIEW_OUT)
    print(SUMMARY_OUT)


if __name__ == "__main__":
    main()
