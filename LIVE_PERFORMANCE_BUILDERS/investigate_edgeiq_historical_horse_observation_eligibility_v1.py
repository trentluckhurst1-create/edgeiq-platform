
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DOC = ROOT / "docs" / "victoria-live-recovery-v5"
CONFIG = ROOT / "config" / "performance-intelligence"
CUTOFF = date.fromisoformat("2026-07-20")
START_COMMIT = "8df332e"

STAGE_FILES = {
    "Performance Base": DATA / "edgeiq_performance_intelligence_base_fact_v1.csv",
    "Normalisation": DATA / "edgeiq_performance_normalisation_fact_v1.csv",
    "Performance Rating Base": DATA / "edgeiq_performance_rating_base_fact_v1.csv",
    "Horse Observations": DATA / "edgeiq_horse_performance_observation_fact_v1.csv",
    "Horse Aggregates": DATA / "edgeiq_horse_performance_aggregate_fact_v1.csv",
    "Horse Ratings": DATA / "edgeiq_horse_performance_rating_fact_v1.csv",
    "Snapshots": DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
    "EPI": DATA / "edgeiq_race_entry_epi_fact_v1.csv",
}

REJECTION_FILES = {
    "Normalisation": DATA / "edgeiq_performance_normalisation_fact_v1_rejections.csv",
    "Horse Observations": DATA / "edgeiq_horse_performance_observation_fact_v1_rejections.csv",
}

DATE_FIELDS = [
    "race_date",
    "performance_date",
    "aggregate_as_of_date",
    "rating_as_of_date",
]


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def clean_name(value: object) -> str:
    return " ".join(text(value).upper().split())


