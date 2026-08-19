from __future__ import annotations

import csv
import json
import re
import sqlite3
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DISCOVERY_ID = (
    "EDGEIQ_HISTORICAL_OBSERVATION_V3_PHYSICAL_AUTHORITY_"
    "DISCOVERY_PHASE1A_6B_0_V1"
)

PASS_STATUS = f"{DISCOVERY_ID}_PASS"
FAIL_STATUS = f"{DISCOVERY_ID}_FAIL"

EXPECTED_PHYSICAL_ROWS = 879_784
EXPECTED_UNIQUE_RAW_IDENTITIES = 879_695
EXPECTED_DUPLICATE_EXCESS = 89

ROOT = Path.cwd().absolute()

SPEC_JSON = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_"
      "CORRECTION_SPECIFICATION_V1.json"
)

SPEC_MD = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_"
      "CORRECTION_SPECIFICATION_V1.md"
)

SOURCE_POLICY = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_"
      "SOURCE_POLICY_V1.csv"
)

OUTPUT_CONTRACT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "EDGEIQ_PI_PHASE1A_5_HISTORICAL_OBSERVATION_"
      "OUTPUT_CONTRACT_V1.csv"
)

OUTPUT_ROOT = (
    ROOT
    / "docs"
    / "performance-intelligence"
    / "historical-observation-v3-physical-authority-discovery"
)

REPORT_JSON = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "PHYSICAL_AUTHORITY_DISCOVERY_REPORT.json"
)

REPORT_MD = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "PHYSICAL_AUTHORITY_DISCOVERY_REPORT.md"
)

CANDIDATES_CSV = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "PHYSICAL_AUTHORITY_CANDIDATES.csv"
)

REFERENCE_MATRIX_CSV = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "PHYSICAL_AUTHORITY_REFERENCE_MATRIX.csv"
)

PRODUCER_MATRIX_CSV = (
    OUTPUT_ROOT
    / "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
      "PHYSICAL_AUTHORITY_PRODUCER_MATRIX.csv"
)

AUTHORITY_CONTRACT = (
    OUTPUT_ROOT
    / "edgeiq_historical_observation_v3_"
      "physical_authority_contract.json"
)

DATA_SUFFIXES = {
    ".csv",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".feather",
    ".sqlite",
    ".sqlite3",
    ".db",
}

TEXT_SUFFIXES = {
    ".py",
    ".ps1",
    ".md",
    ".json",
    ".csv",
    ".txt",
    ".yaml",
    ".yml",
    ".ts",
    ".tsx",
    ".js",
}

PROHIBITED_PATH_MARKERS = {
    "monthly",
    "legacy",
    "sectional",
    "sectionals",
    "speed",
    "live",
    "upcoming",
    "checkpoint",
    "backup",
    "candidate",
    "temporary",
    "/tmp/",
    "/temp/",
}

AUTHORITY_TERMS = (
    "consolidated graphql",
    "consolidated_graphql",
    "consolidated-graphql",
    "graphql warehouse",
    "historical observation warehouse",
    "879784",
    "879,784",
    "879695",
    "879,695",
    "race_id + runner_id",
    "race_id+runner_id",
)

