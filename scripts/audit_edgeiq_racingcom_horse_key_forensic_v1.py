from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path.cwd()

DOCS = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "warehouse-v2"
)

JOIN_DIR = DOCS / "racingcom-deterministic-join-discovery-v1"

AUDIT_PATH = (
    JOIN_DIR
    / "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT.json"
)

JOIN_PATH = (
    JOIN_DIR
    / "edgeiq_racingcom_join_strategy_assessment_v1.csv"
)

PROFILE_PATH = (
    JOIN_DIR
    / "edgeiq_racingcom_column_profile_v1.csv"
)

OUTPUT_PATH = (
    JOIN_DIR
    / "EDGEIQ_RACINGCOM_HORSE_KEY_FORENSIC_V1.json"
)

PUBLIC_DATA = ROOT / "public" / "data"

TARGET_FILES = [
    PUBLIC_DATA / "racingcom_sectional_warehouse_v2.csv",
    PUBLIC_DATA
    / "racingcom_rendered_speed_data_batches"
    / "batch_11250_splits.csv",
    PUBLIC_DATA
    / "racingcom_rendered_speed_data_batches"
    / "batch_11250_normalised.csv",
]

CANONICAL_PATTERNS = [
    "edgeiq_racingcom_canonical_runner_",
    "edgeiq_racingcom_runner_sectional_fact",
    "edgeiq_racingcom_runner_speed_fact",
    "edgeiq_racingcom_runner_split_fact",
]


def clean(value):
    return "" if value is None else str(value).strip()


def norm_name(value):
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())


def find_column(fieldnames, candidates):
    lookup = {
        re.sub(r"[^a-z0-9]+", "_", clean(field).lower()).strip("_"): field
        for field in fieldnames or []
    }

    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]

    return None


def read_csv(path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            handle = path.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            )
            reader = csv.DictReader(handle)
            return handle, reader
        except UnicodeDecodeError:
            try:
                handle.close()
            except Exception:
                pass

    handle = path.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    )
    return handle, csv.DictReader(handle)


if not AUDIT_PATH.exists():
    raise FileNotFoundError(AUDIT_PATH)

if not JOIN_PATH.exists():
    raise FileNotFoundError(JOIN_PATH)

audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

print("")
print("AUDIT STATUS")
print("------------")
print(audit.get("status"))
print("")

print("PROVEN JOIN RESULTS")
print("-------------------")

join_results = []

with JOIN_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as handle:
    for row in csv.DictReader(handle):
        unique_matches = int(clean(row.get("unique_matches")) or 0)

        if unique_matches <= 0:
            continue

        result = {
            "source_path": clean(row.get("source_path")),
            "join_strategy": clean(row.get("join_strategy")),
            "rows_scanned": int(
                clean(row.get("rows_scanned")) or 0
            ),
            "rows_with_complete_key": int(
                clean(row.get("rows_with_complete_key")) or 0
            ),
            "unique_matches": unique_matches,
            "ambiguous_matches": int(
                clean(row.get("ambiguous_matches")) or 0
            ),
            "no_matches": int(
                clean(row.get("no_matches")) or 0
            ),
            "unique_match_percentage": clean(
                row.get("unique_match_percentage")
            ),
            "implementation_decision": clean(
                row.get("implementation_decision")
            ),
        }

        join_results.append(result)
        print(json.dumps(result, ensure_ascii=False))

print("")

source_profiles = []

print("HORSE_KEY SOURCE PROFILES")
print("-------------------------")

for path in TARGET_FILES:
    if not path.exists():
        print(f"MISSING: {path}")
        continue

    handle, reader = read_csv(path)

    with handle:
        fields = reader.fieldnames or []

        horse_key_col = find_column(
            fields,
            {
                "horse_key",
                "horsekey",
                "source_horse_id",
                "horse_id",
            },
        )

        horse_name_col = find_column(
            fields,
            {
                "horse_name",
                "horsename",
                "horse",
                "runner_name",
                "runner",
            },
        )

        source_url_col = find_column(
            fields,
            {
                "source_url",
                "horse_url",
                "runner_url",
                "url",
            },
        )

        total_rows = 0
        key_rows = 0
        unique_keys = set()
        key_to_names = defaultdict(set)
        key_examples = []
        url_examples = []
        numeric_url_ids = set()

        for row in reader:
            total_rows += 1

            key = clean(row.get(horse_key_col)) if horse_key_col else ""
            name = clean(row.get(horse_name_col)) if horse_name_col else ""
            url = clean(row.get(source_url_col)) if source_url_col else ""

            if key:
                key_rows += 1
                unique_keys.add(key)

                if name:
                    key_to_names[key].add(norm_name(name))

                if len(key_examples) < 10:
                    example = {
                        "horse_key": key,
                        "horse_name": name,
                        "source_url": url,
                    }

                    if example not in key_examples:
                        key_examples.append(example)

            if url and len(url_examples) < 10:
                if url not in url_examples:
                    url_examples.append(url)

            if url:
                for token in re.findall(r"(?<!\d)\d{4,}(?!\d)", url):
                    numeric_url_ids.add(token)

        collision_keys = {
            key: sorted(names)
            for key, names in key_to_names.items()
            if len(names) > 1
        }

        profile = {
            "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "columns": fields,
            "horse_key_column": horse_key_col,
            "horse_name_column": horse_name_col,
            "source_url_column": source_url_col,
            "total_rows": total_rows,
            "rows_with_horse_key": key_rows,
            "unique_horse_keys": len(unique_keys),
            "horse_key_name_collision_count": len(collision_keys),
            "horse_key_examples": key_examples,
            "source_url_examples": url_examples,
            "unique_long_numeric_url_tokens": len(numeric_url_ids),
            "collision_examples": [
                {
                    "horse_key": key,
                    "normalised_names": names,
                }
                for key, names in list(collision_keys.items())[:20]
            ],
        }

        source_profiles.append(profile)

        print(json.dumps(
            {
                "source_path": profile["source_path"],
                "horse_key_column": horse_key_col,
                "horse_name_column": horse_name_col,
                "source_url_column": source_url_col,
                "total_rows": total_rows,
                "rows_with_horse_key": key_rows,
                "unique_horse_keys": len(unique_keys),
                "horse_key_name_collision_count": len(collision_keys),
                "horse_key_examples": key_examples[:5],
                "source_url_examples": url_examples[:5],
            },
            indent=2,
            ensure_ascii=False,
        ))

