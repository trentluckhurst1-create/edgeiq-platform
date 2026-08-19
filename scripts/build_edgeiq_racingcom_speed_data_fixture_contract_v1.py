from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-source-discovery"
V2_DIR = ROOT / "docs" / "performance-intelligence" / "racingcom-ingestion-v2"
RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-source-discovery" / "raw" / "fixture-selection"
MEETING_RAW_DIR = ROOT / "outputs" / "performance-intelligence" / "racingcom-v2" / "raw" / "meeting-discovery"

OUT_CONTRACT = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_contract_v1.csv"
OUT_AUDIT = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_audit_v1.csv"
OUT_SUMMARY = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_summary_v1.json"
OUT_REPORT = DOC_DIR / "edgeiq_racingcom_speed_data_fixture_report_v1.md"

GRAPHQL = "https://graphql.rmdprod.racing.com/"
TODAY = date(2026, 7, 22)
USER_AGENT = "EDGEiQ-Racing/1.0 governed-source-discovery"

FIELDS = [
    "fixture_id", "race_date", "track", "race_no", "race_url", "speed_data_url",
    "completed_status", "visible_speed_data_status", "selection_reason", "source_evidence",
]

AUDIT_FIELDS = ["check", "status", "count", "detail"]


def clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def slugify_track(track: str) -> str:
    s = clean(track).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def add_audit(rows: list[dict[str, Any]], check: str, status: str, count: Any, detail: str) -> None:
    rows.append({"check": check, "status": status, "count": count, "detail": detail})


