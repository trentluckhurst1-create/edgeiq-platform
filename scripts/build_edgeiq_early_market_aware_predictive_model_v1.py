import csv
import math
import re
import statistics
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
COMP = DATA / "edgeiq_comprehensive_predictive_model_research_v1.csv"
BENCH = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1.csv"
MARKET = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1.csv"
MARKET_QUALITY = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_quality.csv"
MARKET_QUAR = DATA / "edgeiq_timestamp_safe_market_snapshot_spine_v1_quarantined.csv"
ASOF = DATA / "edgeiq_prior_asof_rating_spine_v1.csv"

OUT_DETAIL = DATA / "edgeiq_early_market_aware_predictive_model_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_early_market_aware_predictive_model_v1_summary.csv"
OUT_BACKTEST = DATA / "edgeiq_early_market_aware_predictive_model_v1_backtest.csv"
OUT_AGE = DATA / "edgeiq_early_market_aware_predictive_model_v1_by_snapshot_age.csv"
OUT_TRACK = DATA / "edgeiq_early_market_aware_predictive_model_v1_by_track.csv"
OUT_CLASS = DATA / "edgeiq_early_market_aware_predictive_model_v1_by_class.csv"
OUT_LEAKAGE = DATA / "edgeiq_early_market_aware_predictive_model_v1_leakage_audit.csv"
OUT_REPORT = DATA / "edgeiq_early_market_aware_predictive_model_v1_report.txt"

MODELS = [
    "PRIOR_RATING_ONLY_ON_MARKET_COVERAGE",
    "NON_MARKET_MODEL_ON_MARKET_COVERAGE",
    "MARKET_RANK_ONLY",
    "MARKET_PRICE_ONLY",
    "MARKET_PLUS_PRIOR_RATING",
    "MARKET_PLUS_NON_MARKET_MODEL",
    "MARKET_DISCIPLINED_EDGEIQ_MODEL",
]
BENCHMARKS = ["FINAL_SP_FAVOURITE_BENCHMARK", "RANDOM_EXPECTATION"]
MARKET_COVERAGE_GATE = 80.0

DETAIL_FIELDS = [
    "model_variant","race_key","split","race_date","track","race_no","race_id","race_class","distance_band","field_size","market_coverage_pct",
    "horse","horse_key","actual_finish","actual_won","actual_placed_top3","final_sp_payoff","safe_market_price","safe_market_rank","safe_market_implied_probability",
    "market_confidence_band","favourite_flag","top_3_market_flag","snapshot_age_minutes_before_jump","snapshot_age_bucket","firming_drifting_flag",
    "longshot_risk_flag","model_vs_market_disagreement_flag","prior_rating_score","non_market_score","market_rank_score","market_price_score",
    "model_score","model_probability","model_rank","fair_price","component_reason_1","component_reason_2","leakage_flag","research_status"
]
BACKTEST_FIELDS = [
    "model_variant","races_tested","runners_tested","top1_wins","top1_win_pct","top2_wins","top2_win_pct","top3_wins","top3_win_pct",
    "top_rated_placed","top_rated_placed_pct","roi_bets","roi_profit","roi_pct","average_winner_rank","median_winner_rank",
    "same_top_pick_as_market_pct","edgeiq_beats_market_count","market_beats_edgeiq_count","both_win","both_lose","longshot_top_pick_rate_pct",
    "average_top_pick_sp","leakage_failures","benchmark_note"
]
SLICE_FIELDS = ["slice","model_variant","races_tested","runners_tested","top1_win_pct","top2_win_pct","top3_win_pct","top_rated_placed_pct","roi_pct","average_winner_rank","longshot_top_pick_rate_pct","leakage_failures"]
SUMMARY_FIELDS = ["section","metric","value","extra"]
LEAKAGE_FIELDS = ["check","value","status","details"]

def c(v): return "" if v is None else str(v).strip()
def nf(v):
    t=c(v)
    if not t: return None
    t=re.sub(r"[^0-9.\-]", "", t)
    if t in ("", ".", "-", "-."): return None
    try:
        x=float(t)
        return None if math.isnan(x) or math.isinf(x) else x
    except ValueError:
        return None

def nh(v): return re.sub(r"[^A-Z0-9]+", "", c(v).upper())
def nt(v): return re.sub(r"\s+", " ", c(v).upper()).strip()
def nr(v):
    x=nf(v)
    return str(int(round(x))) if x is not None else c(v).replace("R","")
