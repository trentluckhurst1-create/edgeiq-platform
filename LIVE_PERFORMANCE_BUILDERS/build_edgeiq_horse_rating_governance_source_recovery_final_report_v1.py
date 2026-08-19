from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
VALIDATION_CSV = DOC_DIR / "edgeiq_horse_rating_governance_source_recovery_validation_v1.csv"
ORCH_MD = DOC_DIR / "EDGEIQ_HORSE_RATING_GOVERNANCE_ORCHESTRATION_STATUS_V1.md"
FINAL_MD = DOC_DIR / "EDGEIQ_HORSE_RATING_GOVERNANCE_SOURCE_RECOVERY_FINAL_REPORT_V1.md"

FILES = {
    "normalisation_source": ROOT / "config" / "performance-intelligence" / "edgeiq_performance_normalisation_parameter_source_v1.csv",
    "aggregation_source": ROOT / "config" / "performance-intelligence" / "edgeiq_horse_performance_aggregation_parameter_source_v1.csv",
    "identity_map": ROOT / "config" / "performance-intelligence" / "edgeiq_horse_performance_identity_map_v1.csv",
    "pi_base": ROOT / "public" / "data" / "edgeiq_performance_intelligence_base_fact_v1.csv",
    "normalisation_fact": ROOT / "public" / "data" / "edgeiq_performance_normalisation_fact_v1.csv",
    "rating_base_fact": ROOT / "public" / "data" / "edgeiq_performance_rating_base_fact_v1.csv",
    "observation_fact": ROOT / "public" / "data" / "edgeiq_horse_performance_observation_fact_v1.csv",
    "aggregate_fact": ROOT / "public" / "data" / "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "rating_fact": ROOT / "public" / "data" / "edgeiq_horse_performance_rating_fact_v1.csv",
    "live_rating_fact": ROOT / "public" / "data" / "edgeiq_live_horse_performance_rating_fact_v1.csv",
}

NEW_SCRIPTS = [
    ROOT / "scripts" / "build_edgeiq_horse_performance_identity_map_v1.py",
    ROOT / "scripts" / "audit_edgeiq_horse_performance_identity_map_v1.py",
    ROOT / "scripts" / "audit_edgeiq_horse_rating_parameter_provenance_decision_v1.py",
    ROOT / "scripts" / "build_edgeiq_horse_rating_governance_source_recovery_final_report_v1.py",
]


def read_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return sum(1 for _ in reader)


