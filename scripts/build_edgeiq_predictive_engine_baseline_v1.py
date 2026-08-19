import csv
import math
import re
import statistics
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SPINE_PATH = DATA / "edgeiq_prior_asof_rating_spine_v1.csv"
FOCUS_PATH = DATA / "edgeiq_prior_asof_rating_spine_v1_2026_focus_audit.csv"
RESULTS_PATH = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
OUT_BASELINE = DATA / "edgeiq_predictive_engine_baseline_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_predictive_engine_baseline_v1_summary.csv"
OUT_TRACK = DATA / "edgeiq_predictive_engine_baseline_v1_by_track.csv"
OUT_CLASS = DATA / "edgeiq_predictive_engine_baseline_v1_by_class.csv"
OUT_DISTANCE = DATA / "edgeiq_predictive_engine_baseline_v1_by_distance.csv"
OUT_FIELD = DATA / "edgeiq_predictive_engine_baseline_v1_by_field_size.csv"
OUT_LEAKAGE = DATA / "edgeiq_predictive_engine_baseline_v1_leakage_audit.csv"
OUT_REPORT = DATA / "edgeiq_predictive_engine_baseline_v1_report.txt"
YEAR = "2026"
GATE = 80.0

BASE_FIELDS = [
    "race_date","track","race_no","race_id","race_name","race_class","distance_m","distance_band","field_size",
    "focus_coverage_pct","effective_eligible_coverage_pct","coverage_status","coverage_bucket","horse","horse_code",
    "runner_id","barrier","prior_v6_1_rating","prior_rating_date","days_since_prior_rating","prior_rating_quality_flag",
    "ambiguous_prior_rating_flag","predictive_rank","predictive_rank_score","actual_finish","actual_won","actual_placed_top3",
    "runner_in_predictive_rank_flag","runner_exclusion_reason","race_test_status","race_winner","winner_predictive_rank",
    "top1_horse","top2_horses","top3_horses","top1_won_flag","top2_won_flag","top3_won_flag","top_rated_placed_flag"
]
SLICE_FIELDS = [
    "slice","races_tested","runners_tested","avg_focus_coverage_pct","avg_effective_coverage_pct",
    "full_field_coverage_races","partial_field_coverage_races","top1_wins","top1_win_pct","top2_wins","top2_win_pct",
    "top3_wins","top3_win_pct","top_rated_placed","top_rated_placed_pct","average_winner_rank","median_winner_rank",
    "rank1_starts","rank1_wins","rank1_strike_pct","rank2_starts","rank2_wins","rank2_strike_pct",
    "rank3_starts","rank3_wins","rank3_strike_pct","winner_missing_prior_rating_races"
]

def c(v):
    return "" if v is None else str(v).strip()

def nf(v):
    t = c(v)
    if not t:
        return None
    t = re.sub(r"[^0-9.\-]", "", t)
    if t in ("", ".", "-", "-."):
        return None
    try:
        x = float(t)
        return None if math.isnan(x) or math.isinf(x) else x
    except ValueError:
        return None

def ni(v):
    x = nf(v)
    return "" if x is None else str(int(round(x)))

def dt(v):
    t = c(v)[:10]
    if not t:
        return None
    try:
        return datetime.strptime(t, "%Y-%m-%d").date()
    except ValueError:
        return None

def nh(v):
    t = c(v).upper().replace("�", " ").replace("’", "'").replace("`", "'")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\([^)]{1,5}\)", " ", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def rkey(date, track, race_no, race_id):
    return "|".join([c(date), c(track), c(race_no), c(race_id)])

def rkey_spine(row):
    return rkey(row.get("target_race_date"), row.get("track"), row.get("race_no"), row.get("race_id"))

def rkey_results(row):
    return rkey(row.get("race_date"), row.get("track"), ni(row.get("race_no")), ni(row.get("race_id")))

def cov_bucket(p):
    if p >= 100: return "FULL_100"
    if p >= 95: return "VERY_HIGH_95_99"
    if p >= 90: return "HIGH_90_94"
    if p >= 80: return "GATED_80_89"
    return "BELOW_GATE"

def fs_bucket(n):
    try:
        n = int(n)
    except Exception:
        return "UNKNOWN"
    if n <= 7: return "SMALL_1_7"
    if n <= 10: return "MEDIUM_8_10"
    if n <= 14: return "LARGE_11_14"
    return "VERY_LARGE_15_PLUS"

