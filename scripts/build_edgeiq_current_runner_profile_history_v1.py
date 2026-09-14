from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CATALOG = DATA / "edgeiq_three_day_product_catalog_v1.json"
OUT = DATA / "edgeiq_current_runner_profile_history_v1.csv"
AUDIT = DATA / "edgeiq_current_runner_profile_history_v1_audit.json"
BASE_URL = "https://www.racing.com"

FIELDS = [
    "current_race_date", "current_track", "current_race_no", "current_horse", "current_runner_key",
    "horse_url", "historical_race_date", "historical_track", "historical_race_no", "historical_horse",
    "distance", "race_class", "going", "finish", "margin", "field_size", "jockey", "trainer", "weight",
    "sp", "performance_rating", "history_source", "rating_source", "identity_certification",
    "strict_prior_certified", "profile_fetch_status",
]


def text(value: Any) -> str:
    value = "" if value is None else str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value.lower() in {"", "none", "null", "nan", "-", "n/a", "na"} else value


def canon(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def race_no(value: Any) -> str:
    m = re.search(r"\bR(?:ACE)?\s*(\d{1,2})\b", text(value), flags=re.I)
    if not m:
        m = re.search(r"(?:^|\D)(\d{1,2})(?:\D|$)", text(value))
    return str(int(m.group(1))) if m else ""


def date_text(value: Any) -> str:
    raw = text(value)
    if not raw:
        return ""
    patterns = [
        (r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", "%Y-%m-%d"),
        (r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", "%d-%m-%Y"),
        (r"(\d{1,2})\s+([A-Za-z]{3})\s+(20\d{2})", "%d %b %Y"),
        (r"(\d{1,2})[- ]([A-Za-z]{3})[- ](\d{2})", "%d %b %y"),
    ]
    for pattern, fmt in patterns:
        m = re.search(pattern, raw)
        if not m:
            continue
        candidate = " ".join(m.groups()) if "%b" in fmt else "-".join(m.groups())
        try:
            return datetime.strptime(candidate, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def parse_number(value: Any) -> str:
    m = re.search(r"-?\d+(?:\.\d+)?", text(value).replace(",", ""))
    return m.group(0) if m else ""


def current_runners() -> list[dict[str, str]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, str]] = []
    for meeting in payload.get("meetings", []):
        if not isinstance(meeting, dict):
            continue
        meeting_date = text(meeting.get("date"))[:10]
        track = text(meeting.get("meeting"))
        for race in meeting.get("races", []):
            if not isinstance(race, dict):
                continue
            rno = race_no(race.get("raceNumber"))
            for runner in race.get("runners", []):
                if not isinstance(runner, dict):
                    continue
                official = runner.get("official") if isinstance(runner.get("official"), dict) else {}
                source = runner.get("source") if isinstance(runner.get("source"), dict) else {}
                horse = text(official.get("runner")) or text(source.get("horseName"))
                horse_url = text(source.get("horseUrl"))
                if not horse or not horse_url:
                    continue
                key = text(source.get("runner_key")) or f"{meeting_date}|{track}|R{rno}|{canon(horse)}"
                rows.append({
                    "current_race_date": meeting_date,
                    "current_track": track,
                    "current_race_no": rno,
                    "current_horse": horse,
                    "current_runner_key": key,
                    "horse_url": horse_url,
                })
    return rows


def norm_header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def lines(value: Any) -> list[str]:
    return [re.sub(r"\s+", " ", item).strip() for item in str(value or "").splitlines() if re.sub(r"\s+", " ", item).strip()]


def cell_by_header(headers: list[str], cells: list[str], *needles: str) -> str:
    norms = [norm_header(h) for h in headers]
    for needle in needles:
        n = norm_header(needle)
        for idx, header in enumerate(norms):
            if n and n in header and idx < len(cells):
                return text(cells[idx])
    return ""


def parse_track_date(value: str) -> tuple[str, str, str]:
    hist_date = date_text(value)
    vals = lines(value)
    track = ""
    rno = race_no(value)
    for item in vals:
        if date_text(item):
            continue
        cleaned = re.sub(r"\bR(?:ACE)?\s*\d{1,2}\b", "", item, flags=re.I).strip(" -|")
        if cleaned and not re.fullmatch(r"\d+", cleaned):
            track = cleaned
            break
    return track, hist_date, rno


def parse_distance_condition(value: str) -> tuple[str, str]:
    raw = text(value)
    m = re.search(r"\b(\d{3,4})\s*m\b", raw, flags=re.I)
    distance = m.group(1) if m else ""
    going = ""
    gm = re.search(r"\b(FIRM|GOOD|SOFT|HEAVY|SYNTHETIC|AW|DEAD)\s*([0-9])?\b", raw, flags=re.I)
    if gm:
        going = gm.group(1).upper() + ((" " + gm.group(2)) if gm.group(2) else "")
    return distance, going


def parse_runner_cell(value: str, fallback_horse: str) -> tuple[str, str, str]:
    vals = lines(value)
    trainer = ""
    jockey = ""
    for item in vals:
        upper = item.upper()
        if upper.startswith("T:"):
            trainer = text(item[2:])
        elif upper.startswith("J:"):
            jockey = text(item[2:])
    return fallback_horse, trainer, jockey


def extract_form_rows(page, current: dict[str, str]) -> list[dict[str, str]]:
    tables = page.eval_on_selector_all(
        "table",
        """tables => tables.map(t => ({
          headers: Array.from(t.querySelectorAll('thead th')).map(x => (x.innerText || '').trim()),
          rows: Array.from(t.querySelectorAll('tbody tr')).map(tr => Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').trim()))
        }))""",
    )
    output: list[dict[str, str]] = []
    current_date = current["current_race_date"]
    for table in tables:
        headers = [text(h) for h in table.get("headers", [])]
        header_blob = "|".join(norm_header(h) for h in headers)
        if "TRACKDATE" not in header_blob or "DISTCOND" not in header_blob or "RATING" not in header_blob:
            continue
        for cells_raw in table.get("rows", []):
            cells = [text(c) for c in cells_raw]
            if not any(cells):
                continue
            hist_track, hist_date, hist_race_no = parse_track_date(cell_by_header(headers, cells, "TRACK/DATE", "TRACK DATE"))
            if not hist_date or hist_date >= current_date:
                continue
            distance, going = parse_distance_condition(cell_by_header(headers, cells, "DIST/COND", "DIST COND"))
            hist_horse, trainer, jockey = parse_runner_cell(cell_by_header(headers, cells, "HORSE/TRAINER/JOCKEY", "HORSE TRAINER JOCKEY"), current["current_horse"])
            prize_class = cell_by_header(headers, cells, "PRIZE/CLASS", "PRIZE CLASS")
            class_lines = lines(prize_class)
            race_class = class_lines[-1] if class_lines else ""
            finish = cell_by_header(headers, cells, "POS", "POSITION")
            rating = parse_number(cell_by_header(headers, cells, "RATING"))
            output.append({
                "current_race_date": current["current_race_date"],
                "current_track": current["current_track"],
                "current_race_no": current["current_race_no"],
                "current_horse": current["current_horse"],
                "current_runner_key": current["current_runner_key"],
                "horse_url": current["horse_url"],
                "historical_race_date": hist_date,
                "historical_track": hist_track,
                "historical_race_no": hist_race_no,
                "historical_horse": hist_horse,
                "distance": distance,
                "race_class": race_class,
                "going": going,
                "finish": parse_number(finish) or finish,
                "margin": cell_by_header(headers, cells, "MARGIN"),
                "field_size": "",
                "jockey": jockey,
                "trainer": trainer,
                "weight": cell_by_header(headers, cells, "WGT", "WEIGHT"),
                "sp": cell_by_header(headers, cells, "ODDS", "SP"),
                "performance_rating": rating,
                "history_source": "RACING_COM_HORSE_PROFILE_FORM",
                "rating_source": "RACING_COM_HORSE_PROFILE_FORM" if rating else "",
                "identity_certification": "CURRENT_HORSE_PROFILE_URL_EXACT_STRICT_PRIOR",
                "strict_prior_certified": "TRUE",
                "profile_fetch_status": "PASS",
            })
    return output


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    runners = current_runners()
    unique: dict[str, dict[str, str]] = {}
    for runner in runners:
        unique.setdefault(runner["horse_url"], runner)

    rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0", viewport={"width": 1440, "height": 1200})
        page = context.new_page()
        for index, (horse_url, current) in enumerate(unique.items(), start=1):
            url = horse_url if horse_url.startswith("http") else BASE_URL + horse_url
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(1200)
                parsed = extract_form_rows(page, current)
                if not parsed:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(900)
                    parsed = extract_form_rows(page, current)
                rows.extend(parsed)
                if not parsed:
                    failures.append({"horse": current["current_horse"], "horse_url": horse_url, "reason": "NO_FORM_TABLE_ROWS"})
            except Exception as exc:
                failures.append({"horse": current["current_horse"], "horse_url": horse_url, "reason": f"FETCH_ERROR:{type(exc).__name__}"})
            if index % 20 == 0:
                print(f"PROFILE_HISTORY_PROGRESS={index}/{len(unique)} ROWS={len(rows)}")
        page.close()
        context.close()
        browser.close()

    by_url: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_url[row["horse_url"]].append(row)
    expanded: list[dict[str, str]] = []
    for current in runners:
        for source_row in by_url.get(current["horse_url"], []):
            if source_row["historical_race_date"] >= current["current_race_date"]:
                continue
            row = dict(source_row)
            for field in ("current_race_date", "current_track", "current_race_no", "current_horse", "current_runner_key"):
                row[field] = current[field]
            expanded.append(row)

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for row in sorted(expanded, key=lambda r: (r["current_race_date"], r["current_track"], int(r["current_race_no"] or 0), canon(r["current_horse"]), r["historical_race_date"])):
        key = (row["current_runner_key"], row["historical_race_date"], canon(row["historical_track"]), row["historical_race_no"], row["finish"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    write_csv(OUT, deduped)
    by_runner: dict[str, int] = defaultdict(int)
    rated_by_runner: dict[str, int] = defaultdict(int)
    for row in deduped:
        by_runner[row["current_runner_key"]] += 1
        if row["performance_rating"]:
            rated_by_runner[row["current_runner_key"]] += 1
    audit = {
        "schemaVersion": "edgeiq_current_runner_profile_history_v1_audit",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "currentRunners": len(runners),
        "uniqueHorseProfiles": len(unique),
        "historyRows": len(deduped),
        "ratedHistoryRows": sum(1 for row in deduped if row["performance_rating"]),
        "runnersWith1PlusHistory": sum(1 for r in runners if by_runner[r["current_runner_key"]] >= 1),
        "runnersWith3PlusHistory": sum(1 for r in runners if by_runner[r["current_runner_key"]] >= 3),
        "runnersWith5PlusHistory": sum(1 for r in runners if by_runner[r["current_runner_key"]] >= 5),
        "runnersWith1PlusRatedHistory": sum(1 for r in runners if rated_by_runner[r["current_runner_key"]] >= 1),
        "failures": failures,
        "output": str(OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("EDGEIQ_CURRENT_RUNNER_PROFILE_HISTORY_V1 COMPLETE")
    for key in ("currentRunners", "uniqueHorseProfiles", "historyRows", "ratedHistoryRows", "runnersWith1PlusHistory", "runnersWith3PlusHistory", "runnersWith5PlusHistory", "runnersWith1PlusRatedHistory"):
        print(f"{key.upper()}={audit[key]}")
    print(f"PROFILE_FAILURES={len(failures)}")
    return 0 if deduped else 1


if __name__ == "__main__":
    raise SystemExit(main())
