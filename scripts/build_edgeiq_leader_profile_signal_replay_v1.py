import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import build_edgeiq_pace_pressure_signal_replay_v1 as pace

ROOT = pace.ROOT
DATA = pace.DATA
SOURCE_REPLAY = DATA / "edgeiq_pace_pressure_signal_replay_v1.csv"
SOURCE_SUMMARY = DATA / "edgeiq_pace_pressure_signal_replay_v1_summary.csv"
SOURCE_LEAKAGE = DATA / "edgeiq_pace_pressure_signal_replay_v1_leakage_audit.csv"
OUT = DATA / "edgeiq_leader_profile_signal_replay_v1.csv"
SUMMARY = DATA / "edgeiq_leader_profile_signal_replay_v1_summary.csv"
SLICES = DATA / "edgeiq_leader_profile_signal_replay_v1_slices.csv"
LEAKAGE = DATA / "edgeiq_leader_profile_signal_replay_v1_leakage_audit.csv"
REPORT = DATA / "edgeiq_leader_profile_signal_replay_v1_report.txt"

VARIANTS = {
    "CONSERVATIVE": 0.75,
    "STANDARD": 1.25,
    "AGGRESSIVE": 2.00,
}
VALID_CONF = {"MEDIUM", "HIGH"}
ADJ_CAP = 4.0
MIN_RACES = 100
MIN_RUNNERS = 500


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields, seen = [], set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(a, b):
    return round((a / b) * 100, 4) if b else 0.0


def condition_band(value):
    text = pace.clean(value).upper()
    if "HEAVY" in text or text.startswith("H"):
        return "HEAVY"
    if "SOFT" in text or text.startswith("S"):
        return "SOFT"
    if "GOOD" in text or "FIRM" in text or "FAST" in text or "DEAD" in text or text.startswith("G") or text.startswith("F"):
        return "GOOD_FIRM"
    return "UNKNOWN"


def barrier_band(value, field_size):
    b = pace.num(value)
    fs = pace.num(field_size)
    if b is None or fs is None or fs <= 0:
        return "UNKNOWN_BARRIER"
    if b <= max(2, fs / 3):
        return "INSIDE_BARRIER"
    if b > (fs * 2 / 3):
        return "OUTSIDE_BARRIER"
    return "MIDDLE_BARRIER"


def pressure_slice(value):
    if value == "LOW_PRESSURE":
        return "LOW_PRESSURE"
    if value == "MODERATE_PRESSURE":
        return "MEDIUM_PRESSURE"
    if value == "HIGH_PRESSURE":
        return "HIGH_PRESSURE"
    return "UNKNOWN_PRESSURE"


def is_leader_candidate(row):
    return row.get("prior_run_style_band") == "LEADER" and row.get("prior_run_style_confidence") in VALID_CONF


def leader_guard(row, shape):
    if not is_leader_candidate(row):
        return False, "NOT_PRIOR_LEADER_PROFILE"
    if shape.get("race_shape_confidence") not in VALID_CONF:
        return False, "SUPPRESSED_MISSING_RACE_SHAPE_CONFIDENCE"
    if shape.get("unreliable_leader_count") == "YES":
        return False, "SUPPRESSED_UNRELIABLE_LEADER_COUNT"
    leader_count = pace.num(shape.get("leader_count")) or 0
    pressure = shape.get("pace_pressure_band")
    if leader_count > 1 or pressure == "HIGH_PRESSURE":
        return False, "SUPPRESSED_MULTIPLE_LEADERS_OR_HIGH_PRESSURE"
    return True, "LEADER_PROFILE_BOOST_APPLIED"


def leader_adjustment(row, shape, boost):
    ok, reason = leader_guard(row, shape)
    if not ok:
        return 0.0, reason
    raw = boost
    # Small context taper: sprint leaders get full credit, staying leaders slightly less.
    if row.get("distance_band") == "STAYING":
        raw *= 0.80
    capped = max(-ADJ_CAP, min(ADJ_CAP, raw))
    detail = f"{reason}; style=LEADER; style_conf={row.get('prior_run_style_confidence')}; pressure={shape.get('pace_pressure_band')}; leader_count={shape.get('leader_count')}; boost={boost}"
    if capped != raw:
        detail += "; CAP_HIT"
    return capped, detail


