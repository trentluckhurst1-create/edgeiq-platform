import bisect
import csv
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
RESULTS = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
V6 = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RUN_STYLE = DATA / "edgeiq_historical_run_style_v1.csv"
ADJUSTMENT_CAP = 4.0
MIN_ELIGIBLE_RUNNERS = 3
PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}
RATING_COLUMNS = [
    "performance_rating_v6_1_research",
    "performance_rating_v6_1",
    "performance_rating",
    "rating",
    "rating_v6_1",
]

csv.field_size_limit(1024 * 1024 * 128)


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def first(row, columns):
    for col in columns:
        if col in row and clean(row.get(col)).lower() not in PLACEHOLDERS:
            return row.get(col)
    return ""


def parse_num(value):
    text = clean(value).replace("$", "").replace(",", "")
    if text.lower() in PLACEHOLDERS:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def parse_date(value):
    text = clean(value)
    if not text:
        return None
    text = text.replace(".", "")
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d%b%y", "%d%b%Y", "%d %b %y", "%d %b %Y"]:
        try:
            return datetime.strptime(text[:11], fmt).date()
        except Exception:
            pass
    return None


def norm_horse(value):
    text = clean(value).upper().replace("’", "'").replace("`", "'")
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def norm_track(value):
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def fmt(value, places=4):
    if value is None or value == "":
        return ""
    try:
        if places == 0:
            return str(int(round(float(value))))
        return str(round(float(value), places))
    except Exception:
        return clean(value)


def pct(num, den):
    return round((num / den) * 100, 4) if den else 0.0


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def detect_rating(row):
    for col in RATING_COLUMNS:
        value = parse_num(row.get(col))
        if value is not None:
            return value, col
    return None, ""


def normalize_condition_band(condition):
    text = clean(condition).upper()
    if any(key in text for key in ["HEAVY", "HVY", "H10", "H9", "H8"]):
        return "HEAVY"
    if any(key in text for key in ["SOFT", "SFT", "S7", "S6", "S5"]):
        return "SOFT"
    if any(key in text for key in ["GOOD", "FIRM", "FAST", "DEAD", "G4", "G3", "G2", "F2"]):
        return "FIRM_GOOD"
    return "UNKNOWN"


def distance_band(distance):
    d = parse_num(distance)
    if d is None:
        return "UNKNOWN"
    if d <= 1200:
        return "SPRINT"
    if d <= 1600:
        return "MILE"
    if d <= 2000:
        return "MIDDLE"
    return "STAYING"


def normalize_run_style(style):
    text = clean(style).upper().replace("-", "_").replace(" ", "_")
    if not text or text.lower() in PLACEHOLDERS:
        return "UNKNOWN"
    if "LEADER" in text or text in {"FRONT", "FRONTRUNNER", "FRONT_RUNNER", "SPEED"}:
        return "LEADER"
    if "ON_PACE" in text or "ONPACE" in text or "HANDY" in text or "PROMINENT" in text:
        return "ON_PACE"
    if "MID" in text or "SETTLE" in text:
        return "MIDFIELD"
    if "BACK" in text or "CLOSER" in text or "OFF_PACE" in text:
        return "BACKMARKER"
    return "UNKNOWN"


def is_winner(row):
    return parse_num(row.get("finish_pos")) == 1


def finish_value(row):
    value = parse_num(row.get("finish_pos"))
    return int(value) if value is not None else 999


def is_place_proxy(row):
    value = finish_value(row)
    field = parse_num(row.get("field_size")) or 0
    if value <= 2:
        return True
    if field >= 8 and value <= 3:
        return True
    return False


def rank_rows(rows, score_col):
    ranked = sorted(
        rows,
        key=lambda row: (
            -(parse_num(row.get(score_col)) if parse_num(row.get(score_col)) is not None else -999999),
            norm_horse(first(row, ["horse", "horse_key"])),
        ),
    )
    ranks = {norm_horse(first(row, ["horse", "horse_key"])): idx + 1 for idx, row in enumerate(ranked)}
    return ranked, ranks


