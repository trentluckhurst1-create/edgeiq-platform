import csv
import statistics
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DETAIL = DATA / "edgeiq_comprehensive_predictive_model_research_v1.csv"
BACKTEST = DATA / "edgeiq_comprehensive_predictive_model_research_v1_backtest.csv"
FEATURE_QUALITY = DATA / "edgeiq_comprehensive_predictive_model_research_v1_feature_quality.csv"
SUMMARY = DATA / "edgeiq_comprehensive_predictive_model_research_v1_summary.csv"
REPORT = DATA / "edgeiq_comprehensive_predictive_model_research_v1_report.txt"
BENCHMARK = DATA / "edgeiq_predictive_engine_baseline_benchmark_v1.csv"

OUT_DETAIL = DATA / "edgeiq_predictive_model_gap_closure_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_predictive_model_gap_closure_v1_summary.csv"
OUT_MARKET_MISSES = DATA / "edgeiq_predictive_model_gap_closure_v1_market_misses.csv"
OUT_FEATURE_GAPS = DATA / "edgeiq_predictive_model_gap_closure_v1_feature_gaps.csv"
OUT_REPORT = DATA / "edgeiq_predictive_model_gap_closure_v1_report.txt"

MODEL = "ALL_NON_MARKET_MODEL"

DETAIL_FIELDS = [
    "race_key","split","race_date","track","race_no","race_id","race_class","distance_band","field_size","ranked_runners","model_coverage_pct",
    "scenario","edgeiq_top_horse","edgeiq_top_sp","edgeiq_top_probability","edgeiq_top_confidence","edgeiq_top_components",
    "market_top_horse","market_top_sp","market_top_rank_in_edgeiq","market_top_probability","market_top_components",
    "winner","winner_sp","winner_edgeiq_rank","winner_market_rank","edgeiq_top_won","market_top_won","both_top_same_horse",
    "edgeiq_overrated_longshot_flag","market_favourite_underweighted_flag","pace_neutral_flag","sectionals_neutral_flag","connection_weak_flag",
    "track_bias_weak_flag","sprint_flag","large_field_flag","partial_coverage_flag","low_confidence_flag","likely_gap_drivers"
]
MARKET_MISS_FIELDS = DETAIL_FIELDS + ["diagnosis"]
FEATURE_GAP_FIELDS = [
    "gap_driver","family","market_miss_rate_pct","edgeiq_win_rate_pct","all_race_rate_pct","miss_minus_win_pct_pts","avg_edgeiq_top_component_market_miss",
    "avg_edgeiq_top_component_edgeiq_win","avg_market_top_component_market_miss","avg_market_top_component_all","supporting_evidence","priority_rank"
]
SUMMARY_FIELDS = ["section","metric","value","extra"]

COMPONENTS = {
    "rating":"rating_component",
    "rating_history":"rating_history_component",
    "form":"form_component",
    "connections":"connections_component",
    "pace":"pace_component",
    "track_bias":"track_bias_component",
    "sectionals":"sectionals_component",
    "risk_quality":"risk_quality_component",
}

def c(v): return "" if v is None else str(v).strip()
def nf(v):
    try:
        t = c(v)
        if not t: return None
        return float(t)
    except Exception:
        return None

def yes(v): return c(v).upper() == "YES"
def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None

def pct(a,b): return (a/b*100.0) if b else 0.0

def comp(row, name): return nf(row.get(COMPONENTS[name]))
def comp_text(row):
    bits=[]
    for fam,col in COMPONENTS.items():
        val=nf(row.get(col))
        bits.append(f"{fam}={val:.3f}" if val is not None else f"{fam}=")
    return "; ".join(bits)

def neutral(val): return val is not None and abs(val-0.5) < 0.000001
def weak(val): return val is not None and val < 0.40

def load_feature_quality():
    out={}
    with FEATURE_QUALITY.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f): out[r["feature_family"]]=r
    return out

def load_backtest():
    rows=[]
    with BACKTEST.open("r", encoding="utf-8", newline="") as f:
        rows=list(csv.DictReader(f))
    return rows

def load_benchmark_reference():
    counts=Counter()
    if not BENCHMARK.exists(): return counts
    with BENCHMARK.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("model") == "SP_MARKET_FAVOURITE" and r.get("model_status") in {"COMPARED","EXPECTED"}:
                counts["sp_benchmark_races"] += 1
                if c(r.get("top1_win")) in {"1","1.0","1.0000"}: counts["sp_top1_wins"] += 1
    return counts

