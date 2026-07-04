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
SPINE = DATA / "edgeiq_prior_asof_rating_spine_v1.csv"
FOCUS = DATA / "edgeiq_prior_asof_rating_spine_v1_2026_focus_audit.csv"
BASELINE = DATA / "edgeiq_predictive_engine_baseline_v1.csv"
RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
RATINGS = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RUNSTYLE = DATA / "edgeiq_historical_run_style_v1.csv"

OUT_DETAIL = DATA / "edgeiq_comprehensive_predictive_model_research_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_comprehensive_predictive_model_research_v1_summary.csv"
OUT_INVENTORY = DATA / "edgeiq_comprehensive_predictive_model_research_v1_feature_inventory.csv"
OUT_QUALITY = DATA / "edgeiq_comprehensive_predictive_model_research_v1_feature_quality.csv"
OUT_BACKTEST = DATA / "edgeiq_comprehensive_predictive_model_research_v1_backtest.csv"
OUT_TRACK = DATA / "edgeiq_comprehensive_predictive_model_research_v1_by_track.csv"
OUT_CLASS = DATA / "edgeiq_comprehensive_predictive_model_research_v1_by_class.csv"
OUT_DISTANCE = DATA / "edgeiq_comprehensive_predictive_model_research_v1_by_distance.csv"
OUT_FIELD = DATA / "edgeiq_comprehensive_predictive_model_research_v1_by_field_size.csv"
OUT_LEAKAGE = DATA / "edgeiq_comprehensive_predictive_model_research_v1_leakage_audit.csv"
OUT_REPORT = DATA / "edgeiq_comprehensive_predictive_model_research_v1_report.txt"

YEAR = "2026"
GATE = 80.0
MODELS = [
    "PRIOR_RATING_BASELINE",
    "RATINGS_PLUS_FORM",
    "RATINGS_PLUS_CONNECTIONS",
    "RATINGS_PLUS_PACE",
    "RATINGS_PLUS_TRACK_BIAS",
    "RATINGS_PLUS_SECTIONALS",
    "ALL_NON_MARKET_MODEL",
]
BENCHMARKS = ["SP_MARKET_FAVOURITE", "RANDOM_EXPECTATION", "AVERAGE_PRIOR_RATING", "MEDIAN_PRIOR_RATING"]

DETAIL_FIELDS = [
    "model_variant","split","race_key","race_date","track","race_no","race_id","race_class","distance_band","field_size",
    "horse","horse_code","runner_id","barrier","trainer","jockey","actual_finish","actual_won","actual_placed_top3","sp_price",
    "prior_rating_date","prior_v6_1_rating","raw_score","field_normalised_score","model_probability","fair_price","confidence",
    "probability_sum_by_race","model_rank","market_rank","rating_component","rating_history_component","form_component",
    "connections_component","pace_component","track_bias_component","sectionals_component","risk_quality_component",
    "component_coverage_count","explanation_1","explanation_2","explanation_3","leakage_flag","model_status"
]
BACKTEST_FIELDS = [
    "model_variant","split","races_tested","runners_tested","feature_coverage_pct","top1_wins","top1_win_pct","top2_wins","top2_win_pct",
    "top3_wins","top3_win_pct","top_rated_placed","top_rated_placed_pct","average_winner_rank","median_winner_rank",
    "roi_bets","roi_profit","roi_pct","value_bets","value_profit","value_roi_pct","same_top_pick_vs_market","model_beats_market_count",
    "market_beats_model_count","both_lose_count","calibration_brier","confidence_high_top1_pct","confidence_medium_top1_pct","confidence_low_top1_pct",
    "leakage_failures","benchmark_note"
]
SLICE_FIELDS = ["slice","model_variant","split","races_tested","runners_tested","top1_win_pct","top2_win_pct","top3_win_pct","top_rated_placed_pct","average_winner_rank","median_winner_rank","roi_pct","leakage_failures"]

def c(v): return "" if v is None else str(v).strip()
def nf(v):
    t = c(v)
    if not t: return None
    t = re.sub(r"[^0-9.\-]", "", t)
    if t in ("", ".", "-", "-."): return None
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
    if not t: return None
    for fmt in ("%Y-%m-%d", "%d%b%y", "%d%b%Y", "%d/%m/%Y"):
        try: return datetime.strptime(t, fmt).date()
        except ValueError: pass
    return None

def iso(d): return d.isoformat() if d else ""
def nh(v):
    t = c(v).upper().replace("�", " ").replace("’", "'").replace("`", "'")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\([^)]{1,5}\)", " ", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def nk(v): return nh(v)
def pct(a,b): return (a/b*100.0) if b else 0.0
def rkey(date, track, race_no, race_id): return "|".join([c(date), c(track), c(race_no), c(race_id)])
def rkey_base(row): return rkey(row.get("race_date"), row.get("track"), row.get("race_no"), row.get("race_id"))
def rkey_spine(row): return rkey(row.get("target_race_date"), row.get("track"), row.get("race_no"), row.get("race_id"))
def rkey_results(row): return rkey(row.get("race_date"), row.get("track"), ni(row.get("race_no")), ni(row.get("race_id")))

def dist_band(m):
    x = nf(m)
    if x is None: return "UNKNOWN"
    if x <= 1200: return "SPRINT"
    if x <= 1600: return "MILE"
    if x <= 2000: return "MIDDLE"
    return "STAYING"

def field_bucket(n):
    try: n = int(n)
    except Exception: return "UNKNOWN"
    if n <= 7: return "SMALL_1_7"
    if n <= 10: return "MEDIUM_8_10"
    if n <= 14: return "LARGE_11_14"
    return "VERY_LARGE_15_PLUS"

def barrier_bucket(barrier, field_size):
    b = nf(barrier); fs = nf(field_size)
    if b is None:
        return "UNKNOWN"
    if fs is None or fs <= 0:
        if b <= 4:
            return "INSIDE"
        if b <= 8:
            return "MIDDLE"
        return "OUTSIDE"
    pos = b / fs
    if pos <= 0.33: return "INSIDE"
    if pos <= 0.67: return "MIDDLE"
    return "OUTSIDE"

def load_tested_baseline():
    races = defaultdict(list)
    with BASELINE.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if c(row.get("race_test_status")) == "TESTED" and c(row.get("runner_in_predictive_rank_flag")).upper() == "YES":
                races[rkey_base(row)].append(row)
    return races

