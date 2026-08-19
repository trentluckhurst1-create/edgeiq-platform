import pandas as pd
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT_AUDIT = DATA / "edgeiq_dna_v6_source_audit.csv"
OUT_JSON = DATA / "edgeiq_dna_v6_source_audit.json"

CANDIDATES = [
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "full_career_form.csv",
    "runner_form_history.csv",
    "edgeiq_racingcom_results_warehouse_full_v1.csv",
    "edgeiq_horse_profile_v3.csv",
    "edgeiq_live_horse_profile_v3.csv",
    "edgeiq_runner_dna_current.csv",
    "edgeiq_live_runner_board_governed_v1.csv",
    "edgeiq_live_runner_board_v1.csv",
]

WANTED = [
    "horse", "horse_name", "runner", "horse_canon", "horse_key",
    "distance", "distance_m", "race_distance",
    "condition", "track_condition", "track_condition_clean", "condition_recovered",
    "race_class", "race_class_clean", "class", "class_clean",
    "finish_position", "finishing_position", "position", "placing", "result",
    "race_date", "track", "race_no",
]

rows = []

for name in CANDIDATES:
    path = DATA / name
    if not path.exists():
        rows.append({
            "file": name,
            "exists": "NO",
            "rows": 0,
            "cols": "",
            "horse_cols": "",
            "distance_cols": "",
            "condition_cols": "",
            "class_cols": "",
            "finish_cols": "",
            "date_cols": "",
        })
        continue

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as e:
        rows.append({
            "file": name,
            "exists": "READ_ERROR",
            "rows": 0,
            "cols": str(e),
            "horse_cols": "",
            "distance_cols": "",
            "condition_cols": "",
            "class_cols": "",
            "finish_cols": "",
            "date_cols": "",
        })
        continue

    cols = list(df.columns)
    lc = {c.lower(): c for c in cols}

    def find_any(patterns):
        found = []
        for c in cols:
            cl = c.lower()
            if any(p in cl for p in patterns):
                found.append(c)
        return found

    rows.append({
        "file": name,
        "exists": "YES",
        "rows": len(df),
        "cols": "|".join(cols),
        "horse_cols": "|".join(find_any(["horse", "runner"])),
        "distance_cols": "|".join(find_any(["distance", "dist"])),
        "condition_cols": "|".join(find_any(["condition", "going", "track_condition"])),
        "class_cols": "|".join(find_any(["class", "grade"])),
        "finish_cols": "|".join(find_any(["finish", "position", "placing", "result"])),
        "date_cols": "|".join(find_any(["date"])),
    })

audit = pd.DataFrame(rows)
audit.to_csv(OUT_AUDIT, index=False)

summary = {
    "status": "DNA_V6_SOURCE_AUDIT_COMPLETE",
    "files_checked": len(CANDIDATES),
    "files_found": int((audit["exists"] == "YES").sum()),
    "output": str(OUT_AUDIT),
}

OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("[DNA_V6_SOURCE_AUDIT] COMPLETE")
print(audit[["file","exists","rows","horse_cols","distance_cols","condition_cols","class_cols","finish_cols"]].to_string(index=False))
