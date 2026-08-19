from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "EDGEIQ_CANONICAL_RUNTIME_FEED_PRODUCERS_V1"

EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "checkpoints",
    "checkpoint",
    "archive",
    "archives",
    "backup",
    "backups",
}

EXCLUDED_NAME_MARKERS = (
    "audit_",
    "apply_",
    "checkpoint",
    "backup",
    "baseline_doc",
    "readiness",
    "inventory",
    "report",
    "visual_audit",
    "browser_acceptance",
    "smoke",
    "test_",
)

WRITE_CONTEXT_PATTERN = re.compile(
    r"""
    (?:
        write_text|
        write_bytes|
        open\s*\(|
        DictWriter|
        csv\.writer|
        writerow|
        writerows|
        to_csv|
        to_json|
        json\.dump|
        json\.dumps|
        WriteAllText
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    lowered_parts = {part.lower() for part in relative.parts}
    lowered_name = path.name.lower()

    if lowered_parts.intersection(EXCLUDED_PARTS):
        return True

    if any(marker in lowered_name for marker in EXCLUDED_NAME_MARKERS):
        return True

    return False


def feed_reference_lines(
    text: str,
    feed_name: str,
) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if feed_name.lower() in line.lower():
            results.append((line_number, line.strip()))

    return results


def has_write_evidence(
    lines: list[str],
    line_number: int,
) -> bool:
    start = max(0, line_number - 8)
    end = min(len(lines), line_number + 12)
    context = "\n".join(lines[start:end])

    return bool(WRITE_CONTEXT_PATTERN.search(context))


def producer_score(
    path: Path,
    root: Path,
    feed_name: str,
    write_evidence_count: int,
    direct_reference_count: int,
    text: str,
) -> int:
    relative = path.relative_to(root).as_posix().lower()
    name = path.name.lower()
    feed_stem = Path(feed_name).stem.lower()

    score = 0

    if relative.startswith("scripts/"):
        score += 20

    if name.startswith("build_"):
        score += 25

    if feed_stem in name:
        score += 35

    if "terminal_feed" in name:
        score += 10

    if "product_feed" in name:
        score += 8

    score += write_evidence_count * 30
    score += min(direct_reference_count, 5) * 4

    if "output" in text.lower():
        score += 3

    return score


def main() -> int:
    root = Path.cwd().resolve()

    phase_a_path = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-a-runtime-feed-discovery"
        / "EDGEIQ_RUNTIME_FEED_DISCOVERY_V1_RESOLVED_RUNTIME_FEEDS.csv"
    )

    output_root = (
        root
        / "docs"
        / "runtime-data-wiring-audit-v1"
        / "phase-c2-canonical-producers"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    runtime_feeds = load_csv(phase_a_path)

    python_files = sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file() and not excluded(path, root)
    )

    print(f"=== {AUDIT_ID} ===", flush=True)
    print(f"runtime_feeds={len(runtime_feeds)}", flush=True)
    print(f"eligible_python_files={len(python_files)}", flush=True)

    all_candidates: list[dict[str, Any]] = []
    canonical_rows: list[dict[str, Any]] = []

    for index, feed in enumerate(runtime_feeds, start=1):
        feed_path = feed["resolved_feed"]
        feed_name = Path(feed_path).name
        candidates: list[dict[str, Any]] = []

        for path in python_files:
            try:
                text = path.read_text(
                    encoding="utf-8-sig",
                    errors="replace",
                )
            except OSError:
                continue

            references = feed_reference_lines(text, feed_name)

            if not references:
                continue

            lines = text.splitlines()

            write_lines = [
                line_number
                for line_number, _ in references
                if has_write_evidence(lines, line_number)
            ]

            score = producer_score(
                path=path,
                root=root,
                feed_name=feed_name,
                write_evidence_count=len(write_lines),
                direct_reference_count=len(references),
                text=text,
            )

            candidate = {
                "feed_path": feed_path,
                "feed_name": feed_name,
                "candidate_producer": path.relative_to(root).as_posix(),
                "score": score,
                "direct_reference_count": len(references),
                "write_evidence_count": len(write_lines),
                "reference_lines": ",".join(
                    str(line_number)
                    for line_number, _ in references[:20]
                ),
                "write_evidence_lines": ",".join(
                    str(line_number)
                    for line_number in write_lines[:20]
                ),
                "producer_status": (
                    "WRITE_CONFIRMED"
                    if write_lines
                    else "REFERENCE_ONLY"
                ),
            }

            candidates.append(candidate)
            all_candidates.append(candidate)

        candidates.sort(
            key=lambda row: (
                -int(row["write_evidence_count"]),
                -int(row["score"]),
                row["candidate_producer"],
            )
        )

        confirmed = [
            row
            for row in candidates
            if row["producer_status"] == "WRITE_CONFIRMED"
        ]

        selected = confirmed[0] if confirmed else (
            candidates[0] if candidates else None
        )

        if selected:
            canonical_rows.append(
                {
                    **selected,
                    "canonical_status": (
                        "CANONICAL_WRITE_CONFIRMED"
                        if confirmed
                        else "REVIEW_REFERENCE_ONLY"
                    ),
                    "confirmed_writer_count": len(confirmed),
                    "candidate_count": len(candidates),
                }
            )
        else:
            canonical_rows.append(
                {
                    "feed_path": feed_path,
                    "feed_name": feed_name,
                    "candidate_producer": "",
                    "score": 0,
                    "direct_reference_count": 0,
                    "write_evidence_count": 0,
                    "reference_lines": "",
                    "write_evidence_lines": "",
                    "producer_status": "NOT_FOUND",
                    "canonical_status": "NO_PRODUCER_FOUND",
                    "confirmed_writer_count": 0,
                    "candidate_count": 0,
                }
            )

        print(
            f"[producer] {index}/{len(runtime_feeds)} "
            f"{feed_name} -> "
            f"{selected['candidate_producer'] if selected else 'NOT_FOUND'}",
            flush=True,
        )

    fieldnames = [
        "feed_path",
        "feed_name",
        "candidate_producer",
        "score",
        "direct_reference_count",
        "write_evidence_count",
        "reference_lines",
        "write_evidence_lines",
        "producer_status",
    ]

    write_csv(
        output_root / f"{AUDIT_ID}_ALL_CANDIDATES.csv",
        sorted(
            all_candidates,
            key=lambda row: (
                row["feed_name"],
                -int(row["write_evidence_count"]),
                -int(row["score"]),
                row["candidate_producer"],
            ),
        ),
        fieldnames,
    )

    write_csv(
        output_root / f"{AUDIT_ID}_CANONICAL_PRODUCERS.csv",
        canonical_rows,
        fieldnames
        + [
            "canonical_status",
            "confirmed_writer_count",
            "candidate_count",
        ],
    )

    unresolved = [
        row
        for row in canonical_rows
        if row["canonical_status"] != "CANONICAL_WRITE_CONFIRMED"
    ]

    write_csv(
        output_root / f"{AUDIT_ID}_UNRESOLVED.csv",
        unresolved,
        fieldnames
        + [
            "canonical_status",
            "confirmed_writer_count",
            "candidate_count",
        ],
    )

    summary = {
        "audit_id": AUDIT_ID,
        "generated_at_utc": now_utc(),
        "runtime_feeds": len(runtime_feeds),
        "canonical_write_confirmed": sum(
            1
            for row in canonical_rows
            if row["canonical_status"] == "CANONICAL_WRITE_CONFIRMED"
        ),
        "reference_only": sum(
            1
            for row in canonical_rows
            if row["canonical_status"] == "REVIEW_REFERENCE_ONLY"
        ),
        "no_producer_found": sum(
            1
            for row in canonical_rows
            if row["canonical_status"] == "NO_PRODUCER_FOUND"
        ),
        "status": (
            "PASS"
            if not unresolved
            else "REVIEW_REQUIRED"
        ),
    }

    (
        output_root / f"{AUDIT_ID}_SUMMARY.json"
    ).write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n=== PHASE C2 COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())