from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_EPF = DATA / "edgeiq_epf_v1_1_guardrailed.csv"

OUTPUT_MAIN = DATA / "edgeiq_current_epf_feed_v1_1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_current_epf_feed_v1_1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_current_epf_feed_v1_1_audit.csv"

HALF_LIFE_DAYS = 730.5
DECAY_COEFFICIENT = 0.69315


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def clean_horse(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return None


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def is_scratched(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def weighted_average(values: List[Tuple[float, float]]) -> Optional[float]:
    usable = [(value, weight) for value, weight in values if value is not None and weight > 0]
    if not usable:
        return None
    total_weight = sum(weight for _, weight in usable)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in usable) / total_weight


def recency_weight(run_date: Optional[datetime], current_date: Optional[datetime]) -> Optional[float]:
    if run_date is None or current_date is None:
        return None
    days_diff = max((current_date - run_date).days, 0)
    return math.exp((-days_diff / HALF_LIFE_DAYS) * DECAY_COEFFICIENT)


def band_from_display(value: Optional[float], confidence: str) -> str:
    if value is None:
        return "UNKNOWN"
    if confidence == "LOW":
        return "LOW_CONFIDENCE"
    if value >= 10.0:
        return "EXCEPTIONAL"
    if value >= 7.0:
        return "ELITE"
    if value >= 4.0:
        return "STRONG"
    if value >= 2.0:
        return "ABOVE_AVG"
    if value > -2.0:
        return "STANDARD"
    if value > -5.0:
        return "BELOW_AVG"
    return "POOR"


def trend_label(last_values: List[float]) -> str:
    if len(last_values) < 2:
        return "LIMITED"
    if len(last_values) >= 5:
        recent = sum(last_values[:3]) / min(3, len(last_values[:3]))
        prior = sum(last_values[3:6]) / len(last_values[3:6]) if len(last_values[3:6]) > 0 else last_values[-1]
    else:
        recent = last_values[0]
        prior = sum(last_values[1:]) / len(last_values[1:])
    delta = recent - prior
    if delta >= 2.0:
        return "IMPROVING"
    if delta <= -2.0:
        return "REGRESSING"
    return "STABLE"


def aggregate_confidence(total_runs: int, safe_runs: int, confidence_rows: List[str]) -> str:
    if total_runs == 0:
        return "LOW"
    if safe_runs >= 3 and total_runs >= 5 and confidence_rows.count("HIGH") + confidence_rows.count("MEDIUM") >= 3:
        return "HIGH"
    if safe_runs >= 1 and total_runs >= 3:
        return "MEDIUM"
    return "LOW"


def evidence_status(total_runs: int) -> str:
    if total_runs >= 5:
        return "STRONG_PROFILE"
    if total_runs >= 3:
        return "USABLE_PROFILE"
    if total_runs >= 1:
        return "LIMITED_HISTORY"
    return "NO_HISTORY"


def narrative(
    total_runs: int,
    safe_runs: int,
    last_raw: Optional[float],
    last_display: Optional[float],
    weighted_display: Optional[float],
    confidence: str,
) -> str:
    if total_runs == 0:
        return "No guardrailed EPF evidence matched for this runner."
    last_raw_txt = f"{last_raw:.1f}L" if last_raw is not None else "N/A"
    last_display_txt = f"{last_display:.1f}L" if last_display is not None else "N/A"
    weighted_txt = f"{weighted_display:.1f}L" if weighted_display is not None else "N/A"
    return (
        f"Guardrailed EPF uses {total_runs} rated runs ({safe_runs} customer-safe). Last start raw {last_raw_txt}, "
        f"display {last_display_txt}, recency-weighted display {weighted_txt}, confidence {confidence}."
    )


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not INPUT_BOARD.exists():
        raise FileNotFoundError(INPUT_BOARD)
    if not INPUT_EPF.exists():
        raise FileNotFoundError(INPUT_EPF)

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    board_rows = []
    with INPUT_BOARD.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not is_scratched(row):
                board_rows.append(row)

    epf_by_key: DefaultDict[str, List[Dict[str, str]]] = defaultdict(list)
    epf_by_name: DefaultDict[str, List[Dict[str, str]]] = defaultdict(list)
    with INPUT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if clean(row.get("evidence_status")) != "READY":
                continue
            key = clean_horse(row.get("horse_key"))
            name_key = clean_horse(row.get("horse"))
            slim = {
                "race_date": clean(row.get("race_date")),
                "horse": clean(row.get("horse")),
                "horse_key": key,
                "raw_epf_lengths": clean(row.get("raw_epf_lengths")),
                "display_epf_lengths": clean(row.get("display_epf_lengths")),
                "epf_confidence_band": clean(row.get("epf_confidence_band")),
                "epf_customer_safe_flag": clean(row.get("epf_customer_safe_flag")),
            }
            if key:
                epf_by_key[key].append(slim)
            if name_key:
                epf_by_name[name_key].append(slim)

    for bucket in list(epf_by_key.values()) + list(epf_by_name.values()):
        bucket.sort(key=lambda item: parse_date(item.get("race_date")) or datetime.min, reverse=True)

    output_rows: List[Dict[str, object]] = []
    band_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    safe_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    matched = 0

    for row in board_rows:
        horse = clean(row.get("horse"))
        horse_key = clean_horse(row.get("horse_key")) or clean_horse(horse)
        current_date = parse_date(row.get("race_date"))
        history = epf_by_key.get(horse_key, [])
        match_method = "HORSE_KEY"
        if not history:
            history = epf_by_name.get(clean_horse(horse), [])
            match_method = "HORSE_NAME"

        total_runs = len(history)
        safe_runs = sum(1 for item in history if upper(item.get("epf_customer_safe_flag")) == "YES")
        if total_runs > 0:
            matched += 1

        raw_values = [parse_float(item.get("raw_epf_lengths")) for item in history if parse_float(item.get("raw_epf_lengths")) is not None]
        raw_values = [value for value in raw_values if value is not None]
        display_values = [parse_float(item.get("display_epf_lengths")) for item in history if parse_float(item.get("display_epf_lengths")) is not None]
        display_values = [value for value in display_values if value is not None]

        last_raw = raw_values[0] if raw_values else None
        last_display = display_values[0] if display_values else None
        avg_last3_display = round(sum(display_values[:3]) / len(display_values[:3]), 3) if display_values[:3] else None
        avg_last5_display = round(sum(display_values[:5]) / len(display_values[:5]), 3) if display_values[:5] else None
        peak_display = max(display_values) if display_values else None

        weighted_inputs: List[Tuple[float, float]] = []
        for item in history:
            display_value = parse_float(item.get("display_epf_lengths"))
            if display_value is None:
                continue
            weight = recency_weight(parse_date(item.get("race_date")), current_date)
            if weight is not None:
                weighted_inputs.append((display_value, weight))
        recency_weighted_display = weighted_average(weighted_inputs)
        if recency_weighted_display is not None:
            recency_weighted_display = round(recency_weighted_display, 3)

        agg_confidence = aggregate_confidence(
            total_runs=total_runs,
            safe_runs=safe_runs,
            confidence_rows=[clean(item.get("epf_confidence_band")) for item in history],
        )
        current_band = band_from_display(recency_weighted_display if recency_weighted_display is not None else avg_last3_display if avg_last3_display is not None else last_display, agg_confidence)
        current_safe = "YES" if safe_runs >= 1 and agg_confidence in {"HIGH", "MEDIUM"} else "NO"
        trend = trend_label(display_values)
        status = evidence_status(total_runs)

        band_counts[current_band] += 1
        confidence_counts[agg_confidence] += 1
        safe_counts[current_safe] += 1
        status_counts[status] += 1

        output_rows.append(
            {
                "current_race_date": clean(row.get("race_date")),
                "track": upper(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse": horse,
                "horse_key": horse_key,
                "last_start_epf_raw": f"{last_raw:.3f}" if last_raw is not None else "",
                "last_start_epf_display": f"{last_display:.3f}" if last_display is not None else "",
                "avg_last3_epf_display": f"{avg_last3_display:.3f}" if avg_last3_display is not None else "",
                "avg_last5_epf_display": f"{avg_last5_display:.3f}" if avg_last5_display is not None else "",
                "peak_epf_display": f"{peak_display:.3f}" if peak_display is not None else "",
                "recency_weighted_epf_display": f"{recency_weighted_display:.3f}" if recency_weighted_display is not None else "",
                "epf_trend": trend,
                "epf_band_current": current_band,
                "epf_confidence_band": agg_confidence,
                "epf_customer_safe_flag": current_safe,
                "epf_profile_narrative": narrative(total_runs, safe_runs, last_raw, last_display, recency_weighted_display, agg_confidence),
                "history_runs_used": total_runs,
                "customer_safe_history_runs": safe_runs,
                "evidence_status": status,
                "match_method": match_method if total_runs > 0 else "NO_MATCH",
                "built_at": built_at,
            }
        )

    bendigo_rows = [row for row in output_rows if row["track"] == "BENDIGO"]
    bendigo_total = len(bendigo_rows)
    bendigo_safe = sum(1 for row in bendigo_rows if row["epf_customer_safe_flag"] == "YES")

    safe_yes = safe_counts.get("YES", 0)
    if matched >= int(len(board_rows) * 0.85) and safe_yes >= 200:
        readiness = "READY_WITH_GUARDRAILS"
    elif matched >= int(len(board_rows) * 0.70):
        readiness = "READY_WITH_GUARDRAILS"
    else:
        readiness = "NOT_READY"

    summary_row = {
        "status": "EDGEIQ_CURRENT_EPF_FEED_V1_1_BUILT",
        "active_runner_rows": len(board_rows),
        "matched_runners": matched,
        "coverage_pct": f"{(matched / len(board_rows) * 100.0):.3f}" if board_rows else "",
        "customer_safe_runners": safe_yes,
        "customer_safe_pct": f"{(safe_yes / len(board_rows) * 100.0):.3f}" if board_rows else "",
        "strong_profile_count": status_counts.get("STRONG_PROFILE", 0),
        "usable_profile_count": status_counts.get("USABLE_PROFILE", 0),
        "limited_history_count": status_counts.get("LIMITED_HISTORY", 0),
        "no_history_count": status_counts.get("NO_HISTORY", 0),
        "high_confidence_count": confidence_counts.get("HIGH", 0),
        "medium_confidence_count": confidence_counts.get("MEDIUM", 0),
        "low_confidence_count": confidence_counts.get("LOW", 0),
        "bendigo_rows": bendigo_total,
        "bendigo_customer_safe_rows": bendigo_safe,
        "readiness_verdict": readiness,
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(status_counts.items()):
        audit_rows.append({"audit_type": "EVIDENCE_STATUS", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(confidence_counts.items()):
        audit_rows.append({"audit_type": "CONFIDENCE_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "EPF_BAND_CURRENT", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(safe_counts.items()):
        audit_rows.append({"audit_type": "CUSTOMER_SAFE", "audit_value": name, "count": count, "built_at": built_at})
    audit_rows.append({"audit_type": "BENDIGO", "audit_value": "TOTAL_ROWS", "count": bendigo_total, "built_at": built_at})
    audit_rows.append({"audit_type": "BENDIGO", "audit_value": "CUSTOMER_SAFE_ROWS", "count": bendigo_safe, "built_at": built_at})

    fieldnames = list(output_rows[0].keys()) if output_rows else [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "last_start_epf_raw",
        "last_start_epf_display",
        "epf_band_current",
        "epf_confidence_band",
        "epf_customer_safe_flag",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ current EPF feed V1.1 built")
    print(f"Active runners: {len(board_rows)}")
    print(f"Matched runners: {matched}")
    print(f"Customer-safe runners: {safe_yes}")
    print(f"Readiness: {readiness}")


if __name__ == "__main__":
    main()
