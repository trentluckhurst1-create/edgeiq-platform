import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

INPUTS = {
    "ambiguity": PUB / "edgeiq_sectional_ambiguity_diagnostics_v1.csv",
    "fields": PUB / "edgeiq_vic_three_day_race_fields.csv",
    "universe": PUB / "edgeiq_vic_three_day_meeting_universe.csv",
    "scratchings": PUB / "edgeiq_vic_scratchings_diagnostics.csv",
    "silks": PUB / "edgeiq_silk_enrichment_diagnostics.csv",
}

OUT_DETAIL = PUB / "edgeiq_runner_metadata_evidence_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_runner_metadata_summary_v1.csv"

FIELDS = [
    "race_date","track","race_no","horse","sectional_runner",
    "ambiguity_reason","field_match","horse_name_match","saddlecloth_evidence",
    "barrier_evidence","jockey_evidence","trainer_evidence","silk_evidence",
    "scratching_evidence","metadata_score","metadata_grade",
    "safe_escalation_candidate","blocked_by","evidence_notes"
]

def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(v):
    return "".join(ch for ch in str(v or "").upper().strip() if ch.isalnum())

def val(row, *names):
    for n in names:
        if n in row and str(row.get(n, "")).strip():
            return str(row.get(n, "")).strip()
    return ""

def race_key(row):
    return (
        val(row, "race_date", "date", "meeting_date"),
        val(row, "track", "track_name", "meeting"),
        val(row, "race_no", "race_number"),
    )

def horse_key(row):
    return norm(val(row, "horse", "horse_name", "runner_name", "sectional_runner"))

def evidence_value(source, *names):
    for n in names:
        if n in source and str(source.get(n, "")).strip():
            return str(source.get(n, "")).strip()
    return ""

def main():
    PUB.mkdir(parents=True, exist_ok=True)

    ambiguity = read_csv(INPUTS["ambiguity"])
    fields = read_csv(INPUTS["fields"])
    scratchings = read_csv(INPUTS["scratchings"])
    silks = read_csv(INPUTS["silks"])

    field_lookup = {}
    race_field_counts = Counter()

    for r in fields:
        rk = race_key(r)
        hk = horse_key(r)
        if rk and hk:
            field_lookup[(rk, hk)] = r
            race_field_counts[rk] += 1

    scratching_lookup = set()
    for r in scratchings:
        hk = horse_key(r)
        rk = race_key(r)
        status = val(r, "scratched", "is_scratched", "status", "scratching_status")
        if hk and ("SCRATCH" in status.upper() or status.upper() in {"YES", "TRUE", "1"}):
            scratching_lookup.add((rk, hk))

    silk_lookup = set()
    for r in silks:
        hk = horse_key(r)
        rk = race_key(r)
        path = val(r, "silk_path", "image_path", "silk_url", "local_path")
        if hk and path:
            silk_lookup.add((rk, hk))

    out = []

    for r in ambiguity:
        rk = race_key(r)
        horse = val(r, "horse")
        sectional_runner = val(r, "sectional_runner")
        hk = norm(horse or sectional_runner)

        field_row = field_lookup.get((rk, hk), {})
        field_match = "YES" if field_row else "NO"

        horse_name_match = "YES" if field_match else "NO"

        saddlecloth = evidence_value(field_row, "saddlecloth", "number", "runner_number", "cloth_number")
        barrier = evidence_value(field_row, "barrier", "barrier_no", "barrier_number")
        jockey = evidence_value(field_row, "jockey", "jockey_name")
        trainer = evidence_value(field_row, "trainer", "trainer_name")

        saddlecloth_evidence = "YES" if saddlecloth else "NO"
        barrier_evidence = "YES" if barrier else "NO"
        jockey_evidence = "YES" if jockey else "NO"
        trainer_evidence = "YES" if trainer else "NO"
        silk_evidence = "YES" if (rk, hk) in silk_lookup else "NO"
        scratching_evidence = "SCRATCHED" if (rk, hk) in scratching_lookup else "ACTIVE_OR_UNKNOWN"

        score = 0
        score += 25 if field_match == "YES" else 0
        score += 20 if horse_name_match == "YES" else 0
        score += 15 if saddlecloth_evidence == "YES" else 0
        score += 15 if barrier_evidence == "YES" else 0
        score += 10 if jockey_evidence == "YES" else 0
        score += 10 if trainer_evidence == "YES" else 0
        score += 5 if silk_evidence == "YES" else 0

        if scratching_evidence == "SCRATCHED":
            score = min(score, 50)

        if score >= 85:
            grade = "STRONG_METADATA"
        elif score >= 65:
            grade = "PARTIAL_METADATA"
        elif score >= 35:
            grade = "WEAK_METADATA"
        else:
            grade = "NO_METADATA"

        blockers = []
        if field_match == "NO":
            blockers.append("NO_FIELD_MATCH")
        if barrier_evidence == "NO":
            blockers.append("NO_BARRIER")
        if jockey_evidence == "NO":
            blockers.append("NO_JOCKEY")
        if trainer_evidence == "NO":
            blockers.append("NO_TRAINER")
        if saddlecloth_evidence == "NO":
            blockers.append("NO_SADDLECLOTH")
        if scratching_evidence == "SCRATCHED":
            blockers.append("SCRATCHED")

        safe = "YES" if grade == "STRONG_METADATA" and scratching_evidence != "SCRATCHED" else "NO"

        out.append({
            "race_date": rk[0],
            "track": rk[1],
            "race_no": rk[2],
            "horse": horse,
            "sectional_runner": sectional_runner,
            "ambiguity_reason": val(r, "ambiguity_reason"),
            "field_match": field_match,
            "horse_name_match": horse_name_match,
            "saddlecloth_evidence": saddlecloth_evidence,
            "barrier_evidence": barrier_evidence,
            "jockey_evidence": jockey_evidence,
            "trainer_evidence": trainer_evidence,
            "silk_evidence": silk_evidence,
            "scratching_evidence": scratching_evidence,
            "metadata_score": score,
            "metadata_grade": grade,
            "safe_escalation_candidate": safe,
            "blocked_by": "|".join(blockers),
            "evidence_notes": f"saddlecloth={saddlecloth}; barrier={barrier}; jockey={jockey}; trainer={trainer}",
        })

    with OUT_DETAIL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    grades = Counter(r["metadata_grade"] for r in out)
    blockers = Counter()
    reasons = Counter(r["ambiguity_reason"] for r in out)

    for r in out:
        for b in r["blocked_by"].split("|"):
            if b:
                blockers[b] += 1

    summary = []
    summary.append({"metric": "rows", "value": len(out)})
    summary.append({"metric": "safe_escalation_candidates", "value": sum(1 for r in out if r["safe_escalation_candidate"] == "YES")})
    for k, v in grades.most_common():
        summary.append({"metric": f"metadata_grade::{k}", "value": v})
    for k, v in blockers.most_common():
        summary.append({"metric": f"blocker::{k}", "value": v})
    for k, v in reasons.most_common():
        summary.append({"metric": f"ambiguity_reason::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ RUNNER METADATA EVIDENCE V1")
    print("=" * 88)
    print(f"ambiguity rows analysed: {len(ambiguity)}")
    print(f"evidence rows written: {len(out)}")
    print(f"safe escalation candidates: {sum(1 for r in out if r['safe_escalation_candidate'] == 'YES')}")
    print(f"saved: {OUT_DETAIL}")
    print(f"saved: {OUT_SUMMARY}")
    print("metadata grades:")
    for k, v in grades.most_common():
        print(f"  {k}: {v}")
    print("top blockers:")
    for k, v in blockers.most_common(10):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
