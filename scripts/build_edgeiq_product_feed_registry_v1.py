from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFINED = ROOT / "docs/platform-registry-v1/canonical-scope-refiner-v1/EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
CLAIMS = ROOT / "docs/platform-registry-v1/builder-registry-v1-1/EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1_1.csv"
EDGES = ROOT / "docs/platform-registry-v1/builder-dependency-graph-v1-1/EDGEIQ_CANONICAL_BUILDER_GRAPH_EDGES_V1_1.csv"
OUT = ROOT / "docs/platform-registry-v1/product-feed-registry-v1"

REGISTRY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_V1.csv"
DUPLICATES = OUT / "EDGEIQ_PRODUCT_FEED_DUPLICATE_OWNERSHIP_V1.csv"
UNOWNED = OUT / "EDGEIQ_PRODUCT_FEED_UNOWNED_PUBLIC_FILES_V1.csv"
OWNER_PROFILE = OUT / "EDGEIQ_PRODUCT_FEED_OWNER_PROFILE_V1.csv"
FORMAT_PROFILE = OUT / "EDGEIQ_PRODUCT_FEED_FORMAT_PROFILE_V1.csv"
SUMMARY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_SUMMARY_V1.json"
REPORT = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_REPORT_V1.md"

FEED_EXTENSIONS = {".csv", ".json", ".parquet", ".geojson", ".sqlite", ".db"}
PUBLIC_PREFIXES = ("public/data/", "public/feeds/", "public/json/", "public/assets/data/")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def first(row: dict[str, str], *names: str) -> str:
    lowered = {str(k).strip().lower(): str(v or "").strip() for k, v in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value:
            return value
    return ""


def norm(value: str) -> str:
    value = value.strip().strip("'\"").replace("\\", "/")
    root = ROOT.as_posix().rstrip("/") + "/"
    if value.lower().startswith(root.lower()):
        value = value[len(root):]
    while value.startswith("./"):
        value = value[2:]
    return value


def is_feed(path: str) -> bool:
    lower = path.lower()
    return lower.startswith(PUBLIC_PREFIXES) and Path(lower).suffix in FEED_EXTENSIONS


def candidate_output_paths(row: dict[str, str]) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for key, raw in row.items():
        value = norm(str(raw or ""))
        if not value or not is_feed(value):
            continue
        key_lower = str(key).lower()
        score = 0
        if any(token in key_lower for token in ("output", "claim", "artifact", "feed", "path")):
            score += 10
        if any(token in key_lower for token in ("input", "dependency", "source")):
            score -= 5
        candidates.append((score, value))
    if not candidates:
        return []
    best = max(score for score, _ in candidates)
    return sorted({path for score, path in candidates if score == best})


def resolve_builder(row: dict[str, str], canonical_ids: set[str], path_to_id: dict[str, str]) -> str:
    preferred = (
        "builder_id", "producer_builder_id", "source_builder_id",
        "builder", "script", "script_path", "builder_path", "relative_path",
    )
    for name in preferred:
        value = first(row, name)
        if value in canonical_ids:
            return value
        n = norm(value).lower()
        if n in path_to_id:
            return path_to_id[n]

    for raw in row.values():
        value = str(raw or "").strip()
        if value in canonical_ids:
            return value
        n = norm(value).lower()
        if n in path_to_id:
            return path_to_id[n]
    return ""


def feed_category(path: str) -> str:
    name = Path(path).name.lower()
    rules = [
        ("MEETINGS", ("meeting", "three_day", "calendar")),
        ("RACE_FIELDS", ("field", "runner", "declaration")),
        ("FORM", ("form", "recent_run", "career")),
        ("PERFORMANCE", ("performance", "epi", "eri", "sectional", "standard_time")),
        ("MARKET", ("market", "price", "odds", "fluctuation")),
        ("WEATHER", ("weather", "track_condition", "observation")),
        ("RESULTS", ("result", "steward")),
        ("MAP", ("map", "tempo", "race_shape", "early_speed", "late_speed")),
        ("IDENTITY", ("identity", "horse_master", "jockey", "trainer")),
        ("GOVERNANCE", ("audit", "registry", "summary", "validation")),
    ]
    for category, tokens in rules:
        if any(token in name for token in tokens):
            return category
    return "OTHER"


def lifecycle_status(path: str, exists: bool, owner_count: int) -> str:
    lower = path.lower()
    if any(token in lower for token in ("legacy", "archive", "historical", "obsolete")):
        return "HISTORICAL"
    if owner_count == 0:
        return "UNOWNED"
    if not exists:
        return "CLAIMED_NOT_MATERIALISED"
    return "ACTIVE"


def main() -> int:
    refined_rows = read_csv(REFINED)
    claim_rows = read_csv(CLAIMS)
    edge_rows = read_csv(EDGES)

    canonical_rows = [
        row for row in refined_rows
        if first(row, "classification", "builder_classification").upper() == "CANONICAL"
    ]
    canonical_ids = {first(row, "builder_id", "id") for row in canonical_rows}
    canonical_ids.discard("")
    registry_by_id = {
        first(row, "builder_id", "id"): row
        for row in canonical_rows
        if first(row, "builder_id", "id")
    }

    path_to_id: dict[str, str] = {}
    for builder_id, row in registry_by_id.items():
        script_path = first(row, "relative_path", "builder_path", "path", "script_path")
        if script_path:
            path_to_id[norm(script_path).lower()] = builder_id

    owners_by_feed: dict[str, set[str]] = defaultdict(set)
    feeds_by_owner: dict[str, set[str]] = defaultdict(set)

    for row in claim_rows:
        owner = resolve_builder(row, canonical_ids, path_to_id)
        if not owner:
            continue
        for path in candidate_output_paths(row):
            owners_by_feed[path.lower()].add(owner)
            feeds_by_owner[owner].add(path)

    consumers_by_owner: dict[str, set[str]] = defaultdict(set)
    for row in edge_rows:
        producer = first(row, "producer_builder_id")
        consumer = first(row, "consumer_builder_id")
        if producer and consumer:
            consumers_by_owner[producer].add(consumer)

    public_files: set[str] = set()
    for prefix in PUBLIC_PREFIXES:
        directory = ROOT / prefix
        if directory.exists():
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix.lower() in FEED_EXTENSIONS:
                    public_files.add(path.relative_to(ROOT).as_posix())

    all_feed_paths = sorted(set(public_files) | {p for p in owners_by_feed})

    registry_rows: list[dict[str, object]] = []
    duplicate_rows: list[dict[str, object]] = []
    unowned_rows: list[dict[str, object]] = []

    for feed_key in all_feed_paths:
        actual_path = next((p for p in public_files if p.lower() == feed_key.lower()), feed_key)
        owners = sorted(owners_by_feed.get(feed_key.lower(), set()))
        file_path = ROOT / actual_path
        exists = file_path.exists()
        size = file_path.stat().st_size if exists else 0
        modified = (
            datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).isoformat()
            if exists else ""
        )
        owner_paths = [
            first(registry_by_id[owner], "relative_path", "builder_path", "path", "script_path")
            for owner in owners
            if owner in registry_by_id
        ]
        downstream = sorted({
            consumer
            for owner in owners
            for consumer in consumers_by_owner.get(owner, set())
        })
        lifecycle = lifecycle_status(actual_path, exists, len(owners))

        record = {
            "feed_id": f"FEED_{len(registry_rows) + 1:05d}",
            "feed_path": actual_path,
            "feed_name": Path(actual_path).name,
            "feed_format": Path(actual_path).suffix.lower().lstrip("."),
            "feed_category": feed_category(actual_path),
            "lifecycle_status": lifecycle,
            "file_exists": str(exists).lower(),
            "file_size_bytes": size,
            "modified_utc": modified,
            "owner_count": len(owners),
            "owner_builder_ids": " | ".join(owners),
            "owner_builder_paths": " | ".join(owner_paths),
            "downstream_builder_count": len(downstream),
            "downstream_builder_ids": " | ".join(downstream),
            "duplicate_ownership": str(len(owners) > 1).lower(),
        }
        registry_rows.append(record)

        if len(owners) > 1:
            duplicate_rows.append({
                "feed_path": actual_path,
                "owner_count": len(owners),
                "owner_builder_ids": " | ".join(owners),
                "owner_builder_paths": " | ".join(owner_paths),
            })

        if exists and not owners:
            unowned_rows.append({
                "feed_path": actual_path,
                "feed_name": Path(actual_path).name,
                "feed_format": Path(actual_path).suffix.lower().lstrip("."),
                "feed_category": feed_category(actual_path),
                "file_size_bytes": size,
                "modified_utc": modified,
                "governance_action": "ASSIGN_OWNER_OR_EXCLUDE",
            })

    owner_profile_rows = []
    for owner in sorted(feeds_by_owner):
        row = registry_by_id.get(owner, {})
        owned = sorted(feeds_by_owner[owner])
        owner_profile_rows.append({
            "owner_builder_id": owner,
            "owner_builder_path": first(row, "relative_path", "builder_path", "path", "script_path"),
            "claimed_public_feed_count": len(owned),
            "materialised_public_feed_count": sum((ROOT / p).exists() for p in owned),
            "downstream_builder_count": len(consumers_by_owner.get(owner, set())),
            "feed_paths": " | ".join(owned),
        })

    format_counts: dict[str, int] = defaultdict(int)
    category_counts: dict[str, int] = defaultdict(int)
    lifecycle_counts: dict[str, int] = defaultdict(int)
    for row in registry_rows:
        format_counts[str(row["feed_format"])] += 1
        category_counts[str(row["feed_category"])] += 1
        lifecycle_counts[str(row["lifecycle_status"])] += 1

    format_profile_rows = [
        {"feed_format": key, "feed_count": value}
        for key, value in sorted(format_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    fields = [
        "feed_id", "feed_path", "feed_name", "feed_format", "feed_category",
        "lifecycle_status", "file_exists", "file_size_bytes", "modified_utc",
        "owner_count", "owner_builder_ids", "owner_builder_paths",
        "downstream_builder_count", "downstream_builder_ids", "duplicate_ownership",
    ]
    write_csv(REGISTRY, registry_rows, fields)
    write_csv(DUPLICATES, duplicate_rows, [
        "feed_path", "owner_count", "owner_builder_ids", "owner_builder_paths",
    ])
    write_csv(UNOWNED, unowned_rows, [
        "feed_path", "feed_name", "feed_format", "feed_category",
        "file_size_bytes", "modified_utc", "governance_action",
    ])
    write_csv(OWNER_PROFILE, owner_profile_rows, [
        "owner_builder_id", "owner_builder_path", "claimed_public_feed_count",
        "materialised_public_feed_count", "downstream_builder_count", "feed_paths",
    ])
    write_csv(FORMAT_PROFILE, format_profile_rows, ["feed_format", "feed_count"])

    feed_count = len(registry_rows)
    owned_count = sum(1 for row in registry_rows if int(row["owner_count"]) > 0)
    materialised_count = sum(1 for row in registry_rows if row["file_exists"] == "true")
    verdict = "PASS" if feed_count > 0 and owned_count > 0 else "FAIL_NO_GOVERNED_FEEDS"

    summary = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "canonical_builder_count": len(canonical_ids),
        "product_feed_count": feed_count,
        "owned_feed_count": owned_count,
        "unowned_materialised_feed_count": len(unowned_rows),
        "duplicate_ownership_feed_count": len(duplicate_rows),
        "materialised_feed_count": materialised_count,
        "claimed_not_materialised_feed_count": sum(
            1 for row in registry_rows if row["lifecycle_status"] == "CLAIMED_NOT_MATERIALISED"
        ),
        "feed_owner_builder_count": len(owner_profile_rows),
        "ownership_coverage_percentage": round((owned_count / feed_count) * 100.0, 4) if feed_count else 0.0,
        "materialisation_coverage_percentage": round(
            (materialised_count / feed_count) * 100.0, 4
        ) if feed_count else 0.0,
        "format_counts": dict(sorted(format_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# EDGEIQ Product Feed Registry V1",
        "",
        "## Executive Summary",
        "",
        f"- Verdict: **{verdict}**",
        f"- Product feeds registered: **{feed_count}**",
        f"- Feeds with canonical owners: **{owned_count}**",
        f"- Materialised feeds: **{materialised_count}**",
        f"- Unowned materialised feeds: **{len(unowned_rows)}**",
        f"- Duplicate ownership claims: **{len(duplicate_rows)}**",
        f"- Ownership coverage: **{summary['ownership_coverage_percentage']}%**",
        "",
        "## Governance Contract",
        "",
        "A product feed is a supported data artefact under a public product-data path "
        "with a recognised structured-data extension. Ownership is assigned only from "
        "canonical builder output claims.",
        "",
        "## Feed Categories",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for name, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {name} | {count} |")

    lines.extend([
        "",
        "## Governance Exceptions",
        "",
        "- Unowned materialised feeds require an owner assignment or governed exclusion.",
        "- Duplicate ownership requires a single authoritative owner or explicit shared-ownership contract.",
        "- Claimed but unmaterialised feeds require lifecycle review.",
        "",
        "## Acceptance",
        "",
        "The registry is read-only and does not alter feed files or builder source.",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print("EDGEIQ PRODUCT FEED REGISTRY V1")
    print(f"VERDICT={verdict}")
    print(f"PRODUCT_FEEDS={feed_count}")
    print(f"OWNED_FEEDS={owned_count}")
    print(f"UNOWNED_MATERIALISED_FEEDS={len(unowned_rows)}")
    print(f"DUPLICATE_OWNERSHIP_FEEDS={len(duplicate_rows)}")
    print(f"OWNERSHIP_COVERAGE_PERCENT={summary['ownership_coverage_percentage']}")
    print(f"OUTPUT_ROOT={OUT}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
