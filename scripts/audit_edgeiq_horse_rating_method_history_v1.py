
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "horse-performance-rating" / "method-governance"
DOC_DIR.mkdir(parents=True, exist_ok=True)

OUT_REPO = DOC_DIR / "edgeiq_horse_rating_method_repository_evidence_v1.csv"
OUT_GIT = DOC_DIR / "edgeiq_horse_rating_method_git_evidence_v1.csv"
OUT_CANDIDATES = DOC_DIR / "edgeiq_horse_rating_method_historical_candidates_v1.csv"
OUT_CONFLICTS = DOC_DIR / "edgeiq_horse_rating_method_conflicts_v1.csv"
OUT_REPORT = DOC_DIR / "edgeiq_horse_rating_method_recovery_report_v1.md"

TERMS = [
    "performance_normalisation_parameter",
    "horse_performance_aggregation_parameter",
    "horse_performance_identity_map",
    "DIRECT_HISTORICAL_AGGREGATE_VALUE",
    "ROLLING_HORSE_AS_OF_DATE_RATING_FACT",
    "normalisation method",
    "normalization method",
    "aggregate value",
    "horse rating aggregation",
    "recency weighting",
    "surface normalisation",
    "distance normalisation",
    "class normalisation",
    "as-of-date rating",
]

MISSING_FILES = [
    "config/performance-intelligence/edgeiq_performance_normalisation_parameter_source_v1.csv",
    "config/performance-intelligence/edgeiq_horse_performance_aggregation_parameter_source_v1.csv",
    "config/performance-intelligence/edgeiq_horse_performance_identity_map_v1.csv",
]

SCAN_DIRS = ["scripts", "contracts", "config", "docs/performance-intelligence/horse-performance-rating"]
MAX_BYTES = 900_000