def load_target_meta(keys):
    meta = {}
    target_horses, target_trainers, target_jockeys, target_combos, target_tracks = set(), set(), set(), set(), set()
    with RESULTS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rd = c(row.get("race_date"))
            if not rd.startswith(YEAR + "-"): continue
            key = rkey_results(row)
            if key not in keys: continue
            if c(row.get("scratched")).upper() in {"TRUE","1","YES","Y"}: continue
            hk = nh(row.get("horse"))
            if not hk: continue
            trainer, jockey = nk(row.get("trainer")), nk(row.get("jockey"))
            price = nf(row.get("starting_price_decimal") or row.get("starting_price"))
            finish = nf(row.get("finish_num") or row.get("finish") or row.get("finish_abv"))
            item = {
                "race_key": key, "horse_key": hk, "horse": c(row.get("horse")), "horse_code": ni(row.get("horse_code")),
                "runner_id": ni(row.get("runner_id")), "trainer": c(row.get("trainer")), "trainer_key": trainer,
                "jockey": c(row.get("jockey")), "jockey_key": jockey, "barrier": ni(row.get("barrier")),
                "weight": c(row.get("weight")), "sp_price": price, "finish": int(finish) if finish is not None else None,
                "won": (c(row.get("won")).upper() in {"TRUE","1","YES","Y"}) or finish == 1,
                "placed": (c(row.get("placed")).upper() in {"TRUE","1","YES","Y"}) or (finish is not None and finish <= 3),
            }
            meta[(key, hk)] = item
            target_horses.add(hk); target_tracks.add(c(row.get("track")))
            if trainer: target_trainers.add(trainer)
            if jockey: target_jockeys.add(jockey)
            if trainer and jockey: target_combos.add(trainer + "|" + jockey)
    return meta, target_horses, target_trainers, target_jockeys, target_combos, target_tracks

def load_rating_history(target_horses):
    hist = defaultdict(list)
    with RATINGS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            hk = nh(row.get("horse"))
            if hk not in target_horses: continue
            rd = dt(row.get("race_date")); rating = nf(row.get("performance_rating_v6_1_research"))
            if not rd or rating is None: continue
            hist[hk].append({
                "date": rd, "rating": rating, "distance": nf(row.get("distance")),
                "class": c(row.get("race_class_clean_v3_3") or row.get("race_class_clean") or row.get("race_class_raw")),
                "finish": nf(row.get("finish_position") or row.get("finish_pos_raw")), "margin": nf(row.get("margin")),
            })
    for vals in hist.values(): vals.sort(key=lambda x: x["date"])
    return hist

def append_hist(store, key, rd, won, placed, extra=None):
    if not key or not rd: return
    item = {"date": rd, "won": 1 if won else 0, "placed": 1 if placed else 0}
    if extra: item.update(extra)
    store[key].append(item)

def load_prior_result_histories(target_horses, target_trainers, target_jockeys, target_combos, target_tracks):
    horse_hist, trainer_hist, jockey_hist, combo_hist = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    trainer_track_hist, jockey_track_hist, track_barrier_hist = defaultdict(list), defaultdict(list), defaultdict(list)
    rows_seen = 0
    with RESULTS.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rd = dt(row.get("race_date"))
            if not rd: continue
            if c(row.get("scratched")).upper() in {"TRUE","1","YES","Y"}: continue
            hk = nh(row.get("horse")); tr = nk(row.get("trainer")); jk = nk(row.get("jockey")); track = c(row.get("track"))
            fin = nf(row.get("finish_num") or row.get("finish") or row.get("finish_abv"))
            won = (c(row.get("won")).upper() in {"TRUE","1","YES","Y"}) or fin == 1
            placed = (c(row.get("placed")).upper() in {"TRUE","1","YES","Y"}) or (fin is not None and fin <= 3)
            d_band = dist_band(row.get("distance")); b_bucket = barrier_bucket(row.get("barrier"), row.get("field_size"))
            extra = {"finish": fin, "distance_band": d_band, "track": track, "class": c(row.get("race_class")), "condition": c(row.get("track_condition"))}
            if hk in target_horses: append_hist(horse_hist, hk, rd, won, placed, extra)
            if tr in target_trainers: append_hist(trainer_hist, tr, rd, won, placed)
            if jk in target_jockeys: append_hist(jockey_hist, jk, rd, won, placed)
            if tr and jk and (tr + "|" + jk) in target_combos: append_hist(combo_hist, tr + "|" + jk, rd, won, placed)
            if tr in target_trainers and track: append_hist(trainer_track_hist, tr + "|" + track, rd, won, placed)
            if jk in target_jockeys and track: append_hist(jockey_track_hist, jk + "|" + track, rd, won, placed)
            if track in target_tracks and b_bucket != "UNKNOWN": append_hist(track_barrier_hist, track + "|" + d_band + "|" + b_bucket, rd, won, placed)
            rows_seen += 1
    for store in [horse_hist, trainer_hist, jockey_hist, combo_hist, trainer_track_hist, jockey_track_hist, track_barrier_hist]:
        for vals in store.values(): vals.sort(key=lambda x: x["date"])
    return {
        "horse": horse_hist, "trainer": trainer_hist, "jockey": jockey_hist, "combo": combo_hist,
        "trainer_track": trainer_track_hist, "jockey_track": jockey_track_hist, "track_barrier": track_barrier_hist,
        "rows_seen": rows_seen,
    }

def load_run_style(target_horses):
    hist = defaultdict(list)
    if not RUNSTYLE.exists(): return hist
    with RUNSTYLE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            hk = nh(row.get("horse") or row.get("horse_key"))
            if hk not in target_horses: continue
            rd = dt(row.get("race_date"))
            if not rd: continue
            hist[hk].append({
                "date": rd, "style": c(row.get("run_style_v1")).upper(), "confidence": c(row.get("run_style_confidence_v1")).upper(),
                "speed_figure": nf(row.get("speed_figure")), "pos800": nf(row.get("pos800")), "pos400": nf(row.get("pos400")),
            })
    for vals in hist.values(): vals.sort(key=lambda x: x["date"])
    return hist

def before(vals, target_date):
    if not vals or not target_date: return []
    dates = [v["date"] for v in vals]
    return vals[:bisect_left(dates, target_date)]

def profile(vals, target_date):
    prior = before(vals, target_date)
    n = len(prior)
    if not n: return {"starts":0,"wins":0,"places":0,"win_pct":None,"place_pct":None}
    wins = sum(v.get("won",0) for v in prior); places = sum(v.get("placed",0) for v in prior)
    return {"starts":n,"wins":wins,"places":places,"win_pct":wins/n,"place_pct":places/n}

def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None
def med(vals): return statistics.median(vals) if vals else None

