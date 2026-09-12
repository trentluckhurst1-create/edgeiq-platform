from __future__ import annotations

import csv
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
DB = DATA / "edgeiq_sectional_warehouse_v2.sqlite"
WAREHOUSE = DATA / "edgeiq_sectional_warehouse_v2.csv"
QUARANTINE = DATA / "edgeiq_sectional_quarantine_v2.csv"
SUMMARY = DATA / "edgeiq_sectional_warehouse_v2_summary.csv"
PATTERNS = ("sectional", "racingcom", "racing_com", "split", "tempo")
SKIP_PARTS = {"node_modules", "dist", ".git", "__pycache__"}
SKIP_FILES = {WAREHOUSE.name.lower(), QUARANTINE.name.lower(), SUMMARY.name.lower(), DB.name.lower(),
              "edgeiq_sectional_pipeline_v2_audit.csv", "edgeiq_sectional_pipeline_v2_summary.csv",
              "edgeiq_sectional_split_failure_reasons_v2.csv", "edgeiq_sectional_pipeline_audit.csv",
              "edgeiq_sectional_pipeline_summary.csv"}
MISSING = {"", "-", "nan", "none", "null", "undefined", "n/a"}
ALIASES = {
    "race_date": ("race_date", "date", "meeting_date", "run_date"),
    "track": ("track", "venue", "meeting", "track_name"),
    "race_no": ("race_no", "race_number", "race"),
    "horse": ("horse_name", "horse", "runner_name", "runner", "name"),
    "horse_id": ("canonical_horse_id", "horse_id", "horse_key", "runner_id", "runner_key"),
    "distance": ("distance", "race_distance", "dist"),
    "meeting_id": ("meeting_id", "racingcom_meeting_id", "meetingid"),
    "race_id": ("race_id", "canonical_race_id", "racingcom_race_id", "raceid"),
    "last200": ("last200", "last_200", "l200", "last 200"),
    "last400": ("last400", "last_400", "l400", "last 400"),
    "last600": ("last600", "last_600", "l600", "last 600"),
    "source_confidence": ("source_confidence", "registry_confidence", "confidence"),
}
RANGES = {200: (8.0, 22.0), 400: (16.0, 45.0), 600: (24.0, 70.0)}


def clean(v: object) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in MISSING else s


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def find_col(fields: list[str], aliases: tuple[str, ...]) -> str:
    lookup = {norm_name(f): f for f in fields}
    for a in aliases:
        if norm_name(a) in lookup:
            return lookup[norm_name(a)]
    return ""


def cols(fields: list[str]) -> dict[str, str]:
    return {k: find_col(fields, v) for k, v in ALIASES.items()}


def get(row: dict[str, str], c: dict[str, str], key: str) -> str:
    col = c.get(key, "")
    return clean(row.get(col)) if col else ""


def norm_track(v: str) -> str:
    return " ".join(clean(v).upper().replace("_", " ").replace("|", " ").split())