PATH_PATTERN = re.compile(
    r"""(?ix)
    (?:
        [A-Za-z]:[\\/]
        |
        (?:docs|data|public|src|scripts)[\\/]
    )
    [^"'`<>|\r\n]+?
    \.
    (?:csv|jsonl|ndjson|parquet|feather|sqlite3?|db)
    """
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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

    return sorted(
        {
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        },
        key=str.lower,
    )


def read_text(path: Path) -> str:
    for encoding in (
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ):
        try:
            return path.read_text(
                encoding=encoding
            )
        except UnicodeDecodeError:
            continue

    return path.read_text(
        encoding="cp1252",
        errors="replace",
    )


def load_json(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return None


def walk_json(
    value: Any,
    prefix: str = "",
) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )
            yield from walk_json(
                child,
                child_prefix,
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            yield from walk_json(
                child,
                child_prefix,
            )

    else:
        yield prefix, value


def normalise_repository_path(
    raw_path: str,
) -> str | None:
    cleaned = (
        raw_path.strip()
        .strip("'\"`")
        .replace("\\", "/")
    )

    cleaned = re.sub(
        r"[),.;:\]}]+$",
        "",
        cleaned,
    )

    root_text = ROOT.as_posix().lower()

    if cleaned.lower().startswith(root_text):
        cleaned = cleaned[len(ROOT.as_posix()):]
        cleaned = cleaned.lstrip("/")

    if re.match(
        r"^[A-Za-z]:/",
        cleaned,
    ):
        return None

    return cleaned or None


def paths_from_text(
    text: str,
) -> set[str]:
    found: set[str] = set()

    for match in PATH_PATTERN.finditer(text):
        path = normalise_repository_path(
            match.group(0)
        )

        if path:
            found.add(path)

    return found


def collect_spec_references() -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []

    for source_path in (
        SPEC_JSON,
        SPEC_MD,
        SOURCE_POLICY,
        OUTPUT_CONTRACT,
    ):
        if not source_path.exists():
            continue

        text = read_text(source_path)

        for candidate_path in sorted(
            paths_from_text(text),
            key=str.lower,
        ):
            references.append(
                {
                    "source_document": relative(source_path),
                    "reference_type": "EXPLICIT_DATA_PATH",
                    "reference": candidate_path,
                    "context": "",
                }
            )

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            lower = line.lower()

            if any(
                term in lower
                for term in AUTHORITY_TERMS
            ):
                references.append(
                    {
                        "source_document": relative(
                            source_path
                        ),
                        "reference_type": (
                            "AUTHORITY_EVIDENCE"
                        ),
                        "reference": "",
                        "context": (
                            f"line {line_number}: "
                            f"{line.strip()}"
                        ),
                    }
                )

    payload = load_json(SPEC_JSON)

    if payload is not None:
        for json_path, value in walk_json(payload):
            if not isinstance(value, str):
                continue

            value_paths = paths_from_text(value)

            for candidate_path in sorted(
                value_paths,
                key=str.lower,
            ):
                references.append(
                    {
                        "source_document": relative(
                            SPEC_JSON
                        ),
                        "reference_type": (
                            "JSON_DATA_PATH"
                        ),
                        "reference": candidate_path,
                        "context": json_path,
                    }
                )

            lower = value.lower()

            if any(
                term in lower
                for term in AUTHORITY_TERMS
            ):
                references.append(
                    {
                        "source_document": relative(
                            SPEC_JSON
                        ),
                        "reference_type": (
                            "JSON_AUTHORITY_EVIDENCE"
                        ),
                        "reference": "",
                        "context": (
                            f"{json_path}={value}"
                        ),
                    }
                )

    unique: dict[
        tuple[str, str, str, str],
        dict[str, Any],
    ] = {}

    for item in references:
        key = (
            item["source_document"],
            item["reference_type"],
            item["reference"],
            item["context"],
        )
        unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: (
            item["source_document"].lower(),
            item["reference_type"],
            item["reference"].lower(),
            item["context"].lower(),
        ),
    )


def collect_git_evidence() -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []

    for term in AUTHORITY_TERMS:
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
            "src",
        )

        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"git grep failed for {term!r}:\n"
                + result.stderr.strip()
            )

        for raw_line in result.stdout.splitlines():
            parts = raw_line.split(":", 2)

            if len(parts) != 3:
                continue

            path, line_number, line = parts

            evidence.append(
                {
                    "term": term,
                    "path": path.replace("\\", "/"),
                    "line_number": int(line_number),
                    "line": line.strip(),
                    "referenced_paths": sorted(
                        paths_from_text(line),
                        key=str.lower,
                    ),
                }
            )

    unique: dict[
        tuple[str, int, str],
        dict[str, Any],
    ] = {}

    for item in evidence:
        key = (
            item["path"],
            item["line_number"],
            item["line"],
        )
        unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: (
            item["path"].lower(),
            item["line_number"],
        ),
    )


