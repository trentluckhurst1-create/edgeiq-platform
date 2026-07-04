import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

INPUTS = {
    "canonical_split": PUB / "edgeiq_canonical_split_schema_v1.csv",
    "payload_reconstruction": PUB / "edgeiq_sectional_payload_reconstruction_v1.csv",
    "physics_validation": PUB / "edgeiq_sectional_physics_validation_v1.csv",
    "trusted_universe": PUB / "edgeiq_trusted_sectional_universe_v2.csv",
    "shadow_validation": PUB / "edgeiq_shadow_validation_engine_v1.csv",
    "probability_realism": PUB / "edgeiq_sectional_probability_realism_v1.csv",
}

OUT_AUDIT = PUB / "edgeiq_real_sectional_data_readiness_audit_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_real_sectional_data_readiness_summary_v1.csv"

FIELDS = [
    "source_name","source_exists","source_rows",
    "usable_rows","missing_payload_rows","physics_valid_rows",
    "trusted_linked_rows","readiness_grade","readiness_status",
    "primary_blocker","recommended_next_step","notes"
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

def row_has_payload(row):
    joined = " ".join(str(v or "") for v in row.values()).lower()
    return any(x in joined for x in ["split", "sectional", "600", "400", "200", "time", "velocity", "speed"])

def row_physics_valid(row):
    joined = " ".join(str(v or "") for v in row.values()).upper()
    return any(x in joined for x in ["PHYSICS_VALID", "VALID", "PASS", "YES"])

def grade(source, rows, usable, physics):
    if not rows:
        return "F", "MISSING_SOURCE", "SOURCE_MISSING", "Find/build the real sectional source file."
    if usable == 0:
        return "F", "NO_USABLE_PAYLOAD", "NO_REAL_SPLIT_PAYLOAD", "Inspect source schema and payload extraction."
    if physics == 0:
        return "D", "PAYLOAD_NOT_PHYSICS_VALIDATED", "NO_PHYSICS_VALID_ROWS", "Repair physics validation or split schema mapping."
    if physics < max(5, usable * 0.10):
        return "C", "LOW_PHYSICS_COVERAGE", "LOW_VALIDATION_COVERAGE", "Improve canonical split extraction coverage."
    return "B", "REAL_SECTIONAL_SOURCE_USABLE", "COVERAGE_STILL_LIMITED", "Proceed to real split feature extraction sandbox."

def main():
    audit = []

    for name, path in INPUTS.items():
        rows = read_csv(path)
        exists = "YES" if path.exists() else "NO"
        usable = sum(1 for r in rows if row_has_payload(r))
        missing = max(0, len(rows) - usable)
        physics = sum(1 for r in rows if row_physics_valid(r))

        g, status, blocker, step = grade(name, rows, usable, physics)

        audit.append({
            "source_name": name,
            "source_exists": exists,
            "source_rows": len(rows),
            "usable_rows": usable,
            "missing_payload_rows": missing,
            "physics_valid_rows": physics,
            "trusted_linked_rows": "",
            "readiness_grade": g,
            "readiness_status": status,
            "primary_blocker": blocker,
            "recommended_next_step": step,
            "notes": str(path),
        })

    with OUT_AUDIT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(audit)

    grades = Counter(r["readiness_grade"] for r in audit)
    statuses = Counter(r["readiness_status"] for r in audit)
    blockers = Counter(r["primary_blocker"] for r in audit)

    summary = []
    summary.append({"metric": "sources_audited", "value": len(audit)})
    summary.append({"metric": "usable_source_count", "value": sum(1 for r in audit if r["readiness_grade"] in {"A","B","C"})})
    summary.append({"metric": "live_modelling_yes", "value": 0})
    summary.append({"metric": "live_execution_yes", "value": 0})

    for k, v in grades.most_common():
        summary.append({"metric": f"grade::{k}", "value": v})
    for k, v in statuses.most_common():
        summary.append({"metric": f"status::{k}", "value": v})
    for k, v in blockers.most_common():
        summary.append({"metric": f"blocker::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ REAL SECTIONAL DATA READINESS AUDIT V1")
    print("=" * 88)
    print(f"sources audited: {len(audit)}")
    print(f"usable sources: {sum(1 for r in audit if r['readiness_grade'] in {'A','B','C'})}")
    print(f"saved: {OUT_AUDIT}")
    print(f"saved: {OUT_SUMMARY}")
    print("statuses:")
    for k, v in statuses.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