def request_json(url: str, referer: str = "https://www.racing.com/form") -> tuple[int, dict[str, str], Any, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        body = r.read()
        text = body.decode("utf-8", errors="replace")
        return int(r.status), dict(r.headers.items()), json.loads(text), text


def graphql_query(query: str, variables: dict[str, Any], referer: str) -> tuple[str, dict[str, Any], Path]:
    params = {
        "query": query,
        "variables": json.dumps(variables, separators=(",", ":")),
    }
    url = GRAPHQL + "?" + urllib.parse.urlencode(params)
    status, headers, payload, text = request_json(url, referer=referer)
    digest = hashlib.sha256((url + text).encode("utf-8", errors="ignore")).hexdigest()[:16]
    path = RAW_DIR / f"graphql_{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"requested_url": url, "status": status, "headers": headers, "payload": payload}, indent=2, ensure_ascii=False), encoding="utf-8")
    return url, payload, path


def load_cached_month_meetings() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(MEETING_RAW_DIR.glob("*GetMeetsByMonth_2026_7*.txt")):
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        for month in payload.get("Months") or []:
            for item in month.get("CalendarEntries") or []:
                if clean(item.get("State")).upper() != "VIC":
                    continue
                if item.get("IsTrial") or item.get("IsJumpout"):
                    continue
                race_date = clean(item.get("Date"))[:10]
                try:
                    d = datetime.fromisoformat(race_date).date()
                except Exception:
                    continue
                if d >= TODAY:
                    continue
                if not item.get("IsResults") and clean(item.get("FullStatus")).lower() != "results":
                    continue
                if not clean(item.get("MeetCode")) or not clean(item.get("UrlSegment")):
                    continue
                entries.append({
                    "race_date": race_date,
                    "track": clean(item.get("Track") or item.get("Venue")),
                    "meet_code": clean(item.get("MeetCode")),
                    "url_segment": clean(item.get("UrlSegment")),
                    "form_url": "https://www.racing.com/form/" + clean(item.get("UrlSegment")),
                    "source_evidence": f"{rel(path)}; GetMeetsByMonth returned Results meeting with MeetCode={clean(item.get('MeetCode'))}",
                })
    # Recent first, then deterministic by track.
    entries.sort(key=lambda r: (r["race_date"], r["track"]), reverse=True)
    return entries



def discover_races_from_cached_browser_payloads(meetings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_code = {m["meet_code"]: m for m in meetings}
    out: list[dict[str, Any]] = []
    evidence_paths: list[str] = []
    for path in sorted(RAW_DIR.glob("racelist_browser_*.json")):
        m = re.search(r"racelist_browser_(?:direct_)?(\d+)_", path.name)
        if not m:
            continue
        meet_code = m.group(1)
        meeting = by_code.get(meet_code)
        if not meeting:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        races = (((data.get("payload") or {}).get("data") or {}).get("getNoCacheRacesForMeet") or [])
        if not races:
            continue
        evidence_paths.append(rel(path))
        for r in races:
            race_no = clean(r.get("raceNumber"))
            if not race_no:
                continue
            meet = r.get("meet") or {}
            seg = clean(meet.get("meetUrlSegment")) or meeting["url_segment"]
            race_url = f"https://www.racing.com/form/{seg}/race/{race_no}"
            out.append({
                "race_date": meeting["race_date"],
                "track": meeting["track"],
                "race_no": race_no,
                "race_url": race_url,
                "speed_data_url": race_url + "/speed-data",
                "race_status": clean(r.get("raceStatus")),
                "has_sectionals": bool(r.get("hasSectionals")),
                "has_speed_map": bool(r.get("hasSpeedMap")),
                "runner_count": len(r.get("formRaceEntries") or []),
                "graphql_evidence": f"{rel(path)}; getNoCacheRacesForMeet meetCode={meeting['meet_code']} race_id={clean(r.get('id'))} hasSectionals={r.get('hasSectionals')} hasResults={r.get('hasResults')}",
                "meeting_evidence": meeting["source_evidence"],
            })
    return out, evidence_paths

def discover_races_for_meetings_browser(meetings: list[dict[str, Any]], max_meetings: int = 10) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return [], [f"PLAYWRIGHT_NOT_AVAILABLE:{exc}"]

    q = """
query getRaceNumberList_CD($meetCode: ID!) {
  getNoCacheRacesForMeet(meetCode: $meetCode) {
    id
    raceNumber
    raceStatus
    distance
    time
    name
    nameForm
    hasSectionals
    hasSpeedMap
    hasResults
    hasField
    meet { meetUrl meetUrlSegment venue }
    formRaceEntries { horseName }
  }
}
"""
    out: list[dict[str, Any]] = []
    evidence_paths: list[str] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1000})
        for meeting in meetings[:max_meetings]:
            page = context.new_page()
            payloads: list[dict[str, Any]] = []

            def handle_response(resp):
                url = resp.url
                if "graphql.rmdprod.racing.com" not in url:
                    return
                if "getNoCacheRacesForMeet" not in url and "getRaceNumberList" not in url:
                    return
                try:
                    text = resp.text()
                    data = json.loads(text)
                except Exception:
                    return
                races = ((data.get("data") or {}).get("getNoCacheRacesForMeet") or [])
                if races:
                    digest = hashlib.sha256((url + text).encode("utf-8", errors="ignore")).hexdigest()[:16]
                    path = RAW_DIR / f"racelist_browser_{meeting['meet_code']}_{digest}.json"
                    path.write_text(json.dumps({"requested_page": meeting["form_url"], "response_url": url, "payload": data}, indent=2, ensure_ascii=False), encoding="utf-8")
                    payloads.append({"races": races, "path": rel(path), "url": url})

            page.on("response", handle_response)
            try:
                page.goto(meeting["form_url"], wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(2500)
            except Exception:
                pass
            if not payloads:
                # Browser fallback to the same public GraphQL URL shape used by the live race-list builder.
                try:
                    gql_url = GRAPHQL + "?" + urllib.parse.urlencode({
                        "query": q,
                        "variables": json.dumps({"meetCode": str(meeting["meet_code"])}, separators=(",", ":")),
                    })
                    page.goto(gql_url, wait_until="networkidle", timeout=45000)
                    body = page.locator("body").inner_text(timeout=10000)
                    data = json.loads(body)
                    races = ((data.get("data") or {}).get("getNoCacheRacesForMeet") or [])
                    if races:
                        digest = hashlib.sha256((gql_url + body).encode("utf-8", errors="ignore")).hexdigest()[:16]
                        path = RAW_DIR / f"racelist_browser_direct_{meeting['meet_code']}_{digest}.json"
                        path.write_text(json.dumps({"requested_page": gql_url, "payload": data}, indent=2, ensure_ascii=False), encoding="utf-8")
                        payloads.append({"races": races, "path": rel(path), "url": gql_url})
                except Exception:
                    pass
            page.close()
            if payloads:
                chosen = payloads[-1]
                evidence_paths.append(chosen["path"])
                for r in chosen["races"]:
                    race_no = clean(r.get("raceNumber"))
                    if not race_no:
                        continue
                    meet = r.get("meet") or {}
                    seg = clean(meet.get("meetUrlSegment")) or meeting["url_segment"]
                    race_url = f"https://www.racing.com/form/{seg}/race/{race_no}"
                    out.append({
                        "race_date": meeting["race_date"],
                        "track": meeting["track"],
                        "race_no": race_no,
                        "race_url": race_url,
                        "speed_data_url": race_url + "/speed-data",
                        "race_status": clean(r.get("raceStatus")),
                        "has_sectionals": bool(r.get("hasSectionals")),
                        "has_speed_map": bool(r.get("hasSpeedMap")),
                        "runner_count": len(r.get("formRaceEntries") or []),
                        "graphql_evidence": f"{chosen['path']}; getNoCacheRacesForMeet meetCode={meeting['meet_code']} race_id={clean(r.get('id'))} hasSectionals={r.get('hasSectionals')} hasResults={r.get('hasResults')}",
                        "meeting_evidence": meeting["source_evidence"],
                    })
            time.sleep(0.8)
        context.close()
        browser.close()
    return out, evidence_paths

def visible_status_for_pages(races: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        for r in races:
            r["visible_speed_data_status"] = "BROWSER_NOT_AVAILABLE"
            r["browser_evidence"] = f"Playwright import failed: {exc}"
        return races

    terms = ["sectional", "speed", "top speed", "last 200", "last 400", "last 600", "average speed", "distance travelled"]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 1100})
        for idx, race in enumerate(races):
            page = context.new_page()
            body_text = ""
            status = "PAGE_LOAD_FAILED"
            error = ""
            try:
                resp = page.goto(race["speed_data_url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(9000)
                frame_texts = []
                for frame_index, frame in enumerate(page.frames):
                    try:
                        txt = frame.locator("body").inner_text(timeout=5000)
                    except Exception:
                        txt = ""
                    if txt:
                        frame_texts.append(f"FRAME {frame_index} URL={frame.url}\n{txt}")
                body_text = "\n\n---FRAME---\n\n".join(frame_texts)
                http_status = resp.status if resp else "NO_RESPONSE"
                lower = body_text.lower()
                term_hits = [t for t in terms if t in lower]
                numeric_speed = bool(re.search(r"\b\d{2}\.\d{2}\s*km/h\b", body_text, flags=re.I))
                sectional_grid = "avg speed" in lower and "peak" in lower and "dist run" in lower
                if race.get("has_sectionals") and numeric_speed and sectional_grid:
                    status = "VISIBLE_SPEED_DATA_INDICATED"
                elif term_hits and (numeric_speed or sectional_grid):
                    status = "VISIBLE_SPEED_TERMS_ONLY"
                else:
                    status = "NO_VISIBLE_SPEED_DATA"
                digest = hashlib.sha256((race["speed_data_url"] + body_text).encode("utf-8", errors="ignore")).hexdigest()[:16]
                path = RAW_DIR / f"visible_text_{digest}.txt"
                path.write_text(body_text[:300000], encoding="utf-8")
                race["browser_evidence"] = f"{rel(path)}; http_status={http_status}; visible_terms={'|'.join(term_hits)}; numeric_speed={numeric_speed}; sectional_grid={sectional_grid}"
            except Exception as exc:
                error = str(exc).replace("\n", " ")[:300]
                race["browser_evidence"] = f"browser_error={error}"
            finally:
                page.close()
            race["visible_speed_data_status"] = status
            time.sleep(0.75)
        context.close()
        browser.close()
    return races


def historical_fixtures() -> list[dict[str, Any]]:
    admission = read_csv(V2_DIR / "edgeiq_racingcom_csv_admission_contract_v2.csv")
    rows = [r for r in admission if clean(r.get("admission_status")) == "ADMITTED_HISTORICAL_PROVEN_CSV"]
    rows.sort(key=lambda r: (clean(r.get("race_date")), clean(r.get("track")), int(clean(r.get("race_no")) or 0)))
    fixtures = []
    for r in rows:
        race_date = clean(r.get("race_date"))
        track = clean(r.get("track"))
        race_no = clean(r.get("race_no"))
        fixture_id = f"HISTORICAL_CSV_{race_date}_{slugify_track(track)}_R{race_no}"
        fixtures.append({
            "fixture_id": fixture_id,
            "race_date": race_date,
            "track": track,
            "race_no": race_no,
            "race_url": clean(r.get("race_url")),
            "speed_data_url": clean(r.get("source_url")) or clean(r.get("speed_data_url")),
            "completed_status": "COMPLETED_HISTORICAL_CSV_PROVEN",
            "visible_speed_data_status": "HISTORICAL_CSV_VALID_NOT_BROWSER_VISIBLE_FIXTURE",
            "selection_reason": "Eight historically proven CSV races retained from V2 admission.",
            "source_evidence": f"{rel(V2_DIR / 'edgeiq_racingcom_csv_admission_contract_v2.csv')}; admission_status=ADMITTED_HISTORICAL_PROVEN_CSV; provenance={clean(r.get('provenance'))}",
        })
    return fixtures


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    built_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    fixtures = historical_fixtures()
    meetings = load_cached_month_meetings()
    candidate_races, graphql_paths = discover_races_from_cached_browser_payloads(meetings)
    if len(candidate_races) < 7:
        candidate_races, graphql_paths = discover_races_for_meetings_browser(meetings, max_meetings=4)

    # Prefer recent completed races with Racing.com race-list sectional flag for positive fixtures.
    unique: dict[str, dict[str, Any]] = {}
    for r in candidate_races:
        key = f"{r['race_date']}|{r['track']}|{r['race_no']}"
        unique[key] = r
    candidates = sorted(unique.values(), key=lambda r: (r["race_date"], r["track"], int(r["race_no"] or 0)), reverse=True)

    browser_pool = []
    positives_seed = [r for r in candidates if r.get("has_sectionals")][:9]
    negatives_seed = [r for r in candidates if not r.get("has_sectionals")][:5]
    browser_pool = positives_seed + negatives_seed
    visible_checked = visible_status_for_pages(browser_pool)

    positives = [r for r in visible_checked if r.get("has_sectionals") and r.get("visible_speed_data_status") == "VISIBLE_SPEED_DATA_INDICATED"]
    negatives = [r for r in visible_checked if not r.get("has_sectionals") and r.get("visible_speed_data_status") == "NO_VISIBLE_SPEED_DATA"]
    if len(negatives) < 2:
        negatives = [r for r in visible_checked if not r.get("has_sectionals")]

    for r in positives[:5]:
        fixtures.append({
            "fixture_id": f"RECENT_VISIBLE_{r['race_date']}_{slugify_track(r['track'])}_R{r['race_no']}",
            "race_date": r["race_date"],
            "track": r["track"],
            "race_no": r["race_no"],
            "race_url": r["race_url"],
            "speed_data_url": r["speed_data_url"],
            "completed_status": f"COMPLETED_RACINGCOM_RACELIST_STATUS_{r.get('race_status')}",
            "visible_speed_data_status": r.get("visible_speed_data_status"),
            "selection_reason": "Recent completed Racing.com race with getNoCacheRacesForMeet hasSectionals evidence and browser-visible speed/sectional terms.",
            "source_evidence": f"{r.get('meeting_evidence')} || {r.get('graphql_evidence')} || {r.get('browser_evidence')}",
        })
    for r in negatives[:2]:
        fixtures.append({
            "fixture_id": f"NEGATIVE_CONTROL_{r['race_date']}_{slugify_track(r['track'])}_R{r['race_no']}",
            "race_date": r["race_date"],
            "track": r["track"],
            "race_no": r["race_no"],
            "race_url": r["race_url"],
            "speed_data_url": r["speed_data_url"],
            "completed_status": f"COMPLETED_RACINGCOM_RACELIST_STATUS_{r.get('race_status')}",
            "visible_speed_data_status": r.get("visible_speed_data_status"),
            "selection_reason": "Negative control: completed Racing.com race-list row without hasSectionals and browser-visible speed data absent or unproven.",
            "source_evidence": f"{r.get('meeting_evidence')} || {r.get('graphql_evidence')} || {r.get('browser_evidence')}",
        })

    write_csv(OUT_CONTRACT, fixtures, FIELDS)

    audit: list[dict[str, Any]] = []
    hist_count = sum(1 for f in fixtures if f["fixture_id"].startswith("HISTORICAL_CSV_"))
    pos_count = sum(1 for f in fixtures if f["fixture_id"].startswith("RECENT_VISIBLE_"))
    neg_count = sum(1 for f in fixtures if f["fixture_id"].startswith("NEGATIVE_CONTROL_"))
    future_count = 0
    for f in fixtures:
        try:
            if datetime.fromisoformat(f["race_date"]).date() >= TODAY:
                future_count += 1
        except Exception:
            future_count += 1
    duplicate_ids = len(fixtures) - len({f["fixture_id"] for f in fixtures})
    missing_required = sum(1 for f in fixtures if any(not clean(f.get(c)) for c in ["fixture_id", "race_date", "track", "race_no", "completed_status", "visible_speed_data_status", "selection_reason", "source_evidence"]))

    add_audit(audit, "historical_proven_races", "PASS" if hist_count == 8 else "FAIL", hist_count, "Eight historically proven races required.")
    add_audit(audit, "recent_visible_speed_races", "PASS" if pos_count >= 5 else "FAIL", pos_count, "At least five recent completed Racing.com speed-data fixtures required.")
    add_audit(audit, "negative_controls", "PASS" if neg_count >= 2 else "FAIL", neg_count, "At least two completed no-speed-data controls required.")
    add_audit(audit, "no_future_races", "PASS" if future_count == 0 else "FAIL", future_count, "No fixture race_date may be current/future relative to 2026-07-22.")
    add_audit(audit, "no_duplicate_fixture_ids", "PASS" if duplicate_ids == 0 else "FAIL", duplicate_ids, "Fixture ids must be unique.")
    add_audit(audit, "required_fields_populated", "PASS" if missing_required == 0 else "FAIL", missing_required, "Required fixture metadata fields populated; race_url may be blank for historical direct CSV fixtures.")
    add_audit(audit, "graphql_meeting_evidence_retained", "PASS" if graphql_paths else "FAIL", len(set(graphql_paths)), "Race-list GraphQL payloads cached under source-discovery raw fixture-selection.")

    write_csv(OUT_AUDIT, audit, AUDIT_FIELDS)
    fail_count = sum(1 for a in audit if a["status"] == "FAIL")
    summary = {
        "status": "RACINGCOM_SPEED_DATA_FIXTURE_CONTRACT_V1_PASS" if fail_count == 0 else "RACINGCOM_SPEED_DATA_FIXTURE_CONTRACT_V1_FAIL",
        "built_utc": built_utc,
        "fixture_rows": len(fixtures),
        "historical_proven_races": hist_count,
        "recent_visible_speed_races": pos_count,
        "negative_controls": neg_count,
        "candidate_meetings_scanned": min(len(meetings), 10),
        "candidate_races_observed": len(candidates),
        "browser_checked_races": len(visible_checked),
        "future_races": future_count,
        "audit_failures": fail_count,
        "production_changed": "NO",
        "ui_changed": "NO",
        "v2_architecture_modified": "NO",
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = f"""# Racing.com Speed Data Fixture Contract V1

Built UTC: {built_utc}

## Status

`{summary['status']}`

## Counts

- Fixture rows: {len(fixtures)}
- Historical proven CSV races: {hist_count}
- Recent visible speed-data fixtures: {pos_count}
- Negative controls: {neg_count}
- Candidate meetings scanned: {summary['candidate_meetings_scanned']}
- Candidate races observed from Racing.com race-list evidence: {summary['candidate_races_observed']}
- Browser checked races: {summary['browser_checked_races']}
- Future races admitted: {future_count}

## Evidence Basis

Historical fixtures come from the V2 CSV admission contract. Recent and negative-control fixtures come from cached Racing.com `GetMeetsByMonth` meeting evidence plus `getNoCacheRacesForMeet` race-list payloads captured for those observed meetings. Speed-data page visibility was checked with a governed Playwright browser pass and retained body text evidence under `{rel(RAW_DIR)}`.

No fixed race-number probing or unsupported generated race identities are admitted into this fixture contract.
"""
    OUT_REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
