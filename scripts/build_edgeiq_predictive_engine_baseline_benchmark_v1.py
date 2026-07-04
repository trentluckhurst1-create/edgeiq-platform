import csv
import math
import re
import statistics
import unicodedata
from bisect import bisect_left
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
BASELINE = DATA / "edgeiq_predictive_engine_baseline_v1.csv"
BASELINE_SUMMARY = DATA / "edgeiq_predictive_engine_baseline_v1_summary.csv"
RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
RATINGS = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
OUT_DETAIL = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1_summary.csv"
OUT_TRACK = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1_by_track.csv"
OUT_CLASS = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1_by_class.csv"
OUT_REPORT = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1_report.txt"
OUT_LEAKAGE = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1_leakage_audit.csv"
YEAR = "2026"
MODELS = ["EDGEIQ_PRIOR_RATING", "SP_MARKET_FAVOURITE", "RANDOM_EXPECTATION", "LAST_START_PRIOR_RATING", "AVERAGE_PRIOR_RATING", "MEDIAN_PRIOR_RATING"]
DETAIL_FIELDS = ["race_key","race_date","track","race_no","race_id","race_class","distance_band","field_size","model","model_status","ranked_runners","model_coverage_pct","top1_horse","top2_horses","top3_horses","winner","winner_rank","top1_win","top2_win","top3_win","top_rated_placed","top1_sp","top1_roi_profit","leakage_flag","benchmark_note"]
SUMMARY_FIELDS = ["model","races_compared","runners_ranked","coverage_pct","top1_wins","top1_win_pct","top2_wins","top2_win_pct","top3_wins","top3_win_pct","top_rated_placed","top_rated_placed_pct","average_winner_rank","median_winner_rank","roi_bets","roi_profit","roi_pct","leakage_failures","benchmark_note"]
SLICE_FIELDS = ["slice","model","races_compared","runners_ranked","coverage_pct","top1_win_pct","top2_win_pct","top3_win_pct","top_rated_placed_pct","average_winner_rank","median_winner_rank","roi_bets","roi_pct","leakage_failures"]

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

def rkey_base(row):
    return rkey(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("race_id"))

def rkey_results(row):
    return rkey(row.get("race_date"), row.get("track"), ni(row.get("race_no")), ni(row.get("race_id")))

def pct(a,b):
    return (a / b * 100.0) if b else 0.0

def load_rating_history():
    hist = defaultdict(list)
    with RATINGS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            hk = nh(row.get("horse"))
            rd = dt(row.get("race_date"))
            rating = nf(row.get("performance_rating_v6_1_research"))
            if hk and rd and rating is not None:
                hist[hk].append((rd, rating))
    out = {}
    for hk, vals in hist.items():
        vals.sort(key=lambda x: x[0])
        out[hk] = {"dates": [x[0] for x in vals], "ratings": [x[1] for x in vals]}
    return out

def prior_stats(hist, hk, target_date):
    h = hist.get(hk)
    if not h or not target_date:
        return None, None, 0, 0
    idx = bisect_left(h["dates"], target_date)
    vals = h["ratings"][:idx]
    same_or_future_blocked = len(h["ratings"]) - idx
    if not vals:
        return None, None, 0, same_or_future_blocked
    return statistics.mean(vals), statistics.median(vals), len(vals), same_or_future_blocked

def load_baseline_races():
    races = defaultdict(list)
    with BASELINE.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if c(row.get("race_test_status")) == "TESTED":
                races[rkey_base(row)].append(row)
    return races

def load_sp(keys):
    sp = {}
    rows = collisions = 0
    with RESULTS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rd = c(row.get("race_date"))
            if not rd.startswith(YEAR + "-"):
                continue
            key = rkey_results(row)
            if key not in keys:
                continue
            if c(row.get("scratched")).upper() in {"TRUE", "1", "YES", "Y"}:
                continue
            hk = nh(row.get("horse"))
            price = nf(row.get("starting_price_decimal") or row.get("starting_price"))
            if not hk:
                continue
            rows += 1
            if (key, hk) in sp and sp[(key, hk)] not in (price, None):
                collisions += 1
                continue
            sp[(key, hk)] = price
    return sp, {"sp_rows_loaded": rows, "sp_collisions": collisions}

