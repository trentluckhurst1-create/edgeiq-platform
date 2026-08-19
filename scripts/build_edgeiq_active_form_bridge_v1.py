from pathlib import Path
import pandas as pd
import re

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
SUMMARY = DATA / "form_card_summary.csv"
OUT = DATA / "edgeiq_active_form_bridge_v1.csv"
DIAG = DATA / "edgeiq_active_form_bridge_diagnostics_v1.csv"

def clean_key(x):
    s = str(x or "").upper()
    s = s.replace("’", "").replace("'", "")
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s.strip()

live = pd.read_csv(LIVE, low_memory=False)
summary = pd.read_csv(SUMMARY, low_memory=False)

live["_horse_key_bridge"] = live["horse_key"].map(clean_key)
summary["_horse_key_bridge"] = summary["horse_key"].map(clean_key)

summary_cols = [
    "_horse_key_bridge", "horse", "race_date", "track", "race_no",
    "1LS", "2LS", "3LS", "4LS", "5LS", "3LSA", "5LSA", "PEAK", "official_run_count"
]

summary_small = summary[[c for c in summary_cols if c in summary.columns]].copy()

merged = live.merge(
    summary_small,
    on="_horse_key_bridge",
    how="left",
    suffixes=("", "_form_summary_bridge")
)

patch_map = {
    "bridge_1ls": "1LS",
    "bridge_2ls": "2LS",
    "bridge_3ls": "3LS",
    "bridge_4ls": "4LS",
    "bridge_5ls": "5LS",
    "bridge_3lsa": "3LSA",
    "bridge_5lsa": "5LSA",
    "bridge_peak": "PEAK",
    "bridge_official_run_count": "official_run_count",
}

for new_col, source_col in patch_map.items():
    merged[new_col] = merged[source_col] if source_col in merged.columns else ""

merged["active_form_bridge_matched"] = merged["bridge_official_run_count"].notna()
merged["active_form_bridge_grade"] = merged["bridge_official_run_count"].apply(
    lambda x: "NO_FORM" if pd.isna(x) or float(x or 0) <= 0 else (
        "LIGHT" if float(x) < 3 else (
            "MEDIUM" if float(x) < 8 else "STRONG"
        )
    )
)

merged["active_form_bridge_reason"] = merged.apply(
    lambda r: "matched form_card_summary by horse_key" if r["active_form_bridge_matched"] else "no form_card_summary match",
    axis=1
)

keep_cols = [
    "horse", "horse_key", "track", "race_date", "race_no",
    "bridge_1ls", "bridge_2ls", "bridge_3ls", "bridge_4ls", "bridge_5ls",
    "bridge_3lsa", "bridge_5lsa", "bridge_peak", "bridge_official_run_count",
    "active_form_bridge_matched", "active_form_bridge_grade", "active_form_bridge_reason"
]

bridge = merged[[c for c in keep_cols if c in merged.columns]].copy()
bridge.to_csv(OUT, index=False)

for c in ["active_form_bridge_matched", "active_form_bridge_grade", "active_form_bridge_reason",
          "bridge_1ls", "bridge_2ls", "bridge_3ls", "bridge_4ls", "bridge_5ls",
          "bridge_3lsa", "bridge_5lsa", "bridge_peak", "bridge_official_run_count"]:
    live[c] = merged[c]

live.to_csv(LIVE, index=False)

diag = pd.DataFrame([{
    "live_rows": len(live),
    "bridge_matches": int(merged["active_form_bridge_matched"].sum()),
    "bridge_match_pct": round(float(merged["active_form_bridge_matched"].mean() * 100), 2),
    "strong_form_profiles": int((merged["active_form_bridge_grade"] == "STRONG").sum()),
    "medium_form_profiles": int((merged["active_form_bridge_grade"] == "MEDIUM").sum()),
    "light_form_profiles": int((merged["active_form_bridge_grade"] == "LIGHT").sum()),
    "no_form_profiles": int((merged["active_form_bridge_grade"] == "NO_FORM").sum()),
}])

diag.to_csv(DIAG, index=False)

print("SAVED:", OUT)
print("SAVED:", DIAG)
print(diag.to_string(index=False))
print(bridge.to_string(index=False))
