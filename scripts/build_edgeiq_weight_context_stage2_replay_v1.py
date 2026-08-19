import csv
from pathlib import Path
from collections import defaultdict
from statistics import mean, median
from datetime import datetime, timezone
import re

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
QUALITY = DATA / "edgeiq_weight_context_join_quality_v1.csv"
EXPANSION = DATA / "edgeiq_weight_context_join_expansion_v1.csv"
OUT = DATA / "edgeiq_weight_context_stage2_replay_v1.csv"
SUMMARY = DATA / "edgeiq_weight_context_stage2_replay_v1_summary.csv"
REPORT = DATA / "edgeiq_weight_context_stage2_replay_v1_report.txt"

VARIANTS = {
    "CONSERVATIVE_0_75_PER_KG": 0.75,
    "STANDARD_1_00_PER_KG": 1.00,
    "AGGRESSIVE_1_50_PER_KG": 1.50,
}
ADJUSTMENT_CAP = 4.0
MIN_FIELD_FOR_REPLAY = 3

PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined"}


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


def fmt(value, places=4):
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


def race_key(row):
    return "|".join([
        clean(row.get("race_date")),
        clean(row.get("track")).upper(),
        fmt(parse_num(row.get("distance")), 0),
        clean(row.get("race_class_clean")).upper(),
    ])


def rank_rows(rows, score_key):
    ranked = sorted(rows, key=lambda r: (-(parse_num(r.get(score_key)) or -999999), clean(r.get("horse"))))
    ranks = {}
    for idx, row in enumerate(ranked, start=1):
        ranks[id(row)] = idx
    return ranked, ranks


def finish(row):
    return parse_num(row.get("finish_position"))


def is_winner(row):
    f = finish(row)
    return f is not None and int(round(f)) == 1


def is_place_proxy(row):
    f = finish(row)
    return f is not None and 1 <= int(round(f)) <= 3


def verdict_for_variant(races, original_top1_pct, top1_delta, top3_delta, adjusted_better, original_better, suspicious_count):
    if races < 100:
        return "INSUFFICIENT_REPLAY_SAMPLE"
    # A historical source where the original top rank wins essentially every race is not a valid predictive replay.
    # It indicates post-race performance leakage rather than a pre-race rating board.
    if original_top1_pct >= 90:
        return "INSUFFICIENT_REPLAY_SAMPLE"
    if top1_delta >= 1.0 and top3_delta >= 0 and adjusted_better > original_better and suspicious_count / max(races, 1) <= 0.2:
        return "PROMISING_RESEARCH_SIGNAL"
    if top1_delta <= -1.0 or adjusted_better < original_better * 0.8:
        return "NEGATIVE_RESEARCH_SIGNAL"
    return "NEUTRAL_RESEARCH_SIGNAL"


