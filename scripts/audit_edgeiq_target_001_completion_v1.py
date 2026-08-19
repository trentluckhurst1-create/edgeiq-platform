from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
RESTART = ROOT / "docs" / "performance-intelligence" / "restart-v1"

RACE_ENTRY_PATH = DATA / "edgeiq_race_entry_fact_v1.csv"
RATING_PATH = DATA / "edgeiq_horse_performance_rating_fact_v1.csv"
SNAPSHOT_PATH = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv"
SNAPSHOT_AUDIT_PATH = DATA / "edgeiq_race_entry_horse_performance_snapshot_fact_v1_audit.json"

AUDIT_JSON = RESTART / "edgeiq_target_001_completion_audit_v1.json"
AUDIT_CSV = RESTART / "edgeiq_target_001_completion_audit_v1.csv"
AUDIT_MD = RESTART / "EDGEIQ_TARGET_001_COMPLETION_AUDIT_V1.md"


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(raw: str) -> date | None:
    raw = text(raw)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def main() -> None:
    RESTART.mkdir(parents=True, exist_ok=True)
    entries = read_csv(RACE_ENTRY_PATH)
    ratings = read_csv(RATING_PATH)
    snapshots = read_csv(SNAPSHOT_PATH)
    snapshot_audit = json.loads(SNAPSHOT_AUDIT_PATH.read_text(encoding="utf-8"))

    ratings_by_horse: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ratings:
        ratings_by_horse[text(row.get("canonical_horse_id"))].append(row)

    active_entries = [
        row
        for row in entries
        if text(row.get("declaration_status")) == "ACTIVE_ENTRY"
        and text(row.get("scratching_status")) != "SCRATCHED"
    ]

    active_with_any_rating = 0
    active_with_prior_rating = 0
    active_with_no_prior_rating = 0
    rejection_reasons = Counter()

    for row in entries:
        declared = (
            text(row.get("declaration_status")) == "ACTIVE_ENTRY"
            and text(row.get("scratching_status")) != "SCRATCHED"
        )
        if not declared:
            rejection_reasons["NOT_DECLARED_OR_SCRATCHED"] += 1
            continue

        horse_id = text(row.get("canonical_runner_id"))
        race_date = parse_date(text(row.get("race_date")))
        horse_ratings = ratings_by_horse.get(horse_id, [])
        if not horse_ratings:
            rejection_reasons["NO_RATING_IDENTITY_OVERLAP"] += 1
            continue

        active_with_any_rating += 1
        prior = [
            rating
            for rating in horse_ratings
            if parse_date(text(rating.get("rating_as_of_date")))
            and race_date
            and parse_date(text(rating.get("rating_as_of_date"))) < race_date
        ]
        if prior:
            active_with_prior_rating += 1
        else:
            active_with_no_prior_rating += 1
            rejection_reasons["RATING_NOT_PRIOR_TO_RACE"] += 1

    snapshot_entry_ids = [text(row.get("race_entry_id")) for row in snapshots]
    duplicate_snapshot_ids = [
        key
        for key, count in Counter(
            text(row.get("race_entry_horse_performance_snapshot_id"))
            for row in snapshots
        ).items()
        if key and count > 1
    ]
    duplicate_race_entry_ids = [
        key
        for key, count in Counter(snapshot_entry_ids).items()
        if key and count > 1
    ]

    bad_temporal_rows = []
    adapter_source_rows = 0
    selected_names = []
    for row in snapshots:
        race_date = parse_date(text(row.get("race_date")))
        rating_date = parse_date(text(row.get("selected_rating_as_of_date")))
        if not rating_date or not race_date or not rating_date < race_date:
            bad_temporal_rows.append(text(row.get("race_entry_horse_performance_snapshot_id")))
        if (
            text(row.get("source_race_entry_builder_version"))
            == "edgeiq_race_entry_fact_v1.current_contract_adapter.1.0.0"
        ):
            adapter_source_rows += 1
        selected_names.append(text(row.get("canonical_horse_name")))

    checks = [
        {
            "check": "snapshot_file_populated",
            "status": "PASS" if len(snapshots) > 0 else "FAIL",
            "detail": len(snapshots),
        },
        {
            "check": "canonical_audit_passed",
            "status": "PASS" if snapshot_audit.get("status") == "PASS" else "FAIL",
            "detail": snapshot_audit.get("status"),
        },
        {
            "check": "temporal_boundary_clean",
            "status": "PASS" if not bad_temporal_rows else "FAIL",
            "detail": bad_temporal_rows,
        },
        {
            "check": "snapshot_ids_unique",
            "status": "PASS" if not duplicate_snapshot_ids else "FAIL",
            "detail": duplicate_snapshot_ids,
        },
        {
            "check": "one_snapshot_per_race_entry",
            "status": "PASS" if not duplicate_race_entry_ids else "FAIL",
            "detail": duplicate_race_entry_ids,
        },
        {
            "check": "current_contract_adapter_lineage_present",
            "status": "PASS" if adapter_source_rows == len(snapshots) else "FAIL",
            "detail": {
                "adapter_source_rows": adapter_source_rows,
                "snapshot_rows": len(snapshots),
            },
        },
    ]

    status = "PASS" if all(row["status"] == "PASS" for row in checks) else "FAIL"

    payload = {
        "audit": "EDGEIQ_TARGET_001_COMPLETION_AUDIT_V1",
        "audited_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "counts": {
            "race_entry_rows": len(entries),
            "declared_active_race_entries": len(active_entries),
            "horse_performance_rating_rows": len(ratings),
            "active_entries_with_any_rating_identity_overlap": active_with_any_rating,
            "active_entries_with_prior_rating": active_with_prior_rating,
            "active_entries_with_rating_but_no_prior_rating": active_with_no_prior_rating,
            "snapshot_rows": len(snapshots),
        },
        "rejection_reasons": dict(sorted(rejection_reasons.items())),
        "selected_snapshot_horses": selected_names,
        "checks": checks,
        "verdict": (
            "TARGET_001_RECOVERED_WITH_CURRENT_CONTRACT_ADAPTER"
            if status == "PASS"
            else "TARGET_001_REQUIRES_REVIEW"
        ),
    }

    AUDIT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        for row in checks:
            writer.writerow(
                {
                    "check": row["check"],
                    "status": row["status"],
                    "detail": json.dumps(row["detail"], sort_keys=True),
                }
            )

    AUDIT_MD.write_text(
        "\n".join(
            [
                "# EDGEiQ Target 001 Completion Audit V1",
                "",
                f"Status: `{status}`",
                "",
                "## Result",
                "",
                "Target 001 now emits governed point-in-time snapshots from the current canonical race-entry contract through an internal adapter. The output schema remains unchanged and the temporal rule remains `selected_rating_as_of_date < race_date`.",
                "",
                "## Counts",
                "",
                f"- Race-entry rows: {len(entries)}",
                f"- Declared active race-entry rows: {len(active_entries)}",
                f"- Horse performance rating rows: {len(ratings)}",
                f"- Active entries with any rating identity overlap: {active_with_any_rating}",
                f"- Active entries with prior rating: {active_with_prior_rating}",
                f"- Snapshot rows emitted: {len(snapshots)}",
                "",
                "## Rejection Reasons",
                "",
                *[
                    f"- {key}: {value}"
                    for key, value in sorted(rejection_reasons.items())
                ],
                "",
                "## Snapshot Horses",
                "",
                *[
                    f"- {name}"
                    for name in selected_names
                ],
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps({"status": status, "snapshot_rows": len(snapshots)}, indent=2))


if __name__ == "__main__":
    main()
