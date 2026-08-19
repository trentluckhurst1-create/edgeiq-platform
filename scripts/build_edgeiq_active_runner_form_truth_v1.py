from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
SUMMARY = DATA / "form_card_summary.csv"
OFFICIAL = DATA / "edgeiq_official_runs_master_v1.csv"

OUT = DATA / "edgeiq_active_runner_form_truth_v1.csv"
DIAG = DATA / "edgeiq_active_runner_form_truth_diagnostics_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

def num(x):
    return pd.to_numeric(x, errors="coerce")

live = pd.read_csv(LIVE, low_memory=False).copy()
summary = pd.read_csv(SUMMARY, low_memory=False).copy()
official = pd.read_csv(OFFICIAL, low_memory=False).copy()

live["_hk"] = live["horse_key"].map(clean_key)
summary["_hk"] = summary["horse_key"].map(clean_key)
official["_hk"] = official["horse_key"].map(clean_key)

summary_cols = ["_hk", "1LS", "2LS", "3LS", "4LS", "5LS", "3LSA", "5LSA", "PEAK", "official_run_count"]
summary_small = summary[[c for c in summary_cols if c in summary.columns]].copy()

for c in ["1LS", "2LS", "3LS", "4LS", "5LS", "3LSA", "5LSA", "PEAK", "official_run_count"]:
    if c in summary_small.columns:
        summary_small[c] = num(summary_small[c])

official["race_date"] = pd.to_datetime(official["race_date"], errors="coerce")
official["rating_proxy"] = num(official.get("sp", ""))

official_agg = official.groupby("_hk").agg(
    official_archive_rows=("horse", "count"),
    official_archive_race_rows=("official_run_flag", lambda s: int(s.astype(str).str.upper().isin(["TRUE", "1"]).sum())),
    latest_official_run=("race_date", "max"),
).reset_index()

merged = live.merge(summary_small, on="_hk", how="left", suffixes=("", "_summary"))
merged = merged.merge(official_agg, on="_hk", how="left")

merged["summary_match"] = merged["1LS"].notna() | merged["official_run_count_summary"].notna()
merged["archive_match"] = merged["official_archive_rows"].fillna(0).gt(0)

merged["active_truth_official_run_count"] = merged["official_run_count_summary"]
merged["active_truth_official_run_count"] = merged["active_truth_official_run_count"].fillna(merged["official_archive_race_rows"])
merged["active_truth_official_run_count"] = merged["active_truth_official_run_count"].fillna(0)

merged["active_truth_1ls"] = merged["1LS"]
merged["active_truth_2ls"] = merged["2LS"]
merged["active_truth_3ls"] = merged["3LS"]
merged["active_truth_4ls"] = merged["4LS"]
merged["active_truth_5ls"] = merged["5LS"]
merged["active_truth_3lsa"] = merged["3LSA"]
merged["active_truth_5lsa"] = merged["5LSA"]
merged["active_truth_peak"] = merged["PEAK"]

merged["active_truth_grade"] = merged["active_truth_official_run_count"].apply(
    lambda x: "FIRST_STARTER" if x <= 0 else ("LIGHT" if x < 3 else ("DEVELOPING" if x < 8 else "EXPOSED"))
)

merged["active_truth_confidence"] = merged["active_truth_grade"].map({
    "FIRST_STARTER": "VERY_LOW",
    "LIGHT": "LOW",
    "DEVELOPING": "MEDIUM",
    "EXPOSED": "HIGH",
}).fillna("VERY_LOW")

merged["active_truth_source"] = merged.apply(
    lambda r: "FORM_SUMMARY" if r["summary_match"] else ("OFFICIAL_ARCHIVE" if r["archive_match"] else "LIVE_BOARD_ONLY"),
    axis=1
)

patch_cols = [
    "active_truth_official_run_count",
    "active_truth_1ls",
    "active_truth_2ls",
    "active_truth_3ls",
    "active_truth_4ls",
    "active_truth_5ls",
    "active_truth_3lsa",
    "active_truth_5lsa",
    "active_truth_peak",
    "active_truth_grade",
    "active_truth_confidence",
    "active_truth_source",
]

for c in patch_cols:
    live[c] = merged[c]

live.to_csv(LIVE, index=False)

out_cols = [
    "horse", "horse_key", "track", "race_date", "race_no",
    "active_truth_source",
    "active_truth_official_run_count",
    "active_truth_1ls",
    "active_truth_2ls",
    "active_truth_3ls",
    "active_truth_4ls",
    "active_truth_5ls",
    "active_truth_3lsa",
    "active_truth_5lsa",
    "active_truth_peak",
    "active_truth_grade",
    "active_truth_confidence",
]

out = merged[[c for c in out_cols if c in merged.columns]].copy()
out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "live_rows": len(out),
    "form_summary_matches": int(merged["summary_match"].sum()),
    "official_archive_matches": int(merged["archive_match"].sum()),
    "first_starters": int((merged["active_truth_grade"] == "FIRST_STARTER").sum()),
    "light_profiles": int((merged["active_truth_grade"] == "LIGHT").sum()),
    "developing_profiles": int((merged["active_truth_grade"] == "DEVELOPING").sum()),
    "exposed_profiles": int((merged["active_truth_grade"] == "EXPOSED").sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ ACTIVE RUNNER FORM TRUTH V1")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(out.to_string(index=False))
print()
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("PATCHED:", LIVE)
