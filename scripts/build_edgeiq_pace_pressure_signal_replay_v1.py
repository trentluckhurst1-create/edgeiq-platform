import bisect, csv, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
RESULTS = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
V6 = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
OUT = DATA / "edgeiq_pace_pressure_signal_replay_v1.csv"
SUMMARY = DATA / "edgeiq_pace_pressure_signal_replay_v1_summary.csv"
LEAKAGE = DATA / "edgeiq_pace_pressure_signal_replay_v1_leakage_audit.csv"
REPORT = DATA / "edgeiq_pace_pressure_signal_replay_v1_report.txt"

PLACEHOLDERS = {"", "-", "--", "---", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}
RATING_COLS = ["performance_rating_v6_1_research", "performance_rating_v6_1", "performance_rating", "rating"]
VARIANTS = {"CONSERVATIVE": 0.75, "STANDARD": 1.00, "AGGRESSIVE": 1.50}
MIN_RUNNERS = 3
MIN_KNOWN_STYLE_RATIO = 0.60
VALID_CONF = {"MEDIUM", "HIGH"}
ADJ_CAP = 4.0
csv.field_size_limit(1024 * 1024 * 128)

def clean(v):
    return "" if v is None else str(v).strip()

def first(row, cols):
    for c in cols:
        v = clean(row.get(c, ""))
        if v.lower() not in PLACEHOLDERS:
            return v
    return ""

def num(v):
    t = clean(v).replace("$", "").replace(",", "")
    if t.lower() in PLACEHOLDERS:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

def parse_date(v):
    t = clean(v).replace(".", "")
    if not t:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d%b%y", "%d%b%Y", "%d %b %y", "%d %b %Y"]:
        try:
            return datetime.strptime(t[:11], fmt).date()
        except Exception:
            pass
    return None

def norm_horse(v):
    t = clean(v).upper().replace("`", "'").replace("’", "'").replace("â€™", "'")
    t = re.sub(r"\([^)]*\)", "", t)
    return re.sub(r"[^A-Z0-9]+", "", t)

def norm_track(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())

def fmt(v, places=4):
    if v is None or v == "":
        return ""
    try:
        if places == 0:
            return str(int(round(float(v))))
        return str(round(float(v), places))
    except Exception:
        return clean(v)

