import csv
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import re
from statistics import mean, median

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
EXPANSION = DATA / "edgeiq_weight_context_join_expansion_v1.csv"
COLLISIONS = DATA / "edgeiq_weight_context_join_expansion_v1_collision_audit.csv"
UNMATCHED = DATA / "edgeiq_weight_context_join_expansion_v1_unmatched.csv"
OUT = DATA / "edgeiq_weight_context_join_quality_v1.csv"
SUMMARY = DATA / "edgeiq_weight_context_join_quality_v1_summary.csv"
REPORT = DATA / "edgeiq_weight_context_join_quality_v1_report.txt"

csv.field_size_limit(1024 * 1024 * 64)
PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}
STAGES = [
    "STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO",
    "STAGE_2_HORSE_DATE_DISTANCE",
    "STAGE_3_HORSE_DATE_RACE_CLASS",
    "STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN",
    "STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE",
]
BASE_CONFIDENCE = {
    "STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO": 95,
    "STAGE_2_HORSE_DATE_DISTANCE": 82,
    "STAGE_3_HORSE_DATE_RACE_CLASS": 64,
    "STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN": 58,
    "STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE": 48,
}


def clean(value):
    return str(value or "").strip()


def nonblank(value):
    return clean(value).lower() not in PLACEHOLDERS


def parse_num(value):
    text = clean(value).replace("$", "").replace(",", "")
    if text.lower() in PLACEHOLDERS:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_date(value):
    text = clean(value)
    if not text:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(text[:10], fmt).date()
        except Exception:
            pass
    return None


