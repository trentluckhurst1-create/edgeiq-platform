from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

STATIONS = {
    "GEELONG": ROOT / "data" / "weather-source-audit" / "bom-live" / "87184" / "latest_raw.json",
    "HAMILTON": ROOT / "data" / "weather-source-audit" / "bom-live" / "90173" / "latest_raw.json",
}

TOKENS = (
    "temp",
    "apparent",
    "dew",
    "humid",
    "precip",
    "rain",
    "wind",
    "gust",
    "press",
    "datetime",
    "station",
    "name",
    "lat",
    "lon",
)


def flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten(child, path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]"
            rows.extend(flatten(child, path))

    else:
        rows.append((prefix, value))

    return rows


report: list[str] = [
    "EDGEIQ BOM EXACT FIELD PATH AUDIT",
    "=" * 60,
    "",
]

for meeting, path in STATIONS.items():
    report.extend(
        [
            "",
            "=" * 60,
            meeting,
            "=" * 60,
            f"Source: {path}",
            "",
        ]
    )

    if not path.exists():
        report.append("RAW PAYLOAD NOT FOUND")
        continue

    payload = json.loads(path.read_text(encoding="utf-8"))

    rows = flatten(payload)

    for field_path, value in sorted(rows):
        if value is None:
            continue

        lower = field_path.lower()

        if any(token in lower for token in TOKENS):
            report.append(f"{field_path} = {value}")

output = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "EDGEIQ_BOM_EXACT_FIELD_PATH_AUDIT.txt"
)

output.write_text(
    "\n".join(report),
    encoding="utf-8",
)

print(f"[EDGEIQ] Exact BOM field audit written: {output}")
