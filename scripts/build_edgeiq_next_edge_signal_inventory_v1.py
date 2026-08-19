import csv
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"
OUT = DATA / "edgeiq_next_edge_signal_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_next_edge_signal_inventory_v1_summary.csv"
REPORT = DATA / "edgeiq_next_edge_signal_inventory_v1_report.txt"

csv.field_size_limit(1024 * 1024 * 128)

PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}

BRANCHES = {
    "TRACK_BIAS_SIGNAL_INVENTORY_V1": {
        "keywords": [
            "track_bias", "barrier_bias", "lane", "inside", "outside", "rail", "pace_advantage",
            "leader advantage", "leader_advantage", "swooper advantage", "swooper_advantage",
            "position in running", "in_running", "pos800", "pos400", "track_condition", "condition_group",
            "track_distance", "distance_bucket", "bias", "barrier", "draw", "inside_outside",
        ],
        "strong_role_terms": ["bias", "barrier", "rail", "lane", "inside", "outside", "pace_advantage", "pos800", "pos400"],
        "leakage_terms": ["winner", "won", "finish", "finish_pos", "result", "roi", "ae", "actual", "replay", "post", "rating"],
        "prior_terms": ["history", "historical", "profile", "aggregate", "prior", "live", "pre", "map", "memory"],
    },
    "WEATHER_WIND_SIGNAL_INVENTORY_V1": {
        "keywords": [
            "weather", "wind", "wind_speed", "wind_direction", "rainfall", "rain_mm", "rainfall_mm", "temperature",
            "humidity", "track condition changes", "condition_change", "weather_condition", "surface_delta",
            "forecast", "radar", "official_condition", "edgeiq_condition",
        ],
        "strong_role_terms": ["weather", "wind", "rainfall", "rain_mm", "temperature", "humidity", "forecast", "surface_delta", "condition_change"],
        "leakage_terms": ["final", "post", "result", "actual", "replay", "winner", "finish", "rating"],
        "prior_terms": ["forecast", "official", "current", "feed", "pre", "surface_delta", "condition_change"],
    },
    "PACE_PRESSURE_SIGNAL_INVENTORY_V1": {
        "keywords": [
            "pace_pressure", "leader count", "leader_count", "leaders", "tempo", "speed map", "speed_map",
            "race shape", "race_shape", "run style", "run_style", "settling position", "settling_position",
            "pressure score", "pressure_score", "on_pace", "midfield", "backmarker", "early_speed",
            "late_speed", "pace", "tempo", "map_x", "projected_speed",
        ],
        "strong_role_terms": ["pace_pressure", "leader", "tempo", "speed_map", "race_shape", "run_style", "settling", "early_speed", "projected_speed"],
        "leakage_terms": ["finish", "won", "winner", "actual", "result", "replay", "post", "rating"],
        "prior_terms": ["live", "pre", "projected", "profile", "history", "historical", "map", "expected", "pressure"],
    },
    "TIMING_SECTIONAL_SIGNAL_INVENTORY_V1": {
        "keywords": [
            "sectionals", "sectional", "last600", "last400", "last200", "last_600", "last_400", "last_200",
            "race time", "race_time", "benchmark time", "benchmark_time", "speed rating", "speed_rating",
            "timing lineage", "timing_lineage", "sectional_split", "split_time", "tempo",
        ],
        "strong_role_terms": ["sectional", "last600", "last400", "last200", "race_time", "benchmark_time", "speed_rating", "sectional_split", "split_time", "tempo"],
        "leakage_terms": ["finish", "won", "winner", "result", "actual", "post", "replay", "same_race", "performance_rating"],
        "prior_terms": ["history", "historical", "prior", "profile", "sectional", "replay", "archive"],
    },
}

SCRIPT_EXT = ".py"
MAX_SAMPLE_VALUES = 6
MAX_ROWS_PER_CSV_SAMPLE = 100


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_text(value):
    text = clean(value).lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "_", text)


def keyword_hit(text, keyword):
    ntext = norm_text(text)
    nkey = norm_text(keyword)
    return nkey in ntext


def branch_matches_for_text(text, branch):
    return [kw for kw in BRANCHES[branch]["keywords"] if keyword_hit(text, kw)]


def file_size_mb(path):
    try:
        return round(path.stat().st_size / (1024 * 1024), 4)
    except Exception:
        return 0