def norm_horse(value):
    text = clean(value).upper().replace("’", "'").replace("`", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def fmt(value, places=2):
    if value is None:
        return ""
    if places == 0:
        return str(int(round(float(value))))
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def date_quality(row):
    vd = parse_date(row.get("race_date"))
    wd = parse_date(row.get("weight_source_race_date"))
    if not vd or not wd:
        return "MISSING_DATE", None
    delta = abs((wd - vd).days)
    if delta == 0:
        return "EXACT_DATE", 0
    if delta <= 2:
        return "DATE_TOLERANCE", delta
    return "DATE_MISMATCH", delta


def distance_agreement(row):
    vd = parse_num(row.get("distance"))
    wd = parse_num(row.get("weight_source_distance"))
    if vd is None or wd is None:
        return "MISSING_DISTANCE", None
    delta = abs(vd - wd)
    if delta == 0:
        return "EXACT_DISTANCE", delta
    if delta <= 50:
        return "NEAR_DISTANCE", delta
    return "DISTANCE_MISMATCH", delta


def finish_agreement(row):
    vf = parse_num(row.get("finish_position"))
    wf = parse_num(row.get("weight_source_finish"))
    if vf is None or wf is None:
        return "MISSING_FINISH", None
    delta = abs(vf - wf)
    if int(round(vf)) == int(round(wf)):
        return "EXACT_FINISH", delta
    return "FINISH_MISMATCH", delta


def margin_agreement(row):
    vm = parse_num(row.get("margin"))
    wm = parse_num(row.get("weight_source_margin"))
    if vm is None or wm is None:
        return "MISSING_MARGIN", None
    delta = abs(vm - wm)
    if delta <= 0.25:
        return "EXACT_MARGIN", delta
    if delta <= 1.0:
        return "NEAR_MARGIN", delta
    return "MARGIN_MISMATCH", delta


def weight_quality(weight):
    if weight is None:
        return "MISSING_WEIGHT"
    if weight < 40 or weight > 80:
        return "IMPOSSIBLE_WEIGHT"
    if weight < 45 or weight > 75:
        return "SUSPICIOUS_WEIGHT_RANGE"
    return "PLAUSIBLE_WEIGHT"


def confidence_band(score):
    if score >= 80:
        return "HIGH"
    if score >= 65:
        return "MEDIUM"
    if score >= 50:
        return "LOW"
    return "QUARANTINE"


def score_row(row, same_day_multi_flag, suspicious_jump_flag):
    stage = row.get("join_stage", "")
    score = BASE_CONFIDENCE.get(stage, 0)
    dq, date_delta = date_quality(row)
    da, distance_delta = distance_agreement(row)
    fa, finish_delta = finish_agreement(row)
    ma, margin_delta = margin_agreement(row)
    weight = parse_num(row.get("carried_weight_kg"))
    wq = weight_quality(weight)
    candidate_count = int(parse_num(row.get("join_candidate_count")) or 0)
    status = row.get("join_status", "")

    if dq == "EXACT_DATE": score += 8
    elif dq == "DATE_TOLERANCE": score += 1
    elif dq == "MISSING_DATE": score -= 20
    else: score -= 35

    if da == "EXACT_DISTANCE": score += 8
    elif da == "NEAR_DISTANCE": score += 3
    elif da == "MISSING_DISTANCE": score -= 4
    else: score -= 22

    if fa == "EXACT_FINISH": score += 6
    elif fa == "MISSING_FINISH": score -= 3
    else: score -= 16

    if ma == "EXACT_MARGIN": score += 6
    elif ma == "NEAR_MARGIN": score += 2
    elif ma == "MISSING_MARGIN": score -= 3
    else: score -= 16

    if candidate_count == 1: score += 4
    elif candidate_count > 1: score -= 10
    if status == "MATCHED_WITH_UNSAFE_REJECTED": score -= 5
    if status == "MATCHED_SP_TIEBREAK": score += 3
    if same_day_multi_flag: score -= 18
    if suspicious_jump_flag: score -= 14
    if wq == "SUSPICIOUS_WEIGHT_RANGE": score -= 15
    elif wq == "IMPOSSIBLE_WEIGHT": score -= 100
    elif wq == "MISSING_WEIGHT": score -= 100

    score = max(0, min(100, round(score, 2)))
    severe = wq in {"IMPOSSIBLE_WEIGHT", "MISSING_WEIGHT"} or dq == "DATE_MISMATCH"
    if score >= 75 and not severe and not same_day_multi_flag:
        verdict = "ROW_SAFE_FOR_REPLAY"
    elif score >= 55 and not severe:
        verdict = "ROW_STAGE_LIMITED_REPLAY_ONLY"
    else:
        verdict = "ROW_NOT_SAFE_FOR_REPLAY"

    return {
        "join_confidence_score": score,
        "join_confidence_band": confidence_band(score),
        "row_quality_verdict": verdict,
        "date_quality": dq,
        "date_delta_days": "" if date_delta is None else date_delta,
        "distance_agreement": da,
        "distance_delta_m": "" if distance_delta is None else fmt(distance_delta, 0),
        "finish_agreement": fa,
        "finish_delta": "" if finish_delta is None else fmt(finish_delta, 0),
        "margin_agreement": ma,
        "margin_delta": "" if margin_delta is None else fmt(margin_delta, 2),
        "weight_quality": wq,
        "same_horse_multiple_matches_same_day": "YES" if same_day_multi_flag else "NO",
        "suspicious_weight_jump": "YES" if suspicious_jump_flag else "NO",
    }


def stage_verdict(stage, rows, collision_count):
    matched = len(rows)
    if matched == 0:
        return "NOT_SAFE_FOR_REPLAY"
    avg_conf = mean([parse_num(r["join_confidence_score"]) or 0 for r in rows])
    row_safe = sum(1 for r in rows if r["row_quality_verdict"] == "ROW_SAFE_FOR_REPLAY")
    limited = sum(1 for r in rows if r["row_quality_verdict"] == "ROW_STAGE_LIMITED_REPLAY_ONLY")
    safe_like_rate = ((row_safe + limited) / matched) * 100
    row_safe_rate = (row_safe / matched) * 100
    collision_rate = (collision_count / (matched + collision_count)) * 100 if (matched + collision_count) else 0
    impossible = sum(1 for r in rows if r["weight_quality"] == "IMPOSSIBLE_WEIGHT")
    same_day = sum(1 for r in rows if r["same_horse_multiple_matches_same_day"] == "YES")
    date_bad = sum(1 for r in rows if r["date_quality"] in {"DATE_MISMATCH", "MISSING_DATE"})
    if avg_conf >= 78 and row_safe_rate >= 90 and collision_rate <= 2 and impossible == 0 and same_day / matched <= 0.02 and date_bad == 0:
        return "SAFE_FOR_REPLAY"
    if avg_conf >= 55 and safe_like_rate >= 80 and impossible == 0 and collision_rate <= 15:
        return "STAGE_LIMITED_REPLAY_ONLY"
    return "NOT_SAFE_FOR_REPLAY"


def main():
    expansion = read_csv(EXPANSION)
    collisions = read_csv(COLLISIONS)
    unmatched = read_csv(UNMATCHED)
    matched = [r for r in expansion if nonblank(r.get("carried_weight_kg")) and r.get("join_stage") != "NO_MATCH"]

    # Same horse multiple matches same day.
    same_day_groups = defaultdict(list)
    for i, row in enumerate(matched):
        same_day_groups[(norm_horse(row.get("horse")), row.get("race_date"))].append(i)
    same_day_multi = set()
    for key, idxs in same_day_groups.items():
        if key[0] and key[1] and len(idxs) > 1:
            same_day_multi.update(idxs)

    # Suspicious weight jumps by horse chronology.
    suspicious_jump = set()
    by_horse = defaultdict(list)
    for i, row in enumerate(matched):
        d = parse_date(row.get("race_date"))
        w = parse_num(row.get("carried_weight_kg"))
        if d and w is not None:
            by_horse[norm_horse(row.get("horse"))].append((d, i, w))
    for horse, entries in by_horse.items():
        entries.sort()
        for (prev_d, prev_i, prev_w), (cur_d, cur_i, cur_w) in zip(entries, entries[1:]):
            if (cur_d - prev_d).days <= 365 and abs(cur_w - prev_w) >= 8:
                suspicious_jump.add(cur_i)

    quality_rows = []
    for i, row in enumerate(matched):
        quality = score_row(row, i in same_day_multi, i in suspicious_jump)
        out = {
            "race_date": row.get("race_date", ""),
            "track": row.get("track", ""),
            "horse": row.get("horse", ""),
            "distance": row.get("distance", ""),
            "race_class_clean": row.get("race_class_clean", ""),
            "finish_position": row.get("finish_position", ""),
            "margin": row.get("margin", ""),
            "performance_rating_v6_1_research": row.get("performance_rating_v6_1_research", ""),
            "carried_weight_kg": row.get("carried_weight_kg", ""),
            "weight_source_race_date": row.get("weight_source_race_date", ""),
            "weight_source_track": row.get("weight_source_track", ""),
            "weight_source_race_no": row.get("weight_source_race_no", ""),
            "weight_source_distance": row.get("weight_source_distance", ""),
            "weight_source_class": row.get("weight_source_class", ""),
            "weight_source_finish": row.get("weight_source_finish", ""),
            "weight_source_margin": row.get("weight_source_margin", ""),
            "join_stage": row.get("join_stage", ""),
            "join_status": row.get("join_status", ""),
            "join_candidate_count": row.get("join_candidate_count", ""),
            **quality,
            "research_scope": "WEIGHT_CONTEXT_JOIN_QUALITY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
        }
        quality_rows.append(out)

    fields = list(quality_rows[0].keys()) if quality_rows else ["race_date", "track", "horse", "join_stage", "join_confidence_score", "row_quality_verdict"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(quality_rows)

    collisions_by_stage = Counter(r.get("stage", "") for r in collisions)
    summary_rows = []
    total_v6_rows = len(expansion)
    total_matched = len(matched)
    safe_rows = sum(1 for r in quality_rows if r["row_quality_verdict"] == "ROW_SAFE_FOR_REPLAY")
    limited_rows = sum(1 for r in quality_rows if r["row_quality_verdict"] == "ROW_STAGE_LIMITED_REPLAY_ONLY")
    not_safe_rows = sum(1 for r in quality_rows if r["row_quality_verdict"] == "ROW_NOT_SAFE_FOR_REPLAY")
    stage_verdicts = {}

    for stage in STAGES:
        rows = [r for r in quality_rows if r["join_stage"] == stage]
        matched_count = len(rows)
        coll_count = collisions_by_stage[stage]
        avg_conf = mean([parse_num(r["join_confidence_score"]) or 0 for r in rows]) if rows else 0
        duplicate_count = sum(1 for r in rows if (parse_num(r.get("join_candidate_count")) or 0) > 1)
        weight_coverage = (sum(1 for r in rows if nonblank(r.get("carried_weight_kg"))) / matched_count * 100) if matched_count else 0
        rating_coverage = (sum(1 for r in rows if nonblank(r.get("performance_rating_v6_1_research"))) / matched_count * 100) if matched_count else 0
        exact_date_rate = (sum(1 for r in rows if r["date_quality"] == "EXACT_DATE") / matched_count * 100) if matched_count else 0
        tolerance_date_rate = (sum(1 for r in rows if r["date_quality"] == "DATE_TOLERANCE") / matched_count * 100) if matched_count else 0
        exact_distance_rate = (sum(1 for r in rows if r["distance_agreement"] == "EXACT_DISTANCE") / matched_count * 100) if matched_count else 0
        exact_finish_rate = (sum(1 for r in rows if r["finish_agreement"] == "EXACT_FINISH") / matched_count * 100) if matched_count else 0
        exact_margin_rate = (sum(1 for r in rows if r["margin_agreement"] == "EXACT_MARGIN") / matched_count * 100) if matched_count else 0
        suspicious_jump_count = sum(1 for r in rows if r["suspicious_weight_jump"] == "YES")
        impossible_count = sum(1 for r in rows if r["weight_quality"] == "IMPOSSIBLE_WEIGHT")
        same_day_count = sum(1 for r in rows if r["same_horse_multiple_matches_same_day"] == "YES")
        verdict = stage_verdict(stage, rows, coll_count)
        stage_verdicts[stage] = verdict
        summary_rows.append({
            "stage": stage,
            "matched_rows": matched_count,
            "avg_confidence": round(avg_conf, 4),
            "collision_count": coll_count,
            "collision_rate_pct": round((coll_count / (matched_count + coll_count)) * 100, 4) if (matched_count + coll_count) else 0,
            "duplicate_match_count": duplicate_count,
            "duplicate_match_rate_pct": round((duplicate_count / matched_count) * 100, 4) if matched_count else 0,
            "weight_coverage_pct": round(weight_coverage, 4),
            "rating_coverage_pct": round(rating_coverage, 4),
            "exact_date_rate_pct": round(exact_date_rate, 4),
            "tolerance_date_rate_pct": round(tolerance_date_rate, 4),
            "exact_distance_rate_pct": round(exact_distance_rate, 4),
            "exact_finish_rate_pct": round(exact_finish_rate, 4),
            "exact_margin_rate_pct": round(exact_margin_rate, 4),
            "suspicious_weight_jump_count": suspicious_jump_count,
            "impossible_weight_count": impossible_count,
            "same_horse_multiple_matches_same_day_count": same_day_count,
            "stage_verdict": verdict,
        })

    stage2_verdict = stage_verdicts.get("STAGE_2_HORSE_DATE_DISTANCE", "NOT_SAFE_FOR_REPLAY")
    stage5_verdict = stage_verdicts.get("STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE", "NOT_SAFE_FOR_REPLAY")
    if stage2_verdict == "SAFE_FOR_REPLAY" and total_matched and (safe_rows + limited_rows) / total_matched >= 0.8:
        overall = "STAGE_LIMITED_REPLAY_ONLY"
    elif any(v == "SAFE_FOR_REPLAY" for v in stage_verdicts.values()):
        overall = "STAGE_LIMITED_REPLAY_ONLY"
    else:
        overall = "NOT_SAFE_FOR_REPLAY"

    summary_rows.extend([
        {"stage": "OVERALL", "matched_rows": total_matched, "avg_confidence": round(mean([parse_num(r["join_confidence_score"]) or 0 for r in quality_rows]), 4) if quality_rows else 0, "collision_count": len(collisions), "collision_rate_pct": round((len(collisions) / (total_matched + len(collisions))) * 100, 4) if total_matched + len(collisions) else 0, "duplicate_match_count": sum(1 for r in quality_rows if (parse_num(r.get("join_candidate_count")) or 0) > 1), "duplicate_match_rate_pct": round((sum(1 for r in quality_rows if (parse_num(r.get("join_candidate_count")) or 0) > 1) / total_matched) * 100, 4) if total_matched else 0, "weight_coverage_pct": 100 if total_matched else 0, "rating_coverage_pct": round((sum(1 for r in quality_rows if nonblank(r.get("performance_rating_v6_1_research"))) / total_matched) * 100, 4) if total_matched else 0, "exact_date_rate_pct": round((sum(1 for r in quality_rows if r["date_quality"] == "EXACT_DATE") / total_matched) * 100, 4) if total_matched else 0, "tolerance_date_rate_pct": round((sum(1 for r in quality_rows if r["date_quality"] == "DATE_TOLERANCE") / total_matched) * 100, 4) if total_matched else 0, "exact_distance_rate_pct": round((sum(1 for r in quality_rows if r["distance_agreement"] == "EXACT_DISTANCE") / total_matched) * 100, 4) if total_matched else 0, "exact_finish_rate_pct": round((sum(1 for r in quality_rows if r["finish_agreement"] == "EXACT_FINISH") / total_matched) * 100, 4) if total_matched else 0, "exact_margin_rate_pct": round((sum(1 for r in quality_rows if r["margin_agreement"] == "EXACT_MARGIN") / total_matched) * 100, 4) if total_matched else 0, "suspicious_weight_jump_count": sum(1 for r in quality_rows if r["suspicious_weight_jump"] == "YES"), "impossible_weight_count": sum(1 for r in quality_rows if r["weight_quality"] == "IMPOSSIBLE_WEIGHT"), "same_horse_multiple_matches_same_day_count": sum(1 for r in quality_rows if r["same_horse_multiple_matches_same_day"] == "YES"), "stage_verdict": overall},
        {"stage": "CONTROL", "matched_rows": total_v6_rows, "avg_confidence": "", "collision_count": "", "collision_rate_pct": "", "duplicate_match_count": "", "duplicate_match_rate_pct": "", "weight_coverage_pct": round((total_matched / total_v6_rows) * 100, 4) if total_v6_rows else 0, "rating_coverage_pct": "", "exact_date_rate_pct": "", "tolerance_date_rate_pct": "", "exact_distance_rate_pct": "", "exact_finish_rate_pct": "", "exact_margin_rate_pct": "", "suspicious_weight_jump_count": "", "impossible_weight_count": "", "same_horse_multiple_matches_same_day_count": "", "stage_verdict": "coverage_denominator_v6_1_rows"},
        {"stage": "CONSTRAINTS", "matched_rows": "", "avg_confidence": "", "collision_count": "", "collision_rate_pct": "", "duplicate_match_count": "", "duplicate_match_rate_pct": "", "weight_coverage_pct": "", "rating_coverage_pct": "", "exact_date_rate_pct": "", "tolerance_date_rate_pct": "", "exact_distance_rate_pct": "", "exact_finish_rate_pct": "", "exact_margin_rate_pct": "", "suspicious_weight_jump_count": "", "impossible_weight_count": "", "same_horse_multiple_matches_same_day_count": "", "stage_verdict": "research_only_no_production_no_pricing_no_v6_1_no_v7_2g2_no_ui"},
    ])

    summary_fields = list(summary_rows[0].keys())
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader(); writer.writerows(summary_rows)

    stage5_rows = [r for r in quality_rows if r["join_stage"] == "STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE"]
    stage5_date_deltas = [parse_num(r["date_delta_days"]) for r in stage5_rows if parse_num(r["date_delta_days"]) is not None]
    report_lines = [
        "EDGEIQ_WEIGHT_CONTEXT_JOIN_QUALITY_V1",
        f"v6_1_rows={total_v6_rows}",
        f"matched_rows_quality_audited={total_matched}",
        f"unmatched_rows={len(unmatched)}",
        f"safe_rows={safe_rows}",
        f"stage_limited_rows={limited_rows}",
        f"not_safe_rows={not_safe_rows}",
        f"collision_rows={len(collisions)}",
        f"overall_verdict={overall}",
        "",
        "STAGE_VERDICTS",
    ]
    for r in summary_rows:
        if r["stage"] in STAGES:
            report_lines.append(f"{r['stage']}: matched={r['matched_rows']} avg_conf={r['avg_confidence']} collision_rate={r['collision_rate_pct']} exact_date={r['exact_date_rate_pct']} exact_distance={r['exact_distance_rate_pct']} exact_finish={r['exact_finish_rate_pct']} exact_margin={r['exact_margin_rate_pct']} verdict={r['stage_verdict']}")
    report_lines.extend([
        "",
        "STAGE_5_DATE_TOLERANCE_RISK_AUDIT",
        f"stage5_rows={len(stage5_rows)}",
        f"stage5_avg_date_delta_days={round(mean(stage5_date_deltas), 4) if stage5_date_deltas else 0}",
        f"stage5_max_date_delta_days={max(stage5_date_deltas) if stage5_date_deltas else 0}",
        f"stage5_verdict={stage5_verdict}",
        "",
        "CONSTRAINTS",
        "research_only=YES",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "ui_changed=NO",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "wfa_claim_made=NO",
    ])
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(REPORT)

if __name__ == "__main__":
    main()
