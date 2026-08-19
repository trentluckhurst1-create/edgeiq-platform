from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TARGET = ROOT / "scripts" / "build_edgeiq_three_day_product_catalog_v1.py"

if not TARGET.exists():
    raise SystemExit(f"TARGET_MISSING={TARGET}")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
checkpoint_dir = (
    ROOT
    / "checkpoints"
    / f"edgeiq_before_three_day_catalog_runner_merge_v1_{stamp}"
)
checkpoint_dir.mkdir(parents=True, exist_ok=True)

checkpoint_file = checkpoint_dir / TARGET.name
shutil.copy2(TARGET, checkpoint_file)

text = TARGET.read_text(encoding="utf-8-sig")

anchor = '''def normalise_race(
    row: dict[str, Any],
    meeting_name: str,
    meeting_date: str,
) -> dict[str, Any]:
'''

helpers = r'''def value_present(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {
            "none",
            "null",
            "n/a",
            "na",
            "-",
        }

    if isinstance(value, (list, tuple, dict)):
        return bool(value)

    return True


def runner_identity(runner: dict[str, Any]) -> str:
    official = runner.get("official") or {}
    source = runner.get("source") or {}

    number = (
        official.get("no")
        or official.get("number")
        or first(source, RUNNER_NUMBER_KEYS)
        or ""
    )

    name = (
        clean_text(official.get("runner"))
        or runner_name_from(source)
        or ""
    )

    normalised_name = re.sub(
        r"[^A-Z0-9]+",
        "",
        name.upper(),
    )

    return f"{number}|{normalised_name}"


def merge_missing_values(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(primary)

    for key, value in supplemental.items():
        current = merged.get(key)

        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = merge_missing_values(current, value)
            continue

        if not value_present(current) and value_present(value):
            merged[key] = value

    return merged


def merge_runner_records(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(primary)

    primary_official = primary.get("official") or {}
    supplemental_official = supplemental.get("official") or {}

    merged["official"] = merge_missing_values(
        primary_official,
        supplemental_official,
    )

    primary_source = primary.get("source") or {}
    supplemental_source = supplemental.get("source") or {}

    merged["source"] = merge_missing_values(
        primary_source,
        supplemental_source,
    )

    for collection_key in ("historicalRuns", "evidenceRuns"):
        primary_rows = primary.get(collection_key)
        supplemental_rows = supplemental.get(collection_key)

        if not primary_rows and supplemental_rows:
            merged[collection_key] = supplemental_rows

    return merged


def merge_race_records(
    primary: dict[str, Any],
    supplemental: dict[str, Any],
) -> dict[str, Any]:
    merged = merge_missing_values(primary, supplemental)

    primary_runners = [
        runner
        for runner in primary.get("runners", [])
        if isinstance(runner, dict)
    ]
    supplemental_runners = [
        runner
        for runner in supplemental.get("runners", [])
        if isinstance(runner, dict)
    ]

    merged_runners = list(primary_runners)
    runner_indexes = {
        runner_identity(runner): index
        for index, runner in enumerate(merged_runners)
        if runner_identity(runner)
    }

    for supplemental_runner in supplemental_runners:
        identity = runner_identity(supplemental_runner)

        if identity and identity in runner_indexes:
            index = runner_indexes[identity]
            merged_runners[index] = merge_runner_records(
                merged_runners[index],
                supplemental_runner,
            )
            continue

        runner_indexes[identity] = len(merged_runners)
        merged_runners.append(supplemental_runner)

    merged["runners"] = merged_runners
    return merged


'''

if "def merge_race_records(" not in text:
    if anchor not in text:
        raise SystemExit("NORMALISE_RACE_ANCHOR_NOT_FOUND")

    text = text.replace(
        anchor,
        helpers + anchor,
        1,
    )

old_collision_block = '''            if existing_index is None:
                meeting["races"].append(candidate)
            elif (
                len(candidate["runners"])
                > len(meeting["races"][existing_index]["runners"])
            ):
                meeting["races"][existing_index] = candidate
'''

new_collision_block = '''            if existing_index is None:
                meeting["races"].append(candidate)
            else:
                meeting["races"][existing_index] = merge_race_records(
                    meeting["races"][existing_index],
                    candidate,
                )
'''

if old_collision_block not in text:
    if new_collision_block not in text:
        raise SystemExit("RACE_COLLISION_BLOCK_NOT_FOUND")
else:
    text = text.replace(
        old_collision_block,
        new_collision_block,
        1,
    )

TARGET.write_text(text, encoding="utf-8")

print("EDGEIQ_THREE_DAY_CATALOG_RUNNER_MERGE_PATCH_V1_APPLIED")
print(f"TARGET={TARGET}")
print(f"CHECKPOINT={checkpoint_file}")