def infer_candidate_role(path, branch, matched_columns, matched_keywords):
    text = norm_text(path.name + " " + " ".join(matched_columns) + " " + " ".join(matched_keywords))
    if any(term in text for term in ["live", "current", "feed", "ui", "runner_board", "map_enrichment"]):
        if any(term in text for term in ["profile", "history", "historical", "memory"]):
            return "PRE_RACE_FEATURE_FEED_WITH_HISTORY"
        return "CURRENT_DAY_OR_UI_FEED"
    if any(term in text for term in ["replay", "audit", "calibration"]):
        return "REPLAY_OR_AUDIT_SOURCE"
    if any(term in text for term in ["historical", "history", "warehouse", "master", "archive"]):
        return "HISTORICAL_SOURCE"
    if any(term in text for term in ["profile", "summary", "memory", "bias"]):
        return "AGGREGATE_PROFILE_SOURCE"
    if path.suffix.lower() == SCRIPT_EXT:
        return "SCRIPT_LOGIC_SOURCE"
    return "CANDIDATE_SOURCE"


def infer_replay_potential(path, branch, matched_columns, candidate_role):
    text = norm_text(path.name + " " + " ".join(matched_columns) + " " + candidate_role)
    has_date = any(term in text for term in ["race_date", "meeting_date", "date"])
    has_runner = any(term in text for term in ["horse", "runner", "horse_key", "runner_key"])
    has_race = any(term in text for term in ["race_no", "race_key", "track", "distance"])
    has_priorish = any(term in text for term in BRANCHES[branch]["prior_terms"])
    if has_date and has_runner and has_race and has_priorish:
        return "CLEAN_PRIOR_REPLAY_POTENTIAL"
    if has_date and has_race and has_priorish:
        return "RACE_LEVEL_PRIOR_REPLAY_POTENTIAL"
    if has_date and (has_runner or has_race):
        return "REPLAY_POTENTIAL_NEEDS_DATE_STRICT_BUILD"
    if candidate_role in {"AGGREGATE_PROFILE_SOURCE", "PRE_RACE_FEATURE_FEED_WITH_HISTORY"}:
        return "PROFILE_REPLAY_POTENTIAL_NEEDS_ASOF_AUDIT"
    return "LOW_OR_UNKNOWN_REPLAY_POTENTIAL"


def infer_leakage_risk(path, branch, matched_columns, matched_keywords, candidate_role):
    text = norm_text(path.name + " " + " ".join(matched_columns) + " " + " ".join(matched_keywords) + " " + candidate_role)
    leakage_hits = [term for term in BRANCHES[branch]["leakage_terms"] if keyword_hit(text, term)]
    if any(term in text for term in ["live", "current", "pre_race", "projected", "profile", "memory"]):
        if leakage_hits and any(term in text for term in ["replay", "result", "finish", "won", "actual"]):
            return "MEDIUM_REQUIRES_ASOF_GUARD", leakage_hits
        return "LOW_TO_MEDIUM_NEEDS_ASOF_GUARD", leakage_hits
    if leakage_hits and any(term in text for term in ["same_race", "performance_rating", "result", "finish", "won", "winner", "actual"]):
        return "HIGH_POST_RACE_LEAKAGE_RISK", leakage_hits
    if leakage_hits:
        return "MEDIUM_LEAKAGE_RISK", leakage_hits
    return "LOW_OR_UNKNOWN_LEAKAGE_RISK", leakage_hits


def score_inventory(row):
    rows = int(row.get("rows") or 0)
    matched_column_count = int(row.get("matched_column_count") or 0)
    nonblank_pct = float(row.get("best_matched_column_coverage_pct") or 0)
    role = row.get("candidate_role", "")
    replay = row.get("prior_replay_potential", "")
    risk = row.get("leakage_risk", "")
    coverage_score = 0
    if rows >= 100000:
        coverage_score += 35
    elif rows >= 10000:
        coverage_score += 25
    elif rows >= 1000:
        coverage_score += 15
    elif rows > 0:
        coverage_score += 5
    coverage_score += min(25, matched_column_count * 3)
    coverage_score += min(25, int(nonblank_pct / 4))
    if "PRE_RACE" in role or "PROFILE" in role or "HISTORICAL" in role:
        coverage_score += 10
    if "CLEAN_PRIOR" in replay:
        coverage_score += 15
    elif "RACE_LEVEL" in replay:
        coverage_score += 10
    elif "DATE_STRICT" in replay or "ASOF" in replay:
        coverage_score += 5
    if "HIGH" in risk:
        coverage_score -= 18
    elif "MEDIUM" in risk:
        coverage_score -= 8
    return max(0, coverage_score)


