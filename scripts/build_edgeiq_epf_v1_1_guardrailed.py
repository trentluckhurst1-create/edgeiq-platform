from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_EPF = DATA / "edgeiq_epf_v1.csv"
INPUT_STANDARDS = DATA / "edgeiq_historical_standard_times_v1.csv"
INPUT_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"

OUTPUT_MAIN = DATA / "edgeiq_epf_v1_1_guardrailed.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_epf_v1_1_guardrailed_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_epf_v1_1_guardrailed_audit.csv"

DISPLAY_CAP = 20.0
MIN_STANDARD_SAMPLE = 10
MIN_STANDARD_SAMPLE_RARE_DISTANCE = 12


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "").replace("L", "").replace("l", "")
    try:
        return float(txt)
    except Exception:
        return None


def parse_int(value: object) -> Optional[int]:
    num = parse_float(value)
    if num is None:
        return None
    return int(round(num))


def normalize_condition(value: object) -> str:
    txt = upper(value)
    if txt == "":
        return "UNKNOWN"
    if "HEAVY" in txt:
        return "HEAVY"
    if "SOFT" in txt:
        return "SOFT"
    if "GOOD" in txt:
        return "GOOD"
    if "FIRM" in txt:
        return "FIRM"
    if "SYNTH" in txt or "POLY" in txt or "TAPETA" in txt or "ALL WEATHER" in txt:
        return "SYNTH"
    if txt in {"3", "4"}:
        return "GOOD"
    if txt in {"5", "6", "7"}:
        return "SOFT"
    if txt in {"8", "9", "10"}:
        return "HEAVY"
    return "UNKNOWN"


def race_type_from_meta(race_class: str, race_name: str) -> str:
    raw = " ".join([upper(race_class), upper(race_name)]).strip()
    if raw == "":
        return "UNKNOWN"
    blocked = ["TRIAL", "HURDLE", "STEEPLE", "JUMP", "CHASE"]
    if any(token in raw for token in blocked):
        return "NON_FLAT_OR_TRIAL"
    return "FLAT"


def source_time_quality(winner_time_sec: Optional[float], distance_m: Optional[int]) -> str:
    if winner_time_sec is None or distance_m is None or distance_m <= 0:
        return "MISSING_TIME"
    sec_per_100m = (winner_time_sec / distance_m) * 100.0
    if sec_per_100m < 5.0:
        return "SUSPICIOUS_FAST"
    if sec_per_100m > 9.5:
        return "SUSPICIOUS_SLOW"
    return "PLAUSIBLE"


def recommended_min_sample(distance_m: Optional[int]) -> int:
    if distance_m is not None and distance_m >= 3200:
        return MIN_STANDARD_SAMPLE_RARE_DISTANCE
    return MIN_STANDARD_SAMPLE


def standard_lookup() -> Tuple[Dict[Tuple[str, int, str], Dict[str, str]], Dict[Tuple[str, int], Dict[str, str]]]:
    exact: Dict[Tuple[str, int, str], Dict[str, str]] = {}
    fallback: Dict[Tuple[str, int], Dict[str, str]] = {}
    with INPUT_STANDARDS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            track = upper(row.get("track"))
            distance_m = parse_int(row.get("distance_m"))
            if not track or distance_m is None:
                continue
            scope = clean(row.get("profile_scope"))
            if scope == "TRACK_DISTANCE_CONDITION":
                exact[(track, distance_m, upper(row.get("condition_group")))] = row
            elif scope == "TRACK_DISTANCE_ALL":
                fallback[(track, distance_m)] = row
    return exact, fallback


def load_race_meta() -> Dict[Tuple[str, str, str], Dict[str, str]]:
    meta: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    with INPUT_RESULTS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            race_key = (clean(row.get("race_date")), upper(row.get("track")), clean(str(parse_int(row.get("race_no")) or clean(row.get("race_no")))))
            if race_key in meta:
                continue
            meta[race_key] = {
                "race_class": clean(row.get("race_class")),
                "race_name": clean(row.get("race_name")),
                "track_condition": clean(row.get("track_condition")),
                "track_rating": clean(row.get("track_rating")),
                "source_file": clean(row.get("source_file")),
            }
    return meta


def raw_band(value: Optional[float]) -> str:
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


