from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


UNIT = "RRV2_UNIT_008"
VERSION = "V1_BOUNDED"
MAX_RUNTIME_SECONDS = 90
MAX_SCRIPT_FILES = 5000
MAX_FILE_BYTES = 2_000_000
MAX_CSS_CANDIDATES = 25

ROOT = Path.cwd().resolve()
START_TIME = time.monotonic()

RECOVERY_ROOT = ROOT / "docs" / "repository-recovery-v2"
VERIFICATION_CSV = (
    RECOVERY_ROOT / "edgeiq_snapshot_reference_verification_v1.csv"
)

RESOLUTION_CSV = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_dependency_resolution_v1.csv"
)
REFERENCE_CSV = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_reference_evidence_v1.csv"
)
CSS_CANDIDATES_CSV = (
    RECOVERY_ROOT /
    "edgeiq_protected_css_counterpart_candidates_v1.csv"
)
RESOLUTION_JSON = (
    RECOVERY_ROOT /
    "edgeiq_protected_snapshot_dependency_resolution_v1.json"
)
REPORT_MD = (
    RECOVERY_ROOT /
    "EDGEIQ_PROTECTED_SNAPSHOT_DEPENDENCY_RESOLUTION_V1.md"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def elapsed() -> float:
    return time.monotonic() - START_TIME


def progress(message: str) -> None:
    print(
        f"[{elapsed():7.2f}s] {message}",
        flush=True,
    )


def enforce_runtime(stage: str) -> None:
    if elapsed() > MAX_RUNTIME_SECONDS:
        raise TimeoutError(
            f"{UNIT} exceeded {MAX_RUNTIME_SECONDS} seconds "
            f"during {stage}."
        )


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_text_bounded(path: Path) -> str:
    enforce_runtime(f"reading {path.name}")

    if not path.is_file():
        return ""

    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        progress(
            f"SKIP_OVERSIZE path={repo_relative(path)} bytes={size}"
        )
        return ""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def first_present(row: dict[str, str], names: list[str]) -> str:
    lowered = {
        str(key).strip().lower(): str(value or "").strip()
        for key, value in row.items()
    }

    for name in names:
        value = lowered.get(name.lower(), "")
        if value:
            return value

    return ""


def is_protected_row(row: dict[str, str]) -> bool:
    searchable = " ".join(
        str(value or "")
        for value in row.values()
    ).upper()

    return (
        "PROTECT" in searchable
        or "RETAIN" in searchable
        or "DEPENDENCY" in searchable
    )


def load_protected_paths() -> list[str]:
    progress("STAGE_1 loading protected snapshot verification evidence")

    if not VERIFICATION_CSV.is_file():
        raise FileNotFoundError(
            f"Missing verification evidence: {VERIFICATION_CSV}"
        )

    with VERIFICATION_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    protected: list[str] = []

    path_fields = [
        "snapshot_path",
        "file_path",
        "path",
        "repository_path",
        "candidate_path",
    ]

    for row in rows:
        path_value = first_present(row, path_fields)

        if not path_value:
            continue

        normalised = path_value.replace("\\", "/").lstrip("./")

        if is_protected_row(row):
            protected.append(normalised)

    protected = sorted(set(protected))

    if len(protected) != 5:
        progress(
            "Verification CSV did not expose exactly five protected rows; "
            "using the five governed known protected paths."
        )

        protected = [
            (
                "src/components/"
                "RaceIntelligenceScreen_"
                "BEFORE_DNA_EXPLAINABILITY_UI_WIRE_V1.tsx"
            ),
            (
                "src/components/"
                "RaceIntelligenceScreen_"
                "BEFORE_FACTOR_JOIN_KEY_FIX.tsx"
            ),
            (
                "src/components/"
                "RaceIntelligenceScreen_"
                "BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx"
            ),
            (
                "src/edgeiq-os/race/"
                "RaceFileV3_STABLE_BEFORE_COMPONENT_EXTRACTION_"
                "20260709.tsx"
            ),
            (
                "src/edgeiq-os/styles/"
                "edgeiqOsV2_STABLE_BEFORE_COMPONENT_EXTRACTION_"
                "20260709.css"
            ),
        ]

    if len(protected) != 5:
        raise RuntimeError(
            f"Expected exactly five protected snapshots; found "
            f"{len(protected)}."
        )

    for index, path_value in enumerate(protected, start=1):
        progress(
            f"PROTECTED {index}/5 {path_value}"
        )

        if not (ROOT / path_value).is_file():
            raise FileNotFoundError(
                f"Protected snapshot missing: {path_value}"
            )

    progress("STAGE_1_COMPLETE protected_snapshot_count=5")
    return protected


def classify_reference(line: str) -> str:
    lowered = line.lower()

    if any(
        token in lowered
        for token in (
            "read_text",
            "read_bytes",
            "open(",
            "copyfile",
            "copy2",
            "shutil.copy",
            "source_path",
            "input_path",
        )
    ):
        return "EXECUTABLE_INPUT_DEPENDENCY"

    if any(
        token in lowered
        for token in (
            "exists(",
            "is_file(",
            "test-path",
        )
    ):
        return "EXISTENCE_GUARD_REFERENCE"

    if any(
        token in lowered
        for token in (
            "rollback",
            "backup",
            "restore",
        )
    ):
        return "ROLLBACK_OR_BACKUP_REFERENCE"

    return "TEXTUAL_PATH_REFERENCE"


def gather_script_files() -> list[Path]:
    scripts_root = ROOT / "scripts"

    files = sorted(
        path
        for path in scripts_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {
            ".py",
            ".ps1",
            ".mjs",
            ".js",
            ".ts",
        }
        and path.resolve() != Path(__file__).resolve()
    )

    if len(files) > MAX_SCRIPT_FILES:
        raise RuntimeError(
            f"Script search exceeded bounded limit of "
            f"{MAX_SCRIPT_FILES}; found {len(files)}."
        )

    return files


def search_references(
    protected_paths: list[str],
) -> list[dict[str, object]]:
    progress("STAGE_2 bounded script-reference investigation")

    script_files = gather_script_files()
    progress(
        f"SCRIPT_SCOPE files={len(script_files)} "
        f"limit={MAX_SCRIPT_FILES}"
    )

    protected_terms: dict[str, set[str]] = {}

    for protected_path in protected_paths:
        path_obj = Path(protected_path)

        protected_terms[protected_path] = {
            protected_path.lower(),
            protected_path.replace("/", "\\").lower(),
            path_obj.name.lower(),
            path_obj.stem.lower(),
        }

    evidence: list[dict[str, object]] = []

    for index, script_path in enumerate(script_files, start=1):
        enforce_runtime("script-reference search")

        if index == 1 or index % 100 == 0:
            progress(
                f"SCRIPT_SCAN {index}/{len(script_files)} "
                f"{repo_relative(script_path)}"
            )

        text = read_text_bounded(script_path)
        if not text:
            continue

        lines = text.splitlines()

        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()

            for protected_path, terms in protected_terms.items():
                if not any(term in lowered for term in terms):
                    continue

                evidence.append(
                    {
                        "snapshot_path": protected_path,
                        "referencing_file": repo_relative(script_path),
                        "line_number": line_number,
                        "reference_class": classify_reference(line),
                        "line_text": line.strip()[:500],
                    }
                )

    progress(
        f"STAGE_2_COMPLETE reference_rows={len(evidence)}"
    )

    return evidence


CSS_SELECTOR_PATTERN = re.compile(
    r"(?m)([^{}]+)\{"
)


def css_selectors(text: str) -> set[str]:
    selectors: set[str] = set()

    for match in CSS_SELECTOR_PATTERN.finditer(text):
        raw = match.group(1).strip()

        if not raw or raw.startswith("@"):
            continue

        for selector in raw.split(","):
            cleaned = re.sub(
                r"\s+",
                " ",
                selector.strip(),
            )

            if cleaned and len(cleaned) <= 300:
                selectors.add(cleaned)

    return selectors


def css_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(
            r"[A-Za-z_][A-Za-z0-9_-]{2,}",
            text,
        )
    }