def build_prior_rating_history():
    rows = read_csv(V6)
    by_horse = defaultdict(list)
    rating_source_columns = defaultdict(int)
    for row in rows:
        horse = norm_horse(first(row, ["horse", "horse_name", "runner", "runner_name", "horse_key"]))
        date = parse_date(first(row, ["race_date", "date", "meeting_date"]))
        rating, col = detect_rating(row)
        if not horse or date is None or rating is None:
            continue
        rating_source_columns[col] += 1
        by_horse[horse].append((date, rating, row))
    for horse in by_horse:
        by_horse[horse].sort(key=lambda item: item[0])
    return by_horse, dict(rating_source_columns), len(rows)


def find_prior_rating(history, horse_key, target_date):
    items = history.get(horse_key, [])
    if not items or target_date is None:
        return None, None, None
    dates = [item[0] for item in items]
    idx = bisect.bisect_left(dates, target_date) - 1
    if idx < 0:
        return None, None, None
    date, rating, row = items[idx]
    return date, rating, row


def build_previous_weight_history(result_rows):
    by_horse = defaultdict(list)
    for row in result_rows:
        horse = norm_horse(first(row, ["horse", "horse_name", "runner", "runner_name", "horse_key"]))
        date = parse_date(first(row, ["race_date", "date", "meeting_date"]))
        weight = parse_num(row.get("weight"))
        if not horse or date is None or weight is None:
            continue
        by_horse[horse].append((date, weight, row))
    for horse in by_horse:
        by_horse[horse].sort(key=lambda item: item[0])
    return by_horse


def find_previous_weight(history, horse_key, target_date):
    items = history.get(horse_key, [])
    if not items or target_date is None:
        return None, None, None
    dates = [item[0] for item in items]
    idx = bisect.bisect_left(dates, target_date) - 1
    if idx < 0:
        return None, None, None
    date, weight, row = items[idx]
    return date, weight, row


def build_prior_run_style_history():
    if not RUN_STYLE.exists():
        return {}, 0
    rows = read_csv(RUN_STYLE)
    by_horse = defaultdict(list)
    for row in rows:
        horse = norm_horse(first(row, ["horse", "horse_name", "runner", "runner_name", "horse_key"]))
        date = parse_date(first(row, ["race_date", "date", "meeting_date"]))
        style = normalize_run_style(first(row, ["run_style_v1", "run_style", "pace_role_v1", "dominant_run_style"]))
        if not horse or date is None:
            continue
        by_horse[horse].append((date, style, row))
    for horse in by_horse:
        by_horse[horse].sort(key=lambda item: item[0])
    return by_horse, len(rows)


def find_prior_run_style(history, horse_key, target_date):
    items = history.get(horse_key, [])
    if not items or target_date is None:
        return None, "UNKNOWN", None
    dates = [item[0] for item in items]
    idx = bisect.bisect_left(dates, target_date) - 1
    if idx < 0:
        return None, "UNKNOWN", None
    date, style, row = items[idx]
    return date, style, row


