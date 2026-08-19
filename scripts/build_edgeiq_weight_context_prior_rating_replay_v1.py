import bisect
import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
RESULTS = DATA / "edgeiq_historical_run_ratings_master_v1.csv"
V6 = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
OUT = DATA / "edgeiq_weight_context_prior_rating_replay_v1.csv"
SUMMARY = DATA / "edgeiq_weight_context_prior_rating_replay_v1_summary.csv"
REPORT = DATA / "edgeiq_weight_context_prior_rating_replay_v1_report.txt"

VARIANTS = {
    "CONSERVATIVE_0_75_PER_KG": 0.75,
    "STANDARD_1_00_PER_KG": 1.00,
    "AGGRESSIVE_1_50_PER_KG": 1.50,
}
ADJUSTMENT_CAP = 4.0
MIN_ELIGIBLE_RUNNERS = 3
PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}

csv.field_size_limit(1024 * 1024 * 64)


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def nonblank(value):
    return clean(value).lower() not in PLACEHOLDERS


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


def norm_track(value):
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def fmt(value, places=4):
    if value is None:
        return ""
    if places == 0:
        return str(int(round(float(value))))
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def first(row, keys):
    for key in keys:
        value = clean(row.get(key, ""))
        if nonblank(value):
            return value
    return ""


def race_key(row):
    return "|".join([
        first(row, ["race_date", "date", "meeting_date"]),
        norm_track(first(row, ["track", "venue"])),
        first(row, ["race_no", "race", "race_number"]),
    ])


def rating_value(row):
    return parse_num(first(row, ["performance_rating_v6_1_research", "performance_rating_v6", "performance_rating_v5_1", "performance_rating"]))


def finish_value(row):
    return parse_num(first(row, ["finish_pos", "finish_position", "finish_pos_raw"]))


def is_winner(row):
    finish = finish_value(row)
    return finish is not None and int(round(finish)) == 1


def is_place_proxy(row):
    finish = finish_value(row)
    return finish is not None and 1 <= int(round(finish)) <= 3


def build_prior_history(v6_rows):
    history = defaultdict(list)
    for row in v6_rows:
        horse_key = norm_horse(first(row, ["horse", "horse_name", "runner_name", "horse_key"]))
        date = parse_date(first(row, ["race_date", "date", "meeting_date"]))
        rating = rating_value(row)
        if not horse_key or date is None or rating is None:
            continue
        history[horse_key].append((date, rating, row))
    for horse_key in list(history.keys()):
        history[horse_key].sort(key=lambda item: item[0])
    return history


def latest_prior(history, horse_name, target_date):
    horse_key = norm_horse(horse_name)
    entries = history.get(horse_key, [])
    if not entries or target_date is None:
        return None
    dates = [entry[0] for entry in entries]
    idx = bisect.bisect_left(dates, target_date) - 1
    if idx < 0:
        return None
    return entries[idx]


def rank_rows(rows, score_key):
    ranked = sorted(rows, key=lambda r: (-(parse_num(r.get(score_key)) or -999999), clean(r.get("horse"))))
    ranks = {id(row): i + 1 for i, row in enumerate(ranked)}
    return ranked, ranks


def verdict_for_variant(races, top1_delta, top3_delta, adjusted_better, original_better, over_adjustments, suspicious_lightweight):
    if races < 100:
        return "INSUFFICIENT_PRIOR_SAMPLE"
    risk_rate = (over_adjustments + suspicious_lightweight) / max(races, 1)
    if top1_delta >= 1.0 and top3_delta >= 0 and adjusted_better > original_better and risk_rate <= 0.25:
        return "PROMISING_RESEARCH_SIGNAL"
    if top1_delta <= -1.0 or adjusted_better < original_better * 0.8:
        return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"


