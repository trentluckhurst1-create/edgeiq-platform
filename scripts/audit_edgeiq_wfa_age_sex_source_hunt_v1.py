from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_wfa_age_sex_source_hunt_v1.csv"
SUMMARY = DATA / "edgeiq_wfa_age_sex_source_hunt_v1_summary.txt"

AGE_NAMES = ["age", "horse_age", "runner_age", "age_years"]
SEX_NAMES = ["sex", "gender", "horse_sex", "runner_sex", "sex_code"]
WEIGHT_NAMES = ["weight", "carried_weight", "weight_carried", "handicap_weight", "allocated_weight"]
KEY_NAMES = ["horse", "runner", "runner_name", "race_date", "date", "track", "venue", "race_no", "race_number", "distance"]

def norm(s):
    return str(s).strip().lower()

def has_any(cols, names):
    lower = {norm(c): c for c in cols}
    return [lower[n] for n in names if n in lower]

rows = []

for path in sorted(DATA.glob("*.csv")):
    try:
        df = pd.read_csv(path, nrows=1000, low_memory=False)
        cols = list(df.columns)

        age_cols = has_any(cols, AGE_NAMES)
        sex_cols = has_any(cols, SEX_NAMES)
        weight_cols = has_any(cols, WEIGHT_NAMES)
        key_cols = has_any(cols, KEY_NAMES)

        if age_cols or sex_cols or weight_cols:
            rows.append({
                "source_file": path.name,
                "columns": len(cols),
                "sample_rows_read": len(df),
                "age_fields": " | ".join(age_cols),
                "sex_fields": " | ".join(sex_cols),
                "weight_fields": " | ".join(weight_cols),
                "key_fields": " | ".join(key_cols),
                "has_age": bool(age_cols),
                "has_sex": bool(sex_cols),
                "has_weight": bool(weight_cols),
                "has_basic_join_keys": ("horse" in [norm(c) for c in key_cols] or "runner" in [norm(c) for c in key_cols] or "runner_name" in [norm(c) for c in key_cols]),
            })

    except Exception:
        continue

out_df = pd.DataFrame(rows)
if not out_df.empty:
    out_df = out_df.sort_values(
        ["has_age", "has_sex", "has_weight", "source_file"],
        ascending=[False, False, False, True]
    )

out_df.to_csv(OUT, index=False)

lines = []
lines.append("EDGEIQ_WFA_AGE_SEX_SOURCE_HUNT_V1")
lines.append(f"built_at={datetime.now(timezone.utc).isoformat()}")
lines.append(f"csv_files_scanned={len(list(DATA.glob('*.csv')))}")
lines.append(f"candidate_files={len(out_df)}")
lines.append("")
lines.append("TOP CANDIDATES:")
if out_df.empty:
    lines.append("No age/sex/weight candidate files found.")
else:
    for _, r in out_df.head(40).iterrows():
        lines.append(
            f"{r['source_file']} | age={r['age_fields']} | sex={r['sex_fields']} | weight={r['weight_fields']} | keys={r['key_fields']}"
        )

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("[EDGEIQ_WFA_AGE_SEX_SOURCE_HUNT_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
if out_df.empty:
    print("No candidates found")
else:
    print(out_df.head(60).to_string(index=False))
