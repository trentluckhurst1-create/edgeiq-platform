import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_profile_engine_v1_2.csv"
OUT = DATA / "edgeiq_runner_profile_engine_v1_2_audit.csv"
SUMMARY = DATA / "edgeiq_runner_profile_engine_v1_2_audit_summary.csv"

print("[RUNNER_PROFILE_ENGINE_V1_2_AUDIT] START")

df = pd.read_csv(SRC, dtype=str).fillna("")

checks = []

def add_check(name, total, passed, fail_examples=""):
    failed = total - passed
    status = "PASS" if failed == 0 else "WARN"
    checks.append({
        "check": name,
        "status": status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "fail_examples": fail_examples,
        "built_at": datetime.now(timezone.utc).isoformat()
    })

rows = len(df)

add_check(
    "rows_present",
    rows,
    rows if rows > 0 else 0
)

add_check(
    "horse_present",
    rows,
    int((df["horse"].astype(str).str.strip() != "").sum()),
    ", ".join(df[df["horse"].astype(str).str.strip() == ""]["runner_key"].head(5).tolist())
)

add_check(
    "profile_context_available",
    rows,
    int((pd.to_numeric(df["profile_context_rows"], errors="coerce").fillna(0) > 0).sum()),
    ", ".join(df[pd.to_numeric(df["profile_context_rows"], errors="coerce").fillna(0) == 0]["horse"].head(8).tolist())
)

add_check(
    "career_starts_available",
    rows,
    int((pd.to_numeric(df["career_starts"], errors="coerce").fillna(0) > 0).sum()),
    ", ".join(df[pd.to_numeric(df["career_starts"], errors="coerce").fillna(0) == 0]["horse"].head(8).tolist())
)

add_check(
    "dna_score_available",
    rows,
    int((df["dna_score"].astype(str).str.strip() != "").sum()),
    ", ".join(df[df["dna_score"].astype(str).str.strip() == ""]["horse"].head(8).tolist())
)

add_check(
    "profile_summary_present",
    rows,
    int((df["profile_summary"].astype(str).str.strip() != "").sum()),
    ", ".join(df[df["profile_summary"].astype(str).str.strip() == ""]["horse"].head(8).tolist())
)

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_PROFILE_ENGINE_V1_2_AUDIT_BUILT",
    "rows": rows,
    "checks": len(audit),
    "pass_checks": int((audit["status"] == "PASS").sum()),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": int((audit["status"] == "FAIL").sum()),
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_PROFILE_ENGINE_V1_2_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
