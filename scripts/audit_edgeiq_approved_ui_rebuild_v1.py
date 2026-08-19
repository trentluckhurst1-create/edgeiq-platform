from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "full-product-implementation" / "screenshots" / "approved-ui-rebuild"
CSS_PATH = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
NAV_PATH = ROOT / "src" / "edgeiq-os" / "race" / "components" / "AppNavigation.tsx"
ENCODING_AUDIT = OUT_DIR / "EDGEIQ_APPROVED_UI_ENCODING_AUDIT_V1.json"
CAPTURE_AUDIT = OUT_DIR / "EDGEIQ_APPROVED_UI_CAPTURE_V1.json"

WORKSPACES = [
    "01_HOME",
    "02_MEETINGS",
    "03_RACE_OVERVIEW",
    "04_FIELD",
    "05_FORM_GUIDE",
    "06_PERFORMANCE",
    "07_MAP",
    "08_EPI",
    "09_MARKET",
    "10_OVERVIEW",
    "11_SCRATCHINGS",
    "12_GEAR_CHANGES",
    "13_TRACK",
    "14_WEATHER",
    "15_RESULTS",
    "16_INSIGHTS",
    "17_LAB",
    "18_COMPARE",
    "19_REVIEW",
]

ARTIFACT_SUFFIXES = [
    "_APPROVED.png",
    "_RENDERED.png",
    "_OVERLAY.png",
    "_DIFF.png",
    "_COMPARISON.json",
]

FORBIDDEN_SOURCE_MARKERS = ["\u00e2", "\u00c2", "\u00c3", "\ufeff"]


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def active_source_encoding_hits() -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for path in (ROOT / "src").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".ts", ".tsx", ".css", ".js", ".jsx"}:
            continue
        if any(token in path.name for token in ["_CHECKPOINT_", "BEFORE_", "_BEFORE_", "UI_LOCKED", "MASTER_LOCK"]):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in FORBIDDEN_SOURCE_MARKERS):
                hits.append({"file": str(path.relative_to(ROOT)), "line": line_no})
                break
    return hits


def main() -> None:
    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for workspace in WORKSPACES:
        row: dict[str, object] = {"workspace": workspace}
        for suffix in ARTIFACT_SUFFIXES:
            path = OUT_DIR / f"{workspace}{suffix}"
            exists = path.exists() and path.stat().st_size > 0
            row[suffix.strip("_").replace(".", "_")] = "YES" if exists else "NO"
            if not exists:
                missing.append(str(path.relative_to(ROOT)))
        comparison = read_json(OUT_DIR / f"{workspace}_COMPARISON.json")
        row["rms_difference"] = comparison.get("rms_difference", "")
        row["material_region_count"] = comparison.get("material_region_count", "")
        row["visual_status"] = comparison.get("visual_status", "")
        rows.append(row)

    encoding = read_json(ENCODING_AUDIT)
    capture = read_json(CAPTURE_AUDIT)
    capture_errors = [item for item in capture.get("results", []) if item.get("type")]
    source_hits = active_source_encoding_hits()
    css = CSS_PATH.read_text(encoding="utf-8", errors="replace") if CSS_PATH.exists() else ""
    nav = NAV_PATH.read_text(encoding="utf-8", errors="replace") if NAV_PATH.exists() else ""

    status = "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_PASS"
    failures: list[str] = []
    if missing:
        failures.append(f"missing_artifacts={len(missing)}")
    if encoding.get("status") != "EDGEIQ_APPROVED_UI_ENCODING_AUDIT_PASS":
        failures.append("encoding_audit_not_pass")
    if source_hits:
        failures.append(f"active_source_encoding_hits={len(source_hits)}")
    if capture.get("workspace_count") != 19:
        failures.append("capture_workspace_count_not_19")
    if capture_errors:
        failures.append(f"browser_capture_errors={len(capture_errors)}")
    if "EDGEIQ APPROVED UI PHASE 09-21 REMAINING WORKSPACES" not in css:
        failures.append("remaining_workspace_css_marker_missing")
    for label in ["HOME", "MEETINGS", "RACE", "FIELD", "FORM GUIDE", "PERFORMANCE", "EPI", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "RESULTS", "LAB", "COMPARE", "REVIEW"]:
        if label not in nav:
            failures.append(f"nav_label_missing={label}")

    if failures:
        status = "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_FAIL"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_V1.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace_count": len(WORKSPACES),
        "missing_artifacts": missing,
        "encoding_audit_status": encoding.get("status"),
        "active_source_encoding_hits": source_hits[:20],
        "capture_workspace_count": capture.get("workspace_count"),
        "capture_error_count": len(capture_errors),
        "failures": failures,
        "status": status,
    }
    (OUT_DIR / "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_V1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DIR / "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_V1.txt").write_text(
        "\n".join(
            [
                "EDGEIQ_APPROVED_UI_REBUILD_AUDIT_V1",
                f"status={status}",
                f"workspace_count={len(WORKSPACES)}",
                f"missing_artifacts={len(missing)}",
                f"encoding_audit_status={encoding.get('status')}",
                f"active_source_encoding_hits={len(source_hits)}",
                f"capture_error_count={len(capture_errors)}",
                *failures,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(status)
    print(status)


if __name__ == "__main__":
    main()
