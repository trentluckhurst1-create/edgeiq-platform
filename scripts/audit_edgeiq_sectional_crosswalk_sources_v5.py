from __future__ import annotations

import csv
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
OUT = DATA / "edgeiq_sectional_crosswalk_sources_v5.csv"
SUMMARY = DATA / "edgeiq_sectional_crosswalk_sources_v5_summary.csv"

SKIP_DIRS = {"checkpoints", "node_modules", "dist", ".git", "__pycache__"}
SKIP_FILES = {
    "edgeiq_sectional_payload_reconstruction_v1.csv",
    "edgeiq_sectional_physics_validation_v1.csv",
    "sectionals.csv",
    "edgeiq_sectional_warehouse_v2.csv",
    "edgeiq_sectional_quarantine_v2.csv",
    "edgeiq_sectional_warehouse_v3.csv",
    "edgeiq_sectional_quarantine_v3.csv",
}
MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a"}

ALIASES = {
    "date": ("race_date", "date", "meeting_date", "run_date"),
    "track": ("track", "venue", "meeting", "track_name", "venue_name"),
    "horse": ("horse_name", "horse", "runner_name", "runner", "name"),
    "horse_id": ("canonical_horse_id", "horse_id", "horse_key", "runner_id", "canonical_runner_id", "runner_key"),
    "distance": ("distance", "race_distance", "dist", "race_distance_metres", "distance_metres"),
    "race_no": ("race_no", "race_number", "race", "race_num"),
    "race_id": ("canonical_race_id", "race_id", "racingcom_race_id", "raceid"),
    "meeting_id": ("meeting_id", "racingcom_meeting_id", "meetingid"),
}


def norm(v: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(v).lower())


def find_col(fields: list[str], aliases: tuple[str, ...]) -> str:
    lookup = {norm(f): f for f in fields}
    for a in aliases:
        if norm(a) in lookup:
            return lookup[norm(a)]
    return ""


def clean(v: object) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def iter_csvs():
    for p in DATA.rglob("*.csv"):
        try:
            rel = p.relative_to(ROOT)
        except Exception:
            continue
        if any(part.lower() in SKIP_DIRS for part in rel.parts):
            continue
        if p.name.lower() in SKIP_FILES:
            continue
        if p.name.lower().startswith("edgeiq_sectional_crosswalk_sources_v5"):
            continue
        yield p


def score(cols: dict[str, str]) -> int:
    s = 0
    if cols["date"]: s += 15
    if cols["track"]: s += 15
    if cols["horse"] or cols["horse_id"]: s += 25
    if cols["distance"]: s += 15
    if cols["race_no"]: s += 20
    if cols["race_id"]: s += 25
    if cols["meeting_id"]: s += 10
    return s


def main() -> None:
    rows = []
    total = Counter()

    for p in iter_csvs():
        total["csv_files_scanned"] += 1
        try:
            with p.open("r", newline="", encoding="utf-8-sig", errors="replace") as h:
                r = csv.reader(h)
                fields = next(r, [])
            if not fields:
                continue
            cols = {k: find_col(fields, aliases) for k, aliases in ALIASES.items()}
            sc = score(cols)
            if sc < 55:
                continue

            try:
                size = p.stat().st_size
            except Exception:
                size = 0

            has_identity_output = bool(cols["race_no"] or cols["race_id"])
            has_join_core = bool(cols["date"] and cols["track"] and (cols["horse"] or cols["horse_id"]))
            has_distance = bool(cols["distance"])
            candidate_class = ""
            if has_join_core and has_identity_output and has_distance:
                candidate_class = "TIER_A_DATE_TRACK_HORSE_DISTANCE_TO_RACE"
            elif has_join_core and has_identity_output:
                candidate_class = "TIER_B_DATE_TRACK_HORSE_TO_RACE"
            elif (cols["horse"] or cols["horse_id"]) and has_identity_output:
                candidate_class = "TIER_C_HORSE_TO_RACE_WITH_PARTIAL_CONTEXT"
            else:
                candidate_class = "TIER_D_SCHEMA_LEAD"

            rows.append({
                "source_file": str(p.relative_to(ROOT)),
                "size_bytes": size,
                "score": sc,
                "candidate_class": candidate_class,
                "date_col": cols["date"],
                "track_col": cols["track"],
                "horse_col": cols["horse"],
                "horse_id_col": cols["horse_id"],
                "distance_col": cols["distance"],
                "race_no_col": cols["race_no"],
                "race_id_col": cols["race_id"],
                "meeting_id_col": cols["meeting_id"],
                "header_count": len(fields),
                "headers": "|".join(fields[:200]),
            })
            total["candidate_files"] += 1
            total[candidate_class] += 1
        except Exception:
            total["read_errors"] += 1

    rows.sort(key=lambda x: (-int(x["score"]), -int(x["size_bytes"]), x["source_file"].lower()))

    fields = [
        "source_file","size_bytes","score","candidate_class","date_col","track_col","horse_col","horse_id_col",
        "distance_col","race_no_col","race_id_col","meeting_id_col","header_count","headers"
    ]
    with OUT.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    with SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["metric","value"])
        for k, v in total.items(): w.writerow([k, v])
        w.writerow(["top_candidate", rows[0]["source_file"] if rows else ""])
        w.writerow(["top_candidate_class", rows[0]["candidate_class"] if rows else ""])
        w.writerow(["top_candidate_score", rows[0]["score"] if rows else 0])

    print("="*90)
    print("EDGEIQ SECTIONAL CROSSWALK SOURCE DISCOVERY V5")
    print("="*90)
    for k, v in total.items(): print(f"{k}: {v}")
    if rows:
        print("TOP CANDIDATES:")
        for r in rows[:20]:
            print(f"{r['score']:>3} | {r['candidate_class']} | {r['source_file']}")
    print("OUT:", OUT)
    print("SUMMARY:", SUMMARY)

if __name__ == "__main__":
    main()
