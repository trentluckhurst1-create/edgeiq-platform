import csv
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean, median
from datetime import datetime, timezone
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
V6_SOURCE = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
WEIGHT_SOURCE = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
OUT = DATA / "edgeiq_weight_context_research_v1.csv"
AUDIT = DATA / "edgeiq_weight_context_research_v1_audit.csv"
SUMMARY = DATA / "edgeiq_weight_context_research_v1_summary.csv"
REPORT = DATA / "edgeiq_weight_context_research_v1_report.txt"

csv.field_size_limit(1024 * 1024 * 64)

PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}


def clean(value):
    return str(value or "").strip()


def norm_text(value):
    text = clean(value).upper()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def norm_track(value):
    text = clean(value).upper()
    text = re.sub(r"[^A-Z0-9]+", "", text)
    return text


def parse_num(value):
    text = clean(value)
    if text.lower() in PLACEHOLDERS:
        return None
    text = text.replace("$", "").replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def parse_int(value):
    n = parse_num(value)
    return int(n) if n is not None else None


def fmt(value, places=2):
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if places == 0:
        return str(int(round(float(value))))
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


def first(row, keys):
    for key in keys:
        value = clean(row.get(key, ""))
        if value and value.lower() not in PLACEHOLDERS:
            return value
    return ""


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def key_exact(row):
    return "|".join([
        first(row, ["race_date", "date", "meeting_date"]),
        norm_track(first(row, ["track", "venue"])),
        norm_text(first(row, ["horse", "horse_name", "runner_name", "horse_key"])),
        fmt(parse_num(first(row, ["distance", "distance_m"])), 0),
    ])


def key_no_distance(row):
    return "|".join([
        first(row, ["race_date", "date", "meeting_date"]),
        norm_track(first(row, ["track", "venue"])),
        norm_text(first(row, ["horse", "horse_name", "runner_name", "horse_key"])),
    ])


def key_horse_only(row):
    return norm_text(first(row, ["horse", "horse_name", "runner_name", "horse_key"]))


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


def relative_band(delta):
    if delta is None:
        return "MISSING"
    if delta <= -3:
        return "WELL_BELOW_RACE_AVG"
    if delta <= -1:
        return "BELOW_RACE_AVG"
    if delta < 1:
        return "NEAR_RACE_AVG"
    if delta < 3:
        return "ABOVE_RACE_AVG"
    return "WELL_ABOVE_RACE_AVG"


def build_index(weight_rows):
    exact = defaultdict(list)
    no_distance = defaultdict(list)
    horse_only = defaultdict(list)
    for row in weight_rows:
        weight = parse_num(first(row, ["weight", "wgt", "weight_carried", "allocated_weight"] ))
        if weight is None:
            continue
        enriched = dict(row)
        enriched["_weight_kg"] = weight
        exact[key_exact(row)].append(enriched)
        no_distance[key_no_distance(row)].append(enriched)
        horse_only[key_horse_only(row)].append(enriched)
    return exact, no_distance, horse_only


def choose_match(v6_row, exact, no_distance, horse_only):
    for method, idx, key_func in [
        ("EXACT_DATE_TRACK_HORSE_DISTANCE", exact, key_exact),
        ("DATE_TRACK_HORSE", no_distance, key_no_distance),
    ]:
        key = key_func(v6_row)
        matches = idx.get(key, [])
        if len(matches) == 1:
            return matches[0], method, len(matches)
        if len(matches) > 1:
            finish = parse_int(first(v6_row, ["finish_position", "finish_pos", "finish_pos_raw"] ))
            if finish is not None:
                finish_matches = [m for m in matches if parse_int(first(m, ["finish_pos", "finish_position"])) == finish]
                if len(finish_matches) == 1:
                    return finish_matches[0], method + "_FINISH_TIEBREAK", len(matches)
            # Prefer same distance nearest numeric distance if possible.
            vdist = parse_num(first(v6_row, ["distance", "distance_m"] ))
            if vdist is not None:
                ranked = sorted(matches, key=lambda m: abs((parse_num(first(m, ["distance", "distance_m"])) or vdist) - vdist))
                return ranked[0], method + "_NEAREST_DISTANCE", len(matches)
            return matches[0], method + "_FIRST_OF_MULTIPLE", len(matches)
    return None, "NO_WEIGHT_MATCH", 0


