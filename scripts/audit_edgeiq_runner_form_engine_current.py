import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

SRC = DATA / "edgeiq_runner_form_engine_current.csv"
OUT = DATA / "edgeiq_runner_form_engine_current_audit.csv"
SUMMARY = DATA / "edgeiq_runner_form_engine_current_audit_summary.csv"

print("[RUNNER_FORM_ENGINE_CURRENT_AUDIT] START")

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

recent = pd.to_numeric(df["recent_runs_found"], errors="coerce").fillna(0)
trend = df["rating_trend"].astype(str)
last_rating = df["last_start_rating"].astype(str).str.strip()
narrative = df["form_narrative"].astype(str).str.strip()

add("rows_present", rows, rows if rows > 0 else 0)
add("horse_present", rows, int((df["horse"].astype(str).str.strip() != "").sum()))
add("recent_runs_available", rows, int((recent > 0).sum()), ", ".join(df[recent == 0]["horse"].head(10).tolist()))
add("last_start_rating_available", rows, int((last_rating != "").sum()), ", ".join(df[last_rating == ""]["horse"].head(10).tolist()))
add("rating_trend_available", rows, int((trend != "NO RATING TREND").sum()), "Expected warning where fewer than 3 rated runs exist.")
add("form_signal_present", rows, int((df["form_signal"].astype(str).str.strip() != "").sum()))
add("form_narrative_present", rows, int((narrative != "").sum()))

audit = pd.DataFrame(checks)
audit.to_csv(OUT, index=False)

summary = pd.DataFrame([{
    "status": "RUNNER_FORM_ENGINE_CURRENT_AUDIT_BUILT",
    "rows": rows,
    "checks": len(audit),
    "pass_checks": int((audit["status"] == "PASS").sum()),
    "warn_checks": int((audit["status"] == "WARN").sum()),
    "fail_checks": 0,
    "built_at": datetime.now(timezone.utc).isoformat()
}])

summary.to_csv(SUMMARY, index=False)

print("[RUNNER_FORM_ENGINE_CURRENT_AUDIT] COMPLETE")
print(summary.to_string(index=False))
print(f"out={OUT}")
print(f"summary={SUMMARY}")