def pct(a, b):
    return (a / b * 100.0) if b else 0.0

def load_focus():
    all_races, gated, trials, below = {}, {}, set(), set()
    with FOCUS_PATH.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not c(row.get("race_date")).startswith(YEAR + "-"):
                continue
            key = c(row.get("race_key")) or rkey(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("race_id"))
            cov = nf(row.get("coverage_pct")) or 0.0
            cls = c(row.get("race_class")) or "UNKNOWN"
            item = {
                "race_key": key, "race_date": c(row.get("race_date")), "track": c(row.get("track")),
                "race_no": c(row.get("race_no")), "race_id": c(row.get("race_id")), "race_name": c(row.get("race_name")),
                "race_class": cls, "distance_m": c(row.get("distance_m")), "distance_band": c(row.get("distance_band")) or "UNKNOWN",
                "field_size": int(nf(row.get("field_size")) or 0), "coverage_pct": cov,
                "coverage_status": c(row.get("coverage_status"))
            }
            all_races[key] = item
            if "TRIAL" in cls.upper():
                trials.add(key)
            elif cov >= GATE:
                gated[key] = item
            else:
                below.add(key)
    return all_races, gated, trials, below

def load_outcomes(keys):
    outcomes = defaultdict(list)
    winners = defaultdict(list)
    stats = Counter()
    with RESULTS_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rd = c(row.get("race_date"))
            if not rd.startswith(YEAR + "-"):
                continue
            key = rkey_results(row)
            if key not in keys:
                continue
            if c(row.get("scratched")).upper() in {"TRUE", "1", "YES", "Y"}:
                continue
            stats["outcome_rows_scanned"] += 1
            hk = nh(row.get("horse"))
            if not hk:
                continue
            fin = nf(row.get("finish_num") or row.get("finish") or row.get("finish_abv"))
            won = c(row.get("won")).upper() in {"TRUE", "1", "YES", "Y"} or fin == 1
            placed = c(row.get("placed")).upper() in {"TRUE", "1", "YES", "Y"} or (fin is not None and fin <= 3)
            out = {"horse": c(row.get("horse")), "horse_key": hk, "finish": int(fin) if fin is not None else None, "won": won, "placed": placed}
            if outcomes[(key, hk)]:
                old = outcomes[(key, hk)][0]
                if old.get("finish") != out.get("finish") or old.get("won") != out.get("won"):
                    stats["outcome_collisions"] += 1
            outcomes[(key, hk)].append(out)
            if won:
                winners[key].append(out)
            stats["outcome_rows_loaded"] += 1
    return outcomes, winners, stats

def load_spine(keys):
    races = defaultdict(list)
    seen = 0
    with SPINE_PATH.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if c(row.get("target_year")) != YEAR:
                continue
            key = rkey_spine(row)
            if key in keys:
                races[key].append(row)
                seen += 1
    return races, seen

def safe_runner(row):
    if c(row.get("prior_rating_available_flag")).upper() != "YES":
        return False, "MISSING_PRIOR_RATING"
    if c(row.get("safe_predictive_spine_flag")).upper() != "YES":
        return False, "UNSAFE_SPINE_FLAG"
    if c(row.get("ambiguous_prior_rating_flag")).upper() == "YES":
        return False, "AMBIGUOUS_PRIOR_RATING_QUARANTINED"
    rating = nf(row.get("prior_v6_1_rating"))
    if rating is None:
        return False, "MISSING_PRIOR_RATING_VALUE"
    target = dt(row.get("target_race_date"))
    prior = dt(row.get("prior_rating_date"))
    if target is None or prior is None:
        return False, "BAD_DATE"
    if prior >= target:
        return False, "BAD_PRIOR_DATE"
    return True, "OK"

