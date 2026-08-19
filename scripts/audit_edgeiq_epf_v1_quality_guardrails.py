from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_EPF = DATA / "edgeiq_epf_v1.csv"
INPUT_STANDARDS = DATA / "edgeiq_historical_standard_times_v1.csv"
INPUT_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
INPUT_CURRENT_EPF = DATA / "edgeiq_current_epf_feed_v1.csv"
INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"

OUTPUT_AUDIT = DATA / "edgeiq_epf_v1_quality_guardrails_audit.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_epf_v1_quality_guardrails_summary.csv"

DISPLAY_CAP = 20.0
MIN_STANDARD_SAMPLE = 10
MIN_STANDARD_SAMPLE_RARE_DISTANCE = 12


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


def distance_band(distance_m: Optional[int]) -> str:
    if distance_m is None:
        return "UNKNOWN"
    if distance_m < 1000:
        return "LT_1000"
    if distance_m <= 1199:
        return "1000_1199"
    if distance_m <= 1399:
        return "1200_1399"
    if distance_m <= 1599:
        return "1400_1599"
    if distance_m <= 1999:
        return "1600_1999"
    if distance_m <= 2399:
        return "2000_2399"
    if distance_m <= 3199:
        return "2400_3199"
    return "3200_PLUS"


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


def sample_band(sample_size: int) -> str:
    if sample_size <= 0:
        return "0"
    if sample_size < 5:
        return "1_4"
    if sample_size < 10:
        return "5_9"
    if sample_size < 20:
        return "10_19"
    return "20_PLUS"


def recommended_min_sample(distance_m: Optional[int]) -> int:
    if distance_m is not None and distance_m >= 3200:
        return MIN_STANDARD_SAMPLE_RARE_DISTANCE
    return MIN_STANDARD_SAMPLE


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


