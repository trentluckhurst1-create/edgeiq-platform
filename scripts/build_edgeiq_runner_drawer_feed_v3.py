from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path("public/data")
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
GEAR = DATA / "edgeiq_gear_signal_engine_v1.csv"
DEBUT = DATA / "edgeiq_debutant_intelligence_engine_v1.csv"
MODE = DATA / "edgeiq_intelligence_mode_engine_v2.csv"
OUT = DATA / "edgeiq_runner_drawer_feed_v3.csv"
SUMMARY = DATA / "edgeiq_runner_drawer_feed_v3_summary.csv"
REPORT = DATA / "edgeiq_runner_drawer_feed_v3_report.txt"

def clean(v): return "" if pd.isna(v) else str(v).strip()
def nt(v): return re.sub(r"\s+", " ", clean(v).upper()).strip()
def nr(v):
    s=clean(v).upper().replace("R", "")
    try: return str(int(float(s)))
    except Exception: return s
def nh(v): return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())
def row_key(r): return f"{clean(r.get('race_date',''))}|{nt(r.get('track',''))}|{nr(r.get('race_no',''))}|{nh(r.get('horse_key', r.get('horse','')))}"
def race_key(r): return f"{nt(r.get('track',''))}|{nr(r.get('race_no',''))}"

gov = pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)
gear = pd.read_csv(GEAR, dtype=str, keep_default_na=False, low_memory=False) if GEAR.exists() else pd.DataFrame()
debut = pd.read_csv(DEBUT, dtype=str, keep_default_na=False, low_memory=False) if DEBUT.exists() else pd.DataFrame()
mode = pd.read_csv(MODE, dtype=str, keep_default_na=False, low_memory=False) if MODE.exists() else pd.DataFrame()
gear_map = {row_key(r): r for _, r in gear.iterrows()} if not gear.empty else {}
debut_map = {row_key(r): r for _, r in debut.iterrows()} if not debut.empty else {}
mode_map = {race_key(r): r for _, r in mode.iterrows()} if not mode.empty else {}

rows=[]
for _, r in gov.iterrows():
    out = r.to_dict()
    g = gear_map.get(row_key(r), {})
    d = debut_map.get(row_key(r), {})
    m = mode_map.get(race_key(r), {})
    gear_band = clean(g.get("gear_signal_band", "NO_GEAR")) if hasattr(g, 'get') else "NO_GEAR"
    gear_summary = clean(g.get("gear_summary", "No listed gear change for this runner.")) if hasattr(g, 'get') else "No listed gear change for this runner."
    debut_summary = clean(d.get("debutant_intelligence_summary", "")) if hasattr(d, 'get') else ""
    if not debut_summary:
        debut_summary = "No debutant-specific intelligence triggered for this runner."
    mode_name = clean(m.get("intelligence_mode_v2", "")) if hasattr(m, 'get') else ""
    mode_summary = clean(m.get("race_intelligence_summary", "")) if hasattr(m, 'get') else ""
    low_warning = ""
    if clean(r.get("no_projection_flag", "")).upper() == "YES":
        low_warning = "Projection coverage is limited; use supporting intelligence with caution."
    elif mode_name == "LOW_CONFIDENCE":
        low_warning = "Race-level data confidence is reduced; avoid over-weighting a single lens."
    primary_lens = "Ratings"
    if mode_name == "LOW_CONFIDENCE": primary_lens = "Connections / Market / Gear context"
    elif mode_name == "BALANCED": primary_lens = "Balanced intelligence"
    elif mode_name == "DEBUTANT_DRIVEN": primary_lens = "Debutant and stable intelligence"
    out.update({
        "gear_panel_title": "Gear Intelligence" if gear_band != "NO_GEAR" else "Gear Intelligence - No Listed Change",
        "gear_panel_summary": gear_summary,
        "debutant_panel_summary": debut_summary,
        "intelligence_mode_summary": mode_summary,
        "low_data_warning": low_warning,
        "primary_edgeiq_lens": primary_lens,
        "gear_signal_band": gear_band,
        "gear_signal_score": clean(g.get("gear_signal_score", "0")) if hasattr(g, 'get') else "0",
        "intelligence_mode_v2": mode_name,
        "intelligence_confidence_v2": clean(m.get("intelligence_confidence_v2", "")) if hasattr(m, 'get') else "",
        "production_changed": "NO",
        "pricing_changed": "NO",
        "built_at": datetime.now(timezone.utc).isoformat(),
    })
    rows.append(out)

outdf = pd.DataFrame(rows)
outdf.to_csv(OUT, index=False)
summary_rows = [
    {"metric": "status", "value": "EDGEIQ_RUNNER_DRAWER_FEED_V3_BUILT"},
    {"metric": "governed_rows", "value": len(gov)},
    {"metric": "output_rows", "value": len(outdf)},
    {"metric": "rows_with_gear_panel", "value": int(outdf["gear_panel_summary"].astype(str).str.strip().ne("").sum())},
    {"metric": "rows_with_no_gear", "value": int((outdf["gear_signal_band"] == "NO_GEAR").sum())},
    {"metric": "rows_with_low_data_warning", "value": int(outdf["low_data_warning"].astype(str).str.strip().ne("").sum())},
    {"metric": "production_changed", "value": "NO"},
    {"metric": "pricing_changed", "value": "NO"},
    {"metric": "built_at", "value": datetime.now(timezone.utc).isoformat()},
]
pd.DataFrame(summary_rows).to_csv(SUMMARY, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_RUNNER_DRAWER_FEED_V3",
    "============================",
    f"Rows: {len(outdf)}",
    f"Rows with no gear: {int((outdf['gear_signal_band'] == 'NO_GEAR').sum())}",
    f"Rows with low data warning: {int(outdf['low_data_warning'].astype(str).str.strip().ne('').sum())}",
    "No UI wire performed.",
    "Production changed: NO",
    "Pricing changed: NO",
]) + "\n", encoding="utf-8")
print("RUNNER_DRAWER_V3_COMPLETE", len(outdf))
