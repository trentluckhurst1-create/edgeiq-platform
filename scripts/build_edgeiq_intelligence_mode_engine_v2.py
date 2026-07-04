from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path("public/data")
V1 = DATA / "edgeiq_intelligence_mode_engine_v1.csv"
GEAR = DATA / "edgeiq_gear_signal_engine_v1.csv"
DEBUT = DATA / "edgeiq_debutant_intelligence_engine_v1.csv"
MARKET = DATA / "edgeiq_market_alignment_engine_v1.csv"
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
OUT = DATA / "edgeiq_intelligence_mode_engine_v2.csv"
SUMMARY = DATA / "edgeiq_intelligence_mode_engine_v2_summary.csv"
REPORT = DATA / "edgeiq_intelligence_mode_engine_v2_report.txt"

def clean(v): return "" if pd.isna(v) else str(v).strip()
def nt(v): return re.sub(r"\s+", " ", clean(v).upper()).strip()
def nr(v):
    s = clean(v).upper().replace("R", "")
    try: return str(int(float(s)))
    except Exception: return s
def num(v, default=0.0):
    try: return float(str(v).replace("%", "").strip())
    except Exception: return default
def race_key(row): return f"{nt(row.get('track',''))}|{nr(row.get('race_no',''))}"
def pct(a,b): return (a/b*100.0) if b else 0.0

gov = pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)
v1 = pd.read_csv(V1, dtype=str, keep_default_na=False, low_memory=False) if V1.exists() else pd.DataFrame()
gear = pd.read_csv(GEAR, dtype=str, keep_default_na=False, low_memory=False) if GEAR.exists() else pd.DataFrame()
debut = pd.read_csv(DEBUT, dtype=str, keep_default_na=False, low_memory=False) if DEBUT.exists() else pd.DataFrame()
market = pd.read_csv(MARKET, dtype=str, keep_default_na=False, low_memory=False) if MARKET.exists() else pd.DataFrame()

v1_map = {race_key(r): r for _, r in v1.iterrows()} if not v1.empty else {}
gear_groups = {k: g for k, g in gear.groupby(gear.apply(race_key, axis=1))} if not gear.empty else {}
debut_groups = {k: g for k, g in debut.groupby(debut.apply(race_key, axis=1))} if not debut.empty else {}
market_groups = {k: g for k, g in market.groupby(market.apply(race_key, axis=1))} if not market.empty else {}