def is_active(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return not any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not INPUT_EPF.exists():
        raise FileNotFoundError(INPUT_EPF)
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    exact_standards, fallback_standards = standard_lookup()
    race_meta = load_race_meta()

    active_board = []
    with INPUT_BOARD.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if is_active(row):
                active_board.append(row)

    current_feed_rows = []
    with INPUT_CURRENT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
        current_feed_rows = list(csv.DictReader(handle))

    active_epf_by_runner = {
        (clean(row.get("current_race_date")), upper(row.get("track")), clean(row.get("race_no")), clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))): row
        for row in current_feed_rows
    }

    detail_rows: List[Dict[str, object]] = []
    root_causes_gt25: Counter[str] = Counter()
    root_causes_gt50: Counter[str] = Counter()
    threshold_counts: Counter[str] = Counter()
    sample_band_counts: Counter[str] = Counter()
    distance_band_counts: Counter[str] = Counter()
    time_quality_counts: Counter[str] = Counter()
    race_type_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    condition_counts: Counter[str] = Counter()
    active_extremes = 0

    with INPUT_EPF.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_epf = parse_float(row.get("epf_lengths"))
            if raw_epf is None:
                continue
            abs_epf = abs(raw_epf)
            if abs_epf <= 25:
                continue

            race_date = clean(row.get("race_date"))
            track = upper(row.get("track"))
            race_no = clean(row.get("race_no"))
            horse_key = clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))
            distance_m = parse_int(row.get("distance"))
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
            race_key = (race_date, track, race_no)
            meta = race_meta.get(race_key, {})
            race_class = clean(meta.get("race_class"))
            race_name = clean(meta.get("race_name"))
            race_type = race_type_from_meta(race_class, race_name)
            time_quality = source_time_quality(parse_float(row.get("winner_time_sec")), distance_m)
            finish_position = parse_int(row.get("finish_position"))
            beaten_margin = parse_float(row.get("beaten_margin"))
            missing_margin_flag = finish_position not in {1, None} and beaten_margin is None
            unusual_margin_flag = beaten_margin is not None and beaten_margin >= 25.0
            abnormal_finish_flag = finish_position is not None and finish_position >= 100
            rare_distance_flag = distance_m is not None and distance_m >= 3200
            sparse_standard_flag = standard_sample_size < recommended_min_sample(distance_m)
            confidence = confidence_band(
                sample_size=standard_sample_size,
                time_quality=time_quality,
                race_type=race_type,
                distance_m=distance_m,
                abnormal_finish_flag=abnormal_finish_flag,
            )

            causes: List[str] = []
            if sparse_standard_flag:
                causes.append("SPARSE_STANDARD")
            if rare_distance_flag:
                causes.append("RARE_DISTANCE")
            if race_type != "FLAT":
                causes.append("NON_FLAT_OR_TRIAL")
            if time_quality != "PLAUSIBLE":
                causes.append(f"TIME_{time_quality}")
            if missing_margin_flag:
                causes.append("MISSING_MARGIN")
            if unusual_margin_flag:
                causes.append("UNUSUAL_MARGIN")
            if abnormal_finish_flag:
                causes.append("ABNORMAL_FINISH_CODE")
            if standard_evidence_status != "READY":
                causes.append("LIMITED_STANDARD_CONTEXT")

            if raw_epf > 25:
                threshold_counts["GT_POS_25"] += 1
            if raw_epf < -25:
                threshold_counts["LT_NEG_25"] += 1
            if raw_epf > 50:
                threshold_counts["GT_POS_50"] += 1
            if raw_epf < -50:
                threshold_counts["LT_NEG_50"] += 1
            if abs_epf > 50:
                for cause in causes or ["NO_CLEAR_CAUSE"]:
                    root_causes_gt50[cause] += 1
            for cause in causes or ["NO_CLEAR_CAUSE"]:
                root_causes_gt25[cause] += 1

            sample_band_counts[sample_band(standard_sample_size)] += 1
            distance_band_counts[distance_band(distance_m)] += 1
            time_quality_counts[time_quality] += 1
            race_type_counts[race_type] += 1
            class_counts[race_class or "UNKNOWN"] += 1
            condition_counts[condition_group] += 1

            active_row = active_epf_by_runner.get((race_date, track, race_no, horse_key))
            current_extreme = False
            if active_row:
                current_reweighted = parse_float(active_row.get("recency_weighted_epf"))
                current_extreme = current_reweighted is not None and abs(current_reweighted) > 20
                if current_extreme:
                    active_extremes += 1

            detail_rows.append(
                {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "horse": clean(row.get("horse")),
                    "horse_key": horse_key,
                    "distance_m": distance_m if distance_m is not None else "",
                    "distance_band": distance_band(distance_m),
                    "condition_group": condition_group,
                    "race_class": race_class or "UNKNOWN",
                    "race_name": race_name,
                    "race_type": race_type,
                    "finish_position": finish_position if finish_position is not None else "",
                    "beaten_margin": f"{beaten_margin:.3f}" if beaten_margin is not None else "",
                    "raw_epf_lengths": f"{raw_epf:.3f}",
                    "epf_sign": "POSITIVE" if raw_epf > 0 else "NEGATIVE",
                    "extreme_band": "ABS_GT_50" if abs_epf > 50 else "ABS_GT_25",
                    "winner_time_sec": clean(row.get("winner_time_sec")),
                    "source_time_quality": time_quality,
                    "standard_sample_size": standard_sample_size,
                    "standard_scope_used": standard_scope or "NONE",
                    "standard_evidence_status": standard_evidence_status,
                    "standard_sample_band": sample_band(standard_sample_size),
                    "epf_confidence_band_candidate": confidence,
                    "sparse_standard_flag": "YES" if sparse_standard_flag else "NO",
                    "rare_distance_flag": "YES" if rare_distance_flag else "NO",
                    "unusual_margin_flag": "YES" if unusual_margin_flag else "NO",
                    "missing_margin_flag": "YES" if missing_margin_flag else "NO",
                    "abnormal_finish_flag": "YES" if abnormal_finish_flag else "NO",
                    "root_cause_flags": ";".join(causes) if causes else "NO_CLEAR_CAUSE",
                    "current_active_runner_flag": "YES" if active_row else "NO",
                    "current_active_extreme_flag": "YES" if current_extreme else "NO",
                    "source_file": clean(row.get("source_file")) or clean(meta.get("source_file")),
                    "built_at": built_at,
                }
            )

    bendigo_board = [row for row in active_board if upper(row.get("track")) == "BENDIGO"]
    bendigo_total = len(bendigo_board)
    bendigo_matched = 0
    for row in current_feed_rows:
        if upper(row.get("track")) == "BENDIGO" and clean(row.get("evidence_status")) != "NO_HISTORY":
            bendigo_matched += 1

    current_band_counts = Counter(clean(row.get("epf_band_current")) or "UNKNOWN" for row in current_feed_rows)
    current_safe_status = "NEEDS_GUARDRAILS"

    summary_rows: List[Dict[str, object]] = [
        {"section": "OVERALL", "key": "extreme_rows_abs_gt_25", "value": len(detail_rows), "built_at": built_at},
        {"section": "OVERALL", "key": "gt_pos_25", "value": threshold_counts.get("GT_POS_25", 0), "built_at": built_at},
        {"section": "OVERALL", "key": "lt_neg_25", "value": threshold_counts.get("LT_NEG_25", 0), "built_at": built_at},
        {"section": "OVERALL", "key": "gt_pos_50", "value": threshold_counts.get("GT_POS_50", 0), "built_at": built_at},
        {"section": "OVERALL", "key": "lt_neg_50", "value": threshold_counts.get("LT_NEG_50", 0), "built_at": built_at},
    ]

    for key, count in sorted(root_causes_gt25.items()):
        summary_rows.append({"section": "ROOT_CAUSE_ABS_GT_25", "key": key, "value": count, "built_at": built_at})
    for key, count in sorted(root_causes_gt50.items()):
        summary_rows.append({"section": "ROOT_CAUSE_ABS_GT_50", "key": key, "value": count, "built_at": built_at})
    for key, count in sorted(sample_band_counts.items()):
        summary_rows.append({"section": "SAMPLE_BAND", "key": key, "value": count, "built_at": built_at})
    for key, count in sorted(distance_band_counts.items()):
        summary_rows.append({"section": "DISTANCE_BAND", "key": key, "value": count, "built_at": built_at})
    for key, count in sorted(time_quality_counts.items()):
        summary_rows.append({"section": "TIME_QUALITY", "key": key, "value": count, "built_at": built_at})
    for key, count in sorted(race_type_counts.items()):
        summary_rows.append({"section": "RACE_TYPE", "key": key, "value": count, "built_at": built_at})

    summary_rows.extend(
        [
            {"section": "ACTIVE_FEED", "key": "active_runner_rows", "value": len(current_feed_rows), "built_at": built_at},
            {"section": "ACTIVE_FEED", "key": "active_current_extremes_recency_weighted_gt_20", "value": active_extremes, "built_at": built_at},
            {"section": "ACTIVE_FEED", "key": "bendigo_active_rows", "value": bendigo_total, "built_at": built_at},
            {"section": "ACTIVE_FEED", "key": "bendigo_epf_matched_rows", "value": bendigo_matched, "built_at": built_at},
            {"section": "ACTIVE_FEED", "key": "customer_safe_pre_guardrail_verdict", "value": current_safe_status, "built_at": built_at},
            {"section": "RECOMMENDATION", "key": "recommended_display_cap_lengths", "value": DISPLAY_CAP, "built_at": built_at},
            {"section": "RECOMMENDATION", "key": "recommended_min_standard_sample", "value": MIN_STANDARD_SAMPLE, "built_at": built_at},
            {"section": "RECOMMENDATION", "key": "recommended_min_standard_sample_rare_distance", "value": MIN_STANDARD_SAMPLE_RARE_DISTANCE, "built_at": built_at},
            {
                "section": "RECOMMENDATION",
                "key": "recommended_exclusion_rules",
                "value": "NON_FLAT_OR_TRIAL|MISSING_TIME|SUSPICIOUS_TIME|SPARSE_STANDARD|ABNORMAL_FINISH_CODE",
                "built_at": built_at,
            },
        ]
    )

    for key, count in sorted(current_band_counts.items()):
        summary_rows.append({"section": "ACTIVE_BAND_V1", "key": key, "value": count, "built_at": built_at})

    detail_fields = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "distance_m",
        "distance_band",
        "condition_group",
        "race_class",
        "race_name",
        "race_type",
        "finish_position",
        "beaten_margin",
        "raw_epf_lengths",
        "epf_sign",
        "extreme_band",
        "winner_time_sec",
        "source_time_quality",
        "standard_sample_size",
        "standard_scope_used",
        "standard_evidence_status",
        "standard_sample_band",
        "epf_confidence_band_candidate",
        "sparse_standard_flag",
        "rare_distance_flag",
        "unusual_margin_flag",
        "missing_margin_flag",
        "abnormal_finish_flag",
        "root_cause_flags",
        "current_active_runner_flag",
        "current_active_extreme_flag",
        "source_file",
        "built_at",
    ]

    write_csv(OUTPUT_AUDIT, detail_rows, detail_fields)
    write_csv(OUTPUT_SUMMARY, summary_rows, ["section", "key", "value", "built_at"])

    print("EDGEiQ EPF V1 quality guardrail audit complete")
    print(f"Extreme rows >25L absolute: {len(detail_rows)}")
    print(f"Current active rows: {len(current_feed_rows)}")
    print(f"Bendigo current EPF matches: {bendigo_matched}/{bendigo_total}")
    print("Recommended display cap: 20L")
    print("Recommended readiness: NEEDS_GUARDRAILS")


if __name__ == "__main__":
    main()
