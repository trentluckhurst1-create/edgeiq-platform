import csv
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
V6_SOURCE = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
WEIGHT_SOURCE = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
OUT = DATA / "edgeiq_weight_context_join_expansion_v1.csv"
SUMMARY = DATA / "edgeiq_weight_context_join_expansion_v1_summary.csv"
UNMATCHED = DATA / "edgeiq_weight_context_join_expansion_v1_unmatched.csv"
COLLISION = DATA / "edgeiq_weight_context_join_expansion_v1_collision_audit.csv"
REPORT = DATA / "edgeiq_weight_context_join_expansion_v1_report.txt"

csv.field_size_limit(1024 * 1024 * 64)
PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}


def clean(value):
    return str(value or "").strip()


def nonblank(value):
    return clean(value).lower() not in PLACEHOLDERS


def first(row, keys):
    for key in keys:
        value = clean(row.get(key, ""))
        if nonblank(value):
            return value
    return ""


def norm_horse(value):
    text = clean(value).upper().replace("’", "'").replace("`", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value):
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def norm_class(value):
    text = clean(value).upper()
    text = text.replace("+", "UP")
    return re.sub(r"[^A-Z0-9]+", "", text)


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


def fmt_num(value, places=2):
    if value is None:
        return ""
    if places == 0:
        return str(int(round(float(value))))
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


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


def date_text(value):
    d = parse_date(value)
    return d.isoformat() if d else clean(value)


def finish_num(row):
    return parse_num(first(row, ["finish_position", "finish_pos", "finish_pos_raw"]))


def margin_num(row):
    return parse_num(first(row, ["margin", "margin_raw"]))


def distance_num(row):
    return parse_num(first(row, ["distance", "distance_m"]))


def rating_num(row):
    return parse_num(first(row, ["performance_rating_v6_1_research", "performance_rating_v6", "performance_rating_v5_1", "performance_rating"] ))


def weight_num(row):
    return parse_num(first(row, ["weight", "wgt", "weight_carried", "allocated_weight"] ))


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def key_parts(row, stage):
    horse = norm_horse(first(row, ["horse", "horse_name", "runner_name", "horse_key"] ))
    date = date_text(first(row, ["race_date", "date", "meeting_date"] ))
    track = norm_track(first(row, ["track", "venue"] ))
    race_no = first(row, ["race_no", "race", "race_number"] )
    distance = fmt_num(distance_num(row), 0)
    race_class = norm_class(first(row, ["race_class_clean", "race_class_clean_v3_3", "race_class_recovered", "race_class_raw", "race_class", "class_name"] ))
    finish = fmt_num(finish_num(row), 0)
    margin = fmt_num(margin_num(row), 1)
    if stage == "STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO":
        return "|".join([horse, date, track, race_no]) if horse and date and track and race_no else ""
    if stage == "STAGE_2_HORSE_DATE_DISTANCE":
        return "|".join([horse, date, distance]) if horse and date and distance else ""
    if stage == "STAGE_3_HORSE_DATE_RACE_CLASS":
        return "|".join([horse, date, race_class]) if horse and date and race_class else ""
    if stage == "STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN":
        return "|".join([horse, track, distance, finish, margin]) if horse and track and distance and finish and margin else ""
    return ""


def make_indices(weight_rows):
    stages = [
        "STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO",
        "STAGE_2_HORSE_DATE_DISTANCE",
        "STAGE_3_HORSE_DATE_RACE_CLASS",
        "STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN",
    ]
    indices = {stage: defaultdict(list) for stage in stages}
    date_tolerance = defaultdict(list)
    for row in weight_rows:
        if weight_num(row) is None:
            continue
        enriched = dict(row)
        enriched["_weight_kg"] = weight_num(row)
        for stage in stages:
            key = key_parts(enriched, stage)
            if key:
                indices[stage][key].append(enriched)
        horse = norm_horse(first(enriched, ["horse", "horse_name", "runner_name", "horse_key"] ))
        track = norm_track(first(enriched, ["track", "venue"] ))
        distance = fmt_num(distance_num(enriched), 0)
        finish = fmt_num(finish_num(enriched), 0)
        margin = fmt_num(margin_num(enriched), 1)
        d = parse_date(first(enriched, ["race_date", "date", "meeting_date"] ))
        if horse and track and distance and d:
            date_tolerance[(horse, track, distance)].append(enriched)
        if horse and finish and margin and d:
            date_tolerance[(horse, finish, margin)].append(enriched)
    return indices, date_tolerance


