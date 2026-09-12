from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
QUARANTINE = DATA / "edgeiq_sectional_quarantine_v2.csv"
SUMMARY = DATA / "edgeiq_sectional_identity_recovery_v3_summary.csv"
FILES_OUT = DATA / "edgeiq_sectional_identity_recovery_v3_files.csv"
SAMPLES = DATA / "edgeiq_sectional_identity_recovery_v3_samples.csv"

MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a"}
DATE_ALIASES = ("race_date", "date", "meeting_date", "run_date")
TRACK_ALIASES = ("track", "venue", "meeting", "track_name")
RACE_NO_ALIASES = ("race_no", "race_number", "race")
RACE_ID_ALIASES = ("canonical_race_id", "race_id", "racingcom_race_id", "raceid")
MEETING_ID_ALIASES = ("meeting_id", "racingcom_meeting_id", "meetingid")
HORSE_ALIASES = ("horse_name", "horse", "runner_name", "runner", "name")


def clean(v: object) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def find_col(fields: list[str], aliases: tuple[str, ...]) -> str:
    lookup = {norm(f): f for f in fields}
    for a in aliases:
        if norm(a) in lookup:
            return lookup[norm(a)]
    return ""


def first(row: dict[str, str], col: str) -> str:
    return clean(row.get(col)) if col else ""


def classify_missing(date: str, track: str, race_no: str) -> str:
    missing = []
    if not date: missing.append("DATE")
    if not track: missing.append("TRACK")
    if not race_no: missing.append("RACE_NO")
    return "+".join(missing) if missing else "NONE"


def path_date_hint(path: str) -> str:
    m = re.search(r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)", path)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def path_race_hint(path: str) -> str:
    m = re.search(r"(?:^|[^a-z0-9])r(?:ace)?[_ -]?(\d{1,2})(?:[^0-9]|$)", path.lower())
    return m.group(1) if m else ""