def verdict_for(races, runners, top1_delta, top3_delta, original_better, adjusted_better, over_adjustments, leakage_failures):
    if leakage_failures:
        return "LEAKAGE_RISK_BLOCKED"
    if races < MIN_RACES or runners < MIN_RUNNERS:
        return "INSUFFICIENT_SAMPLE"
    over_rate = over_adjustments / races if races else 0
    if top1_delta >= 0.75 and top3_delta >= 0 and adjusted_better > original_better and over_rate <= 0.20:
        return "PROMISING_RESEARCH_SIGNAL"
    if top1_delta <= -0.75 or top3_delta <= -1.0 or adjusted_better < original_better * 0.75:
        return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"

def build_candidate_races():
    replay, meta = pace.build_spine()
    candidate_races = []
    excluded = defaultdict(int)
    for race in replay:
        rows = [dict(r) for r in race["rows"]]
        leaders = [r for r in rows if is_leader_candidate(r)]
        if not leaders:
            excluded["NO_PRIOR_LEADER_CANDIDATE"] += 1
            continue
        shape = race["shape"]
        original_ranked, original_ranks = pace.rank_rows(rows, "prior_rating")
        best_leader = sorted(leaders, key=lambda r: -(pace.num(r.get("prior_rating")) or -999999))[0]
        best_leader_rank = original_ranks.get(best_leader["horse_norm"], "")
        leader_top_rated = "YES" if original_ranked[0]["horse_norm"] == best_leader["horse_norm"] else "NO"
        row0 = rows[0]
        candidate_races.append({
            "race": race,
            "rows": rows,
            "leaders": leaders,
            "best_leader": best_leader,
            "best_leader_original_rank": best_leader_rank,
            "leader_top_rated_already": leader_top_rated,
            "condition_band": condition_band(pace.first(row0, ["condition", "track_condition", "going"])),
            "barrier_band": barrier_band(best_leader.get("barrier"), len(rows)),
            "pressure_slice": pressure_slice(shape.get("pace_pressure_band")),
            "field_size_band": row0.get("field_size_band", "UNKNOWN_FIELD"),
            "distance_band": row0.get("distance_band", "UNKNOWN"),
        })
    meta["candidate_races"] = len(candidate_races)
    meta["candidate_runners"] = sum(len(c["rows"]) for c in candidate_races)
    meta["leader_candidates"] = sum(len(c["leaders"]) for c in candidate_races)
    meta["candidate_excluded"] = dict(excluded)
    return candidate_races, meta


