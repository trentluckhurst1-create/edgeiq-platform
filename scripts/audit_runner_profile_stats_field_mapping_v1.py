from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_v1.csv"
SNAPSHOT_FILE = ROOT / "src" / "edgeiq-os" / "services" / "live-race-data-snapshot.ts"
OUTPUT_FILE = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_field_mapping_v1.txt"

COUNTRY_SUFFIX_RE = re.compile(r"\s+\((?:NZ|IRE|GB|USA|FR|JPN|AUS|SAF|GER)\)\s*$", re.IGNORECASE)
PUNCT_RE = re.compile(r"[^A-Z0-9\s]+")
SPACE_RE = re.compile(r"\s+")

FIELDS = [
    "career_starts",
    "career_wins",
    "career_places",
    "career_win_pct",
    "career_place_pct",
    "latest_track_starts",
    "latest_distance_starts",
    "first_up_starts",
    "last_5_starts",
    "avg_sp",
    "best_sp",
    "last_start_sp",
]


def normalise_runner_name(value: object) -> str:
    text = str(value or "")
    text = text.replace("’", "'").replace("`", "'").replace("´", "'")
    text = COUNTRY_SUFFIX_RE.sub("", text.strip())
    text = text.upper().strip()
    text = PUNCT_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def read_profile_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with PROFILE_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for field in ("normalized_runner", "runner", "latest_runner_name", "resolved_runner_key"):
                key = normalise_runner_name(row.get(field, ""))
                if key:
                    rows.setdefault(key, row)
    return rows


def active_runners() -> list[str]:
    if not SNAPSHOT_FILE.exists():
        return ["KING TAGALOA"]
    text = SNAPSHOT_FILE.read_text(encoding="utf-8", errors="ignore")
    runners = [match.group(1).strip() for match in re.finditer(r"runner:\s*['\"]([^'\"]+)['\"]", text)]
    selected = ["KING TAGALOA"]
    for runner in runners:
        if runner not in selected:
            selected.append(runner)
        if len(selected) >= 8:
            break
    return selected


def main() -> int:
    profiles = read_profile_rows()
    lines = [
        "EDGEIQ RUNNER PROFILE STATS FIELD MAPPING V1",
        f"Profile file: {PROFILE_FILE.relative_to(ROOT)}",
        f"Active source: {SNAPSHOT_FILE.relative_to(ROOT)}",
        "",
    ]

    for runner in active_runners():
        key = normalise_runner_name(runner)
        row = profiles.get(key)
        lines.append(f"Runner: {runner}")
        lines.append(f"Normalised: {key}")
        lines.append(f"Matched row found: {'YES' if row else 'NO'}")
        if row:
            for field in FIELDS:
                lines.append(f"- {field}: {row.get(field, '')}")
        lines.append("")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