def pct(a, b):
    return round((a / b) * 100, 4) if b else 0.0

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    fields, seen = [], set()
    for r in rows:
        for k in r:
            if k not in seen:
                fields.append(k); seen.add(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def style_band(v):
    t = clean(v).upper().replace("-", "_").replace(" ", "_")
    if not t or t.lower() in PLACEHOLDERS:
        return "UNKNOWN"
    if "LEADER" in t or t in {"FRONT", "FRONT_RUNNER", "FRONTRUNNER", "SPEED"}:
        return "LEADER"
    if "ON_PACE" in t or "ONPACE" in t or "HANDY" in t or "PROMINENT" in t:
        return "ON_PACE"
    if "MID" in t or "SETTLE" in t:
        return "MIDFIELD"
    if "BACK" in t or "CLOSER" in t or "OFF_PACE" in t:
        return "BACKMARKER"
    return "UNKNOWN"

def conf_band(v):
    t = clean(v).upper()
    if "HIGH" in t: return "HIGH"
    if "MED" in t or t == "M": return "MEDIUM"
    if "LOW" in t: return "LOW"
    return "MISSING"

def dist_band(v):
    d = num(v)
    if d is None: return "UNKNOWN"
    if d <= 1200: return "SPRINT"
    if d <= 1600: return "MILE"
    if d <= 2000: return "MIDDLE"
    return "STAYING"

def field_band(n):
    if n <= 7: return "SMALL_FIELD"
    if n >= 12: return "LARGE_FIELD"
    return "MID_FIELD"

def rating_value(row):
    for c in RATING_COLS:
        x = num(row.get(c))
        if x is not None:
            return x, c
    return None, ""

def build_rating_history():
    rows = read_csv(V6)
    hist = defaultdict(list); col_counts = defaultdict(int); skipped = 0
    for r in rows:
        h = norm_horse(first(r, ["horse", "horse_name", "runner", "runner_name", "horse_key"]))
        d = parse_date(first(r, ["race_date", "date", "meeting_date"]))
        rating, col = rating_value(r)
        if not h or d is None or rating is None:
            skipped += 1; continue
        hist[h].append((d, rating)); col_counts[col] += 1
    for h in hist:
        hist[h].sort(key=lambda x: x[0])
    return hist, len(rows), skipped, dict(col_counts)

def find_prior_rating(hist, horse, target_date):
    items = hist.get(horse, [])
    if not items or target_date is None:
        return None, None
    dates = [x[0] for x in items]
    i = bisect.bisect_left(dates, target_date) - 1
    if i < 0:
        return None, None
    return items[i]

def build_style_history():
    rows = read_csv(RUN_STYLE)
    hist = defaultdict(list); skipped = 0
    for r in rows:
        h = norm_horse(first(r, ["horse", "horse_name", "runner", "runner_name", "horse_key"]))
        d = parse_date(first(r, ["race_date", "date", "meeting_date"]))
        if not h or d is None:
            skipped += 1; continue
        style = style_band(first(r, ["run_style_v1", "run_style", "pace_role_v1", "dominant_run_style"]))
        conf = conf_band(first(r, ["run_style_confidence_v1", "style_confidence", "confidence"]))
        hist[h].append((d, style, conf))
    for h in hist:
        hist[h].sort(key=lambda x: x[0])
    return hist, len(rows), skipped

def find_prior_style(hist, horse, target_date):
    items = hist.get(horse, [])
    if not items or target_date is None:
        return None, "UNKNOWN", "MISSING"
    dates = [x[0] for x in items]
    i = bisect.bisect_left(dates, target_date) - 1
    if i < 0:
        return None, "UNKNOWN", "MISSING"
    return items[i]

def is_winner(row):
    return num(row.get("finish_pos")) == 1

def finish_value(row):
    x = num(row.get("finish_pos"))
    return int(x) if x is not None else 999

def rank_rows(rows, col):
    ranked = sorted(rows, key=lambda r: (-(num(r.get(col)) if num(r.get(col)) is not None else -999999), r.get("horse_norm", "")))
    ranks = {r["horse_norm"]: i + 1 for i, r in enumerate(ranked)}
    return ranked, ranks

def race_shape(rows):
    field = len(rows); counts = defaultdict(int); known = 0; confident = 0
    for r in rows:
        s = r.get("prior_run_style_band", "UNKNOWN")
        c = r.get("prior_run_style_confidence", "MISSING")
        counts[s] += 1
        if s != "UNKNOWN": known += 1
        if s != "UNKNOWN" and c in VALID_CONF: confident += 1
    leader = counts["LEADER"]; onpace = counts["ON_PACE"]; front = leader + onpace
    known_conf_ratio = confident / field if field else 0
    front_ratio = front / field if field else 0
    if known_conf_ratio < MIN_KNOWN_STYLE_RATIO:
        band = "UNKNOWN_PRESSURE"; shape_conf = "MISSING"; unreliable = "YES"
    else:
        shape_conf = "HIGH" if known_conf_ratio >= 0.80 else "MEDIUM"
        unreliable = "YES" if leader > max(4, round(field * 0.45)) else "NO"
        if unreliable == "YES": band = "UNRELIABLE_LEADER_COUNT"
        elif leader >= 3 or front_ratio >= 0.45: band = "HIGH_PRESSURE"
        elif leader >= 2 or front_ratio >= 0.30: band = "MODERATE_PRESSURE"
        elif leader <= 1 and front_ratio < 0.30: band = "LOW_PRESSURE"
        else: band = "UNKNOWN_PRESSURE"
    score = round((leader * 18) + (onpace * 7) + (front_ratio * 25), 4)
    return {
        "leader_count": leader, "on_pace_count": onpace, "midfield_count": counts["MIDFIELD"],
        "backmarker_count": counts["BACKMARKER"], "unknown_style_count": counts["UNKNOWN"],
        "known_confident_style_ratio": known_conf_ratio, "front_ratio": front_ratio,
        "pace_pressure_score": score, "pace_pressure_band": band,
        "race_shape_confidence": shape_conf, "unreliable_leader_count": unreliable,
    }

def base_adjustment(style, pressure):
    table = {
        "LOW_PRESSURE": {"LEADER": 0.85, "ON_PACE": 0.45, "MIDFIELD": -0.10, "BACKMARKER": -0.45, "UNKNOWN": 0.0},
        "MODERATE_PRESSURE": {"LEADER": -0.15, "ON_PACE": 0.20, "MIDFIELD": 0.15, "BACKMARKER": 0.05, "UNKNOWN": 0.0},
        "HIGH_PRESSURE": {"LEADER": -0.90, "ON_PACE": -0.35, "MIDFIELD": 0.35, "BACKMARKER": 0.70, "UNKNOWN": 0.0},
    }
    return table.get(pressure, {}).get(style, 0.0)

def pace_adjustment(row, shape, mult):
    style = row.get("prior_run_style_band", "UNKNOWN")
    conf = row.get("prior_run_style_confidence", "MISSING")
    pressure = shape.get("pace_pressure_band", "UNKNOWN_PRESSURE")
    shape_conf = shape.get("race_shape_confidence", "MISSING")
    if conf not in VALID_CONF:
        return 0.0, "SUPPRESSED_NO_RUN_STYLE_CONFIDENCE"
    if shape_conf not in VALID_CONF:
        return 0.0, "SUPPRESSED_MISSING_RACE_SHAPE_CONFIDENCE"
    if shape.get("unreliable_leader_count") == "YES":
        return 0.0, "SUPPRESSED_UNRELIABLE_LEADER_COUNT"
    if pressure not in {"LOW_PRESSURE", "MODERATE_PRESSURE", "HIGH_PRESSURE"}:
        return 0.0, "SUPPRESSED_UNKNOWN_PRESSURE_BAND"
    raw = base_adjustment(style, pressure) * mult
    if row.get("distance_band") == "SPRINT": raw *= 1.10
    if row.get("distance_band") == "STAYING": raw *= 0.85
    capped = max(-ADJ_CAP, min(ADJ_CAP, raw))
    reason = f"style={style}; pressure={pressure}; style_conf={conf}; shape_conf={shape_conf}; variant_multiplier={mult}"
    if capped != raw: reason += "; CAP_HIT"
    return capped, reason

def build_spine():
    results = read_csv(RESULTS)
    rating_hist, v6_rows, v6_skipped, rating_cols = build_rating_history()
    style_hist, style_rows, style_skipped = build_style_history()
    groups = defaultdict(list)
    for r in results:
        d = parse_date(r.get("race_date")); tr = norm_track(r.get("track")); rn = clean(r.get("race_no"))
        if d is None or not tr or not rn: continue
        groups[f"{d.isoformat()}|{tr}|{rn}"].append(r)
    replay = []
    excluded = defaultdict(int)
    style_conf_counts = defaultdict(int)
    bad_rating_dates = 0; bad_style_dates = 0; leakage_failures = 0; prior_style_used = 0
    for key, group in groups.items():
        if len(group) < MIN_RUNNERS:
            excluded["TARGET_FIELD_TOO_SMALL"] += 1; continue
        date_text, tr, rn = key.split("|", 2)
        target_date = parse_date(date_text)
        winners = [r for r in group if num(r.get("finish_pos")) == 1]
        if len(winners) != 1:
            excluded["WINNER_NOT_UNIQUE_OR_MISSING"] += 1; continue
        eligible = []
        for r in group:
            if num(r.get("finish_pos")) is None: continue
            h = norm_horse(first(r, ["horse", "horse_name", "runner_name", "horse_key"]))
            if not h: continue
            prior_date, prior_rating = find_prior_rating(rating_hist, h, target_date)
            if prior_date is None or prior_rating is None: continue
            if prior_date >= target_date:
                bad_rating_dates += 1; leakage_failures += 1; continue
            style_date, style, conf = find_prior_style(style_hist, h, target_date)
            if style_date is not None and style_date >= target_date:
                bad_style_dates += 1; leakage_failures += 1
                style_date, style, conf = None, "UNKNOWN", "MISSING"
            if style_date is not None: prior_style_used += 1
            style_conf_counts[conf] += 1
            item = dict(r)
            item.update({
                "race_key": key, "race_date_iso": target_date.isoformat(), "horse_norm": h,
                "prior_rating": prior_rating, "prior_rating_date": prior_date.isoformat(),
                "days_since_prior_rating": (target_date - prior_date).days,
                "prior_run_style_date": style_date.isoformat() if style_date else "",
                "prior_run_style_band": style, "prior_run_style_confidence": conf,
                "distance_band": dist_band(first(r, ["distance", "race_distance"])),
                "field_size_band": field_band(len(group)),
            })
            eligible.append(item)
        if len(eligible) < MIN_RUNNERS:
            excluded["INSUFFICIENT_PRIOR_RATED_RUNNERS"] += 1; continue
        winner_key = norm_horse(first(winners[0], ["horse", "horse_name", "runner_name", "horse_key"]))
        if not any(r["horse_norm"] == winner_key for r in eligible):
            excluded["WINNER_NOT_PRIOR_RATED"] += 1; continue
        replay.append({"race_key": key, "date": target_date, "track": tr, "race_no": rn, "rows": eligible, "winner_key": winner_key, "shape": race_shape(eligible)})
    meta = {
        "results_rows": len(results), "v6_rows": v6_rows, "v6_skipped": v6_skipped,
        "run_style_rows": style_rows, "run_style_skipped": style_skipped,
        "race_groups": len(groups), "replay_races": len(replay), "replay_runners": sum(len(x["rows"]) for x in replay),
        "excluded": dict(excluded), "bad_prior_rating_dates": bad_rating_dates, "bad_prior_style_dates": bad_style_dates,
        "leakage_failures": leakage_failures, "prior_style_rows_used": prior_style_used,
        "style_confidence_counts": dict(style_conf_counts), "rating_source_columns": rating_cols,
    }
    return replay, meta

def evaluate_variant(replay, meta, variant, mult):
    out = []
    for race in replay:
        rows = [dict(r) for r in race["rows"]]
        shp = race["shape"]
        for r in rows:
            adj, reason = pace_adjustment(r, shp, mult)
            r["original_prior_rating"] = r["prior_rating"]
            r["pace_pressure_adjustment"] = adj
            r["pace_pressure_adjustment_reason"] = reason
            r["pace_pressure_adjusted_prior_rating"] = (num(r.get("prior_rating")) or 0) + adj
        orig_ranked, orig_ranks = rank_rows(rows, "original_prior_rating")
        adj_ranked, adj_ranks = rank_rows(rows, "pace_pressure_adjusted_prior_rating")
        orig_top, adj_top = orig_ranked[0], adj_ranked[0]
        orig_top3, adj_top3 = orig_ranked[:3], adj_ranked[:3]
        same = orig_top["horse_norm"] == adj_top["horse_norm"]
        orig_finish, adj_finish = finish_value(orig_top), finish_value(adj_top)
        moves = [abs(adj_ranks.get(r["horse_norm"], 0) - orig_ranks.get(r["horse_norm"], 0)) for r in rows]
        over = sum(1 for r in rows if abs(num(r.get("pace_pressure_adjustment")) or 0) >= ADJ_CAP)
        if moves and max(moves) >= 5: over += 1
        winner = next((r for r in rows if r["horse_norm"] == race["winner_key"]), {})
        out.append({
            "variant": variant, "race_key": race["race_key"], "race_date": race["date"].isoformat(),
            "track": first(orig_top, ["track"]), "race_no": race["race_no"], "eligible_runner_count": len(rows),
            "actual_winner": first(winner, ["horse"]), "actual_winner_original_rank": orig_ranks.get(race["winner_key"], ""),
            "actual_winner_adjusted_rank": adj_ranks.get(race["winner_key"], ""),
            "leader_count": shp["leader_count"], "on_pace_count": shp["on_pace_count"], "midfield_count": shp["midfield_count"],
            "backmarker_count": shp["backmarker_count"], "unknown_style_count": shp["unknown_style_count"],
            "known_confident_style_ratio": fmt(shp["known_confident_style_ratio"], 4), "pace_pressure_score": fmt(shp["pace_pressure_score"], 4),
            "pace_pressure_band": shp["pace_pressure_band"], "race_shape_confidence": shp["race_shape_confidence"],
            "unreliable_leader_count": shp["unreliable_leader_count"], "field_size_band": orig_top.get("field_size_band", "UNKNOWN_FIELD"),
            "distance_band": orig_top.get("distance_band", "UNKNOWN"),
            "original_top_pick": first(orig_top, ["horse"]), "original_top_pick_finish": fmt(orig_finish, 0),
            "original_top_pick_prior_rating": fmt(orig_top.get("prior_rating"), 3), "original_top_pick_prior_rating_date": orig_top.get("prior_rating_date", ""),
            "original_top_pick_style": orig_top.get("prior_run_style_band", "UNKNOWN"), "original_top_pick_style_confidence": orig_top.get("prior_run_style_confidence", "MISSING"),
            "adjusted_top_pick": first(adj_top, ["horse"]), "adjusted_top_pick_finish": fmt(adj_finish, 0),
            "adjusted_top_pick_prior_rating": fmt(adj_top.get("prior_rating"), 3), "adjusted_top_pick_prior_rating_date": adj_top.get("prior_rating_date", ""),
            "adjusted_top_pick_style": adj_top.get("prior_run_style_band", "UNKNOWN"), "adjusted_top_pick_style_confidence": adj_top.get("prior_run_style_confidence", "MISSING"),
            "adjusted_top_pick_pace_adjustment": fmt(adj_top.get("pace_pressure_adjustment"), 3),
            "adjusted_top_pick_adjusted_rating": fmt(adj_top.get("pace_pressure_adjusted_prior_rating"), 3),
            "adjusted_top_pick_adjustment_reason": adj_top.get("pace_pressure_adjustment_reason", ""),
            "original_top1_win": "YES" if is_winner(orig_top) else "NO", "adjusted_top1_win": "YES" if is_winner(adj_top) else "NO",
            "original_top3_contains_winner": "YES" if any(is_winner(r) for r in orig_top3) else "NO",
            "adjusted_top3_contains_winner": "YES" if any(is_winner(r) for r in adj_top3) else "NO",
            "same_top_pick": "YES" if same else "NO",
            "original_top_pick_better": "YES" if (not same and orig_finish < adj_finish) else "NO",
            "adjusted_top_pick_better": "YES" if (not same and adj_finish < orig_finish) else "NO",
            "both_lost": "YES" if (not is_winner(orig_top) and not is_winner(adj_top)) else "NO",
            "average_rank_movement": fmt(mean(moves) if moves else 0, 4), "max_rank_movement": max(moves) if moves else 0,
            "over_adjustment_flag": "YES" if over else "NO", "over_adjustment_count": over,
            "leakage_failure_flag": "YES" if meta["leakage_failures"] else "NO",
            "production_changed": "NO", "pricing_changed": "NO", "v6_1_changed": "NO", "v7_2g2_changed": "NO", "ui_changed": "NO",
            "built_at": datetime.now(timezone.utc).isoformat(),
        })
    return out

def verdict_for(races, runners, top1_delta, top3_delta, original_better, adjusted_better, over_adjustments, leakage_failures):
    if leakage_failures: return "LEAKAGE_RISK_BLOCKED"
    if races < 100 or runners < 500: return "INSUFFICIENT_SAMPLE"
    over_rate = over_adjustments / races if races else 0
    if top1_delta >= 0.75 and top3_delta >= 0 and adjusted_better > original_better and over_rate <= 0.20:
        return "PROMISING_RESEARCH_SIGNAL"
    if top1_delta <= -0.75 or top3_delta <= -1.0 or adjusted_better < original_better * 0.75:
        return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"

def metric_row(rows, variant, slice_name, slice_value, meta):
    races = len(rows); runners = sum(int(num(r.get("eligible_runner_count")) or 0) for r in rows)
    o1 = sum(1 for r in rows if r.get("original_top1_win") == "YES"); a1 = sum(1 for r in rows if r.get("adjusted_top1_win") == "YES")
    o3 = sum(1 for r in rows if r.get("original_top3_contains_winner") == "YES"); a3 = sum(1 for r in rows if r.get("adjusted_top3_contains_winner") == "YES")
    same = sum(1 for r in rows if r.get("same_top_pick") == "YES")
    ob = sum(1 for r in rows if r.get("original_top_pick_better") == "YES"); ab = sum(1 for r in rows if r.get("adjusted_top_pick_better") == "YES")
    both = sum(1 for r in rows if r.get("both_lost") == "YES")
    moves = [num(r.get("average_rank_movement")) or 0 for r in rows]
    max_move = max([int(num(r.get("max_rank_movement")) or 0) for r in rows] or [0])
    over = sum(1 for r in rows if r.get("over_adjustment_flag") == "YES")
    o1p, a1p, o3p, a3p = pct(o1, races), pct(a1, races), pct(o3, races), pct(a3, races)
    top1_delta, top3_delta = round(a1p - o1p, 4), round(a3p - o3p, 4)
    verdict = verdict_for(races, runners, top1_delta, top3_delta, ob, ab, over, meta["leakage_failures"])
    return {
        "variant": variant, "slice_name": slice_name, "slice_value": slice_value,
        "races_tested": races, "runners_tested": runners,
        "original_top1_win_pct": o1p, "adjusted_top1_win_pct": a1p, "top1_delta_pct": top1_delta,
        "original_top3_win_pct": o3p, "adjusted_top3_win_pct": a3p, "top3_delta_pct": top3_delta,
        "same_top_pick_pct": pct(same, races), "original_better_count": ob, "adjusted_better_count": ab,
        "both_lost_count": both, "average_rank_movement": round(mean(moves), 4) if moves else 0,
        "max_rank_movement": max_move, "over_adjustment_count": over, "leakage_failures": meta["leakage_failures"],
        "verdict": verdict, "production_changed": "NO", "pricing_changed": "NO", "v6_1_changed": "NO", "v7_2g2_changed": "NO", "ui_changed": "NO",
    }

def build_summary(all_rows, meta):
    summary = []
    by_variant = defaultdict(list)
    for r in all_rows: by_variant[r["variant"]].append(r)
    specs = [
        ("STYLE", "adjusted_top_pick_style", ["LEADER", "ON_PACE", "MIDFIELD", "BACKMARKER", "UNKNOWN"]),
        ("PRESSURE", "pace_pressure_band", ["HIGH_PRESSURE", "MODERATE_PRESSURE", "LOW_PRESSURE", "UNKNOWN_PRESSURE", "UNRELIABLE_LEADER_COUNT"]),
        ("FIELD_SIZE", "field_size_band", ["SMALL_FIELD", "MID_FIELD", "LARGE_FIELD"]),
        ("DISTANCE", "distance_band", ["SPRINT", "MILE", "MIDDLE", "STAYING", "UNKNOWN"]),
    ]
    for variant, rows in by_variant.items():
        summary.append(metric_row(rows, variant, "OVERALL", "OVERALL", meta))
        for sname, col, vals in specs:
            for val in vals:
                subset = [r for r in rows if r.get(col) == val]
                if subset: summary.append(metric_row(subset, variant, sname, val, meta))
    return summary

def build_leakage(meta):
    return [
        {"audit_item":"TARGET_RESULTS_SOURCE", "source_file":str(RESULTS.relative_to(ROOT)).replace("\\","/"), "fields_used":"race_date|track|race_no|horse|finish_pos|distance", "usage":"EVALUATION_AND_RACE_GROUPING_ONLY", "leakage_risk":"CONTROLLED_EVALUATION_OUTCOME_ONLY", "status":"PASS", "details":"finish_pos used only after ranking to score replay outcomes; not used as feature."},
        {"audit_item":"PRIOR_RATING_SOURCE", "source_file":str(V6.relative_to(ROOT)).replace("\\","/"), "fields_used":"horse|race_date|performance_rating_v6_1_research", "usage":"STRICT_PRIOR_FEATURE", "leakage_risk":"LOW_AFTER_DATE_GUARD", "status":"PASS" if meta["bad_prior_rating_dates"] == 0 else "FAIL", "details":f"bad_prior_rating_dates={meta['bad_prior_rating_dates']}; rule=prior_rating_date < target_race_date"},
        {"audit_item":"PRIOR_RUN_STYLE_SOURCE", "source_file":str(RUN_STYLE.relative_to(ROOT)).replace("\\","/"), "fields_used":"horse|race_date|run_style_v1|run_style_confidence_v1", "usage":"STRICT_PRIOR_FEATURE", "leakage_risk":"LOW_AFTER_DATE_GUARD", "status":"PASS" if meta["bad_prior_style_dates"] == 0 else "FAIL", "details":f"bad_prior_style_dates={meta['bad_prior_style_dates']}; target-race pos800/pos400 not used."},
        {"audit_item":"EXCLUDED_DIRECT_PACE_PRESSURE_REPLAY_FILE", "source_file":"public/data/edgeiq_pace_pressure_engine_v1.csv", "fields_used":"NONE", "usage":"EXCLUDED_FROM_FEATURES", "leakage_risk":"MEDIUM_REPLAY_FILE_HAS_OUTCOME_COLUMNS", "status":"PASS", "details":"Contains won/placed/finish_position, so not joined as a feature source."},
        {"audit_item":"EXCLUDED_DIRECT_RACE_SHAPE_ARCHIVE_FILE", "source_file":"public/data/edgeiq_historical_race_shape_archive_v1.csv", "fields_used":"NONE", "usage":"EXCLUDED_FROM_FEATURES", "leakage_risk":"MEDIUM_TO_HIGH_HAS_INRUN_AND_RESULT_COLUMNS", "status":"PASS", "details":"Contains inRun/finish/won style fields, so not joined as target-race feature source."},
        {"audit_item":"OVERALL_LEAKAGE_FAILURES", "source_file":"ALL_USED_SOURCES", "fields_used":"date guards", "usage":"LEAKAGE_GATE", "leakage_risk":"BLOCKING_IF_NONZERO", "status":"PASS" if meta["leakage_failures"] == 0 else "FAIL", "details":f"leakage_failures={meta['leakage_failures']}"},
    ]

def write_report(summary, meta):
    overall = [r for r in summary if r["slice_name"] == "OVERALL"]
    best = max(overall, key=lambda r: (float(r["top1_delta_pct"]), float(r["top3_delta_pct"]))) if overall else {}
    lines = [
        "EDGEIQ_PACE_PRESSURE_SIGNAL_REPLAY_V1", f"built_at={datetime.now(timezone.utc).isoformat()}",
        f"target_results_source={RESULTS.name}", f"prior_rating_source={V6.name}", f"prior_run_style_source={RUN_STYLE.name}",
        f"results_rows={meta['results_rows']}", f"v6_rows={meta['v6_rows']}", f"run_style_rows={meta['run_style_rows']}",
        f"race_groups={meta['race_groups']}", f"replay_races={meta['replay_races']}", f"replay_runners={meta['replay_runners']}",
        "prior_rating_rule=latest V6.1 rating strictly before target race date",
        "prior_run_style_rule=latest historical run-style row strictly before target race date",
        "direct_same_race_pace_pressure_files_used=NO", "post_race_fields_used_as_features=NO",
        f"leakage_failures={meta['leakage_failures']}", "production_changed=NO", "pricing_changed=NO", "v6_1_changed=NO", "v7_2g2_changed=NO", "ui_changed=NO", "", "EXCLUDED_RACES",
    ]
    for k, v in sorted(meta["excluded"].items()): lines.append(f"{k}={v}")
    lines += ["", "STYLE_CONFIDENCE_COUNTS"]
    for k, v in sorted(meta["style_confidence_counts"].items()): lines.append(f"{k}={v}")
    lines += ["", "OVERALL_VARIANT_RESULTS"]
    for r in overall:
        lines.append(f"{r['variant']}: races={r['races_tested']} runners={r['runners_tested']} original_top1={r['original_top1_win_pct']} adjusted_top1={r['adjusted_top1_win_pct']} top1_delta={r['top1_delta_pct']} original_top3={r['original_top3_win_pct']} adjusted_top3={r['adjusted_top3_win_pct']} top3_delta={r['top3_delta_pct']} same_top_pick={r['same_top_pick_pct']} original_better={r['original_better_count']} adjusted_better={r['adjusted_better_count']} avg_rank_move={r['average_rank_movement']} max_rank_move={r['max_rank_movement']} over_adjustments={r['over_adjustment_count']} verdict={r['verdict']}")
    if best:
        lines += ["", f"best_variant_by_top1_delta={best['variant']}", f"best_variant_verdict={best['verdict']}"]
    promising = [r for r in summary if r["slice_name"] != "OVERALL" and r["verdict"] == "PROMISING_RESEARCH_SIGNAL"]
    lines += ["", "PROMISING_SLICES"]
    if promising:
        for r in promising[:20]: lines.append(f"{r['variant']} {r['slice_name']}={r['slice_value']} races={r['races_tested']} top1_delta={r['top1_delta_pct']} top3_delta={r['top3_delta_pct']} verdict={r['verdict']}")
    else:
        lines.append("NONE")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    replay, meta = build_spine()
    rows = []
    for variant, mult in VARIANTS.items(): rows.extend(evaluate_variant(replay, meta, variant, mult))
    write_csv(OUT, rows)
    summary = build_summary(rows, meta); write_csv(SUMMARY, summary)
    leakage = build_leakage(meta); write_csv(LEAKAGE, leakage)
    write_report(summary, meta)
    print(OUT); print(SUMMARY); print(LEAKAGE); print(REPORT)

if __name__ == "__main__":
    main()