def main():
    v6_rows = read_csv(V6_SOURCE)
    weight_rows = read_csv(WEIGHT_SOURCE)
    exact, no_distance, horse_only = build_index(weight_rows)

    joined = []
    audit_rows = []
    match_counter = Counter()
    race_groups = defaultdict(list)

    for row in v6_rows:
        match, method, candidates = choose_match(row, exact, no_distance, horse_only)
        match_counter[method] += 1
        rating = parse_num(first(row, ["performance_rating_v6_1_research", "performance_rating_v6", "performance_rating_v5_1", "performance_rating_v3"] ))
        weight = match.get("_weight_kg") if match else None
        date = first(row, ["race_date", "date", "meeting_date"])
        track = first(row, ["track", "venue"])
        horse = first(row, ["horse", "horse_name", "runner_name"])
        distance = parse_num(first(row, ["distance", "distance_m"] ))
        race_key = "|".join([date, norm_track(track), fmt(distance, 0), first(row, ["race_class_clean", "race_class_raw", "race_class_recovered", "race_class"]), first(row, ["condition_recovered", "condition", "track_condition"] )])
        out = {
            "race_date": date,
            "track": track,
            "horse": horse,
            "distance": fmt(distance, 0),
            "race_class_clean": first(row, ["race_class_clean", "race_class_recovered", "race_class_raw", "race_class"]),
            "condition_recovered": first(row, ["condition_recovered", "condition", "track_condition"]),
            "finish_position": first(row, ["finish_position", "finish_pos", "finish_pos_raw"]),
            "margin": first(row, ["margin", "margin_raw"]),
            "performance_rating_v6_1_research": fmt(rating, 2),
            "performance_rating_v6_1_research_reason": first(row, ["performance_rating_v6_1_research_reason"]),
            "carried_weight_kg": fmt(weight, 2),
            "weight_band_research_v1": weight_band(weight),
            "weight_source_file": WEIGHT_SOURCE.name if match else "",
            "weight_source_weight_raw": first(match or {}, ["weight", "wgt", "weight_carried", "allocated_weight"]),
            "weight_source_jockey": first(match or {}, ["jockey", "rider"]),
            "weight_source_trainer": first(match or {}, ["trainer"]),
            "weight_source_barrier": first(match or {}, ["barrier"]),
            "weight_source_sp": first(match or {}, ["sp", "SP"]),
            "join_method": method,
            "join_candidate_count": candidates,
            "research_scope": "WEIGHT_CONTEXT_ONLY_NO_AGE_SEX_NO_WFA_CLAIM",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "_race_key": race_key,
        }
        joined.append(out)
        if weight is not None and rating is not None:
            race_groups[race_key].append(out)

    # Race-relative weight context, after all rows are joined.
    for race_key, rows in race_groups.items():
        weights = [parse_num(r["carried_weight_kg"]) for r in rows if parse_num(r["carried_weight_kg"]) is not None]
        if not weights:
            continue
        avg_weight = mean(weights)
        max_weight = max(weights)
        min_weight = min(weights)
        sorted_weights = sorted(weights, reverse=True)
        for r in rows:
            w = parse_num(r["carried_weight_kg"])
            delta = w - avg_weight if w is not None else None
            r["race_avg_weight_kg"] = fmt(avg_weight, 2)
            r["race_min_weight_kg"] = fmt(min_weight, 2)
            r["race_max_weight_kg"] = fmt(max_weight, 2)
            r["weight_delta_to_race_avg_kg"] = fmt(delta, 2)
            r["weight_relative_band_research_v1"] = relative_band(delta)
            r["weight_rank_in_joined_race"] = sorted_weights.index(w) + 1 if w in sorted_weights else ""

    for r in joined:
        r.pop("_race_key", None)
        r.setdefault("race_avg_weight_kg", "")
        r.setdefault("race_min_weight_kg", "")
        r.setdefault("race_max_weight_kg", "")
        r.setdefault("weight_delta_to_race_avg_kg", "")
        r.setdefault("weight_relative_band_research_v1", "MISSING")
        r.setdefault("weight_rank_in_joined_race", "")

    out_fields = [
        "race_date", "track", "horse", "distance", "race_class_clean", "condition_recovered",
        "finish_position", "margin", "performance_rating_v6_1_research", "performance_rating_v6_1_research_reason",
        "carried_weight_kg", "weight_band_research_v1", "race_avg_weight_kg", "race_min_weight_kg",
        "race_max_weight_kg", "weight_delta_to_race_avg_kg", "weight_relative_band_research_v1",
        "weight_rank_in_joined_race", "weight_source_file", "weight_source_weight_raw", "weight_source_jockey",
        "weight_source_trainer", "weight_source_barrier", "weight_source_sp", "join_method", "join_candidate_count",
        "research_scope", "production_changed", "pricing_changed", "v6_1_changed", "v7_2g2_changed", "built_at",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader(); writer.writerows(joined)

    total = len(joined)
    matched = sum(1 for r in joined if r["carried_weight_kg"])
    rating_rows = sum(1 for r in joined if r["performance_rating_v6_1_research"])
    weight_and_rating = sum(1 for r in joined if r["carried_weight_kg"] and r["performance_rating_v6_1_research"])
    relative_rows = sum(1 for r in joined if r["weight_delta_to_race_avg_kg"])
    audit_rows = [
        {"metric": "v6_1_source", "value": V6_SOURCE.name},
        {"metric": "weight_source", "value": WEIGHT_SOURCE.name},
        {"metric": "v6_1_rows", "value": total},
        {"metric": "weight_source_rows", "value": len(weight_rows)},
        {"metric": "joined_weight_rows", "value": matched},
        {"metric": "weight_join_coverage_pct", "value": fmt((matched / total) * 100 if total else None, 4)},
        {"metric": "v6_1_rating_rows", "value": rating_rows},
        {"metric": "weight_and_rating_rows", "value": weight_and_rating},
        {"metric": "race_relative_weight_rows", "value": relative_rows},
        {"metric": "age_fields_used", "value": "NO"},
        {"metric": "sex_fields_used", "value": "NO"},
        {"metric": "wfa_claim_made", "value": "NO"},
        {"metric": "production_changed", "value": "NO"},
        {"metric": "pricing_changed", "value": "NO"},
        {"metric": "v6_1_changed", "value": "NO"},
        {"metric": "v7_2g2_changed", "value": "NO"},
        {"metric": "status", "value": "EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_BUILT" if matched else "EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_NO_WEIGHT_MATCHES"},
    ]
    with AUDIT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader(); writer.writerows(audit_rows)

    summary_rows = list(audit_rows)
    for method, count in match_counter.most_common():
        summary_rows.append({"metric": f"join_method_{method}", "value": count})
    weight_values = [parse_num(r["carried_weight_kg"]) for r in joined if parse_num(r["carried_weight_kg"]) is not None]
    rating_values = [parse_num(r["performance_rating_v6_1_research"]) for r in joined if parse_num(r["performance_rating_v6_1_research"]) is not None]
    if weight_values:
        summary_rows.extend([
            {"metric": "avg_carried_weight_kg", "value": fmt(mean(weight_values), 4)},
            {"metric": "median_carried_weight_kg", "value": fmt(median(weight_values), 4)},
            {"metric": "min_carried_weight_kg", "value": fmt(min(weight_values), 4)},
            {"metric": "max_carried_weight_kg", "value": fmt(max(weight_values), 4)},
        ])
    if rating_values:
        summary_rows.extend([
            {"metric": "avg_v6_1_rating", "value": fmt(mean(rating_values), 4)},
            {"metric": "median_v6_1_rating", "value": fmt(median(rating_values), 4)},
        ])
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader(); writer.writerows(summary_rows)

    REPORT.write_text("\n".join([
        "EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1",
        f"v6_1_source={V6_SOURCE.name}",
        f"weight_source={WEIGHT_SOURCE.name}",
        f"v6_1_rows={total}",
        f"joined_weight_rows={matched}",
        f"weight_join_coverage_pct={fmt((matched / total) * 100 if total else None, 4)}",
        f"weight_and_rating_rows={weight_and_rating}",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "wfa_claim_made=NO",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "status=" + ("EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_BUILT" if matched else "EDGEIQ_WEIGHT_CONTEXT_RESEARCH_V1_NO_WEIGHT_MATCHES"),
    ]) + "\n", encoding="utf-8")
    print(REPORT)

if __name__ == "__main__":
    main()