def display_band(value: Optional[float], confidence: str) -> str:
    if value is None:
        return "UNKNOWN"
    if confidence == "LOW":
        return "LOW_CONFIDENCE"
    return raw_band(value)


def confidence_band(
    sample_size: int,
    time_quality: str,
    race_type: str,
    distance_m: Optional[int],
    abnormal_finish_flag: bool,
) -> str:
    if race_type != "FLAT" or time_quality != "PLAUSIBLE" or abnormal_finish_flag:
        return "LOW"
    min_needed = recommended_min_sample(distance_m)
    if sample_size >= max(20, min_needed):
        return "HIGH"
    if sample_size >= min_needed:
        return "MEDIUM"
    return "LOW"


def build_guardrail_flags(
    raw_epf: Optional[float],
    sample_size: int,
    distance_m: Optional[int],
    race_type: str,
    time_quality: str,
    missing_margin_flag: bool,
    abnormal_finish_flag: bool,
    standard_evidence_status: str,
) -> List[str]:
    flags: List[str] = []
    if raw_epf is not None and abs(raw_epf) > DISPLAY_CAP:
        flags.append("DISPLAY_CAPPED")
    if sample_size < recommended_min_sample(distance_m):
        flags.append("SPARSE_STANDARD")
    if distance_m is not None and distance_m >= 3200:
        flags.append("RARE_DISTANCE")
    if race_type != "FLAT":
        flags.append("NON_FLAT_OR_TRIAL")
    if time_quality != "PLAUSIBLE":
        flags.append(f"TIME_{time_quality}")
    if missing_margin_flag:
        flags.append("MISSING_MARGIN")
    if abnormal_finish_flag:
        flags.append("ABNORMAL_FINISH_CODE")
    if standard_evidence_status != "READY":
        flags.append("LIMITED_STANDARD_CONTEXT")
    return flags