def build_replay_spine():
    result_rows = read_csv(RESULTS)
    prior_history, rating_source_columns, v6_rows = build_prior_rating_history()
    prev_weight_history = build_previous_weight_history(result_rows)
    run_style_history, run_style_rows = build_prior_run_style_history()
    groups = defaultdict(list)
    for row in result_rows:
        date = parse_date(row.get("race_date"))
        track = norm_track(row.get("track"))
        race_no = clean(row.get("race_no"))
        if date is None or not track or not race_no:
            continue
        groups[f"{date.isoformat()}|{track}|{race_no}"].append(row)

    replay_races = []
    excluded = defaultdict(int)
    target_rows_with_weight = 0
    target_rows_with_prior_rating = 0
    target_rows_with_previous_weight = 0
    target_rows_with_prior_run_style = 0

    for key, rows in groups.items():
        if len(rows) < MIN_ELIGIBLE_RUNNERS:
            excluded["TARGET_FIELD_TOO_SMALL"] += 1
            continue
        target_date_text, track_key, race_no = key.split("|", 2)
        target_date = parse_date(target_date_text)
        winners = [row for row in rows if parse_num(row.get("finish_pos")) == 1]
        if len(winners) != 1:
            excluded["WINNER_NOT_UNIQUE_OR_MISSING"] += 1
            continue
        weighted_rows = [row for row in rows if parse_num(row.get("weight")) is not None and parse_num(row.get("finish_pos")) is not None]
        if len(weighted_rows) < MIN_ELIGIBLE_RUNNERS:
            excluded["INSUFFICIENT_CURRENT_WEIGHT_ROWS"] += 1
            continue
        current_weights = [parse_num(row.get("weight")) for row in weighted_rows if parse_num(row.get("weight")) is not None]
        race_avg_weight = mean(current_weights) if current_weights else None
        if race_avg_weight is None:
            excluded["MISSING_FIELD_AVERAGE_WEIGHT"] += 1
            continue
        target_rows_with_weight += len(weighted_rows)
        eligible = []
        for row in weighted_rows:
            horse_name = first(row, ["horse", "horse_name", "runner_name", "horse_key"])
            horse_key = norm_horse(horse_name)
            current_weight = parse_num(row.get("weight"))
            if not horse_key or current_weight is None:
                continue
            prior_date, prior_rating, prior_row = find_prior_rating(prior_history, horse_key, target_date)
            if prior_rating is None or prior_date is None or prior_date >= target_date:
                continue
            prev_weight_date, prev_weight, prev_weight_row = find_previous_weight(prev_weight_history, horse_key, target_date)
            style_date, prior_style, style_row = find_prior_run_style(run_style_history, horse_key, target_date)
            item = dict(row)
            item["race_key"] = key
            item["race_date_iso"] = target_date.isoformat()
            item["track_key_norm"] = track_key
            item["horse_norm"] = horse_key
            item["prior_rating"] = prior_rating
            item["prior_rating_date"] = prior_date.isoformat()
            item["days_since_prior_rating"] = (target_date - prior_date).days
            item["carried_weight_kg"] = current_weight
            item["race_avg_weight_kg"] = race_avg_weight
            item["weight_delta_vs_avg_kg"] = current_weight - race_avg_weight
            item["previous_start_weight_kg"] = prev_weight if prev_weight is not None else ""
            item["previous_start_weight_date"] = prev_weight_date.isoformat() if prev_weight_date else ""
            item["weight_change_vs_previous_start_kg"] = current_weight - prev_weight if prev_weight is not None else ""
            item["distance_band"] = distance_band(first(row, ["distance", "race_distance"]))
            item["condition_band"] = normalize_condition_band(first(row, ["condition", "track_condition", "going"]))
            item["prior_run_style_band"] = prior_style
            item["prior_run_style_date"] = style_date.isoformat() if style_date else ""
            item["source_scope"] = "PRIOR_RATING_AND_CURRENT_WEIGHT_RESEARCH_ONLY"
            if prev_weight is not None:
                target_rows_with_previous_weight += 1
            if prior_style != "UNKNOWN":
                target_rows_with_prior_run_style += 1
            eligible.append(item)
        target_rows_with_prior_rating += len(eligible)
        if len(eligible) < MIN_ELIGIBLE_RUNNERS:
            excluded["INSUFFICIENT_PRIOR_RATED_RUNNERS"] += 1
            continue
        winner_key = norm_horse(first(winners[0], ["horse", "horse_name", "runner_name", "horse_key"]))
        winner_eligible = [row for row in eligible if row.get("horse_norm") == winner_key]
        if not winner_eligible:
            excluded["WINNER_NOT_PRIOR_RATED"] += 1
            continue
        replay_races.append({
            "race_key": key,
            "target_date": target_date,
            "track_key": track_key,
            "race_no": race_no,
            "rows": eligible,
            "winner": winner_eligible[0],
            "distance_band": eligible[0].get("distance_band", "UNKNOWN") if eligible else "UNKNOWN",
            "condition_band": eligible[0].get("condition_band", "UNKNOWN") if eligible else "UNKNOWN",
        })

    meta = {
        "result_rows": len(result_rows),
        "v6_rating_rows": v6_rows,
        "run_style_rows": run_style_rows,
        "target_race_groups": len(groups),
        "base_replay_races": len(replay_races),
        "base_replay_runners": sum(len(race["rows"]) for race in replay_races),
        "target_rows_with_weight": target_rows_with_weight,
        "target_rows_with_prior_rating": target_rows_with_prior_rating,
        "target_rows_with_previous_weight": target_rows_with_previous_weight,
        "target_rows_with_prior_run_style": target_rows_with_prior_run_style,
        "excluded": dict(excluded),
        "rating_source_columns": rating_source_columns,
    }
    return replay_races, meta


