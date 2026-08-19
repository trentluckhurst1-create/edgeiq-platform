import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"

form_path = DATA / "edgeiq_form_enrichment_feed_v2.csv"

targets = [
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
]

summary_rows = []

def clean(v):
    return str(v).strip().upper() if pd.notna(v) else ""

def hkey(v):
    return "".join(ch for ch in clean(v) if ch.isalnum())

def rno(v):
    return clean(v).replace("R", "")

def key(row):
    return (
        clean(row.get("race_date", "")),
        clean(row.get("track", "")),
        rno(row.get("race_no", "")),
        hkey(row.get("horse_key", "")) or hkey(row.get("horse", "")),
    )

form = pd.read_csv(form_path, low_memory=False)
form_map = {key(r): r for _, r in form.iterrows()}

form_cols = [c for c in form.columns if c not in ["race_date", "track", "race_no", "horse"]]

for path in targets:
    df = pd.read_csv(path, low_memory=False)
    backup = path.with_name(path.stem + "_BACKUP_BEFORE_FORM_FIELDS_MERGE_20260628" + path.suffix)
    df.to_csv(backup, index=False)

    matched = 0
    for idx, row in df.iterrows():
        f = form_map.get(key(row))
        if f is None:
            continue
        matched += 1
        for c in form_cols:
            df.at[idx, c] = f.get(c, "")

    df.to_csv(path, index=False)

    summary_rows.append({
        "file": path.name,
        "rows": len(df),
        "matched_form_rows": matched,
        "missing_form_rows": len(df) - matched,
        "backup": str(backup),
    })

summary = pd.DataFrame(summary_rows)
summary_out = DATA / "edgeiq_form_fields_merged_into_runner_boards_v1_summary.csv"
report_out = DATA / "edgeiq_form_fields_merged_into_runner_boards_v1_report.txt"

summary.to_csv(summary_out, index=False)

with open(report_out, "w", encoding="utf-8") as f:
    f.write("[EDGEIQ_FORM_FIELDS_MERGED_INTO_RUNNER_BOARDS_V1]\n")
    f.write(f"built_at={datetime.now(timezone.utc).isoformat()}\n\n")
    f.write(summary.to_string(index=False))
    f.write("\n\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n")

print("[EDGEIQ_FORM_FIELDS_MERGED_INTO_RUNNER_BOARDS_V1] COMPLETE")
print(summary.to_string(index=False))
print(report_out)
