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
INPUT_EPF = DATA / "edgeiq_epf_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_current_epf_feed_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_current_epf_feed_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_current_epf_feed_v1_audit.csv"

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


def epf_band(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
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


def evidence_status(run_count: int) -> str:
    if run_count >= 5:
        return "STRONG_PROFILE"
    if run_count >= 3:
        return "USABLE_PROFILE"
    if run_count >= 1:
        return "LIMITED_HISTORY"
    return "NO_HISTORY"


def narrative(
    run_count: int,
    last_start_epf: Optional[float],
    avg_last3_epf: Optional[float],
    peak_epf: Optional[float],
    trend: str,
) -> str:
    if run_count == 0:
        return "No historical EPF evidence matched for this runner."
    last_txt = f"{last_start_epf:.1f}L" if last_start_epf is not None else "N/A"
    avg3_txt = f"{avg_last3_epf:.1f}L" if avg_last3_epf is not None else "N/A"
    peak_txt = f"{peak_epf:.1f}L" if peak_epf is not None else "N/A"
    return (
        f"EPF profile uses {run_count} rated runs. Last start {last_txt}, last-three average {avg3_txt}, "
        f"peak {peak_txt}, trend {trend}."
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
            if key:
                epf_by_key[key].append(row)
            if name_key:
                epf_by_name[name_key].append(row)

    for bucket in list(epf_by_key.values()) + list(epf_by_name.values()):
        bucket.sort(key=lambda item: parse_date(item.get("race_date")) or datetime.min, reverse=True)

    output_rows: List[Dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    band_counts: Counter[str] = Counter()
    matched_runners = 0

    for row in board_rows:
        horse = clean(row.get("horse"))
        horse_key = clean_horse(row.get("horse_key")) or clean_horse(horse)
        current_date = parse_date(row.get("race_date"))
        history = epf_by_key.get(horse_key, [])
        match_method = "HORSE_KEY"
        if not history:
            history = epf_by_name.get(clean_horse(horse), [])
            match_method = "HORSE_NAME"

        usable_history = [item for item in history if parse_date(item.get("race_date")) is not None]
        run_count = len(usable_history)
        status = evidence_status(run_count)
        status_counts[status] += 1
        if run_count > 0:
            matched_runners += 1

        epf_values = [parse_float(item.get("epf_lengths")) for item in usable_history if parse_float(item.get("epf_lengths")) is not None]
        epf_values = [value for value in epf_values if value is not None]

        last_start = epf_values[0] if len(epf_values) >= 1 else None
        avg_last3 = round(sum(epf_values[:3]) / len(epf_values[:3]), 3) if epf_values[:3] else None
        avg_last5 = round(sum(epf_values[:5]) / len(epf_values[:5]), 3) if epf_values[:5] else None
        peak = max(epf_values) if epf_values else None

        weighted_inputs: List[Tuple[float, float]] = []
        for item in usable_history:
            epf_value = parse_float(item.get("epf_lengths"))
            if epf_value is None:
                continue
            weight = recency_weight(parse_date(item.get("race_date")), current_date)
            if weight is not None:
                weighted_inputs.append((epf_value, weight))
        recency_weighted = weighted_average(weighted_inputs)
        if recency_weighted is not None:
            recency_weighted = round(recency_weighted, 3)

        trend = trend_label(epf_values)
        current_band = epf_band(recency_weighted if recency_weighted is not None else avg_last3 if avg_last3 is not None else last_start)
        band_counts[current_band] += 1

        out_row = {
            "current_race_date": clean(row.get("race_date")),
            "track": upper(row.get("track")),
            "race_no": clean(row.get("race_no")),
            "horse": horse,
            "horse_key": horse_key,
            "last_start_epf": f"{last_start:.3f}" if last_start is not None else "",
            "avg_last3_epf": f"{avg_last3:.3f}" if avg_last3 is not None else "",
            "avg_last5_epf": f"{avg_last5:.3f}" if avg_last5 is not None else "",
            "peak_epf": f"{peak:.3f}" if peak is not None else "",
            "recency_weighted_epf": f"{recency_weighted:.3f}" if recency_weighted is not None else "",
            "epf_trend": trend,
            "epf_band_current": current_band,
            "epf_profile_narrative": narrative(run_count, last_start, avg_last3, peak, trend),
            "history_runs_used": run_count,
            "evidence_status": status,
            "match_method": match_method if run_count > 0 else "NO_MATCH",
            "built_at": built_at,
        }
        output_rows.append(out_row)

    summary_row = {
        "status": "EDGEIQ_CURRENT_EPF_FEED_V1_BUILT",
        "active_runner_rows": len(board_rows),
        "matched_runners": matched_runners,
        "coverage_pct": f"{(matched_runners / len(board_rows) * 100.0):.3f}" if board_rows else "",
        "strong_profile_count": status_counts.get("STRONG_PROFILE", 0),
        "usable_profile_count": status_counts.get("USABLE_PROFILE", 0),
        "limited_history_count": status_counts.get("LIMITED_HISTORY", 0),
        "no_history_count": status_counts.get("NO_HISTORY", 0),
        "exceptional_band_count": band_counts.get("EXCEPTIONAL", 0),
        "elite_band_count": band_counts.get("ELITE", 0),
        "strong_band_count": band_counts.get("STRONG", 0),
        "above_avg_band_count": band_counts.get("ABOVE_AVG", 0),
        "standard_band_count": band_counts.get("STANDARD", 0),
        "below_avg_band_count": band_counts.get("BELOW_AVG", 0),
        "poor_band_count": band_counts.get("POOR", 0),
        "unknown_band_count": band_counts.get("UNKNOWN", 0),
        "readiness_verdict": "READY_FOR_HIDDEN_GEM" if matched_runners >= 250 else "LIMITED",
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(status_counts.items()):
        audit_rows.append({"audit_type": "EVIDENCE_STATUS", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "EPF_BAND_CURRENT", "audit_value": name, "count": count, "built_at": built_at})

    fields = [
        "current_race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "last_start_epf",
        "avg_last3_epf",
        "avg_last5_epf",
        "peak_epf",
        "recency_weighted_epf",
        "epf_trend",
        "epf_band_current",
        "epf_profile_narrative",
        "history_runs_used",
        "evidence_status",
        "match_method",
        "built_at",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fields)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ current EPF feed V1 built")
    print(f"Active runners: {len(board_rows)}")
    print(f"Matched runners: {matched_runners}")
    print(f"Readiness: {summary_row['readiness_verdict']}")


if __name__ == "__main__":
    main()