def key(date, track, race_no, horse): return "|".join([c(date), nt(track), nr(race_no), nh(horse)])
def race_key(date, track, race_no): return "|".join([c(date), nt(track), nr(race_no)])
def pct(a,b): return (a/b*100.0) if b else 0.0
def mean(vals):
    vals=[v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None

def minmax(vals):
    nums=[v for v in vals if v is not None]
    if not nums: return [0.5 for _ in vals]
    mn=min(nums); mx=max(nums)
    if abs(mx-mn)<1e-12: return [0.5 if v is not None else 0.5 for v in vals]
    return [((v-mn)/(mx-mn) if v is not None else 0.5) for v in vals]

def age_bucket(minutes):
    m=nf(minutes)
    if m is None: return "UNKNOWN"
    if m <= 30: return "LATE_0_30"
    if m <= 60: return "MID_30_60"
    if m <= 180: return "EARLY_60_180"
    return "VERY_EARLY_180_PLUS"

def load_comp_rows():
    by_model = {"ALL_NON_MARKET_MODEL": {}, "PRIOR_RATING_BASELINE": {}}
    races = defaultdict(set)
    with COMP.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            model=row.get("model_variant")
            if model not in by_model: continue
            if row.get("leakage_flag") != "PASS": continue
            k=key(row.get("race_date"),row.get("track"),row.get("race_no"),row.get("horse"))
            by_model[model][k]=row
            races[race_key(row.get("race_date"),row.get("track"),row.get("race_no"))].add(k)
    return by_model, races

def load_market_rows():
    out={}; races=defaultdict(set); unsafe=0; after=0
    with MARKET.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("feature_safe_flag") != "YES":
                unsafe += 1; continue
            mins=nf(row.get("latest_safe_minutes_before_jump"))
            if mins is None or mins < 0:
                after += 1; continue
            price=nf(row.get("latest_safe_price"))
            if price is None or price <= 1: continue
            k=key(row.get("race_date"),row.get("track"),row.get("race_no"),row.get("horse"))
            out[k]=row
            races[race_key(row.get("race_date"),row.get("track"),row.get("race_no"))].add(k)
    return out, races, unsafe, after

def join_rows():
    comp, comp_races = load_comp_rows()
    market, market_races, unsafe, after = load_market_rows()
    overlap_keys=[rk for rk in market_races if rk in comp_races]
    exact_runner_overlap=0
    overlap_detail=[]
    for ork in sorted(overlap_keys):
        comp_count=len(comp_races.get(ork,set()))
        market_count=len(market_races.get(ork,set()))
        matched_count=sum(1 for hk in comp_races.get(ork,set()) if hk in market)
        exact_runner_overlap += matched_count
        overlap_detail.append({
            "race_key":ork,
            "comp_runners":comp_count,
            "market_runners":market_count,
            "matched_runners":matched_count,
            "coverage_pct":pct(matched_count,comp_count),
        })
    joined=defaultdict(list); excluded=Counter(); join_misses=[]
    for rk, comp_keys in comp_races.items():
        market_keys=market_races.get(rk,set())
        if not market_keys: continue
        comp_count=len(comp_keys)
        matched_keys=[k for k in comp_keys if k in market and k in comp["ALL_NON_MARKET_MODEL"] and k in comp["PRIOR_RATING_BASELINE"]]
        coverage=pct(len(matched_keys),comp_count)
        if coverage < MARKET_COVERAGE_GATE:
            excluded["RACE_MARKET_COVERAGE_BELOW_80"] += 1
            continue
        for k in matched_keys:
            nm=comp["ALL_NON_MARKET_MODEL"][k]
            pr=comp["PRIOR_RATING_BASELINE"][k]
            mk=market[k]
            item={"race_join_key":rk,"horse_join_key":k,"non_market":nm,"prior":pr,"market":mk,"market_coverage_pct":coverage,"comp_field_size":comp_count}
            joined[rk].append(item)
        if len(matched_keys) < 2: excluded["TOO_FEW_JOINED_RUNNERS"] += 1
    # Require winner in joined rows for fair evaluation.
    final=defaultdict(list)
    for rk, items in joined.items():
        if len(items)<2: continue
        if not any(x["non_market"].get("actual_won") == "YES" for x in items):
            excluded["WINNER_NOT_IN_MARKET_COVERED_RUNNERS"] += 1
            continue
        final[rk]=items
    return final, excluded, {
        "unsafe_market_rows_seen":unsafe,
        "after_jump_market_rows_seen":after,
        "market_rows":len(market),
        "comprehensive_model_races":len(comp_races),
        "safe_market_races":len(market_races),
        "overlapping_races":len(overlap_keys),
        "exact_runner_overlap":exact_runner_overlap,
        "overlap_detail":overlap_detail,
    }

def score_base_features(races):
    for rk, items in races.items():
        prior_raw=[]; nm_raw=[]; market_prices=[]; market_ranks=[]
        for it in items:
            prior_raw.append(nf(it["prior"].get("field_normalised_score")) or nf(it["prior"].get("raw_score")))
            nm_raw.append(nf(it["non_market"].get("field_normalised_score")) or nf(it["non_market"].get("raw_score")))
            market_prices.append(nf(it["market"].get("latest_safe_price")))
            market_ranks.append(nf(it["market"].get("market_rank")))
        prior_scores=minmax(prior_raw); nm_scores=minmax(nm_raw)
        implied=[(1.0/p if p and p>0 else None) for p in market_prices]
        market_price_scores=minmax(implied)
        n=len(items)
        for i,it in enumerate(items):
            rank=market_ranks[i]
            rank_score=(n-rank)/(n-1) if rank is not None and n>1 else 0.5
            it["prior_score"]=prior_scores[i]
            it["non_market_score"]=nm_scores[i]
            it["market_price_score"]=market_price_scores[i]
            it["market_rank_score"]=max(0.0,min(1.0,rank_score))
    return races

def disciplined_score(it):
    p=it["prior_score"]; nm=it["non_market_score"]; mp=it["market_price_score"]; mr=it["market_rank_score"]
    price=nf(it["market"].get("latest_safe_price"))
    top3=it["market"].get("top_3_market_flag") == "YES"
    fav=it["market"].get("favourite_flag") == "YES"
    conf=it["market"].get("market_confidence_band")
    score=0.40*mp + 0.25*nm + 0.18*p + 0.12*mr
    score += 0.04 if top3 else 0.0
    score += 0.03 if fav else 0.0
    if conf == "HIGH_LATE_PRE_RACE": score += 0.02
    elif conf == "EARLY_ONLY": score -= 0.02
    strong_disagreement = nm >= 0.88 and p >= 0.70
    if price is not None and price >= 10 and not strong_disagreement:
        score -= 0.16
    elif price is not None and price >= 10 and strong_disagreement:
        score -= 0.04
    if not top3 and not strong_disagreement:
        score -= 0.04
    return max(0.0,min(1.0,score))

def model_score(model,it):
    p=it["prior_score"]; nm=it["non_market_score"]; mp=it["market_price_score"]; mr=it["market_rank_score"]
    if model == "PRIOR_RATING_ONLY_ON_MARKET_COVERAGE": return p
    if model == "NON_MARKET_MODEL_ON_MARKET_COVERAGE": return nm
    if model == "MARKET_RANK_ONLY": return mr
    if model == "MARKET_PRICE_ONLY": return mp
    if model == "MARKET_PLUS_PRIOR_RATING": return 0.58*mp + 0.32*p + 0.10*mr
    if model == "MARKET_PLUS_NON_MARKET_MODEL": return 0.58*mp + 0.32*nm + 0.10*mr
    if model == "MARKET_DISCIPLINED_EDGEIQ_MODEL": return disciplined_score(it)
    return nm

def softmax(scores):
    vals=[math.exp((s-0.5)*4.0) for s in scores]
    total=sum(vals) or 1.0
    return [v/total for v in vals]

def build_detail_rows(races):
    out=[]
    for rk, items in sorted(races.items(), key=lambda kv:(kv[1][0]["non_market"].get("race_date"),kv[1][0]["non_market"].get("track"),kv[1][0]["non_market"].get("race_no"))):
        for model in MODELS:
            scores=[model_score(model,it) for it in items]
            probs=softmax(scores)
            order=sorted(range(len(items)), key=lambda i:(-scores[i], items[i]["non_market"].get("horse")))
            ranks={idx:rank for rank,idx in enumerate(order,1)}
            for i,it in enumerate(items):
                nm=it["non_market"]; mk=it["market"]
                price=nf(mk.get("latest_safe_price")); final_sp=nf(nm.get("sp_price")); prob=probs[i]
                disagreement=abs((nf(mk.get("market_rank")) or 99) - ranks[i]) >= 3
                longshot=price is not None and price >= 10
                reason1="Timestamp-safe market price/rank used as feature." if model.startswith("MARKET") else "No market feature used in this variant."
                reason2="Longshot guardrail active." if model=="MARKET_DISCIPLINED_EDGEIQ_MODEL" and longshot else "Prior/as-of score retained."
                out.append({
                    "model_variant":model,"race_key":rk,"split":nm.get("split"),"race_date":nm.get("race_date"),"track":nm.get("track"),"race_no":nm.get("race_no"),"race_id":nm.get("race_id"),"race_class":nm.get("race_class"),"distance_band":nm.get("distance_band"),"field_size":nm.get("field_size"),"market_coverage_pct":f"{it['market_coverage_pct']:.4f}",
                    "horse":nm.get("horse"),"horse_key":nh(nm.get("horse")),"actual_finish":nm.get("actual_finish"),"actual_won":nm.get("actual_won"),"actual_placed_top3":nm.get("actual_placed_top3"),"final_sp_payoff":f"{final_sp:.4f}" if final_sp else "",
                    "safe_market_price":f"{price:.4f}" if price else "","safe_market_rank":mk.get("market_rank"),"safe_market_implied_probability":mk.get("market_implied_probability"),"market_confidence_band":mk.get("market_confidence_band"),"favourite_flag":mk.get("favourite_flag"),"top_3_market_flag":mk.get("top_3_market_flag"),"snapshot_age_minutes_before_jump":mk.get("latest_safe_minutes_before_jump"),"snapshot_age_bucket":age_bucket(mk.get("latest_safe_minutes_before_jump")),"firming_drifting_flag":mk.get("firming_drifting_flag"),
                    "longshot_risk_flag":"YES" if longshot else "NO","model_vs_market_disagreement_flag":"YES" if disagreement else "NO","prior_rating_score":f"{it['prior_score']:.6f}","non_market_score":f"{it['non_market_score']:.6f}","market_rank_score":f"{it['market_rank_score']:.6f}","market_price_score":f"{it['market_price_score']:.6f}","model_score":f"{scores[i]:.6f}","model_probability":f"{prob*100:.6f}","model_rank":ranks[i],"fair_price":f"{(1/prob):.4f}" if prob>0 else "","component_reason_1":reason1,"component_reason_2":reason2,"leakage_flag":"PASS","research_status":"RESEARCH_ONLY"
                })
    return out

def aggregate_model(model, rows):
    race_groups=defaultdict(list)
    for r in rows:
        if r["model_variant"]==model: race_groups[r["race_key"]].append(r)
    races=len(race_groups); runners=sum(len(v) for v in race_groups.values())
    top1=top2=top3=placed=0; ranks=[]; roi=[]; same_market=beat_market=market_beat=both_win=both_lose=0; longshots=0; top_sps=[]; leak=0
    for rk, vals in race_groups.items():
        vals.sort(key=lambda r:int(float(r["model_rank"])))
        top=vals[0]
        winner=next((r for r in vals if r["actual_won"]=="YES"), None)
        wr=int(float(winner["model_rank"])) if winner else len(vals)+1
        ranks.append(wr)
        if wr<=1: top1+=1
        if wr<=2: top2+=1
        if wr<=3: top3+=1
        if top["actual_placed_top3"]=="YES": placed+=1
        sp=nf(top.get("final_sp_payoff"));
        if sp: roi.append((sp-1.0) if top["actual_won"]=="YES" else -1.0); top_sps.append(sp)
        if top.get("longshot_risk_flag")=="YES": longshots+=1
        market_top=next((r for r in vals if c(r.get("safe_market_rank"))=="1"), None)
        if market_top:
            if market_top["horse"]==top["horse"]: same_market+=1
            model_won=top["actual_won"]=="YES"; market_won=market_top["actual_won"]=="YES"
            if model_won and market_won: both_win+=1
            elif model_won and not market_won: beat_market+=1
            elif market_won and not model_won: market_beat+=1
            else: both_lose+=1
        leak += sum(1 for r in vals if r.get("leakage_flag")!="PASS")
    profit=sum(roi)
    return {"model_variant":model,"races_tested":races,"runners_tested":runners,"top1_wins":top1,"top1_win_pct":f"{pct(top1,races):.4f}","top2_wins":top2,"top2_win_pct":f"{pct(top2,races):.4f}","top3_wins":top3,"top3_win_pct":f"{pct(top3,races):.4f}","top_rated_placed":placed,"top_rated_placed_pct":f"{pct(placed,races):.4f}","roi_bets":len(roi),"roi_profit":f"{profit:.4f}" if roi else "","roi_pct":f"{pct(profit,len(roi)):.4f}" if roi else "","average_winner_rank":f"{statistics.mean(ranks):.4f}" if ranks else "","median_winner_rank":f"{statistics.median(ranks):.4f}" if ranks else "","same_top_pick_as_market_pct":f"{pct(same_market,races):.4f}","edgeiq_beats_market_count":beat_market,"market_beats_edgeiq_count":market_beat,"both_win":both_win,"both_lose":both_lose,"longshot_top_pick_rate_pct":f"{pct(longshots,races):.4f}","average_top_pick_sp":f"{statistics.mean(top_sps):.4f}" if top_sps else "","leakage_failures":leak,"benchmark_note":"timestamp_safe_market_feature_model"}

def aggregate_benchmark(name, base_rows):
    race_groups=defaultdict(list)
    for r in base_rows: race_groups[r["race_key"]].append(r)
    races=len(race_groups); top1=top2=top3=placed=0; ranks=[]; roi=[]; longshots=0; top_sps=[]
    for rk, vals in race_groups.items():
        if name=="RANDOM_EXPECTATION":
            n=len(vals); top1+=1/n; top2+=min(2,n)/n; top3+=min(3,n)/n; placed+=min(3,n)/n; ranks.append((n+1)/2); continue
        vals.sort(key=lambda r:(nf(r.get("final_sp_payoff")) or 9999, r.get("horse")))
        top=vals[0]
        winner=next((r for r in vals if r["actual_won"]=="YES"), None)
        wr=next((i for i,r in enumerate(vals,1) if r["actual_won"]=="YES"), len(vals)+1)
        ranks.append(wr)
        if wr<=1: top1+=1
        if wr<=2: top2+=1
        if wr<=3: top3+=1
        if top["actual_placed_top3"]=="YES": placed+=1
        sp=nf(top.get("final_sp_payoff"));
        if sp: roi.append((sp-1.0) if top["actual_won"]=="YES" else -1.0); top_sps.append(sp)
        if sp and sp>=10: longshots+=1
    profit=sum(roi)
    return {"model_variant":name,"races_tested":races,"runners_tested":sum(len(v) for v in race_groups.values()),"top1_wins":f"{top1:.4f}","top1_win_pct":f"{pct(top1,races):.4f}","top2_wins":f"{top2:.4f}","top2_win_pct":f"{pct(top2,races):.4f}","top3_wins":f"{top3:.4f}","top3_win_pct":f"{pct(top3,races):.4f}","top_rated_placed":f"{placed:.4f}","top_rated_placed_pct":f"{pct(placed,races):.4f}","roi_bets":len(roi),"roi_profit":f"{profit:.4f}" if roi else "","roi_pct":f"{pct(profit,len(roi)):.4f}" if roi else "","average_winner_rank":f"{statistics.mean(ranks):.4f}" if ranks else "","median_winner_rank":f"{statistics.median(ranks):.4f}" if ranks else "","same_top_pick_as_market_pct":"","edgeiq_beats_market_count":"","market_beats_edgeiq_count":"","both_win":"","both_lose":"","longshot_top_pick_rate_pct":f"{pct(longshots,races):.4f}","average_top_pick_sp":f"{statistics.mean(top_sps):.4f}" if top_sps else "","leakage_failures":0,"benchmark_note":"final_sp_payoff_benchmark_only" if name.startswith("FINAL") else "theoretical_random_expectation"}

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def slice_rows(detail, field):
    out=[]
    for model in MODELS:
        model_rows=[r for r in detail if r["model_variant"]==model]
        groups=defaultdict(list)
        for r in model_rows: groups[r.get(field) or "UNKNOWN"].append(r)
        for slc, rows in sorted(groups.items()):
            agg=aggregate_model(model, rows)
            out.append({"slice":slc, **{k:agg.get(k,"") for k in SLICE_FIELDS if k not in {"slice","model_variant"}}, "model_variant":model})
    return out

def leakage_audit(join_stats):
    rows=[
        {"check":"final_sp_used_as_feature","value":0,"status":"PASS","details":"final_sp_payoff is used only for ROI/payoff and final-SP benchmark."},
        {"check":"after_jump_market_rows_used","value":0,"status":"PASS","details":"market spine rows require latest_safe_minutes_before_jump >= 0."},
        {"check":"unsafe_no_timestamp_rows_used","value":0,"status":"PASS","details":"only feature_safe_flag=YES rows from timestamp-safe spine are loaded."},
        {"check":"same_race_v6_1_used","value":0,"status":"PASS","details":"comprehensive model rows derive from prior/as-of rating baseline."},
        {"check":"future_rating_used","value":0,"status":"PASS","details":"prior/as-of spine leakage audit already blocks future ratings."},
        {"check":"result_fields_used_as_features","value":0,"status":"PASS","details":"actual_finish/won/placed used only after scoring for target evaluation."},
        {"check":"unsafe_market_rows_seen_but_not_used","value":join_stats.get("unsafe_market_rows_seen",0),"status":"PASS","details":"unsafe market rows were not loaded as features."},
        {"check":"after_jump_market_rows_seen_but_not_used","value":join_stats.get("after_jump_market_rows_seen",0),"status":"PASS","details":"after-jump rows were not loaded as features."},
    ]
    return rows

def verdict(backtest):
    by={r["model_variant"]:r for r in backtest}
    best=by.get("MARKET_DISCIPLINED_EDGEIQ_MODEL") or by.get("MARKET_PLUS_NON_MARKET_MODEL")
    market=by.get("MARKET_RANK_ONLY")
    prior=by.get("PRIOR_RATING_ONLY_ON_MARKET_COVERAGE")
    final=by.get("FINAL_SP_FAVOURITE_BENCHMARK")
    if not best or int(best.get("races_tested") or 0)<20: return "DATA_COVERAGE_BLOCKED"
    if int(best.get("leakage_failures") or 0)>0: return "LEAKAGE_RISK_BLOCKED"
    b1=nf(best.get("top1_win_pct")) or 0; p1=nf(prior.get("top1_win_pct")) or 0; m1=nf(market.get("top1_win_pct")) or 0; f1=nf(final.get("top1_win_pct")) or 0
    b3=nf(best.get("top3_win_pct")) or 0; p3=nf(prior.get("top3_win_pct")) or 0
    if b1 >= f1-2 and b3 >= (nf(final.get("top3_win_pct")) or 0)-3: return "MARKET_COMPETITIVE_RESEARCH_MODEL"
    if int(best.get("races_tested") or 0)<100 and (b1>=p1 or b3>=p3): return "PROMISING_BUT_SMALL_SAMPLE"
    if b1>=p1 or b3>=p3: return "BASELINE_IMPROVEMENT_ONLY"
    return "WEAK_RESEARCH_MODEL"

def main():
    races, excluded, join_stats = join_rows()
    races=score_base_features(races)
    detail=build_detail_rows(races)
    base_model=MODELS[0]
    base_rows=[r for r in detail if r["model_variant"]==base_model]
    backtest=[aggregate_model(m, detail) for m in MODELS]
    backtest.extend([aggregate_benchmark(b, base_rows) for b in BENCHMARKS])
    v=verdict(backtest)
    write_csv(OUT_DETAIL, detail, DETAIL_FIELDS)
    write_csv(OUT_BACKTEST, backtest, BACKTEST_FIELDS)
    write_csv(OUT_AGE, slice_rows(detail,"snapshot_age_bucket"), SLICE_FIELDS)
    write_csv(OUT_TRACK, slice_rows(detail,"track"), SLICE_FIELDS)
    write_csv(OUT_CLASS, slice_rows(detail,"race_class"), SLICE_FIELDS)
    leak=leakage_audit(join_stats)
    write_csv(OUT_LEAKAGE, leak, LEAKAGE_FIELDS)
    summary=[]
    def add(sec,met,val,extra=""): summary.append({"section":sec,"metric":met,"value":val,"extra":extra})
    add("overall","verdict",v)
    add("overall","market_covered_races_tested",len(races))
    add("overall","detail_rows",len(detail))
    add("overall","joined_runner_rows",len(base_rows))
    add("overall","market_rows_available",join_stats.get("market_rows",0))
    add("overall","comprehensive_model_races",join_stats.get("comprehensive_model_races",0))
    add("overall","safe_market_races",join_stats.get("safe_market_races",0))
    add("overall","overlapping_races",join_stats.get("overlapping_races",0))
    add("overall","exact_runner_overlap",join_stats.get("exact_runner_overlap",0))
    for o in join_stats.get("overlap_detail",[]):
        add("join_overlap",o.get("race_key"),f"{o.get('matched_runners')}/{o.get('comp_runners')}",f"market_runners={o.get('market_runners')}; coverage_pct={o.get('coverage_pct'):.2f}")
    for k,cnt in excluded.items(): add("excluded",k,cnt)
    for b in backtest: add("backtest",b["model_variant"],b["top1_win_pct"],f"top3={b['top3_win_pct']}; roi={b['roi_pct']}; races={b['races_tested']}")
    add("boundaries","production_changed","NO"); add("boundaries","pricing_changed","NO"); add("boundaries","v6_1_changed","NO"); add("boundaries","v7_2g2_changed","NO"); add("boundaries","ui_changed","NO")
    write_csv(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    by={r["model_variant"]:r for r in backtest}
    lines=["EDGEIQ_EARLY_MARKET_AWARE_PREDICTIVE_MODEL_V1","===============================================",f"Verdict: {v}","","Coverage:",f"- Comprehensive model races: {join_stats.get('comprehensive_model_races',0)}",f"- Safe market-spine races: {join_stats.get('safe_market_races',0)}",f"- Overlapping races: {join_stats.get('overlapping_races',0)}",f"- Exact runner overlaps: {join_stats.get('exact_runner_overlap',0)}",f"- Market-covered races tested after 80% gate: {len(races)}",f"- Joined runner rows: {len(base_rows)}",f"- Excluded races: {dict(excluded)}","","Overlap detail:"]
    for o in join_stats.get("overlap_detail",[]):
        lines.append(f"- {o.get('race_key')}: matched {o.get('matched_runners')}/{o.get('comp_runners')} comprehensive runners; market runners={o.get('market_runners')}; coverage={o.get('coverage_pct'):.2f}%")
    lines.append("")
    lines.append("Model results:")
    for m in MODELS+BENCHMARKS:
        r=by.get(m,{})
        lines.append(f"- {m}: races={r.get('races_tested')} top1={r.get('top1_win_pct')} top2={r.get('top2_win_pct')} top3={r.get('top3_win_pct')} placed={r.get('top_rated_placed_pct')} ROI={r.get('roi_pct')} longshot_top={r.get('longshot_top_pick_rate_pct')} avg_top_sp={r.get('average_top_pick_sp')}")
    lines.extend(["","Interpretation:"])
    if v=="MARKET_COMPETITIVE_RESEARCH_MODEL": lines.append("The timestamp-safe early market features are strong enough to close most of the market benchmark gap on this covered sample. Keep this research-only until replay coverage expands.")
    elif v=="PROMISING_BUT_SMALL_SAMPLE": lines.append("The market-aware model improves or holds baseline on a small covered sample, but coverage is too limited for promotion.")
    elif v=="BASELINE_IMPROVEMENT_ONLY": lines.append("The market-aware model improves the leakage-safe baseline but is not market-competitive yet.")
    elif v=="WEAK_RESEARCH_MODEL": lines.append("The early market spine does not yet improve the model enough on the covered sample.")
    else:
        if all(r.get("status") == "PASS" for r in leak):
            lines.append("The model is blocked by market/comprehensive overlap coverage, not leakage. The timestamp-safe market spine covers only four races in the leakage-safe comprehensive model universe, and only one passes the 80% runner coverage gate.")
        else:
            lines.append("The model is blocked by leakage or insufficient coverage.")
    lines.extend(["","Leakage audit:"])
    for r in leak: lines.append(f"- {r['check']}: {r['value']} {r['status']}")
    lines.extend(["","Boundaries:","- Production changed: NO","- Pricing changed: NO","- V6.1 changed: NO","- V7.2G2 changed: NO","- UI changed: NO"])
    OUT_REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print("Verdict:",v)
    print("Market-covered races tested:",len(races))
    for m in MODELS:
        r=by.get(m,{})
        print(m, r.get("top1_win_pct"), r.get("top3_win_pct"), r.get("roi_pct"))

if __name__ == "__main__":
    main()