def same_finish_margin(v6, w):
    vf, wf = finish_num(v6), finish_num(w)
    vm, wm = margin_num(v6), margin_num(w)
    finish_ok = vf is None or wf is None or int(round(vf)) == int(round(wf))
    margin_ok = vm is None or wm is None or abs(vm - wm) <= 0.25
    return finish_ok and margin_ok


def choose_unique(v6_row, matches, stage, collision_rows):
    if not matches:
        return None, "NO_CANDIDATE", 0
    safe = [m for m in matches if same_finish_margin(v6_row, m)]
    rejected = len(matches) - len(safe)
    candidates = safe or matches
    if len(candidates) == 1 and not rejected:
        return candidates[0], "MATCHED", len(matches)
    if len(candidates) == 1 and rejected:
        return candidates[0], "MATCHED_WITH_UNSAFE_REJECTED", len(matches)
    # Try same SP as a last deterministic tie-break if available.
    vsp = parse_num(first(v6_row, ["sp", "SP"] ))
    if vsp is not None:
        sp_matches = [m for m in candidates if parse_num(first(m, ["sp", "SP"] )) is not None and abs(parse_num(first(m, ["sp", "SP"] )) - vsp) < 0.01]
        if len(sp_matches) == 1:
            return sp_matches[0], "MATCHED_SP_TIEBREAK", len(matches)
    collision_rows.append({
        "stage": stage,
        "v6_race_date": first(v6_row, ["race_date", "date", "meeting_date"]),
        "v6_track": first(v6_row, ["track", "venue"]),
        "v6_horse": first(v6_row, ["horse", "horse_name", "runner_name"]),
        "v6_distance": fmt_num(distance_num(v6_row), 0),
        "v6_finish": fmt_num(finish_num(v6_row), 0),
        "v6_margin": fmt_num(margin_num(v6_row), 2),
        "candidate_count": len(matches),
        "safe_candidate_count": len(safe),
        "unsafe_rejected_count": rejected,
        "decision": "REJECTED_COLLISION",
    })
    return None, "REJECTED_COLLISION", len(matches)


def date_tolerance_candidates(v6_row, date_index):
    horse = norm_horse(first(v6_row, ["horse", "horse_name", "runner_name", "horse_key"] ))
    track = norm_track(first(v6_row, ["track", "venue"] ))
    distance = fmt_num(distance_num(v6_row), 0)
    finish = fmt_num(finish_num(v6_row), 0)
    margin = fmt_num(margin_num(v6_row), 1)
    vd = parse_date(first(v6_row, ["race_date", "date", "meeting_date"] ))
    if not horse or not vd:
        return []
    pools = []
    if horse and track and distance:
        pools.extend(date_index.get((horse, track, distance), []))
    if horse and finish and margin:
        pools.extend(date_index.get((horse, finish, margin), []))
    seen = set()
    out = []
    for row in pools:
        wd = parse_date(first(row, ["race_date", "date", "meeting_date"] ))
        if not wd or abs((wd - vd).days) > 2:
            continue
        ident = (first(row, ["race_date"]), first(row, ["track"]), first(row, ["race_no"]), first(row, ["horse"]), first(row, ["weight"]), first(row, ["finish_pos"]), first(row, ["margin"] ))
        if ident in seen:
            continue
        seen.add(ident)
        out.append(row)
    return out