def capped_adjustment(raw):
    if raw is None:
        return 0.0, False
    capped = max(-ADJUSTMENT_CAP, min(ADJUSTMENT_CAP, raw))
    return capped, abs(raw) > ADJUSTMENT_CAP


def evaluate_module(module_name, module_slug, adjustment_fn, context_band_fn=None, race_filter_fn=None, output_prefix=None, report_title=None, method_notes=None):
    replay_races, meta = build_replay_spine()
    built_at = datetime.now(timezone.utc).isoformat()
    output_rows = []
    races_used = []
    excluded_module = defaultdict(int)

    for race in replay_races:
        rows = [dict(row) for row in race["rows"]]
        if race_filter_fn:
            rows = [row for row in rows if race_filter_fn(row)]
        if len(rows) < MIN_ELIGIBLE_RUNNERS:
            excluded_module["INSUFFICIENT_MODULE_ELIGIBLE_RUNNERS"] += 1
            continue
        winner_key = race["winner"].get("horse_norm")
        if not any(row.get("horse_norm") == winner_key for row in rows):
            excluded_module["WINNER_NOT_MODULE_ELIGIBLE"] += 1
            continue
        for row in rows:
            row["original_prior_rating"] = row["prior_rating"]
            raw_adjustment, reason = adjustment_fn(row, race)
            adjustment, cap_hit = capped_adjustment(raw_adjustment)
            row["interaction_raw_adjustment"] = raw_adjustment if raw_adjustment is not None else 0.0
            row["interaction_adjustment"] = adjustment
            row["interaction_adjustment_reason"] = reason
            row["interaction_cap_hit"] = "YES" if cap_hit else "NO"
            row["interaction_adjusted_prior_rating"] = parse_num(row.get("prior_rating")) + adjustment
        original_ranked, original_ranks = rank_rows(rows, "original_prior_rating")
        adjusted_ranked, adjusted_ranks = rank_rows(rows, "interaction_adjusted_prior_rating")
        original_top = original_ranked[0]
        adjusted_top = adjusted_ranked[0]
        original_top3 = original_ranked[:3]
        adjusted_top3 = adjusted_ranked[:3]
        rank_movements = []
        for row in rows:
            horse = row.get("horse_norm")
            if horse in original_ranks and horse in adjusted_ranks:
                rank_movements.append(abs(adjusted_ranks[horse] - original_ranks[horse]))
        original_finish = finish_value(original_top)
        adjusted_finish = finish_value(adjusted_top)
        same_pick = original_top.get("horse_norm") == adjusted_top.get("horse_norm")
        original_better = (not same_pick) and original_finish < adjusted_finish
        adjusted_better = (not same_pick) and adjusted_finish < original_finish
        both_lost = (not is_winner(original_top)) and (not is_winner(adjusted_top))
        cap_hit_or_large_move_count = sum(1 for row in rows if row.get("interaction_cap_hit") == "YES")
        if rank_movements and max(rank_movements) >= 5:
            cap_hit_or_large_move_count += 1
        context_band = context_band_fn(race, original_top, adjusted_top, rows) if context_band_fn else "OVERALL"
        output_rows.append({
            "module": module_name,
            "module_slug": module_slug,
            "context_band": context_band,
            "race_key": race["race_key"],
            "race_date": race["target_date"].isoformat(),
            "track": first(original_top, ["track"]),
            "race_no": race["race_no"],
            "eligible_runner_count": len(rows),
            "race_avg_weight_kg": fmt(first(original_top, ["race_avg_weight_kg"]), 3),
            "actual_winner": first(race["winner"], ["horse"]),
            "actual_winner_original_rank": original_ranks.get(winner_key, ""),
            "actual_winner_adjusted_rank": adjusted_ranks.get(winner_key, ""),
            "original_top_pick": first(original_top, ["horse"]),
            "original_top_pick_finish": fmt(original_finish, 0),
            "original_top_pick_prior_rating": fmt(original_top.get("prior_rating"), 3),
            "original_top_pick_prior_rating_date": original_top.get("prior_rating_date", ""),
            "original_top_pick_weight": fmt(original_top.get("carried_weight_kg"), 3),
            "original_top_pick_weight_delta_vs_avg_kg": fmt(original_top.get("weight_delta_vs_avg_kg"), 3),
            "original_top_pick_weight_change_vs_previous_start_kg": fmt(original_top.get("weight_change_vs_previous_start_kg"), 3),
            "original_top_pick_distance_band": original_top.get("distance_band", "UNKNOWN"),
            "original_top_pick_condition_band": original_top.get("condition_band", "UNKNOWN"),
            "original_top_pick_prior_run_style_band": original_top.get("prior_run_style_band", "UNKNOWN"),
            "adjusted_top_pick": first(adjusted_top, ["horse"]),
            "adjusted_top_pick_finish": fmt(adjusted_finish, 0),
            "adjusted_top_pick_prior_rating": fmt(adjusted_top.get("prior_rating"), 3),
            "adjusted_top_pick_prior_rating_date": adjusted_top.get("prior_rating_date", ""),
            "adjusted_top_pick_weight": fmt(adjusted_top.get("carried_weight_kg"), 3),
            "adjusted_top_pick_weight_delta_vs_avg_kg": fmt(adjusted_top.get("weight_delta_vs_avg_kg"), 3),
            "adjusted_top_pick_weight_change_vs_previous_start_kg": fmt(adjusted_top.get("weight_change_vs_previous_start_kg"), 3),
            "adjusted_top_pick_distance_band": adjusted_top.get("distance_band", "UNKNOWN"),
            "adjusted_top_pick_condition_band": adjusted_top.get("condition_band", "UNKNOWN"),
            "adjusted_top_pick_prior_run_style_band": adjusted_top.get("prior_run_style_band", "UNKNOWN"),
            "adjusted_top_pick_adjustment": fmt(adjusted_top.get("interaction_adjustment"), 3),
            "adjusted_top_pick_adjusted_prior_rating": fmt(adjusted_top.get("interaction_adjusted_prior_rating"), 3),
            "adjusted_top_pick_adjustment_reason": adjusted_top.get("interaction_adjustment_reason", ""),
            "original_top1_win": "YES" if is_winner(original_top) else "NO",
            "adjusted_top1_win": "YES" if is_winner(adjusted_top) else "NO",
            "original_top3_contains_winner": "YES" if any(is_winner(row) for row in original_top3) else "NO",
            "adjusted_top3_contains_winner": "YES" if any(is_winner(row) for row in adjusted_top3) else "NO",
            "same_top_pick": "YES" if same_pick else "NO",
            "original_top_pick_better": "YES" if original_better else "NO",
            "adjusted_top_pick_better": "YES" if adjusted_better else "NO",
            "both_lost": "YES" if both_lost else "NO",
            "average_rank_movement": fmt(mean(rank_movements) if rank_movements else 0, 4),
            "max_rank_movement": max(rank_movements) if rank_movements else 0,
            "over_adjustment_flag": "YES" if cap_hit_or_large_move_count else "NO",
            "cap_hit_or_large_move_count": cap_hit_or_large_move_count,
            "research_scope": "INTERACTION_SIGNAL_RESEARCH_ONLY_PRIOR_RATINGS_NO_AGE_SEX_NO_WFA",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
            "built_at": built_at,
        })
        races_used.append(output_rows[-1])

    if output_prefix is None:
        output_prefix = module_slug
    out_path = DATA / f"{output_prefix}.csv"
    summary_path = DATA / f"{output_prefix}_summary.csv"
    report_path = DATA / f"{output_prefix}_report.txt"
    write_csv(out_path, output_rows)

    summary_rows = build_summary_rows(module_name, module_slug, output_rows, meta, excluded_module, method_notes)
    write_csv(summary_path, summary_rows)
    write_report(report_path, report_title or module_name, module_slug, summary_rows, meta, excluded_module, method_notes)
    return out_path, summary_path, report_path


