from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESOLVER_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_"
    "PHASE1A_6B_V1"
)

PASS_STATUS = f"{RESOLVER_ID}_PASS"
FAIL_STATUS = f"{RESOLVER_ID}_FAIL"

EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

ROOT = Path.cwd().absolute()

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-authority"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_RESOLUTION_REPORT.md"
)

CANDIDATES_CSV = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_AUTHORITY_CANDIDATES.csv"
)

AUTHORITY_CONTRACT = (
    OUTPUT_ROOT
    / "edgeiq_historical_observation_v3_authority_contract.json"
)


TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".csv",
    ".txt",
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".yaml",
    ".yml",
}

PROHIBITED_MARKERS = {
    "monthly": "MONTHLY",
    "legacy": "LEGACY",
    "speed": "SPEED",
    "sectional": "SECTIONAL",
    "sectionals": "SECTIONAL",
    "live": "LIVE",
    "upcoming": "UPCOMING",
    "checkpoint": "CHECKPOINT",
    "backup": "BACKUP",
    "candidate": "CANDIDATE",
    "temporary": "TEMPORARY",
    "/tmp/": "TEMPORARY",
    "/temp/": "TEMPORARY",
}

AUTHORITY_MARKERS = {
    "graphql",
    "consolidated",
    "racingcom",
    "racing.com",
    "racing_com",
    "historical",
    "observation",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def repository_paths() -> list[str]:
    result = run_git(
        "ls-files",
        "-co",
        "--exclude-standard",
    )

    if result.returncode != 0:
        raise RuntimeError(
            "git ls-files failed:\n"
            + result.stderr.strip()
        )

    paths = {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }

    return sorted(paths, key=str.lower)


def git_evidence_lines() -> list[dict[str, Any]]:
    search_terms = [
        "879784",
        "879,784",
        "879695",
        "879,695",
        "consolidated GraphQL",
        "consolidated graphql",
        "GraphQL authority",
        "graphql authority",
        "duplicate excess",
        "89 duplicate",
    ]

    evidence: list[dict[str, Any]] = []

    for term in search_terms:
        result = run_git(
            "grep",
            "-n",
            "-I",
            "-F",
            "-e",
            term,
            "--",
            "docs",
            "scripts",
        )

        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"git grep failed for {term!r}:\n"
                + result.stderr.strip()
            )

        for line in result.stdout.splitlines():
            parts = line.split(":", 2)

            if len(parts) != 3:
                continue

            path, line_number, text = parts

            evidence.append(
                {
                    "term": term,
                    "path": path.replace("\\", "/"),
                    "line_number": int(line_number),
                    "text": text.strip(),
                }
            )

    unique: dict[tuple[str, int, str], dict[str, Any]] = {}

    for item in evidence:
        key = (
            item["path"],
            item["line_number"],
            item["text"],
        )
        unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: (
            item["path"].lower(),
            item["line_number"],
        ),
    )


def classify_path(path: str) -> tuple[list[str], list[str]]:
    text = f"/{path.replace(chr(92), '/').lower()}/"

    authority_hits = sorted(
        marker
        for marker in AUTHORITY_MARKERS
        if marker in text
    )

    prohibited_hits = sorted(
        {
            classification
            for marker, classification
            in PROHIBITED_MARKERS.items()
            if marker in text
        }
    )

    return authority_hits, prohibited_hits


def score_candidate(
    path: str,
    authority_hits: list[str],
    prohibited_hits: list[str],
    evidence_paths: set[str],
) -> int:
    text = path.lower()
    score = 0

    if "graphql" in text:
        score += 50

    if "consolidated" in text:
        score += 60

    if (
        "racingcom" in text
        or "racing.com" in text
        or "racing_com" in text
    ):
        score += 20

    if "historical" in text:
        score += 15

    if "observation" in text:
        score += 15

    if path in evidence_paths:
        score += 40

    if Path(path).suffix.lower() == ".csv":
        score += 20

    score += len(authority_hits) * 3
    score -= len(prohibited_hits) * 100

    return score