def main() -> None:
    if not QUARANTINE.exists():
        raise SystemExit(f"Missing prerequisite: {QUARANTINE}")

    wanted: dict[str, set[int]] = defaultdict(set)
    with QUARANTINE.open("r", newline="", encoding="utf-8-sig") as h:
        for r in csv.DictReader(h):
            if clean(r.get("reason")) == "MISSING_RACE_IDENTITY":
                try:
                    wanted[clean(r.get("source_file"))].add(int(clean(r.get("row_no"))))
                except Exception:
                    pass

    aggregate = Counter()
    file_rows = []
    samples = []

    for ix, (rel, row_numbers) in enumerate(sorted(wanted.items()), 1):
        p = ROOT / rel
        local = Counter()
        if not p.exists():
            local["SOURCE_FILE_MISSING"] += len(row_numbers)
            aggregate.update(local)
            file_rows.append({"source_file": rel, "target_rows": len(row_numbers), "status": "SOURCE_FILE_MISSING"})
            continue
        try:
            with p.open("r", newline="", encoding="utf-8-sig") as h:
                reader = csv.DictReader(h)
                fields = list(reader.fieldnames or [])
                dcol = find_col(fields, DATE_ALIASES)
                tcol = find_col(fields, TRACK_ALIASES)
                ncol = find_col(fields, RACE_NO_ALIASES)
                ridcol = find_col(fields, RACE_ID_ALIASES)
                midcol = find_col(fields, MEETING_ID_ALIASES)
                hcol = find_col(fields, HORSE_ALIASES)
                max_target = max(row_numbers) if row_numbers else 0
                for row_no, row in enumerate(reader, 2):
                    if row_no > max_target: break
                    if row_no not in row_numbers: continue
                    date = first(row, dcol)[:10]
                    track = first(row, tcol)
                    race_no = first(row, ncol)
                    rid = first(row, ridcol)
                    mid = first(row, midcol)
                    miss = classify_missing(date, track, race_no)
                    local[f"MISSING_{miss}"] += 1
                    aggregate[f"MISSING_{miss}"] += 1
                    if rid:
                        local["HAS_RACE_ID_FALLBACK"] += 1
                        aggregate["HAS_RACE_ID_FALLBACK"] += 1
                    if mid:
                        local["HAS_MEETING_ID_FALLBACK"] += 1
                        aggregate["HAS_MEETING_ID_FALLBACK"] += 1
                    pd = path_date_hint(rel)
                    pr = path_race_hint(rel)
                    if pd:
                        local["HAS_PATH_DATE_HINT"] += 1
                        aggregate["HAS_PATH_DATE_HINT"] += 1
                    if pr:
                        local["HAS_PATH_RACE_HINT"] += 1
                        aggregate["HAS_PATH_RACE_HINT"] += 1
                    if rid and (pd or date) and (race_no or pr):
                        local["HIGH_VALUE_RECOVERY_CANDIDATE"] += 1
                        aggregate["HIGH_VALUE_RECOVERY_CANDIDATE"] += 1
                    if len(samples) < 250:
                        samples.append({
                            "source_file": rel, "row_no": row_no, "missing_components": miss,
                            "race_date": date, "track": track, "race_no": race_no,
                            "race_id": rid, "meeting_id": mid, "path_date_hint": pd,
                            "path_race_hint": pr, "horse": first(row, hcol),
                            "headers": "|".join(fields[:80]),
                        })
                file_rows.append({
                    "source_file": rel,
                    "target_rows": len(row_numbers),
                    "date_col": dcol, "track_col": tcol, "race_no_col": ncol,
                    "race_id_col": ridcol, "meeting_id_col": midcol,
                    "missing_date": sum(v for k,v in local.items() if "DATE" in k and k.startswith("MISSING_")),
                    "missing_track": sum(v for k,v in local.items() if "TRACK" in k and k.startswith("MISSING_")),
                    "missing_race_no": sum(v for k,v in local.items() if "RACE_NO" in k and k.startswith("MISSING_")),
                    "has_race_id_fallback": local["HAS_RACE_ID_FALLBACK"],
                    "has_meeting_id_fallback": local["HAS_MEETING_ID_FALLBACK"],
                    "path_date_hints": local["HAS_PATH_DATE_HINT"],
                    "path_race_hints": local["HAS_PATH_RACE_HINT"],
                    "high_value_candidates": local["HIGH_VALUE_RECOVERY_CANDIDATE"],
                    "status": "AUDITED",
                })
        except Exception as exc:
            file_rows.append({"source_file": rel, "target_rows": len(row_numbers), "status": f"READ_ERROR:{exc}"})
            aggregate["FILE_READ_ERROR"] += 1
        if ix % 25 == 0:
            print(f"AUDITED {ix} source files")

    with SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["metric","value"])
        w.writerow(["quarantine_missing_race_identity", sum(len(v) for v in wanted.values())])
        w.writerow(["source_files", len(wanted)])
        for k,v in aggregate.most_common(): w.writerow([k.lower(), v])

    fields = ["source_file","target_rows","date_col","track_col","race_no_col","race_id_col","meeting_id_col",
              "missing_date","missing_track","missing_race_no","has_race_id_fallback","has_meeting_id_fallback",
              "path_date_hints","path_race_hints","high_value_candidates","status"]
    with FILES_OUT.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(file_rows)

    sfields = ["source_file","row_no","missing_components","race_date","track","race_no","race_id","meeting_id",
               "path_date_hint","path_race_hint","horse","headers"]
    with SAMPLES.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=sfields); w.writeheader(); w.writerows(samples)

    print("="*90)
    print("EDGEIQ SECTIONAL IDENTITY RECOVERY AUDIT V3")
    print("="*90)
    print("quarantine_missing_race_identity:", sum(len(v) for v in wanted.values()))
    print("source_files:", len(wanted))
    for k,v in aggregate.most_common(20): print(f"{k}: {v}")
    print("SUMMARY:", SUMMARY)
    print("FILES:", FILES_OUT)
    print("SAMPLES:", SAMPLES)

if __name__ == "__main__":
    main()
