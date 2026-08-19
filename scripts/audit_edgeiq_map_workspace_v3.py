from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
RACE_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
RUNNER_WORKSPACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RunnerProfileWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
LIVE_SNAPSHOT = ROOT / "src" / "edgeiq-os" / "services" / "live-race-data-snapshot.ts"
RACE_FILE_SERVICE = ROOT / "src" / "edgeiq-os" / "services" / "race-file-v2.ts"
OUT = ROOT / "public" / "data" / "edgeiq_map_workspace_v3_audit.txt"


def read(path: Path) -> str:
  return path.read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
  marker = f"function {name}"
  start = source.find(marker)
  if start == -1:
    return ""
  brace = source.find("{", start)
  if brace == -1:
    return ""
  depth = 0
  for index in range(brace, len(source)):
    char = source[index]
    if char == "{":
      depth += 1
    elif char == "}":
      depth -= 1
      if depth == 0:
        return source[start : index + 1]
  return source[start:]


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
  return (name, condition, detail)


def live_snapshot_diagnostics() -> list[str]:
  lines: list[str] = []
  if not LIVE_SNAPSHOT.exists():
    return ["Live snapshot diagnostics: source file not found."]
  source = read(LIVE_SNAPSHOT)
  blocks = re.findall(r"\{[^{}]*runner:\s*['\"]([^'\"]+)['\"][^{}]*\}", source, re.S)
  market_scratch_blocks = re.findall(r"\{[^{}]*runner:\s*['\"]([^'\"]+)['\"][^{}]*(?:SCRATCHED|Scratched)[^{}]*\}", source, re.S)
  total = len(blocks)
  scratched = len(set(market_scratch_blocks))
  active = max(0, total - scratched)

  shared_default = False
  if RACE_FILE_SERVICE.exists():
    service = read(RACE_FILE_SERVICE)
    shared_default = "historicalRuns: [sampleRun(0, runner), sampleRun(1, runner)]" in service

  if shared_default:
    lanes = Counter({"MIDFIELD": active})
    sources = Counter({"shared-template": active})
    confidence = Counter({"Limited evidence": active})
    warning = (
      "WARNING: all active runners resolve through the same generated historical run template; "
      "V3 keeps the map read but downgrades confidence to Limited evidence."
    )
  else:
    lanes = Counter()
    sources = Counter()
    confidence = Counter()
    warning = "No shared generated historical run template detected by static audit."

  lines.extend(
    [
      "Diagnostics:",
      f"- total runners: {total}",
      f"- active runners: {active}",
      f"- scratched runners: {scratched}",
      f"- lane counts: {dict(lanes) if lanes else 'static audit unavailable'}",
      f"- evidence counts: {dict(confidence) if confidence else 'static audit unavailable'}",
      f"- source pathway counts: {dict(sources) if sources else 'static audit unavailable'}",
      f"- {warning}",
    ]
  )
  return lines