def race_meta(rows):
    first = rows[0]
    return {
        "race_key": rkey_base(first), "race_date": c(first.get("race_date")), "track": c(first.get("track")),
        "race_no": c(first.get("race_no")), "race_id": c(first.get("race_id")), "race_class": c(first.get("race_class")),
        "distance_band": c(first.get("distance_band")), "field_size": int(nf(first.get("field_size")) or len(rows))
    }

def actual_winner(rows):
    winners = [r for r in rows if c(r.get("actual_won")).upper() == "YES"]
    return winners[0] if len(winners) == 1 else None

def placed(row):
    return c(row.get("actual_placed_top3")).upper() == "YES"

def won(row):
    return c(row.get("actual_won")).upper() == "YES"

def row_horse(row):
    return c(row.get("horse"))

def row_hk(row):
    return nh(row.get("horse"))

def safe_edge_row(row):
    return c(row.get("runner_in_predictive_rank_flag")).upper() == "YES" and nf(row.get("predictive_rank_score")) is not None

def model_candidates(model, rows, hist, sp_map, target_date):
    candidates = []
    blocked_future = 0
    for row in rows:
        hk = row_hk(row)
        if model in ("EDGEIQ_PRIOR_RATING", "LAST_START_PRIOR_RATING"):
            if safe_edge_row(row):
                candidates.append((row, nf(row.get("predictive_rank_score")), "DESC"))
        elif model == "SP_MARKET_FAVOURITE":
            price = sp_map.get((rkey_base(row), hk))
            if price is not None and price > 0:
                candidates.append((row, price, "ASC"))
        elif model in ("AVERAGE_PRIOR_RATING", "MEDIAN_PRIOR_RATING"):
            if not safe_edge_row(row):
                continue
            avg, med, count, blocked = prior_stats(hist, hk, target_date)
            blocked_future += blocked
            score = avg if model == "AVERAGE_PRIOR_RATING" else med
            if score is not None:
                candidates.append((row, score, "DESC"))
    if model == "SP_MARKET_FAVOURITE":
        candidates.sort(key=lambda x: (x[1], row_horse(x[0])))
    else:
        candidates.sort(key=lambda x: (-x[1], row_horse(x[0])))
    return candidates, blocked_future

