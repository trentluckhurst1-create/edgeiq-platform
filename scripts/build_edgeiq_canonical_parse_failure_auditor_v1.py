from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import tokenize
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "builder-registry-v1-1"
OUTPUT_ROOT = REPOSITORY_ROOT / "docs" / "platform-registry-v1" / "parse-failure-auditor-v1"

REGISTRY_PATH = INPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_REGISTRY_V1_1.csv"
FAILURES_PATH = INPUT_ROOT / "EDGEIQ_CANONICAL_BUILDER_PARSE_FAILURES_V1_1.csv"

CLASSIFICATION_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_CLASSIFICATION_V1.csv"
DIRECTORY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_DIRECTORY_PROFILE_V1.csv"
ERROR_TYPES_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_ERROR_TYPES_V1.csv"
REMEDIATION_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_REMEDIATION_QUEUE_V1.csv"
SUMMARY_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_SUMMARY_V1.json"
REPORT_PATH = OUTPUT_ROOT / "EDGEIQ_CANONICAL_PARSE_FAILURE_REPORT_V1.md"

CLASSIFICATIONS = {"ACTIVE_CODE", "GENERATED", "CHECKPOINT", "ARCHIVED", "TRUNCATED", "POWERSHELL_WRAPPER", "EMBEDDED_SOURCE", "NONCANONICAL", "UNKNOWN"}
ACTIONS = {"REPAIR", "EXCLUDE", "ARCHIVE", "DELETE", "INVESTIGATE", "NONE"}
HISTORICAL_TOKENS = {"archive", "archived", "history", "historical", "legacy", "obsolete", "deprecated", "retired", "backup", "backups", "old", "superseded"}
CHECKPOINT_TOKENS = {"checkpoint", "checkpoints", "snapshot", "snapshots", "restore", "recovery", "rollback", "before_", "_before", "after_", "_after"}
GENERATED_TOKENS = {"generated", "autogen", "auto_generated", "generated_source", "materialized", "materialised", "fixture", "fixtures"}
TEMP_TOKENS = {"tmp", "temp", "temporary", "scratch", "staging", "stage"}
ACTIVE_DIRECTORY_HINTS = {"scripts", "src", "engine", "engines", "pipeline", "pipelines", "warehouse", "builders", "builder"}

@dataclass(frozen=True)
class FailureRecord:
    builder_id: str
    relative_path: str
    absolute_path: str
    directory: str
    parser_error_type: str
    parser_message: str
    parser_line: int
    parser_column: int
    observed_error_type: str
    observed_error_message: str
    observed_error_line: int
    observed_error_column: int
    file_exists: bool
    file_size_bytes: int
    modified_utc: str
    sha256: str
    classification: str
    governance_action: str
    confidence: str
    evidence: str
    priority: int

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def first_value(row: dict[str, str], names: Iterable[str], default: str = "") -> str:
    lowered = {str(k).strip().lower(): (v or "") for k, v in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default

def as_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default

def normalise_relative_path(raw: str) -> str:
    value = raw.strip().strip('"').replace("\\", "/")
    root = REPOSITORY_ROOT.as_posix().rstrip("/") + "/"
    if value.lower().startswith(root.lower()):
        value = value[len(root):]
    return value.lstrip("./")

def canonical_registry_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result = {}
    for row in rows:
        builder_id = first_value(row, ["builder_id", "id"])
        classification = first_value(row, ["classification", "builder_classification"]).upper()
        if builder_id and classification == "CANONICAL":
            result[builder_id] = row
    return result

def detect_parse_failure(path: Path) -> tuple[str, str, int, int]:
    if not path.exists():
        return "FileNotFoundError", "File does not exist", 0, 0
    try:
        with tokenize.open(path) as handle:
            source = handle.read()
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        return type(exc).__name__, str(exc), as_int(getattr(exc, "lineno", 0)), as_int(getattr(exc, "offset", 0))
    try:
        ast.parse(source, filename=str(path))
        return "NO_PARSE_FAILURE", "File parses successfully during audit", 0, 0
    except (SyntaxError, IndentationError, TabError) as exc:
        return type(exc).__name__, str(getattr(exc, "msg", str(exc))), as_int(getattr(exc, "lineno", 0)), as_int(getattr(exc, "offset", 0))
    except Exception as exc:
        return type(exc).__name__, str(exc), 0, 0

def read_text_sample(path: Path, limit: int = 120000) -> str:
    if not path.exists():
        return ""
    try:
        with tokenize.open(path) as handle:
            return handle.read(limit)
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:limit]
        except Exception:
            return ""