def run_build() -> tuple[bool, str]:
  result = subprocess.run(
    ["npm.cmd", "run", "build"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=180,
  )
  output = (result.stdout + "\n" + result.stderr).strip()
  return result.returncode == 0, output[-5000:]


def main() -> None:
  component = read(COMPONENT)
  css = read(CSS)
  race_workspace = read(RACE_WORKSPACE)
  runner_workspace = read(RUNNER_WORKSPACE)
  combined_mounts = race_workspace + "\n" + runner_workspace

  map_runner_fn = extract_function(component, "buildMapRunner")
  observations_fn = extract_function(component, "mapObservations")
  projection_fn = extract_function(component, "projectionEndpoint")
  lane_decision_slice = map_runner_fn.lower().split("const lane =", 1)[0].split("): maprunner", 1)[-1]
  sort_fn = "b.barrierSort - a.barrierSort" in component

  checks = [
    check("MapWorkspace V3 component exists", "eiq-speed-map-v3" in component),
    check("Race MAP mounted", "<MapWorkspace" in race_workspace),
    check("Runner MAP mounted", "<MapWorkspace" in runner_workspace),
    check("Right-to-left orientation visible", "RACING DIRECTION &lt;-" in component and "Barrier/start side right" in component),
    check("Barrier/start side on right", "eiq-speed-map-v3__barrier" in component and "BARRIERS / START" in component),
    check("Barrier order descending", sort_fn),
    check("Projection extends left from barrier", "--map-end" in component and "right: 8px" in css and "left: var(--map-end)" in css),
    check("Leader projection longer than rearward", "LEADERS: 14" in component and "BACK: 78" in component),
    check("Zone labels correct", all(label in component for label in ["LEAD / FORWARD", "ON PACE", "MIDFIELD", "REARWARD", "BARRIERS / START"])),
    check("Old four lane board removed", "eiq-speed-map__lanes" not in component and "eiq-speed-map__lane" not in component and "eiq-speed-map__lanes" not in css),
    check("Runner row shows no/runner/barrier/jockey/trainer/weight/map/market", all(label in component for label in ["Runner Map Table", "Barrier", "Jockey", "Trainer", "Weight", "Market"])),
    check("Scratched runners subdued", "isScratched" in component and "is-scratched" in component and "filter: grayscale" in css),
    check("Scratched runners excluded from active pressure counts", "const active = rows.filter((row) => !row.scratched)" in component),
    check("Shape Pressure secondary panel", "Shape Pressure" in component),
    check("Track Read secondary panel", "Track Read" in component),
    check("Evidence Key subtle", "EvidenceKey" in component and "eiq-map-evidence-key" in css),
    check("Runner mini-map exists", "RunnerMiniMap" in component and "eiq-runner-mini-map" in css),
    check("No banned UI language reintroduced", not re.search(r"\b(FEEDS|COMMAND|Analyst Summary|Background Run|Historical Reference|AI predicts)\b", component + "\n" + css[css.find(".eiq-map-workspace {"):css.find("/* EDGEIQ OS navigation restructure */", css.find(".eiq-map-workspace {"))])),
    check("No star symbols in MAP source", "â˜…" not in component and "â˜†" not in component),
    check("No unsafe any in MapWorkspace", re.search(r"\bany\b", component) is None),
    check("Classification does not use market", "marketText" in map_runner_fn and "market" not in lane_decision_slice),
    check("Classification does not use barrier before row assignment", "barrier" not in lane_decision_slice),
    check("Classification does not use finishing position", "finish" not in observations_fn.lower()),
    check("Shared-template detection exists", "shared-template" in component and "sharedTemplateSignatures" in component),
    check("Shared template downgraded", 'if (usesSharedTemplate) return "Limited evidence"' in component),
    check("Strong evidence guarded away from shared template", 'if (usesSharedTemplate) return "Limited evidence"' in component and 'if (observations.length >= 3) return "Strong evidence"' in component),
    check("Fallback source remains limited", 'return "limited"' in component and 'return "Limited evidence"' in component),
    check("Projection length not based on barrier or market", "barrier" not in projection_fn.lower() and "market" not in projection_fn.lower()),
    check("CSS V3 map block present", ".eiq-map-layout-v3" in css and ".eiq-speed-map-v3__row" in css),
  ]

  build_ok, build_output = run_build()
  checks.append(check("npm run build passes", build_ok, build_output))

  lines = ["EDGEIQ_MAP_WORKSPACE_V3_AUDIT"]
  failed = 0
  for name, condition, detail in checks:
    status = "PASS" if condition else "FAIL"
    if not condition:
      failed += 1
    lines.append(f"{status}: {name}")
    if detail and not condition:
      lines.append(f"  {detail}")

  lines.append("")
  lines.extend(live_snapshot_diagnostics())
  lines.append("")
  lines.append("RESULT: " + ("EDGEIQ_MAP_WORKSPACE_V3_AUDIT_PASS" if failed == 0 else "EDGEIQ_MAP_WORKSPACE_V3_AUDIT_FAIL"))

  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("\n".join(lines))
  if failed:
    raise SystemExit(1)


if __name__ == "__main__":
  main()