rows = []
for rk, group in gov.groupby(gov.apply(race_key, axis=1), sort=False):
    sample = group.iloc[0]
    runners = len(group)
    base = v1_map.get(rk, {})
    projection_cov = num(base.get("projection_coverage_pct", ""), None) if hasattr(base, 'get') else None
    no_proj_pct = num(base.get("no_projection_pct", ""), None) if hasattr(base, 'get') else None
    if projection_cov is None:
        no_proj = group.get("no_projection_flag", pd.Series([""]*runners)).astype(str).str.upper().eq("YES").sum()
        no_proj_pct = pct(no_proj, runners)
        projection_cov = 100 - no_proj_pct
    gg = gear_groups.get(rk, pd.DataFrame())
    gear_available = int((gg.get("gear_signal_band", pd.Series(dtype=str)).astype(str) != "NO_GEAR").sum()) if not gg.empty else 0
    gear_pct = pct(gear_available, runners)
    dg = debut_groups.get(rk, pd.DataFrame())
    debut_pos = int(dg.get("debutant_intelligence_band", pd.Series(dtype=str)).astype(str).isin(["ELITE", "POSITIVE", "INTERESTING"]).sum()) if not dg.empty else 0
    first_starter_pct = num(base.get("first_starter_pct", ""), 0) if hasattr(base, 'get') else 0
    if first_starter_pct == 0 and not dg.empty:
        no_hist = dg.get("no_history_flag", pd.Series(dtype=str)).astype(str).str.upper().eq("YES").sum()
        first_starter_pct = pct(no_hist, runners)
    mg = market_groups.get(rk, pd.DataFrame())
    market_available = 0
    if not mg.empty:
        band = mg.get("market_alignment_band", pd.Series(dtype=str)).astype(str).str.strip()
        market_available = int(band.ne("").sum())
    market_cov = num(base.get("market_coverage_pct", ""), pct(market_available, runners)) if hasattr(base, 'get') else pct(market_available, runners)
    market_status = "AVAILABLE" if market_cov > 0 or market_available > 0 else "UNAVAILABLE"
    pace_cov = num(base.get("pace_coverage_pct", ""), pct(group.get("run_style", pd.Series(dtype=str)).astype(str).str.strip().ne("").sum(), runners)) if hasattr(base, 'get') else 0
    conn_cov = num(base.get("connection_coverage_pct", ""), 0) if hasattr(base, 'get') else 0
    if first_starter_pct >= 25:
        mode = "DEBUTANT_DRIVEN"
        weights = {"ratings":5,"connections":35,"gear":20,"market":15,"debutant":25,"pace":0}
        path = "Debutant, connections and gear context lead the analysis."
    elif projection_cov < 70 or no_proj_pct > 30:
        mode = "LOW_CONFIDENCE"
        weights = {"ratings":0,"connections":30,"gear":20,"market":25,"debutant":15,"pace":10}
        path = "Low projection coverage; lean on non-rating intelligence."
    elif gear_pct >= 20 or conn_cov >= 60:
        mode = "BALANCED"
        weights = {"ratings":35,"connections":25,"gear":15,"market":15,"debutant":0,"pace":10}
        path = "Ratings remain important, but supporting intelligence is material."
    else:
        mode = "RATINGS_DRIVEN"
        weights = {"ratings":55,"connections":10,"gear":5,"market":10,"debutant":0,"pace":20}
        path = "Ratings and pace are the primary lens."
    if gear_pct == 0:
        weights["gear"] = 0
    if market_status == "UNAVAILABLE":
        weights["market"] = 0
    confidence = max(0, min(100, projection_cov * 0.45 + pace_cov * 0.2 + conn_cov * 0.15 + gear_pct * 0.1 + (market_cov if market_status == "AVAILABLE" else 0) * 0.1))
    rows.append({
        "track": clean(sample.get("track", "")),
        "race_no": clean(sample.get("race_no", "")),
        "runners": runners,
        "projection_coverage_pct": round(projection_cov, 2),
        "no_projection_pct": round(no_proj_pct, 2),
        "gear_coverage_pct": round(gear_pct, 2),
        "market_coverage_pct": round(market_cov, 2),
        "market_status": market_status,
        "debutant_signal_pct": round(first_starter_pct, 2),
        "pace_coverage_pct": round(pace_cov, 2),
        "connection_coverage_pct": round(conn_cov, 2),
        "intelligence_mode_v2": mode,
        "intelligence_confidence_v2": round(confidence, 1),
        "ratings_weight": weights["ratings"],
        "connections_weight": weights["connections"],
        "gear_weight": weights["gear"],
        "market_weight": weights["market"],
        "debutant_weight": weights["debutant"],
        "pace_weight": weights["pace"],
        "primary_analysis_path": path,
        "race_intelligence_summary": f"{mode}: projection coverage {projection_cov:.1f}%, gear coverage {gear_pct:.1f}%, market {market_status.lower()}.",
        "production_changed": "NO",
        "pricing_changed": "NO",
        "built_at": datetime.now(timezone.utc).isoformat(),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
mode_counts = out["intelligence_mode_v2"].value_counts().to_dict() if not out.empty else {}
summary_rows = [
    {"metric": "status", "value": "EDGEIQ_INTELLIGENCE_MODE_ENGINE_V2_BUILT"},
    {"metric": "races", "value": len(out)},
]
for k, v in sorted(mode_counts.items()):
    summary_rows.append({"metric": f"mode_{k}", "value": int(v)})
summary_rows.extend([
    {"metric": "avg_confidence", "value": round(float(out["intelligence_confidence_v2"].mean()), 2) if not out.empty else 0},
    {"metric": "gear_available_races", "value": int((out["gear_coverage_pct"] > 0).sum()) if not out.empty else 0},
    {"metric": "market_unavailable_races", "value": int((out["market_status"] == "UNAVAILABLE").sum()) if not out.empty else 0},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
])
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_INTELLIGENCE_MODE_ENGINE_V2",
    "==================================",
    f"Races: {len(out)}",
    f"Mode counts: {mode_counts}",
    f"Gear available races: {int((out['gear_coverage_pct'] > 0).sum()) if not out.empty else 0}",
    f"Market unavailable races: {int((out['market_status'] == 'UNAVAILABLE').sum()) if not out.empty else 0}",
    "Production changed: NO",
    "Pricing changed: NO",
]) + "\n", encoding="utf-8")
print("INTELLIGENCE_MODE_V2_COMPLETE", len(out), mode_counts)
