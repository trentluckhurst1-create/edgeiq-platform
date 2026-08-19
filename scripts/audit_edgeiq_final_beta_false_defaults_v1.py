from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SRC_ROOTS = [
    ROOT / "src",
]
DATA_ROOT = ROOT / "public" / "data"
OUT_PREFIX = DATA_ROOT / "edgeiq_final_beta_false_default_audit_v1"

EXCLUDED_DIRS = {
    "node_modules",
    "dist",
    ".git",
    "checkpoints",
    "visual_audits",
    "__pycache__",
}

ACTIVE_DATA_NAME_HINTS = (
    "terminal",
    "governed",
    "three_day",
    "current",
    "live",
    "meeting",
    "weather",
    "form_guide",
    "map",
    "market",
    "overview",
    "insights",
    "epi",
    "result",
    "scratch",
    "gear",
    "track",
)

TEXT_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".csv",
}

PATTERNS = [
    {
        "code": "UNIVERSAL_400",
        "severity": "HIGH",
        "regex": re.compile(r"(?<![\d.])(?:\$?\s*400(?:\.0+)?)(?![\d.])", re.I),
        "description": "Possible false or universal $400 price/default.",
    },
    {
        "code": "ZERO_FALLBACK",
        "severity": "HIGH",
        "regex": re.compile(
            r"(?:\?\?|\|\|)\s*(?:0|0\.0|['\"]0%['\"]|['\"]\$?0(?:\.00)?['\"])",
            re.I,
        ),
        "description": "Blank evidence may be coerced to zero.",
    },
    {
        "code": "HARDCODED_AVAILABLE",
        "severity": "MEDIUM",
        "regex": re.compile(
            r"['\"](?:AVAILABLE|AVAILABLE_CURRENT|CURRENT|READY|FRESH)['\"]",
            re.I,
        ),
        "description": "Hard-coded operational/freshness state requiring provenance review.",
    },
    {
        "code": "HARDCODED_CONFIDENCE",
        "severity": "HIGH",
        "regex": re.compile(
            r"(?:confidence|coverage|probability|edge|match)\s*[:=]\s*"
            r"(?:['\"]?\d{1,3}%['\"]?|\d?\.\d+)",
            re.I,
        ),
        "description": "Possible hard-coded analytical percentage or confidence.",
    },
    {
        "code": "GENERIC_NARRATIVE",
        "severity": "MEDIUM",
        "regex": re.compile(
            r"['\"][^'\"]*(?:strong chance|best bet|value opportunity|"
            r"should win|likely winner|clear top pick|major threat)[^'\"]*['\"]",
            re.I,
        ),
        "description": "Possible unguided tipping or generic analytical narrative.",
    },
    {
        "code": "INTERNAL_BETA_LANGUAGE",
        "severity": "LOW",
        "regex": re.compile(
            r"\b(?:BETA-\d+|WORKSPACE BETA|FEED STATUS|NULL HANDLING|"
            r"ROWS MATCHED|ROWS LOADED|MODEL INFORMATION)\b",
            re.I,
        ),
        "description": "Internal engineering language visible in active UI.",
    },
]

SAFE_CONTEXT_MARKERS = (
    "audit",
    "example",
    "test",
    "fixture",
    "legend",
    "historical",
    "threshold",
    "http 400",
    "status code 400",
)

def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)

def iter_source_files():
    for root in SRC_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in TEXT_SUFFIXES
                and not is_excluded(path)
            ):
                yield path

def iter_active_data_files():
    if not DATA_ROOT.exists():
        return
    for path in DATA_ROOT.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".csv"}:
            continue
        name = path.name.lower()
        if any(hint in name for hint in ACTIVE_DATA_NAME_HINTS):
            yield path

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as exc:
        return f"__READ_ERROR__:{exc}"

def classify_context(line: str) -> str:
    lower = line.lower()
    if any(marker in lower for marker in SAFE_CONTEXT_MARKERS):
        return "REVIEW_CONTEXT"
    return "ACTIVE_RISK"

def scan_file(path: Path, scope: str) -> list[dict[str, Any]]:
    text = read_text(path)
    if text.startswith("__READ_ERROR__:"):
        return [{
            "scope": scope,
            "file": str(path.relative_to(ROOT)),
            "line": "",
            "code": "READ_ERROR",
            "severity": "MEDIUM",
            "context_classification": "ERROR",
            "match": "",
            "line_text": text,
            "description": "File could not be read.",
        }]

    findings: list[dict[str, Any]] = []
    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        for pattern in PATTERNS:
            for match in pattern["regex"].finditer(line):
                findings.append({
                    "scope": scope,
                    "file": str(path.relative_to(ROOT)),
                    "line": line_number,
                    "code": pattern["code"],
                    "severity": pattern["severity"],
                    "context_classification": classify_context(line),
                    "match": match.group(0)[:200],
                    "line_text": stripped[:500],
                    "description": pattern["description"],
                })

    return findings

