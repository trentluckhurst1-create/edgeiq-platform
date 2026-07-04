import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

INFILE = DATA / "edgeiq_race_understanding_engine_v3_graphql.csv"
OUT = DATA / "edgeiq_race_understanding_engine_v3_graphql_audit.csv"

if not INFILE.exists():
    raise FileNotFoundError(f"Missing input: {INFILE}")

df = pd.read_csv(INFILE, dtype=str).fillna("")

checks = []

def add_check(name, status, detail):
    checks.append({
        "check": name,
        "status": status,
        "detail": detail,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

required = [
    "track",
    "race_no",
    "horse",
    "stable_intent_label",
    "context_signal_count",
    "dna_score",
    "dna_band",
    "historical_setup_score",
    "narrative_strength",
    "customer_verdict",
    "why_we_like_it",
    "main_risk",
    "full_narrative"
]

missing_cols = [c for c in required if c not in df.columns]
add_check("required_columns", "FAIL" if missing_cols else "PASS", ",".join(missing_cols) if missing_cols else "all present")

add_check("row_count", "FAIL" if len(df) == 0 else "PASS", str(len(df)))

blank_horse = int((df["horse"].astype(str).str.strip() == "").sum()) if "horse" in df.columns else len(df)
add_check("blank_horse", "FAIL" if blank_horse else "PASS", str(blank_horse))

blank_narrative = int((df["full_narrative"].astype(str).str.strip() == "").sum()) if "full_narrative" in df.columns else len(df)
add_check("blank_full_narrative", "FAIL" if blank_narrative else "PASS", str(blank_narrative))

dup_cols = [c for c in ["track", "race_no", "horse"] if c in df.columns]
dupes = int(df.duplicated(dup_cols).sum()) if len(dup_cols) == 3 else 0
add_check("duplicate_track_race_horse", "FAIL" if dupes else "PASS", str(dupes))

if "historical_setup_score" in df.columns:
    scores = pd.to_numeric(df["historical_setup_score"], errors="coerce")
    bad_scores = int(((scores < 0) | (scores > 100) | scores.isna()).sum())
    add_check("score_range_0_100", "FAIL" if bad_scores else "PASS", str(bad_scores))

if "narrative_strength" in df.columns:
    allowed = {"ELITE", "STRONG", "POSITIVE", "WATCH", "LOW_CONVICTION"}
    bad_bands = int((~df["narrative_strength"].isin(allowed)).sum())
    add_check("valid_narrative_strength", "FAIL" if bad_bands else "PASS", str(bad_bands))

out = pd.DataFrame(checks)
out.to_csv(OUT, index=False)

fail_count = int((out["status"] == "FAIL").sum())
warn_count = int((out["status"] == "WARN").sum())

print("[RACE_UNDERSTANDING_ENGINE_V3_GRAPHQL_AUDIT] COMPLETE")
print(f"out={OUT}")
print(f"checks={len(out)} warn={warn_count} fail={fail_count}")
print(out.to_string(index=False))
