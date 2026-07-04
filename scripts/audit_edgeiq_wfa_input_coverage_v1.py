from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_wfa_input_coverage_v1.csv"
SUMMARY = DATA / "edgeiq_wfa_input_coverage_v1_summary.txt"

SOURCE_FILES = [
    "edgeiq_historical_results_warehouse_v2_graphql.csv",
    "edgeiq_historical_performance_rating_v6_1_research.csv",
]

ALIASES = {
    "horse": ["horse", "runner", "runner_name", "name"],
    "race_date": ["race_date", "date", "meeting_date"],
    "age": ["age", "horse_age", "runner_age"],
    "sex": ["sex", "gender", "horse_sex", "runner_sex"],
    "weight": ["weight", "carried_weight", "weight_carried", "handicap_weight", "allocated_weight"],
    "distance": ["distance", "race_distance", "distance_m"],
    "race_class": ["race_class", "class", "race_class_clean", "grade"],
    "finish": ["finish", "finish_position", "position", "placing", "result_position"],
    "margin": ["margin", "beaten_margin", "margin_beaten"],
    "rating": ["rating", "performance_rating", "performance_rating_v6_1_research", "projected_rating", "last_start_rating"],
}

def norm(s):
    return str(s).strip().lower()

def find_col(cols, names):
    lower = {norm(c): c for c in cols}
    for n in names:
        if n in lower:
            return lower[n]
    return None

def nonblank(series):
    if series is None:
        return pd.Series([], dtype=bool)
    return series.notna() & (series.astype(str).str.strip() != "") & (series.astype(str).str.strip() != "0")

rows = []

for fname in SOURCE_FILES:
    path = DATA / fname
    if not path.exists():
        rows.append({
            "source_file": fname,
            "status": "MISSING",
            "rows": 0
        })
        continue

    df = pd.read_csv(path, low_memory=False)
    cols = list(df.columns)

    found = {k: find_col(cols, v) for k, v in ALIASES.items()}

    checks = {}
    for key, col in found.items():
        if col:
            checks[key] = nonblank(df[col])
        else:
            checks[key] = pd.Series([False] * len(df))

    full_ready = (
        checks["horse"] &
        checks["race_date"] &
        checks["age"] &
        checks["sex"] &
        checks["weight"] &
        checks["distance"] &
        checks["race_class"] &
        checks["finish"] &
        checks["margin"] &
        checks["rating"]
    )

    weight_only_ready = (
        checks["horse"] &
        checks["race_date"] &
        checks["weight"] &
        checks["distance"] &
        checks["finish"] &
        checks["margin"] &
        checks["rating"] &
        ~(checks["age"] & checks["sex"])
    )

    def count(mask):
        return int(mask.sum())

    total = len(df)

    row = {
        "source_file": fname,
        "status": "OK",
        "rows": total,
    }

    for key, col in found.items():
        row[f"{key}_field"] = col or ""
        row[f"{key}_nonblank"] = count(checks[key])
        row[f"{key}_coverage_pct"] = round((count(checks[key]) / total) * 100, 2) if total else 0

    row["FULL_WFA_READY"] = count(full_ready)
    row["FULL_WFA_READY_PCT"] = round((count(full_ready) / total) * 100, 2) if total else 0
    row["WEIGHT_ONLY_READY"] = count(weight_only_ready)
    row["WEIGHT_ONLY_READY_PCT"] = round((count(weight_only_ready) / total) * 100, 2) if total else 0

    row["AGE_SEX_MISSING"] = count(~(checks["age"] & checks["sex"]))
    row["WEIGHT_MISSING"] = count(~checks["weight"])
    row["CLASS_MISSING"] = count(~checks["race_class"])
    row["DISTANCE_MISSING"] = count(~checks["distance"])
    row["RATING_MISSING"] = count(~checks["rating"])

    if row["FULL_WFA_READY"] > 0:
        row["best_status"] = "FULL_WFA_READY"
    elif row["WEIGHT_ONLY_READY"] > 0:
        row["best_status"] = "WEIGHT_ONLY_READY"
    elif row["WEIGHT_MISSING"] >= total:
        row["best_status"] = "WEIGHT_MISSING"
    elif row["AGE_SEX_MISSING"] >= total:
        row["best_status"] = "AGE_SEX_MISSING"
    elif row["RATING_MISSING"] >= total:
        row["best_status"] = "RATING_MISSING"
    else:
        row["best_status"] = "PARTIAL_NOT_READY"

    rows.append(row)

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT, index=False)

lines = []
lines.append("EDGEIQ_WFA_INPUT_COVERAGE_V1")
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append("")
for _, r in out_df.iterrows():
    lines.append(f"{r['source_file']}")
    lines.append(f"  status={r['status']}")
    lines.append(f"  rows={r['rows']}")
    lines.append(f"  best_status={r.get('best_status', '')}")
    lines.append(f"  FULL_WFA_READY={r.get('FULL_WFA_READY', 0)} ({r.get('FULL_WFA_READY_PCT', 0)}%)")
    lines.append(f"  WEIGHT_ONLY_READY={r.get('WEIGHT_ONLY_READY', 0)} ({r.get('WEIGHT_ONLY_READY_PCT', 0)}%)")
    lines.append(f"  age_field={r.get('age_field', '')}")
    lines.append(f"  sex_field={r.get('sex_field', '')}")
    lines.append(f"  weight_field={r.get('weight_field', '')}")
    lines.append(f"  rating_field={r.get('rating_field', '')}")
    lines.append("")

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("[EDGEIQ_WFA_INPUT_COVERAGE_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(out_df.to_string(index=False))