def norm_horse(v: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", clean(v).upper())


def norm_race_no(v: str) -> str:
    digits = re.sub(r"[^0-9]", "", clean(v).upper().replace("RACE", "").replace("R", ""))
    return str(int(digits)) if digits else ""


def parse_time(v: str, metres: int) -> float | None:
    raw = clean(v)
    if not raw:
        return None
    try:
        if ":" in raw:
            a, b = raw.split(":", 1)
            x = float(a) * 60 + float(b)
        else:
            x = float(re.sub(r"[^0-9.\-]", "", raw))
    except Exception:
        return None
    lo, hi = RANGES[metres]
    return round(x, 4) if lo <= x <= hi else None


def source_rank(path: Path, confidence: str) -> int:
    text = str(path).lower()
    score = 0
    if "racingcom" in text or "racing_com" in text:
        score += 30
    if "canonical" in text or "registry" in text or "warehouse" in text:
        score += 20
    conf = clean(confidence).upper()
    if conf == "HIGH": score += 30
    elif conf == "MEDIUM": score += 15
    return score


def candidate_csvs() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.csv"):
        if p.name.lower() in SKIP_FILES:
            continue
        if any(part.lower() in SKIP_PARTS for part in p.parts):
            continue
        if any(k in p.name.lower() for k in PATTERNS):
            out.append(p)
    return sorted(out, key=lambda p: str(p).lower())


def setup(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    DROP TABLE IF EXISTS best;
    DROP TABLE IF EXISTS quarantine;
    CREATE TABLE best (
      canonical_key TEXT PRIMARY KEY,
      race_date TEXT, track TEXT, race_no TEXT, meeting_id TEXT, race_id TEXT,
      horse_id TEXT, horse_name TEXT, horse_key TEXT, distance TEXT,
      last200 REAL, last400 REAL, last600 REAL,
      split_count INTEGER, source_rank INTEGER, source_confidence TEXT,
      source_file TEXT, validation_status TEXT, ingested_at TEXT
    );
    CREATE TABLE quarantine (
      source_file TEXT, row_no INTEGER, reason TEXT, race_date TEXT, track TEXT,
      race_no TEXT, horse_name TEXT, horse_id TEXT, last200_raw TEXT,
      last400_raw TEXT, last600_raw TEXT
    );
    """)
    conn.commit()


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if DB.exists(): DB.unlink()
    conn = sqlite3.connect(DB)
    setup(conn)
    seen = accepted = quarantined = dedup_updates = 0
    now = datetime.now(timezone.utc).isoformat()

    for fi, path in enumerate(candidate_csvs(), 1):
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as h:
                reader = csv.DictReader(h)
                fields = list(reader.fieldnames or [])
                c = cols(fields)
                if not any(c.get(k) for k in ("last200","last400","last600")):
                    continue
                for row_no, row in enumerate(reader, 2):
                    seen += 1
                    race_date = get(row,c,"race_date")[:10]
                    track = norm_track(get(row,c,"track"))
                    race_no = norm_race_no(get(row,c,"race_no"))
                    horse = get(row,c,"horse")
                    horse_id = get(row,c,"horse_id")
                    hk = norm_horse(horse or horse_id)
                    raw200, raw400, raw600 = get(row,c,"last200"), get(row,c,"last400"), get(row,c,"last600")
                    s200 = parse_time(raw200,200) if raw200 else None
                    s400 = parse_time(raw400,400) if raw400 else None
                    s600 = parse_time(raw600,600) if raw600 else None
                    split_count = sum(x is not None for x in (s200,s400,s600))
                    reason = ""
                    if not race_date or not track or not race_no:
                        reason = "MISSING_RACE_IDENTITY"
                    elif not hk:
                        reason = "MISSING_HORSE_IDENTITY"
                    elif split_count == 0:
                        reason = "NO_VALID_NAMED_SPLITS"
                    if reason:
                        quarantined += 1
                        conn.execute("INSERT INTO quarantine VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                     (str(path.relative_to(ROOT)),row_no,reason,race_date,track,race_no,horse,horse_id,raw200,raw400,raw600))
                        continue

                    canonical_key = f"{race_date}|{track}|{race_no}|{hk}"
                    confidence = get(row,c,"source_confidence")
                    rank = source_rank(path, confidence)
                    prior = conn.execute("SELECT split_count, source_rank FROM best WHERE canonical_key=?", (canonical_key,)).fetchone()
                    quality = (split_count, rank)
                    if prior and quality <= (prior[0], prior[1]):
                        continue
                    if prior:
                        dedup_updates += 1
                    accepted += 1
                    conn.execute("""
                    INSERT INTO best VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(canonical_key) DO UPDATE SET
                      race_date=excluded.race_date, track=excluded.track, race_no=excluded.race_no,
                      meeting_id=excluded.meeting_id, race_id=excluded.race_id, horse_id=excluded.horse_id,
                      horse_name=excluded.horse_name, horse_key=excluded.horse_key, distance=excluded.distance,
                      last200=excluded.last200, last400=excluded.last400, last600=excluded.last600,
                      split_count=excluded.split_count, source_rank=excluded.source_rank,
                      source_confidence=excluded.source_confidence, source_file=excluded.source_file,
                      validation_status=excluded.validation_status, ingested_at=excluded.ingested_at
                    """, (canonical_key,race_date,track,race_no,get(row,c,"meeting_id"),get(row,c,"race_id"),horse_id,horse,hk,
                          get(row,c,"distance"),s200,s400,s600,split_count,rank,confidence,
                          str(path.relative_to(ROOT)),"CANONICAL_VALIDATED_NAMED_SPLITS",now))
                    if seen % 100000 == 0:
                        conn.commit(); print(f"ROWS {seen:,} | accepted candidates {accepted:,} | quarantine {quarantined:,}")
        except Exception as exc:
            print(f"WARN {path}: {exc}")
        conn.commit()
        if fi % 50 == 0:
            print(f"FILES {fi}")

    def export(query: str, path: Path) -> int:
        cur = conn.execute(query)
        names = [d[0] for d in cur.description]
        n = 0
        with path.open("w", newline="", encoding="utf-8") as h:
            w = csv.writer(h); w.writerow(names)
            for r in cur:
                w.writerow(r); n += 1
        return n

    warehouse_rows = export("SELECT * FROM best ORDER BY race_date, track, CAST(race_no AS INTEGER), horse_name", WAREHOUSE)
    quarantine_rows = export("SELECT * FROM quarantine", QUARANTINE)
    unique_races = conn.execute("SELECT COUNT(DISTINCT race_date || '|' || track || '|' || race_no) FROM best").fetchone()[0]
    unique_horses = conn.execute("SELECT COUNT(DISTINCT horse_key) FROM best").fetchone()[0]
    full_600 = conn.execute("SELECT COUNT(*) FROM best WHERE last600 IS NOT NULL").fetchone()[0]
    full_400 = conn.execute("SELECT COUNT(*) FROM best WHERE last400 IS NOT NULL").fetchone()[0]
    full_200 = conn.execute("SELECT COUNT(*) FROM best WHERE last200 IS NOT NULL").fetchone()[0]
    reason_rows = conn.execute("SELECT reason, COUNT(*) FROM quarantine GROUP BY reason ORDER BY COUNT(*) DESC").fetchall()

    summary_rows = [
        ("run_timestamp_utc", now), ("source_rows_scanned", seen), ("canonical_rows", warehouse_rows),
        ("quarantine_rows", quarantine_rows), ("unique_races", unique_races), ("unique_horses", unique_horses),
        ("rows_with_last200", full_200), ("rows_with_last400", full_400), ("rows_with_last600", full_600),
        ("dedup_replacements", dedup_updates),
        ("production_status", "USABLE_CANONICAL_FOUNDATION" if warehouse_rows > 0 else "NOT_READY")
    ] + [(f"quarantine_{r.lower()}", n) for r,n in reason_rows]
    with SUMMARY.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h); w.writerow(["metric","value"]); w.writerows(summary_rows)

    print("="*90)
    print("EDGEIQ SECTIONAL WAREHOUSE V2")
    print("="*90)
    for k,v in summary_rows: print(f"{k}: {v}")
    print("WAREHOUSE:", WAREHOUSE)
    print("QUARANTINE:", QUARANTINE)
    print("SUMMARY:", SUMMARY)
    conn.close()

if __name__ == "__main__":
    main()