def main():
    result_rows = read_csv(RESULTS)
    v6_rows = read_csv(V6)
    prior_history = build_prior_history(v6_rows)

    grouped = defaultdict(list)
    for row in result_rows:
        if parse_date(first(row, ["race_date", "date", "meeting_date"])) is None:
            continue
        if not first(row, ["horse", "horse_name", "runner_name", "horse_key"]):
            continue
        if parse_num(first(row, ["weight", "wgt", "weight_carried", "allocated_weight"])) is None:
            continue
        if finish_value(row) is None:
            continue
        grouped[race_key(row)].append(row)

    replay_races = []
    excluded = defaultdict(int)
    total_prior_runner_rows = 0
    target_rows_with_weight = 0
    target_rows_with_prior = 0

    for key, rows in grouped.items():
        if len(rows) < MIN_ELIGIBLE_RUNNERS:
            excluded["TARGET_FIELD_TOO_SMALL"] += 1
            continue
        winners = [row for row in rows if is_winner(row)]
        if len(winners) != 1:
            excluded["WINNER_NOT_UNIQUE_OR_MISSING"] += 1
            continue
        target_rows_with_weight += len(rows)
        weights = [parse_num(first(row, ["weight", "wgt", "weight_carried", "allocated_weight"])) for row in rows]
        weights = [w for w in weights if w is not None]
        if len(weights) < MIN_ELIGIBLE_RUNNERS:
            excluded["INSUFFICIENT_WEIGHT_ROWS"] += 1
            continue
        race_avg_weight = mean(weights)
        eligible = []
        target_date = parse_date(first(rows[0], ["race_date", "date", "meeting_date"]))
        for row in rows:
            prior = latest_prior(prior_history, first(row, ["horse", "horse_name", "runner_name", "horse_key"]), target_date)
            weight = parse_num(first(row, ["weight", "wgt", "weight_carried", "allocated_weight"]))
            if prior is None or weight is None:
                continue
            prior_date, prior_rating, prior_row = prior
            item = dict(row)
            item["prior_rating"] = prior_rating
            item["prior_rating_date"] = prior_date.isoformat()
            item["days_since_prior_rating"] = (target_date - prior_date).days if target_date and prior_date else ""
            item["carried_weight_kg"] = weight
            item["race_avg_weight_kg"] = race_avg_weight
            item["weight_delta_vs_avg_kg"] = weight - race_avg_weight
            eligible.append(item)
        target_rows_with_prior += len(eligible)
        if len(eligible) < MIN_ELIGIBLE_RUNNERS:
            excluded["INSUFFICIENT_PRIOR_RATED_RUNNERS"] += 1
            continue
        winner_key = norm_horse(first(winners[0], ["horse", "horse_name", "runner_name", "horse_key"]))
        winner_eligible = [row for row in eligible if norm_horse(first(row, ["horse", "horse_name", "runner_name", "horse_key"])) == winner_key]
        if not winner_eligible:
            excluded["WINNER_NOT_PRIOR_RATED"] += 1
            continue
        replay_races.append((key, eligible, winner_eligible[0]))
        total_prior_runner_rows += len(eligible)

    output_rows = []
    summary_rows = []
    original_cache = {}
    original_top1_wins = 0
    original_top3_wins = 0
    original_place_proxy = 0
    for key, rows, winner in replay_races:
        for row in rows:
            row["original_prior_rating"] = row["prior_rating"]
        ranked, ranks = rank_rows(rows, "original_prior_rating")
        top = ranked[0]
        top3 = ranked[:3]
        original_cache[key] = (ranked, ranks, top, top3)
        original_top1_wins += 1 if is_winner(top) else 0
        original_top3_wins += 1 if any(is_winner(row) for row in top3) else 0
        original_place_proxy += 1 if is_place_proxy(top) else 0

    for variant, per_kg in VARIANTS.items():
        races = len(replay_races)
        adjusted_top1_wins = 0
        adjusted_top3_wins = 0
        adjusted_place_proxy = 0
        same_top_pick = 0
        original_better = 0
        adjusted_better = 0
        both_lost = 0
        rank_movements = []
        over_adjustment_count = 0
        suspicious_lightweight_boosts = 0
        cap_hit_rows = 0

        for key, rows, winner in replay_races:
            race_over_adjust = 0
            race_light_boost = 0
            for row in rows:
                prior_rating = parse_num(row.get("prior_rating"))
                delta = parse_num(row.get("weight_delta_vs_avg_kg"))
                raw_adjustment = -delta * per_kg
                capped = max(-ADJUSTMENT_CAP, min(ADJUSTMENT_CAP, raw_adjustment))
                if abs(raw_adjustment) > ADJUSTMENT_CAP:
                    cap_hit_rows += 1
                    race_over_adjust += 1
                # Flag large lightweight boosts even if capped.
                if delta is not None and delta <= -3 and capped >= 2.5:
                    race_light_boost += 1
                row[f"adjustment_{variant}"] = capped
                row[f"adjusted_prior_rating_{variant}"] = prior_rating + capped

            original_ranked, original_ranks, original_top, original_top3 = original_cache[key]
            adjusted_ranked, adjusted_ranks = rank_rows(rows, f"adjusted_prior_rating_{variant}")
            adjusted_top = adjusted_ranked[0]
            adjusted_top3 = adjusted_ranked[:3]
            original_finish = finish_value(original_top)
            adjusted_finish = finish_value(adjusted_top)
            same_pick = norm_horse(first(original_top, ["horse", "horse_key"])) == norm_horse(first(adjusted_top, ["horse", "horse_key"]))
            same_top_pick += 1 if same_pick else 0
            adjusted_top1_wins += 1 if is_winner(adjusted_top) else 0
            adjusted_top3_wins += 1 if any(is_winner(row) for row in adjusted_top3) else 0
            adjusted_place_proxy += 1 if is_place_proxy(adjusted_top) else 0
            if original_finish is not None and adjusted_finish is not None:
                if original_finish < adjusted_finish:
                    original_better += 1
                elif adjusted_finish < original_finish:
                    adjusted_better += 1
            if not is_winner(original_top) and not is_winner(adjusted_top):
                both_lost += 1

            total_movement = 0
            max_movement = 0
            for row in rows:
                movement = abs(original_ranks[id(row)] - adjusted_ranks[id(row)])
                total_movement += movement
                max_movement = max(max_movement, movement)
                rank_movements.append(movement)
                if movement >= 5:
                    race_over_adjust += 1
            if race_over_adjust:
                over_adjustment_count += 1
            if race_light_boost:
                suspicious_lightweight_boosts += 1

            output_rows.append({
                "variant": variant,
                "kg_to_rating_points": per_kg,
                "race_key": key,
                "race_date": first(rows[0], ["race_date", "date", "meeting_date"]),
                "track": first(rows[0], ["track", "venue"]),
                "race_no": first(rows[0], ["race_no", "race", "race_number"]),
                "distance": first(rows[0], ["distance", "distance_m"]),
                "race_class": first(rows[0], ["class_name", "race_class", "race_class_clean"]),
                "eligible_runner_count": len(rows),
                "race_avg_weight_kg": fmt(parse_num(rows[0].get("race_avg_weight_kg")), 3),
                "actual_winner": first(winner, ["horse", "horse_key"]),
                "actual_winner_original_rank": original_ranks[id(winner)],
                "actual_winner_adjusted_rank": adjusted_ranks[id(winner)],
                "original_top_pick": first(original_top, ["horse", "horse_key"]),
                "original_top_pick_finish": fmt(original_finish, 0),
                "original_top_pick_prior_rating": fmt(parse_num(original_top.get("prior_rating")), 3),
                "original_top_pick_prior_rating_date": original_top.get("prior_rating_date", ""),
                "original_top_pick_weight": fmt(parse_num(original_top.get("carried_weight_kg")), 2),
                "adjusted_top_pick": first(adjusted_top, ["horse", "horse_key"]),
                "adjusted_top_pick_finish": fmt(adjusted_finish, 0),
                "adjusted_top_pick_prior_rating": fmt(parse_num(adjusted_top.get("prior_rating")), 3),
                "adjusted_top_pick_prior_rating_date": adjusted_top.get("prior_rating_date", ""),
                "adjusted_top_pick_weight": fmt(parse_num(adjusted_top.get("carried_weight_kg")), 2),
                "adjusted_top_pick_weight_delta_vs_avg_kg": fmt(parse_num(adjusted_top.get("weight_delta_vs_avg_kg")), 3),
                "adjusted_top_pick_adjustment": fmt(parse_num(adjusted_top.get(f"adjustment_{variant}")), 3),
                "adjusted_top_pick_adjusted_prior_rating": fmt(parse_num(adjusted_top.get(f"adjusted_prior_rating_{variant}")), 3),
                "original_top1_win": "YES" if is_winner(original_top) else "NO",
                "adjusted_top1_win": "YES" if is_winner(adjusted_top) else "NO",
                "original_top3_contains_winner": "YES" if any(is_winner(row) for row in original_top3) else "NO",
                "adjusted_top3_contains_winner": "YES" if any(is_winner(row) for row in adjusted_top3) else "NO",
                "same_top_pick": "YES" if same_pick else "NO",
                "original_top_pick_better": "YES" if original_finish is not None and adjusted_finish is not None and original_finish < adjusted_finish else "NO",
                "adjusted_top_pick_better": "YES" if original_finish is not None and adjusted_finish is not None and adjusted_finish < original_finish else "NO",
                "both_lost": "YES" if (not is_winner(original_top) and not is_winner(adjusted_top)) else "NO",
                "average_rank_movement": fmt(total_movement / len(rows), 4),
                "max_rank_movement": max_movement,
                "over_adjustment_flag": "YES" if race_over_adjust else "NO",
                "suspicious_lightweight_boost_flag": "YES" if race_light_boost else "NO",
                "cap_hit_or_large_move_count": race_over_adjust,
                "research_scope": "PRIOR_RATING_WEIGHT_CONTEXT_REPLAY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM",
                "production_changed": "NO",
                "pricing_changed": "NO",
                "v6_1_changed": "NO",
                "v7_2g2_changed": "NO",
                "ui_changed": "NO",
                "built_at": datetime.now(timezone.utc).isoformat(),
            })

        original_top1_pct = original_top1_wins / races * 100 if races else 0
        adjusted_top1_pct = adjusted_top1_wins / races * 100 if races else 0
        original_top3_pct = original_top3_wins / races * 100 if races else 0
        adjusted_top3_pct = adjusted_top3_wins / races * 100 if races else 0
        verdict = verdict_for_variant(
            races,
            adjusted_top1_pct - original_top1_pct,
            adjusted_top3_pct - original_top3_pct,
            adjusted_better,
            original_better,
            over_adjustment_count,
            suspicious_lightweight_boosts,
        )
        summary_rows.append({
            "variant": variant,
            "kg_to_rating_points": per_kg,
            "races_tested": races,
            "runners_tested": total_prior_runner_rows,
            "target_rows_with_weight": target_rows_with_weight,
            "target_rows_with_prior_rating": target_rows_with_prior,
            "excluded_race_groups": sum(excluded.values()),
            "original_top1_win_pct": fmt(original_top1_pct, 4),
            "adjusted_top1_win_pct": fmt(adjusted_top1_pct, 4),
            "top1_delta_pct": fmt(adjusted_top1_pct - original_top1_pct, 4),
            "original_top3_win_pct": fmt(original_top3_pct, 4),
            "adjusted_top3_win_pct": fmt(adjusted_top3_pct, 4),
            "top3_delta_pct": fmt(adjusted_top3_pct - original_top3_pct, 4),
            "original_place_proxy_pct": fmt(original_place_proxy / races * 100 if races else 0, 4),
            "adjusted_place_proxy_pct": fmt(adjusted_place_proxy / races * 100 if races else 0, 4),
            "same_top_pick_pct": fmt(same_top_pick / races * 100 if races else 0, 4),
            "original_better_count": original_better,
            "adjusted_better_count": adjusted_better,
            "both_lost_count": both_lost,
            "average_rank_movement": fmt(mean(rank_movements) if rank_movements else 0, 4),
            "max_rank_movement": max(rank_movements) if rank_movements else 0,
            "over_adjustment_count": over_adjustment_count,
            "suspicious_lightweight_boosts": suspicious_lightweight_boosts,
            "cap_hit_rows": cap_hit_rows,
            "adjustment_cap_points": ADJUSTMENT_CAP,
            "race_relative_only": "YES",
            "absolute_weight_boost_used": "NO",
            "age_fields_used": "NO",
            "sex_fields_used": "NO",
            "wfa_claim_made": "NO",
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
            "verdict": verdict,
        })

    out_fields = list(output_rows[0].keys()) if output_rows else ["variant", "race_key"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader(); writer.writerows(output_rows)

    summary_fields = list(summary_rows[0].keys()) if summary_rows else ["variant", "verdict"]
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader(); writer.writerows(summary_rows)

    best = max(summary_rows, key=lambda r: (float(r["top1_delta_pct"]), float(r["top3_delta_pct"]), int(r["adjusted_better_count"]))) if summary_rows else None
    lines = [
        "EDGEIQ_WEIGHT_CONTEXT_PRIOR_RATING_REPLAY_V1",
        f"historical_results_weight_source={RESULTS.name}",
        f"prior_rating_source={V6.name}",
        f"result_rows={len(result_rows)}",
        f"v6_rating_rows={len(v6_rows)}",
        f"target_race_groups={len(grouped)}",
        f"races_tested={len(replay_races)}",
        f"runners_tested={total_prior_runner_rows}",
        f"excluded_race_groups={sum(excluded.values())}",
        "prior_rating_rule=latest V6.1 rating with race_date strictly before target race_date",
        "adjustment=prior_rating - clamp((carried_weight_kg - race_avg_weight_kg) * kg_to_rating_points, -4, 4)",
        "race_relative_only=YES",
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
        "EXCLUDED_RACE_GROUPS",
    ]
    lines.extend([f"{k}={v}" for k, v in sorted(excluded.items())])
    lines.extend(["", "VARIANT_RESULTS"])
    for row in summary_rows:
        lines.append(
            f"{row['variant']}: races={row['races_tested']} runners={row['runners_tested']} original_top1={row['original_top1_win_pct']} adjusted_top1={row['adjusted_top1_win_pct']} top1_delta={row['top1_delta_pct']} original_top3={row['original_top3_win_pct']} adjusted_top3={row['adjusted_top3_win_pct']} same_top_pick={row['same_top_pick_pct']} original_better={row['original_better_count']} adjusted_better={row['adjusted_better_count']} over_adjustments={row['over_adjustment_count']} suspicious_lightweight_boosts={row['suspicious_lightweight_boosts']} verdict={row['verdict']}"
        )
    if best:
        lines.extend(["", f"best_variant_by_top1_delta={best['variant']}", f"best_variant_verdict={best['verdict']}"])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)

if __name__ == "__main__":
    main()


