from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs" / "full-product-implementation" / "encoding-repair"
REPORT_PATH = REPORT_DIR / "edgeiq_approved_ui_encoding_repair_v1_report.json"

TEXT_SUFFIXES = {".ts", ".tsx", ".css", ".md", ".txt", ".json", ".html"}
SCAN_ROOTS = [ROOT / "src", ROOT / "docs" / "product-specification"]

REPLACEMENTS = {
    "\ufeff": "",
    "\u00ef\u00bb\u00bf": "",
    "\u00e2\u2122\u017e": "",
    "\u00c2\u2020": "->",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\u009d": '"',
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u00a6": "...",
    "\u00c3\u2014": "x",
}

MARKERS = [
    "\u00ef\u00bb\u00bf",
    "\u00e2\u2122\u017e",
    "\u00c2\u2020",
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u201c",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u009d",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u02dc",
    "\u00e2\u20ac\u00a6",
]


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                if "checkpoints" in path.parts or "_CHECKPOINT_" in path.name:
                    continue
                files.append(path)
    return sorted(files)


def targeted_source_repair(path: Path, text: str) -> str:
    rel = str(path.relative_to(ROOT)).replace("/", "\\")
    repaired = text

    if rel == "src\\services\\productShellMeetingService.ts":
        repaired = re.sub(
            r'const raw = text\(value\)\.replace\(/.*?/g, "-"\)\.trim\(\);',
            'const raw = text(value).replace(/[\\u2013\\u2014]/g, "-").trim();',
            repaired,
        )

    if rel in {
        "src\\edgeiq-os\\race\\services\\meetingDetailFeed.ts",
        "src\\edgeiq-os\\race\\services\\scratchingsFeed.ts",
    }:
        repaired = re.sub(
            r'if \(!text \|\| text === "-" \|\| text === ".*?" \|\| text === ".*?"\) return "";',
            'if (!text || text === "-" || text === "\\u2014") return "";',
            repaired,
        )

    if rel == "src\\services\\commandWorkspaceSummaryService.ts":
        repaired = re.sub(
            r'const cleanWeight = \(row: Row\) => firstText\((.*?), ".*?"\);',
            r'const cleanWeight = (row: Row) => firstText(\1, "-");',
            repaired,
        )

    legacy_placeholder_files = {
        "src\\components\\RaceIntelligenceScreen.tsx",
        "src\\components\\overlays\\CareerHistoryModal.tsx",
        "src\\components\\workspaces\\RaceLabWorkspace.tsx",
        "src\\screens\\HomeScreen.tsx",
        "src\\screens\\MeetingsScreen.tsx",
    }
    if rel in legacy_placeholder_files:
        repaired = repaired.replace("\u00e2\u2020\u2019", "->").replace("\u00e2\u2020\u0090", "<-")
        repaired = repaired.replace("\u00e2\u20ac\u00b9", "<").replace("\u00e2\u20ac\u00ba", ">")
        repaired = re.sub(r'"[^"\n]*(?:\u00c3|\u00c2|\u00e2|\ufffd)[^"\n]*"', '"-"', repaired)
        repaired = re.sub(r">([^<]*(?:\u00c3|\u00c2|\u00e2|\ufffd)[^<]*)<", ">-<", repaired)

    return repaired


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    changed: list[dict[str, object]] = []
    scanned = 0

    for path in candidate_files():
        scanned += 1
        original = path.read_text(encoding="utf-8", errors="replace")
        repaired = original
        replacements_used: dict[str, int] = {}
        for bad, good in REPLACEMENTS.items():
            count = repaired.count(bad)
            if count:
                repaired = repaired.replace(bad, good)
                replacements_used[bad.encode("unicode_escape").decode("ascii")] = count

        targeted = targeted_source_repair(path, repaired)
        if targeted != repaired:
            replacements_used["targeted_source_repair"] = replacements_used.get("targeted_source_repair", 0) + 1
            repaired = targeted

        if repaired != original:
            checkpoint = path.with_name(f"{path.stem}_CHECKPOINT_PRE_ENCODING_REPAIR_V1{path.suffix}")
            if not checkpoint.exists():
                checkpoint.write_text(original, encoding="utf-8", newline="")
            path.write_text(repaired, encoding="utf-8", newline="")
            changed.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "checkpoint": str(checkpoint.relative_to(ROOT)),
                    "replacements": replacements_used,
                }
            )

    remaining: list[dict[str, object]] = []
    for path in candidate_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = []
        for marker in MARKERS:
            if marker in text:
                hits.append(marker.encode("unicode_escape").decode("ascii"))
        if hits:
            remaining.append({"file": str(path.relative_to(ROOT)), "markers": hits})

    report = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scanned_files": scanned,
        "changed_files": len(changed),
        "changes": changed,
        "remaining_marker_files": remaining,
        "status": "EDGEIQ_APPROVED_UI_ENCODING_REPAIR_COMPLETE" if not remaining else "EDGEIQ_APPROVED_UI_ENCODING_REPAIR_REVIEW_REQUIRED",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    if remaining:
        raise SystemExit("EDGEIQ_APPROVED_UI_ENCODING_REPAIR_REVIEW_REQUIRED")
    print("EDGEIQ_APPROVED_UI_ENCODING_REPAIR_COMPLETE")


if __name__ == "__main__":
    main()