def main():
    quality = read_csv(QUALITY)
    expansion = read_csv(EXPANSION)  # loaded to satisfy audit trace and row-count control

    stage2 = [
        dict(row) for row in quality
        if row.get("join_stage") == "STAGE_2_HORSE_DATE_DISTANCE"
        and row.get("row_quality_verdict") != "ROW_NOT_SAFE_FOR_REPLAY"
        and nonblank(row.get("carried_weight_kg"))
        and nonblank(row.get("performance_rating_v6_1_research"))
        and row.get("weight_quality") != "IMPOSSIBLE_WEIGHT"
    ]

    grouped = defaultdict(list)
    for row in stage2:
        grouped[race_key(row)].append(row)

    replay_races = []
    excluded_groups = []
    for key, rows in grouped.items():
        winners = [r for r in rows if is_winner(r)]
        ratings = [parse_num(r.get("performance_rating_v6_1_research")) for r in rows if parse_num(r.get("performance_rating_v6_1_research")) is not None]
        weights = [parse_num(r.get("carried_weight_kg")) for r in rows if parse_num(r.get("carried_weight_kg")) is not None]
        if len(rows) < MIN_FIELD_FOR_REPLAY:
            excluded_groups.append((key, "FIELD_TOO_SMALL", len(rows)))
            continue
        if len(winners) != 1:
            excluded_groups.append((key, "WINNER_NOT_UNIQUE_OR_MISSING", len(rows)))
            continue
        if len(ratings) != len(rows) or len(weights) != len(rows):
            excluded_groups.append((key, "MISSING_RATING_OR_WEIGHT", len(rows)))
            continue
        replay_races.append((key, rows, winners[0]))

    output_rows = []
    variant_stats = {}
    base_top1_wins = 0
    base_top3_wins = 0
    base_top1_places = 0

    # Original metrics are independent of variant.
    original_race_cache = {}
    for key, rows, winner in replay_races:
        original_ranked, original_ranks = rank_rows(rows, "performance_rating_v6_1_research")
        top_original = original_ranked[0]
        top3_original = original_ranked[:3]
        original_race_cache[key] = (original_ranked, original_ranks, top_original, top3_original)
        base_top1_wins += 1 if is_winner(top_original) else 0
        base_top3_wins += 1 if any(is_winner(r) for r in top3_original) else 0
        base_top1_places += 1 if is_place_proxy(top_original) else 0

    for variant, per_kg in VARIANTS.items():
        races = len(replay_races)
        adjusted_top1_wins = 0
        adjusted_top3_wins = 0
        adjusted_top1_places = 0
        same_top_pick = 0
        original_top_pick_better = 0
        adjusted_top_pick_better = 0
        both_lost = 0
        rank_movements = []
        suspicious_overadjustments = 0
        cap_hit_rows = 0
        top_pick_changed_by_cap = 0

        for key, rows, winner in replay_races:
            weights = [parse_num(r.get("carried_weight_kg")) for r in rows]
            avg_weight = mean(weights)
            race_suspicious = 0
            for row in rows:
                rating = parse_num(row.get("performance_rating_v6_1_research"))
                weight = parse_num(row.get("carried_weight_kg"))
                burden_delta = weight - avg_weight
                raw_adjustment = -burden_delta * per_kg
                capped_adjustment = max(-ADJUSTMENT_CAP, min(ADJUSTMENT_CAP, raw_adjustment))
                row[f"adjustment_{variant}"] = capped_adjustment
                row[f"adjusted_rating_{variant}"] = rating + capped_adjustment
                if abs(raw_adjustment) > ADJUSTMENT_CAP:
                    cap_hit_rows += 1
                    race_suspicious += 1

            original_ranked, original_ranks, top_original, top3_original = original_race_cache[key]
            adjusted_ranked, adjusted_ranks = rank_rows(rows, f"adjusted_rating_{variant}")
            top_adjusted = adjusted_ranked[0]
            top3_adjusted = adjusted_ranked[:3]

            adjusted_top1_wins += 1 if is_winner(top_adjusted) else 0
            adjusted_top3_wins += 1 if any(is_winner(r) for r in top3_adjusted) else 0
            adjusted_top1_places += 1 if is_place_proxy(top_adjusted) else 0
            same = clean(top_original.get("horse")) == clean(top_adjusted.get("horse"))
            same_top_pick += 1 if same else 0
            orig_finish = finish(top_original)
            adj_finish = finish(top_adjusted)
            if orig_finish is not None and adj_finish is not None:
                if orig_finish < adj_finish:
                    original_top_pick_better += 1
                elif adj_finish < orig_finish:
                    adjusted_top_pick_better += 1
            if not is_winner(top_original) and not is_winner(top_adjusted):
                both_lost += 1

            max_movement = 0
            total_movement = 0
            for row in rows:
                movement = abs(original_ranks[id(row)] - adjusted_ranks[id(row)])
                rank_movements.append(movement)
                total_movement += movement
                max_movement = max(max_movement, movement)
                if movement >= 5:
                    race_suspicious += 1
            if race_suspicious:
                suspicious_overadjustments += 1
            if not same and abs(parse_num(top_adjusted.get(f"adjustment_{variant}")) or 0) >= ADJUSTMENT_CAP:
                top_pick_changed_by_cap += 1

            output_rows.append({
                "variant": variant,
                "kg_to_rating_points": per_kg,
                "race_key": key,
                "race_date": rows[0].get("race_date", ""),
                "track": rows[0].get("track", ""),
                "distance": rows[0].get("distance", ""),
                "race_class_clean": rows[0].get("race_class_clean", ""),
                "stage2_runner_count": len(rows),
                "race_avg_weight_kg": fmt(avg_weight, 3),
                "actual_winner": winner.get("horse", ""),
                "actual_winner_original_rank": original_ranks[id(winner)],
                "actual_winner_adjusted_rank": adjusted_ranks[id(winner)],
                "original_top_pick": top_original.get("horse", ""),
                "original_top_pick_finish": fmt(orig_finish, 0),
                "original_top_pick_rating": top_original.get("performance_rating_v6_1_research", ""),
                "original_top_pick_weight": top_original.get("carried_weight_kg", ""),
                "adjusted_top_pick": top_adjusted.get("horse", ""),
                "adjusted_top_pick_finish": fmt(adj_finish, 0),
                "adjusted_top_pick_original_rating": top_adjusted.get("performance_rating_v6_1_research", ""),
                "adjusted_top_pick_weight": top_adjusted.get("carried_weight_kg", ""),
                "adjusted_top_pick_adjustment": fmt(parse_num(top_adjusted.get(f"adjustment_{variant}")), 3),
                "adjusted_top_pick_adjusted_rating": fmt(parse_num(top_adjusted.get(f"adjusted_rating_{variant}")), 3),
                "original_top1_win": "YES" if is_winner(top_original) else "NO",
                "adjusted_top1_win": "YES" if is_winner(top_adjusted) else "NO",
                "original_top3_contains_winner": "YES" if any(is_winner(r) for r in top3_original) else "NO",
                "adjusted_top3_contains_winner": "YES" if any(is_winner(r) for r in top3_adjusted) else "NO",
                "same_top_pick": "YES" if same else "NO",
                "original_top_pick_better": "YES" if orig_finish is not None and adj_finish is not None and orig_finish < adj_finish else "NO",
                "weight_context_top_pick_better": "YES" if orig_finish is not None and adj_finish is not None and adj_finish < orig_finish else "NO",
                "both_lost": "YES" if (not is_winner(top_original) and not is_winner(top_adjusted)) else "NO",
                "average_rank_movement": fmt(total_movement / len(rows), 4),
                "max_rank_movement": max_movement,
                "suspicious_overadjustment_flag": "YES" if race_suspicious else "NO",
                "cap_hit_runner_count": race_suspicious,
                "research_scope": "STAGE2_REPLAY_ONLY_NO_AGE_SEX_NO_WFA_CLAIM",
                "production_changed": "NO",
                "pricing_changed": "NO",
                "v6_1_changed": "NO",
                "v7_2g2_changed": "NO",
                "ui_changed": "NO",
                "built_at": datetime.now(timezone.utc).isoformat(),
            })

        original_top1_pct = (base_top1_wins / races * 100) if races else 0
        adjusted_top1_pct = (adjusted_top1_wins / races * 100) if races else 0
        original_top3_pct = (base_top3_wins / races * 100) if races else 0
        adjusted_top3_pct = (adjusted_top3_wins / races * 100) if races else 0
        source_leakage_flag = "YES" if original_top1_pct >= 90 else "NO"
        predictive_replay_valid = "NO_POST_RACE_RATING_LEAKAGE" if source_leakage_flag == "YES" else "YES"
        verdict = verdict_for_variant(
            races,
            original_top1_pct,
            adjusted_top1_pct - original_top1_pct,
            adjusted_top3_pct - original_top3_pct,
            adjusted_top_pick_better,
            original_top_pick_better,
            suspicious_overadjustments,
        )
        variant_stats[variant] = {
            "variant": variant,
            "kg_to_rating_points": per_kg,
            "replay_races": races,
            "stage2_runner_rows": sum(len(rows) for _, rows, _ in replay_races),
            "excluded_race_groups": len(excluded_groups),
            "original_top1_win_pct": original_top1_pct,
            "adjusted_top1_win_pct": adjusted_top1_pct,
            "top1_delta_pct": adjusted_top1_pct - original_top1_pct,
            "original_top3_win_pct": original_top3_pct,
            "adjusted_top3_win_pct": adjusted_top3_pct,
            "top3_delta_pct": adjusted_top3_pct - original_top3_pct,
            "original_top1_place_proxy_pct": (base_top1_places / races * 100) if races else 0,
            "adjusted_top1_place_proxy_pct": (adjusted_top1_places / races * 100) if races else 0,
            "same_top_pick_pct": (same_top_pick / races * 100) if races else 0,
            "original_top_pick_better_count": original_top_pick_better,
            "weight_context_top_pick_better_count": adjusted_top_pick_better,
            "both_lost_count": both_lost,
            "average_rank_movement": mean(rank_movements) if rank_movements else 0,
            "max_rank_movement": max(rank_movements) if rank_movements else 0,
            "suspicious_overadjustment_races": suspicious_overadjustments,
            "cap_hit_rows": cap_hit_rows,
            "top_pick_changed_by_cap_count": top_pick_changed_by_cap,
            "source_leakage_flag": source_leakage_flag,
            "predictive_replay_valid": predictive_replay_valid,
            "verdict": verdict,
        }

    out_fields = list(output_rows[0].keys()) if output_rows else ["variant", "race_key", "verdict"]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader(); writer.writerows(output_rows)

    summary_rows = []
    for stats in variant_stats.values():
        row = {k: (fmt(v, 4) if isinstance(v, float) else v) for k, v in stats.items()}
        row.update({
            "stage_filter": "STAGE_2_HORSE_DATE_DISTANCE_ONLY",
            "excluded_stages": "STAGE_3|STAGE_4|STAGE_5",
            "collision_rows_excluded": "YES",
            "not_safe_rows_excluded": "YES",
            "adjustment_cap_points": ADJUSTMENT_CAP,
            "race_relative_only": "YES",
            "absolute_weight_boost_used": "NO",
            "age_fields_used": "NO",
            "sex_fields_used": "NO",
            "wfa_claim_made": "NO",
            "source_leakage_flag": stats.get("source_leakage_flag", ""),
            "predictive_replay_valid": stats.get("predictive_replay_valid", ""),
            "production_changed": "NO",
            "pricing_changed": "NO",
            "v6_1_changed": "NO",
            "v7_2g2_changed": "NO",
            "ui_changed": "NO",
        })
        summary_rows.append(row)

    summary_fields = list(summary_rows[0].keys()) if summary_rows else ["variant", "verdict"]
    with SUMMARY.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader(); writer.writerows(summary_rows)

    best = max(variant_stats.values(), key=lambda s: (s["top1_delta_pct"], s["top3_delta_pct"], -s["suspicious_overadjustment_races"])) if variant_stats else None
    report_lines = [
        "EDGEIQ_WEIGHT_CONTEXT_STAGE2_REPLAY_V1",
        f"quality_rows={len(quality)}",
        f"expansion_rows={len(expansion)}",
        f"stage2_quality_rows={len(stage2)}",
        f"replay_races={len(replay_races)}",
        f"excluded_race_groups={len(excluded_groups)}",
        "stage_filter=STAGE_2_HORSE_DATE_DISTANCE_ONLY",
        "excluded_stages=STAGE_3|STAGE_4|STAGE_5",
        "collision_rows_excluded=YES",
        "not_safe_rows_excluded=YES",
        "adjustment=rating - clamp((carried_weight_kg - race_avg_weight_kg) * kg_to_rating_points, -4, 4)",
        "race_relative_only=YES",
        "absolute_weight_boost_used=NO",
        "age_fields_used=NO",
        "sex_fields_used=NO",
        "wfa_claim_made=NO",
        "predictive_replay_valid=NO_POST_RACE_RATING_LEAKAGE" if any(s.get("source_leakage_flag") == "YES" for s in variant_stats.values()) else "predictive_replay_valid=YES",
        "source_leakage_note=Original historical performance rating ranked the winner first in >=90% of eligible replay groups; treat this as post-race rating leakage, not a predictive replay.",
        "production_changed=NO",
        "pricing_changed=NO",
        "v6_1_changed=NO",
        "v7_2g2_changed=NO",
        "ui_changed=NO",
        "",
        "VARIANT_RESULTS",
    ]
    for stats in variant_stats.values():
        report_lines.append(
            f"{stats['variant']}: races={stats['replay_races']} original_top1={stats['original_top1_win_pct']:.4f} adjusted_top1={stats['adjusted_top1_win_pct']:.4f} top1_delta={stats['top1_delta_pct']:.4f} original_top3={stats['original_top3_win_pct']:.4f} adjusted_top3={stats['adjusted_top3_win_pct']:.4f} same_top_pick={stats['same_top_pick_pct']:.4f} adjusted_better={stats['weight_context_top_pick_better_count']} original_better={stats['original_top_pick_better_count']} suspicious={stats['suspicious_overadjustment_races']} predictive_valid={stats['predictive_replay_valid']} verdict={stats['verdict']}"
        )
    if best:
        report_lines.extend(["", f"best_variant_by_top1_delta={best['variant']}", f"best_variant_verdict={best['verdict']}"])
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(REPORT)

if __name__ == "__main__":
    main()