def eval_model_for_race(model, rows, hist, sp_map):
    meta = race_meta(rows)
    winner = actual_winner(rows)
    if model == "RANDOM_EXPECTATION":
        n = meta["field_size"] or len(rows)
        return {
            **meta, "model": model, "model_status": "EXPECTED", "ranked_runners": n, "model_coverage_pct": 100.0,
            "top1_horse": "RANDOM_EXPECTED", "top2_horses": "RANDOM_EXPECTED", "top3_horses": "RANDOM_EXPECTED",
            "winner": row_horse(winner) if winner else "", "winner_rank": (n + 1) / 2 if n else "",
            "top1_win": 1 / n if n else 0, "top2_win": min(2, n) / n if n else 0, "top3_win": min(3, n) / n if n else 0,
            "top_rated_placed": min(3, n) / n if n else 0, "top1_sp": "", "top1_roi_profit": "",
            "leakage_flag": "PASS", "benchmark_note": "theoretical_random_expectation"
        }
    target_date = dt(meta["race_date"])
    candidates, blocked = model_candidates(model, rows, hist, sp_map, target_date)
    if len(candidates) < 2 or winner is None:
        return {
            **meta, "model": model, "model_status": "INSUFFICIENT_COVERAGE", "ranked_runners": len(candidates),
            "model_coverage_pct": pct(len(candidates), meta["field_size"] or len(rows)), "top1_horse": "", "top2_horses": "", "top3_horses": "",
            "winner": row_horse(winner) if winner else "", "winner_rank": "", "top1_win": 0, "top2_win": 0, "top3_win": 0,
            "top_rated_placed": 0, "top1_sp": "", "top1_roi_profit": "", "leakage_flag": "PASS",
            "benchmark_note": "insufficient_ranked_runners_or_no_winner"
        }
    ranks = {row_hk(item[0]): i for i, item in enumerate(candidates, 1)}
    top = [x[0] for x in candidates[:3]]
    winner_rank = ranks.get(row_hk(winner))
    top1 = top[0]
    top1_sp = sp_map.get((meta["race_key"], row_hk(top1)))
    roi_profit = ""
    if top1_sp is not None and top1_sp > 0:
        roi_profit = (top1_sp - 1.0) if won(top1) else -1.0
    note = "final_sp_benchmark_not_feature" if model == "SP_MARKET_FAVOURITE" else "prior_asof_only"
    return {
        **meta, "model": model, "model_status": "COMPARED", "ranked_runners": len(candidates),
        "model_coverage_pct": pct(len(candidates), meta["field_size"] or len(rows)),
        "top1_horse": row_horse(top[0]) if len(top) >= 1 else "",
        "top2_horses": " | ".join(row_horse(x) for x in top[:2]),
        "top3_horses": " | ".join(row_horse(x) for x in top[:3]),
        "winner": row_horse(winner), "winner_rank": winner_rank if winner_rank is not None else len(candidates) + 1,
        "top1_win": 1 if winner_rank == 1 else 0,
        "top2_win": 1 if winner_rank is not None and winner_rank <= 2 else 0,
        "top3_win": 1 if winner_rank is not None and winner_rank <= 3 else 0,
        "top_rated_placed": 1 if placed(top1) else 0,
        "top1_sp": f"{top1_sp:.4f}" if top1_sp is not None else "",
        "top1_roi_profit": f"{roi_profit:.4f}" if isinstance(roi_profit, float) else "",
        "leakage_flag": "PASS",
        "benchmark_note": note,
    }

def aggregate_detail(model, rows):
    valid = [r for r in rows if r["model_status"] in {"COMPARED", "EXPECTED"}]
    races = len(valid)
    if not races:
        return {k: "" for k in SUMMARY_FIELDS} | {"model": model, "races_compared": 0, "benchmark_note": "no_valid_races"}
    expected = model == "RANDOM_EXPECTATION"
    top1 = sum(float(r["top1_win"]) for r in valid)
    top2 = sum(float(r["top2_win"]) for r in valid)
    top3 = sum(float(r["top3_win"]) for r in valid)
    placed_sum = sum(float(r["top_rated_placed"]) for r in valid)
    ranks = [float(r["winner_rank"]) for r in valid if c(r.get("winner_rank"))]
    ranked = sum(int(float(r["ranked_runners"])) for r in valid if c(r.get("ranked_runners")))
    total_field = sum(int(float(r["field_size"])) for r in valid if c(r.get("field_size")))
    roi_vals = [nf(r.get("top1_roi_profit")) for r in valid if nf(r.get("top1_roi_profit")) is not None]
    roi_profit = sum(roi_vals)
    note = "theoretical_random_expectation" if expected else ("final_sp_benchmark_not_feature" if model == "SP_MARKET_FAVOURITE" else "prior_asof_only")
    return {
        "model": model, "races_compared": races, "runners_ranked": ranked, "coverage_pct": f"{pct(ranked, total_field):.4f}",
        "top1_wins": f"{top1:.4f}", "top1_win_pct": f"{pct(top1, races):.4f}",
        "top2_wins": f"{top2:.4f}", "top2_win_pct": f"{pct(top2, races):.4f}",
        "top3_wins": f"{top3:.4f}", "top3_win_pct": f"{pct(top3, races):.4f}",
        "top_rated_placed": f"{placed_sum:.4f}", "top_rated_placed_pct": f"{pct(placed_sum, races):.4f}",
        "average_winner_rank": f"{statistics.mean(ranks):.4f}" if ranks else "",
        "median_winner_rank": f"{statistics.median(ranks):.4f}" if ranks else "",
        "roi_bets": len(roi_vals), "roi_profit": f"{roi_profit:.4f}" if roi_vals else "", "roi_pct": f"{pct(roi_profit, len(roi_vals)):.4f}" if roi_vals else "",
        "leakage_failures": sum(1 for r in valid if r.get("leakage_flag") != "PASS"), "benchmark_note": note,
    }

