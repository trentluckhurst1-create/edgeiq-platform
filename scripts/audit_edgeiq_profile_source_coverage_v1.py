from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SOURCES = {
    "LIVE": DATA / "edgeiq_live_runner_board_governed_v1.csv",
    "RATING": DATA / "edgeiq_historical_performance_rating_v6_1_research.csv",
    "CAREER": DATA / "full_career_form.csv",
    "FORM": DATA / "runner_form_history.csv",
    "WAREHOUSE": DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv",
    "BARRIER": DATA / "edgeiq_barrier_bias_v1.csv",
}

OUT = DATA / "edgeiq_profile_source_coverage_v1.csv"
SUMMARY = DATA / "edgeiq_profile_source_coverage_v1_summary.csv"
COL_AUDIT = DATA / "edgeiq_profile_source_coverage_v1_column_audit.csv"

def canon(x):
    s = str(x or "").strip().upper()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def find_horse_col(df):
    candidates = [
        "horse",
        "horse_name",
        "runner",
        "runner_name",
        "horseName",
        "Horse",
        "runnerName",
        "selection_name",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        cl = c.lower()
        if "horse" in cl and "key" not in cl:
            return c
    for c in df.columns:
        cl = c.lower()
        if "runner" in cl and "key" not in cl:
            return c
    return ""

loaded = {}
col_rows = []

for name, path in SOURCES.items():
    if not path.exists():
        loaded[name] = pd.DataFrame()
        col_rows.append({"source": name, "path": str(path), "status": "MISSING_FILE", "horse_col": "", "rows": 0})
        continue

    df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    horse_col = find_horse_col(df)

    if horse_col:
        df["horse_key_audit"] = df[horse_col].map(canon)
        status = "OK"
    else:
        df["horse_key_audit"] = ""
        status = "NO_HORSE_COLUMN"

    loaded[name] = df
    col_rows.append({
        "source": name,
        "path": str(path),
        "status": status,
        "horse_col": horse_col,
        "rows": len(df),
        "columns_preview": "|".join(list(df.columns)[:20]),
    })

live = loaded["LIVE"]

rows = []

for horse in sorted(live["horse_key_audit"].dropna().unique()):
    if not horse:
        continue

    counts = {}
    for source_name, df in loaded.items():
        if source_name == "LIVE":
            continue
        if len(df) == 0 or "horse_key_audit" not in df.columns:
            counts[source_name] = 0
        else:
            counts[source_name] = int((df["horse_key_audit"] == horse).sum())

    best_source = max(counts, key=counts.get)
    best_count = counts[best_source]

    rating_rows = counts.get("RATING", 0)

    if best_count == 0:
        status = "NO_HISTORY_FOUND"
    elif rating_rows < best_count:
        status = "PROFILE_SOURCE_MISMATCH"
    else:
        status = "FULL_COVERAGE"

    live_names = live[live["horse_key_audit"].eq(horse)]
    display_horse = live_names.iloc[0].get("horse", horse) if len(live_names) else horse

    rows.append({
        "horse": display_horse,
        "horse_key": horse,
        "rating_rows": counts.get("RATING", 0),
        "career_rows": counts.get("CAREER", 0),
        "form_rows": counts.get("FORM", 0),
        "warehouse_rows": counts.get("WAREHOUSE", 0),
        "barrier_rows": counts.get("BARRIER", 0),
        "best_source": best_source,
        "best_count": best_count,
        "coverage_status": status,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

summary_rows = [{"metric": "status", "value": "PROFILE_SOURCE_COVERAGE_V1_COMPLETE"}]
summary_rows.append({"metric": "live_horses", "value": len(out)})

if len(out):
    for k, v in out["coverage_status"].value_counts().items():
        summary_rows.append({"metric": f"coverage_{k}", "value": int(v)})
    for k, v in out["best_source"].value_counts().items():
        summary_rows.append({"metric": f"best_source_{k}", "value": int(v)})

summary = pd.DataFrame(summary_rows)
summary.to_csv(SUMMARY, index=False)

pd.DataFrame(col_rows).to_csv(COL_AUDIT, index=False)

print("[PROFILE_SOURCE_COVERAGE_V1] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(f"column_audit={COL_AUDIT}")