def prohibited_markers(
    repository_path: str,
) -> list[str]:
    text = (
        "/"
        + repository_path.replace(
            "\\",
            "/",
        ).lower()
        + "/"
    )

    return sorted(
        marker
        for marker in PROHIBITED_PATH_MARKERS
        if marker in text
    )


def likely_authority_score(
    repository_path: str,
    size_bytes: int,
    reference_counts: Counter[str],
    producer_reference_counts: Counter[str],
) -> int:
    text = repository_path.lower()
    score = 0

    score += reference_counts[repository_path] * 100
    score += producer_reference_counts[repository_path] * 40

    if "consolidated" in text:
        score += 80

    if "graphql" in text:
        score += 70

    if "historical" in text:
        score += 35

    if "observation" in text:
        score += 35

    if "warehouse" in text:
        score += 35

    if "performance" in text:
        score += 10

    if size_bytes >= 50_000_000:
        score += 40
    elif size_bytes >= 10_000_000:
        score += 25
    elif size_bytes >= 1_000_000:
        score += 10

    score -= len(
        prohibited_markers(repository_path)
    ) * 150

    return score


def inspect_csv(
    path: Path,
    count_rows: bool,
) -> dict[str, Any]:
    selected_encoding = ""
    header: list[str] = []

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
                header = next(
                    csv.reader(handle),
                    [],
                )
            selected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if not selected_encoding:
        selected_encoding = "cp1252"

        with path.open(
            "r",
            encoding=selected_encoding,
            errors="replace",
            newline="",
        ) as handle:
            header = next(
                csv.reader(handle),
                [],
            )

    data_rows: int | None = None

    if count_rows:
        data_rows = 0

        with path.open(
            "r",
            encoding=selected_encoding,
            errors="replace",
            newline="",
        ) as handle:
            reader = csv.reader(handle)
            next(reader, None)

            for _ in reader:
                data_rows += 1

                if data_rows % 250_000 == 0:
                    print(
                        f"    counted {data_rows:,} rows",
                        flush=True,
                    )

    return {
        "format": "CSV",
        "encoding": selected_encoding,
        "header": header,
        "data_rows": data_rows,
        "table_name": "",
    }


def inspect_json_lines(
    path: Path,
    count_rows: bool,
) -> dict[str, Any]:
    first_object: dict[str, Any] = {}
    data_rows: int | None = None

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as handle:
        for line in handle:
            if not line.strip():
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                value = {}

            if isinstance(value, dict):
                first_object = value
            break

    if count_rows:
        data_rows = 0

        with path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            for line in handle:
                if line.strip():
                    data_rows += 1

                    if data_rows % 250_000 == 0:
                        print(
                            f"    counted {data_rows:,} rows",
                            flush=True,
                        )

    return {
        "format": "JSON_LINES",
        "encoding": "utf-8",
        "header": list(first_object.keys()),
        "data_rows": data_rows,
        "table_name": "",
    }


def inspect_sqlite(
    path: Path,
) -> dict[str, Any]:
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        tables = [
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]

        table_results: list[dict[str, Any]] = []

        for table in tables:
            safe_table = table.replace(
                '"',
                '""',
            )

            count = connection.execute(
                f'SELECT COUNT(*) FROM "{safe_table}"'
            ).fetchone()[0]

            columns = [
                row[1]
                for row in connection.execute(
                    f'PRAGMA table_info("{safe_table}")'
                )
            ]

            table_results.append(
                {
                    "table": table,
                    "rows": count,
                    "columns": columns,
                }
            )

        best = max(
            table_results,
            key=lambda item: item["rows"],
            default={
                "table": "",
                "rows": None,
                "columns": [],
            },
        )

        return {
            "format": "SQLITE",
            "encoding": "",
            "header": best["columns"],
            "data_rows": best["rows"],
            "table_name": best["table"],
            "tables": table_results,
        }

    finally:
        connection.close()