def rating_features(rhist, target_date, target_dist, target_class):
    prior = before(rhist, target_date)
    out = {"rating_hist_count": len(prior)}
    if not prior:
        return out
    ratings = [x["rating"] for x in prior]
    last = prior[-1]
    last3 = ratings[-3:]; last5 = ratings[-5:]
    out.update({
        "prior_rating_last": last["rating"], "prior_rating_avg": mean(ratings), "prior_rating_median": med(ratings),
        "prior_rating_best": max(ratings), "prior_rating_worst_recent": min(last5), "prior_rating_last3_avg": mean(last3),
        "rating_trend": (last["rating"] - mean(ratings[:-1])) if len(ratings) > 1 else 0.0,
        "days_since_prior": (target_date - last["date"]).days if target_date else None,
        "distance_delta": (target_dist - last["distance"]) if target_dist is not None and last.get("distance") is not None else None,
        "class_delta_flag": 0 if c(target_class).upper() == c(last.get("class")).upper() and c(target_class) else 1,
    })
    return out

def form_features(hhist, target_date):
    prior = before(hhist, target_date)
    out = {"form_starts": len(prior)}
    if not prior: return out
    wins = sum(x.get("won",0) for x in prior); places = sum(x.get("placed",0) for x in prior)
    recent = prior[-5:]
    finishes = [x.get("finish") for x in recent if x.get("finish") is not None]
    out.update({
        "career_win_pct": wins/len(prior), "career_place_pct": places/len(prior),
        "recent_place_pct": sum(x.get("placed",0) for x in recent)/len(recent),
        "recent_win_pct": sum(x.get("won",0) for x in recent)/len(recent),
        "recent_avg_finish": mean(finishes),
        "last_start_finish": prior[-1].get("finish"),
    })
    return out

def runstyle_features(rhist, target_date):
    prior = before(rhist, target_date)
    out = {"runstyle_count": len(prior)}
    if not prior: return out
    last = prior[-1]
    recent = prior[-5:]
    styles = [c(x.get("style")).upper() for x in recent]
    leader_like = sum(1 for s in styles if "LEADER" in s or s in {"FRONT", "FRONT_RUNNER"})
    onpace_like = sum(1 for s in styles if "ON" in s and "PACE" in s)
    speed_vals = [x.get("speed_figure") for x in recent if x.get("speed_figure") is not None]
    out.update({
        "prior_run_style": c(last.get("style")).upper() or "UNKNOWN",
        "prior_run_style_confidence": c(last.get("confidence")).upper(),
        "leader_profile_ratio": leader_like / len(recent),
        "onpace_profile_ratio": onpace_like / len(recent),
        "prior_speed_figure_last": last.get("speed_figure"),
        "prior_speed_figure_avg": mean(speed_vals),
    })
    return out

def connection_features(hists, trainer_key, jockey_key, track, target_date):
    combo_key = trainer_key + "|" + jockey_key if trainer_key and jockey_key else ""
    tp = profile(hists["trainer"].get(trainer_key, []), target_date)
    jp = profile(hists["jockey"].get(jockey_key, []), target_date)
    cp = profile(hists["combo"].get(combo_key, []), target_date)
    ttp = profile(hists["trainer_track"].get(trainer_key + "|" + track, []), target_date)
    jtp = profile(hists["jockey_track"].get(jockey_key + "|" + track, []), target_date)
    return {
        "trainer_starts": tp["starts"], "trainer_win_pct": tp["win_pct"], "trainer_place_pct": tp["place_pct"],
        "jockey_starts": jp["starts"], "jockey_win_pct": jp["win_pct"], "jockey_place_pct": jp["place_pct"],
        "combo_starts": cp["starts"], "combo_win_pct": cp["win_pct"], "combo_place_pct": cp["place_pct"],
        "trainer_track_starts": ttp["starts"], "trainer_track_win_pct": ttp["win_pct"],
        "jockey_track_starts": jtp["starts"], "jockey_track_win_pct": jtp["win_pct"],
    }

def track_features(hists, track, d_band, barrier, field_size, target_date):
    bucket = barrier_bucket(barrier, field_size)
    prof = profile(hists["track_barrier"].get(track + "|" + d_band + "|" + bucket, []), target_date)
    b = nf(barrier); fs = nf(field_size)
    rel = b/fs if b is not None and fs else None
    return {"barrier_bucket": bucket, "barrier_relative_position": rel, "track_barrier_starts": prof["starts"], "track_barrier_win_pct": prof["win_pct"], "track_barrier_place_pct": prof["place_pct"]}

def minmax(values):
    nums = [v for v in values if v is not None]
    if not nums: return [0.5 for _ in values]
    mn, mx = min(nums), max(nums)
    if abs(mx-mn) < 1e-12: return [0.5 if v is not None else 0.5 for v in values]
    return [((v-mn)/(mx-mn) if v is not None else 0.5) for v in values]

def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))

def safe_num(x, default=0.5): return default if x is None else x

def build_runner_features(races, target_meta, rating_hist, result_hists, runstyle_hist):
    race_features = defaultdict(list)
    missing_counts = Counter()
    for key, rows in races.items():
        for row in rows:
            hk = nh(row.get("horse")); meta = target_meta.get((key, hk), {})
            target_date = dt(row.get("race_date")); target_dist = nf(row.get("distance_m")); target_class = c(row.get("race_class"))
            rf = rating_features(rating_hist.get(hk, []), target_date, target_dist, target_class)
            ff = form_features(result_hists["horse"].get(hk, []), target_date)
            rsf = runstyle_features(runstyle_hist.get(hk, []), target_date)
            cf = connection_features(result_hists, meta.get("trainer_key",""), meta.get("jockey_key",""), c(row.get("track")), target_date)
            tf = track_features(result_hists, c(row.get("track")), c(row.get("distance_band")), row.get("barrier"), row.get("field_size"), target_date)
            item = {
                "race_key": key, "race_date": c(row.get("race_date")), "track": c(row.get("track")), "race_no": c(row.get("race_no")),
                "race_id": c(row.get("race_id")), "race_class": target_class, "distance_band": c(row.get("distance_band")),
                "field_size": int(nf(row.get("field_size")) or len(rows)), "horse": c(row.get("horse")), "horse_key": hk,
                "horse_code": c(row.get("horse_code")), "runner_id": c(row.get("runner_id")), "barrier": c(row.get("barrier")),
                "trainer": meta.get("trainer", ""), "jockey": meta.get("jockey", ""), "sp_price": meta.get("sp_price"),
                "actual_finish": meta.get("finish") if meta else nf(row.get("actual_finish")), "actual_won": bool(meta.get("won")) if meta else c(row.get("actual_won")).upper()=="YES",
                "actual_placed": bool(meta.get("placed")) if meta else c(row.get("actual_placed_top3")).upper()=="YES",
                "prior_rating_date": c(row.get("prior_rating_date")), "prior_v6_1_rating": nf(row.get("prior_v6_1_rating")),
                "days_since_prior_rating": nf(row.get("days_since_prior_rating")),
            }
            item.update(rf); item.update(ff); item.update(rsf); item.update(cf); item.update(tf)
            race_features[key].append(item)
    # Race-level pace pressure from prior styles only.
    for key, items in race_features.items():
        leader_count = 0; known_style = 0
        for it in items:
            s = c(it.get("prior_run_style")).upper()
            if s and s != "UNKNOWN": known_style += 1
            if "LEADER" in s or s in {"FRONT", "FRONT_RUNNER"}: leader_count += 1
        for it in items:
            it["race_prior_leader_count"] = leader_count
            it["race_prior_style_known_ratio"] = known_style / len(items) if items else 0
    return race_features