def metric_row(module_name, module_slug, context_band, rows, meta, excluded_module, method_notes):
    races = len(rows)
    runners = sum(int(parse_num(row.get("eligible_runner_count")) or 0) for row in rows)
    original_top1 = sum(1 for row in rows if row.get("original_top1_win") == "YES")
    adjusted_top1 = sum(1 for row in rows if row.get("adjusted_top1_win") == "YES")
    original_top3 = sum(1 for row in rows if row.get("original_top3_contains_winner") == "YES")
    adjusted_top3 = sum(1 for row in rows if row.get("adjusted_top3_contains_winner") == "YES")
    same_top = sum(1 for row in rows if row.get("same_top_pick") == "YES")
    original_better = sum(1 for row in rows if row.get("original_top_pick_better") == "YES")
    adjusted_better = sum(1 for row in rows if row.get("adjusted_top_pick_better") == "YES")
    both_lost = sum(1 for row in rows if row.get("both_lost") == "YES")
    over_adjustment = sum(1 for row in rows if row.get("over_adjustment_flag") == "YES")
    rank_moves = [parse_num(row.get("average_rank_movement")) or 0 for row in rows]
    original_top1_pct = pct(original_top1, races)
    adjusted_top1_pct = pct(adjusted_top1, races)
    original_top3_pct = pct(original_top3, races)
    adjusted_top3_pct = pct(adjusted_top3, races)
    top1_delta = round(adjusted_top1_pct - original_top1_pct, 4)
    top3_delta = round(adjusted_top3_pct - original_top3_pct, 4)
    verdict = verdict_for(races, runners, top1_delta, top3_delta, original_better, adjusted_better, over_adjustment)
    return {
        "module": module_name,
        "module_slug": module_slug,
        "context_band": context_band,
        "races_tested": races,
        "runners_tested": runners,
        "original_top1_win_pct": original_top1_pct,
        "adjusted_top1_win_pct": adjusted_top1_pct,
        "top1_delta_pct": top1_delta,
        "original_top3_win_pct": original_top3_pct,
        "adjusted_top3_win_pct": adjusted_top3_pct,
        "top3_delta_pct": top3_delta,
        "same_top_pick_pct": pct(same_top, races),
        "original_better_count": original_better,
        "adjusted_better_count": adjusted_better,
        "both_lost_count": both_lost,
        "average_rank_movement": round(mean(rank_moves), 4) if rank_moves else 0,
        "over_adjustment_count": over_adjustment,
        "base_replay_races": meta.get("base_replay_races", 0),
        "base_replay_runners": meta.get("base_replay_runners", 0),
        "excluded_module_races": sum(excluded_module.values()),
        "target_rows_with_previous_weight": meta.get("target_rows_with_previous_weight", 0),
        "target_rows_with_prior_run_style": meta.get("target_rows_with_prior_run_style", 0),
        "method_notes": method_notes or "",
        "prior_rating_rule": "latest V6.1 rating with race_date strictly before target race_date",
        "age_fields_used": "NO",
        "sex_fields_used": "NO",
        "wfa_claim_made": "NO",
        "production_changed": "NO",
        "pricing_changed": "NO",
        "v6_1_changed": "NO",
        "v7_2g2_changed": "NO",
        "ui_changed": "NO",
        "verdict": verdict,
    }


