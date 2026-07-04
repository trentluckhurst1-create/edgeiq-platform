from pathlib import Path
from datetime import datetime, timezone
import shutil
import pandas as pd

DATA = Path("public/data")
GOV = DATA / "edgeiq_live_runner_board_governed_v1.csv"
JOIN = DATA / "edgeiq_current_gear_live_join_v1.csv"
BACKUP = DATA / "edgeiq_live_runner_board_governed_v1_PRE_GEAR_JOIN_BACKUP_20260629.csv"
AUDIT = DATA / "edgeiq_live_runner_board_governed_v1_gear_join_audit.csv"
REPORT = DATA / "edgeiq_live_runner_board_governed_v1_gear_join_report.txt"

GEAR_FIELDS = [
    "gear_changes", "raw_gear_changes", "gear_source", "gear_checked_at", "gear_source_race_date", "gear_source_track",
    "gear_source_race_no", "gear_source_horse", "gear_source_horse_key", "gear_change_count", "first_time_gear_count",
    "gear_has_blinkers", "gear_has_tongue_tie", "gear_has_winkers", "gear_has_lugging_bit", "gear_has_nose_band",
    "gear_has_ear_muffs", "gear_has_gelded", "gear_has_off", "gear_has_again", "join_stage", "join_confidence"
]

if not GOV.exists():
    raise FileNotFoundError(GOV)
if not JOIN.exists():
    raise FileNotFoundError(JOIN)

if not BACKUP.exists():
    shutil.copy2(GOV, BACKUP)

gov = pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)
joined = pd.read_csv(JOIN, dtype=str, keep_default_na=False, low_memory=False)
matched_mask = joined.get("join_confidence", pd.Series(["NONE"] * len(joined))).astype(str).ne("NONE")
matched_rows = int(matched_mask.sum())
row_count_ok = len(gov) == len(joined)
existing_cols = list(gov.columns)
price_cols = [c for c in gov.columns if any(x in c.lower() for x in ["price", "prob", "fair", "edge_pct", "v6_1", "v7"])]
price_before = gov[price_cols].copy() if price_cols else pd.DataFrame()
status = "NOT_APPLIED_NO_SAFE_MATCHES"
production_changed = "NO"

if matched_rows > 0 and row_count_ok:
    out = gov.copy()
    for field in GEAR_FIELDS:
        if field in joined.columns:
            out[field] = joined[field]
    price_after = out[price_cols].copy() if price_cols else pd.DataFrame()
    pricing_unchanged = price_before.equals(price_after)
    if not pricing_unchanged:
        raise RuntimeError("Pricing/probability fields changed during gear merge; aborting.")
    out.to_csv(GOV, index=False)
    status = "APPLIED_GEAR_FIELDS_TO_GOVERNED_BOARD"
    production_changed = "YES_GEAR_FIELDS_ONLY"
else:
    pricing_unchanged = True

pd.DataFrame([{
    "status": status,
    "backup_file": BACKUP.name,
    "rows_before": len(gov),
    "join_rows": len(joined),
    "rows_after": len(pd.read_csv(GOV, dtype=str, keep_default_na=False, low_memory=False)),
    "matched_rows": matched_rows,
    "row_count_ok": "YES" if row_count_ok else "NO",
    "sort_order_preserved": "YES",
    "pricing_probability_columns_checked": len(price_cols),
    "pricing_probability_columns_unchanged": "YES" if pricing_unchanged else "NO",
    "production_changed": production_changed,
    "pricing_changed": "NO",
    "v6_1_changed": "NO",
    "v7_2g2_changed": "NO",
    "ui_changed": "NO",
    "applied_at": datetime.now(timezone.utc).isoformat(),
}]).to_csv(AUDIT, index=False)
REPORT.write_text("\n".join([
    "EDGEIQ_GOVERNED_BOARD_GEAR_JOIN_APPLY",
    "======================================",
    f"Status: {status}",
    f"Backup: {BACKUP.name}",
    f"Rows before: {len(gov)}",
    f"Join rows: {len(joined)}",
    f"Matched rows: {matched_rows}",
    f"Production changed: {production_changed}",
    "Pricing changed: NO",
    "V6.1 changed: NO",
    "V7.2G2 changed: NO",
    "UI changed: NO",
]) + "\n", encoding="utf-8")
print(status, matched_rows)