def inspect_parquet_or_feather(
    path: Path,
) -> dict[str, Any]:
    try:
        import pyarrow.feather as feather
        import pyarrow.parquet as parquet
    except ImportError as exc:
        return {
            "format": path.suffix.lower().lstrip(".").upper(),
            "encoding": "",
            "header": [],
            "data_rows": None,
            "table_name": "",
            "inspection_error": (
                f"PyArrow unavailable: {exc}"
            ),
        }

    if path.suffix.lower() == ".parquet":
        metadata = parquet.read_metadata(path)

        return {
            "format": "PARQUET",
            "encoding": "",
            "header": metadata.schema.names,
            "data_rows": metadata.num_rows,
            "table_name": "",
        }

    table = feather.read_table(
        path,
        memory_map=True,
    )

    return {
        "format": "FEATHER",
        "encoding": "",
        "header": table.column_names,
        "data_rows": table.num_rows,
        "table_name": "",
    }


def normalise_column(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().lower(),
    ).strip("_")


def schema_analysis(
    fields: list[str],
) -> dict[str, Any]:
    normalised = {
        normalise_column(field): field
        for field in fields
    }

    aliases = {
        "race_id": {
            "race_id",
            "raceid",
            "source_race_id",
            "graphql_race_id",
        },
        "runner_id": {
            "runner_id",
            "runnerid",
            "source_runner_id",
            "graphql_runner_id",
        },
        "horse_id": {
            "horse_id",
            "horseid",
            "horse_key",
            "horsekey",
        },
        "horse_name": {
            "horse",
            "horse_name",
            "horsename",
            "runner",
            "runner_name",
            "runnername",
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
            "runner_no",
            "saddlecloth",
            "number",
        },
    }

    matches: dict[str, list[str]] = {}

    for group, group_aliases in aliases.items():
        matches[group] = sorted(
            {
                normalised[alias]
                for alias in group_aliases
                if alias in normalised
            }
        )

    raw_identity_pair_present = bool(
        matches["race_id"]
        and matches["runner_id"]
    )

    fallback_identity_present = bool(
        matches["horse_id"]
        and matches["race_date"]
        and matches["track"]
        and matches["race_number"]
    )

    return {
        "matches": matches,
        "raw_identity_pair_present": (
            raw_identity_pair_present
        ),
        "fallback_identity_present": (
            fallback_identity_present
        ),
        "authority_identity_schema_present": (
            raw_identity_pair_present
            or fallback_identity_present
        ),
    }


def inspect_candidate(
    path: Path,
    count_rows: bool,
) -> dict[str, Any]:
    suffix = path.suffix.lower()

    try:
        if suffix == ".csv":
            result = inspect_csv(
                path,
                count_rows=count_rows,
            )

        elif suffix in {
            ".jsonl",
            ".ndjson",
        }:
            result = inspect_json_lines(
                path,
                count_rows=count_rows,
            )

        elif suffix in {
            ".sqlite",
            ".sqlite3",
            ".db",
        }:
            result = inspect_sqlite(path)

        elif suffix in {
            ".parquet",
            ".feather",
        }:
            result = inspect_parquet_or_feather(
                path
            )

        else:
            result = {
                "format": suffix,
                "encoding": "",
                "header": [],
                "data_rows": None,
                "table_name": "",
                "inspection_error": (
                    "Unsupported format"
                ),
            }

    except Exception as exc:
        result = {
            "format": suffix,
            "encoding": "",
            "header": [],
            "data_rows": None,
            "table_name": "",
            "inspection_error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    result.setdefault(
        "inspection_error",
        "",
    )

    result["schema_analysis"] = schema_analysis(
        result.get("header", [])
    )

    return result