print("")

canonical_files = sorted({
    path
    for path in PUBLIC_DATA.glob("*.csv")
    if any(pattern in path.name.lower() for pattern in CANONICAL_PATTERNS)
})

canonical_profiles = []
canonical_key_values = set()

print("CANONICAL FACT HORSE-KEY AVAILABILITY")
print("-------------------------------------")

for path in canonical_files:
    handle, reader = read_csv(path)

    with handle:
        fields = reader.fieldnames or []

        horse_key_col = find_column(
            fields,
            {
                "horse_key",
                "horsekey",
                "source_horse_id",
                "horse_id",
            },
        )

        runner_id_col = find_column(
            fields,
            {
                "runner_id",
                "runnerid",
            },
        )

        total_rows = 0
        key_rows = 0
        runner_rows = 0
        unique_keys = set()
        examples = []

        for row in reader:
            total_rows += 1

            key = clean(row.get(horse_key_col)) if horse_key_col else ""
            runner_id = (
                clean(row.get(runner_id_col))
                if runner_id_col
                else ""
            )

            if key:
                key_rows += 1
                unique_keys.add(key)
                canonical_key_values.add(key)

            if runner_id:
                runner_rows += 1

            if len(examples) < 5 and (key or runner_id):
                examples.append({
                    "horse_key": key,
                    "runner_id": runner_id,
                })

        profile = {
            "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "horse_key_column": horse_key_col,
            "runner_id_column": runner_id_col,
            "total_rows": total_rows,
            "rows_with_horse_key": key_rows,
            "unique_horse_keys": len(unique_keys),
            "rows_with_runner_id": runner_rows,
            "examples": examples,
        }

        canonical_profiles.append(profile)

        print(json.dumps(profile, ensure_ascii=False))

raw_key_values = set()

for profile in source_profiles:
    path = ROOT / profile["source_path"]

    if not path.exists() or not profile["horse_key_column"]:
        continue

    handle, reader = read_csv(path)

    with handle:
        for row in reader:
            key = clean(row.get(profile["horse_key_column"]))

            if key:
                raw_key_values.add(key)

overlap = raw_key_values.intersection(canonical_key_values)

checks = {
    "join_discovery_audit_passed": (
        audit.get("status")
        == "EDGEIQ_RACINGCOM_DETERMINISTIC_JOIN_DISCOVERY_V1_AUDIT_PASS"
    ),
    "target_files_found": bool(source_profiles),
    "horse_key_found_in_raw_sources": any(
        profile["horse_key_column"]
        for profile in source_profiles
    ),
    "raw_horse_keys_observed": bool(raw_key_values),
    "canonical_files_profiled": bool(canonical_profiles),
}

status = (
    "EDGEIQ_RACINGCOM_HORSE_KEY_FORENSIC_V1_AUDIT_PASS"
    if all(checks.values())
    else "EDGEIQ_RACINGCOM_HORSE_KEY_FORENSIC_V1_AUDIT_FAIL"
)

result = {
    "status": status,
    "generated_at_utc": (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    ),
    "join_discovery_status": audit.get("status"),
    "proven_join_results": join_results,
    "raw_source_profiles": source_profiles,
    "canonical_fact_profiles": canonical_profiles,
    "raw_unique_horse_keys": len(raw_key_values),
    "canonical_unique_horse_keys": len(canonical_key_values),
    "raw_to_canonical_horse_key_overlap": len(overlap),
    "raw_to_canonical_overlap_examples": sorted(overlap)[:50],
    "checks": checks,
    "architectural_conclusion": (
        "Treat horse_key as the primary Racing.com source-horse identity "
        "candidate. Its semantic stability and mapping to canonical horse "
        "identity must be proven before aliases or warehouse rows are changed."
    ),
}

OUTPUT_PATH.write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("")
print("FINAL HORSE-KEY FORENSIC RESULT")
print("-------------------------------")
print(json.dumps({
    "status": status,
    "raw_unique_horse_keys": len(raw_key_values),
    "canonical_unique_horse_keys": len(canonical_key_values),
    "raw_to_canonical_horse_key_overlap": len(overlap),
    "checks": checks,
}, indent=2))

print("")
print(f"Written: {OUTPUT_PATH}")