def build_summary_rows(module_name, module_slug, output_rows, meta, excluded_module, method_notes):
    rows = [metric_row(module_name, module_slug, "OVERALL", output_rows, meta, excluded_module, method_notes)]
    by_band = defaultdict(list)
    for row in output_rows:
        band = row.get("context_band") or "UNKNOWN"
        by_band[band].append(row)
    for band in sorted(by_band):
        if band == "OVERALL":
            continue
        rows.append(metric_row(module_name, module_slug, band, by_band[band], meta, excluded_module, method_notes))
    return rows


def verdict_for(races, runners, top1_delta, top3_delta, original_better, adjusted_better, over_adjustment):
    if races < 100 or runners < 500:
        return "INSUFFICIENT_SAMPLE"
    over_rate = over_adjustment / races if races else 0
    if top1_delta >= 0.75 and top3_delta >= 0 and adjusted_better > original_better and over_rate <= 0.25:
        return "PROMISING_RESEARCH_SIGNAL"
    if top1_delta <= -0.75 or top3_delta <= -1.0 or adjusted_better < original_better * 0.75:
        return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"


def write_report(path, title, module_slug, summary_rows, meta, excluded_module, method_notes):
    overall = next((row for row in summary_rows if row.get("context_band") == "OVERALL"), summary_rows[0] if summary_rows else {})
    lines = [
        title,
        f"module_slug={module_slug}",
        f"historical_results_weight_source={RESULTS.name}",
        f"prior_rating_source={V6.name}",
        f"run_style_source={RUN_STYLE.name if RUN_STYLE.exists() else 'MISSING'}",
        f"result_rows={meta.get('result_rows', 0)}",
        f"v6_rating_rows={meta.get('v6_rating_rows', 0)}",
        f"target_race_groups={meta.get('target_race_groups', 0)}",
        f"base_replay_races={meta.get('base_replay_races', 0)}",
        f"base_replay_runners={meta.get('base_replay_runners', 0)}",
        f"races_tested={overall.get('races_tested', 0)}",
        f"runners_tested={overall.get('runners_tested', 0)}",
        f"method_notes={method_notes or ''}",
        "prior_rating_rule=latest V6.1 rating with race_date strictly before target race_date",
        "race_relative_current_weight_used=YES_WHERE_APPLICABLE",
        "previous_start_weight_used=YES_FOR_WEIGHT_CHANGE_ONLY",
        "absolute_weight_boost_used=NO",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "wfa_claim_made=NO",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "ui_changed=NO",
        "",
        "BASE_EXCLUDED_RACE_GROUPS",
    ]
    for key, value in sorted((meta.get("excluded") or {}).items()):
        lines.append(f"{key}={value}")
    lines.extend(["", "MODULE_EXCLUDED_RACE_GROUPS"])
    for key, value in sorted(excluded_module.items()):
        lines.append(f"{key}={value}")
    lines.extend(["", "SUMMARY_RESULTS"])
    for row in summary_rows:
        lines.append(
            f"{row['context_band']}: races={row['races_tested']} runners={row['runners_tested']} original_top1={row['original_top1_win_pct']} adjusted_top1={row['adjusted_top1_win_pct']} top1_delta={row['top1_delta_pct']} original_top3={row['original_top3_win_pct']} adjusted_top3={row['adjusted_top3_win_pct']} top3_delta={row['top3_delta_pct']} same_top_pick={row['same_top_pick_pct']} original_better={row['original_better_count']} adjusted_better={row['adjusted_better_count']} both_lost={row['both_lost_count']} avg_rank_move={row['average_rank_movement']} over_adjustments={row['over_adjustment_count']} verdict={row['verdict']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def standard_race_relative_adjustment(row, per_kg, reason):
    delta = parse_num(row.get("weight_delta_vs_avg_kg"))
    if delta is None:
        return 0.0, f"{reason}; missing current race-relative delta"
    return -delta * per_kg, f"{reason}; race_relative_delta_kg={fmt(delta, 3)}; per_kg={per_kg}"