def inspect_csv_header(path: Path) -> tuple[list[str], str]:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                errors="strict",
                newline="",
            ) as handle:
                reader = csv.reader(handle)
                header = next(reader, [])
                return header, encoding
        except UnicodeDecodeError:
            continue

    with path.open(
        "r",
        encoding="cp1252",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.reader(handle)
        return next(reader, []), "cp1252-replace"


def count_csv_rows(path: Path, encoding: str) -> int:
    actual_encoding = (
        "cp1252"
        if encoding == "cp1252-replace"
        else encoding
    )

    error_mode = (
        "replace"
        if encoding == "cp1252-replace"
        else "strict"
    )

    count = 0

    with path.open(
        "r",
        encoding=actual_encoding,
        errors=error_mode,
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        next(reader, None)

        for _ in reader:
            count += 1

            if count % 250_000 == 0:
                print(
                    f"  counted {count:,} rows: "
                    f"{path.relative_to(ROOT).as_posix()}",
                    flush=True,
                )

    return count


def normalise_field(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().lower(),
    ).strip("_")


def identity_field_analysis(
    header: list[str],
) -> dict[str, Any]:
    normalised = {
        normalise_field(field): field
        for field in header
    }

    field_groups = {
        "horse_identity": {
            "horse_key",
            "horsekey",
            "source_horse_id",
            "sourcehorseid",
            "horse_id",
            "horseid",
        },
        "horse_name": {
            "horse_name",
            "horsename",
            "horse",
            "runner_name",
            "runnername",
            "runner",
        },
        "race_date": {
            "race_date",
            "racedate",
            "meeting_date",
            "meetingdate",
            "date",
        },
        "track": {
            "track",
            "track_name",
            "trackname",
            "venue",
            "meeting",
        },
        "race_number": {
            "race_number",
            "racenumber",
            "race_no",
            "raceno",
        },
        "runner_number": {
            "runner_number",
            "runnernumber",
            "saddlecloth",
            "saddlecloth_number",
            "number",
        },
    }

    matches: dict[str, list[str]] = {}

    for group, aliases in field_groups.items():
        matches[group] = sorted(
            {
                normalised[alias]
                for alias in aliases
                if alias in normalised
            }
        )

    required_groups_present = all(
        matches[group]
        for group in (
            "horse_identity",
            "race_date",
            "track",
            "race_number",
        )
    )

    return {
        "normalised_field_count": len(normalised),
        "matches": matches,
        "required_groups_present": required_groups_present,
    }


def main() -> int:
    print(RESOLVER_ID)
    print("=" * len(RESOLVER_ID))
    print()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = repository_paths()
    evidence = git_evidence_lines()

    evidence_paths = {
        item["path"]
        for item in evidence
    }

    candidates: list[dict[str, Any]] = []

    for repository_path in paths:
        suffix = Path(repository_path).suffix.lower()

        if suffix != ".csv":
            continue

        authority_hits, prohibited_hits = classify_path(
            repository_path
        )

        if not authority_hits:
            continue

        score = score_candidate(
            repository_path,
            authority_hits,
            prohibited_hits,
            evidence_paths,
        )

        if score <= 0:
            continue

        physical_path = ROOT / repository_path

        candidates.append(
            {
                "repository_path": repository_path,
                "exists": physical_path.exists(),
                "size_bytes": (
                    physical_path.stat().st_size
                    if physical_path.exists()
                    else None
                ),
                "authority_markers": authority_hits,
                "prohibited_markers": prohibited_hits,
                "evidence_reference": (
                    repository_path in evidence_paths
                ),
                "score": score,
                "header": [],
                "encoding": "",
                "data_rows": None,
                "row_contract_match": False,
                "identity_field_analysis": {},
                "inspection_error": "",
            }
        )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["repository_path"].lower(),
        )
    )

    inspection_candidates = [
        item
        for item in candidates
        if item["exists"]
        and not item["prohibited_markers"]
        and (
            "graphql" in item["authority_markers"]
            or "consolidated" in item["authority_markers"]
            or item["evidence_reference"]
        )
    ][:12]

    print(
        f"Repository paths considered: {len(paths):,}",
        flush=True,
    )
    print(
        f"Text evidence lines found: {len(evidence):,}",
        flush=True,
    )
    print(
        f"Ranked CSV candidates: {len(candidates):,}",
        flush=True,
    )
    print(
        f"CSV candidates selected for inspection: "
        f"{len(inspection_candidates):,}",
        flush=True,
    )
    print()

    for index, candidate in enumerate(
        inspection_candidates,
        start=1,
    ):
        path = ROOT / candidate["repository_path"]

        print(
            f"[{index}/{len(inspection_candidates)}] "
            f"{candidate['repository_path']}",
            flush=True,
        )

        try:
            header, encoding = inspect_csv_header(path)
            candidate["header"] = header
            candidate["encoding"] = encoding
            candidate["identity_field_analysis"] = (
                identity_field_analysis(header)
            )

            print(
                f"  header fields: {len(header):,}",
                flush=True,
            )

            data_rows = count_csv_rows(
                path,
                encoding,
            )

            candidate["data_rows"] = data_rows
            candidate["row_contract_match"] = (
                data_rows == EXPECTED_PHYSICAL_ROWS
            )

            print(
                f"  data rows: {data_rows:,}",
                flush=True,
            )
            print(
                f"  physical contract match: "
                f"{candidate['row_contract_match']}",
                flush=True,
            )

        except Exception as exc:
            candidate["inspection_error"] = (
                f"{type(exc).__name__}: {exc}"
            )

            print(
                f"  ERROR: "
                f"{candidate['inspection_error']}",
                flush=True,
            )

    authority_matches = [
        candidate
        for candidate in inspection_candidates
        if candidate["row_contract_match"]
        and not candidate["prohibited_markers"]
        and (
            "graphql" in candidate["authority_markers"]
            or "consolidated" in candidate["authority_markers"]
        )
        and candidate.get(
            "identity_field_analysis",
            {},
        ).get(
            "required_groups_present",
            False,
        )
    ]

    if len(authority_matches) == 1:
        status = PASS_STATUS
        decision = "AUTHORITY_LOCKED"
        selected_authority = authority_matches[0]

        decision_reason = (
            "Exactly one non-prohibited consolidated/GraphQL "
            "CSV matched the governed physical population and "
            "contained the minimum identity fields."
        )
    elif not authority_matches:
        status = FAIL_STATUS
        decision = "NO_AUTHORITY_PROVEN"
        selected_authority = None

        decision_reason = (
            "No candidate simultaneously matched the physical "
            "population contract, consolidated/GraphQL authority "
            "classification, prohibited-source exclusions and "
            "minimum identity schema."
        )
    else:
        status = FAIL_STATUS
        decision = "AMBIGUOUS_AUTHORITY"
        selected_authority = None

        decision_reason = (
            "Multiple candidates satisfied the authority gate. "
            "The warehouse cannot be built until one physical "
            "authority is uniquely governed."
        )

    candidate_fieldnames = [
        "repository_path",
        "score",
        "exists",
        "size_bytes",
        "authority_markers",
        "prohibited_markers",
        "evidence_reference",
        "data_rows",
        "row_contract_match",
        "header_field_count",
        "required_identity_groups_present",
        "encoding",
        "inspection_error",
    ]

    with CANDIDATES_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=candidate_fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()

        for candidate in candidates:
            analysis = candidate.get(
                "identity_field_analysis",
                {},
            )

            writer.writerow(
                {
                    "repository_path": (
                        candidate["repository_path"]
                    ),
                    "score": candidate["score"],
                    "exists": candidate["exists"],
                    "size_bytes": candidate["size_bytes"],
                    "authority_markers": "|".join(
                        candidate["authority_markers"]
                    ),
                    "prohibited_markers": "|".join(
                        candidate["prohibited_markers"]
                    ),
                    "evidence_reference": (
                        candidate["evidence_reference"]
                    ),
                    "data_rows": candidate["data_rows"],
                    "row_contract_match": (
                        candidate["row_contract_match"]
                    ),
                    "header_field_count": len(
                        candidate.get("header", [])
                    ),
                    "required_identity_groups_present": (
                        analysis.get(
                            "required_groups_present",
                            False,
                        )
                    ),
                    "encoding": candidate["encoding"],
                    "inspection_error": (
                        candidate["inspection_error"]
                    ),
                }
            )

    contract: dict[str, Any] = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
            "AUTHORITY_CONTRACT"
        ),
        "version": "1.0.0",
        "status": status,
        "decision": decision,
        "generated_at_utc": now_utc(),
        "expected_physical_rows": (
            EXPECTED_PHYSICAL_ROWS
        ),
        "expected_unique_raw_identities": (
            EXPECTED_UNIQUE_RAW_IDENTITIES
        ),
        "expected_duplicate_excess": (
            EXPECTED_DUPLICATE_EXCESS
        ),
        "selected_authority": (
            {
                "repository_path": (
                    selected_authority[
                        "repository_path"
                    ]
                ),
                "size_bytes": (
                    selected_authority["size_bytes"]
                ),
                "data_rows": (
                    selected_authority["data_rows"]
                ),
                "encoding": (
                    selected_authority["encoding"]
                ),
                "header": (
                    selected_authority["header"]
                ),
                "identity_field_analysis": (
                    selected_authority[
                        "identity_field_analysis"
                    ]
                ),
            }
            if selected_authority
            else None
        ),
        "prohibited_source_classes": sorted(
            set(PROHIBITED_MARKERS.values())
        ),
        "admission_rules": [
            (
                "exactly one physical source authority "
                "must be selected"
            ),
            (
                "authority must be consolidated GraphQL "
                "or explicitly proven equivalent"
            ),
            (
                "physical data row count must equal "
                f"{EXPECTED_PHYSICAL_ROWS}"
            ),
            (
                "monthly, legacy, speed, sectional, live, "
                "upcoming, checkpoint, backup, candidate "
                "and temporary sources are prohibited"
            ),
            (
                "minimum race and horse identity fields "
                "must exist before warehouse construction"
            ),
        ],
    }

    AUTHORITY_CONTRACT.write_text(
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report = {
        "resolver_id": RESOLVER_ID,
        "status": status,
        "decision": decision,
        "decision_reason": decision_reason,
        "generated_at_utc": now_utc(),
        "repository_paths_considered": len(paths),
        "evidence_lines": evidence,
        "candidate_count": len(candidates),
        "inspected_candidate_count": len(
            inspection_candidates
        ),
        "matching_authority_count": len(
            authority_matches
        ),
        "selected_authority": (
            selected_authority
            if selected_authority
            else None
        ),
        "expected_population_contract": {
            "physical_rows": (
                EXPECTED_PHYSICAL_ROWS
            ),
            "unique_raw_identities": (
                EXPECTED_UNIQUE_RAW_IDENTITIES
            ),
            "duplicate_excess": (
                EXPECTED_DUPLICATE_EXCESS
            ),
        },
        "candidates": candidates,
        "mutations_performed": [],
        "warehouse_written": False,
        "existing_v2_modified": False,
        "obsolete_v3_modified": False,
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    evidence_lines = []

    for item in evidence[:40]:
        evidence_lines.append(
            f"- `{item['path']}:{item['line_number']}` — "
            f"{item['text']}"
        )

    if not evidence_lines:
        evidence_lines.append(
            "- No tracked textual evidence was located."
        )

    candidate_lines = [
        "| Candidate | Rows | Score | Prohibited | "
        "Identity schema |",
        "|---|---:|---:|---|---:|",
    ]

    for candidate in inspection_candidates:
        analysis = candidate.get(
            "identity_field_analysis",
            {},
        )

        candidate_lines.append(
            "| `"
            + candidate["repository_path"]
            + "` | "
            + (
                f"{candidate['data_rows']:,}"
                if isinstance(
                    candidate["data_rows"],
                    int,
                )
                else "Not counted"
            )
            + " | "
            + str(candidate["score"])
            + " | "
            + (
                ", ".join(
                    candidate["prohibited_markers"]
                )
                or "None"
            )
            + " | "
            + str(
                analysis.get(
                    "required_groups_present",
                    False,
                )
            )
            + " |"
        )

    selected_text = (
        f"`{selected_authority['repository_path']}`"
        if selected_authority
        else "None"
    )

    report_md = "\n".join(
        [
            (
                "# EDGEIQ Historical Observation V3 "
                "Authority Resolution"
            ),
            "",
            f"**Status:** `{status}`",
            "",
            f"**Decision:** `{decision}`",
            "",
            f"**Selected authority:** {selected_text}",
            "",
            "## Decision rationale",
            "",
            decision_reason,
            "",
            "## Safety scope",
            "",
            "- No warehouse was written.",
            "- Existing V2 was not modified.",
            (
                "- The rejected untracked V3 implementation "
                "was not modified."
            ),
            (
                "- Repository file discovery used Git's "
                "index rather than recursive filesystem "
                "resolution."
            ),
            (
                "- Only highly ranked authority candidates "
                "were row-counted."
            ),
            "",
            "## Governed population contract",
            "",
            (
                f"- Physical rows: "
                f"**{EXPECTED_PHYSICAL_ROWS:,}**"
            ),
            (
                f"- Unique raw identities: "
                f"**{EXPECTED_UNIQUE_RAW_IDENTITIES:,}**"
            ),
            (
                f"- Duplicate excess: "
                f"**{EXPECTED_DUPLICATE_EXCESS:,}**"
            ),
            "",
            "## Inspected candidates",
            "",
            *candidate_lines,
            "",
            "## Repository evidence",
            "",
            *evidence_lines,
            "",
            "## Deliverables",
            "",
            f"- `{REPORT_JSON.relative_to(ROOT).as_posix()}`",
            f"- `{REPORT_MD.relative_to(ROOT).as_posix()}`",
            (
                f"- `{CANDIDATES_CSV.relative_to(ROOT).as_posix()}`"
            ),
            (
                f"- `{AUTHORITY_CONTRACT.relative_to(ROOT).as_posix()}`"
            ),
            "",
        ]
    )

    REPORT_MD.write_text(
        report_md,
        encoding="utf-8",
    )

    print()
    print(f"STATUS: {status}")
    print(f"DECISION: {decision}")
    print(
        f"MATCHING AUTHORITIES: "
        f"{len(authority_matches)}"
    )
    print(
        "SELECTED AUTHORITY: "
        + (
            selected_authority[
                "repository_path"
            ]
            if selected_authority
            else "NONE"
        )
    )
    print(
        f"REPORT: "
        f"{REPORT_MD.relative_to(ROOT).as_posix()}"
    )
    print()
    print(
        "PHASE 1A.6B AUTHORITY RESOLUTION COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
