from pathlib import Path
import csv
import json
import re
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT = ROOT / "public" / "data" / "edgeiq_final_beta_false_default_audit_v1"

SOURCE_ROOTS = [
    ROOT / "src" / "edgeiq-os" / "race",
    ROOT / "src" / "edgeiq-os" / "services",
    ROOT / "src" / "edgeiq-os" / "shell",
    ROOT / "src" / "edgeiq-os" / "styles",
]

CURRENT_FEEDS = [
    "edgeiq_three_day_product_catalog_v1.json",
    "edgeiq_form_guide_enriched_v2.json",
    "edgeiq_map_terminal_feed_v1.json",
    "edgeiq_market_terminal_feed_v1.json",
    "edgeiq_overview_terminal_feed_v1.json",
    "edgeiq_insights_terminal_feed_v1.json",
    "edgeiq_epi_workspace_terminal_feed_v1.json",
    "edgeiq_on_track_weather_governed_v1_2.json",
    "edgeiq_gear_terminal_feed_v1.json",
    "edgeiq_meeting_results_terminal_feed_v1.json",
]

PATTERNS = [
    ("PRICE_400", "HIGH", re.compile(r"(?<![\d.])\$?\s*400(?:\.0+)?(?![\d.])", re.I)),
    ("ZERO_FALLBACK", "HIGH", re.compile(r"(?:\?\?|\|\|)\s*(?:0|['\"]0%['\"]|['\"]\$?0(?:\.00)?['\"])", re.I)),
    ("HARDCODED_STATE", "MEDIUM", re.compile(r"['\"](?:AVAILABLE_CURRENT|AVAILABLE|CURRENT|READY|FRESH)['\"]", re.I)),
    ("HARDCODED_PERCENT", "HIGH", re.compile(r"(?:confidence|coverage|probability|edge)\s*[:=]\s*['\"]?\d{1,3}%?['\"]?", re.I)),
    ("INTERNAL_UI_LANGUAGE", "LOW", re.compile(r"\b(?:BETA-\d+|WORKSPACE BETA|FEED STATUS|NULL HANDLING|ROWS MATCHED|ROWS LOADED|MODEL INFORMATION)\b", re.I)),
]

findings = []

def scan_text(path: Path, scope: str):
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception as exc:
        findings.append({
            "scope": scope,
            "file": str(path.relative_to(ROOT)),
            "line": "",
            "code": "READ_ERROR",
            "severity": "MEDIUM",
            "match": "",
            "line_text": str(exc),
        })
        return

    for number, line in enumerate(lines, start=1):
        for code, severity, pattern in PATTERNS:
            for match in pattern.finditer(line):
                findings.append({
                    "scope": scope,
                    "file": str(path.relative_to(ROOT)),
                    "line": number,
                    "code": code,
                    "severity": severity,
                    "match": match.group(0),
                    "line_text": line.strip()[:500],
                })

source_files = []
for root in SOURCE_ROOTS:
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".ts", ".tsx", ".css"}:
            source_files.append(path)

for path in sorted(source_files):
    scan_text(path, "ACTIVE_SOURCE")

data_files = []
for name in CURRENT_FEEDS:
    path = ROOT / "public" / "data" / name
    if path.exists():
        data_files.append(path)
        scan_text(path, "CURRENT_FEED")

findings.sort(key=lambda x: (x["severity"], x["file"], str(x["line"]), x["code"]))

summary = {
    "status": "EDGEIQ_FINAL_BETA_FALSE_DEFAULT_AUDIT_V1_COMPLETE",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "source_files_scanned": len(source_files),
    "current_feeds_scanned": len(data_files),
    "total_findings": len(findings),
    "high": sum(1 for x in findings if x["severity"] == "HIGH"),
    "medium": sum(1 for x in findings if x["severity"] == "MEDIUM"),
    "low": sum(1 for x in findings if x["severity"] == "LOW"),
}

OUT.parent.mkdir(parents=True, exist_ok=True)

with OUT.with_suffix(".json").open("w", encoding="utf-8") as handle:
    json.dump({"summary": summary, "findings": findings}, handle, indent=2)

with OUT.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["scope", "file", "line", "code", "severity", "match", "line_text"],
    )
    writer.writeheader()
    writer.writerows(findings)

lines = [
    "EDGEIQ FINAL BETA FALSE DEFAULT AUDIT V1",
    f"Generated UTC: {summary['generated_utc']}",
    f"Source files scanned: {summary['source_files_scanned']}",
    f"Current feeds scanned: {summary['current_feeds_scanned']}",
    f"Total findings: {summary['total_findings']}",
    f"High: {summary['high']}",
    f"Medium: {summary['medium']}",
    f"Low: {summary['low']}",
    "",
    "HIGH-SEVERITY FINDINGS",
]

high = [x for x in findings if x["severity"] == "HIGH"]

if not high:
    lines.append("- None detected.")
else:
    for row in high[:150]:
        lines.append(
            f"- {row['file']}:{row['line']} [{row['code']}] {row['line_text']}"
        )

OUT.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("EDGEIQ_FINAL_BETA_FALSE_DEFAULT_AUDIT_V1_COMPLETE")
print(f"source_files_scanned={len(source_files)}")
print(f"current_feeds_scanned={len(data_files)}")
print(f"total_findings={len(findings)}")
print(f"high={summary['high']}")
print(f"medium={summary['medium']}")
print(f"low={summary['low']}")