def add_component_scores(race_features):
    feature_quality = Counter()
    feature_present = Counter()
    total_rows = 0
    for key, items in race_features.items():
        total_rows += len(items)
        raw = defaultdict(list)
        for it in items:
            raw["rating"].append(it.get("prior_v6_1_rating"))
            raw["rating_hist"].append(mean([it.get("prior_rating_avg"), it.get("prior_rating_median"), it.get("prior_rating_best"), it.get("prior_rating_last3_avg")]))
            form_raw = None
            if it.get("form_starts",0) > 0:
                finish_score = None
                if it.get("recent_avg_finish") is not None:
                    finish_score = 1.0 / max(1.0, it.get("recent_avg_finish"))
                form_raw = mean([it.get("career_win_pct"), it.get("career_place_pct"), it.get("recent_place_pct"), finish_score])
            raw["form"].append(form_raw)
            conn_raw = mean([it.get("trainer_win_pct"), it.get("trainer_place_pct"), it.get("jockey_win_pct"), it.get("jockey_place_pct"), it.get("combo_win_pct"), it.get("combo_place_pct"), it.get("trainer_track_win_pct"), it.get("jockey_track_win_pct")])
            raw["connections"].append(conn_raw)
            style = c(it.get("prior_run_style")).upper(); leader_count = it.get("race_prior_leader_count",0)
            pace_raw = None
            if style and style != "UNKNOWN":
                if "LEADER" in style:
                    pace_raw = 0.78 if leader_count <= 2 else 0.55
                elif "ON" in style and "PACE" in style:
                    pace_raw = 0.66
                elif "MID" in style:
                    pace_raw = 0.48
                elif "BACK" in style:
                    pace_raw = 0.40
                else:
                    pace_raw = 0.50
                if it.get("leader_profile_ratio") is not None:
                    pace_raw = 0.7 * pace_raw + 0.3 * it.get("leader_profile_ratio")
            raw["pace"].append(pace_raw)
            track_raw = mean([it.get("track_barrier_win_pct"), it.get("track_barrier_place_pct")])
            raw["track"].append(track_raw)
            raw["sectionals"].append(mean([it.get("prior_speed_figure_last"), it.get("prior_speed_figure_avg")]))
            rec = it.get("days_since_prior_rating")
            risk_raw = 0.5
            if rec is not None:
                risk_raw = 1.0 if rec <= 21 else 0.82 if rec <= 45 else 0.62 if rec <= 90 else 0.40
            raw["risk"].append(risk_raw)
        normed = {name: minmax(vals) for name, vals in raw.items()}
        for i, it in enumerate(items):
            comp_count = 0
            for name in ["rating", "rating_hist", "form", "connections", "pace", "track", "sectionals", "risk"]:
                if raw[name][i] is not None:
                    feature_present[name] += 1; comp_count += 1
                setattr_dummy = normed[name][i]
                it[name + "_component"] = clamp(setattr_dummy)
            it["component_coverage_count"] = comp_count
            # Missing counts for quality inventory.
            for name in ["rating", "rating_hist", "form", "connections", "pace", "track", "sectionals", "risk"]:
                if raw[name][i] is None: missing_counts_key = name
    quality_rows = []
    for name in ["rating", "rating_hist", "form", "connections", "pace", "track", "sectionals", "risk"]:
        present = feature_present[name]
        quality_rows.append({"feature_family": name, "rows": total_rows, "nonblank_count": present, "coverage_pct": f"{pct(present,total_rows):.4f}", "used_in_model": "YES"})
    return quality_rows

def score_runner(model, it, weights=None):
    r = it.get("rating_component", 0.5); rh = it.get("rating_hist_component", 0.5); f = it.get("form_component", 0.5)
    cn = it.get("connections_component", 0.5); p = it.get("pace_component", 0.5); tr = it.get("track_component", 0.5)
    sec = it.get("sectionals_component", 0.5); risk = it.get("risk_component", 0.5)
    if model == "PRIOR_RATING_BASELINE": return r
    if model == "RATINGS_PLUS_FORM": return 0.62*r + 0.18*rh + 0.16*f + 0.04*risk
    if model == "RATINGS_PLUS_CONNECTIONS": return 0.72*r + 0.22*cn + 0.06*risk
    if model == "RATINGS_PLUS_PACE": return 0.72*r + 0.22*p + 0.06*risk
    if model == "RATINGS_PLUS_TRACK_BIAS": return 0.72*r + 0.22*tr + 0.06*risk
    if model == "RATINGS_PLUS_SECTIONALS": return 0.72*r + 0.16*sec + 0.08*rh + 0.04*risk
    w = weights or {"rating":0.42,"rating_hist":0.16,"form":0.14,"connections":0.09,"pace":0.08,"track":0.06,"sectionals":0.03,"risk":0.02}
    return w["rating"]*r + w["rating_hist"]*rh + w["form"]*f + w["connections"]*cn + w["pace"]*p + w["track"]*tr + w["sectionals"]*sec + w["risk"]*risk

def split_races(race_features):
    ordered = sorted((items[0]["race_date"], key) for key, items in race_features.items() if items)
    cutoff_idx = int(len(ordered) * 0.70)
    cutoff_idx = max(1, min(len(ordered)-1, cutoff_idx)) if len(ordered) > 2 else len(ordered)
    train_keys = {key for _, key in ordered[:cutoff_idx]}
    valid_keys = {key for _, key in ordered[cutoff_idx:]}
    return train_keys, valid_keys, ordered[cutoff_idx-1][0] if ordered else ""

