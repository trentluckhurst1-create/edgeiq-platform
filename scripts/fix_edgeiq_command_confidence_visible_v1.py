import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

command_path = DATA / "edgeiq_command_enrichment_feed_v3.csv"
runners_path = DATA / "edgeiq_runners_enrichment_feed_v1_1.csv"

backup_path = DATA / "edgeiq_command_enrichment_feed_v3_BACKUP_BEFORE_CONFIDENCE_FIX_20260628.csv"
audit_path = DATA / "edgeiq_command_confidence_visible_fix_v1.csv"
report_path = DATA / "edgeiq_command_confidence_visible_fix_v1_report.txt"

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def key(row):
    return (
        clean(row.get("race_date", "")),
        clean(row.get("track", "")),
        clean(row.get("race_no", "")),
        clean(row.get("horse", "")),
    )

def num(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None

command = pd.read_csv(command_path, low_memory=False)
runners = pd.read_csv(runners_path, low_memory=False)

command.to_csv(backup_path, index=False)

runners_by_key = {key(r): r for _, r in runners.iterrows()}

audit_rows = []
fixed = 0
still_missing = 0

if "edgeiq_score_confidence_v3" not in command.columns:
    command["edgeiq_score_confidence_v3"] = ""

if "edgeiq_score_source_v3" not in command.columns:
    command["edgeiq_score_source_v3"] = ""

for idx, row in command.iterrows():
    current = num(row.get("edgeiq_score_confidence_v3", ""))
    r = runners_by_key.get(key(row))
    source_value = None
    source_field = ""

    if r is not None:
        for field in ["score_confidence", "confidence_score", "dna_score", "dna_v6_2_score"]:
            val = num(r.get(field, ""))
            if val is not None:
                source_value = val
                source_field = f"RUNNERS_V1_1:{field}"
                break

    status = "OK_EXISTING"
    if current is None:
        if source_value is not None:
            command.at[idx, "edgeiq_score_confidence_v3"] = round(source_value, 2)
            src = str(row.get("edgeiq_score_source_v3", ""))
            if "CONFIDENCE:MISSING" in src:
                src = src.replace("CONFIDENCE:MISSING", f"CONFIDENCE:{source_field}")
            elif "CONFIDENCE:" not in src:
                src = (src + f"|CONFIDENCE:{source_field}").strip("|")
            command.at[idx, "edgeiq_score_source_v3"] = src
            fixed += 1
            status = "FIXED_FROM_RUNNERS_V1_1"
        else:
            still_missing += 1
            status = "STILL_MISSING"
    audit_rows.append({
        "race_date": row.get("race_date", ""),
        "track": row.get("track", ""),
        "race_no": row.get("race_no", ""),
        "horse": row.get("horse", ""),
        "before_confidence": current,
        "after_confidence": command.at[idx, "edgeiq_score_confidence_v3"],
        "source_field": source_field,
        "status": status,
    })

command.to_csv(command_path, index=False)
pd.DataFrame(audit_rows).to_csv(audit_path, index=False)

with open(report_path, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_COMMAND_CONFIDENCE_VISIBLE_FIX_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n")
    f.write(f"rows={len(command)}\n")
    f.write(f"fixed={fixed}\n")
    f.write(f"still_missing={still_missing}\n")
    f.write(f"backup={backup_path}\n")
    f.write(f"audit={audit_path}\n")
    f.write("pricing_maths_changed=NO\n")
    f.write("v6_1_changed=NO\n")
    f.write("v7_2g2_changed=NO\n")

print("[EDGEIQ_COMMAND_CONFIDENCE_VISIBLE_FIX_V1] COMPLETE")
print(f"fixed={fixed}")
print(f"still_missing={still_missing}")
print(report_path)
