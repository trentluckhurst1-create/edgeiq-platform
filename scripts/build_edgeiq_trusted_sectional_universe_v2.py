import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_AUDIT = PUB / "edgeiq_sectional_promotion_audit_v1.csv"
IN_ESCALATION = PUB / "edgeiq_field_linked_sectional_escalation_v1.csv"
IN_META = PUB / "edgeiq_runner_metadata_evidence_v1.csv"

OUT_UNIVERSE = PUB / "edgeiq_trusted_sectional_universe_v2.csv"
OUT_SUMMARY = PUB / "edgeiq_trusted_sectional_summary_v2.csv"

FIELDS = [
    "race_date","track","race_no","horse","sectional_runner",
    "audit_score","audit_grade","promotion_tier","metadata_grade",
    "source_lineage","physics_status","trust_level",
    "trusted_for_modelling","trusted_for_execution",
    "trusted_reason","validation_status","notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def val(row, name):
    return str(row.get(name, "") or "").strip()

def norm(v):
    return "".join(ch for ch in str(v or "").upper().strip() if ch.isalnum())

def key(row):
    return (
        val(row, "race_date"),
        val(row, "track"),
        val(row, "race_no"),
        norm(val(row, "horse") or val(row, "sectional_runner")),
    )

def main():
    audit = read_csv(IN_AUDIT)
    escalation = read_csv(IN_ESCALATION)
    meta = read_csv(IN_META)

    esc_lookup = {key(r): r for r in escalation}
    meta_lookup = {key(r): r for r in meta}

    out = []

    for r in audit:
        if val(r, "audit_status") != "PASS":
            continue
        if val(r, "trusted_sectional_candidate") != "YES":
            continue
        if val(r, "scratch_status_pass") != "YES":
            continue
        if val(r, "duplicate_conflict_pass") != "YES":
            continue

        k = key(r)
        e = esc_lookup.get(k, {})
        m = meta_lookup.get(k, {})

        physics_status = val(r, "physics_pass")
        if physics_status == "YES":
            trust_level = "AUDITED_FIELD_LINKED"
        else:
            trust_level = "AUDITED_FIELD_LINKED_PHYSICS_REVIEW"

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "sectional_runner": val(r, "sectional_runner"),
            "audit_score": val(r, "audit_score"),
            "audit_grade": val(r, "audit_grade"),
            "promotion_tier": val(e, "promotion_tier"),
            "metadata_grade": val(m, "metadata_grade"),
            "source_lineage": "FIELD_LINKED_CURRENT_VIC",
            "physics_status": physics_status,
            "trust_level": trust_level,
            "trusted_for_modelling": "NO",
            "trusted_for_execution": "NO",
            "trusted_reason": "Passed promotion audit as field-linked sectional candidate.",
            "validation_status": "SHADOW_VALIDATION_REQUIRED",
            "notes": "Quarantined trusted universe. Not yet ingested into ratings/execution.",
        })

    with OUT_UNIVERSE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    trust = Counter(r["trust_level"] for r in out)
    physics = Counter(r["physics_status"] for r in out)

    summary = []
    summary.append({"metric": "trusted_universe_rows", "value": len(out)})
    summary.append({"metric": "trusted_for_modelling_yes", "value": sum(1 for r in out if r["trusted_for_modelling"] == "YES")})
    summary.append({"metric": "trusted_for_execution_yes", "value": sum(1 for r in out if r["trusted_for_execution"] == "YES")})
    for k, v in trust.most_common():
        summary.append({"metric": f"trust_level::{k}", "value": v})
    for k, v in physics.most_common():
        summary.append({"metric": f"physics_status::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ TRUSTED SECTIONAL UNIVERSE V2")
    print("=" * 88)
    print(f"trusted universe rows: {len(out)}")
    print(f"trusted for modelling YES: {sum(1 for r in out if r['trusted_for_modelling'] == 'YES')}")
    print(f"trusted for execution YES: {sum(1 for r in out if r['trusted_for_execution'] == 'YES')}")
    print(f"saved: {OUT_UNIVERSE}")
    print(f"saved: {OUT_SUMMARY}")
    print("trust levels:")
    for k, v in trust.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
