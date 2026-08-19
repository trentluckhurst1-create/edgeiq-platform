from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "approved-ui-rebuild"
REPORT_PATH = OUT_DIR / "EDGEIQ_APPROVED_UI_ENCODING_AUDIT_V1.json"

TEXT_SUFFIXES = {".ts", ".tsx", ".css", ".md", ".txt", ".json", ".html"}
SCAN_ROOTS = [ROOT / "src", ROOT / "docs" / "product-specification"]

MARKERS = [
    "\u00e2\u2122\u017e",
    "\u00c2\u2020",
    "\u00f0\u00c5\u00b8",
    "\u00ef\u00bb\u00bf",
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u201c",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u009d",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u02dc",
    "\u00e2\u20ac\u00a6",
    "\u00e2\u2020\u2019",
    "\u00e2\u2020\u0090",
    "\u00e2\u20ac\u00b9",
    "\u00e2\u20ac\u00ba",
    "\u00c2\u00b7",
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                if (
                    "checkpoints" in path.parts
                    or "_CHECKPOINT_" in path.name
                    or "BEFORE_" in path.name
                    or "_BEFORE_" in path.name
                    or "_STABLE_" in path.name
                ):
                    continue
                files.append(path)
    return sorted(files)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, object]] = []
    scanned = 0
    for path in iter_files():
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in MARKERS:
            idx = text.find(marker)
            if idx >= 0:
                line_no = text[:idx].count("\n") + 1
                line = text.splitlines()[line_no - 1][:220] if text.splitlines() else ""
                findings.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": line_no,
                        "marker": marker.encode("unicode_escape").decode("ascii"),
                        "sample": line,
                    }
                )

    report = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scanned_files": scanned,
        "finding_count": len(findings),
        "findings": findings[:500],
        "status": "EDGEIQ_APPROVED_UI_ENCODING_AUDIT_PASS" if not findings else "EDGEIQ_APPROVED_UI_ENCODING_AUDIT_FAIL",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if findings:
        raise SystemExit("EDGEIQ_APPROVED_UI_ENCODING_AUDIT_FAIL")
    print("EDGEIQ_APPROVED_UI_ENCODING_AUDIT_PASS")


if __name__ == "__main__":
    main()