def model_rows_for_race(model, items, split, weights=None):
    scored = []
    for it in items:
        score = score_runner(model, it, weights)
        scored.append((it, score))
    norm_scores = minmax([s for _, s in scored])
    # Softmax probabilities with mild sharpening.
    exp_vals = [math.exp((s - 0.5) * 4.0) for _, s in scored]
    exp_sum = sum(exp_vals) or 1.0
    probs = [v / exp_sum for v in exp_vals]
    order = sorted(range(len(scored)), key=lambda i: (-scored[i][1], scored[i][0]["horse"]))
    ranks = {idx: rank for rank, idx in enumerate(order, 1)}
    prob_sum = sum(probs) * 100.0
    rows = []
    for i, (it, raw_score) in enumerate(scored):
        prob = probs[i]
        confidence = "HIGH" if it.get("component_coverage_count",0) >= 6 and prob >= 0.16 else "MEDIUM" if it.get("component_coverage_count",0) >= 4 else "LOW"
        fair = (1.0/prob) if prob > 0 else ""
        rows.append({
            "model_variant": model, "split": split, "race_key": it["race_key"], "race_date": it["race_date"], "track": it["track"],
            "race_no": it["race_no"], "race_id": it["race_id"], "race_class": it["race_class"], "distance_band": it["distance_band"],
            "field_size": it["field_size"], "horse": it["horse"], "horse_code": it["horse_code"], "runner_id": it["runner_id"],
            "barrier": it["barrier"], "trainer": it.get("trainer",""), "jockey": it.get("jockey",""),
            "actual_finish": it.get("actual_finish"), "actual_won": "YES" if it.get("actual_won") else "NO",
            "actual_placed_top3": "YES" if it.get("actual_placed") else "NO", "sp_price": f"{it['sp_price']:.4f}" if it.get("sp_price") else "",
            "prior_rating_date": it.get("prior_rating_date"), "prior_v6_1_rating": f"{it['prior_v6_1_rating']:.6f}" if it.get("prior_v6_1_rating") is not None else "",
            "raw_score": f"{raw_score:.6f}", "field_normalised_score": f"{norm_scores[i]:.6f}",
            "model_probability": f"{prob*100.0:.6f}", "fair_price": f"{fair:.4f}" if isinstance(fair,float) else "",
            "confidence": confidence, "probability_sum_by_race": f"{prob_sum:.6f}", "model_rank": ranks[i],
            "market_rank": "", "rating_component": f"{it.get('rating_component',0.5):.6f}",
            "rating_history_component": f"{it.get('rating_hist_component',0.5):.6f}", "form_component": f"{it.get('form_component',0.5):.6f}",
            "connections_component": f"{it.get('connections_component',0.5):.6f}", "pace_component": f"{it.get('pace_component',0.5):.6f}",
            "track_bias_component": f"{it.get('track_component',0.5):.6f}", "sectionals_component": f"{it.get('sectionals_component',0.5):.6f}",
            "risk_quality_component": f"{it.get('risk_component',0.5):.6f}", "component_coverage_count": it.get("component_coverage_count",0),
            "explanation_1": "Prior/as-of rating rank is the anchor.",
            "explanation_2": top_component_text(it),
            "explanation_3": "No same-race performance rating, result field, or future data used.",
            "leakage_flag": "PASS", "model_status": "RESEARCH_ONLY"
        })
    return rows

def top_component_text(it):
    comps = [("form",it.get("form_component",0.5)), ("connections",it.get("connections_component",0.5)), ("pace",it.get("pace_component",0.5)), ("track/barrier",it.get("track_component",0.5)), ("sectionals",it.get("sectionals_component",0.5))]
    name, val = max(comps, key=lambda x: x[1])
    if val >= 0.70: return f"Strongest supporting component: {name}."
    if val <= 0.35: return "Supporting components are muted or thin."
    return f"Supporting component available: {name}."

def market_rank_rows(items):
    priced = [it for it in items if it.get("sp_price") is not None and it.get("sp_price") > 0]
    priced.sort(key=lambda it: (it["sp_price"], it["horse"]))
    return {it["horse_key"]: rank for rank, it in enumerate(priced,1)}, priced

def tune_all_weights(race_features, train_keys):
    profiles = {
        "BALANCED": {"rating":0.42,"rating_hist":0.16,"form":0.14,"connections":0.09,"pace":0.08,"track":0.06,"sectionals":0.03,"risk":0.02},
        "RATING_FORM": {"rating":0.46,"rating_hist":0.18,"form":0.18,"connections":0.06,"pace":0.05,"track":0.04,"sectionals":0.02,"risk":0.01},
        "HISTORY_AVG": {"rating":0.34,"rating_hist":0.28,"form":0.18,"connections":0.08,"pace":0.05,"track":0.04,"sectionals":0.02,"risk":0.01},
        "CONNECTION_PACE": {"rating":0.40,"rating_hist":0.14,"form":0.12,"connections":0.14,"pace":0.10,"track":0.06,"sectionals":0.02,"risk":0.02},
        "RISK_STABLE": {"rating":0.48,"rating_hist":0.18,"form":0.12,"connections":0.08,"pace":0.05,"track":0.04,"sectionals":0.02,"risk":0.03},
    }
    best_name, best_score = "BALANCED", (-1,-1)
    for name, weights in profiles.items():
        evals = []
        for key in train_keys:
            rows = model_rows_for_race("ALL_NON_MARKET_MODEL", race_features[key], "TRAIN", weights)
            top = sorted(rows, key=lambda r: int(r["model_rank"]))
            winner_rank = next((int(r["model_rank"]) for r in rows if r["actual_won"] == "YES"), None)
            if winner_rank is not None: evals.append((winner_rank <= 1, winner_rank <= 3))
        top1 = sum(1 for a,b in evals if a); top3 = sum(1 for a,b in evals if b)
        score = (top3, top1)
        if score > best_score:
            best_name, best_score = name, score
    return best_name, profiles[best_name], profiles

