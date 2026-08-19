import pandas as pd
from pathlib import Path
import re, math
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

form_path = DATA / "edgeiq_form_enrichment_feed_v1.csv"

candidate_files = [
    DATA / "edgeiq_historical_performance_rating_v6_1_research.csv",
    DATA / "edgeiq_runner_form_engine_current.csv",
    DATA / "edgeiq_runner_trajectory_feed_v1.csv",
    DATA / "edgeiq_runners_enrichment_feed_v1_1.csv",
    DATA / "edgeiq_runner_dna_drawer_feed_v2.csv",
    DATA / "edgeiq_command_enrichment_feed_v3.csv",
]

out = DATA / "edgeiq_form_no_history_all_sources_trace_v1.csv"
summary_out = DATA / "edgeiq_form_no_history_all_sources_trace_v1_summary.csv"
report_out = DATA / "edgeiq_form_no_history_all_sources_trace_v1_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def strip_suffixes(s):
    s = clean(s)
    s = re.sub(r"\s*\((NZ|GB|IRE|USA|FR|JPN|SAF|GER|CAN|ARG|BRZ|CHI|HK|AUS)\)\s*$", "", s)
    s = re.sub(r"\s*\([0-9]+E\)\s*$", "", s)
    return s.strip()

def hkey(v):
    return "".join(ch for ch in strip_suffixes(v) if ch.isalnum())

form = pd.read_csv(form_path, low_memory=False)
no_hist = form[form["form_truth_status"].astype(str).str.upper().eq("NO_HISTORY")].copy()

source_maps = {}
source_cols = {}

for path in candidate_files:
    if not path.exists():
        continue
    df = pd.read_csv(path, low_memory=False)
    horse_cols = [c for c in df.columns if c.lower() in ["horse", "runner", "horse_name"] or "horse" in c.lower()]
    if not horse_cols:
        continue

    form_cols = [c for c in df.columns if any(x in c.lower() for x in [
        "last_start", "rating", "finish", "margin", "form", "history", "trend", "start", "distance", "track", "class", "condition"
    ])]

    keys = {}
    for _, r in df.iterrows():
        for hc in horse_cols[:4]:
            k = hkey(r.get(hc, ""))
            if k:
                keys.setdefault(k, 0)
                keys[k] += 1

    source_maps[path.name] = keys
    source_cols[path.name] = " | ".join(form_cols[:80])

rows = []

for _, r in no_hist.iterrows():
    k = hkey(r.get("horse", ""))
    hits = []
    for source, mp in source_maps.items():
        count = mp.get(k, 0)
        if count:
            hits.append(f"{source}:{count}")

    classification = "TRUE_NO_HISTORY_OR_WAREHOUSE_GAP"
    if hits:
        classification = "HISTORY_EXISTS_IN_OTHER_SOURCE_REQUIRES_FORM_BACKFILL"

    rows.append({
        "race_date": r.get("race_date",""),
        "track": r.get("track",""),
        "race_no": r.get("race_no",""),
        "horse": r.get("horse",""),
        "horse_key": k,
        "classification": classification,
        "source_hits": " | ".join(hits),
    })

trace = pd.DataFrame(rows)
trace.to_csv(out, index=False)

summary = trace.groupby("classification").size().reset_index(name="count").sort_values("count", ascending=False)
summary = pd.concat([pd.DataFrame([{"classification":"TOTAL_NO_HISTORY_REVIEWED","count":len(trace)}]), summary], ignore_index=True)
summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_NO_HISTORY_ALL_SOURCES_TRACE_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))
    f.write("\n\nSOURCE FORM COLUMNS\n")
    for source, cols in source_cols.items():
        f.write(f"\n--- {source} ---\n{cols}\n")
    f.write("\n\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n")

print("[EDGEIQ_FORM_NO_HISTORY_ALL_SOURCES_TRACE_V1] COMPLETE")
print(summary.to_string(index=False))
print(out)