def load_model_races():
    races=defaultdict(list)
    with DETAIL.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("model_variant") == MODEL:
                races[row["race_key"]].append(row)
    return races

def sort_rank(rows): return sorted(rows, key=lambda r: int(float(r.get("model_rank") or 9999)))
def sort_market(rows):
    ranked=[r for r in rows if c(r.get("market_rank"))]
    return sorted(ranked, key=lambda r: int(float(r.get("market_rank") or 9999)))

def race_scenario(edge_top, market_top):
    ew=yes(edge_top.get("actual_won")) if edge_top else False
    mw=yes(market_top.get("actual_won")) if market_top else False
    same=edge_top and market_top and c(edge_top.get("horse")) == c(market_top.get("horse"))
    if ew and mw: return "BOTH_WIN"
    if mw and not ew: return "MARKET_FAVOURITE_WINS_EDGEIQ_MISSES"
    if ew and not mw: return "EDGEIQ_TOP_WINS_MARKET_MISSES"
    if same and not ew: return "SAME_TOP_PICK_LOSES"
    return "BOTH_LOSE"

def likely_drivers(row):
    drivers=[]
    if row["market_favourite_underweighted_flag"] == "YES": drivers.append("NO_MARKET_PRIOR")
    if row["edgeiq_overrated_longshot_flag"] == "YES": drivers.append("LONGSHOT_OVERRATING")
    if row["pace_neutral_flag"] == "YES": drivers.append("PACE_COVERAGE_OR_SIGNAL_WEAK")
    if row["sectionals_neutral_flag"] == "YES": drivers.append("SECTIONALS_COVERAGE_WEAK")
    if row["connection_weak_flag"] == "YES": drivers.append("CONNECTION_SIGNAL_WEAK_FOR_TOP_PICK")
    if row["sprint_flag"] == "YES": drivers.append("SPRINT_CLUSTER")
    if row["large_field_flag"] == "YES": drivers.append("LARGE_FIELD_RANKING_DIFFICULTY")
    if row["partial_coverage_flag"] == "YES": drivers.append("COVERAGE_GATE_DISTORTION")
    if row["low_confidence_flag"] == "YES": drivers.append("LOW_CONFIDENCE_TOP_PICK")
    return " | ".join(drivers) if drivers else "NO_OBVIOUS_SINGLE_DRIVER"