def customer_safe_flag(
    confidence: str,
    flags: List[str],
    evidence_status: str,
) -> str:
    critical = {
        "SPARSE_STANDARD",
        "NON_FLAT_OR_TRIAL",
        "TIME_MISSING_TIME",
        "TIME_SUSPICIOUS_FAST",
        "TIME_SUSPICIOUS_SLOW",
        "MISSING_MARGIN",
        "ABNORMAL_FINISH_CODE",
    }
    if evidence_status != "READY":
        return "NO"
    if confidence == "LOW":
        return "NO"
    if any(flag in critical for flag in flags):
        return "NO"
    return "YES"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    exact_standards, fallback_standards = standard_lookup()
    race_meta = load_race_meta()

    output_rows: List[Dict[str, object]] = []
    confidence_counts: Counter[str] = Counter()
    safe_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    display_band_counts: Counter[str] = Counter()

    with INPUT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_epf = parse_float(row.get("epf_lengths"))
            distance_m = parse_int(row.get("distance"))
            race_date = clean(row.get("race_date"))
            track = upper(row.get("track"))
            race_no = clean(row.get("race_no"))
            condition_group = normalize_condition(row.get("condition_official"))

            standard_row = None
            standard_scope = ""
            if distance_m is not None:
                standard_row = exact_standards.get((track, distance_m, condition_group))
                if standard_row is not None:
                    standard_scope = "TRACK_DISTANCE_CONDITION"
                else:
                    standard_row = fallback_standards.get((track, distance_m))
                    if standard_row is not None:
                        standard_scope = "TRACK_DISTANCE_ALL"
            standard_sample_size = int(parse_float(standard_row.get("sample_races")) or 0) if standard_row else 0
            standard_evidence_status = clean(standard_row.get("evidence_status")) if standard_row else "MISSING"

            meta = race_meta.get((race_date, track, race_no), {})
            race_class = clean(meta.get("race_class"))
            race_name = clean(meta.get("race_name"))
            race_type = race_type_from_meta(race_class, race_name)
            winner_time_sec = parse_float(row.get("winner_time_sec"))
            time_quality = source_time_quality(winner_time_sec, distance_m)
            finish_position = parse_int(row.get("finish_position"))
            beaten_margin = parse_float(row.get("beaten_margin"))
            missing_margin_flag = finish_position not in {1, None} and beaten_margin is None
            abnormal_finish_flag = finish_position is not None and finish_position >= 100

            confidence = confidence_band(
                sample_size=standard_sample_size,
                time_quality=time_quality,
                race_type=race_type,
                distance_m=distance_m,
                abnormal_finish_flag=abnormal_finish_flag,
            )
            flags = build_guardrail_flags(
                raw_epf=raw_epf,
                sample_size=standard_sample_size,
                distance_m=distance_m,
                race_type=race_type,
                time_quality=time_quality,
                missing_margin_flag=missing_margin_flag,
                abnormal_finish_flag=abnormal_finish_flag,
                standard_evidence_status=standard_evidence_status,
            )
            if raw_epf is None:
                display_epf = None
            else:
                display_epf = max(-DISPLAY_CAP, min(DISPLAY_CAP, raw_epf))
            safe_flag = customer_safe_flag(confidence, flags, clean(row.get("evidence_status")))
            raw_epf_band = raw_band(raw_epf)
            display_epf_band = display_band(display_epf, confidence)

            confidence_counts[confidence] += 1
            safe_counts[safe_flag] += 1
            display_band_counts[display_epf_band] += 1
            for flag in flags:
                flag_counts[flag] += 1

            output_rows.append(
                {
                    **row,
                    "raw_epf_lengths": f"{raw_epf:.3f}" if raw_epf is not None else "",
                    "display_epf_lengths": f"{display_epf:.3f}" if display_epf is not None else "",
                    "raw_epf_band": raw_epf_band,
                    "display_epf_band": display_epf_band,
                    "epf_confidence_band": confidence,
                    "epf_guardrail_flag": ";".join(flags) if flags else "NONE",
                    "epf_customer_safe_flag": safe_flag,
                    "standard_sample_size": standard_sample_size,
                    "standard_scope_used": standard_scope or "NONE",
                    "standard_evidence_status": standard_evidence_status,
                    "race_type": race_type,
                    "race_class": race_class or "UNKNOWN",
                    "race_name": race_name,
                    "source_time_quality": time_quality,
                    "built_at_guardrailed": built_at,
                }
            )

    summary_row = {
        "status": "EDGEIQ_EPF_V1_1_GUARDRAILED_BUILT",
        "rows": len(output_rows),
        "high_confidence_rows": confidence_counts.get("HIGH", 0),
        "medium_confidence_rows": confidence_counts.get("MEDIUM", 0),
        "low_confidence_rows": confidence_counts.get("LOW", 0),
        "customer_safe_yes_rows": safe_counts.get("YES", 0),
        "customer_safe_no_rows": safe_counts.get("NO", 0),
        "display_capped_rows": flag_counts.get("DISPLAY_CAPPED", 0),
        "sparse_standard_rows": flag_counts.get("SPARSE_STANDARD", 0),
        "rare_distance_rows": flag_counts.get("RARE_DISTANCE", 0),
        "time_flag_rows": flag_counts.get("TIME_MISSING_TIME", 0) + flag_counts.get("TIME_SUSPICIOUS_FAST", 0) + flag_counts.get("TIME_SUSPICIOUS_SLOW", 0),
        "recommended_display_cap_lengths": DISPLAY_CAP,
        "readiness_verdict": "READY_WITH_GUARDRAILS" if safe_counts.get("YES", 0) > 0 else "NOT_READY",
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(confidence_counts.items()):
        audit_rows.append({"audit_type": "CONFIDENCE_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(safe_counts.items()):
        audit_rows.append({"audit_type": "CUSTOMER_SAFE", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(display_band_counts.items()):
        audit_rows.append({"audit_type": "DISPLAY_EPF_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(flag_counts.items()):
        audit_rows.append({"audit_type": "GUARDRAIL_FLAG", "audit_value": name, "count": count, "built_at": built_at})

    fieldnames = list(output_rows[0].keys()) if output_rows else [
        "race_date",
        "track",
        "race_no",
        "horse",
        "raw_epf_lengths",
        "display_epf_lengths",
        "epf_confidence_band",
        "epf_guardrail_flag",
        "epf_customer_safe_flag",
    ]
    write_csv(OUTPUT_MAIN, output_rows, fieldnames)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ EPF V1.1 guardrailed build complete")
    print(f"Rows: {len(output_rows)}")
    print(f"Customer safe rows: {safe_counts.get('YES', 0)}")
    print(f"Readiness: {summary_row['readiness_verdict']}")


if __name__ == "__main__":
    main()
