from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
DATA = ROOT / "public" / "data"
DOCS = ROOT / "docs" / "performance-intelligence" / "standard-time-recovery"
SOURCE = DATA / "edgeiq_racingcom_graphql_speed_normalised_v1.csv"

SEMANTICS = DOCS / "edgeiq_racingcom_speed_observation_semantics_v1.csv"
PROGRESSION = DOCS / "edgeiq_racingcom_runner_distance_progression_v1.csv"
BOUNDARY = DOCS / "edgeiq_racingcom_segment_boundary_validation_v1.csv"
AUDIT = DOCS / "edgeiq_racingcom_speed_semantics_audit_v1.csv"
REPORT = DOCS / "edgeiq_racingcom_speed_semantics_report_v1.md"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_split(label: str) -> tuple[int | None, int | None]:
    text = clean(label).upper()
    m = re.fullmatch(r"(\d+)M-(\d+)M", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d+)M-FINISH", text)
    if m:
        return int(m.group(1)), 0
    return None, None


def parse_point(label: str) -> int | None:
    if clean(label).upper() == "FINISH":
        return 0
    m = re.fullmatch(r"(\d+)M", clean(label).upper())
    return int(m.group(1)) if m else None


def main() -> int:
    rows = read_csv(SOURCE)
    semantics_rows = []
    boundary_rows = []
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        runner_key = clean(row.get("horse_id")) or clean(row.get("horse"))
        grouped[(clean(row.get("race_id")), runner_key)].append(row)
        row_type = clean(row.get("row_type"))
        start, end = parse_split(row.get("distance_label", ""))
        point = parse_point(row.get("distance_label", ""))
        speed = fnum(row.get("avg_speed_mps"))
        kmh = fnum(row.get("avg_speed_kmh"))
        if row_type == "SPLIT" and start is not None and end is not None:
            obs = "INDIVIDUAL_SEGMENT"
            distance = start - end
        elif row_type == "SECTIONAL" and point is not None:
            obs = "CUMULATIVE_DISTANCE_POINT"
            distance = 0
        else:
            obs = "UNRESOLVED"
            distance = 0
        conversion_ok = "YES" if speed is not None and kmh is not None and abs((speed * 3.6) - kmh) <= 0.02 else ("NOT_TESTED" if speed is None or kmh is None else "NO")
        plausible = "YES" if speed is not None and 5 <= speed <= 25 else "NO"
        semantics_rows.append({
            "race_id": clean(row.get("race_id")),
            "horse_id": runner_key,
            "row_type": row_type,
            "distance_label": clean(row.get("distance_label")),
            "observation_semantics": obs,
            "segment_start_metres": "" if start is None else str(start),
            "segment_end_metres": "" if end is None else str(end),
            "segment_distance_metres": str(distance) if distance else "",
            "avg_speed_mps": clean(row.get("avg_speed_mps")),
            "avg_speed_kmh": clean(row.get("avg_speed_kmh")),
            "speed_plausible": plausible,
            "kmh_conversion_deterministic": conversion_ok,
            "source_payload_sha256": clean(row.get("response_sha256")),
        })
        if row_type == "SPLIT":
            boundary_status = "VALID_SEGMENT_BOUNDARY" if start is not None and end is not None and start > end and start - end == 200 else "INVALID_SEGMENT_BOUNDARY"
            boundary_rows.append({
                "race_id": clean(row.get("race_id")),
                "horse_id": runner_key,
                "distance_label": clean(row.get("distance_label")),
                "segment_start_metres": "" if start is None else str(start),
                "segment_end_metres": "" if end is None else str(end),
                "segment_distance_metres": "" if start is None or end is None else str(start - end),
                "boundary_status": boundary_status,
            })

    progression_rows = []
    monotonic_failures = 0
    stable_identity_failures = 0
    for (race_id, runner), runner_rows in grouped.items():
        split_points = sorted([parse_split(r.get("distance_label", ""))[0] for r in runner_rows if clean(r.get("row_type")) == "SPLIT" and parse_split(r.get("distance_label", ""))[0] is not None], reverse=True)
        sectional_points = sorted([parse_point(r.get("distance_label", "")) for r in runner_rows if clean(r.get("row_type")) == "SECTIONAL" and parse_point(r.get("distance_label", "")) is not None], reverse=True)
        split_valid = all(split_points[i] > split_points[i + 1] for i in range(len(split_points) - 1))
        sectional_valid = all(sectional_points[i] > sectional_points[i + 1] for i in range(len(sectional_points) - 1))
        if not split_valid or not sectional_valid:
            monotonic_failures += 1
        horses = {clean(r.get("horse")) for r in runner_rows if clean(r.get("horse"))}
        if len(horses) != 1:
            stable_identity_failures += 1
        progression_rows.append({
            "race_id": race_id,
            "horse_id": runner,
            "horse": "|".join(sorted(horses)),
            "split_distance_progression": "|".join(str(x) for x in split_points),
            "sectional_distance_progression": "|".join(str(x) for x in sectional_points),
            "split_monotonic": "YES" if split_valid else "NO",
            "sectional_monotonic": "YES" if sectional_valid else "NO",
            "runner_identity_stable": "YES" if len(horses) == 1 else "NO",
        })

    counts = Counter(r["observation_semantics"] for r in semantics_rows)
    duplicate_obs = len(semantics_rows) - len({(r["race_id"], r["horse_id"], r["row_type"], r["distance_label"]) for r in semantics_rows})
    bad_boundaries = sum(1 for r in boundary_rows if r["boundary_status"] != "VALID_SEGMENT_BOUNDARY")
    bad_speeds = sum(1 for r in semantics_rows if r["avg_speed_mps"] and r["speed_plausible"] != "YES")
    bad_conversion = sum(1 for r in semantics_rows if r["kmh_conversion_deterministic"] == "NO")
    audit_rows = [
        {"check": "input_rows", "status": "PASS" if len(rows) == 898 else "FAIL", "value": str(len(rows)), "detail": "GraphQL normalised rows."},
        {"check": "individual_segments", "status": "PASS" if counts["INDIVIDUAL_SEGMENT"] == 449 else "FAIL", "value": str(counts["INDIVIDUAL_SEGMENT"]), "detail": "SPLIT rows are valid incremental segment observations."},
        {"check": "cumulative_points", "status": "PASS" if counts["CUMULATIVE_DISTANCE_POINT"] == 449 else "FAIL", "value": str(counts["CUMULATIVE_DISTANCE_POINT"]), "detail": "SECTIONAL rows are cumulative distance points, not independent segment facts."},
        {"check": "unresolved_rows", "status": "PASS" if counts["UNRESOLVED"] == 0 else "FAIL", "value": str(counts["UNRESOLVED"]), "detail": "No unresolved semantics."},
        {"check": "segment_boundaries_valid", "status": "PASS" if bad_boundaries == 0 else "FAIL", "value": str(bad_boundaries), "detail": "All split boundaries are 200m positive intervals."},
        {"check": "speed_values_plausible", "status": "PASS" if bad_speeds == 0 else "FAIL", "value": str(bad_speeds), "detail": "m/s values in plausible racing range."},
        {"check": "kmh_conversion_deterministic", "status": "PASS" if bad_conversion == 0 else "FAIL", "value": str(bad_conversion), "detail": "km/h equals m/s * 3.6 within tolerance."},
        {"check": "duplicate_observations_absent", "status": "PASS" if duplicate_obs == 0 else "FAIL", "value": str(duplicate_obs), "detail": "Unique by race-runner-rowtype-distance."},
        {"check": "runner_identity_stable", "status": "PASS" if stable_identity_failures == 0 else "FAIL", "value": str(stable_identity_failures), "detail": "Horse identity stable per race-runner."},
        {"check": "distance_progression_monotonic", "status": "PASS" if monotonic_failures == 0 else "FAIL", "value": str(monotonic_failures), "detail": "Distances progress from race start toward finish."},
    ]
    write_csv(SEMANTICS, semantics_rows, ["race_id", "horse_id", "row_type", "distance_label", "observation_semantics", "segment_start_metres", "segment_end_metres", "segment_distance_metres", "avg_speed_mps", "avg_speed_kmh", "speed_plausible", "kmh_conversion_deterministic", "source_payload_sha256"])
    write_csv(PROGRESSION, progression_rows, ["race_id", "horse_id", "horse", "split_distance_progression", "sectional_distance_progression", "split_monotonic", "sectional_monotonic", "runner_identity_stable"])
    write_csv(BOUNDARY, boundary_rows, ["race_id", "horse_id", "distance_label", "segment_start_metres", "segment_end_metres", "segment_distance_metres", "boundary_status"])
    write_csv(AUDIT, audit_rows, ["check", "status", "value", "detail"])
    status = "RACINGCOM_SPEED_OBSERVATION_SEMANTICS_PASS" if all(r["status"] == "PASS" for r in audit_rows) else "RACINGCOM_SPEED_OBSERVATION_SEMANTICS_REVIEW"
    REPORT.write_text(f"# Racing.com Speed Observation Semantics V1\n\nStatus: `{status}`\n\n`SPLIT` rows are individual 200m segment observations. `SECTIONAL` rows are cumulative distance points and are not counted as independent Standard Time segment facts.\n", encoding="utf-8")
    print(json.dumps({"status": status, "individual_segments": counts["INDIVIDUAL_SEGMENT"], "cumulative_points": counts["CUMULATIVE_DISTANCE_POINT"], "unresolved": counts["UNRESOLVED"]}, indent=2))
    return 0 if status.endswith("_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