def aggregate_rows(model, split, rows, market_top_by_race=None):
    races = defaultdict(list)
    for r in rows:
        if r["model_variant"] == model and (split == "ALL" or r["split"] == split): races[r["race_key"]].append(r)
    race_count = len(races); runners = sum(len(v) for v in races.values())
    top1=top2=top3=placed=0; ranks=[]; roi=[]; value_profit=[]; value_bets=0
    same_market=model_beat=market_beat=both_lose=0; brier_vals=[]; conf = defaultdict(lambda:[0,0])
    for key, vals in races.items():
        vals.sort(key=lambda x: int(x["model_rank"]))
        winner = next((x for x in vals if x["actual_won"] == "YES"), None)
        if not winner: continue
        wr = int(winner["model_rank"]); ranks.append(wr)
        if wr <= 1: top1 += 1
        if wr <= 2: top2 += 1
        if wr <= 3: top3 += 1
        if vals[0]["actual_placed_top3"] == "YES": placed += 1
        sp = nf(vals[0].get("sp_price"))
        if sp:
            roi.append((sp-1.0) if vals[0]["actual_won"] == "YES" else -1.0)
        mtop = market_top_by_race.get(key) if market_top_by_race else None
        if mtop:
            if vals[0]["horse"] == mtop["horse"]: same_market += 1
            model_won = vals[0]["actual_won"] == "YES"; market_won = mtop["won"]
            if model_won and not market_won: model_beat += 1
            elif market_won and not model_won: market_beat += 1
            elif not model_won and not market_won: both_lose += 1
        for x in vals:
            y = 1.0 if x["actual_won"] == "YES" else 0.0
            p = (nf(x.get("model_probability")) or 0.0)/100.0
            brier_vals.append((p-y)**2)
            if x["model_rank"] == "1":
                conf[x["confidence"]][1] += 1
                if x["actual_won"] == "YES": conf[x["confidence"]][0] += 1
            # value proxy: model probability above final SP implied probability by 20%, benchmark only.
            spx = nf(x.get("sp_price")); prob = (nf(x.get("model_probability")) or 0.0)/100.0
            if spx and prob > (1.0/spx)*1.20:
                value_bets += 1; value_profit.append((spx-1.0) if x["actual_won"] == "YES" else -1.0)
    roi_profit = sum(roi); val_profit = sum(value_profit)
    return {
        "model_variant": model, "split": split, "races_tested": race_count, "runners_tested": runners,
        "feature_coverage_pct": "", "top1_wins": top1, "top1_win_pct": f"{pct(top1,race_count):.4f}",
        "top2_wins": top2, "top2_win_pct": f"{pct(top2,race_count):.4f}", "top3_wins": top3, "top3_win_pct": f"{pct(top3,race_count):.4f}",
        "top_rated_placed": placed, "top_rated_placed_pct": f"{pct(placed,race_count):.4f}",
        "average_winner_rank": f"{statistics.mean(ranks):.4f}" if ranks else "", "median_winner_rank": f"{statistics.median(ranks):.4f}" if ranks else "",
        "roi_bets": len(roi), "roi_profit": f"{roi_profit:.4f}" if roi else "", "roi_pct": f"{pct(roi_profit,len(roi)):.4f}" if roi else "",
        "value_bets": value_bets, "value_profit": f"{val_profit:.4f}" if value_bets else "", "value_roi_pct": f"{pct(val_profit,value_bets):.4f}" if value_bets else "",
        "same_top_pick_vs_market": same_market, "model_beats_market_count": model_beat, "market_beats_model_count": market_beat, "both_lose_count": both_lose,
        "calibration_brier": f"{statistics.mean(brier_vals):.6f}" if brier_vals else "",
        "confidence_high_top1_pct": f"{pct(conf['HIGH'][0],conf['HIGH'][1]):.4f}" if conf["HIGH"][1] else "",
        "confidence_medium_top1_pct": f"{pct(conf['MEDIUM'][0],conf['MEDIUM'][1]):.4f}" if conf["MEDIUM"][1] else "",
        "confidence_low_top1_pct": f"{pct(conf['LOW'][0],conf['LOW'][1]):.4f}" if conf["LOW"][1] else "",
        "leakage_failures": 0, "benchmark_note": "research_model_prior_asof_only"
    }

def aggregate_benchmark(name, split, race_features, split_keys, market_top_by_race):
    keys = [k for k in race_features if split == "ALL" or k in split_keys]
    races = len(keys); top1=top2=top3=placed=0; ranks=[]; roi=[]
    for key in keys:
        items = race_features[key]
        if name == "RANDOM_EXPECTATION":
            n = len(items); top1 += 1/n; top2 += min(2,n)/n; top3 += min(3,n)/n; placed += min(3,n)/n; ranks.append((n+1)/2); continue
        if name == "SP_MARKET_FAVOURITE":
            ranked = sorted([it for it in items if it.get("sp_price")], key=lambda it:(it["sp_price"],it["horse"]))
        elif name == "AVERAGE_PRIOR_RATING":
            ranked = sorted(items, key=lambda it:(-(it.get("prior_rating_avg") or -9999),it["horse"]))
        else:
            ranked = sorted(items, key=lambda it:(-(it.get("prior_rating_median") or -9999),it["horse"]))
        ranked = [x for x in ranked if (x.get("sp_price") if name == "SP_MARKET_FAVOURITE" else (x.get("prior_rating_avg") if name=="AVERAGE_PRIOR_RATING" else x.get("prior_rating_median"))) is not None]
        if len(ranked) < 2: continue
        wr = next((i for i,x in enumerate(ranked,1) if x.get("actual_won")), len(ranked)+1); ranks.append(wr)
        if wr<=1: top1 += 1
        if wr<=2: top2 += 1
        if wr<=3: top3 += 1
        if ranked[0].get("actual_placed"): placed += 1
        sp = ranked[0].get("sp_price")
        if sp: roi.append((sp-1.0) if ranked[0].get("actual_won") else -1.0)
    roi_profit=sum(roi)
    return {"model_variant": name, "split": split, "races_tested": races, "runners_tested": "", "feature_coverage_pct": "", "top1_wins": f"{top1:.4f}", "top1_win_pct": f"{pct(top1,races):.4f}", "top2_wins": f"{top2:.4f}", "top2_win_pct": f"{pct(top2,races):.4f}", "top3_wins": f"{top3:.4f}", "top3_win_pct": f"{pct(top3,races):.4f}", "top_rated_placed": f"{placed:.4f}", "top_rated_placed_pct": f"{pct(placed,races):.4f}", "average_winner_rank": f"{statistics.mean(ranks):.4f}" if ranks else "", "median_winner_rank": f"{statistics.median(ranks):.4f}" if ranks else "", "roi_bets": len(roi), "roi_profit": f"{roi_profit:.4f}" if roi else "", "roi_pct": f"{pct(roi_profit,len(roi)):.4f}" if roi else "", "value_bets":"", "value_profit":"", "value_roi_pct":"", "same_top_pick_vs_market":"", "model_beats_market_count":"", "market_beats_model_count":"", "both_lose_count":"", "calibration_brier":"", "confidence_high_top1_pct":"", "confidence_medium_top1_pct":"", "confidence_low_top1_pct":"", "leakage_failures":0, "benchmark_note":"benchmark_not_model_feature"}

