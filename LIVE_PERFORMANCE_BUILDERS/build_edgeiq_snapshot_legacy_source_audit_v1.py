from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path.cwd()

OUT = ROOT / "docs" / "platform-working-tree-reconciliation-v1"
OUT.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT / "edgeiq_snapshot_legacy_source_audit_v1.csv"
JSON_PATH = OUT / "edgeiq_snapshot_legacy_source_audit_v1.json"
REPORT_PATH = OUT / "EDGEIQ_SNAPSHOT_LEGACY_SOURCE_AUDIT_V1.md"


SNAPSHOT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "BEFORE_SNAPSHOT",
        re.compile(r"(^|[/_])before([/_]|$)", re.IGNORECASE),
    ),
    (
        "UI_LOCK_SNAPSHOT",
        re.compile(r"ui[_-]?locked", re.IGNORECASE),
    ),
    (
        "MASTER_LOCK_SNAPSHOT",
        re.compile(r"master[_-]?lock", re.IGNORECASE),
    ),
    (
        "LEGACY_SOURCE",
        re.compile(r"(^|[/_])legacy([/_\.]|$)", re.IGNORECASE),
    ),
    (
        "BACKUP_SOURCE",
        re.compile(
            r"(^|[/_])(backup|bak|copy|old|original)([/_\.]|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "DATED_SNAPSHOT",
        re.compile(r"(20\d{6}|20\d{4}[_-]\d{2}[_-]\d{2})"),
    ),
    (
        "VERSIONED_SNAPSHOT",
        re.compile(
            r"([_-]v\d+([_-]\d+)*)(?=\.[^.]+$)",
            re.IGNORECASE,
        ),
    ),
]