def file_metadata(path: Path) -> tuple[int, str, str]:
    if not path.exists():
        return 0, "", ""
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return stat.st_size, modified, digest

def classify(relative_path: str, path: Path, source: str, observed_type: str, observed_message: str) -> tuple[str, str, str, str, int]:
    path_parts = {p.lower() for p in Path(relative_path).parts}
    filename = Path(relative_path).name.lower()
    lower_source = source.lower()
    stripped = source.lstrip()
    if not path.exists():
        return "UNKNOWN", "INVESTIGATE", "HIGH", "Registry references a file that does not exist.", 2
    powershell_markers = ("$erroractionpreference", "set-strictmode", "set-location", "write-host", "join-path", "get-content", "set-content", "param(")
    powershell_hits = sum(marker in lower_source for marker in powershell_markers)
    python_markers = ("import ", "from ", "def ", "class ", "if __name__")
    python_hits = sum(marker in lower_source for marker in python_markers)
    if stripped.startswith(("$", "param(", "Set-StrictMode", "Set-Location")) or (powershell_hits >= 3 and python_hits <= 1):
        return "POWERSHELL_WRAPPER", "EXCLUDE", "HIGH", f"PowerShell markers detected in .py content ({powershell_hits} markers).", 6
    embedded_markers = ("buildersource = r'''", 'buildersource = r"""', "$buildersource = @'", "$source = @'", "set-content -literalpath", "python_source =", "script_source =")
    if any(marker in lower_source for marker in embedded_markers):
        return "EMBEDDED_SOURCE", "EXCLUDE", "HIGH", "File is a source-materialisation or embedded-source wrapper.", 7
    if path_parts & CHECKPOINT_TOKENS or any(token in filename for token in CHECKPOINT_TOKENS):
        return "CHECKPOINT", "ARCHIVE", "HIGH", "Path or filename contains checkpoint/snapshot/recovery semantics.", 5
    if path_parts & HISTORICAL_TOKENS or any(token in filename for token in HISTORICAL_TOKENS):
        return "ARCHIVED", "EXCLUDE", "HIGH", "Path or filename contains historical/archive/legacy semantics.", 8
    if path_parts & GENERATED_TOKENS or any(token in filename for token in GENERATED_TOKENS):
        return "GENERATED", "EXCLUDE", "MEDIUM", "Path or filename contains generated/materialised/fixture semantics.", 9
    if path_parts & TEMP_TOKENS or filename.startswith(("_", "~")):
        return "NONCANONICAL", "EXCLUDE", "MEDIUM", "Temporary/staging/scratch naming indicates noncanonical scope.", 10
    message_lower = observed_message.lower()
    if any(pattern in message_lower for pattern in ("unexpected eof", "unterminated string", "was never closed", "eof while scanning", "unexpected end", "incomplete input")):
        return "TRUNCATED", "REPAIR", "HIGH", f"Parser message indicates incomplete or truncated source: {observed_message}", 3
    if observed_type == "NO_PARSE_FAILURE":
        return "UNKNOWN", "INVESTIGATE", "HIGH", "Registry recorded a failure, but the live file now parses successfully.", 2
    active_hint = bool(path_parts & ACTIVE_DIRECTORY_HINTS)
    builder_name = bool(re.match(r"^(build|run|audit|check|patch|apply)_", filename))
    if active_hint and builder_name:
        return "ACTIVE_CODE", "REPAIR", "MEDIUM", "Live builder-style filename in an active source directory.", 1
    if builder_name:
        return "ACTIVE_CODE", "REPAIR", "LOW", "Builder-style filename without clear historical/generated markers.", 1
    return "UNKNOWN", "INVESTIGATE", "LOW", "No deterministic classification rule matched.", 4