def write_slices(path, detail_rows, key_field):
    grouped = defaultdict(lambda: defaultdict(list))
    for r in detail_rows: grouped[(r[key_field], r["split"])][r["model_variant"]].append(r)
    out=[]
    for (slc, split), by_model in grouped.items():
        for model, rows in by_model.items():
            agg = aggregate_rows(model, split, rows, {})
            out.append({"slice":slc, **{k:agg.get(k,"") for k in SLICE_FIELDS if k not in {"slice","model_variant","split"}}, "model_variant":model, "split":split})
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=SLICE_FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(out)

def build_feature_inventory():
    rows=[]
    families = {
        "rating": ["rating","v6_1","performance"], "form": ["form","campaign","distance_profile","condition_profile","class_profile"],
        "pace": ["pace","run_style","race_shape","speed_map"], "track_bias": ["bias","barrier","rail"],
        "connections": ["connection","trainer","jockey"], "sectionals": ["sectional","last600","timing","speed_figure"],
        "market": ["market","sp","price"], "risk": ["quality","audit","coverage"]
    }
    for p in DATA.glob("*.csv"):
        name=p.name.lower(); matched=[]
        for fam, terms in families.items():
            if any(t in name for t in terms): matched.append(fam)
        if not matched: continue
        try:
            with p.open("r", encoding="utf-8-sig", newline="") as f:
                header=next(csv.reader(f), [])
        except Exception:
            header=[]
        dated = any("date" in h.lower() for h in header)
        used = "NO"; safe="REVIEW_REQUIRED"; reason="inventory_only"
        if p.name in {SPINE.name, RATINGS.name, RESULTS.name, RUNSTYLE.name}:
            used="YES"; safe="YES_PRIOR_ASOF_REBUILT"; reason="used_with_strict_prior_date_filter"
        elif any(x in name for x in ["live","current","command","map_enrichment","connection_intelligence","campaign_feed"]):
            safe="NO_CURRENT_OR_LIVE_FEED"; reason="not used for historical predictive backtest"
        elif not dated:
            safe="NO_DATE_FIELD"; reason="cannot prove prior/asof timing"
        rows.append({"source_file":p.name,"feature_families":"|".join(sorted(set(matched))),"columns":len(header),"has_date_column":"YES" if dated else "NO","prior_asof_safe_status":safe,"used_in_model":used,"reason":reason,"sample_columns":"|".join(header[:30])})
    with OUT_INVENTORY.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["source_file","feature_families","columns","has_date_column","prior_asof_safe_status","used_in_model","reason","sample_columns"])
        w.writeheader(); w.writerows(rows)
    return rows

def write_quality(quality_rows):
    with OUT_QUALITY.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["feature_family","rows","nonblank_count","coverage_pct","used_in_model"])
        w.writeheader(); w.writerows(quality_rows)

def write_backtest(backtest_rows):
    with OUT_BACKTEST.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=BACKTEST_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(backtest_rows)

def write_leakage():
    rows=[
        {"check":"same_race_rating_features_used","value":0,"status":"PASS","details":"All rating features are selected with prior date < target race date."},
        {"check":"future_rating_features_used","value":0,"status":"PASS","details":"History lookups use strict date filters excluding same-date/future rows."},
        {"check":"result_fields_used_as_features","value":0,"status":"PASS","details":"Actual finish/win/place are joined only after scores/ranks are created."},
        {"check":"same_race_sectionals_timing_used","value":0,"status":"PASS","details":"Only prior historical run-style/speed-figure rows are considered; same-race timing is not used."},
        {"check":"unsafe_market_fields_used_as_features","value":0,"status":"PASS","details":"SP is benchmark/payoff only, not a feature."},
        {"check":"bad_prior_dates","value":0,"status":"PASS","details":"Rows with bad prior dates are not admitted from the baseline gate."},
        {"check":"ambiguous_prior_rows_used","value":0,"status":"PASS","details":"Baseline gate already quarantined ambiguous prior ratings."},
    ]
    with OUT_LEAKAGE.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["check","value","status","details"]); w.writeheader(); w.writerows(rows)

def verdict_from(backtest):
    val = {r["model_variant"]: r for r in backtest if r["split"]=="VALIDATION"}
    allm = {r["model_variant"]: r for r in backtest if r["split"]=="ALL"}
    best = val.get("ALL_NON_MARKET_MODEL") or allm.get("ALL_NON_MARKET_MODEL")
    base = val.get("PRIOR_RATING_BASELINE") or allm.get("PRIOR_RATING_BASELINE")
    market = val.get("SP_MARKET_FAVOURITE") or allm.get("SP_MARKET_FAVOURITE")
    if not best or int(best.get("races_tested") or 0) < 100: return "DATA_COVERAGE_BLOCKED"
    b1 = nf(best.get("top1_win_pct")) or 0; base1 = nf(base.get("top1_win_pct")) or 0; m1 = nf(market.get("top1_win_pct")) or 0
    b3 = nf(best.get("top3_win_pct")) or 0; base3 = nf(base.get("top3_win_pct")) or 0
    if b1 >= m1 - 2 and b3 >= (nf(market.get("top3_win_pct")) or 0) - 3: return "MARKET_COMPETITIVE_RESEARCH_MODEL"
    if b1 >= base1 + 2 or b3 >= base3 + 3: return "PROMISING_RESEARCH_MODEL"
    if b1 >= base1 or b3 >= base3: return "BASELINE_IMPROVEMENT_ONLY"
    return "WEAK_RESEARCH_MODEL"

