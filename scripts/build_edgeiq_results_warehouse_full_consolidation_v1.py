import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

BATCH_DIR = DATA / "edgeiq_racingcom_results_batches_v1"

OUT_FULL = DATA / "edgeiq_racingcom_results_warehouse_full_v1.csv"
OUT_CURRENT_BACKUP = DATA / "edgeiq_racingcom_results_warehouse_v1_before_full_consolidation_backup.csv"
OUT_CURRENT = DATA / "edgeiq_racingcom_results_warehouse_v1.csv"
AUDIT = DATA / "edgeiq_racingcom_results_warehouse_full_v1_audit.csv"

def main():
    files = sorted(BATCH_DIR.glob("edgeiq_racingcom_results_batch_offset_*.csv"))

    frames = []
    batch_rows = []

    for f in files:
        try:
            df = pd.read_csv(f)
            rows = len(df)
            if rows > 0:
                df["source_batch_file_v1"] = f.name
                frames.append(df)

            batch_rows.append({
                "batch_file": f.name,
                "rows": rows,
                "status": "LOADED",
            })
        except Exception as e:
            batch_rows.append({
                "batch_file": f.name,
                "rows": 0,
                "status": f"ERROR: {repr(e)}",
            })

    if not frames:
        raise RuntimeError("No result batch rows found to consolidate.")

    out = pd.concat(frames, ignore_index=True)

    key_cols = []
    for c in ["meeting_date", "track", "race_no", "horseName", "finishPosition"]:
        if c in out.columns:
            key_cols.append(c)

    before = len(out)

    if key_cols:
        out = out.drop_duplicates(key_cols, keep="last")

    after = len(out)

    if "meeting_date" in out.columns:
        out = out.sort_values(["meeting_date", "track", "race_no", "finishPosition", "horseName"], na_position="last")

    if OUT_CURRENT.exists():
        pd.read_csv(OUT_CURRENT).to_csv(OUT_CURRENT_BACKUP, index=False)

    out.to_csv(OUT_FULL, index=False)
    out.to_csv(OUT_CURRENT, index=False)

    min_date = out["meeting_date"].min() if "meeting_date" in out.columns else ""
    max_date = out["meeting_date"].max() if "meeting_date" in out.columns else ""
    races = out[["meeting_date", "track", "race_no"]].drop_duplicates().shape[0] if all(c in out.columns for c in ["meeting_date", "track", "race_no"]) else ""

    sp_rows = int(out["sp"].astype(str).str.strip().ne("").sum()) if "sp" in out.columns else 0

    summary = pd.DataFrame([
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "batch_files_found", "value": len(files)},
        {"metric": "batch_files_loaded", "value": len(frames)},
        {"metric": "raw_rows_before_dedupe", "value": before},
        {"metric": "rows_after_dedupe", "value": after},
        {"metric": "unique_races", "value": races},
        {"metric": "min_meeting_date", "value": min_date},
        {"metric": "max_meeting_date", "value": max_date},
        {"metric": "sp_rows", "value": sp_rows},
        {"metric": "wrote_full", "value": str(OUT_FULL)},
        {"metric": "wrote_current", "value": str(OUT_CURRENT)},
        {"metric": "backup_previous_current", "value": str(OUT_CURRENT_BACKUP)},
    ])

    audit = pd.concat([summary, pd.DataFrame(batch_rows)], ignore_index=True)
    audit.to_csv(AUDIT, index=False)

    print("[RESULTS_WAREHOUSE_FULL_CONSOLIDATION_V1] COMPLETE")
    print(f"batch_files_found={len(files)}")
    print(f"raw_rows_before_dedupe={before}")
    print(f"rows_after_dedupe={after}")
    print(f"unique_races={races}")
    print(f"date_range={min_date} to {max_date}")
    print(f"sp_rows={sp_rows}")
    print(f"wrote={OUT_FULL}")
    print(f"also_replaced_current={OUT_CURRENT}")
    print(f"audit={AUDIT}")

if __name__ == "__main__":
    main()