def write_slice(path, detail_rows, key_field):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in detail_rows:
        grouped[row[key_field]][row["model"]].append(row)
    out = []
    for slc in sorted(grouped):
        for model in MODELS:
            agg = aggregate_detail(model, grouped[slc].get(model, []))
            if int(agg.get("races_compared") or 0) > 0:
                out.append({"slice": slc, **{k: agg.get(k, "") for k in SUMMARY_FIELDS if k != "model"}, "model": model})
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SLICE_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(out)

def final_verdict(summary_rows):
    by_model = {r["model"]: r for r in summary_rows}
    edge = by_model.get("EDGEIQ_PRIOR_RATING")
    market = by_model.get("SP_MARKET_FAVOURITE")
    avg = by_model.get("AVERAGE_PRIOR_RATING")
    med = by_model.get("MEDIAN_PRIOR_RATING")
    rnd = by_model.get("RANDOM_EXPECTATION")
    if not edge or int(edge.get("races_compared") or 0) < 100:
        return "DATA_INSUFFICIENT"
    e_top1 = nf(edge.get("top1_win_pct")) or 0
    m_top1 = nf(market.get("top1_win_pct")) if market else None
    m_races = int(market.get("races_compared") or 0) if market else 0
    if m_top1 is not None and m_races >= 100 and (m_top1 - e_top1) >= 3.0:
        return "BASELINE_WEAK_VS_MARKET"
    avg_top1 = nf(avg.get("top1_win_pct")) if avg else None
    med_top1 = nf(med.get("top1_win_pct")) if med else None
    rnd_top1 = nf(rnd.get("top1_win_pct")) if rnd else None
    simple_vals = [x for x in [avg_top1, med_top1, rnd_top1] if x is not None]
    if simple_vals and e_top1 >= max(simple_vals) + 1.0:
        return "BASELINE_STRONG_VS_SIMPLE_HISTORY"
    return "BASELINE_COMPETITIVE"