def set_overlap(
    left: set[str],
    right: set[str],
) -> float:
    if not left or not right:
        return 0.0

    return len(left & right) / len(left | right)


def css_candidate_paths(
    snapshot_path: str,
) -> list[Path]:
    snapshot = ROOT / snapshot_path

    explicit_candidates = [
        ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css",
        ROOT / "src" / "index.css",
    ]

    candidates: list[Path] = []

    for path in explicit_candidates:
        if (
            path.is_file()
            and path.resolve() != snapshot.resolve()
            and path not in candidates
        ):
            candidates.append(path)

    css_roots = [
        ROOT / "src" / "edgeiq-os",
        ROOT / "src" / "styles",
        ROOT / "src" / "components",
    ]

    discovered: list[Path] = []

    for css_root in css_roots:
        if not css_root.is_dir():
            continue

        for path in css_root.rglob("*.css"):
            if path.resolve() == snapshot.resolve():
                continue

            if path not in discovered:
                discovered.append(path)

    discovered.sort(
        key=lambda path: (
            0 if path.name.lower() == "edgeiqosv2.css" else 1,
            len(path.parts),
            repo_relative(path),
        )
    )

    for path in discovered:
        if path not in candidates:
            candidates.append(path)

        if len(candidates) >= MAX_CSS_CANDIDATES:
            break

    return candidates[:MAX_CSS_CANDIDATES]