def aggregate(name, evals):
    races = len(evals)
    runners = sum(x["runners_tested"] for x in evals)
    top1 = sum(1 for x in evals if x["top1"])
    top2 = sum(1 for x in evals if x["top2"])
    top3 = sum(1 for x in evals if x["top3"])
    placed = sum(1 for x in evals if x["top_placed"])
    full = sum(1 for x in evals if x["coverage_status"] == "FULL_FIELD_PRIOR_COVERAGE")
    ranks = [x["winner_rank_summary"] for x in evals if x.get("winner_rank_summary") is not None]
    rs = {1: [0, 0], 2: [0, 0], 3: [0, 0]}
    for x in evals:
        for rank in (1, 2, 3):
            if x["rank_starts"].get(rank, 0):
                rs[rank][0] += 1
                rs[rank][1] += x["rank_wins"].get(rank, 0)
    avg_focus = statistics.mean([x["focus_cov"] for x in evals]) if evals else 0.0
    avg_eff = statistics.mean([x["eff_cov"] for x in evals]) if evals else 0.0
    avg_rank = statistics.mean(ranks) if ranks else None
    med_rank = statistics.median(ranks) if ranks else None
    missing_winner = sum(1 for x in evals if x.get("winner_missing_prior"))
    return {
        "slice": name, "races_tested": races, "runners_tested": runners,
        "avg_focus_coverage_pct": f"{avg_focus:.4f}", "avg_effective_coverage_pct": f"{avg_eff:.4f}",
        "full_field_coverage_races": full, "partial_field_coverage_races": races - full,
        "top1_wins": top1, "top1_win_pct": f"{pct(top1, races):.4f}",
        "top2_wins": top2, "top2_win_pct": f"{pct(top2, races):.4f}",
        "top3_wins": top3, "top3_win_pct": f"{pct(top3, races):.4f}",
        "top_rated_placed": placed, "top_rated_placed_pct": f"{pct(placed, races):.4f}",
        "average_winner_rank": f"{avg_rank:.4f}" if avg_rank is not None else "",
        "median_winner_rank": f"{med_rank:.4f}" if med_rank is not None else "",
        "rank1_starts": rs[1][0], "rank1_wins": rs[1][1], "rank1_strike_pct": f"{pct(rs[1][1], rs[1][0]):.4f}",
        "rank2_starts": rs[2][0], "rank2_wins": rs[2][1], "rank2_strike_pct": f"{pct(rs[2][1], rs[2][0]):.4f}",
        "rank3_starts": rs[3][0], "rank3_wins": rs[3][1], "rank3_strike_pct": f"{pct(rs[3][1], rs[3][0]):.4f}",
        "winner_missing_prior_rating_races": missing_winner,
    }

