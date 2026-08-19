import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SOURCE = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
REPORT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_ACTUAL_RUN_SCHEMA_DIAGNOSTIC.txt"

if not SOURCE.exists():
    raise SystemExit(f"MISSING_SOURCE={SOURCE}")

with SOURCE.open("r", encoding="utf-8-sig") as handle:
    payload = json.load(handle)

races = payload.get("races", []) if isinstance(payload, dict) else []

runner_count = 0
runners_with_full_form = 0
historical_run_count = 0

runner_key_counts = Counter()
run_key_counts = Counter()
epi_type_counts = Counter()
rating_type_counts = Counter()
historical_epi_type_counts = Counter()
race_rating_type_counts = Counter()
position_type_counts = Counter()
sectional_type_counts = Counter()

field_non_blank = Counter()

samples = []
sample_limit = 12

def is_populated(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True

for race_index, race in enumerate(races):
    if not isinstance(race, dict):
        continue

    runners = race.get("runners", [])
    if not isinstance(runners, list):
        continue

    for runner_index, runner in enumerate(runners):
        if not isinstance(runner, dict):
            continue

        runner_count += 1
        runner_key_counts.update(runner.keys())

        epi_type_counts[type(runner.get("epi")).__name__] += 1
        rating_type_counts[type(runner.get("rating")).__name__] += 1

        full_form = runner.get("fullForm")

        if not isinstance(full_form, list) or not full_form:
            continue

        runners_with_full_form += 1

        for run_index, run in enumerate(full_form):
            if not isinstance(run, dict):
                continue

            historical_run_count += 1
            run_key_counts.update(run.keys())

            historical_epi_type_counts[type(run.get("historicalEpi")).__name__] += 1
            race_rating_type_counts[type(run.get("raceRating")).__name__] += 1

            position_value = (
                run.get("positionInRunning")
                if "positionInRunning" in run
                else run.get("position_in_running")
            )
            position_type_counts[type(position_value).__name__] += 1
            sectional_type_counts[type(run.get("sectionalIndices")).__name__] += 1

            candidate_fields = {
                "performanceRating": run.get("performanceRating"),
                "historicalEpi": run.get("historicalEpi"),
                "raceRating": run.get("raceRating"),
                "positionInRunning": run.get("positionInRunning"),
                "position_in_running": run.get("position_in_running"),
                "inRunning": run.get("inRunning"),
                "settlingPosition": run.get("settlingPosition"),
                "sectionalIndices": run.get("sectionalIndices"),
                "esi800600": run.get("esi800600"),
                "esi600400": run.get("esi600400"),
                "esi400200": run.get("esi400200"),
                "esi200F": run.get("esi200F"),
            }

            for key, value in candidate_fields.items():
                if is_populated(value):
                    field_non_blank[key] += 1

            if len(samples) < sample_limit:
                samples.append({
                    "race_index": race_index,
                    "meeting": race.get("meeting"),
                    "race_date": race.get("raceDate"),
                    "race_number": race.get("raceNumber"),
                    "runner_index": runner_index,
                    "runner_id": runner.get("runnerId"),
                    "runner_name": runner.get("runnerName"),
                    "runner_epi": runner.get("epi"),
                    "runner_rating": runner.get("rating"),
                    "run_index": run_index,
                    "run": run,
                })

lines = []

lines.append("EDGEIQ FORM GUIDE ACTUAL RUN SCHEMA DIAGNOSTIC")
lines.append("=" * 76)
lines.append(f"SOURCE={SOURCE}")
lines.append(f"RACES={len(races)}")
lines.append(f"RUNNERS={runner_count}")
lines.append(f"RUNNERS_WITH_FULL_FORM={runners_with_full_form}")
lines.append(f"HISTORICAL_RUNS={historical_run_count}")
lines.append("")

lines.append("TOP RUNNER KEYS")
lines.append("-" * 76)
for key, count in runner_key_counts.most_common():
    lines.append(f"{key}: {count}")
lines.append("")

lines.append("TOP HISTORICAL RUN KEYS")
lines.append("-" * 76)
for key, count in run_key_counts.most_common():
    lines.append(f"{key}: {count}")
lines.append("")

lines.append("FIELD NON-BLANK COVERAGE")
lines.append("-" * 76)
for key in [
    "performanceRating",
    "historicalEpi",
    "raceRating",
    "positionInRunning",
    "position_in_running",
    "inRunning",
    "settlingPosition",
    "sectionalIndices",
    "esi800600",
    "esi600400",
    "esi400200",
    "esi200F",
]:
    lines.append(f"{key}: {field_non_blank[key]}/{historical_run_count}")
lines.append("")

lines.append("VALUE TYPE COUNTS")
lines.append("-" * 76)
lines.append(f"RUNNER_EPI_TYPES={dict(epi_type_counts)}")
lines.append(f"RUNNER_RATING_TYPES={dict(rating_type_counts)}")
lines.append(f"HISTORICAL_EPI_TYPES={dict(historical_epi_type_counts)}")
lines.append(f"RACE_RATING_TYPES={dict(race_rating_type_counts)}")
lines.append(f"POSITION_IN_RUNNING_TYPES={dict(position_type_counts)}")
lines.append(f"SECTIONAL_INDICES_TYPES={dict(sectional_type_counts)}")
lines.append("")

lines.append("REAL HISTORICAL RUN SAMPLES")
lines.append("=" * 76)
for sample in samples:
    lines.append(json.dumps(sample, ensure_ascii=False, indent=2, default=str))
    lines.append("-" * 76)

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"WROTE={REPORT}")
print(f"RACES={len(races)}")
print(f"RUNNERS={runner_count}")
print(f"RUNNERS_WITH_FULL_FORM={runners_with_full_form}")
print(f"HISTORICAL_RUNS={historical_run_count}")
print("FIELD_NON_BLANK=" + json.dumps(dict(field_non_blank), sort_keys=True))
print("RUNNER_EPI_TYPES=" + json.dumps(dict(epi_type_counts), sort_keys=True))
print("HISTORICAL_EPI_TYPES=" + json.dumps(dict(historical_epi_type_counts), sort_keys=True))
print("RACE_RATING_TYPES=" + json.dumps(dict(race_rating_type_counts), sort_keys=True))
print("POSITION_TYPES=" + json.dumps(dict(position_type_counts), sort_keys=True))
print("SECTIONAL_TYPES=" + json.dumps(dict(sectional_type_counts), sort_keys=True))
print("EDGEIQ_FORM_GUIDE_ACTUAL_RUN_SCHEMA_DIAGNOSTIC_PASS")
