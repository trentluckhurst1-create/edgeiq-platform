from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESTART = ROOT / "docs" / "performance-intelligence" / "restart-v1"
BUILDER = ROOT / "scripts" / "build_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py"
AUDIT = ROOT / "scripts" / "audit_edgeiq_race_entry_horse_performance_snapshot_fact_v1.py"


DECISION_JSON = RESTART / "edgeiq_target_001_schema_authority_decision_v1.json"
DECISION_MD = RESTART / "EDGEIQ_TARGET_001_SCHEMA_AUTHORITY_DECISION_V1.md"
ALTERNATIVES_CSV = RESTART / "edgeiq_target_001_schema_authority_alternatives_v1.csv"


def replace_once(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f"Expected patch block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    return True


def write_decision_files() -> None:
    RESTART.mkdir(parents=True, exist_ok=True)

    decision = {
        "unit": "TARGET_001_SCHEMA_AUTHORITY_DECISION_V1",
        "target_output": "public/data/edgeiq_race_entry_horse_performance_snapshot_fact_v1.csv",
        "selected_authority": "public/data/edgeiq_race_entry_fact_v1.csv",
        "selected_contract": "CURRENT_CANONICAL_RACE_ENTRY_FACT_V1",
        "resolution": "IMPLEMENT_GOVERNED_CURRENT_CONTRACT_ADAPTER_IN_TARGET_001_PRODUCER",
        "reason": (
            "Unit 002D found no populated exact old-contract race-entry dataset. "
            "The current canonical race-entry fact is the only governed live/current entry authority."
        ),
        "output_schema_changed": False,
        "temporal_rule_changed": False,
        "temporal_rule": "selected_rating_as_of_date < race_date",
        "thresholds_weakened": False,
        "data_fabricated": False,
        "adapter_builder_version": "edgeiq_race_entry_fact_v1.current_contract_adapter.1.0.0",
        "field_mapping": {
            "race_entry_id": "deterministic RE1 hash from canonical_race_id, canonical_runner_id, source_record_id",
            "race_id": "canonical_race_id",
            "runner_id": "canonical_runner_id",
            "canonical_horse_id": "canonical_runner_id",
            "canonical_horse_name": "runner_name",
            "race_entry_status": "DECLARED_GOVERNED only for ACTIVE_ENTRY and not SCRATCHED",
            "race_entry_evidence_sha256": "source_hash",
            "builder_version": "edgeiq_race_entry_fact_v1.current_contract_adapter.1.0.0",
        },
        "classification_before_fix": "DIRECT_INPUT_SCHEMA_CONTRACT_MISMATCH",
    }
    DECISION_JSON.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    DECISION_MD.write_text(
        "\n".join(
            [
                "# EDGEiQ Target 001 Schema Authority Decision V1",
                "",
                "## Decision",
                "",
                "Use `public/data/edgeiq_race_entry_fact_v1.csv` as the authoritative race-entry input for Target 001 and adapt its current canonical contract inside the Target 001 producer.",
                "",
                "## Reason",
                "",
                "Unit 002D scanned the repository and found no populated dataset matching the old Target 001 race-entry input contract. The current canonical race-entry fact is populated and governed, but uses the successor live/current schema.",
                "",
                "## Guardrails",
                "",
                "- Target 001 output schema is unchanged.",
                "- No duplicate race-entry authority is created.",
                "- No thresholds are weakened.",
                "- No data is fabricated.",
                "- The point-in-time rule remains `selected_rating_as_of_date < race_date`.",
                "- Non-active or scratched entries are not emitted as declared governed snapshots.",
                "",
                "## Adapter Mapping",
                "",
                "- `race_id` comes from `canonical_race_id`.",
                "- `runner_id` and `canonical_horse_id` come from `canonical_runner_id`.",
                "- `canonical_horse_name` comes from `runner_name`.",
                "- `race_entry_evidence_sha256` comes from `source_hash`.",
                "- `race_entry_id` is deterministic from canonical race/runner/source identity.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = [
        {
            "alternative": "REPOINT_TO_OLD_CONTRACT_DATASET",
            "decision": "REJECTED",
            "reason": "Unit 002D found no populated exact old-contract race-entry dataset.",
        },
        {
            "alternative": "RESTORE_OLD_PRODUCER_INPUT_AUTHORITY",
            "decision": "REJECTED",
            "reason": "Would create duplicate authority and remain incompatible with current canonical race-entry facts.",
        },
        {
            "alternative": "LOWER_TEMPORAL_OR_EVIDENCE_RULES",
            "decision": "REJECTED",
            "reason": "Would weaken governance and risk fabricated or leaky performance snapshots.",
        },
        {
            "alternative": "GOVERNED_CURRENT_CONTRACT_ADAPTER",
            "decision": "SELECTED",
            "reason": "Preserves current canonical authority, output schema, and point-in-time rating rule.",
        },
    ]
    with ALTERNATIVES_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def patch_builder() -> bool:
    old = '''    race_entry_fields, race_entry_rows = read_csv(
        RACE_ENTRY_PATH
    )

    require_fields(
        RACE_ENTRY_PATH,
        race_entry_fields,
        [
            "race_entry_id",
            "race_id",
            "race_date",
            "runner_id",
            "canonical_horse_id",
            "canonical_horse_name",
            "race_entry_status",
            "race_entry_evidence_sha256",
            "builder_version",
        ],
    )
'''
    new = '''    race_entry_fields, raw_race_entry_rows = read_csv(
        RACE_ENTRY_PATH
    )

    legacy_race_entry_fields = [
        "race_entry_id",
        "race_id",
        "race_date",
        "runner_id",
        "canonical_horse_id",
        "canonical_horse_name",
        "race_entry_status",
        "race_entry_evidence_sha256",
        "builder_version",
    ]

    current_race_entry_fields = [
        "canonical_race_id",
        "canonical_runner_id",
        "race_date",
        "runner_name",
        "declaration_status",
        "scratching_status",
        "source_hash",
        "source_system",
        "source_record_id",
    ]

    if all(
        field in race_entry_fields
        for field in legacy_race_entry_fields
    ):
        race_entry_rows = raw_race_entry_rows
    elif all(
        field in race_entry_fields
        for field in current_race_entry_fields
    ):
        adapter_builder_version = (
            "edgeiq_race_entry_fact_v1.current_contract_adapter.1.0.0"
        )
        race_entry_rows = []
        for row in raw_race_entry_rows:
            canonical_race_id = text(row["canonical_race_id"])
            canonical_runner_id = text(row["canonical_runner_id"])
            source_record_id = text(row["source_record_id"])
            race_entry_id = (
                "RE1-"
                + sha256_payload(
                    [
                        adapter_builder_version,
                        canonical_race_id,
                        canonical_runner_id,
                        source_record_id,
                    ]
                )[:24].upper()
            )
            declared = (
                text(row["declaration_status"]) == "ACTIVE_ENTRY"
                and text(row["scratching_status"]) != "SCRATCHED"
            )
            race_entry_rows.append(
                {
                    "race_entry_id": race_entry_id,
                    "race_id": canonical_race_id,
                    "race_date": text(row["race_date"]),
                    "runner_id": canonical_runner_id,
                    "canonical_horse_id": canonical_runner_id,
                    "canonical_horse_name": text(row["runner_name"]),
                    "race_entry_status": (
                        "DECLARED_GOVERNED"
                        if declared
                        else "NOT_DECLARED_GOVERNED"
                    ),
                    "race_entry_evidence_sha256": text(row["source_hash"]),
                    "builder_version": adapter_builder_version,
                }
            )
    else:
        require_fields(
            RACE_ENTRY_PATH,
            race_entry_fields,
            legacy_race_entry_fields,
        )
'''
    return replace_once(BUILDER, old, new)


def patch_audit() -> bool:
    old = '''    current_population_expected = (
        len(rating_rows) == 0
        and len(fact_rows) == 0
    )

    check(
        "current_population_expected",
        current_population_expected,
        {
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "race_entry_rows": (
                len(race_entry_rows)
            ),
            "snapshot_rows": (
                len(fact_rows)
            ),
        },
    )
'''
    new = '''    declared_race_entry_count = sum(
        1
        for row in race_entry_rows
        if text(row.get("declaration_status", "")) == "ACTIVE_ENTRY"
        and text(row.get("scratching_status", "")) != "SCRATCHED"
    )

    snapshot_population_within_race_entry_bounds = (
        len(fact_rows) <= max(len(race_entry_rows), declared_race_entry_count)
    )

    check(
        "snapshot_population_within_race_entry_bounds",
        snapshot_population_within_race_entry_bounds,
        {
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "race_entry_rows": (
                len(race_entry_rows)
            ),
            "declared_race_entry_count": (
                declared_race_entry_count
            ),
            "snapshot_rows": (
                len(fact_rows)
            ),
        },
    )

    check(
        "snapshot_not_header_only_when_inputs_are_populated",
        not (
            len(rating_rows) > 0
            and declared_race_entry_count > 0
            and len(fact_rows) == 0
        ),
        {
            "horse_performance_rating_rows": (
                len(rating_rows)
            ),
            "declared_race_entry_count": (
                declared_race_entry_count
            ),
            "snapshot_rows": (
                len(fact_rows)
            ),
        },
    )
'''
    return replace_once(AUDIT, old, new)


def main() -> None:
    write_decision_files()
    changed = {
        "builder_patched": patch_builder(),
        "audit_patched": patch_audit(),
        "decision_files_written": True,
    }
    print(json.dumps(changed, indent=2))


if __name__ == "__main__":
    main()
