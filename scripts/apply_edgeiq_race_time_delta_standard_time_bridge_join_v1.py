from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_edgeiq_race_time_delta_versus_standard_v1.py"
AUDIT = ROOT / "scripts" / "audit_edgeiq_race_time_delta_versus_standard_v1.py"
RESTART = ROOT / "docs" / "performance-intelligence" / "restart-v1"
REPORT = RESTART / "edgeiq_race_time_delta_standard_time_bridge_join_v1.json"


def replace_once(path: Path, old: str, new: str) -> bool:
    body = path.read_text(encoding="utf-8")
    if new in body:
        return False
    if old not in body:
        raise RuntimeError(f"Patch block not found in {path}")
    path.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")
    return True


def patch_builder() -> bool:
    old = '''    standard_by_group: dict[str, dict[str, str]] = {}
    for row in standard_rows:
        group_id = text(row["benchmark_group_id"])

        if not group_id:
            fail("Blank benchmark_group_id in standard time fact.")

        if group_id in standard_by_group:
            fail(f"Duplicate standard for benchmark group: {group_id}")

        if text(row["standard_time_status"]) != "AVAILABLE":
            fail(f"Non-available row in Standard Time Fact: {group_id}")

        standard_by_group[group_id] = row
'''
    new = '''    standard_by_group: dict[str, dict[str, str]] = {}
    standard_by_track_distance: dict[tuple[str, str], dict[str, str]] = {}
    for row in standard_rows:
        group_id = text(row["benchmark_group_id"])

        if not group_id:
            fail("Blank benchmark_group_id in standard time fact.")

        if group_id in standard_by_group:
            fail(f"Duplicate standard for benchmark group: {group_id}")

        if text(row["standard_time_status"]) != "AVAILABLE":
            fail(f"Non-available row in Standard Time Fact: {group_id}")

        standard_by_group[group_id] = row
        track_distance_key = (
            text(row["track_name"]).upper(),
            text(row["official_distance_metres"]),
        )
        if track_distance_key in standard_by_track_distance:
            fail(
                "Duplicate Standard Time track-distance key: "
                f"{track_distance_key}"
            )
        standard_by_track_distance[track_distance_key] = row
'''
    changed = replace_once(BUILDER, old, new)

    old = '''        standard = standard_by_group.get(group_id)

        if standard is None:
            continue
'''
    new = '''        standard = standard_by_group.get(group_id)
        if standard is None:
            standard = standard_by_track_distance.get(
                (
                    text(observation["track_name"]).upper(),
                    text(observation["official_distance_metres"]),
                )
            )

        if standard is None:
            continue

        group_id = text(standard["benchmark_group_id"])
'''
    changed = replace_once(BUILDER, old, new) or changed
    return changed


def patch_audit() -> bool:
    old = '''    standard_by_group = {
        text(row["benchmark_group_id"]): row
        for row in standard_rows
    }

    expected_observation_ids = sorted(
        observation_id
        for observation_id, eligibility in eligibility_by_id.items()
        if (
            text(eligibility["benchmark_use_class"])
            == ELIGIBLE_CLASS
            and group_by_observation.get(observation_id)
            in standard_by_group
        )
    )
'''
    new = '''    standard_by_group = {
        text(row["benchmark_group_id"]): row
        for row in standard_rows
    }
    standard_by_track_distance = {
        (
            text(row["track_name"]).upper(),
            text(row["official_distance_metres"]),
        ): row
        for row in standard_rows
    }

    def standard_for_observation(
        observation_id: str,
    ) -> dict[str, str] | None:
        observation = observation_by_id.get(observation_id)
        if observation is None:
            return None
        group_id = group_by_observation.get(observation_id)
        standard = standard_by_group.get(group_id or "")
        if standard is not None:
            return standard
        return standard_by_track_distance.get(
            (
                text(observation["track_name"]).upper(),
                text(observation["official_distance_metres"]),
            )
        )

    expected_observation_ids = sorted(
        observation_id
        for observation_id, eligibility in eligibility_by_id.items()
        if (
            text(eligibility["benchmark_use_class"])
            == ELIGIBLE_CLASS
            and standard_for_observation(observation_id) is not None
        )
    )
'''
    changed = replace_once(AUDIT, old, new)

    old = '''        group_id = group_by_observation.get(observation_id)
        standard = standard_by_group.get(group_id or "")

        if standard is None:
            lineage_errors.append(
                f"{observation_id}: no canonical standard"
            )
            continue
'''
    new = '''        standard = standard_for_observation(observation_id)

        if standard is None:
            lineage_errors.append(
                f"{observation_id}: no canonical standard"
            )
            continue

        group_id = text(standard["benchmark_group_id"])
'''
    changed = replace_once(AUDIT, old, new) or changed

    old = '''        "current_population_expected",
        (
            len(observation_rows) == 39
            and len(standard_rows) == 0
            and len(delta_rows) == 0
        ),
        {
            "observation_rows": len(observation_rows),
            "standard_time_rows": len(standard_rows),
            "race_time_delta_rows": len(delta_rows),
        },
'''
    new = '''        "current_population_expected",
        len(delta_rows) == len(expected_observation_ids),
        {
            "observation_rows": len(observation_rows),
            "standard_time_rows": len(standard_rows),
            "expected_delta_rows": len(expected_observation_ids),
            "race_time_delta_rows": len(delta_rows),
        },
'''
    changed = replace_once(AUDIT, old, new) or changed
    return changed


def main() -> None:
    RESTART.mkdir(parents=True, exist_ok=True)
    changed = {
        "builder_patched": patch_builder(),
        "audit_patched": patch_audit(),
    }
    REPORT.write_text(json.dumps(changed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(changed, indent=2))


if __name__ == "__main__":
    main()