def main():
    all_2026, gated, trials, below = load_focus()
    outcomes, winners, outcome_stats = load_outcomes(set(gated.keys()))
    races, spine_seen = load_spine(set(gated.keys()))

    baseline_rows = []
    evals = []
    by_track, by_class, by_dist, by_field, by_cov = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    excluded_races, excluded_runners = Counter(), Counter()
    same_race_use = future_use = bad_prior_ranked = result_feature_use = 0

    for key, focus in sorted(gated.items(), key=lambda kv: (kv[1]["race_date"], kv[1]["track"], kv[1]["race_no"], kv[1]["race_id"])):
        rows = races.get(key, [])
        if not rows:
            excluded_races["NO_SPINE_ROWS_FOR_GATED_RACE"] += 1
            continue

        ranked = []
        infos = []
        for row in rows:
            ok, reason = safe_runner(row)
            hk = nh(row.get("horse"))
            out_list = outcomes.get((key, hk), [])
            out = out_list[0] if out_list else None
            if len(out_list) > 1:
                ok, reason = False, "OUTCOME_COLLISION_QUARANTINED"
            target, prior = dt(row.get("target_race_date")), dt(row.get("prior_rating_date"))
            if prior and target:
                if prior == target:
                    same_race_use += 1
                if prior > target:
                    future_use += 1
                if ok and prior >= target:
                    bad_prior_ranked += 1
            if ok:
                ranked.append({"row": row, "horse_key": hk, "rating": nf(row.get("prior_v6_1_rating")), "outcome": out})
            else:
                excluded_runners[reason] += 1
            infos.append({"row": row, "ok": ok, "reason": reason, "horse_key": hk, "outcome": out})

        field_size = focus["field_size"] or len(rows)
        eff_cov = pct(len(ranked), field_size)
        if eff_cov < GATE:
            status = "EXCLUDED_EFFECTIVE_COVERAGE_BELOW_80_AFTER_QUARANTINE"
            excluded_races[status] += 1
        else:
            race_winners = winners.get(key, [])
            if not race_winners:
                status = "EXCLUDED_NO_ACTUAL_WINNER_FOUND"
                excluded_races[status] += 1
            elif len(race_winners) > 1:
                status = "EXCLUDED_MULTIPLE_WINNERS_FOUND"
                excluded_races[status] += 1
            elif len(ranked) < 2:
                status = "EXCLUDED_TOO_FEW_RANKED_RUNNERS"
                excluded_races[status] += 1
            else:
                status = "TESTED"

        ranked.sort(key=lambda x: (-(x["rating"] if x["rating"] is not None else -99999), c(x["row"].get("horse"))))
        rank_by_horse = {}
        top_horses = []
        rank_starts = {1: 0, 2: 0, 3: 0}
        rank_wins = {1: 0, 2: 0, 3: 0}
        for i, item in enumerate(ranked, 1):
            rank_by_horse[item["horse_key"]] = i
            if i <= 3:
                top_horses.append(c(item["row"].get("horse")))
                rank_starts[i] = 1
                if item.get("outcome") and item["outcome"].get("won"):
                    rank_wins[i] = 1

        winner = winners.get(key, [None])[0] if winners.get(key) else None
        winner_key = winner.get("horse_key") if winner else ""
        winner_rank = rank_by_horse.get(winner_key)
        winner_missing = bool(winner and winner_rank is None)
        top1 = winner_rank == 1
        top2 = winner_rank is not None and winner_rank <= 2
        top3 = winner_rank is not None and winner_rank <= 3
        top_item = ranked[0] if ranked else None
        top_placed = bool(top_item and top_item.get("outcome") and top_item["outcome"].get("placed"))
        winner_rank_summary = winner_rank if winner_rank is not None else (len(ranked) + 1 if winner else None)
        top1_horse = top_horses[0] if top_horses else ""
        top2_horses = " | ".join(top_horses[:2])
        top3_horses = " | ".join(top_horses[:3])

        if status == "TESTED":
            ev = {
                "race_key": key, "track": focus["track"], "race_class": focus["race_class"], "distance_band": focus["distance_band"],
                "field_bucket": fs_bucket(field_size), "coverage_bucket": cov_bucket(focus["coverage_pct"]),
                "coverage_status": focus["coverage_status"], "focus_cov": focus["coverage_pct"], "eff_cov": eff_cov,
                "runners_tested": len(ranked), "top1": top1, "top2": top2, "top3": top3, "top_placed": top_placed,
                "winner_rank_summary": winner_rank_summary, "winner_missing_prior": winner_missing,
                "rank_starts": rank_starts, "rank_wins": rank_wins,
            }
            evals.append(ev)
            by_track[focus["track"]].append(ev)
            by_class[focus["race_class"]].append(ev)
            by_dist[focus["distance_band"]].append(ev)
            by_field[fs_bucket(field_size)].append(ev)
            by_cov[cov_bucket(focus["coverage_pct"])].append(ev)

        for info in infos:
            row, out = info["row"], info.get("outcome")
            rating = nf(row.get("prior_v6_1_rating"))
            rank = rank_by_horse.get(info["horse_key"], "") if info["ok"] else ""
            baseline_rows.append({
                "race_date": focus["race_date"], "track": focus["track"], "race_no": focus["race_no"], "race_id": focus["race_id"],
                "race_name": focus["race_name"], "race_class": focus["race_class"], "distance_m": focus["distance_m"],
                "distance_band": focus["distance_band"], "field_size": field_size, "focus_coverage_pct": f"{focus['coverage_pct']:.4f}",
                "effective_eligible_coverage_pct": f"{eff_cov:.4f}", "coverage_status": focus["coverage_status"],
                "coverage_bucket": cov_bucket(focus["coverage_pct"]), "horse": c(row.get("horse")), "horse_code": c(row.get("horse_code")),
                "runner_id": c(row.get("runner_id")), "barrier": c(row.get("barrier")),
                "prior_v6_1_rating": f"{rating:.6f}" if rating is not None else "", "prior_rating_date": c(row.get("prior_rating_date")),
                "days_since_prior_rating": c(row.get("days_since_prior_rating")), "prior_rating_quality_flag": c(row.get("prior_rating_quality_flag")),
                "ambiguous_prior_rating_flag": c(row.get("ambiguous_prior_rating_flag")), "predictive_rank": rank,
                "predictive_rank_score": f"{rating:.6f}" if info["ok"] and rating is not None else "",
                "actual_finish": out.get("finish") if out else "", "actual_won": "YES" if out and out.get("won") else "NO" if out else "",
                "actual_placed_top3": "YES" if out and out.get("placed") else "NO" if out else "",
                "runner_in_predictive_rank_flag": "YES" if info["ok"] else "NO",
                "runner_exclusion_reason": "" if info["ok"] else info["reason"], "race_test_status": status,
                "race_winner": winner.get("horse") if winner else "", "winner_predictive_rank": winner_rank if winner_rank is not None else "",
                "top1_horse": top1_horse, "top2_horses": top2_horses, "top3_horses": top3_horses,
                "top1_won_flag": "YES" if top1 else "NO" if status == "TESTED" else "",
                "top2_won_flag": "YES" if top2 else "NO" if status == "TESTED" else "",
                "top3_won_flag": "YES" if top3 else "NO" if status == "TESTED" else "",
                "top_rated_placed_flag": "YES" if top_placed else "NO" if status == "TESTED" else "",
            })

    with OUT_BASELINE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BASE_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(baseline_rows)

    overall = aggregate("ALL_TESTED", evals)

    def write_slice(path, groups):
        rows = [aggregate(name, vals) for name, vals in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SLICE_FIELDS, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
        return rows

    write_slice(OUT_TRACK, by_track)
    write_slice(OUT_CLASS, by_class)
    write_slice(OUT_DISTANCE, by_dist)
    write_slice(OUT_FIELD, by_field)

    verdict = "SAFE_BASELINE_BUILT"
    if same_race_use or future_use or bad_prior_ranked or result_feature_use:
        verdict = "LEAKAGE_RISK_BLOCKED"
    elif int(overall["races_tested"]) == 0:
        verdict = "DATA_COVERAGE_BLOCKED"
    elif int(overall["races_tested"]) < 500:
        verdict = "PARTIAL_BASELINE_BUILT"

    summary = []
    def add(sec, met, val, extra=""):
        summary.append({"section": sec, "metric": met, "value": val, "extra": extra})

    add("overall", "verdict", verdict)
    add("overall", "year", YEAR)
    add("overall", "focus_races_2026", len(all_2026))
    add("overall", "focus_races_at_80pct_plus_before_trial_quarantine", len(gated) + len([k for k in trials if all_2026.get(k, {}).get("coverage_pct", 0) >= GATE]))
    add("overall", "trials_quarantined", len(trials))
    add("overall", "below_coverage_gate_races", len(below))
    add("overall", "gated_non_trial_races_loaded", len(gated))
    add("overall", "spine_rows_loaded_for_gated_races", spine_seen)
    add("overall", "baseline_output_rows", len(baseline_rows))
    for k in ["races_tested", "runners_tested", "full_field_coverage_races", "partial_field_coverage_races", "top1_win_pct", "top2_win_pct", "top3_win_pct", "average_winner_rank", "median_winner_rank", "top_rated_placed_pct", "rank1_strike_pct", "rank2_strike_pct", "rank3_strike_pct", "winner_missing_prior_rating_races"]:
        add("overall", k, overall[k])
    for k, v in outcome_stats.items():
        add("outcome_join", k, v)
    for k, v in excluded_races.most_common():
        add("excluded_races", k, v)
    for k, v in excluded_runners.most_common():
        add("excluded_runners", k, v)
    for name, vals in sorted(by_cov.items()):
        row = aggregate(name, vals)
        add("performance_by_coverage_bucket", name, row["races_tested"], f"top1={row['top1_win_pct']}; top3={row['top3_win_pct']}; runners={row['runners_tested']}")

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["section", "metric", "value", "extra"])
        w.writeheader(); w.writerows(summary)

    leakage = [
        {"check": "same_race_rating_use", "value": same_race_use, "status": "PASS" if same_race_use == 0 else "FAIL", "details": "Predictive ranks use only prior_rating_date < target_race_date."},
        {"check": "future_rating_use", "value": future_use, "status": "PASS" if future_use == 0 else "FAIL", "details": "Future-dated ratings are not allowed into predictive ranks."},
        {"check": "bad_prior_dates", "value": bad_prior_ranked, "status": "PASS" if bad_prior_ranked == 0 else "FAIL", "details": "Rows with prior date >= target date are never ranked."},
        {"check": "result_fields_used_as_feature", "value": result_feature_use, "status": "PASS", "details": "Finish/won/placed are joined after ranking and used only as target outcomes."},
        {"check": "market_data_used_as_feature", "value": 0, "status": "PASS", "details": "No market/SP/favourite fields are used in this baseline."},
        {"check": "ambiguous_prior_rows_ranked", "value": 0, "status": "PASS", "details": "Ambiguous prior rating rows are quarantined before ranking."},
    ]
    with OUT_LEAKAGE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["check", "value", "status", "details"])
        w.writeheader(); w.writerows(leakage)

    lines = [
        "EDGEIQ_PREDICTIVE_ENGINE_BASELINE_V1",
        "====================================",
        f"Verdict: {verdict}",
        "",
        "Method:",
        f"- Used only {YEAR} races from the prior/as-of rating spine.",
        f"- Required race prior-rating coverage >= {GATE:.0f}%.",
        "- Quarantined trials, ambiguous prior ratings, missing prior ratings, and unsafe prior-date rows.",
        "- Ranked only by prior_v6_1_rating dated strictly before the target race.",
        "- Joined actual results only after ranking for target evaluation.",
        "- Market/SP data not used.",
        "",
        "Core results:",
        f"- Races tested: {overall['races_tested']}",
        f"- Runners tested: {overall['runners_tested']}",
        f"- Full-field coverage races tested: {overall['full_field_coverage_races']}",
        f"- Partial-field coverage races tested: {overall['partial_field_coverage_races']}",
        f"- Top-1 win %: {overall['top1_win_pct']}",
        f"- Top-2 win %: {overall['top2_win_pct']}",
        f"- Top-3 win %: {overall['top3_win_pct']}",
        f"- Average winner rank: {overall['average_winner_rank']}",
        f"- Median winner rank: {overall['median_winner_rank']}",
        f"- Top-rated placed %: {overall['top_rated_placed_pct']}",
        f"- Rank 1 strike %: {overall['rank1_strike_pct']}",
        f"- Rank 2 strike %: {overall['rank2_strike_pct']}",
        f"- Rank 3 strike %: {overall['rank3_strike_pct']}",
        "",
        "Exclusions:",
        f"- Trial races quarantined: {len(trials)}",
        f"- Below coverage gate races: {len(below)}",
    ]
    for k, v in excluded_races.most_common(12):
        lines.append(f"- {k}: {v}")
    lines.extend([
        "",
        "Leakage audit:",
        f"- Same-race rating use: {same_race_use}",
        f"- Future rating use: {future_use}",
        f"- Bad prior dates ranked: {bad_prior_ranked}",
        f"- Result fields used as features: {result_feature_use}",
        "",
        "Interpretation:",
    ])
    if verdict == "SAFE_BASELINE_BUILT":
        lines.append("The first leakage-safe predictive baseline is built and suitable as the foundation metric for current-window EDGEiQ predictive research under the documented gates.")
    elif verdict == "PARTIAL_BASELINE_BUILT":
        lines.append("The baseline is leakage-safe but sample size is modest after gates. Use for targeted research only.")
    elif verdict == "LEAKAGE_RISK_BLOCKED":
        lines.append("The baseline is blocked because leakage safeguards failed.")
    else:
        lines.append("The baseline is blocked by data coverage or target outcome availability.")
    lines.extend(["", "Production/pricing boundaries:", "- Production changed: NO", "- Pricing changed: NO", "- V6.1 changed: NO", "- V7.2G2 changed: NO", "- UI changed: NO"])
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Verdict: {verdict}")
    print(f"Races tested: {overall['races_tested']}")
    print(f"Runners tested: {overall['runners_tested']}")
    print(f"Top1 win pct: {overall['top1_win_pct']}")
    print(f"Top2 win pct: {overall['top2_win_pct']}")
    print(f"Top3 win pct: {overall['top3_win_pct']}")
    print(f"Leakage failures: {same_race_use + future_use + bad_prior_ranked + result_feature_use}")

if __name__ == "__main__":
    main()
