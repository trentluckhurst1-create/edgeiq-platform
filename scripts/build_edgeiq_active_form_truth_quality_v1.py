from pathlib import Path
import pandas as pd

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

LIVE = DATA / "edgeiq_execution_board_live.csv"
TRUTH = DATA / "edgeiq_active_runner_form_truth_v1.csv"
OUT = DATA / "edgeiq_active_form_truth_quality_v1.csv"
DIAG = DATA / "edgeiq_active_form_truth_quality_diagnostics_v1.csv"

live = pd.read_csv(LIVE, low_memory=False)
truth = pd.read_csv(TRUTH, low_memory=False)

df = truth.copy()

def score_row(r):
    score = 0
    notes = []

    if str(r.get("horse_key", "")).strip():
        score += 10
    else:
        notes.append("missing horse_key")

    if str(r.get("track", "")).strip():
        score += 10
    else:
        notes.append("missing track")

    if pd.notna(r.get("race_date", "")):
        score += 10
    else:
        notes.append("missing race_date")

    if pd.notna(r.get("race_no", "")):
        score += 10
    else:
        notes.append("missing race_no")

    run_count = pd.to_numeric(r.get("active_truth_official_run_count", 0), errors="coerce")
    run_count = 0 if pd.isna(run_count) else run_count

    if run_count >= 8:
        score += 35
    elif run_count >= 3:
        score += 25
    elif run_count >= 1:
        score += 15
    else:
        notes.append("no official run depth")

    if pd.notna(r.get("active_truth_peak", None)):
        score += 15
    else:
        notes.append("missing peak rating")

    if pd.notna(r.get("active_truth_3lsa", None)) or pd.notna(r.get("active_truth_5lsa", None)):
        score += 10
    else:
        notes.append("missing recent rating averages")

    return score, "; ".join(notes) if notes else "OK"

scores = df.apply(score_row, axis=1, result_type="expand")
df["active_truth_quality_score"] = scores[0]
df["active_truth_quality_notes"] = scores[1]

df["active_truth_quality_grade"] = df["active_truth_quality_score"].apply(
    lambda x: "ELITE" if x >= 90 else (
        "GOOD" if x >= 75 else (
            "THIN" if x >= 55 else "POOR"
        )
    )
)

df["active_truth_execution_guidance"] = df.apply(
    lambda r:
        "ALLOW_MODEL_WEIGHT"
        if r["active_truth_quality_grade"] in ["ELITE", "GOOD"]
        else (
            "REDUCE_MODEL_WEIGHT"
            if r["active_truth_quality_grade"] == "THIN"
            else "MARKET_LED_ONLY"
        ),
    axis=1
)

df.to_csv(OUT, index=False)

patch = df[[
    "horse_key",
    "active_truth_quality_score",
    "active_truth_quality_grade",
    "active_truth_quality_notes",
    "active_truth_execution_guidance",
]].copy()

live = live.merge(
    patch,
    on="horse_key",
    how="left",
    suffixes=("", "_new")
)

for c in [
    "active_truth_quality_score",
    "active_truth_quality_grade",
    "active_truth_quality_notes",
    "active_truth_execution_guidance",
]:
    new_col = c + "_new"
    if new_col in live.columns:
        live[c] = live[new_col].combine_first(live[c] if c in live.columns else None)
        live = live.drop(columns=[new_col])

live.to_csv(LIVE, index=False)

diag = pd.DataFrame([{
    "rows": len(df),
    "elite": int((df["active_truth_quality_grade"] == "ELITE").sum()),
    "good": int((df["active_truth_quality_grade"] == "GOOD").sum()),
    "thin": int((df["active_truth_quality_grade"] == "THIN").sum()),
    "poor": int((df["active_truth_quality_grade"] == "POOR").sum()),
    "market_led_only": int((df["active_truth_execution_guidance"] == "MARKET_LED_ONLY").sum()),
    "reduce_model_weight": int((df["active_truth_execution_guidance"] == "REDUCE_MODEL_WEIGHT").sum()),
    "allow_model_weight": int((df["active_truth_execution_guidance"] == "ALLOW_MODEL_WEIGHT").sum()),
}])

diag.to_csv(DIAG, index=False)

print("=" * 100)
print("EDGEIQ ACTIVE FORM TRUTH QUALITY V1")
print("=" * 100)
print(diag.to_string(index=False))
print()
print(df.to_string(index=False))
print()
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("PATCHED:", LIVE)