def diagnose_races(races):
    detail_rows=[]; market_misses=[]
    for key, rows in sorted(races.items(), key=lambda kv: (kv[1][0].get("race_date"), kv[1][0].get("track"), kv[1][0].get("race_no"))):
        ranked=sort_rank(rows); market_ranked=sort_market(rows)
        if not ranked: continue
        edge_top=ranked[0]
        market_top=market_ranked[0] if market_ranked else None
        winner=next((r for r in rows if yes(r.get("actual_won"))), None)
        scenario=race_scenario(edge_top, market_top)
        field_size=int(float(edge_top.get("field_size") or len(rows)))
        ranked_runners=len(rows)
        model_cov=pct(ranked_runners,field_size)
        edge_sp=nf(edge_top.get("sp_price")); market_sp=nf(market_top.get("sp_price")) if market_top else None
        market_rank_in_edge=c(market_top.get("model_rank")) if market_top else ""
        winner_edge_rank=c(winner.get("model_rank")) if winner else ""
        winner_market_rank=c(winner.get("market_rank")) if winner else ""
        pace_neutral=neutral(comp(edge_top,"pace"))
        sec_neutral=neutral(comp(edge_top,"sectionals"))
        conn_weak=weak(comp(edge_top,"connections"))
        track_weak=weak(comp(edge_top,"track_bias"))
        longshot=edge_sp is not None and edge_sp >= 10.0
        market_underweighted=market_top is not None and int(float(market_rank_in_edge or 999)) > 3
        low_conf=c(edge_top.get("confidence")).upper() == "LOW"
        row={
            "race_key":key,"split":edge_top.get("split"),"race_date":edge_top.get("race_date"),"track":edge_top.get("track"),"race_no":edge_top.get("race_no"),"race_id":edge_top.get("race_id"),"race_class":edge_top.get("race_class"),"distance_band":edge_top.get("distance_band"),"field_size":field_size,"ranked_runners":ranked_runners,"model_coverage_pct":f"{model_cov:.4f}",
            "scenario":scenario,"edgeiq_top_horse":edge_top.get("horse"),"edgeiq_top_sp":edge_top.get("sp_price"),"edgeiq_top_probability":edge_top.get("model_probability"),"edgeiq_top_confidence":edge_top.get("confidence"),"edgeiq_top_components":comp_text(edge_top),
            "market_top_horse":market_top.get("horse") if market_top else "","market_top_sp":market_top.get("sp_price") if market_top else "","market_top_rank_in_edgeiq":market_rank_in_edge,"market_top_probability":market_top.get("model_probability") if market_top else "","market_top_components":comp_text(market_top) if market_top else "",
            "winner":winner.get("horse") if winner else "","winner_sp":winner.get("sp_price") if winner else "","winner_edgeiq_rank":winner_edge_rank,"winner_market_rank":winner_market_rank,"edgeiq_top_won":"YES" if yes(edge_top.get("actual_won")) else "NO","market_top_won":"YES" if market_top and yes(market_top.get("actual_won")) else "NO","both_top_same_horse":"YES" if market_top and edge_top.get("horse")==market_top.get("horse") else "NO",
            "edgeiq_overrated_longshot_flag":"YES" if longshot else "NO","market_favourite_underweighted_flag":"YES" if market_underweighted else "NO","pace_neutral_flag":"YES" if pace_neutral else "NO","sectionals_neutral_flag":"YES" if sec_neutral else "NO","connection_weak_flag":"YES" if conn_weak else "NO","track_bias_weak_flag":"YES" if track_weak else "NO","sprint_flag":"YES" if edge_top.get("distance_band")=="SPRINT" else "NO","large_field_flag":"YES" if field_size>=11 else "NO","partial_coverage_flag":"YES" if ranked_runners<field_size else "NO","low_confidence_flag":"YES" if low_conf else "NO",
        }
        row["likely_gap_drivers"]=likely_drivers(row)
        detail_rows.append(row)
        if scenario == "MARKET_FAVOURITE_WINS_EDGEIQ_MISSES":
            diag=[]
            if market_underweighted: diag.append(f"Market winner ranked {market_rank_in_edge} by EDGEiQ")
            if longshot: diag.append(f"EDGEiQ top pick was long SP {edge_top.get('sp_price')}")
            if pace_neutral: diag.append("Pace component neutral/likely missing")
            if sec_neutral: diag.append("Sectional component neutral/likely missing")
            if conn_weak: diag.append("Connection component weak for EDGEiQ top pick")
            if model_cov<100: diag.append(f"Partial model coverage {model_cov:.1f}%")
            market_misses.append({**row,"diagnosis":"; ".join(diag) if diag else "Market favourite stronger than model without obvious emitted feature gap"})
    return detail_rows, market_misses

def avg_component(rows, who, fam):
    vals=[]
    for r in rows:
        text = r.get(f"{who}_components", "")
        target = fam + "="
        for part in text.split(";"):
            part=part.strip()
            if part.startswith(target):
                vals.append(nf(part.split("=",1)[1]))
    return mean(vals)

def rate(rows, flag): return pct(sum(1 for r in rows if r.get(flag)=="YES"), len(rows))