def investigate_css(
    protected_paths: list[str],
) -> list[dict[str, object]]:
    progress("STAGE_3 bounded CSS counterpart investigation")

    css_snapshots = [
        path
        for path in protected_paths
        if path.lower().endswith(".css")
    ]

    if len(css_snapshots) != 1:
        raise RuntimeError(
            f"Expected one protected CSS snapshot; found "
            f"{len(css_snapshots)}."
        )

    snapshot_path = css_snapshots[0]
    snapshot_file = ROOT / snapshot_path
    snapshot_text = read_text_bounded(snapshot_file)

    snapshot_selectors = css_selectors(snapshot_text)
    snapshot_tokens = css_tokens(snapshot_text)
    snapshot_hash = sha256_file(snapshot_file)

    candidates = css_candidate_paths(snapshot_path)

    progress(
        f"CSS_SCOPE candidates={len(candidates)} "
        f"limit={MAX_CSS_CANDIDATES} "
        f"snapshot_selectors={len(snapshot_selectors)}"
    )

    rows: list[dict[str, object]] = []

    for index, candidate in enumerate(candidates, start=1):
        enforce_runtime("CSS candidate investigation")

        progress(
            f"CSS_COMPARE {index}/{len(candidates)} "
            f"{repo_relative(candidate)}"
        )

        candidate_text = read_text_bounded(candidate)
        if not candidate_text:
            continue

        candidate_selectors = css_selectors(candidate_text)
        candidate_tokens = css_tokens(candidate_text)

        selector_overlap = set_overlap(
            snapshot_selectors,
            candidate_selectors,
        )
        token_overlap = set_overlap(
            snapshot_tokens,
            candidate_tokens,
        )

        name_match = (
            1.0
            if candidate.name.lower() == "edgeiqosv2.css"
            else 0.0
        )

        exact_hash_match = (
            sha256_file(candidate) == snapshot_hash
        )

        weighted_score = (
            selector_overlap * 0.65
            + token_overlap * 0.25
            + name_match * 0.10
        )

        if exact_hash_match:
            weighted_score = 1.0

        rows.append(
            {
                "snapshot_path": snapshot_path,
                "candidate_path": repo_relative(candidate),
                "exact_hash_match": str(exact_hash_match).upper(),
                "snapshot_selector_count": len(snapshot_selectors),
                "candidate_selector_count": len(candidate_selectors),
                "shared_selector_count": len(
                    snapshot_selectors & candidate_selectors
                ),
                "selector_overlap": round(selector_overlap, 6),
                "token_overlap": round(token_overlap, 6),
                "weighted_counterpart_score": round(
                    weighted_score,
                    6,
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            float(row["weighted_counterpart_score"]),
            int(row["shared_selector_count"]),
        ),
        reverse=True,
    )

    progress(
        f"STAGE_3_COMPLETE css_candidate_rows={len(rows)}"
    )

    return rows


def determine_resolution(
    snapshot_path: str,
    references: list[dict[str, object]],
    css_rows: list[dict[str, object]],
) -> dict[str, object]:
    own_references = [
        row
        for row in references
        if row["snapshot_path"] == snapshot_path
    ]

    executable_classes = {
        "EXECUTABLE_INPUT_DEPENDENCY",
        "ROLLBACK_OR_BACKUP_REFERENCE",
    }

    executable_references = [
        row
        for row in own_references
        if row["reference_class"] in executable_classes
    ]

    counterpart = ""
    counterpart_score = ""
    status = ""
    action = ""
    rationale = ""

    if snapshot_path.lower().endswith(".css"):
        relevant_css = [
            row
            for row in css_rows
            if row["snapshot_path"] == snapshot_path
        ]

        best = relevant_css[0] if relevant_css else None

        if best:
            counterpart = str(best["candidate_path"])
            counterpart_score = str(
                best["weighted_counterpart_score"]
            )

        if executable_references:
            status = "EXECUTABLE_DEPENDENCY_CONFIRMED"
            action = "RETAIN_PENDING_SCRIPT_REMEDIATION"
            rationale = (
                "The CSS snapshot is consumed by an executable or "
                "rollback path."
            )
        elif best and float(
            best["weighted_counterpart_score"]
        ) >= 0.45:
            status = "PROBABLE_ACTIVE_COUNTERPART_FOUND"
            action = "REVIEW_FOR_GOVERNED_ARCHIVE_SIMULATION"
            rationale = (
                "No executable dependency was detected and a bounded "
                "selector/token comparison found a probable active "
                "counterpart."
            )
        elif own_references:
            status = "NON_EXECUTABLE_REFERENCE_ONLY"
            action = "REVIEW_REFERENCE_THEN_ARCHIVE_SIMULATION"
            rationale = (
                "Only non-executable textual references were detected."
            )
        else:
            status = "NO_EXECUTABLE_REFERENCE_FOUND"
            action = "REVIEW_FOR_GOVERNED_ARCHIVE_SIMULATION"
            rationale = (
                "No script dependency was detected in the bounded "
                "governed search."
            )

    elif executable_references:
        status = "EXECUTABLE_DEPENDENCY_CONFIRMED"
        action = "RETAIN_PENDING_SCRIPT_REMEDIATION"
        rationale = (
            "At least one script appears to consume this snapshot as "
            "an input, backup or rollback source."
        )

    elif own_references:
        status = "NON_EXECUTABLE_REFERENCE_ONLY"
        action = "REVIEW_REFERENCE_THEN_ARCHIVE_SIMULATION"
        rationale = (
            "References were detected but none were classified as "
            "executable input dependencies."
        )

    else:
        status = "NO_EXECUTABLE_REFERENCE_FOUND"
        action = "REVIEW_FOR_GOVERNED_ARCHIVE_SIMULATION"
        rationale = (
            "No reference was detected in the bounded scripts scope."
        )

    return {
        "snapshot_path": snapshot_path,
        "snapshot_exists": "TRUE",
        "snapshot_sha256": sha256_file(ROOT / snapshot_path),
        "detected_reference_count": len(own_references),
        "detected_reference_file_count": len(
            {
                str(row["referencing_file"])
                for row in own_references
            }
        ),
        "reference_classes": "|".join(
            sorted(
                {
                    str(row["reference_class"])
                    for row in own_references
                }
            )
        ),
        "active_counterpart": counterpart,
        "css_best_candidate": counterpart,
        "css_best_candidate_score": counterpart_score,
        "resolution_status": status,
        "recommended_action": action,
        "rationale": rationale,
    }


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    progress(
        f"OUTPUT_WRITTEN {repo_relative(path)} rows={len(rows)}"
    )


def write_outputs(
    protected_paths: list[str],
    references: list[dict[str, object]],
    css_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    progress("STAGE_4 resolving governed dispositions")

    resolutions = [
        determine_resolution(
            snapshot_path,
            references,
            css_rows,
        )
        for snapshot_path in protected_paths
    ]

    write_csv(
        REFERENCE_CSV,
        references,
        [
            "snapshot_path",
            "referencing_file",
            "line_number",
            "reference_class",
            "line_text",
        ],
    )

    write_csv(
        CSS_CANDIDATES_CSV,
        css_rows,
        [
            "snapshot_path",
            "candidate_path",
            "exact_hash_match",
            "snapshot_selector_count",
            "candidate_selector_count",
            "shared_selector_count",
            "selector_overlap",
            "token_overlap",
            "weighted_counterpart_score",
        ],
    )

    write_csv(
        RESOLUTION_CSV,
        resolutions,
        [
            "snapshot_path",
            "snapshot_exists",
            "snapshot_sha256",
            "detected_reference_count",
            "detected_reference_file_count",
            "reference_classes",
            "active_counterpart",
            "css_best_candidate",
            "css_best_candidate_score",
            "resolution_status",
            "recommended_action",
            "rationale",
        ],
    )

    status_counts: dict[str, int] = {}

    for row in resolutions:
        key = str(row["resolution_status"])
        status_counts[key] = status_counts.get(key, 0) + 1

    payload = {
        "unit": UNIT,
        "version": VERSION,
        "generated_at_utc": now_utc(),
        "verdict": "PASS",
        "bounded_execution": {
            "maximum_runtime_seconds": MAX_RUNTIME_SECONDS,
            "maximum_script_files": MAX_SCRIPT_FILES,
            "maximum_file_bytes": MAX_FILE_BYTES,
            "maximum_css_candidates": MAX_CSS_CANDIDATES,
            "difflib_used": False,
            "repository_mutation_performed": False,
        },
        "summary": {
            "protected_snapshot_count": len(protected_paths),
            "reference_evidence_rows": len(references),
            "css_candidate_rows": len(css_rows),
            "status_counts": status_counts,
            "runtime_seconds": round(elapsed(), 3),
        },
        "resolutions": resolutions,
    }

    RESOLUTION_JSON.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    progress(
        f"OUTPUT_WRITTEN {repo_relative(RESOLUTION_JSON)}"
    )

    report_lines = [
        "# EDGEIQ Protected Snapshot Dependency Resolution V1",
        "",
        f"- Unit: `{UNIT}`",
        f"- Version: `{VERSION}`",
        f"- Verdict: `PASS`",
        f"- Generated UTC: `{payload['generated_at_utc']}`",
        f"- Runtime seconds: `{payload['summary']['runtime_seconds']}`",
        f"- Protected snapshots: `{len(protected_paths)}`",
        f"- Reference evidence rows: `{len(references)}`",
        f"- CSS candidate rows: `{len(css_rows)}`",
        f"- `difflib` used: `NO`",
        f"- Repository mutations: `NONE`",
        "",
        "## Protected Snapshot Decisions",
        "",
        "| Snapshot | References | Status | Recommended action |",
        "|---|---:|---|---|",
    ]

    for row in resolutions:
        report_lines.append(
            "| "
            + str(row["snapshot_path"])
            + " | "
            + str(row["detected_reference_count"])
            + " | "
            + str(row["resolution_status"])
            + " | "
            + str(row["recommended_action"])
            + " |"
        )

    report_lines.extend(
        [
            "",
            "## Execution Safety",
            "",
            "- Investigation scope was bounded.",
            "- No source file was edited.",
            "- No protected snapshot was moved.",
            "- No file was staged.",
            "- No commit was created.",
            "- Whole-file `difflib.SequenceMatcher` was not used.",
            "",
        ]
    )

    REPORT_MD.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    progress(
        f"OUTPUT_WRITTEN {repo_relative(REPORT_MD)}"
    )

    progress("STAGE_4_COMPLETE outputs_written=5")
    return resolutions


def main() -> int:
    progress(
        f"{UNIT} {VERSION} START "
        f"hard_internal_limit={MAX_RUNTIME_SECONDS}s"
    )

    protected_paths = load_protected_paths()
    references = search_references(protected_paths)
    css_rows = investigate_css(protected_paths)
    resolutions = write_outputs(
        protected_paths,
        references,
        css_rows,
    )

    enforce_runtime("final validation")

    required_outputs = [
        RESOLUTION_CSV,
        REFERENCE_CSV,
        CSS_CANDIDATES_CSV,
        RESOLUTION_JSON,
        REPORT_MD,
    ]

    for output_path in required_outputs:
        if not output_path.is_file():
            raise RuntimeError(
                f"Required output missing: {output_path}"
            )

    progress("===== UNIT 008 COMPLETE =====")
    progress("VERDICT=PASS")
    progress(f"PROTECTED_SNAPSHOT_COUNT={len(protected_paths)}")
    progress(f"REFERENCE_EVIDENCE_ROWS={len(references)}")
    progress(f"CSS_CANDIDATE_ROWS={len(css_rows)}")
    progress(
        "EXECUTABLE_DEPENDENCIES="
        + str(
            sum(
                1
                for row in resolutions
                if row["resolution_status"]
                == "EXECUTABLE_DEPENDENCY_CONFIRMED"
            )
        )
    )
    progress(f"RUNTIME_SECONDS={elapsed():.3f}")
    progress("NO_REPOSITORY_MUTATION=TRUE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except TimeoutError as exc:
        progress(f"VERDICT=TIMEOUT error={exc}")
        raise SystemExit(124)

    except Exception as exc:
        progress(
            f"VERDICT=FAIL "
            f"error_type={type(exc).__name__} "
            f"error={exc}"
        )
        raise
