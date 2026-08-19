from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "src" / "edgeiq-os" / "race" / "components" / "MapWorkspace.tsx"
RACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
RUNNER = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RunnerProfileWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
OUT = ROOT / "public" / "data" / "edgeiq_map_workspace_v2_audit.txt"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def add(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def run_build() -> tuple[bool, str]:
    completed = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    tail = "\n".join(completed.stdout.splitlines()[-12:])
    return completed.returncode == 0, tail


def section_between(text: str, start_marker: str, end_marker: str) -> str:
    if start_marker not in text or end_marker not in text:
        return ""
    return text.split(start_marker, 1)[1].split(end_marker, 1)[0]


def main() -> None:
    map_text = read(MAP)
    race_text = read(RACE)
    runner_text = read(RUNNER)
    css_text = read(CSS)
    all_map_impl = "\n".join([map_text, race_text, runner_text])
    results: list[tuple[str, bool, str]] = []

    add(results, "MAP workspace exists", MAP.exists())
    add(results, "MAP workspace is mounted in race workspace", "MapWorkspace" in race_text and 'from "./MapWorkspace"' in race_text)
    add(results, "MAP workspace is mounted in runner workspace", "MapWorkspace" in runner_text and 'mode="runner"' in runner_text)
    for lane in ["LEADERS", "ON PACE", "MIDFIELD", "BACK"]:
        add(results, f"{lane} lane exists", lane in map_text)
    add(results, "Runner number is rendered", "runnerNumber(" in map_text)
    add(results, "Runner name is rendered", '["official", "runner"]' in map_text)
    add(results, "Barrier is rendered", "Bar" in map_text and '["official", "barrier"]' in map_text)
    add(results, "Jockey is rendered", '["official", "jockey"]' in map_text)
    add(results, "Trainer is rendered", '["official", "trainer"]' in map_text)
    add(results, "Market is optional and safely handled", "runnerMarket" in map_text and "marketText ?" in map_text)
    add(results, "Evidence confidence treatment exists", "ConfidenceState" in map_text and "Evidence Read" in map_text)
    for state in ["Strong evidence", "Supported", "Limited evidence"]:
        add(results, f"{state} state exists", state in map_text)
    add(results, "Shape Pressure treatment exists", "Shape Pressure" in map_text and "shapePressureNotes" in map_text)
    add(results, "Runner-level Expected Position exists", "Expected Position" in map_text)
    add(results, "Runner-level Barrier context exists", "Barrier And Early Position" in map_text and "barrierContext" in map_text)
    add(results, "Runner-level Tempo Fit exists", "tempoFit" in map_text and "Tempo And Pressure Fit" in map_text)
    add(results, "Runner-level Pressure Fit exists", "pressureFit" in map_text)
    add(results, "Map Positive exists", "mapPositive" in map_text and "Map Positive / Map Risk" in map_text)
    add(results, "Map Risk exists", "mapRisk" in map_text and "Map Positive / Map Risk" in map_text)
    add(results, "Today's Map Summary exists", "Today's Map Summary" in map_text)
    add(results, "Early Watch exists", "Early Watch" in map_text)

    forbidden_patterns = [
        ("FEEDS", re.compile(r"\bFEEDS\b", re.I)),
        ("Analyst Summary", re.compile(r"Analyst Summary", re.I)),
        ("REF", re.compile(r"\bREF\b", re.I)),
        ("Background Run", re.compile(r"Background Run", re.I)),
        ("Historical Reference", re.compile(r"Historical Reference", re.I)),
        ("COMMAND", re.compile(r"\bCOMMAND\b", re.I)),
        ("AI predicts", re.compile(r"AI predicts", re.I)),
    ]
    for label, pattern in forbidden_patterns:
        add(results, f"No {label} text exists in MAP implementation", pattern.search(all_map_impl) is None)

    add(results, "No star graphics or star-rating language exists", not re.search(r"[\u2605\u2606]|star\s*rating|rating\s*star", map_text, re.I))
    add(results, "No unsafe any in MAP implementation", "any" not in map_text)
    placement_sections = "\n".join([
        section_between(map_text, "function mapRunner", "function laneRank"),
        section_between(map_text, "function buildMap", "function RaceMap"),
    ])
    add(results, "No market-price-driven lane-placement logic exists", "market" not in placement_sections.lower())
    observations = section_between(map_text, "function mapObservations", "function dominantLane").lower()
    add(results, "Placement ignores finishing position", "finish" not in observations)
    add(results, "Placement ignores barrier number", "barrier" not in observations)
    add(results, "MAP CSS exists", ".eiq-map-workspace" in css_text and ".eiq-speed-map__lane" in css_text)

    build_ok, build_tail = run_build()
    add(results, "TypeScript build passes", build_ok, build_tail)

    overall = all(ok for _, ok, _ in results)
    lines = ["EDGEIQ MAP WORKSPACE V2 AUDIT", "=" * 36, f"OVERALL: {'PASS' if overall else 'FAIL'}", ""]
    for name, ok, detail in results:
        lines.append(f"{'PASS' if ok else 'FAIL'} | {name}")
        if detail:
            lines.append(f"       {detail.replace(chr(10), chr(10) + '       ')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    raise SystemExit(0 if overall else 1)


if __name__ == "__main__":
    main()
