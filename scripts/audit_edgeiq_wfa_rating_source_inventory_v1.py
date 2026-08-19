from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_wfa_rating_source_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_wfa_rating_source_inventory_v1_summary.txt"

TARGET_FILES = [
    "edgeiq_historical_results_warehouse_v2_graphql.csv",
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
    "edgeiq_form_enrichment_feed_v4.csv",
    "edgeiq_form_display_clean_v2.csv",
    "edgeiq_runner_dna_drawer_feed_v2.csv",
    "edgeiq_command_enrichment_feed_v3.csv",
]

FIELD_GROUPS = {
    "horse": ["horse", "runner", "runner_name", "name"],
    "race_date": ["race_date", "date", "meeting_date"],
    "track": ["track", "venue", "course"],
    "race_no": ["race_no", "race_number", "race"],
    "age": ["age", "horse_age", "runner_age"],
    "sex": ["sex", "gender", "horse_sex", "runner_sex"],
    "weight": ["weight", "carried_weight", "weight_carried", "handicap_weight", "allocated_weight"],
    "distance": ["distance", "race_distance", "distance_m"],
    "race_class": ["race_class", "class", "race_class_clean", "grade"],
    "finish": ["finish", "finish_position", "position", "placing", "result_position"],
    "margin": ["margin", "beaten_margin", "margin_beaten"],
    "rating": ["rating", "performance_rating", "performance_rating_v6_1_research", "projected_rating", "last_start_rating"],
    "time": ["time", "race_time", "official_time"],
    "sectional": ["sectional", "last_600", "last600", "sectional_time", "closing_sectional"],
}

def norm(s):
    return str(s).strip().lower()

rows = []

for fname in TARGET_FILES:
    path = DATA / fname
    exists = path.exists()
    row = {
        "source_file": fname,
        "exists": exists,
        "rows": 0,
        "columns": 0,
        "read_status": "MISSING" if not exists else "PENDING",
    }

    if exists:
        try:
            df = pd.read_csv(path, nrows=5000, low_memory=False)
            cols = list(df.columns)
            lower_cols = {norm(c): c for c in cols}

            row["rows"] = sum(1 for _ in open(path, "r", encoding="utf-8", errors="ignore")) - 1
            row["columns"] = len(cols)
            row["read_status"] = "OK"

            for group, candidates in FIELD_GROUPS.items():
                matched = [lower_cols[c] for c in candidates if c in lower_cols]
                row[f"has_{group}"] = bool(matched)
                row[f"{group}_fields"] = " | ".join(matched)

            critical = ["horse", "race_date", "age", "sex", "weight", "distance", "race_class", "finish", "margin", "rating"]
            present = sum(1 for c in critical if row.get(f"has_{c}") is True)
            row["critical_wfa_fields_present"] = present
            row["critical_wfa_fields_possible"] = len(critical)
            row["wfa_source_score_pct"] = round((present / len(critical)) * 100, 2)

        except Exception as e:
            row["read_status"] = f"ERROR: {e}"

    rows.append(row)

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT, index=False)

existing = out_df[out_df["exists"] == True]
best = existing.sort_values("wfa_source_score_pct", ascending=False).head(10) if not existing.empty else pd.DataFrame()

summary_lines = []
summary_lines.append("EDGEIQ_WFA_RATING_SOURCE_INVENTORY_V1")
summary_lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
summary_lines.append(f"target_files={len(TARGET_FILES)}")
summary_lines.append(f"existing_files={int(out_df['exists'].sum())}")
summary_lines.append("")
summary_lines.append("BEST SOURCES:")
if best.empty:
    summary_lines.append("No existing target files found.")
else:
    for _, r in best.iterrows():
        summary_lines.append(
            f"{r['source_file']} | score={r.get('wfa_source_score_pct', 0)}% | rows={r.get('rows', 0)} | status={r.get('read_status')}"
        )

SUMMARY.write_text("\n".join(summary_lines), encoding="utf-8")

print("[EDGEIQ_WFA_RATING_SOURCE_INVENTORY_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(out_df[["source_file", "exists", "rows", "columns", "read_status", "wfa_source_score_pct"]].to_string(index=False))
