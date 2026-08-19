from __future__ import annotations

import csv
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
CONFIG = ROOT / "config"
SCRIPTS = ROOT / "scripts"

OUT = DATA / "edgeiq_raw_sectional_payload_discovery_v1.csv"
SUMMARY = DATA / "edgeiq_raw_sectional_payload_discovery_summary_v1.csv"
SOURCE_MAP = DATA / "edgeiq_raw_sectional_payload_source_map_v1.csv"

DISCOVERY_FIELDS = [
    "source_type",
    "source_hint",
    "payload_structure_detected",
    "sectional_depth_detected",
    "early_mid_late_detected",
    "full_split_ladder_detected",
    "timing_metadata_detected",
    "horse_level_timing_detected",
    "payload_quality_potential",
    "recommended_followup",
    "risk_level",
    "notes",
]

SOURCE_MAP_FIELDS = [
    "source_name",
    "source_type",
    "source_hint",
    "source_file",
    "rows_or_size",
    "operation_or_endpoint",
    "payload_family",
    "detected_fields",
    "opportunity_type",
    "risk_level",
    "recommended_followup",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

SCAN_FILES = [
    DATA / "edgeiq_racingcom_speed_network_probe_v1.csv",
    DATA / "edgeiq_racingcom_completed_payload_probe_v1.csv",
    DATA / "edgeiq_racingcom_graphql_parser_v1.csv",
    DATA / "edgeiq_vic_real_chrome_network_log_v1.csv",
    DATA / "edgeiq_vic_real_chrome_network_log_v2.csv",
    DATA / "edgeiq_vic_racingcom_speed_data_diagnostics_v1.csv",
    DATA / "edgeiq_vic_racingcom_speed_data_ingestion_v1.csv",
    DATA / "edgeiq_csv_click_network_capture_v1.csv",
    DATA / "edgeiq_vic_visible_page_csv_click_v1.csv",
    DATA / "edgeiq_vic_dom_sectionals_raw_body_v1.txt",
    DATA / "edgeiq_vic_dom_sectionals_v3.csv",
    DATA / "edgeiq_sectional_discovered_links_v1.csv",
    DATA / "edgeiq_sectional_source_ingestion_v1.csv",
    DATA / "edgeiq_sectional_scraper_inventory.csv",
    DATA / "replay_links.csv",
    DATA / "sectionals.csv",
    CONFIG / "sectional_sources.csv",
]

SCRIPT_HINTS = [
    SCRIPTS / "probe_racingcom_speed_data_network_v1.py",
    SCRIPTS / "probe_racingcom_completed_speed_payload_v1.py",
    SCRIPTS / "build_edgeiq_racingcom_graphql_parser_v1.py",
    SCRIPTS / "build_edgeiq_racingcom_csv_ingestion_v1.py",
    SCRIPTS / "build_edgeiq_racingcom_calendar_discovery_v1.py",
    SCRIPTS / "build_edgeiq_vic_racingcom_speed_data_ingestion_v1.py",
    SCRIPTS / "build_edgeiq_vic_racingcom_browser_csv_downloader_v1.py",
    SCRIPTS / "click_visible_racingcom_csv_now_v1.py",
    SCRIPTS / "capture_csv_click_network_v1.py",
    SCRIPTS / "build_edgeiq_vic_dom_sectional_parser_v1.py",
    SCRIPTS / "build_edgeiq_vic_dom_sectional_parser_v2.py",
    SCRIPTS / "build_edgeiq_vic_dom_sectional_parser_v3.py",
    SCRIPTS / "run_edgeiq_vic_real_90day_sectional_backfill_v1.py",
]

SOURCE_TYPE_PATTERNS = [
    ("page embedded state", ["__NEXT_DATA__", "window.__", "hydration", "getLayoutForRoute", "layoutForRoute", "jsonLayout"]),
    ("JSON hydration payloads", ["application/json", "jsonLayout", "graphql", "operationName", "variables", "data"]),
    ("replay metadata", ["replay", "video", "media", "stream", "m3u8", "mp4"]),
    ("timing graphics payloads", ["timing", "sectional", "speed", "distanceTravelled", "topSpeed", "position", "distance_travelled"]),
    ("event/race APIs", ["getRace", "getMeeting", "getNoCacheRacesForMeet", "GetMeetingByVenue", "raceNumber", "raceStatus"]),
    ("sectional ladder APIs", ["last200", "last400", "last600", "toEightHundredMetresSeconds", "eightHundredToFourHundredMetresSeconds", "fourHundredToFinishMetresSeconds"]),
    ("websocket/event-stream hints", ["websocket", "wss://", "event-stream", "signalr", "socket.io", "EventSource"]),
    ("HTML embedded timing structures", ["text/html", "<script", "data-", "sectionals", "speed-data", "csv"]),
]

FIELD_PATTERNS = {
    "last200": re.compile(r"last[_-]?200|last200|last 200", re.I),
    "last400": re.compile(r"last[_-]?400|last400|last 400", re.I),
    "last600": re.compile(r"last[_-]?600|last600|last 600", re.I),
    "early": re.compile(r"toEightHundred|to800|early[_-]?speed|early", re.I),
    "mid": re.compile(r"eightHundredToFourHundred|800To400|midrace|mid[_-]?speed|middle", re.I),
    "late": re.compile(r"fourHundredToFinish|400ToFinish|late[_-]?speed|finish", re.I),
    "top_speed": re.compile(r"topSpeed|top_speed|speedValue|speed_value", re.I),
    "distance": re.compile(r"distanceTravelled|distance_travelled|distance", re.I),
    "horse": re.compile(r"horseName|horse_name|runner|raceEntry|formRaceEntries|horse", re.I),
    "time": re.compile(r"winningTime|raceTime|standardTime|time", re.I),
    "sectional": re.compile(r"sectional|sectionals|split|splits", re.I),
    "replay": re.compile(r"replay|video|stream|media", re.I),
    "graphql": re.compile(r"graphql|query|operationName|variables", re.I),
}


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def read_text(path: Path, max_chars: int = 500_000) -> str:
    if not path.exists():
        return ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
            return handle.read(max_chars)
    except OSError:
        return ""


def read_csv_sample(path: Path, max_rows: int = 500) -> tuple[list[str], list[dict[str, str]], int]:
    if not path.exists():
        return [], [], 0
    rows: list[dict[str, str]] = []
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="", errors="ignore") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            for row in reader:
                total += 1
                if len(rows) < max_rows:
                    rows.append(dict(row))
        return headers, rows, total
    except (OSError, csv.Error):
        return [], [], 0


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{time.time_ns()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def detect_source_type(text: str, fallback: str = "") -> str:
    scores: Counter[str] = Counter()
    haystack = text[:250_000]
    for source_type, terms in SOURCE_TYPE_PATTERNS:
        for term in terms:
            if term.lower() in haystack.lower():
                scores[source_type] += 1
    if scores:
        return scores.most_common(1)[0][0]
    return fallback or "unknown local payload evidence"


def detected_fields(text: str) -> list[str]:
    fields = []
    for name, pattern in FIELD_PATTERNS.items():
        if pattern.search(text):
            fields.append(name)
    return fields


def bool_text(value: bool) -> str:
    return "YES" if value else "NO"


def estimate_depth(fields: list[str], text: str) -> str:
    depth = 0
    if "last200" in fields:
        depth += 1
    if "last400" in fields:
        depth += 1
    if "last600" in fields:
        depth += 1
    if "early" in fields:
        depth += 1
    if "mid" in fields:
        depth += 1
    if "late" in fields:
        depth += 1
    if "top_speed" in fields:
        depth += 1
    if "distance" in fields:
        depth += 1
    if depth >= 6:
        return "FULL_OR_NEAR_FULL_TIMING_DEPTH"
    if depth >= 4:
        return "MULTI_PHASE_TIMING_DEPTH"
    if depth >= 2:
        return "PARTIAL_TIMING_DEPTH"
    if "sectional" in fields or "speed" in text.lower():
        return "SECTIONAL_HINT_ONLY"
    return "NO_SECTIONAL_DEPTH_DETECTED"


def classify_potential(fields: list[str], source_type: str, rows_or_size: int, text: str) -> str:
    full = {"last200", "last400", "last600"}.issubset(set(fields))
    phase = {"early", "mid", "late"}.issubset(set(fields))
    horse_level = "horse" in fields and ("time" in fields or "sectional" in fields or phase)
    if full and phase and horse_level:
        return "HIGH_VALUE_PAYLOAD_DISCOVERY"
    if (phase and horse_level) or (full and horse_level) or ("event/race APIs" == source_type and rows_or_size > 0 and "sectional" in fields):
        return "MEDIUM_VALUE_DISCOVERY"
    if "sectional" in fields or "top_speed" in fields or "distance" in fields or "replay" in fields:
        return "LOW_VALUE_DISCOVERY"
    return "NO_USABLE_DISCOVERY"


def risk_for(source_type: str, text: str, potential: str) -> str:
    lowered = text.lower()
    if "auth" in lowered or "bearer" in lowered or "403" in lowered or "forbidden" in lowered:
        return "HIGH"
    if source_type == "websocket/event-stream hints":
        return "MEDIUM"
    if potential == "HIGH_VALUE_PAYLOAD_DISCOVERY":
        return "MEDIUM"
    if potential == "NO_USABLE_DISCOVERY":
        return "LOW"
    return "LOW"


def followup_for(source_type: str, fields: list[str], potential: str, risk: str) -> str:
    if risk == "HIGH":
        return "Do not automate; document access constraint and seek permitted source path."
    if potential == "HIGH_VALUE_PAYLOAD_DISCOVERY":
        return "Manually inspect saved raw payload lineage and build parser against cached samples before any polite recapture."
    if source_type in {"event/race APIs", "sectional ladder APIs", "JSON hydration payloads"}:
        return "Map operation names and cached response schemas; prefer saved payloads and explicit low-rate manual validation."
    if source_type == "page embedded state":
        return "Inspect embedded JSON/state extraction from saved HTML only; avoid live crawling until schema is proven."
    if source_type == "replay metadata":
        return "Catalogue replay metadata fields and confirm whether timing overlays exist in cached network logs."
    if source_type == "websocket/event-stream hints":
        return "Record endpoint hints only; do not connect or replay streams without explicit approval."
    if potential == "LOW_VALUE_DISCOVERY":
        return "Keep as source-map evidence; revisit only if high-priority environments remain unresolved."
    return "No immediate follow-up; insufficient local payload evidence."


def source_hint_from_row(row: dict[str, str], path: Path) -> str:
    for key in ["response_url", "url", "source_url", "page_url", "body_saved_path", "raw_sample_file", "source_file", "source_name"]:
        value = clean(row.get(key))
        if value:
            return value[:400]
    return path.name


def operation_from_hint(hint: str, row: dict[str, str]) -> str:
    explicit = clean(row.get("operation_name") or row.get("source_operation") or row.get("parse_hint"))
    if explicit:
        return explicit[:220]
    parsed = urlparse(hint)
    query = parse_qs(parsed.query)
    if "operationName" in query:
        return clean(query["operationName"][0])[:220]
    if "query" in query:
        decoded = unquote(query["query"][0])
        match = re.search(r"\b(query|mutation)\s+([A-Za-z0-9_]+)", decoded)
        if match:
            return match.group(2)[:220]
    return ""


def payload_family(source_type: str, operation: str, fields: list[str]) -> str:
    op = upper(operation)
    if "GETRACERESULT" in op:
        return "completed race result payload"
    if "RACENUMBERLIST" in op or "NOCACHERACES" in op:
        return "meeting race list payload"
    if "GETMEETING" in op or "MEETINGBYVENUE" in op:
        return "meeting metadata payload"
    if "BADGES" in op:
        return "runner badge/sectional-stars payload"
    if source_type == "replay metadata":
        return "replay metadata payload"
    if source_type == "HTML embedded timing structures":
        return "html/dom timing payload"
    if "last200" in fields or "early" in fields:
        return "sectional timing payload"
    if "graphql" in fields:
        return "graphql payload"
    return "source evidence payload"


def discovery_from_evidence(source_type: str, hint: str, fields: list[str], text: str, rows_or_size: int) -> dict[str, object]:
    full_split = {"last200", "last400", "last600"}.issubset(set(fields))
    early_mid_late = {"early", "mid", "late"}.issubset(set(fields))
    timing_metadata = any(field in fields for field in ["time", "top_speed", "distance", "early", "mid", "late"])
    horse_level = "horse" in fields and timing_metadata
    potential = classify_potential(fields, source_type, rows_or_size, text)
    risk = risk_for(source_type, text, potential)
    return {
        "source_type": source_type,
        "source_hint": hint,
        "payload_structure_detected": ",".join(fields) if fields else "NO_STRUCTURED_TIMING_FIELDS_DETECTED",
        "sectional_depth_detected": estimate_depth(fields, text),
        "early_mid_late_detected": bool_text(early_mid_late),
        "full_split_ladder_detected": bool_text(full_split),
        "timing_metadata_detected": bool_text(timing_metadata),
        "horse_level_timing_detected": bool_text(horse_level),
        "payload_quality_potential": potential,
        "recommended_followup": followup_for(source_type, fields, potential, risk),
        "risk_level": risk,
        "notes": "Offline local payload discovery only. No scraping, endpoint brute forcing, auth bypass, live modelling, ratings, overlays, or execution.",
    }


def scan_csv_file(path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    headers, rows, total = read_csv_sample(path)
    discoveries: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []
    if not headers and not rows:
        return discoveries, source_rows

    header_text = " ".join(headers)
    for index, row in enumerate(rows[:300]):
        row_text = json.dumps(row, ensure_ascii=False)
        text = f"{header_text} {row_text}"
        fields = detected_fields(text)
        source_type = detect_source_type(text, "CSV/network diagnostic payload")
        hint = source_hint_from_row(row, path)
        operation = operation_from_hint(hint, row)
        potential = classify_potential(fields, source_type, total, text)
        if potential == "NO_USABLE_DISCOVERY" and index > 30:
            continue
        discovery = discovery_from_evidence(source_type, hint, fields, text, total)
        discoveries.append(discovery)
        source_rows.append(
            {
                "source_name": path.stem,
                "source_type": source_type,
                "source_hint": hint,
                "source_file": str(path.relative_to(ROOT)),
                "rows_or_size": total,
                "operation_or_endpoint": operation,
                "payload_family": payload_family(source_type, operation, fields),
                "detected_fields": ",".join(fields),
                "opportunity_type": potential,
                "risk_level": discovery["risk_level"],
                "recommended_followup": discovery["recommended_followup"],
                "notes": "Mapped from existing local CSV/network diagnostics only.",
            }
        )
    return discoveries, source_rows


def scan_text_file(path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    text = read_text(path)
    if not text:
        return [], []
    fields = detected_fields(text)
    source_type = detect_source_type(text, "local text/script payload evidence")
    potential = classify_potential(fields, source_type, path.stat().st_size if path.exists() else 0, text)
    hint = str(path.relative_to(ROOT))
    discovery = discovery_from_evidence(source_type, hint, fields, text, path.stat().st_size if path.exists() else 0)
    source = {
        "source_name": path.stem,
        "source_type": source_type,
        "source_hint": hint,
        "source_file": hint,
        "rows_or_size": path.stat().st_size if path.exists() else 0,
        "operation_or_endpoint": "",
        "payload_family": payload_family(source_type, "", fields),
        "detected_fields": ",".join(fields),
        "opportunity_type": potential,
        "risk_level": discovery["risk_level"],
        "recommended_followup": discovery["recommended_followup"],
        "notes": "Mapped from existing local text/script evidence only.",
    }
    return [discovery], [source]


def dedupe_rows(rows: list[dict[str, object]], keys: list[str]) -> list[dict[str, object]]:
    deduped = []
    seen = set()
    for row in rows:
        key = tuple(clean(row.get(field)) for field in keys)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def sort_discoveries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rank = {
        "HIGH_VALUE_PAYLOAD_DISCOVERY": 4,
        "MEDIUM_VALUE_DISCOVERY": 3,
        "LOW_VALUE_DISCOVERY": 2,
        "NO_USABLE_DISCOVERY": 1,
    }
    return sorted(rows, key=lambda row: (-rank.get(clean(row.get("payload_quality_potential")), 0), clean(row.get("source_type")), clean(row.get("source_hint"))))


def build_summary(discoveries: list[dict[str, object]], source_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    potential = Counter(clean(row.get("payload_quality_potential")) for row in discoveries)
    source_types = Counter(clean(row.get("source_type")) for row in discoveries)
    full_split = sum(1 for row in discoveries if clean(row.get("full_split_ladder_detected")) == "YES")
    horse_level = sum(1 for row in discoveries if clean(row.get("horse_level_timing_detected")) == "YES")
    embedded_json = sum(1 for row in discoveries if clean(row.get("source_type")) in {"page embedded state", "JSON hydration payloads"})
    api_candidates = sum(1 for row in discoveries if clean(row.get("source_type")) in {"event/race APIs", "sectional ladder APIs", "JSON hydration payloads"})

    next_step = "Map Racing.com GraphQL completed-race payload schemas from cached responses, then manually validate fuller split/phase extraction on target environments before any new low-rate capture."
    if potential.get("HIGH_VALUE_PAYLOAD_DISCOVERY", 0):
        next_step = "Prioritise cached high-value payload schema parser before any live recapture."
    elif potential.get("MEDIUM_VALUE_DISCOVERY", 0):
        next_step = "Promote medium-value GraphQL/race API structures to manual schema validation against cached payload bodies."

    summary = [
        {"metric": "discoveries", "value": len(discoveries)},
        {"metric": "high_value_discoveries", "value": potential.get("HIGH_VALUE_PAYLOAD_DISCOVERY", 0)},
        {"metric": "medium_value_discoveries", "value": potential.get("MEDIUM_VALUE_DISCOVERY", 0)},
        {"metric": "low_value_discoveries", "value": potential.get("LOW_VALUE_DISCOVERY", 0)},
        {"metric": "no_usable_discoveries", "value": potential.get("NO_USABLE_DISCOVERY", 0)},
        {"metric": "full_split_candidates", "value": full_split},
        {"metric": "horse_level_timing_candidates", "value": horse_level},
        {"metric": "payload_sources_detected", "value": len(source_rows)},
        {"metric": "embedded_json_sources", "value": embedded_json},
        {"metric": "api_structure_candidates", "value": api_candidates},
        {"metric": "recommended_next_step", "value": next_step},
        {"metric": "live_modelling_yes", "value": 0},
        {"metric": "live_execution_yes", "value": 0},
        {"metric": "offline_research_only", "value": "YES"},
    ]
    for source_type, count in source_types.most_common():
        summary.append({"metric": f"source_type::{source_type}", "value": count})
    return summary


def main() -> None:
    discoveries: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []

    for path in SCAN_FILES:
        if not path.exists():
            continue
        if path.suffix.lower() == ".csv":
            found, mapped = scan_csv_file(path)
        else:
            found, mapped = scan_text_file(path)
        discoveries.extend(found)
        source_rows.extend(mapped)

    for path in SCRIPT_HINTS:
        if not path.exists():
            continue
        found, mapped = scan_text_file(path)
        discoveries.extend(found)
        source_rows.extend(mapped)

    discoveries = sort_discoveries(dedupe_rows(discoveries, ["source_type", "source_hint", "payload_structure_detected"]))
    source_rows = dedupe_rows(source_rows, ["source_name", "source_hint", "operation_or_endpoint", "payload_family"])
    summary = build_summary(discoveries, source_rows)

    write_csv(OUT, discoveries, DISCOVERY_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    write_csv(SOURCE_MAP, source_rows, SOURCE_MAP_FIELDS)

    print("=" * 88)
    print("EDGEIQ RAW SECTIONAL PAYLOAD DISCOVERY AUDIT V1")
    print("=" * 88)
    for row in summary[:14]:
        print(f"{row['metric']}: {row['value']}")
    print(f"saved: {OUT}")
    print(f"saved: {SUMMARY}")
    print(f"saved: {SOURCE_MAP}")


if __name__ == "__main__":
    main()