def evaluate_variant(candidate_races, meta, variant, boost):
    out = []
    for item in candidate_races:
        race = item["race"]
        rows = [dict(r) for r in item["rows"]]
        shape = race["shape"]
        boosted_count = 0
        suppressed_count = 0
        for r in rows:
            adj, reason = leader_adjustment(r, shape, boost)
            if adj != 0:
                boosted_count += 1
            elif is_leader_candidate(r):
                suppressed_count += 1
            r["original_prior_rating"] = r["prior_rating"]
            r["leader_profile_adjustment"] = adj
            r["leader_profile_adjustment_reason"] = reason
            r["leader_profile_adjusted_prior_rating"] = (pace.num(r.get("prior_rating")) or 0) + adj
        original_ranked, original_ranks = pace.rank_rows(rows, "original_prior_rating")
        adjusted_ranked, adjusted_ranks = pace.rank_rows(rows, "leader_profile_adjusted_prior_rating")
        original_top = original_ranked[0]
        adjusted_top = adjusted_ranked[0]
        original_top3 = original_ranked[:3]
        adjusted_top3 = adjusted_ranked[:3]
        same_pick = original_top["horse_norm"] == adjusted_top["horse_norm"]
        original_finish = pace.finish_value(original_top)
        adjusted_finish = pace.finish_value(adjusted_top)
        moves = [abs(adjusted_ranks.get(r["horse_norm"], 0) - original_ranks.get(r["horse_norm"], 0)) for r in rows]
        over = sum(1 for r in rows if abs(pace.num(r.get("leader_profile_adjustment")) or 0) >= ADJ_CAP)
        if moves and max(moves) >= 5:
            over += 1
        winner = next((r for r in rows if r["horse_norm"] == race["winner_key"]), {})
        best_leader = item["best_leader"]
        best_leader_norm = best_leader["horse_norm"]
        out.append({
            "variant": variant,
            "race_key": race["race_key"],
            "race_date": race["date"].isoformat(),
            "track": pace.first(original_top, ["track"]),
            "race_no": race["race_no"],
            "eligible_runner_count": len(rows),
            "leader_candidate_count": len(item["leaders"]),
            "boosted_leader_count": boosted_count,
            "suppressed_leader_count": suppressed_count,
            "actual_winner": pace.first(winner, ["horse"]),
            "actual_winner_original_rank": original_ranks.get(race["winner_key"], ""),
            "actual_winner_adjusted_rank": adjusted_ranks.get(race["winner_key"], ""),
            "best_prior_leader": pace.first(best_leader, ["horse"]),
            "best_prior_leader_finish": pace.fmt(pace.finish_value(best_leader), 0),
            "best_prior_leader_original_rank": item["best_leader_original_rank"],
            "best_prior_leader_adjusted_rank": adjusted_ranks.get(best_leader_norm, ""),
            "leader_top_rated_already": item["leader_top_rated_already"],
            "best_prior_leader_barrier": pace.fmt(best_leader.get("barrier"), 0),
            "best_prior_leader_prior_rating": pace.fmt(best_leader.get("prior_rating"), 3),
            "best_prior_leader_prior_rating_date": best_leader.get("prior_rating_date", ""),
            "best_prior_leader_style_confidence": best_leader.get("prior_run_style_confidence", ""),
            "leader_count": shape["leader_count"],
            "on_pace_count": shape["on_pace_count"],
            "midfield_count": shape["midfield_count"],
            "backmarker_count": shape["backmarker_count"],
            "unknown_style_count": shape["unknown_style_count"],
            "known_confident_style_ratio": pace.fmt(shape["known_confident_style_ratio"], 4),
            "pace_pressure_band": shape["pace_pressure_band"],
            "race_shape_confidence": shape["race_shape_confidence"],
            "unreliable_leader_count": shape["unreliable_leader_count"],
            "distance_band": item["distance_band"],
            "field_size_band": item["field_size_band"],
            "condition_band": item["condition_band"],
            "barrier_band": item["barrier_band"],
            "pressure_slice": item["pressure_slice"],
            "original_top_pick": pace.first(original_top, ["horse"]),
            "original_top_pick_finish": pace.fmt(original_finish, 0),
            "original_top_pick_prior_rating": pace.fmt(original_top.get("prior_rating"), 3),
            "original_top_pick_prior_rating_date": original_top.get("prior_rating_date", ""),
            "original_top_pick_style": original_top.get("prior_run_style_band", "UNKNOWN"),
            "adjusted_top_pick": pace.first(adjusted_top, ["horse"]),
            "adjusted_top_pick_finish": pace.fmt(adjusted_finish, 0),
            "adjusted_top_pick_prior_rating": pace.fmt(adjusted_top.get("prior_rating"), 3),
            "adjusted_top_pick_prior_rating_date": adjusted_top.get("prior_rating_date", ""),
            "adjusted_top_pick_style": adjusted_top.get("prior_run_style_band", "UNKNOWN"),
            "adjusted_top_pick_leader_adjustment": pace.fmt(adjusted_top.get("leader_profile_adjustment"), 3),
            "adjusted_top_pick_adjusted_rating": pace.fmt(adjusted_top.get("leader_profile_adjusted_prior_rating"), 3),
            "adjusted_top_pick_adjustment_reason": adjusted_top.get("leader_profile_adjustment_reason", ""),
            "original_top1_win": "YES" if pace.is_winner(original_top) else "NO",
            "adjusted_top1_win": "YES" if pace.is_winner(adjusted_top) else "NO",
            "original_top3_contains_winner": "YES" if any(pace.is_winner(r) for r in original_top3) else "NO",
            "adjusted_top3_contains_winner": "YES" if any(pace.is_winner(r) for r in adjusted_top3) else "NO",
            "same_top_pick": "YES" if same_pick else "NO",
            "original_top_pick_better": "YES" if (not same_pick and original_finish < adjusted_finish) else "NO",
            "adjusted_top_pick_better": "YES" if (not same_pick and adjusted_finish < original_finish) else "NO",
            "both_lost": "YES" if (not pace.is_winner(original_top) and not pace.is_winner(adjusted_top)) else "NO",
            "average_rank_movement": pace.fmt(mean(moves) if moves else 0, 4),
            "max_rank_movement": max(moves) if moves else 0,
            "over_adjustment_flag": "YES" if over else "NO",
            "over_adjustment_count": over,
            "leakage_failure_flag": "YES" if meta["leakage_failures"] else "NO",
            "production_changed": "NO", "pricing_changed": "NO", "v6_1_changed": "NO", "v7_2g2_changed": "NO", "ui_changed": "NO",
            "built_at": datetime.now(timezone.utc).isoformat(),
        })
    return out