def weight_band(weight):
    if weight is None:
        return "MISSING_WEIGHT"
    if weight < 52:
        return "LIGHT_UNDER_52"
    if weight < 55:
        return "LIGHT_52_TO_54_9"
    if weight < 58:
        return "MID_55_TO_57_9"
    if weight < 61:
        return "HIGH_58_TO_60_9"
    return "TOPWEIGHT_61_PLUS"


def main():
    v6_rows = read_csv(V6_SOURCE)
    weight_rows = read_csv(WEIGHT_SOURCE)
    indices, date_index = make_indices(weight_rows)
    stages = [
        "STAGE_1_EXACT_HORSE_DATE_TRACK_RACE_NO",
        "STAGE_2_HORSE_DATE_DISTANCE",
        "STAGE_3_HORSE_DATE_RACE_CLASS",
        "STAGE_4_HORSE_TRACK_DISTANCE_FINISH_MARGIN",
        "STAGE_5_NORMALISED_HORSE_DATE_TOLERANCE",
    ]
    stage_counts = Counter()
    stage_status = Counter()
    collision_rows = []
    unmatched = []
    output = []
    duplicate_match_count = 0
    unsafe_rejected = 0

    for row in v6_rows:
        selected = None
        selected_stage = "NO_MATCH"
        selected_status = "NO_CANDIDATE"
        candidate_count = 0
        for stage in stages[:4]:
            key = key_parts(row, stage)
            matches = indices[stage].get(key, []) if key else []
            candidate_count = len(matches)
            if candidate_count > 1:
                duplicate_match_count += 1
            match, status, raw_count = choose_unique(row, matches, stage, collision_rows)
            stage_status[(stage, status)] += 1
            if status == "MATCHED_WITH_UNSAFE_REJECTED":
                unsafe_rejected += max(0, raw_count - 1)
            if match is not None:
                selected = match
                selected_stage = stage
                selected_status = status
                candidate_count = raw_count
                break
            if status == "REJECTED_COLLISION":
                unsafe_rejected += raw_count
        if selected is None:
            stage = stages[4]
            matches = date_tolerance_candidates(row, date_index)
            if len(matches) > 1:
                duplicate_match_count += 1
            match, status, raw_count = choose_unique(row, matches, stage, collision_rows)
            stage_status[(stage, status)] += 1
            if status == "MATCHED_WITH_UNSAFE_REJECTED":
                unsafe_rejected += max(0, raw_count - 1)
            if status == "REJECTED_COLLISION":
                unsafe_rejected += raw_count
            if match is not None:
                selected = match
                selected_stage = stage
                selected_status = status
                candidate_count = raw_count

        if selected is not None:
            stage_counts[selected_stage] += 1
        else:
            unmatched.append({
                "race_date": first(row, ["race_date", "date", "meeting_date"]),
                "track": first(row, ["track", "venue"]),
                "horse": first(row, ["horse", "horse_name", "runner_name"]),
                "distance": fmt_num(distance_num(row), 0),
                "race_class_clean": first(row, ["race_class_clean", "race_class_clean_v3_3", "race_class_recovered", "race_class_raw", "race_class"]),
                "finish_position": fmt_num(finish_num(row), 0),
                "margin": fmt_num(margin_num(row), 2),
                "unmatched_reason": selected_status,
            })

        weight = selected.get("_weight_kg") if selected else None
        output.append({
            "race_date": first(row, ["race_date", "date", "meeting_date"]),
            "track": first(row, ["track", "venue"]),
            "horse": first(row, ["horse", "horse_name", "runner_name"]),
            "distance": fmt_num(distance_num(row), 0),
            "race_class_clean": first(row, ["race_class_clean", "race_class_clean_v3_3", "race_class_recovered", "race_class_raw", "race_class"]),
            "condition_recovered": first(row, ["condition_recovered", "condition", "track_condition"]),
            "finish_position": fmt_num(finish_num(row), 0),
            "margin": fmt_num(margin_num(row), 2),
            "performance_rating_v6_1_research": fmt_num(rating_num(row), 2),
            "carried_weight_kg": fmt_num(weight, 2),
            "weight_band_research_v1": weight_band(weight),
            "weight_source_race_date": first(selected or {}, ["race_date", "date", "meeting_date"]),
            "weight_source_track": first(selected or {}, ["track", "venue"]),
            "weight_source_race_no": first(selected or {}, ["race_no", "race", "race_number"]),
            "weight_source_distance": fmt_num(distance_num(selected or {}), 0),
            "weight_source_class": first(selected or {}, ["class_name", "race_class", "race_class_clean"]),
            "weight_source_finish": fmt_num(finish_num(selected or {}), 0),
            "weight_source_margin": fmt_num(margin_num(selected or {}), 2),
            "weight_source_jockey": first(selected or {}, ["jockey", "rider"]),
            "weight_source_trainer": first(selected or {}, ["trainer"]),
            "weight_source_sp": first(selected or {}, ["sp", "SP"]),
            "join_stage": selected_stage,
            "join_status": selected_status,
            "join_candidate_count": candidate_count,
            "research_scope": "JOIN_EXPANSION_WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "built_at": datetime.now(timezone.utc).isoformat(),
        })

    out_fields = list(output[0].keys()) if output else []
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader(); writer.writerows(output)

    unmatched_fields = list(unmatched[0].keys()) if unmatched else ["race_date", "track", "horse", "distance", "race_class_clean", "finish_position", "margin", "unmatched_reason"]
    with UNMATCHED.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=unmatched_fields)
        writer.writeheader(); writer.writerows(unmatched)

    collision_fields = ["stage", "v6_race_date", "v6_track", "v6_horse", "v6_distance", "v6_finish", "v6_margin", "candidate_count", "safe_candidate_count", "unsafe_rejected_count", "decision"]
    with COLLISION.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=collision_fields)
        writer.writeheader(); writer.writerows(collision_rows)

    total = len(v6_rows)
    matched = sum(stage_counts.values())
    coverage = (matched / total) * 100 if total else 0
    good_enough = "YES_WITH_WARNINGS" if coverage >= 50 else "NO_REPLAY_COVERAGE_TOO_LOW"
    summary = [
        {"metric": "v6_1_rows", "value": total},
        {"metric": "weight_source_rows", "value": len(weight_rows)},
        {"metric": "matched_rows", "value": matched},
        {"metric": "final_coverage_pct", "value": f"{coverage:.4f}"},
        {"metric": "unmatched_rows", "value": len(unmatched)},
        {"metric": "collision_count", "value": len(collision_rows)},
        {"metric": "duplicate_match_count", "value": duplicate_match_count},
        {"metric": "unsafe_matches_rejected", "value": unsafe_rejected},
        {"metric": "good_enough_for_replay", "value": good_enough},
        {"metric": "age_fields_used", "value": "NO"},
        {"metric": "sex_fields_used", "value": "NO"},
        {"metric": "wfa_claim_made", "value": "NO"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "status", "value": "EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1_BUILT"},
    ]
    for stage in stages:
        summary.append({"metric": f"matched_{stage}", "value": stage_counts[stage]})
    for (stage, status), count in stage_status.most_common():
        summary.append({"metric": f"stage_status_{stage}_{status}", "value": count})

    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader(); writer.writerows(summary)

    REPORT.write_text("\n".join([
        "EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1",
        f"v6_1_rows={total}",
        f"matched_rows={matched}",
        f"final_coverage_pct={coverage:.4f}",
        f"collision_count={len(collision_rows)}",
        f"duplicate_match_count={duplicate_match_count}",
        f"unsafe_matches_rejected={unsafe_rejected}",
        f"good_enough_for_replay={good_enough}",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "wfa_claim_made=NO",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "status=EDGEIQ_WEIGHT_CONTEXT_JOIN_EXPANSION_V1_BUILT",
    ]) + "\n", encoding="utf-8")
    print(REPORT)

if __name__ == "__main__":
    main()