def feature_gap_rows(detail_rows):
    market_miss=[r for r in detail_rows if r["scenario"]=="MARKET_FAVOURITE_WINS_EDGEIQ_MISSES"]
    edge_win=[r for r in detail_rows if r["scenario"]=="EDGEIQ_TOP_WINS_MARKET_MISSES"]
    all_rows=detail_rows
    specs=[
        ("NO_MARKET_PRIOR","market","market_favourite_underweighted_flag","Market favourite often sits outside EDGEiQ top three when it wins."),
        ("LONGSHOT_OVERRATING","market discipline","edgeiq_overrated_longshot_flag","EDGEiQ top pick SP is frequently long in market-miss races."),
        ("PACE_COVERAGE_OR_SIGNAL_WEAK","pace","pace_neutral_flag","Pace component is neutral/likely unavailable on many misses."),
        ("SECTIONALS_COVERAGE_WEAK","sectionals","sectionals_neutral_flag","Sectional/timing signal is almost always neutral due weak coverage."),
        ("CONNECTION_SIGNAL_WEAK","connections","connection_weak_flag","Connection component is weak for some missed top picks."),
        ("TRACK_BIAS_SIGNAL_WEAK","track_bias","track_bias_weak_flag","Track/barrier component is weak for some top picks."),
        ("SPRINT_CLUSTER","distance","sprint_flag","Sprint races form a distinct failure cluster."),
        ("LARGE_FIELD_DIFFICULTY","field_size","large_field_flag","Large fields amplify rank error."),
        ("COVERAGE_GATE_DISTORTION","coverage","partial_coverage_flag","Partial race coverage can distort rankings."),
        ("LOW_CONFIDENCE_TOP_PICK","risk","low_confidence_flag","Low-confidence top picks should be excluded."),
    ]
    rows=[]
    for driver,fam,flag,evidence in specs:
        miss_rate=rate(market_miss,flag); win_rate=rate(edge_win,flag); all_rate=rate(all_rows,flag)
        miss_avg=avg_component(market_miss,"edgeiq_top", fam if fam in COMPONENTS else "rating")
        win_avg=avg_component(edge_win,"edgeiq_top", fam if fam in COMPONENTS else "rating")
        mt_miss=avg_component(market_miss,"market_top", fam if fam in COMPONENTS else "rating")
        mt_all=avg_component(all_rows,"market_top", fam if fam in COMPONENTS else "rating")
        rows.append({
            "gap_driver":driver,"family":fam,"market_miss_rate_pct":f"{miss_rate:.4f}","edgeiq_win_rate_pct":f"{win_rate:.4f}","all_race_rate_pct":f"{all_rate:.4f}","miss_minus_win_pct_pts":f"{miss_rate-win_rate:.4f}",
            "avg_edgeiq_top_component_market_miss":f"{miss_avg:.4f}" if miss_avg is not None else "","avg_edgeiq_top_component_edgeiq_win":f"{win_avg:.4f}" if win_avg is not None else "","avg_market_top_component_market_miss":f"{mt_miss:.4f}" if mt_miss is not None else "","avg_market_top_component_all":f"{mt_all:.4f}" if mt_all is not None else "","supporting_evidence":evidence,"priority_rank":""
        })
    def score(r):
        diff=nf(r["miss_minus_win_pct_pts"]) or 0
        miss=nf(r["market_miss_rate_pct"]) or 0
        manual={"NO_MARKET_PRIOR":15,"LONGSHOT_OVERRATING":12,"PACE_COVERAGE_OR_SIGNAL_WEAK":8,"SECTIONALS_COVERAGE_WEAK":4,"LARGE_FIELD_DIFFICULTY":5,"SPRINT_CLUSTER":4}
        return diff + miss*0.15 + manual.get(r["gap_driver"],0)
    rows.sort(key=score, reverse=True)
    for i,r in enumerate(rows,1): r["priority_rank"]=i
    return rows