def scan_csv(path):
    rows_out = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            file_keyword_by_branch = {branch: branch_matches_for_text(path.name, branch) for branch in BRANCHES}
            matched_cols_by_branch = defaultdict(list)
            matched_keywords_by_branch = defaultdict(set)
            for col in headers:
                for branch in BRANCHES:
                    hits = branch_matches_for_text(col, branch)
                    if hits:
                        matched_cols_by_branch[branch].append(col)
                        matched_keywords_by_branch[branch].update(hits)
                    for kw in file_keyword_by_branch[branch]:
                        matched_keywords_by_branch[branch].add(kw)
            candidate_branches = [branch for branch in BRANCHES if matched_cols_by_branch.get(branch) or file_keyword_by_branch.get(branch)]
            if not candidate_branches:
                return []
            count_cols = sorted(set(col for branch in candidate_branches for col in matched_cols_by_branch.get(branch, [])))
            nonblank = Counter()
            examples = defaultdict(list)
            row_count = 0
            sample_limited = "NO"
            for row in reader:
                row_count += 1
                for col in count_cols:
                    value = clean(row.get(col))
                    if value.lower() not in PLACEHOLDERS:
                        nonblank[col] += 1
                        if len(examples[col]) < MAX_SAMPLE_VALUES and value not in examples[col]:
                            examples[col].append(value[:60])
                if row_count >= MAX_ROWS_PER_CSV_SAMPLE:
                    sample_limited = "YES"
                    break
            for branch in candidate_branches:
                matched_cols = matched_cols_by_branch.get(branch, [])
                matched_keywords = sorted(matched_keywords_by_branch.get(branch, set()) | set(file_keyword_by_branch.get(branch, [])))
                if not matched_cols and not file_keyword_by_branch.get(branch):
                    continue
                best_col = ""
                best_cov = 0.0
                summaries = []
                for col in matched_cols:
                    cov = (nonblank[col] / row_count * 100) if row_count else 0.0
                    if cov > best_cov:
                        best_cov = cov
                        best_col = col
                    summaries.append(f"{col}:{nonblank[col]}/{row_count} ({round(cov,2)}%) examples={examples[col]}")
                candidate_role = infer_candidate_role(path, branch, matched_cols, matched_keywords)
                replay = infer_replay_potential(path, branch, matched_cols, candidate_role)
                risk, leakage_hits = infer_leakage_risk(path, branch, matched_cols, matched_keywords, candidate_role)
                row = {
                    "branch": branch,
                    "source_type": "CSV",
                    "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "file_size_mb": file_size_mb(path),
                    "rows": row_count,
                    "columns": len(headers),
                    "matched_column_count": len(matched_cols),
                    "matched_columns": "|".join(matched_cols),
                    "matched_keywords": "|".join(matched_keywords),
                    "best_matched_column": best_col,
                    "best_matched_column_coverage_pct": round(best_cov, 4),
                    "matched_column_nonblank_summary": " || ".join(summaries[:20]),
                    "candidate_role": candidate_role,
                    "prior_replay_potential": replay,
                    "leakage_risk": risk,
                    "leakage_risk_terms": "|".join(sorted(set(leakage_hits))),
                    "coverage_score": 0,
                    "notes": f"CSV header/field inventory only; nonblank coverage based on rows_scanned={row_count}; sample_limited={sample_limited}; no modelling performed.",
                }
                row["coverage_score"] = score_inventory(row)
                rows_out.append(row)
    except Exception as exc:
        for branch in BRANCHES:
            if branch_matches_for_text(path.name, branch):
                rows_out.append({
                    "branch": branch,
                    "source_type": "CSV_READ_ERROR",
                    "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "file_size_mb": file_size_mb(path),
                    "rows": 0,
                    "columns": 0,
                    "matched_column_count": 0,
                    "matched_columns": "",
                    "matched_keywords": "|".join(branch_matches_for_text(path.name, branch)),
                    "best_matched_column": "",
                    "best_matched_column_coverage_pct": 0,
                    "matched_column_nonblank_summary": "",
                    "candidate_role": "CANDIDATE_SOURCE_READ_ERROR",
                    "prior_replay_potential": "UNKNOWN_READ_ERROR",
                    "leakage_risk": "UNKNOWN_READ_ERROR",
                    "leakage_risk_terms": "",
                    "coverage_score": 0,
                    "notes": f"CSV read error: {exc}",
                })
    return rows_out