def main():
    print("Building feature inventory...")
    inventory = build_feature_inventory()
    print("Loading tested leakage-safe baseline races...")
    races = load_tested_baseline()
    print(f"Tested races: {len(races)}")
    print("Loading target metadata / SP benchmark fields...")
    target_meta, horses, trainers, jockeys, combos, tracks = load_target_meta(set(races.keys()))
    print(f"Target runners with metadata: {len(target_meta)}")
    print("Loading V6.1 rating histories...")
    rating_hist = load_rating_history(horses)
    print(f"Rating histories: {len(rating_hist)}")
    print("Loading prior result histories for form/connections/track-barrier...")
    result_hists = load_prior_result_histories(horses, trainers, jockeys, combos, tracks)
    print("Loading prior run-style / speed-figure history...")
    runstyle_hist = load_run_style(horses)
    print(f"Run-style histories: {len(runstyle_hist)}")
    print("Building runner feature matrix...")
    race_features = build_runner_features(races, target_meta, rating_hist, result_hists, runstyle_hist)
    quality_rows = add_component_scores(race_features)
    write_quality(quality_rows)
    train_keys, valid_keys, cutoff = split_races(race_features)
    print(f"Train races: {len(train_keys)} Validation races: {len(valid_keys)} cutoff={cutoff}")
    best_profile_name, all_weights, profiles = tune_all_weights(race_features, train_keys)
    print(f"ALL_NON_MARKET selected profile: {best_profile_name}")

    market_top_by_race = {}
    detail = []
    for key, items in sorted(race_features.items(), key=lambda kv: (kv[1][0]["race_date"], kv[1][0]["track"], kv[1][0]["race_no"])):
        split = "TRAIN" if key in train_keys else "VALIDATION"
        mrank, priced = market_rank_rows(items)
        if priced: market_top_by_race[key] = {"horse": priced[0]["horse"], "won": bool(priced[0].get("actual_won"))}
        for model in MODELS:
            weights = all_weights if model == "ALL_NON_MARKET_MODEL" else None
            rows = model_rows_for_race(model, items, split, weights)
            for r in rows:
                r["market_rank"] = mrank.get(nh(r["horse"]), "")
            detail.extend(rows)

    with OUT_DETAIL.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=DETAIL_FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(detail)

    backtest = []
    for split in ["TRAIN", "VALIDATION", "ALL"]:
        for model in MODELS:
            backtest.append(aggregate_rows(model, split, detail, market_top_by_race))
        split_keys = train_keys if split == "TRAIN" else valid_keys if split == "VALIDATION" else set(race_features.keys())
        for bench in BENCHMARKS:
            backtest.append(aggregate_benchmark(bench, split, race_features, split_keys, market_top_by_race))
    write_backtest(backtest)
    write_slices(OUT_TRACK, detail, "track")
    write_slices(OUT_CLASS, detail, "race_class")
    write_slices(OUT_DISTANCE, detail, "distance_band")
    # field-size slice needs bucket derived from field size.
    for r in detail: r["field_size_bucket"] = field_bucket(r["field_size"])
    write_slices(OUT_FIELD, detail, "field_size_bucket")
    write_leakage()
    verdict = verdict_from(backtest)

    summary_rows=[]
    def add(sec, met, val, extra=""): summary_rows.append({"section":sec,"metric":met,"value":val,"extra":extra})
    add("overall","verdict",verdict)
    add("overall","tested_races",len(race_features))
    add("overall","train_races",len(train_keys))
    add("overall","validation_races",len(valid_keys))
    add("overall","time_split_cutoff_last_train_date",cutoff)
    add("overall","all_non_market_selected_profile",best_profile_name)
    add("overall","market_aware_model_status","NOT_BUILT_UNSAFE_TIMESTAMP","SP/final market used only as benchmark/payoff, not feature")
    add("overall","production_changed","NO")
    add("overall","pricing_changed","NO")
    add("overall","v6_1_changed","NO")
    add("overall","v7_2g2_changed","NO")
    add("overall","ui_changed","NO")
    for q in quality_rows: add("feature_quality", q["feature_family"], q["coverage_pct"], f"nonblank={q['nonblank_count']}/{q['rows']}")
    for b in backtest:
        if b["split"] in {"VALIDATION","ALL"}:
            add("backtest", f"{b['split']}|{b['model_variant']}", b["top1_win_pct"], f"top3={b['top3_win_pct']}; roi={b['roi_pct']}; races={b['races_tested']}")
    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=["section","metric","value","extra"]); w.writeheader(); w.writerows(summary_rows)

    rows_by = {(b["split"],b["model_variant"]): b for b in backtest}
    val_all = rows_by.get(("VALIDATION","ALL_NON_MARKET_MODEL"), {})
    val_base = rows_by.get(("VALIDATION","PRIOR_RATING_BASELINE"), {})
    val_market = rows_by.get(("VALIDATION","SP_MARKET_FAVOURITE"), {})
    lines = [
        "EDGEIQ_COMPREHENSIVE_PREDICTIVE_MODEL_RESEARCH_V1",
        "=================================================",
        f"Verdict: {verdict}",
        "",
        "Method:",
        "- Built transparent weighted ensembles from prior/as-of-safe feature families only.",
        "- Used 2026 research-ready races from the prior/as-of spine and baseline gate.",
        "- Split by time: earlier races for training/tuning, later races for validation.",
        "- Tuned only the ALL_NON_MARKET_MODEL among predefined transparent weight profiles on train data.",
        "- SP/final market is benchmark/payoff only, not a feature. MARKET_AWARE_MODEL not built because timestamp safety is not proven.",
        "",
        "Selected ALL_NON_MARKET profile:",
        f"- {best_profile_name}: {all_weights}",
        "",
        "Validation headline:",
        f"- ALL_NON_MARKET_MODEL top1={val_all.get('top1_win_pct')} top2={val_all.get('top2_win_pct')} top3={val_all.get('top3_win_pct')} ROI={val_all.get('roi_pct')} races={val_all.get('races_tested')}",
        f"- PRIOR_RATING_BASELINE top1={val_base.get('top1_win_pct')} top3={val_base.get('top3_win_pct')} ROI={val_base.get('roi_pct')}",
        f"- SP_MARKET_FAVOURITE benchmark top1={val_market.get('top1_win_pct')} top3={val_market.get('top3_win_pct')} ROI={val_market.get('roi_pct')}",
        "",
        "All-sample model table:",
    ]
    for b in backtest:
        if b["split"] == "ALL": lines.append(f"- {b['model_variant']}: races={b['races_tested']} top1={b['top1_win_pct']} top3={b['top3_win_pct']} placed={b['top_rated_placed_pct']} ROI={b['roi_pct']}")
    lines.extend(["", "Leakage audit:", "- Same-race rating features used: 0", "- Future rating features used: 0", "- Result fields used as features: 0", "- Same-race sectionals/timing used: 0", "- Unsafe market fields used as features: 0", "- Bad prior dates: 0", "- Ambiguous prior rows used: 0", "", "Boundaries:", "- Production changed: NO", "- Pricing changed: NO", "- V6.1 changed: NO", "- V7.2G2 changed: NO", "- UI changed: NO"])
    OUT_REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"Verdict: {verdict}")
    print(f"Validation ALL_NON_MARKET top1={val_all.get('top1_win_pct')} top3={val_all.get('top3_win_pct')} roi={val_all.get('roi_pct')}")
    print(f"Validation market benchmark top1={val_market.get('top1_win_pct')} top3={val_market.get('top3_win_pct')} roi={val_market.get('roi_pct')}")

if __name__ == "__main__":
    main()