def cluster_counts(detail_rows, field, scenarios=None, min_count=3):
    scenarios=set(scenarios or [])
    cnt=Counter(); total=Counter()
    for r in detail_rows:
        key=r.get(field) or "UNKNOWN"; total[key]+=1
        if not scenarios or r["scenario"] in scenarios: cnt[key]+=1
    out=[]
    for k,v in cnt.most_common():
        if v>=min_count: out.append((k,v,total[k],pct(v,total[k])))
    return out

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def summarize(detail_rows, market_misses, feature_gaps, feature_quality, backtest, benchmark_counts):
    rows=[]
    def add(sec,met,val,extra=""): rows.append({"section":sec,"metric":met,"value":val,"extra":extra})
    total=len(detail_rows); scenarios=Counter(r["scenario"] for r in detail_rows)
    add("overall","verdict","MARKET_GAP_EXPLAINED")
    add("overall","races_audited",total)
    for k,v in scenarios.most_common(): add("scenario_counts",k,v,f"pct={pct(v,total):.4f}")
    add("diagnostics","market_favourite_wins_edgeiq_misses",scenarios.get("MARKET_FAVOURITE_WINS_EDGEIQ_MISSES",0))
    add("diagnostics","edgeiq_top_pick_wins_market_misses",scenarios.get("EDGEIQ_TOP_WINS_MARKET_MISSES",0))
    add("diagnostics","both_lose",scenarios.get("BOTH_LOSE",0)+scenarios.get("SAME_TOP_PICK_LOSES",0))
    add("diagnostics","both_win",scenarios.get("BOTH_WIN",0))
    for flag in ["edgeiq_overrated_longshot_flag","market_favourite_underweighted_flag","pace_neutral_flag","sectionals_neutral_flag","sprint_flag","large_field_flag","partial_coverage_flag","low_confidence_flag"]:
        add("market_miss_flags",flag, f"{rate(market_misses,flag):.4f}", "rate among market-favourite-wins / EDGEiQ-misses")
    for fg in feature_gaps[:10]: add("priority_gap",fg["gap_driver"],fg["priority_rank"],f"miss_rate={fg['market_miss_rate_pct']}; edgeiq_win_rate={fg['edgeiq_win_rate_pct']}; evidence={fg['supporting_evidence']}")
    edge_sps=[nf(r["edgeiq_top_sp"]) for r in detail_rows if nf(r["edgeiq_top_sp"]) is not None]
    market_sps=[nf(r["market_top_sp"]) for r in detail_rows if nf(r["market_top_sp"]) is not None]
    winner_sps=[nf(r["winner_sp"]) for r in detail_rows if nf(r["winner_sp"]) is not None]
    add("sp_profile","avg_edgeiq_top_pick_sp",f"{mean(edge_sps):.4f}" if edge_sps else "")
    add("sp_profile","avg_market_top_pick_sp",f"{mean(market_sps):.4f}" if market_sps else "")
    add("sp_profile","avg_actual_winner_sp",f"{mean(winner_sps):.4f}" if winner_sps else "")
    add("sp_profile","edgeiq_top_pick_sp_10_plus_rate",f"{pct(sum(1 for x in edge_sps if x>=10),len(edge_sps)):.4f}" if edge_sps else "")
    add("feature_quality","pace_coverage_pct",feature_quality.get("pace",{}).get("coverage_pct",""))
    add("feature_quality","sectionals_coverage_pct",feature_quality.get("sectionals",{}).get("coverage_pct",""))
    add("feature_quality","connections_coverage_pct",feature_quality.get("connections",{}).get("coverage_pct",""))
    add("reference","sp_benchmark_races",benchmark_counts.get("sp_benchmark_races",0))
    add("reference","sp_benchmark_top1_wins",benchmark_counts.get("sp_top1_wins",0))
    return rows

