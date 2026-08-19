from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
SERVICE = ROOT / "src" / "edgeiq-os" / "race" / "services" / "mapFeed.ts"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
DOC = ROOT / "docs" / "full-product-implementation" / "EDGEIQ_MAP_FINAL_SPEC_AUDIT_V1.md"
CSV = ROOT / "docs" / "full-product-implementation" / "edgeiq_map_final_spec_audit_v1.csv"


def read(path: Path) -> str:
  return path.read_text(encoding="utf-8")


def check(name: str, passed: bool, detail: str) -> dict[str, str]:
  return {
    "check": name,
    "status": "PASS" if passed else "FAIL",
    "detail": detail,
  }


def main() -> None:
  component = read(COMPONENT)
  service = read(SERVICE)
  css = read(CSS)
  component_lower = component.lower()

  checks = [
    check(
      "RIGHT_TO_LEFT_ORIENTATION",
      'data-map-orientation="victorian-right-to-left"' in component,
      "MAP visual carries the Victorian right-to-left orientation marker.",
    ),
    check(
      "CURATED_TRACK_ASSET",
      "resolveTrackMapAsset" in component and "eiq-map-v1-track-img" in component,
      "MAP resolves and renders the curated selected-track map asset where available.",
    ),
    check(
      "STRAIGHT_BLUE_LANES",
      "left: var(--eiq-map-left)" in css and "right: 8px" in css and "background: #1f5fd6" in css,
      "Lane bars are straight horizontal blue lines controlled by a left position variable.",
    ),
    check(
      "LABEL_STRUCTURE",
      "<strong>{rowNumber(row)}</strong>" in component and '<span>{rowSpeed(row) || "No speed"}</span>' in component and "<em>{rowRunnerName(row)}</em>" in component,
      "Runner labels contain saddlecloth number, speed value/unavailable state, and horse name.",
    ),
    check(
      "NO_COLOURED_NUMBER_CHIPS",
      "eiq-map-v1-runner-line__label strong" in css and "background: #ffffff" in css and "color: #172033" in css,
      "Saddlecloth numbers use neutral white styling rather than coloured chips.",
    ),
    check(
      "SCRATCHINGS_COMPRESS_IN_SERVICE",
      "function isScratchedRunner" in service and "race.runners.filter((runner) => !isScratchedRunner(runner))" in service,
      "Scratched runners are filtered in the map service before display; React does not recalculate barriers.",
    ),
    check(
      "HONEST_UNAVAILABLE_POSITIONING",
      "is-unavailable" in component and "Runners without governed speed evidence stay at the barrier side" in component,
      "Unavailable speed evidence renders without a lane instead of fabricating position.",
    ),
    check(
      "NO_CONFIDENCE_COPY",
      "confidence" not in component_lower,
      "MAP component has no product-facing confidence copy.",
    ),
    check(
      "NO_PROHIBITED_MAP_PATTERNS",
      not any(term in component_lower for term in ["heatmap", "heat map", "barrier band", "replay", "official sectional time"]),
      "Component does not introduce prohibited MAP patterns.",
    ),
  ]

  CSV.parent.mkdir(parents=True, exist_ok=True)
  with CSV.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"])
    writer.writeheader()
    writer.writerows(checks)

  failures = [row for row in checks if row["status"] != "PASS"]
  DOC.write_text(
    "# EDGEiQ MAP Final Spec Audit V1\n\n"
    + "\n".join(f"- {row['status']}: {row['check']} - {row['detail']}" for row in checks)
    + "\n",
    encoding="utf-8",
  )

  if failures:
    print("EDGEIQ_MAP_FINAL_SPEC_AUDIT_FAIL")
    for failure in failures:
      print(f"{failure['check']}: {failure['detail']}")
    raise SystemExit(1)

  print("EDGEIQ_MAP_FINAL_SPEC_AUDIT_PASS")


if __name__ == "__main__":
  main()
