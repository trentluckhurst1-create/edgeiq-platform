from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BUILDER = ROOT / "scripts" / "build_edgeiq_epi_workspace_terminal_feed_v1.py"

spec = importlib.util.spec_from_file_location(
    "edgeiq_epi_builder_probe",
    BUILDER,
)

if spec is None or spec.loader is None:
    raise SystemExit("BUILDER_IMPORT_SPEC_FAILED")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

catalog = module.read_json(module.CATALOG)
form_payload = module.read_json(module.FORM_GUIDE)
form_races = module.form_race_index(form_payload)

required_keys = module.collect_historical_keys(form_races)
historical = module.historical_rating_index(required_keys)

status_counts = Counter(
    str(result.get("status", ""))
    for result in historical.values()
)

print("EDGEIQ HISTORICAL EPI GOVERNED LOOKUP PROBE")
print("=" * 100)
print(f"FORM_RACES={len(form_races)}")
print(f"REQUIRED_HISTORICAL_KEYS={len(required_keys)}")
print(f"GOVERNED_LOOKUP_KEYS={len(historical)}")

for status, count in sorted(status_counts.items()):
    print(f"{status}={count}")

accepted = {
    key: result
    for key, result in historical.items()
    if result.get("status") in {
        "UNIQUE",
        "SAME_RATING_MULTIPLE_ROWS",
    }
    and result.get("rating") is not None
}

conflicts = {
    key: result
    for key, result in historical.items()
    if result.get("status") == "CONFLICTING_RATINGS"
}

print(f"ACCEPTED_GOVERNED_MATCHES={len(accepted)}")
print(f"REJECTED_CONFLICTS={len(conflicts)}")
print("")

print("ACCEPTED SAMPLE")
print("-" * 100)

for key, result in list(sorted(accepted.items()))[:20]:
    print(
        " | ".join(
            [
                str(key[0]),
                str(key[1]),
                str(key[2]),
                f"{key[3]}m",
                str(result.get("rating")),
                str(result.get("status")),
            ]
        )
    )

if not accepted:
    raise SystemExit("BLOCKED_NO_ACCEPTED_GOVERNED_MATCHES")

print("EDGEIQ_HISTORICAL_EPI_GOVERNED_LOOKUP_PROBE_PASS")