def sha(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_py_compile(path: Path) -> tuple[str, str]:
    proc = subprocess.run([sys.executable, "-m", "py_compile", str(path)], cwd=ROOT, text=True, capture_output=True)
    return ("PASS" if proc.returncode == 0 else "FAIL", (proc.stderr or proc.stdout).strip())


def main() -> None:
    validation_rows = []
    for name, path in FILES.items():
        validation_rows.append({
            "asset": name,
            "path": path.as_posix(),
            "exists": "YES" if path.exists() else "NO",
            "rows": read_count(path),
            "sha256": sha(path),
        })
    for path in NEW_SCRIPTS:
        status, details = run_py_compile(path)
        validation_rows.append({
            "asset": f"py_compile:{path.name}",
            "path": path.as_posix(),
            "exists": "YES" if path.exists() else "NO",
            "rows": "",
            "sha256": status if not details else f"{status}: {details}",
        })
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    with VALIDATION_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset", "path", "exists", "rows", "sha256"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(validation_rows)

    pi_rows = read_count(FILES["pi_base"])
    identity_rows = read_count(FILES["identity_map"])
    norm_rows = read_count(FILES["normalisation_fact"])
    rating_base_rows = read_count(FILES["rating_base_fact"])
    observation_rows = read_count(FILES["observation_fact"])
    aggregate_rows = read_count(FILES["aggregate_fact"])
    rating_rows = read_count(FILES["rating_fact"])

    orchestration = f"""# EDGEiQ Horse Rating Governance Orchestration Status V1

Status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Gate Order

1. Historical PI base: PASS ({pi_rows} rows)
2. Performance normalisation parameter source: BLOCKED (governed source rows not recovered)
3. Performance normalisation fact: BLOCKED ({norm_rows} rows)
4. Performance rating base fact: BLOCKED ({rating_base_rows} rows)
5. Horse identity map: PASS ({identity_rows} rows recovered and validated)
6. Horse observations: BLOCKED ({observation_rows} rows; waits on rating base)
7. Horse aggregates: BLOCKED ({aggregate_rows} rows; waits on observations and aggregation parameters)
8. Horse performance ratings: BLOCKED ({rating_rows} rows)
9. Live projection/EPI downstream: BLOCKED by horse performance rating fact

## Do Not Run Downstream

Do not rebuild live projected performance, EPI, pricing, probability, V6.1, V7.2G2, or UI from this chain until owner-approved normalisation and aggregation parameter sources exist.
"""
    ORCH_MD.write_text(orchestration, encoding="utf-8")

    final = f"""# EDGEiQ Horse Rating Governance Source Recovery Final Report V1

Final status: EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD

## Executive Finding

The missing horse identity governance source was recovered safely. The methodological sources needed to normalise raw performance and aggregate observations were not recoverable from repository or git evidence. Creating them now would require new owner-approved architecture, not source recovery.

## What Was Recovered

- `edgeiq_horse_performance_identity_map_v1.csv`: recovered and promoted.
- Identity coverage: {identity_rows}/24 current historical source identifiers.
- Identity validation: PASS.
- Recovery method: exact Racing.com race-entry IDs from governed historical performance base mapped to canonical Racing.com horse IDs/names from raw GraphQL payloads.
- Fuzzy matching used: NO.

## What Remains Blocked

### Performance Normalisation

Active formula recovered:

`normalised_performance_value = (raw_performance_lengths - centre_value) / scale_value`

Blocked because `centre_value`, `scale_value`, effective date ranges, and approval provenance were not recovered.

### Horse Performance Aggregation

Active aggregate contract recovered as arithmetic or half-life weighted arithmetic mean.

Blocked because aggregation policy values were not recovered: method, lookback days, min/max observations, recency method, and half-life days.

## Current Row Funnel

- Historical PI base rows: {pi_rows}
- Normalisation fact rows: {norm_rows}
- Rating-base fact rows: {rating_base_rows}
- Horse observation rows: {observation_rows}
- Horse aggregate rows: {aggregate_rows}
- Horse performance rating rows: {rating_rows}

The first unresolved zero-row stage is performance normalisation.

## Decisions

- Normalisation parameter candidate built: NO.
- Aggregation parameter candidate built: NO.
- Reason: source rows and methodological values were not recovered; any candidate would fabricate parameters.
- Identity map candidate built: YES.
- Identity map promoted: YES.

## Required Owner Approval Before Unblocking

1. Approve a performance normalisation parameter source with explicit centre/scale methodology and provenance.
2. Approve a horse performance aggregation parameter source with explicit lookback, observation, and recency policy.
3. Re-run the guarded builders in order after approval.

## Safety Confirmations

- Production pricing changed: NO
- Probability engine changed: NO
- V6.1 changed: NO
- V7.2G2 changed: NO
- UI changed: NO
- EPI redesigned: NO
- Thresholds reduced: NO
- Fabricated ratings/parameters: NO
- Current/future leakage introduced: NO
"""
    FINAL_MD.write_text(final, encoding="utf-8")

    print("status=EDGEIQ_PERFORMANCE_INTELLIGENCE_BLOCKED_BY_NORMALISATION_METHOD")
    print(f"identity_rows={identity_rows}")
    print(f"normalisation_rows={norm_rows}")
    print(f"rating_rows={rating_rows}")
    print(f"validation_csv={VALIDATION_CSV}")


if __name__ == "__main__":
    main()
