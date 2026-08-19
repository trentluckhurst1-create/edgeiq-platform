import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_ESCALATION = PUB / "edgeiq_field_linked_sectional_escalation_v1.csv"
IN_META = PUB / "edgeiq_runner_metadata_evidence_v1.csv"
IN_CONFLICTS = PUB / "edgeiq_runner_conflict_resolution_v1.csv"
IN_SPLITS = PUB / "edgeiq_canonical_split_schema_v1.csv"
IN_IDENTITY = PUB / "edgeiq_sectional_identity_engine_v3.csv"

OUT_AUDIT = PUB / "edgeiq_sectional_promotion_audit_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_promotion_audit_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse","sectional_runner",
    "candidate_status","audit_status","audit_grade","audit_score",
    "race_link_pass","runner_link_pass","metadata_pass","physics_pass",
    "source_lineage_pass","duplicate_conflict_pass","scratch_status_pass",
    "distance_pass","promotion_blockers","trusted_sectional_candidate",
    "notes"
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
    escalation = read_csv(IN_ESCALATION)
    meta = read_csv(IN_META)
    conflicts = read_csv(IN_CONFLICTS)
    splits = read_csv(IN_SPLITS)
    identity = read_csv(IN_IDENTITY)

    meta_lookup = {key(r): r for r in meta}

    conflict_keys = set()
    for r in conflicts:
        k = (
            val(r, "race_date") or val(r, "date") or val(r, "meeting_date"),
            val(r, "track") or val(r, "track_name") or val(r, "meeting"),
            val(r, "race_no") or val(r, "race_number"),
            norm(val(r, "horse") or val(r, "horse_name") or val(r, "runner_name")),
        )
        if any(k):
            conflict_keys.add(k)

    split_keys = set()
    for r in splits:
        k = (
            val(r, "race_date") or val(r, "date") or val(r, "meeting_date"),
            val(r, "track") or val(r, "track_name") or val(r, "meeting"),
            val(r, "race_no") or val(r, "race_number"),
            norm(val(r, "horse") or val(r, "horse_name") or val(r, "runner_name")),
        )
        if any(k):
            split_keys.add(k)

    out = []

    for r in escalation:
        k = key(r)
        m = meta_lookup.get(k, {})

        is_candidate = val(r, "promotion_status") == "PROMOTION_CANDIDATE"
        metadata_grade = val(m, "metadata_grade")
        scratching = val(m, "scratching_evidence")
        ambiguity_reason = val(r, "ambiguity_reason")

        race_link_pass = "YES" if val(r, "race_date") and val(r, "track") and val(r, "race_no") else "NO"
        runner_link_pass = "YES" if val(r, "horse") or val(r, "sectional_runner") else "NO"
        metadata_pass = "YES" if metadata_grade == "STRONG_METADATA" else "NO"
        physics_pass = "YES" if ambiguity_reason in {"PHYSICS_VALID_BUT_IDENTITY_WEAK", "MULTIPLE_CANDIDATES"} else "REVIEW"
        source_lineage_pass = "YES" if ambiguity_reason != "PAYLOAD_LINEAGE_WEAK" else "NO"
        duplicate_conflict_pass = "NO" if k in conflict_keys else "YES"
        scratch_status_pass = "NO" if scratching == "SCRATCHED" else "YES"
        distance_pass = "NO" if ambiguity_reason == "DISTANCE_CONFLICT" else "YES"

        checks = [
            race_link_pass,
            runner_link_pass,
            metadata_pass,
            physics_pass,
            source_lineage_pass,
            duplicate_conflict_pass,
            scratch_status_pass,
            distance_pass,
        ]

        score = 0
        for c in checks:
            if c == "YES":
                score += 12.5
            elif c == "REVIEW":
                score += 6.25

        blockers = []
        if not is_candidate:
            blockers.append("NOT_PROMOTION_CANDIDATE")
        if race_link_pass != "YES":
            blockers.append("RACE_LINK_FAIL")
        if runner_link_pass != "YES":
            blockers.append("RUNNER_LINK_FAIL")
        if metadata_pass != "YES":
            blockers.append("METADATA_FAIL")
        if physics_pass == "NO":
            blockers.append("PHYSICS_FAIL")
        if physics_pass == "REVIEW":
            blockers.append("PHYSICS_REVIEW")
        if source_lineage_pass != "YES":
            blockers.append("SOURCE_LINEAGE_FAIL")
        if duplicate_conflict_pass != "YES":
            blockers.append("DUPLICATE_CONFLICT")
        if scratch_status_pass != "YES":
            blockers.append("SCRATCHED")
        if distance_pass != "YES":
            blockers.append("DISTANCE_FAIL")

        if is_candidate and not blockers:
            audit_status = "PASS"
            grade = "PROMOTABLE"
            trusted = "YES"
        elif is_candidate and blockers == ["PHYSICS_REVIEW"]:
            audit_status = "REVIEW"
            grade = "NEAR_PROMOTABLE"
            trusted = "NO"
        elif is_candidate:
            audit_status = "REVIEW"
            grade = "BLOCKED_CANDIDATE"
            trusted = "NO"
        else:
            audit_status = "BLOCKED"
            grade = "NOT_A_CANDIDATE"
            trusted = "NO"

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "sectional_runner": val(r, "sectional_runner"),
            "candidate_status": val(r, "promotion_status"),
            "audit_status": audit_status,
            "audit_grade": grade,
            "audit_score": round(score, 2),
            "race_link_pass": race_link_pass,
            "runner_link_pass": runner_link_pass,
            "metadata_pass": metadata_pass,
            "physics_pass": physics_pass,
            "source_lineage_pass": source_lineage_pass,
            "duplicate_conflict_pass": duplicate_conflict_pass,
            "scratch_status_pass": scratch_status_pass,
            "distance_pass": distance_pass,
            "promotion_blockers": "|".join(blockers),
            "trusted_sectional_candidate": trusted,
            "notes": "Audit gate only. Trusted modelling ingestion must be a separate step.",
        })

    with OUT_AUDIT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    status = Counter(r["audit_status"] for r in out)
    grade = Counter(r["audit_grade"] for r in out)
    trusted = Counter(r["trusted_sectional_candidate"] for r in out)
    blockers = Counter()
    for r in out:
        for b in r["promotion_blockers"].split("|"):
            if b:
                blockers[b] += 1

    summary = []
    summary.append({"metric": "rows", "value": len(out)})
    summary.append({"metric": "trusted_sectional_candidates", "value": trusted.get("YES", 0)})
    for k, v in status.most_common():
        summary.append({"metric": f"audit_status::{k}", "value": v})
    for k, v in grade.most_common():
        summary.append({"metric": f"audit_grade::{k}", "value": v})
    for k, v in blockers.most_common():
        summary.append({"metric": f"blocker::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL PROMOTION AUDIT V1")
    print("=" * 88)
    print(f"rows analysed: {len(out)}")
    print(f"trusted sectional candidates: {trusted.get('YES', 0)}")
    print(f"saved: {OUT_AUDIT}")
    print(f"saved: {OUT_SUMMARY}")
    print("audit status:")
    for k, v in status.most_common():
        print(f"  {k}: {v}")
    print("top blockers:")
    for k, v in blockers.most_common(10):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
