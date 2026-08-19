import csv
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "public" / "data"

INPUTS = {
    "identity": PUB / "edgeiq_sectional_identity_engine_v3.csv",
    "graph": PUB / "edgeiq_runner_entity_graph_v1.csv",
    "conflicts": PUB / "edgeiq_runner_conflict_resolution_v1.csv",
    "composition": PUB / "edgeiq_sectional_field_composition_match_v1.csv",
    "splits": PUB / "edgeiq_canonical_split_schema_v1.csv",
    "universe": PUB / "edgeiq_vic_three_day_meeting_universe.csv",
}

OUT_DETAIL = PUB / "edgeiq_sectional_ambiguity_diagnostics_v1.csv"
OUT_SUMMARY = PUB / "edgeiq_sectional_ambiguity_summary_v1.csv"

DETAIL_FIELDS = [
    "race_date","track","race_no","distance","horse","horse_key",
    "sectional_runner","sectional_source","identity_v3_status",
    "race_identity_status","runner_entity_confidence","conflict_type",
    "ambiguity_reason","missing_evidence","suggested_resolution_path",
    "safe_to_escalate_candidate","notes"
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

def key_parts(row):
    return (
        val(row, "race_date", "date", "meeting_date"),
        val(row, "track", "track_name", "meeting"),
        val(row, "race_no", "race_number"),
        val(row, "horse", "horse_name", "runner_name", "sectional_runner"),
    )

def make_reason(row, conflict_lookup, split_lookup):
    horse = val(row, "horse", "horse_name", "runner_name")
    sectional_runner = val(row, "sectional_runner", "runner", "runner_name", "horse")
    race_status = val(row, "race_identity_status", "race_status", "race_match_status")
    identity_status = val(row, "identity_v3_status", "identity_status", "runner_identity_status")
    confidence = val(row, "runner_entity_confidence", "confidence", "entity_confidence")
    source = val(row, "sectional_source", "source", "source_file")
    race_date, track, race_no, _ = key_parts(row)

    conflict_key = "|".join([race_date, track, race_no, horse or sectional_runner]).upper()
    conflict = conflict_lookup.get(conflict_key, "")

    missing = []
    if not horse and not sectional_runner:
        return "MISSING_RUNNER_NAME", "horse_name/sectional_runner", "NEED_RUNNER_METADATA", "NO", "No runner name exists on the sectional row."

    if conflict:
        return "DUPLICATE_RUNNER_CONFLICT", "unique_runner_entity", "NEED_DUPLICATE_SUPPRESSION", "NO", conflict

    if not race_date:
        missing.append("race_date")
    if not track:
        missing.append("track")
    if not race_no:
        missing.append("race_no")
    if missing:
        return "RACE_KEY_WEAK", ",".join(missing), "NEED_FIELD_COMPOSITION_REVIEW", "NO", "Race key is incomplete."

    if "trusted" in race_status.lower() and "trusted" not in identity_status.lower():
        return "PHYSICS_VALID_BUT_IDENTITY_WEAK", "runner_identity_evidence", "NEED_RUNNER_METADATA", "YES", "Race-level evidence exists but runner-level identity remains unsafe."

    if "distance" in str(row).lower() and val(row, "distance_conflict"):
        return "DISTANCE_CONFLICT", "distance", "NEED_DISTANCE_REVIEW", "NO", "Distance evidence conflicts."

    if source == "":
        return "PAYLOAD_LINEAGE_WEAK", "sectional_source", "NEED_SOURCE_PAYLOAD_REVIEW", "NO", "No reliable sectional source lineage."

    if confidence:
        try:
            c = float(confidence)
            if c >= 0.75:
                return "MULTIPLE_CANDIDATES", "tie_breaker_metadata", "NEED_MANUAL_REVIEW", "YES", "High-confidence near miss still needs tie-break evidence."
        except Exception:
            pass

    return "MULTIPLE_CANDIDATES", "barrier/jockey/trainer/saddlecloth", "NEED_RUNNER_METADATA", "NO", "Default unresolved runner ambiguity."

def main():
    PUB.mkdir(parents=True, exist_ok=True)

    identity_rows = read_csv(INPUTS["identity"])
    conflict_rows = read_csv(INPUTS["conflicts"])
    split_rows = read_csv(INPUTS["splits"])

    conflict_lookup = {}
    for r in conflict_rows:
        race_date, track, race_no, horse = key_parts(r)
        k = "|".join([race_date, track, race_no, horse]).upper()
        if k.strip("|"):
            conflict_lookup[k] = val(r, "conflict_type", "reason", "notes") or "runner conflict"

    split_lookup = {}
    for r in split_rows:
        race_date, track, race_no, horse = key_parts(r)
        k = "|".join([race_date, track, race_no, horse]).upper()
        if k.strip("|"):
            split_lookup[k] = r

    out = []
    for r in identity_rows:
        identity_status = val(r, "identity_v3_status", "identity_status", "runner_identity_status")
        race_status = val(r, "race_identity_status", "race_status", "race_match_status")
        trusted_runner = "trusted" in identity_status.lower()

        if trusted_runner:
            continue

        reason, missing, path, safe, notes = make_reason(r, conflict_lookup, split_lookup)

        out.append({
            "race_date": val(r, "race_date", "date", "meeting_date"),
            "track": val(r, "track", "track_name", "meeting"),
            "race_no": val(r, "race_no", "race_number"),
            "distance": val(r, "distance", "race_distance", "distance_m"),
            "horse": val(r, "horse", "horse_name", "runner_name"),
            "horse_key": val(r, "horse_key", "runner_key", "canonical_horse_key"),
            "sectional_runner": val(r, "sectional_runner", "runner", "runner_name", "horse"),
            "sectional_source": val(r, "sectional_source", "source", "source_file"),
            "identity_v3_status": identity_status,
            "race_identity_status": race_status,
            "runner_entity_confidence": val(r, "runner_entity_confidence", "confidence", "entity_confidence"),
            "conflict_type": conflict_lookup.get("|".join(key_parts(r)).upper(), ""),
            "ambiguity_reason": reason,
            "missing_evidence": missing,
            "suggested_resolution_path": path,
            "safe_to_escalate_candidate": safe,
            "notes": notes,
        })

    with OUT_DETAIL.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DETAIL_FIELDS)
        w.writeheader()
        w.writerows(out)

    reason_counts = Counter(r["ambiguity_reason"] for r in out)
    path_counts = Counter(r["suggested_resolution_path"] for r in out)

    summary = []
    summary.append({"metric": "ambiguous_rows", "value": len(out)})
    summary.append({"metric": "safe_to_escalate_candidates", "value": sum(1 for r in out if r["safe_to_escalate_candidate"] == "YES")})
    for k, v in reason_counts.most_common():
        summary.append({"metric": f"ambiguity_reason::{k}", "value": v})
    for k, v in path_counts.most_common():
        summary.append({"metric": f"resolution_path::{k}", "value": v})

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("=" * 88)
    print("EDGEIQ SECTIONAL AMBIGUITY DIAGNOSTICS V1")
    print("=" * 88)
    print(f"identity rows analysed: {len(identity_rows)}")
    print(f"ambiguous rows written: {len(out)}")
    print(f"saved: {OUT_DETAIL}")
    print(f"saved: {OUT_SUMMARY}")
    print("top reasons:")
    for k, v in reason_counts.most_common(10):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
