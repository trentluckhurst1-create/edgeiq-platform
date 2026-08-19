from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import re

DATA = Path(r".\public\data")
SRC = DATA / "edgeiq_class_pars_v5_2.csv"
AUDIT = DATA / "edgeiq_class_pars_v5_2_full_ladder_repair_audit.csv"

df = pd.read_csv(SRC, dtype=str, keep_default_na=False, low_memory=False)

def n(v):
    return " ".join(str(v).upper().strip().split())

df["race_class_clean_v5_2"] = df["race_class_clean_v5_2"].map(n)

# Full sane ladder. This preserves the existing useful scale but fixes corrupted low-sample BM classes.
ladder = {
    "MAIDEN": 81.70,
    "CLASS 1": 83.81,
    "CLASS 2": 84.85,
    "CLASS 3": 85.43,
    "CLASS 4": 86.25,
    "CLASS 5": 87.00,
    "CLASS 6": 87.50,

    "BM45": 85.80,
    "BM50": 87.06,
    "BM52": 87.35,
    "BM54": 87.70,
    "BM55": 87.95,
    "BM56": 88.89,
    "BM58": 88.89,
    "BM60": 88.55,
    "BM62": 89.85,
    "BM64": 89.51,
    "BM65": 89.75,
    "BM66": 90.09,
    "BM67": 90.30,
    "BM68": 89.61,
    "BM70": 91.09,
    "BM71": 91.25,
    "BM72": 90.99,
    "BM74": 92.00,
    "BM75": 92.10,
    "BM76": 92.30,
    "BM77": 92.45,
    "BM78": 92.65,
    "BM80": 93.00,
    "BM82": 92.19,
    "BM84": 93.78,
    "BM85": 93.95,
    "BM88": 94.60,
    "BM90": 95.00,
    "BM94": 95.80,
    "BM96": 96.20,
    "BM100": 97.00,
    "BM115": 98.00,
    "BM120": 98.50,

    "OPEN": 95.00,
    "SET WEIGHTS": 95.71,
    "SET WEIGHTS PENALTIES": 96.00,
    "LISTED": 97.74,
    "GROUP 3": 99.27,
    "GROUP 2": 100.55,
    "GROUP 1": 100.82,
}

# Enforce smooth BM ladder for any BM class not explicitly sensible.
def bm_expected(cls):
    m = re.fullmatch(r"BM(\d+)", cls)
    if not m:
        return None
    bm = int(m.group(1))
    if bm <= 50:
        return 86.5 + ((bm - 45) * 0.11)
    if bm <= 84:
        return 87.0 + ((bm - 50) * 0.20)
    if bm <= 100:
        return 93.8 + ((bm - 84) * 0.20)
    return 97.0 + min(2.0, (bm - 100) * 0.07)

audit = []
built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

for idx, row in df.iterrows():
    cls = row["race_class_clean_v5_2"]
    old = pd.to_numeric(row.get("class_par_rating_v5_2", ""), errors="coerce")
    new = None
    reason = ""

    if cls in ladder:
        new = ladder[cls]
        reason = "STANDARD_CLASS_LADDER_OVERRIDE"
    else:
        bm_val = bm_expected(cls)
        if bm_val is not None:
            new = bm_val
            reason = "BM_NUMERIC_LADDER_OVERRIDE"

    if new is not None:
        df.at[idx, "class_par_rating_raw_v5_2"] = row.get("class_par_rating_v5_2", "")
        df.at[idx, "class_par_rating_v5_2"] = f"{new:.2f}"
        df.at[idx, "class_par_method_v5_2"] = "FULL_LADDER_REPAIRED_V5_2"
        df.at[idx, "class_par_confidence_v5_2"] = "GOVERNED"
        df.at[idx, "class_par_threshold_rule_v5_2"] = reason
        df.at[idx, "class_par_hierarchy_adjustment_v5_2"] = "" if pd.isna(old) else f"{new - float(old):.2f}"
        df.at[idx, "class_par_hierarchy_reason_v5_2"] = reason

        audit.append({
            "race_class": cls,
            "old_value": "" if pd.isna(old) else round(float(old), 2),
            "new_value": round(new, 2),
            "delta": "" if pd.isna(old) else round(new - float(old), 2),
            "reason": reason,
            "built_at": built_at,
        })

df.to_csv(SRC, index=False)
pd.DataFrame(audit).to_csv(AUDIT, index=False)

print("WROTE:", SRC)
print("AUDIT:", AUDIT)
print(pd.DataFrame(audit).sort_values("race_class").to_string(index=False))
