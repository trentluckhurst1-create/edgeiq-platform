from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

OUT = DATA / "edgeiq_historical_market_odds_source_inventory_v1.csv"
SUMMARY = DATA / "edgeiq_historical_market_odds_source_inventory_v1_summary.csv"

TERMS = [
    "market",
    "price",
    "odds",
    "sp",
    "fixed",
    "fluc",
    "runner_board",
    "live",
    "fair"
]

records = []

print("[HISTORICAL_MARKET_ODDS_SOURCE_INVENTORY_V1] START")

for p in DATA.rglob("*.csv"):
    name = p.name.lower()

    if not any(t in name for t in TERMS):
        continue

    rec = {
        "file": p.name,
        "path": str(p.relative_to(ROOT)),
        "bytes": p.stat().st_size,
        "modified_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
        "matched_terms": ",".join([t for t in TERMS if t in name]),
        "rows_sampled": 0,
        "columns": "",
        "identity_cols": "",
        "market_like_cols": "",
        "price_like_cols": "",
        "odds_like_cols": "",
        "score": 0,
        "read_status": "NOT_READ"
    }

    try:
        df = pd.read_csv(p, nrows=10, low_memory=False)
        cols = [str(c) for c in df.columns]
        lower = [c.lower() for c in cols]

        identity_cols = [
            c for c in cols
            if any(x in c.lower() for x in ["race", "date", "track", "horse", "runner"])
        ]

        market_like_cols = [
            c for c in cols
            if any(x in c.lower() for x in ["market", "price", "odds", "sp", "fixed", "fluc", "win"])
        ]

        price_like_cols = [
            c for c in cols
            if "price" in c.lower()
        ]

        odds_like_cols = [
            c for c in cols
            if any(x in c.lower() for x in ["odds", "fixed", "sp", "market"])
        ]

        score = (
            len(identity_cols) * 2 +
            len(market_like_cols) * 4 +
            len(price_like_cols) * 3 +
            len(odds_like_cols) * 3
        )

        rec.update({
            "rows_sampled": len(df),
            "columns": ";".join(cols),
            "identity_cols": ";".join(identity_cols),
            "market_like_cols": ";".join(market_like_cols),
            "price_like_cols": ";".join(price_like_cols),
            "odds_like_cols": ";".join(odds_like_cols),
            "score": score,
            "read_status": "READ"
        })

    except Exception as e:
        rec["read_status"] = f"READ_FAILED:{type(e).__name__}"

    records.append(rec)

out = pd.DataFrame(records)

if len(out):
    out = out.sort_values(
        ["score", "bytes"],
        ascending=[False, False]
    ).reset_index(drop=True)

out.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "built_at": datetime.now(timezone.utc).isoformat(),
    "files_found": len(out),
    "read_files": int((out["read_status"] == "READ").sum()) if len(out) else 0,
    "top_score": int(out["score"].max()) if len(out) else 0,
    "status": "HISTORICAL_MARKET_ODDS_SOURCE_INVENTORY_BUILT_RESEARCH_ONLY"
}])

summary.to_csv(SUMMARY, index=False)

print("[HISTORICAL_MARKET_ODDS_SOURCE_INVENTORY_V1] COMPLETE")
print(f"out={OUT}")
print(f"summary={SUMMARY}")
print("")
print(summary.to_string(index=False))
print("")
print(out.head(80)[["file","score","matched_terms","identity_cols","market_like_cols","read_status"]].to_string(index=False))
