import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_intelligence_score_engine_v1_1.csv"
OUT = DATA / "edgeiq_intelligence_score_engine_v1_1_audit.csv"

if not SRC.exists():
    raise FileNotFoundError(SRC)

df = pd.read_csv(SRC, dtype=str).fillna("")

checks = []

def add(check, status, detail):
    checks.append({
        "check": check,
        "status": status,
        "detail": detail,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

required = [
    "track",
    "race_no",
    "horse",
    "runner_status",
    "display_decision",
    "stable_intent_band",
    "context_signal_count",
    "dna_v6_2_band_joined",
    "intelligence_score_v1_1",
    "intelligence_band_v1_1",
    "intelligence_verdict_v1_1",
    "top_reasons_v1_1",
    "top_risks_v1_1",
    "customer_narrative_v1_1"
]

missing = [c for c in required if c not in df.columns]
add("required_columns", "FAIL" if missing else "PASS", ",".join(missing) if missing else "all present")

add("row_count", "FAIL" if len(df) == 0 else "PASS", str(len(df)))

blank_horse = int((df["horse"].astype(str).str.strip() == "").sum())
add("blank_horse", "FAIL" if blank_horse else "PASS", str(blank_horse))

blank_narrative = int((df["customer_narrative_v1_1"].astype(str).str.strip() == "").sum())
add("blank_customer_narrative", "FAIL" if blank_narrative else "PASS", str(blank_narrative))

dup_cols = ["race_key", "horse"]
dupes = int(df.duplicated(dup_cols).sum()) if all(c in df.columns for c in dup_cols) else 0
add("duplicate_race_key_horse", "FAIL" if dupes else "PASS", str(dupes))

scores = pd.to_numeric(df["intelligence_score_v1_1"], errors="coerce")
bad_scores = int(((scores < 0) | (scores > 100) | scores.isna()).sum())
add("score_range_0_100", "FAIL" if bad_scores else "PASS", str(bad_scores))

allowed_bands = {"ELITE", "STRONG", "POSITIVE", "WATCH", "LOW_CONVICTION", "SCRATCHED"}
bad_bands = int((~df["intelligence_band_v1_1"].isin(allowed_bands)).sum())
add("valid_intelligence_bands", "FAIL" if bad_bands else "PASS", str(bad_bands))

scratched_bad = int(((df["runner_status"].str.upper() == "SCRATCHED") & (df["intelligence_band_v1_1"] != "SCRATCHED")).sum())
add("scratched_band_alignment", "FAIL" if scratched_bad else "PASS", str(scratched_bad))

dna_allowed = {"ELITE", "STRONG", "POSITIVE", "NEUTRAL", "NEGATIVE", "POOR", "NO_PROFILE"}
bad_dna = int((~df["dna_v6_2_band_joined"].isin(dna_allowed)).sum())
add("valid_dna_bands", "FAIL" if bad_dna else "PASS", str(bad_dna))

out = pd.DataFrame(checks)
out.to_csv(OUT, index=False)

print("[INTELLIGENCE_SCORE_ENGINE_V1_1_AUDIT] COMPLETE")
print(f"out={OUT}")
print(f"checks={len(out)} fail={int((out['status'] == 'FAIL').sum())}")
print(out.to_string(index=False))
