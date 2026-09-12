from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT_SUMMARY = DATA / "edgeiq_sectional_race_number_recovery_v4_summary.csv"
OUT_FILES = DATA / "edgeiq_sectional_race_number_recovery_v4_files.csv"
OUT_GROUPS = DATA / "edgeiq_sectional_race_number_recovery_v4_groups.csv"
OUT_SAMPLES = DATA / "edgeiq_sectional_race_number_recovery_v4_samples.csv"

FILES = [
    DATA / "edgeiq_sectional_payload_reconstruction_v1.csv",
    DATA / "edgeiq_sectional_physics_validation_v1.csv",
    DATA / "sectionals.csv",
]

MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a"}
ALIASES = {
    "race_date": ("race_date", "date", "meeting_date", "run_date"),
    "track": ("track", "venue", "meeting", "track_name"),
    "race_no": ("race_no", "race_number", "race"),
    "race_id": ("race_id", "canonical_race_id", "racingcom_race_id", "raceid"),
    "meeting_id": ("meeting_id", "racingcom_meeting_id", "meetingid"),
    "horse": ("horse_name", "horse", "runner_name", "runner", "name"),
    "horse_id": ("canonical_horse_id", "horse_id", "horse_key", "runner_id", "runner_key"),
    "distance": ("distance", "race_distance", "dist", "race_distance_metres"),
    "barrier": ("barrier", "barrier_number", "gate"),
    "finish": ("finish_position", "finishing_position", "position", "place"),
    "meeting_name": ("meeting_name", "meeting", "venue_name"),
    "source_url": ("source_url", "url", "racingcom_url", "source"),
}


def clean(v: object) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def find_col(fields: list[str], aliases: tuple[str, ...]) -> str:
    lookup = {norm(f): f for f in fields}
    for a in aliases:
        k = norm(a)
        if k in lookup:
            return lookup[k]
    return ""


def cols(fields: list[str]) -> dict[str, str]:
    return {k: find_col(fields, v) for k, v in ALIASES.items()}


def get(row: dict[str, str], c: dict[str, str], key: str) -> str:
    col = c.get(key, "")
    return clean(row.get(col)) if col else ""


