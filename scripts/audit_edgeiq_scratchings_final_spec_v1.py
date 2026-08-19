from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingScratchingsWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "scratchingsFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_scratchings_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_V1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(rows: list[dict[str, str]], check: str, passed: bool, detail: str) -> None:
    rows.append({"check": check, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    component = read(COMPONENT)
    meeting_component = read(MEETING_COMPONENT)
    service = read(SERVICE)
    css = read(CSS)
    rows: list[dict[str, str]] = []

    for token in ["SCRATCHINGS", "STATUS", "BAR", "EFFECTIVE BAR", "FIELD", "UPDATED", "SummaryStrip", "rowStatusClass"]:
        add(rows, f"component_contains_{token}", token in component, token)

    for token in ["fixtureMode", "buildFixtureMeeting", "Development fixture", "REASON", "SOURCE", "Builder", "DATA FRESHNESS", "TimelinePanel"]:
        add(rows, f"component_absent_{token}", token not in component, token)

    add(rows, "meeting_workspace_no_scratchings_fixture", "scratchingsFixtureMode" not in meeting_component and "edgeiqScratchingsFixture" not in meeting_component, "No visible/development scratchings fixture path in meeting route")
    add(rows, "service_no_fixture_builder", "buildFixtureMeeting" not in service and "Development fixture" not in service and "fixtureMode" not in service, "Scratchings service uses current meeting data only")
    add(rows, "service_effective_barrier_helper", "calculateEffectiveBarriers" in service, "Barrier compression helper remains in service")
    add(rows, "css_marker", "/* EDGEIQ SCRATCHINGS FINAL SPEC V1 */" in css, "Scratchings CSS marker")
    add(rows, "css_scratch_fade", "is-scratched" in css and "text-decoration" in css, "Scratched rows fade and strike horse name")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] != "PASS"]
    status = "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_SCRATCHINGS_FINAL_SPEC_AUDIT_FAIL"
    OUT_MD.write_text(
        "\n".join([
            "# EDGEiQ Scratchings Final Spec Audit V1",
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