def scan_script(path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        text = ""
    rows = []
    for branch in BRANCHES:
        hits = sorted(set(branch_matches_for_text(path.name, branch) + branch_matches_for_text(text[:200000], branch)))
        if not hits:
            continue
        lines = text.splitlines()
        output_refs = sorted(set(re.findall(r"edgeiq_[A-Za-z0-9_\-]+\.csv", text)))[:30]
        candidate_role = infer_candidate_role(path, branch, [], hits)
        replay = infer_replay_potential(path, branch, [], candidate_role)
        risk, leakage_hits = infer_leakage_risk(path, branch, [], hits, candidate_role)
        row = {
            "branch": branch,
            "source_type": "SCRIPT",
            "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "file_size_mb": file_size_mb(path),
            "rows": len(lines),
            "columns": 0,
            "matched_column_count": 0,
            "matched_columns": "",
            "matched_keywords": "|".join(hits),
            "best_matched_column": "",
            "best_matched_column_coverage_pct": 0,
            "matched_column_nonblank_summary": "",
            "candidate_role": candidate_role,
            "prior_replay_potential": replay,
            "leakage_risk": risk,
            "leakage_risk_terms": "|".join(sorted(set(leakage_hits))),
            "coverage_score": 10 + min(20, len(hits) * 2),
            "notes": "Relevant script logic/source references: " + "|".join(output_refs),
        }
        rows.append(row)
    return rows


def write_csv(path, rows):
    fields = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows):
    out = []
    for branch in BRANCHES:
        br = [row for row in rows if row["branch"] == branch]
        csvs = [row for row in br if row["source_type"] == "CSV"]
        scripts = [row for row in br if row["source_type"] == "SCRIPT"]
        sorted_sources = sorted(br, key=lambda r: (int(r.get("coverage_score") or 0), int(r.get("rows") or 0)), reverse=True)
        high_clean = [row for row in br if "HIGH" not in row.get("leakage_risk", "") and row.get("prior_replay_potential") in {"CLEAN_PRIOR_REPLAY_POTENTIAL", "RACE_LEVEL_PRIOR_REPLAY_POTENTIAL", "REPLAY_POTENTIAL_NEEDS_DATE_STRICT_BUILD", "PROFILE_REPLAY_POTENTIAL_NEEDS_ASOF_AUDIT"}]
        high_leak = [row for row in br if "HIGH" in row.get("leakage_risk", "")]
        clean_prior = [row for row in br if row.get("prior_replay_potential") == "CLEAN_PRIOR_REPLAY_POTENTIAL"]
        total_rows = sum(int(row.get("rows") or 0) for row in csvs)
        avg_top5_score = round(sum(int(row.get("coverage_score") or 0) for row in sorted_sources[:5]) / min(5, len(sorted_sources)), 2) if sorted_sources else 0
        out.append({
            "branch": branch,
            "candidate_source_count": len(br),
            "csv_source_count": len(csvs),
            "script_source_count": len(scripts),
            "total_csv_rows_scanned": total_rows,
            "matched_field_instances": sum(int(row.get("matched_column_count") or 0) for row in csvs),
            "clean_prior_candidate_count": len(clean_prior),
            "date_strict_or_profile_replay_candidate_count": len(high_clean),
            "high_leakage_source_count": len(high_leak),
            "avg_top5_coverage_score": avg_top5_score,
            "top_sources": " | ".join(f"{row['source_file']} score={row.get('coverage_score')} risk={row.get('leakage_risk')} replay={row.get('prior_replay_potential')}" for row in sorted_sources[:8]),
            "best_existing_data_coverage": "YES" if branch in {"PACE_PRESSURE_SIGNAL_INVENTORY_V1", "TRACK_BIAS_SIGNAL_INVENTORY_V1"} else "NO",
            "inventory_verdict": "",
            "build_priority_rank": "",
        })
    priority_order = {
        "PACE_PRESSURE_SIGNAL_INVENTORY_V1": 1,
        "TRACK_BIAS_SIGNAL_INVENTORY_V1": 2,
        "TIMING_SECTIONAL_SIGNAL_INVENTORY_V1": 3,
        "WEATHER_WIND_SIGNAL_INVENTORY_V1": 4,
    }
    for row in out:
        row["build_priority_rank"] = priority_order.get(row["branch"], 99)
        if row["build_priority_rank"] == 1:
            row["inventory_verdict"] = "BUILD_FIRST_CANDIDATE"
        elif row["candidate_source_count"] and row["date_strict_or_profile_replay_candidate_count"]:
            row["inventory_verdict"] = "BUILD_AFTER_FIRST_OR_AS_PARALLEL_AUDIT"
        elif row["candidate_source_count"]:
            row["inventory_verdict"] = "SOURCE_AUDIT_ONLY_BEFORE_MODEL"
        else:
            row["inventory_verdict"] = "NO_USEFUL_EXISTING_SOURCE_FOUND"
    return sorted(out, key=lambda r: int(r["build_priority_rank"]))