def metric_row(rows, variant, slice_name, slice_value, meta):
    races = len(rows)
    runners = sum(int(pace.num(r.get("eligible_runner_count")) or 0) for r in rows)
    leaders = sum(int(pace.num(r.get("leader_candidate_count")) or 0) for r in rows)
    o1 = sum(1 for r in rows if r.get("original_top1_win") == "YES")
    a1 = sum(1 for r in rows if r.get("adjusted_top1_win") == "YES")
    o3 = sum(1 for r in rows if r.get("original_top3_contains_winner") == "YES")
    a3 = sum(1 for r in rows if r.get("adjusted_top3_contains_winner") == "YES")
    same = sum(1 for r in rows if r.get("same_top_pick") == "YES")
    ob = sum(1 for r in rows if r.get("original_top_pick_better") == "YES")
    ab = sum(1 for r in rows if r.get("adjusted_top_pick_better") == "YES")
    both = sum(1 for r in rows if r.get("both_lost") == "YES")
    over = sum(1 for r in rows if r.get("over_adjustment_flag") == "YES")
    moves = [pace.num(r.get("average_rank_movement")) or 0 for r in rows]
    max_move = max([int(pace.num(r.get("max_rank_movement")) or 0) for r in rows] or [0])
    o1p, a1p = pct(o1, races), pct(a1, races)
    o3p, a3p = pct(o3, races), pct(a3, races)
    top1_delta = round(a1p - o1p, 4)
    top3_delta = round(a3p - o3p, 4)
    verdict = verdict_for(races, runners, top1_delta, top3_delta, ob, ab, over, meta["leakage_failures"])
    return {
        "variant": variant, "slice_name": slice_name, "slice_value": slice_value,
        "races_tested": races, "runners_tested": runners, "leader_candidates": leaders,
        "original_top1_win_pct": o1p, "adjusted_top1_win_pct": a1p, "top1_delta_pct": top1_delta,
        "original_top3_win_pct": o3p, "adjusted_top3_win_pct": a3p, "top3_delta_pct": top3_delta,
        "same_top_pick_pct": pct(same, races), "original_better_count": ob, "adjusted_better_count": ab,
        "both_lost_count": both, "over_adjustment_count": over,
        "average_rank_movement": round(mean(moves), 4) if moves else 0, "max_rank_movement": max_move,
        "leakage_failures": meta["leakage_failures"], "bad_prior_dates": meta["bad_prior_rating_dates"] + meta["bad_prior_style_dates"],
        "verdict": verdict, "production_changed": "NO", "pricing_changed": "NO", "v6_1_changed": "NO", "v7_2g2_changed": "NO", "ui_changed": "NO",
    }


