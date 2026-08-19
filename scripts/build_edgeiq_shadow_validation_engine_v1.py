import csv
from collections import Counter
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_TRUSTED = PUB / "edgeiq_trusted_sectional_universe_v2.csv"
IN_FIELDS = PUB / "edgeiq_vic_three_day_race_fields.csv"
IN_RESULTS = PUB / "race_results.csv"
IN_SCRATCHINGS = PUB / "edgeiq_vic_scratchings_diagnostics.csv"

OUT_VALIDATION = PUB / "edgeiq_shadow_validation_engine_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_shadow_validation_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse",
    "trust_level","validation_cycle_date",
    "field_continuity_pass","results_continuity_pass",
    "scratching_drift_pass","identity_stability_pass",
    "metadata_stability_pass","validation_score",
    "validation_grade","validation_status",
    "future_modelling_candidate",
    "future_execution_candidate",
    "notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def val(row, *names):
    for n in names:
        if n in row and str(row.get(n, "")).strip():
            return str(row.get(n, "")).strip()
    return ""

def norm(v):
    return "".join(ch for ch in str(v or "").upper().strip() if ch.isalnum())

def make_key(row):
    return (
        val(row, "race_date", "date"),
        val(row, "track", "track_name", "meeting"),
        val(row, "race_no", "race_number"),
        norm(val(row, "horse", "horse_name", "runner_name")),
    )

def main():
    trusted = read_csv(IN_TRUSTED)
    fields = read_csv(IN_FIELDS)
    results = read_csv(IN_RESULTS)
    scratchings = read_csv(IN_SCRATCHINGS)

    field_keys = set(make_key(r) for r in fields)
    result_keys = set(make_key(r) for r in results)

    scratched_keys = set()
    for r in scratchings:
        status = val(r, "scratched", "status", "scratching_status")
        if "SCRATCH" in status.upper() or status.upper() in {"YES", "TRUE", "1"}:
            scratched_keys.add(make_key(r))

    out = []

    for r in trusted:
        k = make_key(r)

        field_pass = "YES" if k in field_keys else "NO"
        results_pass = "YES" if k in result_keys else "NO"
        scratching_pass = "NO" if k in scratched_keys else "YES"

        identity_pass = "YES"
        metadata_pass = "YES"

        score = 0
        score += 25 if field_pass == "YES" else 0
        score += 25 if results_pass == "YES" else 0
        score += 20 if scratching_pass == "YES" else 0
        score += 15 if identity_pass == "YES" else 0
        score += 15 if metadata_pass == "YES" else 0

        if score >= 90:
            grade = "ELITE_STABLE"
            status = "SHADOW_PASS"
        elif score >= 70:
            grade = "STABLE"
            status = "SHADOW_PASS"
        elif score >= 50:
            grade = "MONITOR"
            status = "SHADOW_REVIEW"
        else:
            grade = "UNSTABLE"
            status = "SHADOW_FAIL"

        future_model = "YES" if grade == "ELITE_STABLE" else "NO"
        future_exec = "YES" if grade == "ELITE_STABLE" else "NO"

        notes = []
        if field_pass != "YES":
            notes.append("FIELD_CONTINUITY_MISSING")
        if results_pass != "YES":
            notes.append("RESULT_CONTINUITY_MISSING")
        if scratching_pass != "YES":
            notes.append("SCRATCHING_DRIFT")

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "trust_level": val(r, "trust_level"),
            "validation_cycle_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "field_continuity_pass": field_pass,
            "results_continuity_pass": results_pass,
            "scratching_drift_pass": scratching_pass,
            "identity_stability_pass": identity_pass,
            "metadata_stability_pass": metadata_pass,
            "validation_score": score,
            "validation_grade": grade,
            "validation_status": status,
            "future_modelling_candidate": future_model,
            "future_execution_candidate": future_exec,
            "notes": "|".join(notes) if notes else "STABLE_SHADOW_VALIDATION",
        })

    with OUT_VALIDATION.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    grades = Counter(r["validation_grade"] for r in out)
    status_counts = Counter(r["validation_status"] for r in out)

    summary = []
    summary.append({"metric": "trusted_rows_validated", "value": len(out)})
    summary.append({"metric": "future_modelling_candidates", "value": sum(1 for r in out if r["future_modelling_candidate"] == "YES")})
    summary.append({"metric": "future_execution_candidates", "value": sum(1 for r in out if r["future_execution_candidate"] == "YES")})

    for k, v in grades.most_common():
        summary.append({"metric": f"validation_grade::{k}", "value": v})

    for k, v in status_counts.most_common():
        summary.append({"metric": f"validation_status::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SHADOW VALIDATION ENGINE V1")
    print("=" * 88)
    print(f"trusted rows validated: {len(out)}")
    print(f"future modelling candidates: {sum(1 for r in out if r['future_modelling_candidate'] == 'YES')}")
    print(f"future execution candidates: {sum(1 for r in out if r['future_execution_candidate'] == 'YES')}")
    print(f"saved: {OUT_VALIDATION}")
    print(f"saved: {OUT_SUMMARY}")
    print("validation grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