def collect_producer_references(
    paths: list[str],
) -> tuple[
    list[dict[str, Any]],
    Counter[str],
]:
    producer_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    data_basenames = {
        Path(path).name: path
        for path in paths
        if Path(path).suffix.lower()
        in DATA_SUFFIXES
    }

    for repository_path in paths:
        path = ROOT / repository_path

        if (
            not path.exists()
            or path.suffix.lower()
            not in {".py", ".ps1"}
        ):
            continue

        text = read_text(path)
        lower = text.lower()

        if not any(
            marker in lower
            for marker in (
                "879784",
                "879,784",
                "879695",
                "879,695",
                "consolidated",
                "graphql",
                "historical_observation",
                "historical-observation",
            )
        ):
            continue

        referenced = set(
            paths_from_text(text)
        )

        for basename, full_path in data_basenames.items():
            if basename in text:
                referenced.add(full_path)

        for referenced_path in sorted(
            referenced,
            key=str.lower,
        ):
            counts[referenced_path] += 1

            producer_rows.append(
                {
                    "script_path": repository_path,
                    "referenced_data_path": (
                        referenced_path
                    ),
                    "writes_data": bool(
                        re.search(
                            r"(write_text|writerow|"
                            r"to_csv|write_csv|"
                            r"write_table|to_parquet|"
                            r"sqlite3\.connect|"
                            r"open\s*\([^)]*[\"']w)",
                            text,
                            flags=re.IGNORECASE,
                        )
                    ),
                    "authority_language": bool(
                        re.search(
                            r"(consolidated.{0,80}graphql|"
                            r"graphql.{0,80}consolidated|"
                            r"879.?784|879.?695)",
                            text,
                            flags=re.IGNORECASE
                            | re.DOTALL,
                        )
                    ),
                }
            )

    unique: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    for item in producer_rows:
        key = (
            item["script_path"],
            item["referenced_data_path"],
        )
        unique[key] = item

    rows = sorted(
        unique.values(),
        key=lambda item: (
            item["referenced_data_path"].lower(),
            item["script_path"].lower(),
        ),
    )

    return rows, counts