def extract_race_hint(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"(?:^|[/_\-])race[/_\-]?(\d{1,2})(?:$|[/_\-.?&])",
        r"(?:^|[/_\-])r(\d{1,2})(?:$|[/_\-.?&])",
        r"(?:raceNumber|race_number|raceNo|race_no)[=/:-]?(\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return str(int(m.group(1)))
    return ""


def candidate_embedded_race_no(row: dict[str, str], fields: list[str]) -> tuple[str, str]:
    for f in fields:
        v = clean(row.get(f))
        if not v:
            continue
        h = extract_race_hint(v)
        if h:
            return h, f
    return "", ""


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    total = Counter()
    file_rows = []
    group_rows = []
    samples = []

    for path in FILES:
        if not path.exists():
            file_rows.append({"source_file": str(path.relative_to(ROOT)), "status": "MISSING"})
            total["files_missing"] += 1
            continue

        with path.open("r", newline="", encoding="utf-8-sig") as h:
            reader = csv.DictReader(h)
            fields = list(reader.fieldnames or [])
            c = cols(fields)
            counts = Counter()
            group_stats: dict[tuple[str, str], dict[str, object]] = defaultdict(lambda: {
                "rows": 0, "known_race_nos": Counter(), "embedded_hints": Counter(), "distances": Counter(),
                "race_ids": Counter(), "meeting_ids": Counter(), "row_min": None, "row_max": None,
            })

            for row_no, row in enumerate(reader, 2):
                counts["rows"] += 1
                race_date = get(row, c, "race_date")[:10]
                track = get(row, c, "track")
                race_no = get(row, c, "race_no")
                race_id = get(row, c, "race_id")
                meeting_id = get(row, c, "meeting_id")
                distance = get(row, c, "distance")
                horse = get(row, c, "horse")

                if race_no:
                    counts["rows_with_race_no"] += 1
                else:
                    counts["rows_missing_race_no"] += 1
                if race_id:
                    counts["rows_with_race_id"] += 1
                if meeting_id:
                    counts["rows_with_meeting_id"] += 1
                if race_date:
                    counts["rows_with_date"] += 1
                if track:
                    counts["rows_with_track"] += 1

                hint, hint_field = candidate_embedded_race_no(row, fields)
                if hint:
                    counts["rows_with_embedded_race_hint"] += 1
                    if not race_no:
                        counts["missing_race_no_with_embedded_hint"] += 1

                gk = (race_date, track)
                gs = group_stats[gk]
                gs["rows"] = int(gs["rows"]) + 1
                gs["row_min"] = row_no if gs["row_min"] is None else min(int(gs["row_min"]), row_no)
                gs["row_max"] = row_no if gs["row_max"] is None else max(int(gs["row_max"]), row_no)
                if race_no:
                    gs["known_race_nos"][race_no] += 1
                if hint:
                    gs["embedded_hints"][hint] += 1
                if distance:
                    gs["distances"][distance] += 1
                if race_id:
                    gs["race_ids"][race_id] += 1
                if meeting_id:
                    gs["meeting_ids"][meeting_id] += 1

                if len(samples) < 400 and not race_no:
                    samples.append({
                        "source_file": str(path.relative_to(ROOT)), "row_no": row_no,
                        "race_date": race_date, "track": track, "race_no": race_no,
                        "race_id": race_id, "meeting_id": meeting_id, "distance": distance,
                        "horse": horse, "embedded_race_hint": hint, "hint_field": hint_field,
                        "headers": "|".join(fields[:100]),
                    })

            deterministic_groups = ambiguous_groups = 0
            for (race_date, track), gs in group_stats.items():
                known = gs["known_race_nos"]
                hints = gs["embedded_hints"]
                race_ids = gs["race_ids"]
                recover_method = ""
                recover_value = ""
                if len(known) == 1:
                    recover_method = "SINGLE_KNOWN_RACE_NO_IN_DATE_TRACK_GROUP"
                    recover_value = next(iter(known))
                elif len(hints) == 1:
                    recover_method = "SINGLE_EMBEDDED_RACE_HINT_IN_DATE_TRACK_GROUP"
                    recover_value = next(iter(hints))
                elif len(race_ids) == 1 and len(known) == 0:
                    recover_method = "SINGLE_RACE_ID_GROUP_NEEDS_CROSSWALK"
                elif len(known) > 1 or len(hints) > 1 or len(race_ids) > 1:
                    ambiguous_groups += 1
                if recover_method:
                    deterministic_groups += 1
                group_rows.append({
                    "source_file": str(path.relative_to(ROOT)), "race_date": race_date, "track": track,
                    "rows": gs["rows"], "row_min": gs["row_min"], "row_max": gs["row_max"],
                    "known_race_nos": json.dumps(dict(known), sort_keys=True),
                    "embedded_race_hints": json.dumps(dict(hints), sort_keys=True),
                    "race_ids": json.dumps(dict(race_ids), sort_keys=True),
                    "meeting_ids": json.dumps(dict(gs["meeting_ids"]), sort_keys=True),
                    "distances": json.dumps(dict(gs["distances"]), sort_keys=True),
                    "recovery_method": recover_method, "recovery_value": recover_value,
                })

            counts["date_track_groups"] = len(group_stats)
            counts["deterministic_groups"] = deterministic_groups
            counts["ambiguous_groups"] = ambiguous_groups
            total.update(counts)
            file_rows.append({
                "source_file": str(path.relative_to(ROOT)), "status": "AUDITED",
                "rows": counts["rows"], "rows_with_race_no": counts["rows_with_race_no"],
                "rows_missing_race_no": counts["rows_missing_race_no"], "rows_with_race_id": counts["rows_with_race_id"],
                "rows_with_meeting_id": counts["rows_with_meeting_id"], "rows_with_date": counts["rows_with_date"],
                "rows_with_track": counts["rows_with_track"], "rows_with_embedded_race_hint": counts["rows_with_embedded_race_hint"],
                "missing_race_no_with_embedded_hint": counts["missing_race_no_with_embedded_hint"],
                "date_track_groups": counts["date_track_groups"], "deterministic_groups": deterministic_groups,
                "ambiguous_groups": ambiguous_groups,
                "race_no_col": c.get("race_no", ""), "race_id_col": c.get("race_id", ""),
                "meeting_id_col": c.get("meeting_id", ""), "date_col": c.get("race_date", ""),
                "track_col": c.get("track", ""), "distance_col": c.get("distance", ""),
                "headers": "|".join(fields[:150]),
            })

    with OUT_SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["metric", "value"])
        for k, v in total.items():
            w.writerow([k, v])

    ffields = ["source_file","status","rows","rows_with_race_no","rows_missing_race_no","rows_with_race_id",
               "rows_with_meeting_id","rows_with_date","rows_with_track","rows_with_embedded_race_hint",
               "missing_race_no_with_embedded_hint","date_track_groups","deterministic_groups","ambiguous_groups",
               "race_no_col","race_id_col","meeting_id_col","date_col","track_col","distance_col","headers"]
    with OUT_FILES.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=ffields, extrasaction="ignore"); w.writeheader(); w.writerows(file_rows)

    gfields = ["source_file","race_date","track","rows","row_min","row_max","known_race_nos","embedded_race_hints",
               "race_ids","meeting_ids","distances","recovery_method","recovery_value"]
    with OUT_GROUPS.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=gfields); w.writeheader(); w.writerows(group_rows)

    sfields = ["source_file","row_no","race_date","track","race_no","race_id","meeting_id","distance","horse",
               "embedded_race_hint","hint_field","headers"]
    with OUT_SAMPLES.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=sfields); w.writeheader(); w.writerows(samples)

    print("="*90)
    print("EDGEIQ SECTIONAL RACE-NUMBER RECOVERY AUDIT V4")
    print("="*90)
    for k, v in total.items(): print(f"{k}: {v}")
    print("SUMMARY:", OUT_SUMMARY)
    print("FILES:", OUT_FILES)
    print("GROUPS:", OUT_GROUPS)
    print("SAMPLES:", OUT_SAMPLES)

if __name__ == "__main__":
    main()
