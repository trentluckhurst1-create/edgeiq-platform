from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path.cwd()

OUT = ROOT / "docs" / "platform-working-tree-reconciliation-v1"
OUT.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT / "edgeiq_application_source_reconciliation_dossier_v1.csv"
JSON_PATH = OUT / "edgeiq_application_source_reconciliation_dossier_v1.json"
REPORT_PATH = OUT / "EDGEIQ_APPLICATION_SOURCE_RECONCILIATION_DOSSIER_V1.md"


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


def parse_status() -> list[dict[str, str]]:
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
    position = 0

    while position < len(tokens):
        token = tokens[position]

        if not token:
            position += 1
            continue

        if len(token) < 3:
            raise RuntimeError(f"Unexpected Git status token: {token!r}")

        status = token[:2].decode("ascii", errors="replace")
        path = normalise(decode(token[3:]))
        original_path = ""

        if status[0] in {"R", "C"}:
            position += 1

            if position >= len(tokens):
                raise RuntimeError(
                    f"Missing original path for rename/copy: {path}"
                )

            original_path = normalise(decode(tokens[position]))

        rows.append(
            {
                "index_status": status[0],
                "worktree_status": status[1],
                "path": path,
                "original_path": original_path,
            }
        )

        position += 1

    return rows


def read_numstat() -> dict[str, tuple[str, str]]:
    result = run_git(
        "-c",
        "core.quotepath=false",
        "diff",
        "--numstat",
        "--",
        "src",
    )

    stats: dict[str, tuple[str, str]] = {}

    for raw_line in decode(result.stdout).splitlines():
        parts = raw_line.split("\t")

        if len(parts) < 3:
            continue

        added = parts[0]
        deleted = parts[1]
        path = normalise(parts[-1])

        stats[path] = (added, deleted)

    return stats


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def count_lines(path: Path) -> int:
    try:
        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def candidate_unit(path: str) -> str:
    value = path.lower()

    rules = [
        (
            (
                "/meetings/" in value
                or "meetingworkspace" in value
                or "meetingsworkspace" in value
            ),
            "MEETINGS_WORKSPACE",
        ),
        (
            (
                "/race/" in value
                or "raceworkspace" in value
                or "racefile" in value
            ),
            "RACE_WORKSPACE",
        ),
        (
            (
                "/field/" in value
                or "fieldworkspace" in value
            ),
            "FIELD_WORKSPACE",
        ),
        (
            (
                "/performance/" in value
                or "performanceworkspace" in value
            ),
            "PERFORMANCE_WORKSPACE",
        ),
        (
            (
                "/form/" in value
                or "formworkspace" in value
                or "formguide" in value
            ),
            "FORM_WORKSPACE",
        ),
        (
            (
                "/map/" in value
                or "mapworkspace" in value
                or "speedmap" in value
            ),
            "MAP_WORKSPACE",
        ),
        (
            (
                "/market/" in value
                or "marketworkspace" in value
            ),
            "MARKET_WORKSPACE",
        ),
        (
            (
                "/results/" in value
                or "resultsworkspace" in value
            ),
            "RESULTS_WORKSPACE",
        ),
        (
            (
                "/weather/" in value
                or "weatherworkspace" in value
            ),
            "WEATHER_WORKSPACE",
        ),
        (
            (
                "/track/" in value
                or "trackworkspace" in value
            ),
            "TRACK_WORKSPACE",
        ),
        (
            (
                "/overview/" in value
                or "overviewworkspace" in value
            ),
            "OVERVIEW_WORKSPACE",
        ),
        (
            (
                "/insights/" in value
                or "insightsworkspace" in value
            ),
            "INSIGHTS_WORKSPACE",
        ),
        (
            (
                "/nexus/" in value
                or "nexusworkspace" in value
            ),
            "NEXUS_WORKSPACE",
        ),
        (
            (
                "navigation" in value
                or "/nav/" in value
                or "app.tsx" in value
                or "router" in value
            ),
            "APPLICATION_SHELL_AND_NAVIGATION",
        ),
        (
            (
                "/components/" in value
                or "/shared/" in value
                or "/ui/" in value
            ),
            "SHARED_UI_COMPONENT",
        ),
        (
            (
                value.endswith(".css")
                or "/styles/" in value
            ),
            "APPLICATION_STYLING",
        ),
        (
            (
                "/types/" in value
                or value.endswith("types.ts")
                or value.endswith("types.tsx")
            ),
            "SHARED_TYPES",
        ),
        (
            (
                "/data/" in value
                or "/services/" in value
                or "/api/" in value
                or "adapter" in value
                or "loader" in value
            ),
            "FRONTEND_DATA_WIRING",
        ),
    ]

    for matched, unit in rules:
        if matched:
            return unit

    return "SOURCE_UNIT_UNRESOLVED"