def run_git(
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def decode(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def normalise(path: str) -> str:
    return path.replace("\\", "/")


def parse_source_status() -> list[dict[str, str]]:
    result = run_git(
        "-c",
        "core.quotepath=false",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        "src",
    )

    tokens = result.stdout.split(b"\0")
    rows: list[dict[str, str]] = []
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if not token:
            index += 1
            continue

        if len(token) < 3:
            raise RuntimeError(
                f"Unexpected Git status token: {token!r}"
            )

        status = token[:2].decode(
            "ascii",
            errors="replace",
        )

        path = normalise(decode(token[3:]))
        original_path = ""

        if status[0] in {"R", "C"}:
            index += 1

            if index >= len(tokens):
                raise RuntimeError(
                    f"Missing original path for {path}"
                )

            original_path = normalise(
                decode(tokens[index])
            )

        rows.append(
            {
                "index_status": status[0],
                "worktree_status": status[1],
                "path": path,
                "original_path": original_path,
            }
        )

        index += 1

    return rows


def tracked_by_git(path: str) -> bool:
    result = run_git(
        "ls-files",
        "--error-unmatch",
        "--",
        path,
        check=False,
    )
    return result.returncode == 0


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        return sum(1 for _ in handle)


def snapshot_categories(path: str) -> list[str]:
    filename = PurePosixPath(path).name
    categories: list[str] = []

    for category, pattern in SNAPSHOT_PATTERNS:
        if pattern.search(filename):
            categories.append(category)

    return categories


def active_counterpart_candidates(path: str) -> list[str]:
    pure = PurePosixPath(path)
    stem = pure.stem
    suffix = pure.suffix

    candidates: set[str] = set()

    transforms = [
        r"(?i)_before_.*$",
        r"(?i)_before$",
        r"(?i)_ui_locked$",
        r"(?i)_master_lock$",
        r"(?i)_legacy$",
        r"(?i)_backup$",
        r"(?i)_bak$",
        r"(?i)_copy$",
        r"(?i)_old$",
        r"(?i)_original$",
        r"(?i)_20\d{6}$",
        r"(?i)_20\d{4}_\d{2}_\d{2}$",
    ]

    for pattern in transforms:
        cleaned = re.sub(pattern, "", stem)

        if cleaned and cleaned != stem:
            candidates.add(
                str(pure.with_name(cleaned + suffix))
            )

    before_match = re.match(
        r"(?i)(.+?)_before_.+",
        stem,
    )

    if before_match:
        candidates.add(
            str(
                pure.with_name(
                    before_match.group(1) + suffix
                )
            )
        )

    return sorted(
        normalise(candidate)
        for candidate in candidates
    )


def resolution_status(
    candidates: list[str],
) -> tuple[str, str]:
    for candidate in candidates:
        candidate_path = ROOT / Path(candidate)

        if candidate_path.exists():
            return "ACTIVE_COUNTERPART_FOUND", candidate

    if candidates:
        return "COUNTERPART_NOT_FOUND", ""

    return "NO_COUNTERPART_INFERRED", ""


status_rows = parse_source_status()

snapshot_rows: list[dict[str, object]] = []
non_snapshot_rows: list[dict[str, object]] = []

for status_row in status_rows:
    path = status_row["path"]
    categories = snapshot_categories(path)

    tracked = tracked_by_git(path)
    local_path = ROOT / Path(path)

    base_row: dict[str, object] = {
        "index_status": status_row["index_status"],
        "worktree_status": status_row["worktree_status"],
        "tracked_by_git": str(tracked).upper(),
        "path": path,
        "original_path": status_row["original_path"],
        "file_size_bytes": (
            local_path.stat().st_size
            if local_path.is_file()
            else 0
        ),
        "line_count": count_lines(local_path),
        "sha256": (
            file_hash(local_path)
            if local_path.is_file()
            else ""
        ),
    }

    if categories:
        candidates = active_counterpart_candidates(path)

        counterpart_status, counterpart_path = (
            resolution_status(candidates)
        )

        base_row.update(
            {
                "snapshot_categories": "|".join(categories),
                "counterpart_status": counterpart_status,
                "counterpart_path": counterpart_path,
                "counterpart_candidates": "|".join(
                    candidates
                ),
                "recommended_disposition": (
                    "REVIEW_FOR_ARCHIVE_OR_REMOVAL"
                    if counterpart_status
                    == "ACTIVE_COUNTERPART_FOUND"
                    else "MANUAL_ARCHITECTURAL_REVIEW"
                ),
            }
        )

        snapshot_rows.append(base_row)
    else:
        base_row.update(
            {
                "snapshot_categories": "",
                "counterpart_status": "NOT_APPLICABLE",
                "counterpart_path": "",
                "counterpart_candidates": "",
                "recommended_disposition": (
                    "RETAIN_IN_ACTIVE_SOURCE_RECONCILIATION"
                ),
            }
        )

        non_snapshot_rows.append(base_row)

snapshot_rows.sort(
    key=lambda row: (
        str(row["counterpart_status"]),
        str(row["path"]).lower(),
    )
)

fieldnames = [
    "index_status",
    "worktree_status",
    "tracked_by_git",
    "snapshot_categories",
    "counterpart_status",
    "counterpart_path",
    "counterpart_candidates",
    "recommended_disposition",
    "file_size_bytes",
    "line_count",
    "sha256",
    "path",
    "original_path",
]

with CSV_PATH.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fieldnames,
    )
    writer.writeheader()
    writer.writerows(snapshot_rows)

category_counts: Counter[str] = Counter()
counterpart_counts = Counter(
    str(row["counterpart_status"])
    for row in snapshot_rows
)
tracked_counts = Counter(
    str(row["tracked_by_git"])
    for row in snapshot_rows
)

for row in snapshot_rows:
    for category in str(
        row["snapshot_categories"]
    ).split("|"):
        if category:
            category_counts[category] += 1

with JSON_PATH.open(
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        {
            "schema_version": "1.0",
            "source_changed_items": len(status_rows),
            "snapshot_legacy_items": len(snapshot_rows),
            "active_source_items": len(non_snapshot_rows),
            "snapshot_items": snapshot_rows,
        },
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")

with REPORT_PATH.open(
    "w",
    encoding="utf-8",
) as handle:
    handle.write(
        "# EDGEIQ Snapshot and Legacy Source Audit V1\n\n"
    )

    handle.write("## Status\n\n")
    handle.write(
        "PASS - snapshot and legacy source candidates "
        "identified without repository mutation.\n\n"
    )

    handle.write(
        f"- Total changed source items: {len(status_rows)}\n"
    )
    handle.write(
        f"- Snapshot or legacy candidates: "
        f"{len(snapshot_rows)}\n"
    )
    handle.write(
        f"- Remaining active-source candidates: "
        f"{len(non_snapshot_rows)}\n\n"
    )

    handle.write("## Snapshot Category Distribution\n\n")

    if category_counts:
        for category, count in sorted(
            category_counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            handle.write(
                f"- {category}: {count}\n"
            )
    else:
        handle.write("- None detected.\n")

    handle.write(
        "\n## Counterpart Resolution\n\n"
    )

    for status, count in sorted(
        counterpart_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        handle.write(f"- {status}: {count}\n")

    handle.write(
        "\n## Git Tracking State\n\n"
    )

    for status, count in sorted(
        tracked_counts.items()
    ):
        handle.write(f"- {status}: {count}\n")

    handle.write(
        "\n## Snapshot and Legacy Candidates\n\n"
    )

    if snapshot_rows:
        for row in snapshot_rows:
            handle.write(
                f"- `{row['index_status']}"
                f"{row['worktree_status']}` "
                f"`{row['snapshot_categories']}` "
                f"`{row['counterpart_status']}` "
                f"`{row['path']}`"
            )

            if row["counterpart_path"]:
                handle.write(
                    f" -> `{row['counterpart_path']}`"
                )

            handle.write("\n")
    else:
        handle.write("- None detected.\n")

    handle.write(
        "\n## Governance Decision\n\n"
    )
    handle.write(
        "This audit does not authorise deletion, movement, "
        "renaming, staging, reset, stash or commit.\n"
    )
    handle.write(
        "Files with active counterparts are candidates for "
        "archive or removal only after repository-reference "
        "and build-usage checks pass.\n"
    )
    handle.write(
        "Files without inferred counterparts remain subject "
        "to manual architectural review.\n"
    )

print("STATUS=PASS")
print(
    f"TOTAL_CHANGED_SOURCE_ITEMS={len(status_rows)}"
)
print(
    f"SNAPSHOT_LEGACY_CANDIDATES={len(snapshot_rows)}"
)
print(
    f"REMAINING_ACTIVE_SOURCE_CANDIDATES="
    f"{len(non_snapshot_rows)}"
)
print(
    "ACTIVE_COUNTERPART_FOUND="
    f"{counterpart_counts.get('ACTIVE_COUNTERPART_FOUND', 0)}"
)
print(
    "COUNTERPART_NOT_FOUND="
    f"{counterpart_counts.get('COUNTERPART_NOT_FOUND', 0)}"
)
print(
    "NO_COUNTERPART_INFERRED="
    f"{counterpart_counts.get('NO_COUNTERPART_INFERRED', 0)}"
)
print(f"CSV={CSV_PATH}")
print(f"JSON={JSON_PATH}")
print(f"REPORT={REPORT_PATH}")
