from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PI_ROOT = ROOT / "docs" / "performance-intelligence"
AUDIT_DIR = PI_ROOT / "audits"
INVENTORY_DIR = PI_ROOT / "inventories"

MAX_CANDIDATES = 300
MAX_READ_BYTES = 500_000

EXCLUDED_PREFIXES = (
    "_archive_pre_git_commit/",
    "checkpoints/",
    "node_modules/",
    "dist/",
    "build/",
    ".git/",
    "docs/performance-intelligence/",
)

EXCLUDED_FRAGMENTS = (
    "_checkpoint_",
    "_backup_",
    "/backups/",
    "/archives/",
)

ACTIVE_PREFIX_POINTS = {
    "scripts/": 30,
    "public/data/": 25,
    "src/": 20,
    "data/": 18,
    "warehouse/": 35,
    "warehouses/": 35,
}

HIGH_VALUE_TERMS = {
    "warehouse": 18,
    "results": 12,
    "result": 8,
    "sectional": 16,
    "benchmark": 18,
    "standardised": 8,
    "seconds_to_lengths": 25,
    "seconds_per_length": 25,
    "length_conversion": 25,
    "historical_form": 18,
    "runner_profile": 12,
    "performance": 12,
    "canonical": 15,
    "identity": 15,
    "race_strength": 15,
    "fingerprint": 18,
    "campaign": 10,
    "dna": 10,
    "epi": 10,
    "eri": 10,
}

FORMULA_TERMS = {
    "seconds_per_length": (
        "seconds_per_length",
        "seconds per length",
        "secs_per_length",
        "sec_per_length",
    ),
    "seconds_to_lengths": (
        "seconds_to_lengths",
        "seconds to lengths",
        "lengths_vs_benchmark",
        "lengths difference",
        "lengths_difference",
    ),
    "benchmark": (
        "benchmark",
        "par_time",
        "standard_time",
        "track_standard",
    ),
    "sectional": (
        "sectional",
        "last_800",
        "last_600",
        "last_400",
        "last_200",
        "800_600",
        "600_400",
        "400_200",
        "200_finish",
    ),
    "epi": (
        " epi ",
        "epi_",
        "_epi",
        "projected_rating",
    ),
    "eri": (
        " eri ",
        "eri_",
        "_eri",
        "race_strength",
    ),
    "identity": (
        "canonical_horse",
        "canonical_race",
        "canonical_meeting",
        "identity_resolution",
        "horse_id",
        "race_id",
    ),
}

