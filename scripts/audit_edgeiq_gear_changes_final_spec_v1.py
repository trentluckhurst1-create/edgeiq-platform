from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingGearChangesWorkspace.tsx"
MEETING_COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MeetingWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "gearChangesFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT_CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_gear_changes_final_spec_audit_v1.csv"
OUT_MD = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_GEAR_CHANGES_FINAL_SPEC_AUDIT_V1.md"


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

  required_component_tokens = [
    "GEAR CHANGES",
    "PREVIOUS GEAR",
    "TODAY GEAR",
    "FIRST TIME",
    "RUNNER GEAR DETAIL",
    "SummaryStrip",
    "GearFilters",
    "GearTable",
  ]
  for token in required_component_tokens:
    add(rows, f"component_contains_{token}", token in component, token)

  rejected_product_tokens = [
    "fixtureMode",
    "edgeiqGearFixture",
    "buildFixtureRows",
    "Development fixture",
    ">SOURCE<",
    "SOURCE</th>",
    "DATA FRESHNESS",
    "sourceConfidence",
    "Gear terminal feed",
    "Confidence",
    "positive",
    "negative",
    "impact",
    "score",
  ]
  for token in rejected_product_tokens:
    add(rows, f"product_absent_{token}", token not in component, token)

  add(
    rows,
    "meeting_workspace_no_gear_fixture",
    "gearFixtureMode" not in meeting_component and "edgeiqGearFixture" not in meeting_component,
    "No visible/development gear fixture path in meeting route",
  )
  add(
    rows,
    "service_no_fixture_builder",
    "buildFixtureRows" not in service and "Development fixture" not in service and "fixtureMode" not in service,
    "Gear service uses governed terminal rows only",
  )
  add(rows, "service_no_product_source_field", "source:" not in service and "sourceConfidence" not in service, "No product source fields in gear view model")
  add(rows, "service_preserves_guard", "rows.length > 10000" in service, "Frontend oversized CSV safety guard retained")
  add(rows, "css_marker", "/* EDGEIQ GEAR CHANGES FINAL SPEC V1 */" in css, "Gear CSS marker")
  add(rows, "css_white_theme", ".eiq-gear-v1-header" in css and "background: #ffffff" in css, "White theme retained")

  OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
  with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
    writer.writeheader()
    writer.writerows(rows)

  failed = [row for row in rows if row["status"] != "PASS"]
  status = "EDGEIQ_GEAR_CHANGES_FINAL_SPEC_AUDIT_PASS" if not failed else "EDGEIQ_GEAR_CHANGES_FINAL_SPEC_AUDIT_FAIL"
  OUT_MD.write_text(
    "\n".join([
      "# EDGEiQ Gear Changes Final Spec Audit V1",
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