def inspect_structured_data(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    relative = str(path.relative_to(ROOT))

    def walk(value: Any, key_path: str = "$"):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{key_path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{key_path}[{index}]")
        elif isinstance(value, (int, float)):
            lowered = key_path.lower()
            if value == 400 and any(
                token in lowered
                for token in ("price", "market", "fair", "odds", "decimal")
            ):
                findings.append({
                    "scope": "ACTIVE_DATA",
                    "file": relative,
                    "line": "",
                    "code": "STRUCTURED_PRICE_400",
                    "severity": "HIGH",
                    "context_classification": "ACTIVE_RISK",
                    "match": str(value),
                    "line_text": key_path,
                    "description": "Structured active-feed price field equals 400.",
                })
            if value == 0 and any(
                token in lowered
                for token in (
                    "price", "market", "edge", "confidence", "coverage",
                    "probability", "speed", "rating", "suitability",
                    "momentum", "barrier",
                )
            ):
                findings.append({
                    "scope": "ACTIVE_DATA",
                    "file": relative,
                    "line": "",
                    "code": "STRUCTURED_ZERO",
                    "severity": "MEDIUM",
                    "context_classification": "REQUIRES_FIELD_REVIEW",
                    "match": str(value),
                    "line_text": key_path,
                    "description": "Structured analytical field equals zero; verify it is genuine.",
                })

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(read_text(path))
            walk(payload)
        except Exception:
            pass

    elif path.suffix.lower() == ".csv":
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row_number, row in enumerate(reader, start=2):
                    for key, raw in row.items():
                        if raw is None:
                            continue
                        value = raw.strip()
                        lower_key = (key or "").lower()
                        if value in {"400", "400.0", "400.00", "$400", "$400.00"} and any(
                            token in lower_key
                            for token in ("price", "market", "fair", "odds", "decimal")
                        ):
                            findings.append({
                                "scope": "ACTIVE_DATA",
                                "file": relative,
                                "line": row_number,
                                "code": "STRUCTURED_PRICE_400",
                                "severity": "HIGH",
                                "context_classification": "ACTIVE_RISK",
                                "match": value,
                                "line_text": key or "",
                                "description": "CSV active-feed price field equals 400.",
                            })
        except Exception:
            pass

    return findings

all_findings: list[dict[str, Any]] = []
source_files = sorted(set(iter_source_files()))
data_files = sorted(set(iter_active_data_files()))

for file_path in source_files:
    all_findings.extend(scan_file(file_path, "ACTIVE_SOURCE"))

for file_path in data_files:
    all_findings.extend(scan_file(file_path, "ACTIVE_DATA_TEXT"))
    all_findings.extend(inspect_structured_data(file_path))

severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
all_findings.sort(
    key=lambda row: (
        severity_order.get(row["severity"], 9),
        row["context_classification"],
        row["file"],
        str(row["line"]),
        row["code"],
    )
)

summary: dict[str, Any] = {
    "status": "EDGEIQ_FINAL_BETA_FALSE_DEFAULT_AUDIT_V1_COMPLETE",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "source_files_scanned": len(source_files),
    "active_data_files_scanned": len(data_files),
    "total_findings": len(all_findings),
    "active_risk_findings": sum(
        1 for row in all_findings
        if row["context_classification"] == "ACTIVE_RISK"
    ),
    "high_findings": sum(1 for row in all_findings if row["severity"] == "HIGH"),
    "medium_findings": sum(1 for row in all_findings if row["severity"] == "MEDIUM"),
    "low_findings": sum(1 for row in all_findings if row["severity"] == "LOW"),
    "findings_by_code": {},
}

for row in all_findings:
    summary["findings_by_code"][row["code"]] = (
        summary["findings_by_code"].get(row["code"], 0) + 1
    )

OUT_PREFIX.parent.mkdir(parents=True, exist_ok=True)

json_path = OUT_PREFIX.with_suffix(".json")
csv_path = OUT_PREFIX.with_suffix(".csv")
txt_path = OUT_PREFIX.with_suffix(".txt")

json_path.write_text(
    json.dumps(
        {
            "summary": summary,
            "findings": all_findings,
            "source_files": [str(path.relative_to(ROOT)) for path in source_files],
            "active_data_files": [str(path.relative_to(ROOT)) for path in data_files],
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

fieldnames = [
    "scope",
    "file",
    "line",
    "code",
    "severity",
    "context_classification",
    "match",
    "line_text",
    "description",
]

with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_findings)

report_lines = [
    "EDGEIQ FINAL BETA FALSE DEFAULT AUDIT V1",
    f"Generated UTC: {summary['generated_utc']}",
    f"Source files scanned: {summary['source_files_scanned']}",
    f"Active data files scanned: {summary['active_data_files_scanned']}",
    f"Total findings: {summary['total_findings']}",
    f"Active-risk findings: {summary['active_risk_findings']}",
    f"High: {summary['high_findings']}",
    f"Medium: {summary['medium_findings']}",
    f"Low: {summary['low_findings']}",
    "",
    "FINDINGS BY CODE",
]

for code, count in sorted(summary["findings_by_code"].items()):
    report_lines.append(f"- {code}: {count}")

report_lines.extend([
    "",
    "HIGH-SEVERITY ACTIVE RISKS",
])

high_active = [
    row for row in all_findings
    if row["severity"] == "HIGH"
    and row["context_classification"] == "ACTIVE_RISK"
]

if not high_active:
    report_lines.append("- None detected by this static audit.")
else:
    for row in high_active[:200]:
        report_lines.append(
            f"- {row['file']}:{row['line']} "
            f"[{row['code']}] {row['line_text']}"
        )

report_lines.extend([
    "",
    "IMPORTANT",
    "- Findings are candidates requiring evidence review, not automatic defects.",
    "- No product source or feed was modified.",
    "- Historical, test and audit contexts must not be patched blindly.",
])

txt_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

print("EDGEIQ_FINAL_BETA_FALSE_DEFAULT_AUDIT_V1_COMPLETE")
print(f"source_files_scanned={len(source_files)}")
print(f"active_data_files_scanned={len(data_files)}")
print(f"total_findings={len(all_findings)}")
print(f"active_risk_findings={summary['active_risk_findings']}")
print(f"high_findings={summary['high_findings']}")
print(f"json={json_path}")
print(f"csv={csv_path}")
print(f"txt={txt_path}")
