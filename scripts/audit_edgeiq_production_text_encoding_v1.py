from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "production-hardening-v1"
DETAIL_CSV = OUT / "edgeiq_production_text_encoding_audit_v1.csv"
SUMMARY_JSON = OUT / "edgeiq_production_text_encoding_audit_v1_summary.json"

SCAN_ROOTS = [
    ROOT / "src",
    ROOT / "deployment",
    ROOT / "scripts",
    ROOT / "public" / "styles",
    ROOT / "docs" / "operations-readiness",
]

ACTIVE_PRODUCTION_FEEDS = [
    ROOT / "public" / "data" / "edgeiq_three_day_window_v1.json",
    ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1.json",
    ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json",
    ROOT / "public" / "data" / "edgeiq_current_runner_intelligence_audit_v1.csv",
    ROOT / "public" / "data" / "edgeiq_market_terminal_feed_v1.csv",
    ROOT / "public" / "data" / "edgeiq_overview_terminal_feed_v1.csv",
    ROOT / "public" / "data" / "edgeiq_meeting_results_terminal_feed_v1.csv",
    ROOT / "public" / "data" / "edgeiq_three_day_product_catalog_v1_summary.txt",
    ROOT / "public" / "data" / "edgeiq_vic_three_day_race_list_v1.csv",
    ROOT / "public" / "data" / "edgeiq_vic_three_day_meeting_calendar_v1.csv",
    ROOT / "public" / "data" / "edgeiq_current_market_v1.csv",
    ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.csv",
    ROOT / "public" / "performance-intelligence" / "edgeiq_performance_intelligence_product_feeds_v1.json",
    ROOT / "public" / "performance-intelligence" / "edgeiq_performance_intelligence_product_manifest_v1.json",
]

TEXT_SUFFIXES = {
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".mjs",
    ".cjs",
    ".py",
    ".json",
    ".csv",
    ".md",
    ".html",
    ".htm",
    ".css",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "outputs",
    "__pycache__",
    "EDGEIQ_PERFORMANCE_REPAIR_PACK",
}

MOJIBAKE_PATTERNS = [
    "Ã¢â‚¬â„¢",
    "Ã¢â‚¬Å“",
    "Ã¢â‚¬",
    "Ã¢â‚¬â€œ",
    "Ã¢â‚¬â€",
    "Ã‚",
    "Ãƒ",
    "ï¿½",
    "â€™",
    "â€œ",
    "â€",
    "â€“",
    "â€”",
    "â€¢",
    "â—‹",
    "âœ“",
    "Â°",
    "Â±",
    "Â£",
    "Â$",
]