def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def pct(value: int, total: int) -> float:
    return round((value / total * 100.0), 4) if total else 0.0

def main() -> int:
    registry_rows = read_csv(REGISTRY_PATH)
    failure_rows = read_csv(FAILURES_PATH)
    canonical_by_id = canonical_registry_index(registry_rows)
    records = []
    for row in failure_rows:
        builder_id = first_value(row, ["builder_id", "id"])
        if not builder_id or builder_id not in canonical_by_id:
            continue
        registry_row = canonical_by_id[builder_id]
        raw_path = first_value(row, ["relative_path", "builder_path", "path", "file", "script_path"], first_value(registry_row, ["relative_path", "builder_path", "path", "file", "script_path"]))
        relative_path = normalise_relative_path(raw_path)
        absolute_path = REPOSITORY_ROOT / Path(relative_path)
        parser_error_type = first_value(row, ["error_type", "parser_error_type", "exception_type"])
        parser_message = first_value(row, ["message", "error_message", "parser_message"])
        parser_line = as_int(first_value(row, ["line", "lineno", "parser_line"]))
        parser_column = as_int(first_value(row, ["column", "offset", "parser_column"]))
        observed_type, observed_message, observed_line, observed_column = detect_parse_failure(absolute_path)
        source = read_text_sample(absolute_path)
        size, modified, sha256 = file_metadata(absolute_path)
        classification, action, confidence, evidence, priority = classify(relative_path, absolute_path, source, observed_type, observed_message)
        if classification not in CLASSIFICATIONS or action not in ACTIONS:
            raise RuntimeError(f"Invalid classification/action for {relative_path}")
        records.append(FailureRecord(builder_id, relative_path, str(absolute_path), str(Path(relative_path).parent).replace("\\", "/"), parser_error_type, parser_message, parser_line, parser_column, observed_type, observed_message, observed_line, observed_column, absolute_path.exists(), size, modified, sha256, classification, action, confidence, evidence, priority))
    records.sort(key=lambda r: (r.priority, r.relative_path.lower()))
    total = len(records)
    expected_total = len({first_value(row, ["builder_id", "id"]) for row in failure_rows if first_value(row, ["builder_id", "id"]) in canonical_by_id})
    if total != expected_total:
        raise RuntimeError(f"Canonical failure reconciliation failed: records={total}, expected={expected_total}")
    write_csv(CLASSIFICATION_PATH, [asdict(r) for r in records], list(FailureRecord.__dataclass_fields__.keys()))
    directory_counts = Counter(r.directory for r in records)
    directory_classes = defaultdict(Counter)
    for r in records:
        directory_classes[r.directory][r.classification] += 1
    directory_rows = []
    for directory, count in sorted(directory_counts.items(), key=lambda item: (-item[1], item[0])):
        active_defects = directory_classes[directory]["ACTIVE_CODE"] + directory_classes[directory]["TRUNCATED"]
        directory_rows.append({"directory": directory, "failure_count": count, "failure_percentage": pct(count, total), "active_or_truncated_count": active_defects, "estimated_healthy_percentage": round(100.0 - pct(active_defects, count), 4), "classification_counts_json": json.dumps(dict(sorted(directory_classes[directory].items())))})
    write_csv(DIRECTORY_PATH, directory_rows, ["directory", "failure_count", "failure_percentage", "active_or_truncated_count", "estimated_healthy_percentage", "classification_counts_json"])
    error_counts = Counter(r.observed_error_type for r in records)
    error_rows = [{"observed_error_type": error_type, "failure_count": count, "failure_percentage": pct(count, total)} for error_type, count in sorted(error_counts.items(), key=lambda item: (-item[1], item[0]))]
    write_csv(ERROR_TYPES_PATH, error_rows, ["observed_error_type", "failure_count", "failure_percentage"])
    remediation_rows = [{"priority": r.priority, "builder_id": r.builder_id, "relative_path": r.relative_path, "classification": r.classification, "governance_action": r.governance_action, "confidence": r.confidence, "observed_error_type": r.observed_error_type, "observed_error_line": r.observed_error_line, "observed_error_message": r.observed_error_message, "evidence": r.evidence} for r in records]
    write_csv(REMEDIATION_PATH, remediation_rows, ["priority", "builder_id", "relative_path", "classification", "governance_action", "confidence", "observed_error_type", "observed_error_line", "observed_error_message", "evidence"])
    classification_counts = Counter(r.classification for r in records)
    action_counts = Counter(r.governance_action for r in records)
    confidence_counts = Counter(r.confidence for r in records)
    live_defect_count = classification_counts["ACTIVE_CODE"] + classification_counts["TRUNCATED"]
    canonical_builder_count = len(canonical_by_id)
    estimated_health = round(((canonical_builder_count - live_defect_count) / canonical_builder_count) * 100.0, 4) if canonical_builder_count else 0.0
    verdict = "PASS" if total and sum(classification_counts.values()) == total and sum(action_counts.values()) == total else "FAIL_RECONCILIATION"
    summary = {"schema_version": "1.0", "generated_utc": datetime.now(timezone.utc).isoformat(), "verdict": verdict, "repository_root": str(REPOSITORY_ROOT), "input_registry_path": str(REGISTRY_PATH), "input_failures_path": str(FAILURES_PATH), "canonical_builder_count": canonical_builder_count, "canonical_parse_failure_count": total, "canonical_parse_failure_percentage": pct(total, canonical_builder_count), "classification_counts": dict(sorted(classification_counts.items())), "governance_action_counts": dict(sorted(action_counts.items())), "confidence_counts": dict(sorted(confidence_counts.items())), "observed_error_type_counts": dict(sorted(error_counts.items())), "directory_count": len(directory_counts), "active_or_truncated_defect_count": live_defect_count, "estimated_canonical_platform_health_percentage": estimated_health}
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# EDGEIQ Canonical Parse Failure Auditor V1", "", "## Executive Summary", "", f"- Verdict: **{verdict}**", f"- Canonical builders: **{canonical_builder_count}**", f"- Canonical parse failures audited: **{total}**", f"- Active or truncated defects: **{live_defect_count}**", f"- Estimated canonical platform health: **{estimated_health}%**", "", "## Classification Analysis", "", "| Classification | Count | Percentage |", "|---|---:|---:|"]
    for name, count in sorted(classification_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {name} | {count} | {pct(count, total)}% |")
    lines += ["", "## Governance Actions", "", "| Action | Count | Percentage |", "|---|---:|---:|"]
    for name, count in sorted(action_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {name} | {count} | {pct(count, total)}% |")
    lines += ["", "## Leading Directories", "", "| Directory | Failures | Percentage | Active/Truncated |", "|---|---:|---:|---:|"]
    for row in directory_rows[:20]:
        lines.append(f"| `{row['directory']}` | {row['failure_count']} | {row['failure_percentage']}% | {row['active_or_truncated_count']} |")
    lines += ["", "## Error Analysis", "", "| Observed Error | Count | Percentage |", "|---|---:|---:|"]
    for row in error_rows[:20]:
        lines.append(f"| {row['observed_error_type']} | {row['failure_count']} | {row['failure_percentage']}% |")
    lines += ["", "## Remediation Plan", "", "1. Repair `ACTIVE_CODE` and `TRUNCATED` records in priority order.", "2. Investigate `UNKNOWN` records before changing canonical scope.", "3. Exclude only classifications supported by deterministic evidence.", "4. Re-run Builder Registry v1.1 after governed scope refinement.", "", "## Governance Recommendation", "", "Do not mass-edit parser failures. Use this classification as the evidence base for Canonical Scope Refiner V1.", ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("EDGEIQ CANONICAL PARSE FAILURE AUDITOR V1")
    print(f"VERDICT={verdict}")
    print(f"CANONICAL_BUILDERS={canonical_builder_count}")
    print(f"CANONICAL_PARSE_FAILURES_AUDITED={total}")
    print(f"ACTIVE_OR_TRUNCATED_DEFECTS={live_defect_count}")
    print(f"ESTIMATED_CANONICAL_HEALTH_PERCENT={estimated_health}")
    print(f"OUTPUT_ROOT={OUTPUT_ROOT}")
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