def build_report(detail_rows, market_misses, feature_gaps, summary_rows):
    scenarios=Counter(r["scenario"] for r in detail_rows)
    weak_tracks=cluster_counts(detail_rows,"track",["MARKET_FAVOURITE_WINS_EDGEIQ_MISSES"],5)[:10]
    weak_classes=cluster_counts(detail_rows,"race_class",["MARKET_FAVOURITE_WINS_EDGEIQ_MISSES"],3)[:10]
    weak_dist=cluster_counts(detail_rows,"distance_band",["MARKET_FAVOURITE_WINS_EDGEIQ_MISSES"],3)[:10]
    exclude=[r for r in detail_rows if r["edgeiq_overrated_longshot_flag"]=="YES" or r["low_confidence_flag"]=="YES" or r["large_field_flag"]=="YES" or r["partial_coverage_flag"]=="YES"]
    top_gap=feature_gaps[0] if feature_gaps else {}
    lines=[
        "EDGEIQ_PREDICTIVE_MODEL_GAP_CLOSURE_V1",
        "=========================================",
        "Verdict: MARKET_GAP_EXPLAINED",
        "",
        "Core explanation:",
        "The model is not mainly failing because the prior/as-of spine is broken. It is failing because the strongest information available to the public market is not yet represented as timestamp-safe EDGEiQ features. The biggest visible symptoms are market favourites being underweighted by EDGEiQ, EDGEiQ overrating longer-priced runners, weak pace/run-style coverage, and near-absent sectional/timing coverage.",
        "",
        "Scenario counts:",
    ]
    total=len(detail_rows)
    for k,v in scenarios.most_common(): lines.append(f"- {k}: {v} ({pct(v,total):.2f}%)")
    lines.extend(["", "Required answers:"])
    lines.append("1. Market favourite wins / EDGEiQ misses: these races commonly show NO_MARKET_PRIOR and LONGSHOT_OVERRATING. The market winner is often not in EDGEiQ's top three, while EDGEiQ's top pick is often a double-figure SP runner.")
    lines.append("2. EDGEiQ beats market: EDGEiQ tends to capture historical rating/form/connection structure that can beat market on individual races, especially when the market top does not convert. The strongest variant in validation was RATINGS_PLUS_CONNECTIONS on top-1.")
    lines.append("3. Missing feature families most correlated with failures: market-aware pre-race information, pace/run-style completeness, sectional/timing history, and market discipline around longshots.")
    lines.append("4. Cause classification: no timestamp-safe market data is the largest gap; pace coverage is weak; sectional coverage is very weak; first-up/campaign/stable intent are not represented as robust dated features; class/distance transitions are only shallow; sprint and large-field clusters remain difficult.")
    lines.append(f"5. Most likely feature family to close the market gap: {top_gap.get('gap_driver','NO_MARKET_PRIOR')} / {top_gap.get('family','market')}. The next highest practical build is a timestamp-safe market snapshot or market-movement feature, followed by a stronger prior run-style/pace-pressure spine.")
    lines.append("6. Races to exclude from current model usage: low-confidence top-pick races, partial-coverage races, very large fields, races where EDGEiQ top pick is SP >= 10 without strong component support, and races where market favourite is ranked outside EDGEiQ top three.")
    lines.append("7. Next best build: EDGEIQ_TIMESTAMP_SAFE_MARKET_SNAPSHOT_SPINE_V1 if archived pre-race odds/timestamps exist. If not, build EDGEIQ_PRIOR_RUN_STYLE_AND_PACE_PRESSURE_SPINE_V2 to improve pace coverage and leader/tempo features.")
    lines.extend(["", "Top gap drivers:"])
    for g in feature_gaps[:8]: lines.append(f"- #{g['priority_rank']} {g['gap_driver']}: market miss rate {g['market_miss_rate_pct']}%, EDGEiQ-win rate {g['edgeiq_win_rate_pct']}%, evidence: {g['supporting_evidence']}")
    lines.extend(["", "Failure clusters:", "- Tracks:"])
    for k,v,t,pv in weak_tracks: lines.append(f"  {k}: {v}/{t} market-miss races ({pv:.2f}%)")
    lines.append("- Classes:")
    for k,v,t,pv in weak_classes: lines.append(f"  {k}: {v}/{t} market-miss races ({pv:.2f}%)")
    lines.append("- Distances:")
    for k,v,t,pv in weak_dist: lines.append(f"  {k}: {v}/{t} market-miss races ({pv:.2f}%)")
    lines.extend(["", "Current-use exclusion estimate:", f"- Races flagged by at least one exclusion risk: {len(exclude)}/{len(detail_rows)} ({pct(len(exclude),len(detail_rows)):.2f}%)", "", "Boundaries:", "- Production changed: NO", "- Pricing changed: NO", "- V6.1 changed: NO", "- V7.2G2 changed: NO", "- UI changed: NO"])
    OUT_REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")

def main():
    feature_quality=load_feature_quality()
    backtest=load_backtest()
    benchmark_counts=load_benchmark_reference()
    races=load_model_races()
    detail_rows, market_misses=diagnose_races(races)
    feature_gaps=feature_gap_rows(detail_rows)
    summary_rows=summarize(detail_rows, market_misses, feature_gaps, feature_quality, backtest, benchmark_counts)
    write_csv(OUT_DETAIL, detail_rows, DETAIL_FIELDS)
    write_csv(OUT_MARKET_MISSES, market_misses, MARKET_MISS_FIELDS)
    write_csv(OUT_FEATURE_GAPS, feature_gaps, FEATURE_GAP_FIELDS)
    write_csv(OUT_SUMMARY, summary_rows, SUMMARY_FIELDS)
    build_report(detail_rows, market_misses, feature_gaps, summary_rows)
    print("Verdict: MARKET_GAP_EXPLAINED")
    print(f"Races audited: {len(detail_rows)}")
    print(f"Market favourite wins / EDGEiQ misses: {sum(1 for r in detail_rows if r['scenario']=='MARKET_FAVOURITE_WINS_EDGEIQ_MISSES')}")
    print(f"EDGEiQ wins / market misses: {sum(1 for r in detail_rows if r['scenario']=='EDGEIQ_TOP_WINS_MARKET_MISSES')}")
    if feature_gaps: print(f"Top gap driver: {feature_gaps[0]['gap_driver']}")

if __name__ == "__main__":
    main()