def directory_group(path: str) -> str:
    parts = PurePosixPath(path).parts

    if len(parts) >= 4:
        return "/".join(parts[:4])

    if len(parts) >= 3:
        return "/".join(parts[:3])

    return "/".join(parts)


status_rows = parse_status()
numstat = read_numstat()

dossier: list[dict[str, object]] = []

for status_row in status_rows:
    path = status_row["path"]
    local_path = ROOT / Path(path)

    is_untracked = (
        status_row["index_status"] == "?"
        and status_row["worktree_status"] == "?"
    )

    if is_untracked:
        added = str(count_lines(local_path)) if local_path.is_file() else "0"
        deleted = "0"
        tracked_state = "UNTRACKED"
    else:
        added, deleted = numstat.get(path, ("0", "0"))
        tracked_state = "TRACKED"

    file_size = local_path.stat().st_size if local_path.is_file() else 0
    file_hash = sha256_file(local_path) if local_path.is_file() else ""

    dossier.append(
        {
            "candidate_unit": candidate_unit(path),
            "directory_group": directory_group(path),
            "tracked_state": tracked_state,
            "index_status": status_row["index_status"],
            "worktree_status": status_row["worktree_status"],
            "added_lines": added,
            "deleted_lines": deleted,
            "file_size_bytes": file_size,
            "sha256": file_hash,
            "path": path,
            "original_path": status_row["original_path"],
        }
    )

dossier.sort(
    key=lambda row: (
        str(row["candidate_unit"]),
        str(row["directory_group"]),
        str(row["path"]).lower(),
    )
)

fieldnames = [
    "candidate_unit",
    "directory_group",
    "tracked_state",
    "index_status",
    "worktree_status",
    "added_lines",
    "deleted_lines",
    "file_size_bytes",
    "sha256",
    "path",
    "original_path",
]

with CSV_PATH.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(dossier)

with JSON_PATH.open("w", encoding="utf-8") as handle:
    json.dump(
        {
            "schema_version": "1.0",
            "source_changed_items": len(dossier),
            "items": dossier,
        },
        handle,
        indent=2,
        ensure_ascii=False,
    )
    handle.write("\n")

unit_counts = Counter(
    str(row["candidate_unit"])
    for row in dossier
)

directory_counts = Counter(
    str(row["directory_group"])
    for row in dossier
)

tracked_counts = Counter(
    str(row["tracked_state"])
    for row in dossier
)

files_by_unit: dict[str, list[dict[str, object]]] = defaultdict(list)

for row in dossier:
    files_by_unit[str(row["candidate_unit"])].append(row)

with REPORT_PATH.open("w", encoding="utf-8") as handle:
    handle.write(
        "# EDGEIQ Application Source Reconciliation Dossier V1\n\n"
    )

    handle.write("## Status\n\n")
    handle.write(
        "PASS - application source changes inventoried without "
        "staging, deletion, reset, stash or commit.\n\n"
    )

    handle.write(f"- Source changed items: {len(dossier)}\n")
    handle.write(
        f"- Candidate units detected: {len(unit_counts)}\n"
    )
    handle.write(
        f"- Unresolved source items: "
        f"{unit_counts.get('SOURCE_UNIT_UNRESOLVED', 0)}\n\n"
    )

    handle.write("## Tracked State\n\n")

    for key, count in sorted(tracked_counts.items()):
        handle.write(f"- {key}: {count}\n")

    handle.write("\n## Candidate Unit Distribution\n\n")

    for key, count in sorted(
        unit_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        handle.write(f"- {key}: {count}\n")

    handle.write("\n## Directory Distribution\n\n")

    for key, count in sorted(
        directory_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        handle.write(f"- `{key}`: {count}\n")

    handle.write("\n## Files by Candidate Unit\n\n")

    for unit in sorted(files_by_unit):
        handle.write(f"### {unit}\n\n")

        for row in files_by_unit[unit]:
            handle.write(
                f"- `{row['index_status']}{row['worktree_status']}` "
                f"`+{row['added_lines']} -{row['deleted_lines']}` "
                f"`{row['path']}`\n"
            )

        handle.write("\n")

    handle.write("## Governance Decision\n\n")
    handle.write(
        "Candidate-unit assignment is forensic classification only. "
        "It does not authorise staging or committing.\n"
    )
    handle.write(
        "Each source group must be matched against its builder, audit, "
        "evidence and acceptance artefacts before becoming a governed "
        "commit unit.\n"
    )

print("STATUS=PASS")
print(f"SOURCE_CHANGED_ITEMS={len(dossier)}")
print(f"CANDIDATE_UNITS={len(unit_counts)}")
print(
    "UNRESOLVED_SOURCE_ITEMS="
    f"{unit_counts.get('SOURCE_UNIT_UNRESOLVED', 0)}"
)
print(f"CSV={CSV_PATH}")
print(f"JSON={JSON_PATH}")
print(f"REPORT={REPORT_PATH}")
