from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BUILDER = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"
OUT = (
    ROOT
    / "docs"
    / "full-product-implementation"
    / "HISTORICAL_EPI_RUNTIME_TRAVERSAL_PROBE.txt"
)

spec = importlib.util.spec_from_file_location(
    "edgeiq_epi_builder_runtime_probe",
    BUILDER,
)

if spec is None or spec.loader is None:
    raise SystemExit("BUILDER_IMPORT_FAILED")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

catalog_payload = module.read_json(module.CATALOG)
form_payload = module.read_json(module.FORM_GUIDE)

catalog_pairs = module.catalog_races(catalog_payload)
form_races = module.form_race_index(form_payload)
required_keys = module.collect_historical_keys(form_races)
historical = module.historical_rating_index(required_keys)

counters = Counter()
samples: list[str] = []

for meeting, race in catalog_pairs:
    counters["catalog_races"] += 1

    race_key = module.race_match_key(
        race.get("raceDate") or meeting.get("date"),
        race.get("track") or meeting.get("meeting"),
        race.get("raceNumber") or race.get("raceNo"),
    )

    form_race = form_races.get(race_key)

    if not form_race:
        counters["catalog_races_without_form_match"] += 1
        continue

    counters["catalog_races_with_form_match"] += 1

    runners = form_race.get("runners", []) or []

    for runner in runners:
        if not isinstance(runner, dict):
            continue

        counters["runners"] += 1
        full_form = runner.get("fullForm", []) or []

        if not full_form:
            counters["runners_without_full_form"] += 1
            continue

        counters["runners_with_full_form"] += 1

        for run_index, run in enumerate(full_form[:10], start=1):
            if not isinstance(run, dict):
                counters["non_dict_runs"] += 1
                continue

            counters["historical_runs_tested"] += 1

            epi, source, version = module.historical_epi_for_run(
                runner,
                run,
                historical,
            )

            if epi is None:
                counters["runtime_lookup_blank"] += 1
                continue

            counters["runtime_lookup_populated"] += 1

            if len(samples) < 30:
                samples.append(
                    " | ".join(
                        [
                            module.runner_name(runner),
                            module.clean(run.get("date")),
                            module.clean(run.get("track")),
                            f"{module.number_text(run.get('distance'))}m",
                            f"EPI={epi}",
                            f"SOURCE={source}",
                            f"RUN_SLOT={run_index}",
                        ]
                    )
                )

report = [
    "EDGEIQ HISTORICAL EPI RUNTIME TRAVERSAL PROBE",
    "=" * 110,
    "",
]

for key in [
    "catalog_races",
    "catalog_races_with_form_match",
    "catalog_races_without_form_match",
    "runners",
    "runners_with_full_form",
    "runners_without_full_form",
    "historical_runs_tested",
    "runtime_lookup_populated",
    "runtime_lookup_blank",
    "non_dict_runs",
]:
    report.append(f"{key.upper()}={counters[key]}")

report.extend(
    [
        "",
        "POPULATED RUNTIME SAMPLE",
        "-" * 110,
    ]
)

report.extend(samples or ["NO_POPULATED_RUNTIME_SAMPLES"])

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print(f"WROTE={OUT}")

if counters["runtime_lookup_populated"] == 0:
    raise SystemExit("RUNTIME_TRAVERSAL_FOUND_ZERO_POPULATED_LOOKUPS")

print("EDGEIQ_HISTORICAL_EPI_RUNTIME_TRAVERSAL_PROBE_PASS")
