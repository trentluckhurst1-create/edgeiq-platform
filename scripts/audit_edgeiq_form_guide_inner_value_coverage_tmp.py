import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SOURCE = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
REPORT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_INNER_VALUE_COVERAGE_AUDIT.txt"

with SOURCE.open("r", encoding="utf-8-sig") as handle:
    payload = json.load(handle)

def unwrap(value):
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value

def populated(value):
    value = unwrap(value)

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return True

fields = [
    "performanceRating",
    "historicalEpi",
    "raceRating",
    "historicalEarlySpeed",
    "historicalLateSpeed",
    "historicalSpeedRating",
    "historicalSuitability",
    "historicalFormMomentum",
    "benchmarkEvidence",
]

sectional_fields = [
    "index800To600",
    "index600To400",
    "index400To200",
    "index200ToFinish",
    "finishLen",
]

coverage = Counter()
sources = {field: Counter() for field in fields}
sectional_coverage = Counter()
sectional_sources = {field: Counter() for field in sectional_fields}

historical_runs = 0
runs_with_any_sectional_move = 0
runs_with_all_sectional_moves = 0

populated_examples = {
    "historicalEpi": [],
    "raceRating": [],
    "historicalSpeedRating": [],
    "sectionalMoves": [],
}

for race in payload.get("races", []):
    if not isinstance(race, dict):
        continue

    for runner in race.get("runners", []):
        if not isinstance(runner, dict):
            continue

        for run in runner.get("fullForm", []):
            if not isinstance(run, dict):
                continue

            historical_runs += 1

            identity = {
                "meeting": race.get("meeting"),
                "raceDate": race.get("raceDate"),
                "currentRaceNumber": race.get("raceNumber"),
                "runnerId": runner.get("runnerId"),
                "runnerName": runner.get("runnerName"),
                "runDate": run.get("date"),
                "runTrack": run.get("track"),
                "runRaceNumber": run.get("raceNumber"),
            }

            for field in fields:
                raw = run.get(field)

                if populated(raw):
                    coverage[field] += 1

                    if isinstance(raw, dict):
                        source = raw.get("source")
                        if source:
                            sources[field][str(source)] += 1

                    if field in populated_examples and len(populated_examples[field]) < 10:
                        populated_examples[field].append({
                            **identity,
                            field: raw,
                        })

            sectionals = run.get("sectionalIndices")
            move_count = 0

            if isinstance(sectionals, dict):
                for field in sectional_fields:
                    raw = sectionals.get(field)

                    if populated(raw):
                        sectional_coverage[field] += 1

                        if field != "finishLen":
                            move_count += 1

                        if isinstance(raw, dict):
                            source = raw.get("source")
                            if source:
                                sectional_sources[field][str(source)] += 1

            if move_count > 0:
                runs_with_any_sectional_move += 1

                if len(populated_examples["sectionalMoves"]) < 10:
                    populated_examples["sectionalMoves"].append({
                        **identity,
                        "sectionalIndices": sectionals,
                    })

            if move_count == 4:
                runs_with_all_sectional_moves += 1

lines = []
lines.append("EDGEIQ FORM GUIDE INNER VALUE COVERAGE AUDIT")
lines.append("=" * 78)
lines.append(f"HISTORICAL_RUNS={historical_runs}")
lines.append("")

lines.append("HISTORICAL INTELLIGENCE INNER-VALUE COVERAGE")
lines.append("-" * 78)

for field in fields:
    count = coverage[field]
    pct = (count / historical_runs * 100) if historical_runs else 0
    lines.append(f"{field}: {count}/{historical_runs} ({pct:.2f}%)")

lines.append("")
lines.append("SECTIONAL INNER-VALUE COVERAGE")
lines.append("-" * 78)

for field in sectional_fields:
    count = sectional_coverage[field]
    pct = (count / historical_runs * 100) if historical_runs else 0
    lines.append(f"{field}: {count}/{historical_runs} ({pct:.2f}%)")

lines.append(f"runsWithAnySectionalMove: {runs_with_any_sectional_move}/{historical_runs}")
lines.append(f"runsWithAllFourSectionalMoves: {runs_with_all_sectional_moves}/{historical_runs}")

lines.append("")
lines.append("SOURCE COUNTS")
lines.append("=" * 78)

for field in fields:
    lines.append(f"\n{field}")
    for source, count in sources[field].most_common():
        lines.append(f"  {source}: {count}")

for field in sectional_fields:
    lines.append(f"\nsectionalIndices.{field}")
    for source, count in sectional_sources[field].most_common():
        lines.append(f"  {source}: {count}")

lines.append("")
lines.append("POPULATED EXAMPLES")
lines.append("=" * 78)

for group, examples in populated_examples.items():
    lines.append(f"\n{group}")
    lines.append("-" * 78)

    if not examples:
        lines.append("NO POPULATED EXAMPLES")
        continue

    for example in examples:
        lines.append(json.dumps(example, indent=2, ensure_ascii=False))
        lines.append("")

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"WROTE={REPORT}")
print(f"HISTORICAL_RUNS={historical_runs}")

for field in fields:
    print(f"{field}={coverage[field]}/{historical_runs}")

for field in sectional_fields:
    print(f"sectionalIndices.{field}={sectional_coverage[field]}/{historical_runs}")

print(f"RUNS_WITH_ANY_SECTIONAL_MOVE={runs_with_any_sectional_move}/{historical_runs}")
print(f"RUNS_WITH_ALL_SECTIONAL_MOVES={runs_with_all_sectional_moves}/{historical_runs}")
print("EDGEIQ_FORM_GUIDE_INNER_VALUE_COVERAGE_AUDIT_PASS")