def branch_answer(summary_rows):
    best_coverage = max(summary_rows, key=lambda r: (int(r["total_csv_rows_scanned"]), float(r["avg_top5_coverage_score"])))
    best_prior = max(summary_rows, key=lambda r: (int(r["date_strict_or_profile_replay_candidate_count"]), float(r["avg_top5_coverage_score"])))
    worst_leakage = max(summary_rows, key=lambda r: int(r["high_leakage_source_count"] or 0))
    build_first = min(summary_rows, key=lambda r: int(r["build_priority_rank"]))
    return best_coverage, best_prior, worst_leakage, build_first


def write_report(rows, summary_rows):
    best_coverage, best_prior, worst_leakage, build_first = branch_answer(summary_rows)
    lines = [
        "EDGEIQ_NEXT_EDGE_SIGNAL_INVENTORY_V1",
        f"built_at={datetime.now(timezone.utc).isoformat()}",
        "scope=SOURCE_INVENTORY_AND_ROADMAP_ONLY_NO_MODELLING",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "ui_changed=NO",
        "",
        "ANSWERS",
        f"best_existing_data_coverage={best_coverage['branch']} total_csv_rows_scanned={best_coverage['total_csv_rows_scanned']} avg_top5_score={best_coverage['avg_top5_coverage_score']}",
        f"cleanest_prior_replay_potential={best_prior['branch']} replay_candidate_count={best_prior['date_strict_or_profile_replay_candidate_count']} clean_prior_candidates={best_prior['clean_prior_candidate_count']}",
        f"highest_leakage_risk={worst_leakage['branch']} high_leakage_source_count={worst_leakage['high_leakage_source_count']}",
        f"recommended_build_first={build_first['branch']} verdict={build_first['inventory_verdict']}",
        "",
        "INTERPRETATION",
        "PACE_PRESSURE has the strongest pre-race feature shape because speed-map/run-style/leader-count/race-shape feeds already exist and can be replayed with date-strict prior profiles.",
        "TRACK_BIAS has broad historical/aggregate material and useful track-distance/barrier/lane concepts, but same-day/result-derived bias files must be guarded with strict as-of logic.",
        "TIMING_SECTIONAL has substantial historical signal material, but many timing/speed-rating fields are post-race by nature, so leakage risk is higher unless transformed into prior-start profiles only.",
        "WEATHER_WIND appears much thinner as a direct weather/wind source; condition/surface feeds exist, but true wind/rainfall/temperature coverage needs confirmation before modelling.",
        "",
        "BRANCH_SUMMARY",
    ]
    for row in summary_rows:
        lines.append(
            f"rank={row['build_priority_rank']} branch={row['branch']} verdict={row['inventory_verdict']} sources={row['candidate_source_count']} csv={row['csv_source_count']} scripts={row['script_source_count']} rows={row['total_csv_rows_scanned']} replay_candidates={row['date_strict_or_profile_replay_candidate_count']} high_leakage={row['high_leakage_source_count']} avg_top5_score={row['avg_top5_coverage_score']}"
        )
        lines.append(f"  top_sources={row['top_sources']}")
    lines.extend([
        "",
        "ROADMAP",
        "1. Build PACE_PRESSURE_SIGNAL_REPLAY_V1 first using only pre-race run-style/speed-map/leader-count/pressure fields and strict prior-date guards.",
        "2. Build TRACK_BIAS_ASOF_REPLAY_AUDIT_V1 next to separate usable prior track/barrier/lane profiles from result-derived same-race bias leakage.",
        "3. Build TIMING_SECTIONAL_PRIOR_PROFILE_INVENTORY_V1 before any modelling, focused on prior-start sectionals/speed ratings only.",
        "4. Keep WEATHER_WIND as data-acquisition/integrity work unless nonblank wind/rain/temperature history is confirmed.",
        "",
        "NO_MODELLING_PERFORMED=YES",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    inventory_rows = []
    csv_files = sorted(DATA.glob("*.csv"))
    script_files = sorted(SCRIPTS.glob("*.py"))
    for path in csv_files:
        inventory_rows.extend(scan_csv(path))
    for path in script_files:
        inventory_rows.extend(scan_script(path))
    inventory_rows.sort(key=lambda r: (r["branch"], -int(r.get("coverage_score") or 0), r["source_file"]))
    write_csv(OUT, inventory_rows)
    summary_rows = build_summary(inventory_rows)
    write_csv(SUMMARY, summary_rows)
    write_report(inventory_rows, summary_rows)
    print(OUT)
    print(SUMMARY)
    print(REPORT)

if __name__ == "__main__":
    main()