REFERENCE_PATTERN = re.compile(
    r"""["']([^"']+\.(?:csv|json|parquet|feather|sqlite|sqlite3|db))["']""",
    re.IGNORECASE,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_inventory() -> Path:
    files = sorted(
        INVENTORY_DIR.glob(
            "edgeiq_performance_intelligence_asset_inventory_*.csv"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        raise FileNotFoundError("Phase 0 inventory CSV not found.")

    return files[0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def excluded(path_text: str) -> bool:
    value = path_text.replace("\\", "/").lower()

    if value.startswith(EXCLUDED_PREFIXES):
        return True

    return any(fragment in value for fragment in EXCLUDED_FRAGMENTS)


def score(record: dict[str, str]) -> tuple[int, list[str]]:
    path_text = record["path"].replace("\\", "/").lower()
    filename = Path(path_text).name
    value = 0
    reasons: list[str] = []

    for prefix, points in ACTIVE_PREFIX_POINTS.items():
        if path_text.startswith(prefix):
            value += points
            reasons.append(f"active={prefix}")
            break

    for term, points in HIGH_VALUE_TERMS.items():
        if term in path_text:
            value += points
            reasons.append(term)

    if filename.startswith(
        ("build_", "audit_", "ingest_", "normalise_", "derive_")
    ):
        value += 15
        reasons.append("engine_script")

    categories = record.get("categories", "").lower()

    for category in (
        "results",
        "sectionals",
        "benchmarks",
        "length_conversion",
        "performance",
        "identity",
        "patterns",
        "quality",
    ):
        if category in categories:
            value += 4

    return value, reasons


def read_prefix(path: Path) -> str:
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as handle:
            return handle.read(MAX_READ_BYTES)
    except OSError:
        return ""


def resolve_reference(
    source_path: Path,
    reference: str,
) -> tuple[str, str]:
    clean = reference.replace("\\", "/")

    candidates = [
        ROOT / clean,
        source_path.parent / clean,
    ]

    if clean.startswith("data/"):
        candidates.append(ROOT / "public" / clean)

    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue

        if not candidate.exists():
            continue

        try:
            return (
                str(candidate.relative_to(ROOT)).replace("\\", "/"),
                "RESOLVED",
            )
        except ValueError:
            return str(candidate), "OUTSIDE_REPOSITORY"

    return "", "UNRESOLVED_OR_GENERATED"


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)

    inventory_path = latest_inventory()
    inventory = read_csv(inventory_path)

    live_records = [
        record
        for record in inventory
        if not excluded(record["path"])
    ]

    ranked: list[tuple[int, list[str], dict[str, str]]] = []

    for record in live_records:
        candidate_score, reasons = score(record)

        if candidate_score >= 30:
            ranked.append((candidate_score, reasons, record))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[2]["path"].lower(),
        )
    )

    ranked = ranked[:MAX_CANDIDATES]

    candidates: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    for index, (candidate_score, reasons, record) in enumerate(
        ranked,
        start=1,
    ):
        path_text = record["path"].replace("\\", "/")
        source_path = ROOT / path_text
        content = read_prefix(source_path)
        lowered = f" {content.lower()} "

        if index == 1 or index % 20 == 0:
            print(
                f"PROGRESS={index}/{len(ranked)} PATH={path_text}",
                flush=True,
            )

        candidates.append(
            {
                "score": candidate_score,
                "path": path_text,
                "categories": record.get("categories", ""),
                "score_reasons": " | ".join(reasons),
                "extension": record.get("extension", ""),
                "size_bytes": record.get("size_bytes", ""),
                "modified_utc": record.get("modified_utc", ""),
                "row_count": record.get("row_count", ""),
                "column_count": record.get("column_count", ""),
                "columns": record.get("columns", ""),
                "record_count": record.get("record_count", ""),
                "top_level_keys": record.get("top_level_keys", ""),
                "bytes_inspected": len(content.encode("utf-8")),
            }
        )

        seen_reference: set[str] = set()

        for match in REFERENCE_PATTERN.finditer(content):
            raw_reference = match.group(1)

            if raw_reference in seen_reference:
                continue

            seen_reference.add(raw_reference)

            resolved_path, status = resolve_reference(
                source_path,
                raw_reference,
            )

            references.append(
                {
                    "consumer_path": path_text,
                    "referenced_text": raw_reference,
                    "resolved_path": resolved_path,
                    "reference_status": status,
                }
            )

        lines = content.splitlines()
        matched_per_type: Counter[str] = Counter()

        for line_number, line in enumerate(lines, start=1):
            lowered_line = line.lower()

            for evidence_type, terms in FORMULA_TERMS.items():
                if matched_per_type[evidence_type] >= 8:
                    continue

                if any(term in lowered_line for term in terms):
                    evidence.append(
                        {
                            "evidence_type": evidence_type,
                            "path": path_text,
                            "line_number": line_number,
                            "line_text": line.strip()[:500],
                        }
                    )
                    matched_per_type[evidence_type] += 1

    references = list(
        {
            (
                row["consumer_path"],
                row["referenced_text"],
                row["resolved_path"],
            ): row
            for row in references
        }.values()
    )

    evidence = list(
        {
            (
                row["evidence_type"],
                row["path"],
                row["line_number"],
                row["line_text"],
            ): row
            for row in evidence
        }.values()
    )

    evidence_counts = Counter(
        row["evidence_type"]
        for row in evidence
    )

    resolved_count = sum(
        1
        for row in references
        if row["reference_status"] == "RESOLVED"
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    candidates_path = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_live_candidates_fast_{run_id}.csv"
    )
    lineage_path = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_live_lineage_fast_{run_id}.csv"
    )
    evidence_path = (
        INVENTORY_DIR
        / f"edgeiq_performance_intelligence_formula_evidence_fast_{run_id}.csv"
    )
    summary_path = (
        AUDIT_DIR
        / f"edgeiq_performance_intelligence_phase0_1_fast_summary_{run_id}.json"
    )
    latest_path = (
        AUDIT_DIR
        / "edgeiq_performance_intelligence_phase0_1_fast_latest.json"
    )

    summary = {
        "audit_name": (
            "EDGEiQ Performance Intelligence Phase 0.1 "
            "Fast Live Asset Triage"
        ),
        "generated_utc": now_utc(),
        "source_inventory": str(
            inventory_path.relative_to(ROOT)
        ).replace("\\", "/"),
        "original_inventory_count": len(inventory),
        "excluded_count": len(inventory) - len(live_records),
        "live_scope_count": len(live_records),
        "candidate_limit": MAX_CANDIDATES,
        "candidates_inspected": len(candidates),
        "references_found": len(references),
        "resolved_references": resolved_count,
        "unresolved_or_generated_references": (
            len(references) - resolved_count
        ),
        "formula_evidence_count": len(evidence),
        "formula_evidence_counts": dict(
            sorted(evidence_counts.items())
        ),
        "canonical_status": "NOT_YET_DETERMINED",
        "next_stage": (
            "Phase 0.2 domain-specific lineage and schema validation"
        ),
    }

    write_csv(candidates_path, candidates)
    write_csv(lineage_path, references)
    write_csv(evidence_path, evidence)
    write_json(summary_path, summary)
    write_json(latest_path, summary)

    print(
        "EDGEIQ_PERFORMANCE_INTELLIGENCE_"
        "PHASE0_1_FAST_TRIAGE_PASS",
        flush=True,
    )
    print(f"CANDIDATES={candidates_path}", flush=True)
    print(f"LINEAGE={lineage_path}", flush=True)
    print(f"EVIDENCE={evidence_path}", flush=True)
    print(f"SUMMARY={summary_path}", flush=True)


if __name__ == "__main__":
    main()
