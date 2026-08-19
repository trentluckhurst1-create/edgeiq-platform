import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_META = PUB / "edgeiq_runner_metadata_evidence_v1.csv"
IN_AMBIG = PUB / "edgeiq_sectional_ambiguity_diagnostics_v1.csv"
IN_IDENTITY = PUB / "edgeiq_sectional_identity_engine_v3.csv"

OUT_QUEUE = PUB / "edgeiq_field_linked_sectional_escalation_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_field_linked_sectional_escalation_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse","sectional_runner",
    "ambiguity_reason","metadata_score","metadata_grade",
    "safe_escalation_candidate","promotion_status","promotion_tier",
    "promotion_blocker","required_next_evidence","notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def val(row, name):
    return str(row.get(name, "") or "").strip()

def main():
    rows = read_csv(IN_META)

    out = []

    for r in rows:
        safe = val(r, "safe_escalation_candidate")
        grade = val(r, "metadata_grade")
        reason = val(r, "ambiguity_reason")
        score_raw = val(r, "metadata_score")

        try:
            score = float(score_raw)
        except Exception:
            score = 0.0

        blocker = ""
        required = ""
        status = "BLOCKED"
        tier = "NONE"

        if safe == "YES" and grade == "STRONG_METADATA" and score >= 85:
            status = "PROMOTION_CANDIDATE"
            tier = "FIELD_LINKED_STRONG"
            required = "PROMOTION_AUDIT_REQUIRED"
            blocker = ""
        elif grade == "PARTIAL_METADATA":
            status = "NEEDS_MORE_EVIDENCE"
            tier = "PARTIAL"
            blocker = val(r, "blocked_by")
            required = "BARRIER_JOCKEY_TRAINER_SADDLECLOTH"
        elif grade == "WEAK_METADATA":
            status = "BLOCKED"
            tier = "WEAK"
            blocker = val(r, "blocked_by")
            required = "FIELD_MATCH_AND_RUNNER_METADATA"
        else:
            status = "BLOCKED"
            tier = "NONE"
            blocker = val(r, "blocked_by")
            required = "RACE_KEY_AND_FIELD_LINK"

        out.append({
            "race_date": val(r, "race_date"),
            "track": val(r, "track"),
            "race_no": val(r, "race_no"),
            "horse": val(r, "horse"),
            "sectional_runner": val(r, "sectional_runner"),
            "ambiguity_reason": reason,
            "metadata_score": score_raw,
            "metadata_grade": grade,
            "safe_escalation_candidate": safe,
            "promotion_status": status,
            "promotion_tier": tier,
            "promotion_blocker": blocker,
            "required_next_evidence": required,
            "notes": "Candidate only. Not promoted to trusted modelling until audit passes.",
        })

    with OUT_QUEUE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    status_counts = Counter(r["promotion_status"] for r in out)
    tier_counts = Counter(r["promotion_tier"] for r in out)
    reason_counts = Counter(r["ambiguity_reason"] for r in out)

    summary = []
    summary.append({"metric": "rows", "value": len(out)})
    summary.append({"metric": "promotion_candidates", "value": status_counts.get("PROMOTION_CANDIDATE", 0)})
    for k, v in status_counts.most_common():
        summary.append({"metric": f"promotion_status::{k}", "value": v})
    for k, v in tier_counts.most_common():
        summary.append({"metric": f"promotion_tier::{k}", "value": v})
    for k, v in reason_counts.most_common():
        summary.append({"metric": f"ambiguity_reason::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ FIELD-LINKED SECTIONAL ESCALATION V1")
    print("=" * 88)
    print(f"metadata rows analysed: {len(rows)}")
    print(f"promotion candidates: {status_counts.get('PROMOTION_CANDIDATE', 0)}")
    print(f"saved: {OUT_QUEUE}")
    print(f"saved: {OUT_SUMMARY}")
    print("promotion status:")
    for k, v in status_counts.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