def run_git(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def text(value: object) -> str:
    return str(value if value is not None else "").strip()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def classify(path: str, line: str) -> str:
    low = (path + " " + line).casefold()
    if path.startswith("contracts/"):
        return "ACTIVE_GOVERNED_CONTRACT"
    if path.startswith("scripts/build_"):
        return "ACTIVE_CODE_SEMANTICS"
    if path.startswith("config/") and "source_v1.csv" in path:
        return "HISTORICAL_GOVERNED_SOURCE"
    if path.startswith("scripts/"):
        return "HISTORICAL_CODE_SEMANTICS" if "historical" in low or "archive" in low else "ACTIVE_CODE_SEMANTICS"
    if "audit" in low or "report" in low:
        return "AUDIT_EVIDENCE"
    if "test" in low or "fixture" in low:
        return "TEST_FIXTURE"
    if path.endswith(".md") or path.endswith(".txt"):
        return "DOCUMENTATION_ONLY"
    return "UNSUPPORTED_REFERENCE"

repo_rows: list[dict[str, object]] = []
for base in SCAN_DIRS:
    root = ROOT / base
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", "node_modules", ".git"} for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        lower = content.casefold()
        for term in TERMS:
            if term.casefold() in lower:
                first = ""
                for idx, line in enumerate(content.splitlines(), start=1):
                    if term.casefold() in line.casefold():
                        first = f"{idx}: {line.strip()[:220]}"
                        break
                repo_rows.append({
                    "term": term,
                    "file_path": rel,
                    "evidence_classification": classify(rel, first),
                    "line_evidence": first,
                    "file_size_bytes": path.stat().st_size,
                })

git_rows: list[dict[str, object]] = []
for file_path in MISSING_FILES:
    code, out, err = run_git(["log", "--all", "--name-status", "--pretty=format:%H%x09%ad%x09%s", "--date=iso-strict", "--", file_path], timeout=60)
    if out.strip():
        current_commit = ""
        current_date = ""
        current_subject = ""
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3 and len(parts[0]) == 40:
                current_commit, current_date, current_subject = parts[0], parts[1], "\t".join(parts[2:])
            elif parts and parts[0] in {"A", "M", "D", "R100", "R099", "R"}:
                git_rows.append({
                    "search_target": file_path,
                    "commit": current_commit,
                    "commit_date": current_date,
                    "subject": current_subject,
                    "name_status": line,
                    "evidence_classification": "HISTORICAL_GOVERNED_SOURCE",
                })
    else:
        git_rows.append({
            "search_target": file_path,
            "commit": "",
            "commit_date": "",
            "subject": "",
            "name_status": "NO_GIT_PATH_HISTORY_FOUND",
            "evidence_classification": "UNSUPPORTED_REFERENCE",
        })

# Capped commit-subject semantic evidence. Full pickaxe across this repository is resource-heavy;
# source-file recoverability is decided from path history plus active code/contract evidence.
code, out, err = run_git(["log", "--all", "--pretty=format:%H%x09%ad%x09%s", "--date=iso-strict", "--max-count=300"], timeout=30)
if out.strip():
    for line in out.splitlines():
        low = line.casefold()
        for term in TERMS:
            if term.casefold() in low:
                parts = line.split("\t")
                if len(parts) >= 3:
                    git_rows.append({
                        "search_target": term,
                        "commit": parts[0],
                        "commit_date": parts[1],
                        "subject": "\t".join(parts[2:]),
                        "name_status": "COMMIT_SUBJECT_MATCH",
                        "evidence_classification": "HISTORICAL_CODE_SEMANTICS",
                    })

candidate_rows: list[dict[str, object]] = []
for source_file in MISSING_FILES:
    rel = source_file.replace("\\", "/")
    path = ROOT / rel
    candidate_rows.append({
        "candidate_file": rel,
        "active_exists": "YES" if path.exists() else "NO",
        "git_path_history_found": "YES" if any(r["search_target"] == rel and r["evidence_classification"] == "HISTORICAL_GOVERNED_SOURCE" for r in git_rows) else "NO",
        "schema_compatible": "UNKNOWN_UNTIL_SOURCE_FOUND",
        "semantics_compatible": "UNKNOWN_UNTIL_SOURCE_FOUND",
        "recovery_decision": "NOT_RECOVERED_FROM_REPOSITORY_OR_GIT_HISTORY",
    })

conflict_rows = []
normalisation_method_terms = [r for r in repo_rows if r["term"] in {"normalisation method", "normalization method", "surface normalisation", "distance normalisation", "class normalisation"}]
if len({r["line_evidence"] for r in normalisation_method_terms}) > 1:
    conflict_rows.append({
        "conflict_area": "normalisation semantics references",
        "conflict_status": "MULTIPLE_REFERENCES_REVIEW_REQUIRED",
        "evidence_count": len(normalisation_method_terms),
        "detail": "Multiple documentation/code references exist, but active code governs LINEAR_CENTRE_AND_SCALE only.",
    })
else:
    conflict_rows.append({
        "conflict_area": "normalisation semantics references",
        "conflict_status": "NO_ACTIVE_CONFLICT_FOUND",
        "evidence_count": len(normalisation_method_terms),
        "detail": "No conflicting active governed normalisation method found.",
    })

write_csv(OUT_REPO, ["term", "file_path", "evidence_classification", "line_evidence", "file_size_bytes"], repo_rows)
write_csv(OUT_GIT, ["search_target", "commit", "commit_date", "subject", "name_status", "evidence_classification"], git_rows)
write_csv(OUT_CANDIDATES, ["candidate_file", "active_exists", "git_path_history_found", "schema_compatible", "semantics_compatible", "recovery_decision"], candidate_rows)
write_csv(OUT_CONFLICTS, ["conflict_area", "conflict_status", "evidence_count", "detail"], conflict_rows)

historical_sources = [r for r in git_rows if r["evidence_classification"] == "HISTORICAL_GOVERNED_SOURCE"]
active_contracts = [r for r in repo_rows if r["evidence_classification"] == "ACTIVE_GOVERNED_CONTRACT"]
active_code = [r for r in repo_rows if r["evidence_classification"] == "ACTIVE_CODE_SEMANTICS"]
lines = [
    "# EDGEiQ Horse Rating Method Repository Recovery Report V1",
    "",
    f"Repository evidence rows: `{len(repo_rows)}`",
    f"Git evidence rows: `{len(git_rows)}`",
    f"Active governed contract references: `{len(active_contracts)}`",
    f"Active code semantics references: `{len(active_code)}`",
    f"Historical governed source path evidence rows: `{len(historical_sources)}`",
    "",
    "## Recovery Finding",
]
if historical_sources:
    lines.append("Git history contains path evidence for at least one missing governed source. Inspect candidate rows before restoration.")
else:
    lines.append("No matching governed source file was recovered from active repository paths or Git path history for the three missing source CSVs.")
lines.extend([
    "Active code and contracts prove schema and formula semantics, but they do not prove actual parameter values or identity rows.",
    "A historical file name match alone was not used as recovery evidence; no source file was restored in this phase.",
    "",
    "## Candidate Decisions",
])
for row in candidate_rows:
    lines.append(f"- `{row['candidate_file']}`: active_exists={row['active_exists']}, git_path_history_found={row['git_path_history_found']}, decision=`{row['recovery_decision']}`")
OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "repo_rows": len(repo_rows),
    "git_rows": len(git_rows),
    "historical_source_rows": len(historical_sources),
    "report": str(OUT_REPORT),
}, indent=2))


if __name__ == "__main__":
    pass