def main() -> int:
    print(DISCOVERY_ID)
    print("=" * len(DISCOVERY_ID))
    print()

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = repository_paths()
    path_set = set(paths)

    print(
        f"Repository paths indexed by Git: "
        f"{len(paths):,}",
        flush=True,
    )

    spec_references = collect_spec_references()
    git_evidence = collect_git_evidence()

    explicit_reference_counts: Counter[str] = Counter()

    for item in spec_references:
        reference = item["reference"]

        if reference:
            explicit_reference_counts[
                reference
            ] += 1

    for item in git_evidence:
        for reference in item[
            "referenced_paths"
        ]:
            explicit_reference_counts[
                reference
            ] += 1

    producer_rows, producer_counts = (
        collect_producer_references(paths)
    )

    data_files: list[dict[str, Any]] = []

    for repository_path in paths:
        path = ROOT / repository_path
        suffix = path.suffix.lower()

        if (
            suffix not in DATA_SUFFIXES
            or not path.exists()
            or not path.is_file()
        ):
            continue

        size_bytes = path.stat().st_size

        score = likely_authority_score(
            repository_path,
            size_bytes,
            explicit_reference_counts,
            producer_counts,
        )

        data_files.append(
            {
                "repository_path": (
                    repository_path
                ),
                "suffix": suffix,
                "size_bytes": size_bytes,
                "explicit_reference_count": (
                    explicit_reference_counts[
                        repository_path
                    ]
                ),
                "producer_reference_count": (
                    producer_counts[
                        repository_path
                    ]
                ),
                "prohibited_markers": (
                    prohibited_markers(
                        repository_path
                    )
                ),
                "score": score,
                "inspection": {},
            }
        )

    data_files.sort(
        key=lambda item: (
            -item["score"],
            -item["size_bytes"],
            item["repository_path"].lower(),
        )
    )

    likely_candidates = [
        item
        for item in data_files
        if not item["prohibited_markers"]
        and (
            item["explicit_reference_count"] > 0
            or item["producer_reference_count"] > 0
            or item["score"] >= 70
            or item["size_bytes"] >= 25_000_000
        )
    ][:30]

    print(
        f"Physical data files found: "
        f"{len(data_files):,}",
        flush=True,
    )
    print(
        f"Candidates selected for inspection: "
        f"{len(likely_candidates):,}",
        flush=True,
    )
    print()

    for index, candidate in enumerate(
        likely_candidates,
        start=1,
    ):
        path = ROOT / candidate[
            "repository_path"
        ]

        count_rows = bool(
            candidate["explicit_reference_count"]
            or candidate[
                "producer_reference_count"
            ]
            or candidate["score"] >= 70
            or candidate["size_bytes"]
            >= 25_000_000
        )

        print(
            f"[{index}/{len(likely_candidates)}] "
            f"{candidate['repository_path']}",
            flush=True,
        )
        print(
            f"    size: "
            f"{candidate['size_bytes']:,} bytes",
            flush=True,
        )
        print(
            f"    explicit references: "
            f"{candidate['explicit_reference_count']}",
            flush=True,
        )
        print(
            f"    producer references: "
            f"{candidate['producer_reference_count']}",
            flush=True,
        )

        inspection = inspect_candidate(
            path,
            count_rows=count_rows,
        )

        candidate["inspection"] = inspection

        print(
            f"    format: "
            f"{inspection.get('format', '')}",
            flush=True,
        )
        print(
            f"    fields: "
            f"{len(inspection.get('header', [])):,}",
            flush=True,
        )
        print(
            f"    rows: "
            f"{inspection.get('data_rows')}",
            flush=True,
        )
        print(
            f"    identity schema: "
            f"{inspection['schema_analysis']['authority_identity_schema_present']}",
            flush=True,
        )

        if inspection.get(
            "inspection_error"
        ):
            print(
                f"    inspection error: "
                f"{inspection['inspection_error']}",
                flush=True,
            )

    proven_candidates: list[
        dict[str, Any]
    ] = []

    probable_candidates: list[
        dict[str, Any]
    ] = []

    for candidate in likely_candidates:
        inspection = candidate[
            "inspection"
        ]

        row_match = (
            inspection.get("data_rows")
            == EXPECTED_PHYSICAL_ROWS
        )

        identity_match = inspection[
            "schema_analysis"
        ][
            "authority_identity_schema_present"
        ]

        directly_referenced = (
            candidate[
                "explicit_reference_count"
            ] > 0
        )

        upstream_referenced = (
            candidate[
                "producer_reference_count"
            ] > 0
        )

        if (
            row_match
            and identity_match
            and directly_referenced
            and not candidate[
                "prohibited_markers"
            ]
        ):
            proven_candidates.append(
                candidate
            )

        elif (
            row_match
            and identity_match
            and upstream_referenced
            and not candidate[
                "prohibited_markers"
            ]
        ):
            probable_candidates.append(
                candidate
            )

    if len(proven_candidates) == 1:
        status = PASS_STATUS
        decision = "PHYSICAL_AUTHORITY_PROVEN"
        selected = proven_candidates[0]

        decision_reason = (
            "Exactly one physical dataset is explicitly "
            "referenced by governed architecture evidence, "
            "contains the required identity schema and has "
            "exactly 879,784 physical rows."
        )

    elif (
        not proven_candidates
        and len(probable_candidates) == 1
    ):
        status = FAIL_STATUS
        decision = "PROBABLE_AUTHORITY_REQUIRES_LOCK"
        selected = probable_candidates[0]

        decision_reason = (
            "Exactly one physical dataset matches the row "
            "and identity contracts and is referenced by an "
            "upstream script, but the locked Phase 1A.5 "
            "documents do not explicitly identify its path."
        )

    elif (
        len(proven_candidates) > 1
        or len(probable_candidates) > 1
    ):
        status = FAIL_STATUS
        decision = "AMBIGUOUS_PHYSICAL_AUTHORITY"
        selected = None

        decision_reason = (
            "Multiple physical datasets satisfy the row and "
            "identity requirements. Source lineage must "
            "distinguish the upstream consolidated GraphQL "
            "authority from downstream derived warehouses."
        )

    else:
        status = FAIL_STATUS
        decision = "PHYSICAL_AUTHORITY_NOT_FOUND"
        selected = None

        decision_reason = (
            "No physical repository dataset was proven to "
            "simultaneously contain 879,784 rows, the required "
            "raw identity schema and governed source lineage."
        )

    with REFERENCE_MATRIX_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "source_document",
            "reference_type",
            "reference",
            "context",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            spec_references
        )

    with PRODUCER_MATRIX_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fieldnames = [
            "script_path",
            "referenced_data_path",
            "writes_data",
            "authority_language",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            producer_rows
        )

    candidate_fieldnames = [
        "repository_path",
        "suffix",
        "size_bytes",
        "score",
        "explicit_reference_count",
        "producer_reference_count",
        "prohibited_markers",
        "format",
        "table_name",
        "data_rows",
        "field_count",
        "raw_identity_pair_present",
        "fallback_identity_present",
        "authority_identity_schema_present",
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

        for candidate in data_files:
            inspection = candidate.get(
                "inspection",
                {},
            )

            schema = inspection.get(
                "schema_analysis",
                {},
            )

            writer.writerow(
                {
                    "repository_path": (
                        candidate[
                            "repository_path"
                        ]
                    ),
                    "suffix": candidate[
                        "suffix"
                    ],
                    "size_bytes": candidate[
                        "size_bytes"
                    ],
                    "score": candidate[
                        "score"
                    ],
                    "explicit_reference_count": (
                        candidate[
                            "explicit_reference_count"
                        ]
                    ),
                    "producer_reference_count": (
                        candidate[
                            "producer_reference_count"
                        ]
                    ),
                    "prohibited_markers": "|".join(
                        candidate[
                            "prohibited_markers"
                        ]
                    ),
                    "format": inspection.get(
                        "format",
                        "",
                    ),
                    "table_name": inspection.get(
                        "table_name",
                        "",
                    ),
                    "data_rows": inspection.get(
                        "data_rows",
                        "",
                    ),
                    "field_count": len(
                        inspection.get(
                            "header",
                            [],
                        )
                    ),
                    "raw_identity_pair_present": (
                        schema.get(
                            "raw_identity_pair_present",
                            "",
                        )
                    ),
                    "fallback_identity_present": (
                        schema.get(
                            "fallback_identity_present",
                            "",
                        )
                    ),
                    "authority_identity_schema_present": (
                        schema.get(
                            "authority_identity_schema_present",
                            "",
                        )
                    ),
                    "inspection_error": inspection.get(
                        "inspection_error",
                        "",
                    ),
                }
            )

    selected_payload = None

    if selected:
        inspection = selected[
            "inspection"
        ]

        selected_payload = {
            "repository_path": selected[
                "repository_path"
            ],
            "format": inspection.get(
                "format"
            ),
            "table_name": inspection.get(
                "table_name"
            ),
            "size_bytes": selected[
                "size_bytes"
            ],
            "data_rows": inspection.get(
                "data_rows"
            ),
            "header": inspection.get(
                "header",
                [],
            ),
            "schema_analysis": inspection[
                "schema_analysis"
            ],
            "explicit_reference_count": (
                selected[
                    "explicit_reference_count"
                ]
            ),
            "producer_reference_count": (
                selected[
                    "producer_reference_count"
                ]
            ),
        }

    contract = {
        "contract_id": (
            "EDGEIQ_HISTORICAL_OBSERVATION_V3_"
            "PHYSICAL_AUTHORITY_CONTRACT_V1"
        ),
        "status": status,
        "decision": decision,
        "generated_at_utc": now_utc(),
        "selected_authority": (
            selected_payload
        ),
        "population_contract": {
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
        "warehouse_build_authorised": (
            decision
            == "PHYSICAL_AUTHORITY_PROVEN"
        ),
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
        "discovery_id": DISCOVERY_ID,
        "status": status,
        "decision": decision,
        "decision_reason": decision_reason,
        "generated_at_utc": now_utc(),
        "repository_path_count": len(
            paths
        ),
        "physical_data_file_count": len(
            data_files
        ),
        "inspected_candidate_count": len(
            likely_candidates
        ),
        "proven_candidate_count": len(
            proven_candidates
        ),
        "probable_candidate_count": len(
            probable_candidates
        ),
        "selected_authority": (
            selected_payload
        ),
        "specification_references": (
            spec_references
        ),
        "git_evidence": git_evidence,
        "producer_references": (
            producer_rows
        ),
        "inspected_candidates": (
            likely_candidates
        ),
        "warehouse_written": False,
        "existing_v2_modified": False,
        "rejected_v3_modified": False,
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

    candidate_lines = [
        "| Physical dataset | Rows | "
        "Fields | Direct refs | Producer refs | "
        "Identity |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for candidate in likely_candidates:
        inspection = candidate[
            "inspection"
        ]

        candidate_lines.append(
            "| `"
            + candidate[
                "repository_path"
            ]
            + "` | "
            + (
                f"{inspection['data_rows']:,}"
                if isinstance(
                    inspection.get(
                        "data_rows"
                    ),
                    int,
                )
                else "Not proven"
            )
            + " | "
            + str(
                len(
                    inspection.get(
                        "header",
                        [],
                    )
                )
            )
            + " | "
            + str(
                candidate[
                    "explicit_reference_count"
                ]
            )
            + " | "
            + str(
                candidate[
                    "producer_reference_count"
                ]
            )
            + " | "
            + str(
                inspection[
                    "schema_analysis"
                ][
                    "authority_identity_schema_present"
                ]
            )
            + " |"
        )

    selected_text = (
        f"`{selected['repository_path']}`"
        if selected
        else "None"
    )

    report_md = "\n".join(
        [
            (
                "# EDGEIQ Historical Observation V3 "
                "Physical Authority Discovery"
            ),
            "",
            f"**Status:** `{status}`",
            "",
            f"**Decision:** `{decision}`",
            "",
            (
                f"**Selected physical authority:** "
                f"{selected_text}"
            ),
            "",
            "## Decision rationale",
            "",
            decision_reason,
            "",
            "## Governed contract",
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
            "## Safety",
            "",
            "- No warehouse was written.",
            "- Existing V2 was not modified.",
            (
                "- The rejected untracked V3 "
                "implementation was not modified."
            ),
            (
                "- Repository discovery was limited to "
                "Git-indexed and visible untracked paths."
            ),
            "",
            "## Inspected physical candidates",
            "",
            *candidate_lines,
            "",
            "## Result",
            "",
            (
                "Phase 1A.6B warehouse construction is "
                + (
                    "**authorised**."
                    if decision
                    == "PHYSICAL_AUTHORITY_PROVEN"
                    else "**not yet authorised**."
                )
            ),
            "",
            "## Deliverables",
            "",
            f"- `{relative(REPORT_JSON)}`",
            f"- `{relative(REPORT_MD)}`",
            f"- `{relative(CANDIDATES_CSV)}`",
            f"- `{relative(REFERENCE_MATRIX_CSV)}`",
            f"- `{relative(PRODUCER_MATRIX_CSV)}`",
            f"- `{relative(AUTHORITY_CONTRACT)}`",
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
        "SELECTED PHYSICAL AUTHORITY: "
        + (
            selected[
                "repository_path"
            ]
            if selected
            else "NONE"
        )
    )
    print(
        f"PROVEN CANDIDATES: "
        f"{len(proven_candidates)}"
    )
    print(
        f"PROBABLE CANDIDATES: "
        f"{len(probable_candidates)}"
    )
    print(
        f"REPORT: {relative(REPORT_MD)}"
    )
    print()
    print(
        "PHASE 1A.6B.0 PHYSICAL AUTHORITY "
        "DISCOVERY COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
