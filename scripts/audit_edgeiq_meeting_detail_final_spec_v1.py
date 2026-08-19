from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "meetingDetailFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_meeting_detail_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    component = read(COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    for token in [
        "MEETING DETAIL",
        "SummaryStrip",
        "MeetingConditionStrip",
        "SelectedRacePanel",
        "Back to Meetings",
        "RACES",
        "SCRATCHINGS",
        "TRACK",
        "WEATHER",
        "RESULTS",
    ]:
        add(rows, f"component_contains_{token}", token in component, token)

    for token in ["STATE", "RACES", "RUNNERS", "SCRATCHINGS", "OFFICIAL UPDATE"]:
        add(rows, f"service_summary_contains_{token}", token in service, token)

    add(rows, "service_tab_order_contains_gear_changes", "GEAR CHANGES" in service, "GEAR CHANGES tab label is supplied by meeting-detail tab order")

    for token in ["Weather Stations", "Forecast Source", "station ID", "builder status", "Confidence"]:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "component_no_generic_intelligence_copy", "Governed operational evidence" not in component, "No generic Race Intelligence copy rendered")
    add(rows, "css_marker", "/* EDGEIQ MEETING DETAIL FINAL SPEC V1 */" in css, "Meeting detail CSS marker")
    add(rows, "css_track_condition_colours", all(token in css for token in ["is-firm", "is-good", "is-soft", "is-heavy"]), "Track condition classes")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_MEETING_DETAIL_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Meeting Detail Final Spec Audit V1",
            "",
            f"Status: {status}",
            "",
            f"Checks: {len(rows)}",
            f"Failures: {len(failed)}",
            "",
            "## Results",
            "",
            *[f"- {row['status']}: {row['check']} - {row['detail']}" for row in rows],
            "",
        ]),
        encoding="utf-8",
    )
    print(status)
    print(f"Audit CSV: {OUT_CSV}")
    print(f"Audit MD: {OUT_MD}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