def build_metrics(rows, meta):
    summary = []
    slices = []
    by_variant = defaultdict(list)
    for r in rows:
        by_variant[r["variant"]].append(r)
    specs = [
        ("DISTANCE", "distance_band", ["SPRINT", "MILE", "MIDDLE", "STAYING", "UNKNOWN"]),
        ("FIELD_SIZE", "field_size_band", ["SMALL_FIELD", "MID_FIELD", "LARGE_FIELD", "UNKNOWN_FIELD"]),
        ("PRESSURE", "pressure_slice", ["LOW_PRESSURE", "MEDIUM_PRESSURE", "HIGH_PRESSURE", "UNKNOWN_PRESSURE"]),
        ("CONDITION", "condition_band", ["GOOD_FIRM", "SOFT", "HEAVY", "UNKNOWN"]),
        ("BARRIER", "barrier_band", ["INSIDE_BARRIER", "MIDDLE_BARRIER", "OUTSIDE_BARRIER", "UNKNOWN_BARRIER"]),
        ("LEADER_TOP_RATED", "leader_top_rated_already", ["YES", "NO"]),
    ]
    for variant, vrows in by_variant.items():
        summary.append(metric_row(vrows, variant, "OVERALL", "OVERALL", meta))
        for sname, col, vals in specs:
            for val in vals:
                subset = [r for r in vrows if r.get(col) == val]
                if subset:
                    slices.append(metric_row(subset, variant, sname, val, meta))
    return summary, slices


def source_leakage_passed():
    if not SOURCE_LEAKAGE.exists():
        return False, "source leakage audit missing"
    rows = read_csv(SOURCE_LEAKAGE)
    failing = [r for r in rows if r.get("status") != "PASS"]
    if failing:
        return False, f"source leakage audit failures={len(failing)}"
    return True, "source leakage audit all PASS"


def build_leakage(meta, source_pass, source_detail):
    rows = []
    rows.append({"audit_item":"SOURCE_PACE_PRESSURE_REPLAY_LEAKAGE_AUDIT", "source_file":str(SOURCE_LEAKAGE.relative_to(ROOT)).replace("\\","/"), "status":"PASS" if source_pass else "FAIL", "details":source_detail})
    rows.append({"audit_item":"PRIOR_RATING_DATE_GUARD", "source_file":str(pace.V6.relative_to(ROOT)).replace("\\","/"), "status":"PASS" if meta["bad_prior_rating_dates"] == 0 else "FAIL", "details":f"bad_prior_rating_dates={meta['bad_prior_rating_dates']}"})
    rows.append({"audit_item":"PRIOR_RUN_STYLE_DATE_GUARD", "source_file":str(pace.RUN_STYLE.relative_to(ROOT)).replace("\\","/"), "status":"PASS" if meta["bad_prior_style_dates"] == 0 else "FAIL", "details":f"bad_prior_style_dates={meta['bad_prior_style_dates']}; same-race run style excluded by strict prior date"})
    rows.append({"audit_item":"POST_RACE_FEATURE_EXCLUSION", "source_file":"edgeiq_pace_pressure_engine_v1.csv|edgeiq_historical_race_shape_archive_v1.csv", "status":"PASS", "details":"Direct same-race pace/replay/archive files not used as features because they contain outcomes or in-running/result-derived columns."})
    rows.append({"audit_item":"OVERALL_LEAKAGE_FAILURES", "source_file":"ALL_USED_SOURCES", "status":"PASS" if meta["leakage_failures"] == 0 and source_pass else "FAIL", "details":f"leakage_failures={meta['leakage_failures']} source_pass={source_pass}"})
    return rows


