from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingTrackWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "trackFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_track_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_TRACK_FINAL_SPEC_AUDIT_V1.md"


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

  for token in [
    "Track Condition",
    "Rail Position and Track Map",
    "Track Details",
    "Track Pattern Analysis",
    "Historical Profile",
    "Track Notes",
    "resolveTrackMapPath",
  ]:
    add(rows, f"component_contains_{token}", token in component, token)

  for token in [
    "REFRESH TRACK FEEDS",
    "Source State",
    "Contextual Operational Rail",
    "showSources",
    "station",
    "registry",
    "Confidence",
    "builder",
    "track records",
    "class records",
    "official time records",
    "margin records",
    "fixtureMode",
    "missingMapMode",
    "missingHistoricalMode",
  ]:
    add(rows, f"component_absent_{token}", token not in component, token)

  add(
    rows,
    "meeting_workspace_no_track_fixture_query",
    "edgeiqTrackFixture" not in meeting_component and "edgeiqTrackMissingMap" not in meeting_component and "edgeiqTrackMissingHistorical" not in meeting_component,
    "No TRACK fixture or missing-data query paths in meeting route",
  )
  add(
    rows,
    "service_no_fixture_builder",
    "buildFixtureFeeds" not in service and "fixtureMode" not in service and "track_profile_confidence" not in service,
    "Track service has no development fixture or profile confidence display path",
  )
  add(rows, "service_preserves_curated_map_manifest", "edgeiq_track_map_manifest_v1.csv" in service, "Curated map manifest remains wired")
  add(rows, "service_preserves_guard", "rows.length > 10000" in service and "records.length > 10000" in service, "Frontend oversized source guards retained")
  add(rows, "css_white_theme", ".eiq-track-v1-header" in css and "background: #ffffff" in css, "White theme retained")
  add(rows, "css_condition_colours", "is-firm" in css and "is-good" in css and "is-soft" in css and "is-heavy" in css, "Approved track-condition colour classes exist")

  OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
  with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
    writer.writeheader()
    writer.writerows(rows)

  failed = [row for row in rows if row["status"] != "PASS"]
  status = "EDGEIQ_TRACK_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_TRACK_FINAL_SPEC_AUDIT_FAIL"
  OUT_MD.write_text(
    "\n".join([
      "# EDGEiQ Track Final Spec Audit V1",
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
