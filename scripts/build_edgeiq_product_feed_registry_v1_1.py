from __future__ import annotations

import ast
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFINED = ROOT / "docs/platform-registry-v1/canonical-scope-refiner-v1/EDGEIQ_CANONICAL_BUILDER_REGISTRY_REFINED_V1.csv"
CLAIMS = ROOT / "docs/platform-registry-v1/builder-registry-v1-1/EDGEIQ_CANONICAL_BUILDER_OUTPUT_CLAIMS_V1_1.csv"
OUT = ROOT / "docs/platform-registry-v1/product-feed-registry-v1-1"

REGISTRY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_V1_1.csv"
OWNERSHIP_EVIDENCE = OUT / "EDGEIQ_PRODUCT_FEED_OWNERSHIP_EVIDENCE_V1_1.csv"
AMBIGUOUS = OUT / "EDGEIQ_PRODUCT_FEED_AMBIGUOUS_OWNERSHIP_V1_1.csv"
UNOWNED = OUT / "EDGEIQ_PRODUCT_FEED_UNOWNED_PUBLIC_FILES_V1_1.csv"
SUMMARY = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_SUMMARY_V1_1.json"
REPORT = OUT / "EDGEIQ_PRODUCT_FEED_REGISTRY_REPORT_V1_1.md"
SCHEMA = OUT / "EDGEIQ_PRODUCT_FEED_SOURCE_SCHEMA_PROFILE_V1_1.json"

FEED_EXTENSIONS = {".csv", ".json", ".parquet", ".geojson", ".sqlite", ".db"}
PUBLIC_DIR = ROOT / "public" / "data"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
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
    value = str(value or "").strip().strip("'\"").replace("\\", "/")
    root = ROOT.as_posix().rstrip("/") + "/"
    if value.lower().startswith(root.lower()):
        value = value[len(root):]
    while value.startswith("./"):
        value = value[2:]
    return value.lower()


def is_feed_path(value: str) -> bool:
    return Path(value.lower()).suffix in FEED_EXTENSIONS


def resolve_builder(row: dict[str, str], canonical_ids: set[str], path_to_id: dict[str, str]) -> str:
    for name in (
        "builder_id", "producer_builder_id", "source_builder_id",
        "builder", "script", "script_path", "builder_path", "relative_path",
    ):
        value = first(row, name)
        if value in canonical_ids:
            return value
        normal = norm(value)
        if normal in path_to_id:
            return path_to_id[normal]

    for raw in row.values():
        value = str(raw or "").strip()
        if value in canonical_ids:
            return value
        normal = norm(value)
        if normal in path_to_id:
            return path_to_id[normal]
    return ""


def claim_paths(row: dict[str, str]) -> list[str]:
    found = set()
    for raw in row.values():
        value = str(raw or "").strip()
        if value and is_feed_path(value):
            found.add(norm(value))
    return sorted(found)


