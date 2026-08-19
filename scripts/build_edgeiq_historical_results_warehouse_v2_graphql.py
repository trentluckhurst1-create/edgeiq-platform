import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
SUMMARY = DATA / "edgeiq_historical_results_warehouse_v2_graphql_summary.csv"

files = sorted(DATA.glob("edgeiq_graphql_*_results_v1.csv"))

frames = []
for i, f in enumerate(files, 1):
    try:
        df = pd.read_csv(f, low_memory=False)
        df["source_file"] = f.name
        frames.append(df)
        print(f"[WAREHOUSE_V2] {i}/{len(files)} loaded {f.name} rows={len(df)}")
    except Exception as e:
        print(f"[WAREHOUSE_V2] FAILED {f.name}: {e}")

out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

out["race_date"] = pd.to_datetime(out["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
out["track"] = out["track"].fillna("").astype(str).str.upper().str.strip()
out["horse"] = out["horse"].fillna("").astype(str).str.upper().str.strip()
out["trainer"] = out["trainer"].fillna("").astype(str).str.upper().str.strip()
out["jockey"] = out["jockey"].fillna("").astype(str).str.upper().str.strip()
out["finish_num"] = pd.to_numeric(out["finish"], errors="coerce")
out["won"] = (out["finish_num"] == 1).astype(int)
out["placed"] = out["finish_num"].isin([1,2,3]).astype(int)
out["starting_price_decimal"] = pd.to_numeric(out["starting_price_decimal"], errors="coerce")
out["built_at_warehouse_v2"] = datetime.now(timezone.utc).isoformat()

out = out.drop_duplicates(subset=["race_date","track","race_id","runner_id","horse"], keep="last")

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL_BUILT",
    "files_used": len(files),
    "rows": len(out),
    "date_min": out["race_date"].min(),
    "date_max": out["race_date"].max(),
    "unique_tracks": out["track"].nunique(),
    "unique_horses": out["horse"].nunique(),
    "unique_trainers": out["trainer"].nunique(),
    "unique_jockeys": out["jockey"].nunique(),
    "finished_rows": int(out["finish_num"].notna().sum()),
    "sp_rows": int(out["starting_price_decimal"].notna().sum()),
    "built_at": datetime.now(timezone.utc).isoformat(),
}])

summary.to_csv(SUMMARY, index=False)

print("[HISTORICAL_RESULTS_WAREHOUSE_V2_GRAPHQL] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print(summary.to_string(index=False))
