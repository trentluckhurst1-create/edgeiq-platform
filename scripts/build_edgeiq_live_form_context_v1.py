from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
RUNS = DATA / "form_card_runs.csv"
SUMMARY = DATA / "form_card_summary.csv"
OUT = DATA / "edgeiq_live_form_context_v1.csv"
DIAG = DATA / "edgeiq_live_form_context_diagnostics_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False)
runs = pd.read_csv(RUNS, low_memory=False)
summary = pd.read_csv(SUMMARY, low_memory=False)

live["_hk"] = live["horse_key"].map(clean_key)
runs["_hk"] = runs["horse_key"].map(clean_key)
summary["_hk"] = summary["horse_key"].map(clean_key)

runs["run_rating"] = pd.to_numeric(runs["run_rating"], errors="coerce")

official_runs = runs[
    runs["is_official_race"].astype(str).str.upper().isin(["TRUE", "1"])
].copy()

agg = official_runs.groupby("_hk").agg(
    live_official_run_count=("run_rating", "count"),
    live_last3_avg=("run_rating", lambda s: round(s.tail(3).mean(), 2) if len(s.dropna()) else None),
    live_last5_avg=("run_rating", lambda s: round(s.tail(5).mean(), 2) if len(s.dropna()) else None),
    live_peak_rating=("run_rating", "max"),
).reset_index()

merged = live.merge(agg, on="_hk", how="left")

summary_small = summary[[
    c for c in [
        "_hk", "1LS", "2LS", "3LS", "4LS", "5LS",
        "3LSA", "5LSA", "PEAK", "official_run_count"
    ]
    if c in summary.columns
]]

merged = merged.merge(summary_small, on="_hk", how="left")

merged["live_form_context_grade"] = merged["live_official_run_count"].apply(
    lambda x:
        "NO_FORM" if pd.isna(x) or x <= 0 else
        "LIGHTLY_RACED" if x < 3 else
        "EXPOSED" if x >= 8 else
        "DEVELOPING"
)

merged["live_form_context_reason"] = merged.apply(
    lambda r:
        "full exposed profile"
        if r["live_form_context_grade"] == "EXPOSED"
        else (
            "developing runner profile"
            if r["live_form_context_grade"] == "DEVELOPING"
            else (
                "limited official exposure"
                if r["live_form_context_grade"] == "LIGHTLY_RACED"
                else "no official form"
            )
        ),
    axis=1
)

keep = [
    "horse",
    "horse_key",
    "track",
    "race_no",
    "live_official_run_count",
    "live_last3_avg",
    "live_last5_avg",
    "live_peak_rating",
    "1LS",
    "2LS",
    "3LS",
    "4LS",
    "5LS",
    "3LSA",
    "5LSA",
    "PEAK",
    "live_form_context_grade",
    "live_form_context_reason",
]

out = merged[[c for c in keep if c in merged.columns]].copy()

out.to_csv(OUT, index=False)

patch_cols = [
    "live_official_run_count",
    "live_last3_avg",
    "live_last5_avg",
    "live_peak_rating",
    "live_form_context_grade",
    "live_form_context_reason",
]

for c in patch_cols:
    live[c] = merged[c]

live.to_csv(LIVE, index=False)

diag = pd.DataFrame([{
    "live_rows": len(live),
    "matched_live_form_profiles": int(merged["live_official_run_count"].fillna(0).gt(0).sum()),
    "exposed_profiles": int((merged["live_form_context_grade"] == "EXPOSED").sum()),
    "developing_profiles": int((merged["live_form_context_grade"] == "DEVELOPING").sum()),
    "lightly_raced_profiles": int((merged["live_form_context_grade"] == "LIGHTLY_RACED").sum()),
    "no_form_profiles": int((merged["live_form_context_grade"] == "NO_FORM").sum()),
}])

diag.to_csv(DIAG, index=False)

print("SAVED:", OUT)
print("SAVED:", DIAG)
print(diag.to_string(index=False))
print(out.to_string(index=False))