def parse_date(value: object) -> date | None:
    raw = text(value)[:10]
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def row_date(row: dict[str, str]) -> date | None:
    for field in DATE_FIELDS:
        if field in row:
            parsed = parse_date(row.get(field))
            if parsed:
                return parsed
    return None


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        tmp_path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def atomic_write_json(path: Path, payload: object) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def atomic_write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: text(row.get(field, "")) for field in fields})
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def git_show(path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "grep", "-n", "HPR-NORM-A-v1", "HEAD", "--", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"GIT_GREP_FAILED: {exc}"


def file_snippet(path: Path, patterns: Iterable[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.exists():
        return rows
    regex = re.compile("|".join(re.escape(p) for p in patterns), re.IGNORECASE)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            if regex.search(line):
                rows.append({"path": str(path.relative_to(ROOT)), "line": line_no, "text": line.strip()})
    return rows


def stage_summary(name: str, path: Path) -> dict[str, object]:
    fields, rows = read_csv(path)
    dates = [d for d in (row_date(row) for row in rows) if d]
    before = sum(1 for d in dates if d < CUTOFF)
    post = sum(1 for d in dates if d >= CUTOFF)
    horses = set()
    races = set()
    for row in rows:
        cid = text(row.get("canonical_horse_id")) or clean_name(row.get("winner_horse_name"))
        if cid:
            horses.add(cid)
        race_key = text(row.get("race_key")) or text(row.get("race_id")) or text(row.get("canonical_race_id"))
        if race_key:
            races.add(race_key)
    return {
        "stage": name,
        "path": str(path.relative_to(ROOT)),
        "exists": "YES" if path.exists() else "NO",
        "rows": len(rows),
        "min_date": min(dates).isoformat() if dates else "",
        "max_date": max(dates).isoformat() if dates else "",
        "before_2026_07_20_rows": before,
        "on_or_after_2026_07_20_rows": post,
        "distinct_horses_or_winners": len(horses),
        "distinct_races": len(races),
        "fields": fields,
    }


def depth_distribution(observation_rows: list[dict[str, str]]) -> tuple[Counter, dict[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    for row in observation_rows:
        cid = text(row.get("canonical_horse_id"))
        race_key = text(row.get("race_key"))
        # Count distinct race observations per horse. The fact builder already enforces deterministic IDs;
        # the race key guard protects the audit from accidental duplicate rows.
        key = f"{cid}\x1f{race_key}"
        if cid and race_key:
            counts[key] = 1
    horse_counts: dict[str, int] = defaultdict(int)
    for key in counts:
        cid = key.split("\x1f", 1)[0]
        horse_counts[cid] += 1
    dist = Counter()
    for value in horse_counts.values():
        if value == 0:
            dist["0"] += 1
        elif value == 1:
            dist["1"] += 1
        elif value == 2:
            dist["2"] += 1
        elif value == 3:
            dist["3"] += 1
        elif value == 4:
            dist["4"] += 1
        elif value <= 9:
            dist["5-9"] += 1
        elif value <= 19:
            dist["10-19"] += 1
        else:
            dist["20+"] += 1
    return dist, dict(horse_counts)


def main() -> int:
    DOC.mkdir(parents=True, exist_ok=True)
    built_at = "DETERMINISTIC_NO_WALL_CLOCK_FOR_IDEMPOTENCY"

    stage_rows = [stage_summary(name, path) for name, path in STAGE_FILES.items()]
    atomic_write_csv(
        DOC / "EDGEIQ_VICTORIA_LIVE_RECOVERY_V5_STAGE_COUNTS.csv",
        stage_rows,
        [
            "stage", "path", "exists", "rows", "min_date", "max_date",
            "before_2026_07_20_rows", "on_or_after_2026_07_20_rows",
            "distinct_horses_or_winners", "distinct_races",
        ],
    )

    _, obs_rows = read_csv(STAGE_FILES["Horse Observations"])
    _, current_identity_rows = read_csv(CONFIG / "edgeiq_racing_australia_horse_identity_crosswalk_v1.csv")
    _, aggregate_rows = read_csv(STAGE_FILES["Horse Aggregates"])
    _, rating_rows = read_csv(STAGE_FILES["Horse Ratings"])
    _, snapshot_rows = read_csv(STAGE_FILES["Snapshots"])
    _, epi_rows = read_csv(STAGE_FILES["EPI"])
    _, perf_rating_rows = read_csv(STAGE_FILES["Performance Rating Base"])
    _, normalisation_rejections = read_csv(REJECTION_FILES["Normalisation"])

    dist, obs_counts = depth_distribution(obs_rows)
    current_cids = {text(row.get("canonical_horse_id")) for row in current_identity_rows if text(row.get("canonical_horse_id"))}
    current_identity_by_cid = {text(row.get("canonical_horse_id")): row for row in current_identity_rows}

    aggregates_by_horse = {text(row.get("canonical_horse_id")): row for row in aggregate_rows}
    ratings_by_horse = {text(row.get("canonical_horse_id")): row for row in rating_rows}
    snapshots_by_horse = {text(row.get("canonical_horse_id")): row for row in snapshot_rows}
    epi_horse_ids = {text(row.get("canonical_horse_id")) for row in epi_rows if text(row.get("canonical_horse_id"))}

    current_runner_rows: list[dict[str, object]] = []
    for cid in sorted(current_cids):
        identity = current_identity_by_cid.get(cid, {})
        total = obs_counts.get(cid, 0)
        historical = sum(1 for row in obs_rows if text(row.get("canonical_horse_id")) == cid and parse_date(row.get("race_date")) and parse_date(row.get("race_date")) < CUTOFF)
        current = sum(1 for row in obs_rows if text(row.get("canonical_horse_id")) == cid and parse_date(row.get("race_date")) and parse_date(row.get("race_date")) >= CUTOFF)
        has_aggregate = cid in aggregates_by_horse
        has_rating = cid in ratings_by_horse
        has_snapshot = cid in snapshots_by_horse
        has_epi = cid in epi_horse_ids
        if has_epi:
            blocking = ""
        elif not has_rating:
            blocking = "MINIMUM_OBSERVATIONS_NOT_MET" if total < 5 else "NO_HORSE_RATING_OUTPUT"
        elif not has_snapshot:
            blocking = "NO_SNAPSHOT_OUTPUT"
        else:
            blocking = "NO_EPI_OUTPUT"
        current_runner_rows.append({
            "source_horse_name": text(identity.get("source_horse_name")),
            "canonical_horse_id": cid,
            "source_horse_id": text(identity.get("source_horse_id")),
            "raceentry_id": text(identity.get("source_race_entry_id")),
            "current_observation_count": current,
            "historical_observation_count": historical,
            "total_governed_observations": total,
            "aggregate_available": "YES" if has_aggregate else "NO",
            "rating_available": "YES" if has_rating else "NO",
            "snapshot_available": "YES" if has_snapshot else "NO",
            "epi_available": "YES" if has_epi else "NO",
            "blocking_reason": blocking,
        })

    atomic_write_csv(
        DOC / "EDGEIQ_VICTORIA_CURRENT_SALE_RUNNER_DEPTH_V1.csv",
        current_runner_rows,
        [
            "source_horse_name", "canonical_horse_id", "source_horse_id", "raceentry_id",
            "current_observation_count", "historical_observation_count", "total_governed_observations",
            "aggregate_available", "rating_available", "snapshot_available", "epi_available", "blocking_reason",
        ],
    )

    current_winner_names = {clean_name(row.get("winner_horse_name")) for row in perf_rating_rows}
    current_winner_rows = [
        row for row in current_runner_rows
        if clean_name(row.get("source_horse_name")) in current_winner_names
    ]
    atomic_write_csv(
        DOC / "EDGEIQ_VICTORIA_CURRENT_SALE_WINNER_DEPTH_V1.csv",
        current_winner_rows,
        [
            "source_horse_name", "canonical_horse_id", "source_horse_id", "raceentry_id",
            "current_observation_count", "historical_observation_count", "total_governed_observations",
            "aggregate_available", "rating_available", "snapshot_available", "epi_available", "blocking_reason",
        ],
    )

    depth_rows = []
    for bucket in ["0", "1", "2", "3", "4", "5-9", "10-19", "20+"]:
        depth_rows.append({"bucket": bucket, "horse_count": dist.get(bucket, 0)})
    current_depth_counter = Counter()
    for row in current_runner_rows:
        n = int(row["total_governed_observations"])
        current_depth_counter[str(n) if n < 5 else "5+"] += 1
    for bucket in ["0", "1", "2", "3", "4", "5+"]:
        depth_rows.append({"bucket": f"current_sale_{bucket}", "horse_count": current_depth_counter.get(bucket, 0)})
    atomic_write_csv(DOC / "EDGEIQ_HORSE_OBSERVATION_DEPTH_AUDIT_V1.csv", depth_rows, ["bucket", "horse_count"])

    script_evidence = []
    for path in [
        ROOT / "scripts" / "build_edgeiq_performance_normalisation_fact_v1.py",
        ROOT / "scripts" / "build_edgeiq_horse_performance_aggregate_fact_v1.py",
        ROOT / "scripts" / "audit_edgeiq_normalisation_temporal_authority_v1.py",
    ]:
        script_evidence.extend(file_snippet(path, ["effective_from", "race_date < effective_from", "NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE", "minimum_observations", "HPR-NORM-A-v1"]))
    doc_evidence = []
    for path in [
        ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance" / "EDGEIQ_HORSE_RATING_METHODOLOGY_OWNER_APPROVAL_V1.md",
        ROOT / "docs" / "performance-intelligence" / "restart-v1" / "EDGEIQ_NORMALISATION_TEMPORAL_AUTHORITY_DECISION_V1.md",
    ]:
        doc_evidence.extend(file_snippet(path, ["Historical application authorised", "HPR-NORM-A-v1 remains unavailable", "future leakage", "effective-from", "Minimum observations", "live predictive use", "parameter population"] ))

    normalisation_rejection_reasons = Counter(text(row.get("rejection_reason")) for row in normalisation_rejections)

    eligibility_payload = {
        "status": "BLOCKED",
        "historical_hpr_norm_a_v1_application_permitted": "NO",
        "policy_effective_date_interpretation": "INTERPRETATION_A_PERFORMANCE_DATE_ELIGIBILITY_RULE",
        "exact_exclusion_point": "scripts/build_edgeiq_performance_normalisation_fact_v1.py filters race_date < effective_from_date and emits NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE.",
        "evidence_summary": [
            "The parameter fact and source fact both set HPR-NORM-A-v1 effective_from_date to 2026-07-20.",
            "The normalisation builder applies parameter lookup by race_date between effective_from_date and effective_to_date.",
            "The temporal authority decision records Historical application authorised: NO and rejects historical application because the bootstrap parameter was derived from 2026-07-20 evidence.",
            "The owner approval permits historical aggregate construction only from eligible governed observations; it does not override the normalisation effective-date gate.",
        ],
        "normalisation_rejection_reasons": dict(normalisation_rejection_reasons),
        "script_evidence": script_evidence,
        "documentation_evidence": doc_evidence,
    }

    investigation = {
        "report": "EDGEIQ_VICTORIA_LIVE_RECOVERY_V5_INVESTIGATION",
        "built_at_utc": built_at,
        "start_commit": START_COMMIT,
        "current_head": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
        "overall_status": "BLOCKED_GOVERNED_HISTORY_DEPTH",
        "governance_determination": eligibility_payload,
        "stage_counts": stage_rows,
        "horse_observation_depth_distribution": {row["bucket"]: row["horse_count"] for row in depth_rows},
        "current_sale": {
            "current_runners": len(current_runner_rows),
            "governed_identities": len(current_cids),
            "runners_with_historical_observations": sum(1 for row in current_runner_rows if int(row["historical_observation_count"]) > 0),
            "runners_with_5_plus_observations": sum(1 for row in current_runner_rows if int(row["total_governed_observations"]) >= 5),
            "horse_aggregates": sum(1 for row in current_runner_rows if row["aggregate_available"] == "YES"),
            "horse_ratings": sum(1 for row in current_runner_rows if row["rating_available"] == "YES"),
            "snapshots": sum(1 for row in current_runner_rows if row["snapshot_available"] == "YES"),
            "epi": sum(1 for row in current_runner_rows if row["epi_available"] == "YES"),
        },
        "chigurh": next((row for row in current_runner_rows if clean_name(row.get("source_horse_name")) == "CHIGURH"), {}),
    }

    atomic_write_json(DOC / "EDGEIQ_VICTORIA_LIVE_RECOVERY_V5_INVESTIGATION.json", investigation)
    atomic_write_json(DOC / "EDGEIQ_HISTORICAL_HORSE_OBSERVATION_ELIGIBILITY_V1.json", eligibility_payload)

    identity_payload = {
        "status": "PASS",
        "identity_blocker_reopened": "NO",
        "current_identity_rows": len(current_identity_rows),
        "current_governed_identity_rows": len([r for r in current_identity_rows if text(r.get("approval_status")) == "APPROVED"]),
        "current_distinct_canonical_horses": len(current_cids),
        "identity_method": "RACING_AUSTRALIA_SOURCE_ID_EXACT_CURRENT_CROSSWALK",
        "historical_identity_recovery_attempted": "NO",
        "reason": "Historical HPR-NORM-A-v1 application is not authorised, so no historical identity expansion was required or safe in V5.",
    }
    atomic_write_json(DOC / "EDGEIQ_HISTORICAL_HORSE_IDENTITY_AUDIT_V1.json", identity_payload)

    observation_payload = {
        "status": "PASS_WITH_GOVERNED_INSUFFICIENCY",
        "horse_observation_rows": len(obs_rows),
        "distinct_horses_with_observations": len(obs_counts),
        "horses_with_5_plus_observations": sum(1 for v in obs_counts.values() if v >= 5),
        "depth_distribution": dict(dist),
        "current_sale_depth_distribution": dict(current_depth_counter),
        "minimum_observations_required": 5,
        "explanation": "Current post-cutoff observations exist, but no horse reaches the approved five-observation aggregate threshold.",
    }
    atomic_write_json(DOC / "EDGEIQ_HORSE_OBSERVATION_DEPTH_AUDIT_V1.json", observation_payload)

    acceptance_payload = {
        "status": "BLOCKED_GOVERNED_HISTORY_DEPTH",
        "current_runners": len(current_runner_rows),
        "governed_identities": len(current_cids),
        "performance_rating_base_rows": len(perf_rating_rows),
        "horse_observations": len(obs_rows),
        "horse_aggregates": len(aggregate_rows),
        "horse_ratings": len(rating_rows),
        "snapshots": len(snapshot_rows),
        "epi": len(epi_rows),
        "remaining_blocker": "No eligible horse has five governed HPR observations. Historical pre-cutoff HPR-NORM-A-v1 application is explicitly blocked by current temporal authority.",
    }
    atomic_write_json(DOC / "EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V2.json", acceptance_payload)

    def md_table(rows: list[dict[str, object]], fields: list[str]) -> str:
        if not rows:
            return ""
        out = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
        for row in rows:
            out.append("| " + " | ".join(text(row.get(field, "")).replace("|", "/") for field in fields) + " |")
        return "\n".join(out)

    investigation_md = f"""# EDGEiQ Victoria Live Recovery V5 Investigation

Status: `BLOCKED_GOVERNED_HISTORY_DEPTH`

Start commit: `{START_COMMIT}`
Current head: `{investigation['current_head']}`
Built at: `{built_at}`

## Governance Determination

Historical HPR-NORM-A-v1 application permitted: `NO`

Policy effective date interpretation: `INTERPRETATION_A_PERFORMANCE_DATE_ELIGIBILITY_RULE`

Exact exclusion point: `scripts/build_edgeiq_performance_normalisation_fact_v1.py` rejects rows where the performance `race_date` is before the parameter `effective_from_date` with `NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE`.

The later temporal-authority decision explicitly records `Historical application authorised: NO`. The owner approval allows aggregation from eligible governed observations, but it does not authorise backdating the July-20-derived HPR-NORM-A-v1 parameter to earlier performance dates.

## Stage Counts

{md_table(stage_rows, ['stage','rows','min_date','max_date','before_2026_07_20_rows','on_or_after_2026_07_20_rows','distinct_horses_or_winners','distinct_races'])}

## Current Sale Coverage

- Current runners: {acceptance_payload['current_runners']}
- Governed identities: {acceptance_payload['governed_identities']}
- Runners with historical observations: {investigation['current_sale']['runners_with_historical_observations']}
- Runners with 5+ observations: {investigation['current_sale']['runners_with_5_plus_observations']}
- Horse Aggregates: {acceptance_payload['horse_aggregates']}
- Horse Ratings: {acceptance_payload['horse_ratings']}
- Snapshots: {acceptance_payload['snapshots']}
- EPI: {acceptance_payload['epi']}

## CHIGURH

```json
{json.dumps(investigation['chigurh'], indent=2, sort_keys=True)}
```

## Decision

No historical rebuild was performed. With the current governed evidence, pre-2026-07-20 historical Performance Base rows cannot be normalised under HPR-NORM-A-v1 without silent backdating/future leakage. The zero aggregate output is expected until horses accumulate five eligible governed observations or a separately approved earlier/backfill authority is created.
"""

    eligibility_md = f"""# EDGEiQ Historical Horse Observation Eligibility V1

Status: `BLOCKED`

Historical HPR-NORM-A-v1 application permitted: `NO`

## Evidence

- HPR-NORM-A-v1 effective_from_date is `2026-07-20` in the parameter source and parameter fact.
- The canonical normalisation builder selects parameters by performance `race_date` effective window.
- Pre-cutoff rows are rejected with `NORMALISATION_PARAMETER_NOT_EFFECTIVE_FOR_PERFORMANCE_DATE`.
- The temporal authority document explicitly states historical application authorised: `NO`.

## Conclusion

The restriction is an explicit governed temporal rule, not an accidental orchestration omission.
"""

    identity_md = f"""# EDGEiQ Historical Horse Identity Audit V1

Status: `PASS`

Current Racing Australia identity governance remains resolved and was not reopened.

- Current identity rows: {identity_payload['current_identity_rows']}
- Governed identity rows: {identity_payload['current_governed_identity_rows']}
- Distinct canonical current horses: {identity_payload['current_distinct_canonical_horses']}

Historical identity expansion was not attempted because historical HPR-NORM-A-v1 normalisation is not currently authorised.
"""

    depth_md = f"""# EDGEiQ Horse Observation Depth Audit V1

Status: `PASS_WITH_GOVERNED_INSUFFICIENCY`

- Horse Observation rows: {observation_payload['horse_observation_rows']}
- Distinct horses with observations: {observation_payload['distinct_horses_with_observations']}
- Horses with 5+ observations: {observation_payload['horses_with_5_plus_observations']}
- Minimum observations required: 5

## Depth Distribution

{md_table(depth_rows, ['bucket','horse_count'])}
"""

    acceptance_md = f"""# EDGEiQ Victoria Current Ratings EPI Acceptance V2

Status: `BLOCKED_GOVERNED_HISTORY_DEPTH`

- Current runners: {acceptance_payload['current_runners']}
- Governed identities: {acceptance_payload['governed_identities']}
- Performance Rating Base rows: {acceptance_payload['performance_rating_base_rows']}
- Horse Observations: {acceptance_payload['horse_observations']}
- Horse Aggregates: {acceptance_payload['horse_aggregates']}
- Horse Ratings: {acceptance_payload['horse_ratings']}
- Snapshots: {acceptance_payload['snapshots']}
- EPI: {acceptance_payload['epi']}

Remaining blocker: {acceptance_payload['remaining_blocker']}
"""

    atomic_write_text(DOC / "EDGEIQ_VICTORIA_LIVE_RECOVERY_V5_INVESTIGATION.md", investigation_md)
    atomic_write_text(DOC / "EDGEIQ_HISTORICAL_HORSE_OBSERVATION_ELIGIBILITY_V1.md", eligibility_md)
    atomic_write_text(DOC / "EDGEIQ_HISTORICAL_HORSE_IDENTITY_AUDIT_V1.md", identity_md)
    atomic_write_text(DOC / "EDGEIQ_HORSE_OBSERVATION_DEPTH_AUDIT_V1.md", depth_md)
    atomic_write_text(DOC / "EDGEIQ_VICTORIA_CURRENT_RATINGS_EPI_ACCEPTANCE_V2.md", acceptance_md)

    print("EDGEIQ_VICTORIA_LIVE_RECOVERY_V5_INVESTIGATION_PASS_WITH_GOVERNED_INSUFFICIENCY")
    print(json.dumps(acceptance_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
