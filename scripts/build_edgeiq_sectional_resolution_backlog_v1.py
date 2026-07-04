import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

IN_DIAG = PUB / "edgeiq_sectional_ambiguity_diagnostics_v1.csv"
OUT_BACKLOG = PUB / "edgeiq_sectional_resolution_backlog_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_resolution_backlog_summary_v1.csv"

FIELDS = [
    "priority","backlog_category","race_date","track","race_no","horse",
    "ambiguity_reason","missing_evidence","suggested_resolution_path",
    "safe_to_escalate_candidate","recommended_action","notes"
]

CATEGORY_MAP = {
    "HORSE_NAME_COLLISION": "NEED_HORSE_ALIAS",
    "MISSING_RUNNER_NAME": "NEED_RUNNER_METADATA",
    "RACE_KEY_WEAK": "NEED_FIELD_COMPOSITION_REVIEW",
    "FIELD_OVERLAP_LOW": "NEED_FIELD_COMPOSITION_REVIEW",
    "MULTIPLE_CANDIDATES": "NEED_MANUAL_REVIEW",
    "DISTANCE_CONFLICT": "NEED_DISTANCE_REVIEW",
    "TRACK_ALIAS_CONFLICT": "NEED_TRACK_ALIAS",
    "DATE_MISMATCH": "NEED_FIELD_COMPOSITION_REVIEW",
    "PAYLOAD_LINEAGE_WEAK": "NEED_SOURCE_PAYLOAD_REVIEW",
    "DUPLICATE_RUNNER_CONFLICT": "NEED_DUPLICATE_SUPPRESSION",
    "NO_BARRIER_EVIDENCE": "NEED_RUNNER_METADATA",
    "NO_JOCKEY_EVIDENCE": "NEED_RUNNER_METADATA",
    "NO_TRAINER_EVIDENCE": "NEED_RUNNER_METADATA",
    "NO_SADDLECLOTH_EVIDENCE": "NEED_RUNNER_METADATA",
    "PHYSICS_VALID_BUT_IDENTITY_WEAK": "NEED_RUNNER_METADATA",
    "IDENTITY_TRUSTED_BUT_PAYLOAD_WEAK": "NEED_SOURCE_PAYLOAD_REVIEW",
}

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def priority_for(reason, safe):
    if reason in {"DUPLICATE_RUNNER_CONFLICT", "RACE_KEY_WEAK"}:
        return "CRITICAL"
    if safe == "YES":
        return "HIGH"
    if reason in {"PHYSICS_VALID_BUT_IDENTITY_WEAK", "MULTIPLE_CANDIDATES", "PAYLOAD_LINEAGE_WEAK"}:
        return "HIGH"
    if reason in {"DISTANCE_CONFLICT", "TRACK_ALIAS_CONFLICT"}:
        return "MEDIUM"
    return "LOW"

def action_for(category):
    return {
        "NEED_HORSE_ALIAS": "Add/verify canonical horse alias evidence before promotion.",
        "NEED_TRACK_ALIAS": "Review track alias mapping and sponsor-name normalisation.",
        "NEED_DISTANCE_REVIEW": "Compare sectional distance to EDGEiQ race distance.",
        "NEED_FIELD_COMPOSITION_REVIEW": "Repair race key/composition evidence before runner matching.",
        "NEED_SOURCE_PAYLOAD_REVIEW": "Inspect source lineage and payload provenance.",
        "NEED_DUPLICATE_SUPPRESSION": "Resolve duplicate runner/entity conflict before trust.",
        "NEED_RACINGCOM_SOURCE_MAPPING": "Map source race IDs only after ambiguity class is confirmed.",
        "NEED_RUNNER_METADATA": "Add barrier/jockey/trainer/saddlecloth tie-break evidence.",
        "NEED_MANUAL_REVIEW": "Queue high-confidence near-miss for manual review.",
    }.get(category, "Review ambiguity evidence.")

def main():
    rows = read_csv(IN_DIAG)
    backlog = []

    for r in rows:
        reason = r.get("ambiguity_reason", "")
        safe = r.get("safe_to_escalate_candidate", "")
        category = CATEGORY_MAP.get(reason, r.get("suggested_resolution_path", "") or "NEED_MANUAL_REVIEW")

        backlog.append({
            "priority": priority_for(reason, safe),
            "backlog_category": category,
            "race_date": r.get("race_date", ""),
            "track": r.get("track", ""),
            "race_no": r.get("race_no", ""),
            "horse": r.get("horse", "") or r.get("sectional_runner", ""),
            "ambiguity_reason": reason,
            "missing_evidence": r.get("missing_evidence", ""),
            "suggested_resolution_path": r.get("suggested_resolution_path", ""),
            "safe_to_escalate_candidate": safe,
            "recommended_action": action_for(category),
            "notes": r.get("notes", ""),
        })

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    backlog.sort(key=lambda r: (order.get(r["priority"], 9), r["backlog_category"], r["track"], r["race_no"], r["horse"]))

    with OUT_BACKLOG.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(backlog)

    pri = Counter(r["priority"] for r in backlog)
    cat = Counter(r["backlog_category"] for r in backlog)

    summary = []
    summary.append({"metric": "backlog_rows", "value": len(backlog)})
    for k, v in pri.items():
        summary.append({"metric": f"priority::{k}", "value": v})
    for k, v in cat.most_common():
        summary.append({"metric": f"category::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL RESOLUTION BACKLOG V1")
    print("=" * 88)
    print(f"diagnostic rows analysed: {len(rows)}")
    print(f"backlog rows written: {len(backlog)}")
    print(f"saved: {OUT_BACKLOG}")
    print(f"saved: {OUT_SUMMARY}")
    print("top categories:")
    for k, v in cat.most_common(10):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