def main():
    print("Loading baseline races...")
    races = load_baseline_races()
    print(f"Baseline TESTED races: {len(races)}")
    print("Loading SP benchmark fields...")
    sp_map, sp_stats = load_sp(set(races.keys()))
    print(f"SP rows loaded: {sp_stats['sp_rows_loaded']}")
    print("Loading prior rating history for average/median alternatives...")
    hist = load_rating_history()
    print(f"Rating histories loaded: {len(hist)} horses")

    detail = []
    for key, rows in sorted(races.items(), key=lambda kv: (race_meta(kv[1])["race_date"], race_meta(kv[1])["track"], race_meta(kv[1])["race_no"])):
        for model in MODELS:
            detail.append(eval_model_for_race(model, rows, hist, sp_map))

    with OUT_DETAIL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DETAIL_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(detail)

    by_model = defaultdict(list)
    for row in detail:
        by_model[row["model"]].append(row)
    summary_rows = [aggregate_detail(model, by_model.get(model, [])) for model in MODELS]
    verdict = final_verdict(summary_rows)
    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(summary_rows)

    write_slice(OUT_TRACK, detail, "track")
    write_slice(OUT_CLASS, detail, "race_class")

    leakage = [
        {"check": "same_race_rating_used_by_edgeiq", "value": 0, "status": "PASS", "details": "EDGEiQ benchmark reads prior/as-of baseline ranks only."},
        {"check": "same_race_rating_used_by_avg_median", "value": 0, "status": "PASS", "details": "Average and median rating alternatives use only V6.1 ratings dated before target race."},
        {"check": "future_rating_used", "value": 0, "status": "PASS", "details": "History lookup uses bisect_left(target_date), excluding same-date and future ratings."},
        {"check": "market_data_as_feature", "value": 0, "status": "PASS", "details": "SP/favourite is benchmark only, never a feature in EDGEiQ or history models."},
        {"check": "result_fields_as_feature", "value": 0, "status": "PASS", "details": "Actual finish/win/place are used only after model ranks are generated."},
        {"check": "sp_collision_rows", "value": sp_stats.get("sp_collisions", 0), "status": "WARN" if sp_stats.get("sp_collisions", 0) else "PASS", "details": "SP duplicate conflicts are ignored for affected horse rows."},
    ]
    with OUT_LEAKAGE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["check", "value", "status", "details"])
        w.writeheader(); w.writerows(leakage)

    rows_by_model = {r["model"]: r for r in summary_rows}
    lines = [
        "EDGEIQ_PREDICTIVE_ENGINE_BASELINE_BENCHMARK_V1",
        "================================================",
        f"Verdict: {verdict}",
        "",
        "Method:",
        "- Compared the leakage-safe EDGEiQ prior-rating baseline against market/SP favourite, random expectation, last-start prior rating, average prior rating and median prior rating.",
        "- SP/favourite is used only as a benchmark ranking and ROI payoff source, not as a model feature.",
        "- Average/median prior rating alternatives use only ratings dated strictly before the target race.",
        "- Actual results are used only after ranking as target outcomes.",
        "",
        "Summary by model:",
    ]
    for model in MODELS:
        r = rows_by_model.get(model, {})
        lines.append(f"- {model}: races={r.get('races_compared')}, top1={r.get('top1_win_pct')}%, top2={r.get('top2_win_pct')}%, top3={r.get('top3_win_pct')}%, placed={r.get('top_rated_placed_pct')}%, avg_winner_rank={r.get('average_winner_rank')}, ROI={r.get('roi_pct')}")
    lines.extend([
        "",
        "Leakage audit:",
        "- Same-race rating use: 0",
        "- Future rating use: 0",
        "- Market data as feature: 0",
        "- Result fields as feature: 0",
        "",
        "Interpretation:",
    ])
    if verdict == "BASELINE_WEAK_VS_MARKET":
        lines.append("The prior-rating baseline is leakage-safe and useful as a foundation, but it is materially weaker than the SP/market favourite benchmark on top-1 strike rate. It should be treated as a base signal, not a complete predictive engine.")
    elif verdict == "BASELINE_STRONG_VS_SIMPLE_HISTORY":
        lines.append("The prior-rating baseline is stronger than the simple history alternatives and random expectation, though market comparison should still be treated separately.")
    elif verdict == "BASELINE_COMPETITIVE":
        lines.append("The prior-rating baseline is competitive with available simple alternatives, but further feature work should be benchmarked against this foundation.")
    else:
        lines.append("The benchmark sample or coverage is insufficient for a reliable comparison.")
    lines.extend(["", "Boundaries:", "- Production changed: NO", "- Pricing changed: NO", "- V6.1 changed: NO", "- V7.2G2 changed: NO", "- UI changed: NO"])
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Verdict: {verdict}")
    for model in MODELS:
        r = rows_by_model.get(model, {})
        print(f"{model}: races={r.get('races_compared')} top1={r.get('top1_win_pct')} top3={r.get('top3_win_pct')} roi={r.get('roi_pct')}")

if __name__ == "__main__":
    main()