REPLACEMENT_RE = re.compile("\ufffd|ï¿½")
INVALID_ENTITY_RE = re.compile(r"&(?![a-zA-Z][a-zA-Z0-9]+;|#[0-9]+;|#x[0-9a-fA-F]+;)([a-zA-Z0-9#]+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_PARTS:
        return True
    upper_name = path.name.upper()
    if any(token in upper_name for token in ["CHECKPOINT", "BEFORE", "BACKUP", ".BAK", "PRE_"]):
        return True
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return True
    if path.stat().st_size > 250_000_000:
        return True
    return False


def production_surface(path: Path) -> str:
    relative = rel(path)
    if relative.startswith("src/"):
        return "UI_SOURCE"
    if relative.startswith("public/data/") or relative.startswith("public/performance-intelligence/"):
        return "PRODUCTION_FEED"
    if relative.startswith("public/styles/"):
        return "UI_STYLE"
    if relative.startswith("deployment/"):
        return "SERVER_RUNTIME"
    if relative.startswith("scripts/"):
        return "BUILDER_OR_AUDIT"
    return "SUPPORTING_ARTIFACT"


def is_ui_visible(path: Path) -> bool:
    surface = production_surface(path)
    return surface in {"UI_SOURCE", "UI_STYLE", "PRODUCTION_FEED"}


def is_production_blocker(path: Path, finding_type: str) -> bool:
    surface = production_surface(path)
    if surface in {"SUPPORTING_ARTIFACT", "BUILDER_OR_AUDIT"}:
        return False
    if finding_type == "INVALID_HTML_ENTITY":
        return surface in {"UI_SOURCE", "UI_STYLE"}
    return True


def detect_line(path: Path, line_no: int, line: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for pattern in MOJIBAKE_PATTERNS:
        if pattern in line:
            findings.append(
                {
                    "file": rel(path),
                    "line": str(line_no),
                    "surface": production_surface(path),
                    "finding_type": "MOJIBAKE",
                    "pattern": pattern,
                    "ui_visible": "TRUE" if is_ui_visible(path) else "FALSE",
                    "production_blocker": "TRUE" if is_production_blocker(path, "MOJIBAKE") else "FALSE",
                    "excerpt": line.strip()[:240],
                }
            )
    if REPLACEMENT_RE.search(line):
        findings.append(
            {
                "file": rel(path),
                "line": str(line_no),
                "surface": production_surface(path),
                "finding_type": "REPLACEMENT_CHARACTER",
                "pattern": "REPLACEMENT",
                "ui_visible": "TRUE" if is_ui_visible(path) else "FALSE",
                "production_blocker": "TRUE" if is_production_blocker(path, "REPLACEMENT_CHARACTER") else "FALSE",
                "excerpt": line.strip()[:240],
            }
        )
    if path.suffix.lower() in {".html", ".htm", ".tsx", ".ts", ".jsx", ".js"} and INVALID_ENTITY_RE.search(line):
        findings.append(
            {
                "file": rel(path),
                "line": str(line_no),
                "surface": production_surface(path),
                "finding_type": "INVALID_HTML_ENTITY",
                "pattern": "ENTITY_WITHOUT_SEMICOLON",
                "ui_visible": "TRUE" if is_ui_visible(path) else "FALSE",
                "production_blocker": "TRUE" if is_production_blocker(path, "INVALID_HTML_ENTITY") else "FALSE",
                "excerpt": line.strip()[:240],
            }
        )
    return findings


def iter_files() -> list[Path]:
    files: list[Path] = []
    for base in SCAN_ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if skip_path(path):
                continue
            files.append(path)
    for path in ACTIVE_PRODUCTION_FEEDS:
        if path.exists() and path.is_file() and not skip_path(path):
            files.append(path)
    return sorted(set(files))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    files = iter_files()
    files_scanned = 0
    strings_inspected = 0
    invalid_utf8_files = 0

    for path in files:
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            invalid_utf8_files += 1
            rows.append(
                {
                    "file": rel(path),
                    "line": str(exc.start),
                    "surface": production_surface(path),
                    "finding_type": "INVALID_UTF8",
                    "pattern": exc.reason,
                    "ui_visible": "TRUE" if is_ui_visible(path) else "FALSE",
                    "production_blocker": "TRUE" if is_production_blocker(path, "INVALID_UTF8") else "FALSE",
                    "excerpt": "",
                }
            )
            text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            strings_inspected += 1
            rows.extend(detect_line(path, line_no, line))

    fieldnames = ["file", "line", "surface", "finding_type", "pattern", "ui_visible", "production_blocker", "excerpt"]
    with DETAIL_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    mojibake = [row for row in rows if row["finding_type"] == "MOJIBAKE"]
    replacement = [row for row in rows if row["finding_type"] == "REPLACEMENT_CHARACTER"]
    ui_mojibake = [row for row in mojibake if row["ui_visible"] == "TRUE"]
    ui_replacement = [row for row in replacement if row["ui_visible"] == "TRUE"]
    blockers = [row for row in rows if row["production_blocker"] == "TRUE"]
    invalid_utf8_blockers = [row for row in rows if row["finding_type"] == "INVALID_UTF8" and row["production_blocker"] == "TRUE"]
    replacement_blockers = [row for row in replacement if row["production_blocker"] == "TRUE"]
    summary = {
        "schema_version": "EDGEIQ_PRODUCTION_TEXT_ENCODING_AUDIT_V1",
        "generated_at": utc_now(),
        "files_scanned": files_scanned,
        "strings_inspected": strings_inspected,
        "suspect_strings": len(rows),
        "invalid_utf8_files": invalid_utf8_files,
        "invalid_utf8_production_files": len(invalid_utf8_blockers),
        "mojibake_matches": len(mojibake),
        "replacement_characters": len(replacement),
        "replacement_characters_total": len(replacement),
        "replacement_characters_production": len(replacement_blockers),
        "mojibake_ui_strings": len(ui_mojibake),
        "replacement_ui_strings": len(ui_replacement),
        "invalid_html_entities": sum(1 for row in rows if row["finding_type"] == "INVALID_HTML_ENTITY"),
        "INVALID_UTF8_FILES": invalid_utf8_files,
        "INVALID_UTF8_PRODUCTION_FILES": len(invalid_utf8_blockers),
        "MOJIBAKE_UI_STRINGS": len(ui_mojibake),
        "REPLACEMENT_CHARACTERS": len(replacement_blockers),
        "REPLACEMENT_UI_STRINGS": len(ui_replacement),
        "PRODUCTION_TEXT_BLOCKERS": len(blockers),
        "GLOBAL_ENCODING_HEALTH": "PASS"
        if len(blockers) == 0 and invalid_utf8_files == 0 and len(ui_mojibake) == 0 and len(ui_replacement) == 0
        else "FAIL",
        "detail_csv": rel(DETAIL_CSV),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["GLOBAL_ENCODING_HEALTH"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