def source_feed_literals(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return set()

    literals = set()
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.strip()
                if is_feed_path(value):
                    literals.add(norm(value))
    except SyntaxError:
        pattern = re.compile(
            r"""["']([^"']+\.(?:csv|json|parquet|geojson|sqlite|db))["']""",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            literals.add(norm(match.group(1)))

    return literals


def category(path: str) -> str:
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
    for label, tokens in rules:
        if any(token in name for token in tokens):
            return label
    return "OTHER"


def main() -> int:
    registry_rows = read_csv(REFINED)
    claim_rows = read_csv(CLAIMS)

    canonical_rows = [
        row for row in registry_rows
        if first(row, "classification", "builder_classification").upper() == "CANONICAL"
    ]
    canonical_ids = {first(row, "builder_id", "id") for row in canonical_rows}
    canonical_ids.discard("")

    by_id = {
        first(row, "builder_id", "id"): row
        for row in canonical_rows
        if first(row, "builder_id", "id")
    }
    path_to_id = {}
    for builder_id, row in by_id.items():
        relative = first(row, "relative_path", "builder_path", "path", "script_path")
        if relative:
            path_to_id[norm(relative)] = builder_id

    public_files = sorted(
        path.relative_to(ROOT).as_posix()
        for path in PUBLIC_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in FEED_EXTENSIONS
    )
    public_by_norm = {norm(path): path for path in public_files}
    public_by_name: dict[str, list[str]] = defaultdict(list)
    for path in public_files:
        public_by_name[Path(path).name.lower()].append(path)

    evidence: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    ambiguous_rows: list[dict[str, object]] = []

    # Evidence source 1: governed output-claim registry.
    for index, row in enumerate(claim_rows, start=2):
        owner = resolve_builder(row, canonical_ids, path_to_id)
        if not owner:
            continue
        for claimed in claim_paths(row):
            if claimed in public_by_norm:
                actual = public_by_norm[claimed]
                evidence[norm(actual)][owner].add("OUTPUT_CLAIM_EXACT_PATH")
                continue

            name = Path(claimed).name.lower()
            matches = public_by_name.get(name, [])
            if len(matches) == 1:
                evidence[norm(matches[0])][owner].add("OUTPUT_CLAIM_UNIQUE_FILENAME")
            elif len(matches) > 1:
                ambiguous_rows.append({
                    "evidence_source": "OUTPUT_CLAIM",
                    "source_reference": f"row:{index}",
                    "owner_builder_id": owner,
                    "claimed_value": claimed,
                    "candidate_count": len(matches),
                    "candidate_feed_paths": " | ".join(sorted(matches)),
                    "reason": "AMBIGUOUS_FILENAME_MATCH",
                })

    # Evidence source 2: direct canonical builder string literals.
    scanned_builders = 0
    builders_with_feed_literals = 0
    for builder_id, row in sorted(by_id.items()):
        relative = first(row, "relative_path", "builder_path", "path", "script_path")
        if not relative:
            continue
        source_path = ROOT / relative
        if not source_path.exists() or source_path.suffix.lower() != ".py":
            continue

        scanned_builders += 1
        literals = source_feed_literals(source_path)
        if literals:
            builders_with_feed_literals += 1

        for literal in literals:
            if literal in public_by_norm:
                actual = public_by_norm[literal]
                evidence[norm(actual)][builder_id].add("SOURCE_LITERAL_EXACT_PATH")
                continue

            name = Path(literal).name.lower()
            matches = public_by_name.get(name, [])
            if len(matches) == 1:
                evidence[norm(matches[0])][builder_id].add("SOURCE_LITERAL_UNIQUE_FILENAME")
            elif len(matches) > 1:
                ambiguous_rows.append({
                    "evidence_source": "SOURCE_LITERAL",
                    "source_reference": relative,
                    "owner_builder_id": builder_id,
                    "claimed_value": literal,
                    "candidate_count": len(matches),
                    "candidate_feed_paths": " | ".join(sorted(matches)),
                    "reason": "AMBIGUOUS_FILENAME_MATCH",
                })

    feed_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    unowned_rows: list[dict[str, object]] = []

    for index, path in enumerate(public_files, start=1):
        key = norm(path)
        owner_map = evidence.get(key, {})
        owners = sorted(owner_map)
        file_path = ROOT / path
        record = {
            "feed_id": f"FEED_{index:05d}",
            "feed_path": path,
            "feed_name": Path(path).name,
            "feed_format": Path(path).suffix.lower().lstrip("."),
            "feed_category": category(path),
            "file_size_bytes": file_path.stat().st_size,
            "modified_utc": datetime.fromtimestamp(
                file_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "owner_count": len(owners),
            "owner_builder_ids": " | ".join(owners),
            "ownership_status": (
                "OWNED" if len(owners) == 1
                else "MULTIPLE_EVIDENCED_OWNERS" if len(owners) > 1
                else "UNOWNED"
            ),
            "evidence_types": " | ".join(sorted({
                evidence_type
                for owner in owners
                for evidence_type in owner_map[owner]
            })),
        }
        feed_rows.append(record)

        for owner in owners:
            owner_path = first(
                by_id[owner], "relative_path", "builder_path", "path", "script_path"
            )
            evidence_rows.append({
                "feed_path": path,
                "owner_builder_id": owner,
                "owner_builder_path": owner_path,
                "evidence_types": " | ".join(sorted(owner_map[owner])),
            })

        if not owners:
            unowned_rows.append({
                "feed_path": path,
                "feed_name": Path(path).name,
                "feed_format": Path(path).suffix.lower().lstrip("."),
                "feed_category": category(path),
                "governance_action": "ASSIGN_OWNER_OR_EXCLUDE",
            })

    write_csv(REGISTRY, feed_rows, [
        "feed_id", "feed_path", "feed_name", "feed_format", "feed_category",
        "file_size_bytes", "modified_utc", "owner_count", "owner_builder_ids",
        "ownership_status", "evidence_types",
    ])
    write_csv(OWNERSHIP_EVIDENCE, evidence_rows, [
        "feed_path", "owner_builder_id", "owner_builder_path", "evidence_types",
    ])
    write_csv(AMBIGUOUS, ambiguous_rows, [
        "evidence_source", "source_reference", "owner_builder_id", "claimed_value",
        "candidate_count", "candidate_feed_paths", "reason",
    ])
    write_csv(UNOWNED, unowned_rows, [
        "feed_path", "feed_name", "feed_format", "feed_category", "governance_action",
    ])

    owned_count = sum(1 for row in feed_rows if int(row["owner_count"]) > 0)
    single_owner_count = sum(1 for row in feed_rows if int(row["owner_count"]) == 1)
    multiple_owner_count = sum(1 for row in feed_rows if int(row["owner_count"]) > 1)

    verdict = "PASS" if owned_count > 0 and evidence_rows else "FAIL_NO_OWNERSHIP_EVIDENCE"
    summary = {
        "schema_version": "1.1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "canonical_builder_count": len(canonical_ids),
        "canonical_python_builders_scanned": scanned_builders,
        "builders_with_feed_literals": builders_with_feed_literals,
        "product_feed_count": len(feed_rows),
        "owned_feed_count": owned_count,
        "single_owner_feed_count": single_owner_count,
        "multiple_evidenced_owner_feed_count": multiple_owner_count,
        "unowned_feed_count": len(unowned_rows),
        "ownership_evidence_row_count": len(evidence_rows),
        "ambiguous_evidence_row_count": len(ambiguous_rows),
        "ownership_coverage_percentage": round(
            owned_count / len(feed_rows) * 100.0, 4
        ) if feed_rows else 0.0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    SCHEMA.write_text(json.dumps({
        "output_claim_headers": list(claim_rows[0].keys()) if claim_rows else [],
        "refined_registry_headers": list(registry_rows[0].keys()) if registry_rows else [],
        "ownership_evidence_methods": [
            "OUTPUT_CLAIM_EXACT_PATH",
            "OUTPUT_CLAIM_UNIQUE_FILENAME",
            "SOURCE_LITERAL_EXACT_PATH",
            "SOURCE_LITERAL_UNIQUE_FILENAME",
        ],
    }, indent=2) + "\n", encoding="utf-8")

    REPORT.write_text("\n".join([
        "# EDGEIQ Product Feed Registry V1.1",
        "",
        "## Executive Summary",
        "",
        f"- Verdict: **{verdict}**",
        f"- Product feeds discovered: **{len(feed_rows)}**",
        f"- Feeds with ownership evidence: **{owned_count}**",
        f"- Single-owner feeds: **{single_owner_count}**",
        f"- Multiple-evidenced-owner feeds: **{multiple_owner_count}**",
        f"- Unowned feeds: **{len(unowned_rows)}**",
        f"- Ownership coverage: **{summary['ownership_coverage_percentage']}%**",
        "",
        "## Correction from V1",
        "",
        "V1 discovered feeds correctly but resolved no owners. V1.1 combines governed "
        "output claims with direct canonical Python source-literal evidence. Exact path "
        "matches are preferred; unique filename matches are permitted and labelled.",
        "",
        "## Ambiguity Policy",
        "",
        "Non-unique filename matches are never assigned automatically. They are written "
        "to the ambiguous ownership evidence queue.",
        "",
        "## Acceptance",
        "",
        "The unit fails unless at least one materialised product feed has canonical "
        "ownership evidence.",
        "",
    ]), encoding="utf-8")

    print("EDGEIQ PRODUCT FEED REGISTRY V1.1")
    print(f"VERDICT={verdict}")
    print(f"PRODUCT_FEEDS={len(feed_rows)}")
    print(f"OWNED_FEEDS={owned_count}")
    print(f"SINGLE_OWNER_FEEDS={single_owner_count}")
    print(f"MULTIPLE_EVIDENCED_OWNER_FEEDS={multiple_owner_count}")
    print(f"UNOWNED_FEEDS={len(unowned_rows)}")
    print(f"OWNERSHIP_EVIDENCE_ROWS={len(evidence_rows)}")
    print(f"OWNERSHIP_COVERAGE_PERCENT={summary['ownership_coverage_percentage']}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
