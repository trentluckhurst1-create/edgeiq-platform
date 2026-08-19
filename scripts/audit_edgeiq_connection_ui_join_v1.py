import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RUNNER_FILE = DATA / "edgeiq_live_runner_board_v1.csv"
CONNECTION_FILE = DATA / "edgeiq_connection_intelligence_v2_1.csv"
OUT_FILE = DATA / "edgeiq_connection_ui_join_v1.csv"
SUMMARY_FILE = DATA / "edgeiq_connection_ui_join_v1_summary.csv"


FIELDS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "runner_name",
    "runner_horse_key",
    "join_key",
    "connection_race_date",
    "connection_track",
    "connection_race_no",
    "connection_horse",
    "connection_join_key",
    "matched",
    "material_evidence",
    "connection_band",
    "connection_evidence_status",
    "miss_reason",
]


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def text(value):
    return str(value or "").strip()


def clean_track(value):
    return "".join(ch for ch in text(value).upper() if ch.isalnum())


def clean_horse(value):
    return "".join(ch for ch in text(value).upper().split("(")[0] if ch.isalnum())


def clean_horse_loose(value):
    horse = clean_horse(value)
    for suffix in ("NZ", "GB", "IRE", "FR", "USA", "JPN", "AUS"):
        if horse.endswith(suffix):
            return horse[: -len(suffix)]
    return horse


def race_date(row):
    return text(row.get("race_date") or row.get("current_race_date") or row.get("meeting_date") or row.get("date") or row.get("raceDate"))


def race_no(row):
    return text(row.get("race_no") or row.get("raceNo") or row.get("race_number") or row.get("race"))


def horse_name(row):
    return text(row.get("horse") or row.get("horseName") or row.get("runner") or row.get("runner_name"))


def horse_key(row):
    return clean_horse(row.get("horse_key") or row.get("horseKey") or horse_name(row))


def join_key(row):
    return "|".join([
        race_date(row),
        clean_track(row.get("track") or row.get("meeting") or row.get("meeting_name")),
        race_no(row),
        horse_key(row),
    ])


def is_active(row):
    status = text(row.get("runner_status") or row.get("scratch_status")).upper()
    scratched = text(row.get("is_scratched")).upper()
    return status not in {"SCR", "SCRATCHED"} and scratched not in {"TRUE", "YES", "1"}


def material(row):
    band = text(row.get("connection_band")).upper()
    if not row or band == "NO_EVIDENCE":
        return False
    return any(text(row.get(key)) for key in ["connection_band", "connection_score", "connection_angle_1", "connection_narrative", "evidence_quality"])


def match_connection(rows, base):
    base_date = race_date(base)
    base_track = clean_track(base.get("track"))
    base_race = race_no(base)
    base_horse_key = clean_horse(base.get("horse_key") or base.get("horseKey"))
    base_strict = base_horse_key or clean_horse(horse_name(base))
    base_loose = clean_horse_loose(horse_name(base))

    for row in rows:
        row_date = race_date(row)
        row_track = clean_track(row.get("track"))
        row_race = race_no(row)
        row_horse_key = clean_horse(row.get("horse_key") or row.get("horseKey"))
        row_strict = row_horse_key or clean_horse(horse_name(row))
        row_loose = clean_horse_loose(horse_name(row))
        if base_date and row_date and base_date != row_date:
            continue
        if base_track != row_track:
            continue
        if base_race != row_race:
            continue
        if base_strict and row_strict and base_strict == row_strict:
            return row
        if (not base_horse_key or not row_horse_key) and base_loose and row_loose and base_loose == row_loose:
            return row
    return None


def miss_reason(base, connections):
    base_date = race_date(base)
    base_track = clean_track(base.get("track"))
    base_race = race_no(base)
    base_horse = horse_key(base)
    if not any(race_date(row) == base_date for row in connections):
        return "DATE_NOT_FOUND"
    by_date = [row for row in connections if race_date(row) == base_date]
    if not any(clean_track(row.get("track")) == base_track for row in by_date):
        return "TRACK_NOT_FOUND_FOR_DATE"
    by_track = [row for row in by_date if clean_track(row.get("track")) == base_track]
    if not any(race_no(row) == base_race for row in by_track):
        return "RACE_NO_NOT_FOUND_FOR_DATE_TRACK"
    by_race = [row for row in by_track if race_no(row) == base_race]
    if not any(horse_key(row) == base_horse or clean_horse_loose(horse_name(row)) == clean_horse_loose(horse_name(base)) for row in by_race):
        return "HORSE_NOT_FOUND_FOR_RACE"
    return "UNKNOWN_JOIN_MISS"


def main():
    runners = [row for row in read_csv(RUNNER_FILE) if is_active(row)]
    connections = read_csv(CONNECTION_FILE)
    audit_rows = []
    for runner in runners:
        match = match_connection(connections, runner)
        matched = match is not None
        material_evidence = material(match) if match else False
        audit_rows.append({
            "race_date": race_date(runner),
            "track": text(runner.get("track")),
            "race_no": race_no(runner),
            "horse": horse_name(runner),
            "runner_name": text(runner.get("runner_name") or runner.get("runner") or runner.get("horse")),
            "runner_horse_key": text(runner.get("horse_key")),
            "join_key": join_key(runner),
            "connection_race_date": race_date(match) if match else "",
            "connection_track": text(match.get("track")) if match else "",
            "connection_race_no": race_no(match) if match else "",
            "connection_horse": horse_name(match) if match else "",
            "connection_join_key": join_key(match) if match else "",
            "matched": "YES" if matched else "NO",
            "material_evidence": "YES" if material_evidence else "NO",
            "connection_band": text(match.get("connection_band")) if match else "",
            "connection_evidence_status": text(match.get("connection_evidence_status")) if match else "",
            "miss_reason": "" if matched else miss_reason(runner, connections),
        })

    counts = Counter(row["miss_reason"] or "MATCHED" for row in audit_rows)
    matched = sum(1 for row in audit_rows if row["matched"] == "YES")
    material_count = sum(1 for row in audit_rows if row["material_evidence"] == "YES")
    summary_rows = [
        {"metric": "active_runner_rows", "value": str(len(runners))},
        {"metric": "connection_rows", "value": str(len(connections))},
        {"metric": "matched_rows", "value": str(matched)},
        {"metric": "unmatched_rows", "value": str(len(runners) - matched)},
        {"metric": "material_evidence_rows", "value": str(material_count)},
        {"metric": "miss_reason_counts", "value": "; ".join(f"{key}={value}" for key, value in sorted(counts.items()))},
    ]
    write_csv(OUT_FILE, audit_rows, FIELDS)
    write_csv(SUMMARY_FILE, summary_rows, ["metric", "value"])
    print(f"matched={matched} unmatched={len(runners) - matched} material={material_count}")


if __name__ == "__main__":
    main()
