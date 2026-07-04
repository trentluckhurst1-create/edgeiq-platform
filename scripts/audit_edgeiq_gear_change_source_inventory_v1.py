from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

DATA = Path("./public/data")
OUT = DATA / "edgeiq_gear_change_source_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_gear_change_source_inventory_v1_summary.csv"

terms = [
    "gear", "blinkers", "winkers", "tongue", "gelding",
    "visors", "nose", "lugging", "bit", "plates",
    "bandages", "ear", "barrier blanket"
]

rows = []

for p in DATA.glob("*.csv"):
    try:
        df = pd.read_csv(p, nrows=2000, dtype=str, keep_default_na=False, low_memory=False)
    except Exception as e:
        continue

    cols = list(df.columns)
    matched_cols = [
        c for c in cols
        if any(t in c.lower() for t in terms)
    ]

    value_hits = 0
    sample_values = []

    for c in cols:
        if len(sample_values) >= 10:
            break
        s = df[c].astype(str).str.lower()
        mask = s.apply(lambda x: any(t in x for t in terms))
        if mask.any():
            value_hits += int(mask.sum())
            vals = df.loc[mask, c].astype(str).head(5).tolist()
            sample_values.extend(vals)

    if matched_cols or value_hits:
        rows.append({
            "file": p.name,
            "rows_sampled": len(df),
            "matched_columns": " | ".join(matched_cols),
            "matched_column_count": len(matched_cols),
            "value_hits_sample": value_hits,
            "sample_values": " || ".join(sample_values[:10]),
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        })

out = pd.DataFrame(rows).sort_values(
    ["matched_column_count", "value_hits_sample"],
    ascending=False
)

out.to_csv(OUT, index=False)

pd.DataFrame([{
    "status": "EDGEIQ_GEAR_CHANGE_SOURCE_INVENTORY_V1_BUILT",
    "files_with_gear_evidence": len(out),
    "built_at": datetime.now(timezone.utc).isoformat()
}]).to_csv(SUMMARY, index=False)

print("[EDGEIQ_GEAR_CHANGE_SOURCE_INVENTORY_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