def write_report(summary, slices, meta, source_pass, source_detail):
    best = max(summary, key=lambda r: (float(r["top1_delta_pct"]), float(r["top3_delta_pct"]))) if summary else {}
    promising = [r for r in slices if r["verdict"] == "PROMISING_RESEARCH_SIGNAL"]
    lines = [
        "EDGEIQ_LEADER_PROFILE_SIGNAL_REPLAY_V1",
        f"built_at={datetime.now(timezone.utc).isoformat()}",
        f"source_replay={SOURCE_REPLAY.name}", f"source_summary={SOURCE_SUMMARY.name}", f"source_leakage_audit={SOURCE_LEAKAGE.name}",
        f"source_leakage_status={'PASS' if source_pass else 'FAIL'}", f"source_leakage_detail={source_detail}",
        f"candidate_races={meta['candidate_races']}", f"candidate_runners={meta['candidate_runners']}", f"leader_candidates={meta['leader_candidates']}",
        f"base_replay_races={meta['replay_races']}", f"base_replay_runners={meta['replay_runners']}",
        "prior_rating_rule=latest V6.1 rating strictly before target race date",
        "prior_run_style_rule=latest historical run-style row strictly before target race date",
        "leader_boost_guard=only prior LEADER with MEDIUM/HIGH confidence; no boost for multiple leaders/high pressure/unreliable leader count/missing shape confidence",
        f"leakage_failures={meta['leakage_failures']}", f"bad_prior_dates={meta['bad_prior_rating_dates'] + meta['bad_prior_style_dates']}",
        "production_changed=NO", "pricing_changed=NO", "v6_1_changed=NO", "v7_2g2_changed=NO", "ui_changed=NO", "", "OVERALL_VARIANT_RESULTS",
    ]
    for r in summary:
        lines.append(f"{r['variant']}: races={r['races_tested']} runners={r['runners_tested']} leaders={r['leader_candidates']} original_top1={r['original_top1_win_pct']} adjusted_top1={r['adjusted_top1_win_pct']} top1_delta={r['top1_delta_pct']} original_top3={r['original_top3_win_pct']} adjusted_top3={r['adjusted_top3_win_pct']} top3_delta={r['top3_delta_pct']} same_top_pick={r['same_top_pick_pct']} original_better={r['original_better_count']} adjusted_better={r['adjusted_better_count']} avg_rank_move={r['average_rank_movement']} max_rank_move={r['max_rank_movement']} over_adjustments={r['over_adjustment_count']} verdict={r['verdict']}")
    if best:
        lines += ["", f"best_variant_by_top1_delta={best['variant']}", f"best_variant_verdict={best['verdict']}"]
    lines += ["", "PROMISING_SLICES"]
    if promising:
        for r in promising[:30]:
            lines.append(f"{r['variant']} {r['slice_name']}={r['slice_value']} races={r['races_tested']} leaders={r['leader_candidates']} top1_delta={r['top1_delta_pct']} top3_delta={r['top3_delta_pct']} verdict={r['verdict']}")
    else:
        lines.append("NONE")
    if meta.get("candidate_excluded"):
        lines += ["", "CANDIDATE_EXCLUSIONS"]
        for k, v in sorted(meta["candidate_excluded"].items()):
            lines.append(f"{k}={v}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    source_pass, source_detail = source_leakage_passed()
    candidate_races, meta = build_candidate_races()
    if not source_pass:
        meta["leakage_failures"] = meta.get("leakage_failures", 0) + 1
    rows = []
    for variant, boost in VARIANTS.items():
        rows.extend(evaluate_variant(candidate_races, meta, variant, boost))
    write_csv(OUT, rows)
    summary, slices = build_metrics(rows, meta)
    write_csv(SUMMARY, summary)
    write_csv(SLICES, slices)
    leakage = build_leakage(meta, source_pass, source_detail)
    write_csv(LEAKAGE, leakage)
    write_report(summary, slices, meta, source_pass, source_detail)
    print(OUT); print(SUMMARY); print(SLICES); print(LEAKAGE); print(REPORT)

if __name__ == "__main__":
    main()
