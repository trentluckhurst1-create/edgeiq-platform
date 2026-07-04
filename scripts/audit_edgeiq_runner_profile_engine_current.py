import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_profile_engine_current.csv"
OUT = DATA / "edgeiq_runner_profile_engine_current_audit.csv"
SUMMARY = DATA / "edgeiq_runner_profile_engine_current_audit_summary.csv"

print("[RUNNER_PROFILE_ENGINE_CURRENT_AUDIT] START")

df = pd.read_csv(SRC, dtype=str).fillna("")
checks = []

def add(name, total, passed, examples=""):
    failed = total - passed
    status = "PASS" if failed == 0 else "WARN"
    checks.append({
        "check": name,
        "status": status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "examples": examples,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

rows = len(df)
context_rows = pd.to_numeric(df["profile_context_rows"], errors="coerce").fillna(0)
career_starts = pd.to_numeric(df["career_starts"], errors="coerce").fillna(0)
dna_score = df["dna_score"].astype(str).str.strip()
summary_text = df["profile_summary"].astype(str).str.strip()

add("rows_present", rows, rows if rows > 0 else 0)
add("horse_present", rows, int((df["horse"].astype(str).str.strip() != "").sum()))
add("profile_context_available", rows, int((context_rows > 0).sum()), ", ".join(df[context_rows == 0]["horse"].head(10).tolist()))
add("career_starts_available", rows, int((career_starts > 0).sum()), ", ".join(df[career_starts == 0]["horse"].head(10).tolist()))
add("dna_score_available", rows, int((dna_score != "").sum()), ", ".join(df[dna_score == ""]["horse"].head(10).tolist()))
add("profile_summary_present", rows, int((summary_text != "").sum()))

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_PROFILE_ENGINE_CURRENT_AUDIT_BUILT",
    "rows": rows,
    "checks": len(audit),
    "pass_checks": int((audit["status"] == "PASS").sum()),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": 0,
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_PROFILE_ENGINE_CURRENT_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
