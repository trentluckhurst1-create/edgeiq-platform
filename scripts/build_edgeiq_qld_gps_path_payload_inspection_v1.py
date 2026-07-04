from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from edgeiq_memory_safe_io import safe_read_csv, write_csv_atomic


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

IN_DISCOVERY = DATA / "edgeiq_qld_positional_source_discovery_v1.csv"
IN_REPAIR = DATA / "edgeiq_qld_positional_repair_targets_v1.csv"
IN_INGESTION = DATA / "edgeiq_qld_telemetry_ingestion_v1.csv"
IN_LINEAGE = DATA / "edgeiq_qld_telemetry_lineage_v1.csv"

OUT_INSPECTION = DATA / "edgeiq_qld_gps_path_payload_inspection_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_qld_gps_path_payload_summary_v1.csv"
OUT_CANDIDATES = DATA / "edgeiq_qld_explicit_position_payload_candidates_v1.csv"

INSPECTION_FIELDS = [
    "track",
    "source_url",
    "source_hint",
    "payload_candidate_type",
    "coordinate_signal_detected",
    "lane_path_signal_detected",
    "running_order_signal_detected",
    "explicit_rank_signal_detected",
    "download_candidate_detected",
    "risk_level",
    "recommended_followup",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value"]

OFFLINE_NOTE = (
    "QLD GPS/path payload inspection only. Existing URLs and local lineage were inspected without aggressive "
    "scraping, brute forcing, modelling, predictions, overlays, ratings, betting, or execution."
)


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", "") or 0))
    except ValueError:
        return 0


def split_hints(value: object) -> list[str]:
    text = clean(value)
    if not text:
        return []
    parts = [part.strip() for part in text.split("|")]
    return [part for part in parts if part]


def is_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def normalise_track(value: object) -> str:
    track = clean(value).upper()
    aliases = {
        "AQUIS PARK GOLD COAST": "GOLD COAST",
        "AQUIS PARK GOLD COAST POLY": "GOLD COAST POLY",
        "LADBROKES CANNON PARK": "CAIRNS",
        "PICKLEBET PARK WARWICK": "WARWICK",
        "SUNSHINE COAST POLY": "SUNSHINE COAST POLY",
    }
    return aliases.get(track, track)


def infer_download_type(url: str, hint: str) -> str:
    combined = f"{url} {hint}".lower()
    parsed = urlparse(url)
    query_path = parse_qs(parsed.query).get("path", [""])[0].lower()
    combined = f"{combined} {query_path}"
    if ".json" in combined or "json" in combined:
        return "JSON_DOWNLOAD_HINT"
    if ".zip" in combined or "zip" in combined:
        return "ZIP_DOWNLOAD_HINT"
    if ".xlsx" in combined or ".xls" in combined:
        return "XLSX_DOWNLOAD_HINT"
    if ".csv" in combined:
        return "CSV_DOWNLOAD_HINT"
    if "ashx" in combined or "racingfile" in combined:
        return "ASHX_FILE_HANDLER_HINT"
    if "replay" in combined or "video" in combined:
        return "REPLAY_PAGE_HINT"
    if "map" in combined or "gps" in combined:
        return "MAP_PAYLOAD_HINT"
    return "NO_DOWNLOAD_HINT"


def signal_flags(row: dict[str, str], ingestion_rows: list[dict[str, str]], url: str, hint: str) -> dict[str, str]:
    combined = " ".join(
        [
            upper(row.get("source_hint")),
            upper(row.get("source_type")),
            upper(row.get("positional_signal_type")),
            upper(hint),
            upper(url),
        ]
    )
    matching = [ing for ing in ingestion_rows if clean(ing.get("source_url")) == url] if url else []
    has_gps_speed = any(clean(ing.get("gps_speed")) for ing in matching)
    has_gps_position = any(clean(ing.get("gps_position")) for ing in matching)
    has_rank = any(clean(ing.get("rank_at_split")) or clean(ing.get("position_at_split")) for ing in matching)
    return {
        "coordinate": "YES" if has_gps_position or any(token in combined for token in ["COORDINATE", "GPS_POSITION", "LAT", "LON", "MAP"]) else "NO",
        "lane_path": "YES" if any(token in combined for token in ["LANE", "PATH", "TRACK MAP", "GPS MAP", "DISTANCE_TRAVELLED"]) else "NO",
        "running_order": "YES" if any(token in combined for token in ["RUNNING_ORDER", "ORDER", "POSITION_AT_SPLIT"]) else "NO",
        "rank": "YES" if has_rank or any(token in combined for token in ["RANK", "SECTIONAL_RANK", "LAST_200_RANK", "LAST_400_RANK", "LAST_600_RANK"]) else "NO",
        "gps_speed": "YES" if has_gps_speed or "SPEED" in combined else "NO",
    }


def classify_payload(flags: dict[str, str], download_type: str, source_type: str) -> str:
    if flags["rank"] == "YES" or flags["running_order"] == "YES":
        return "EXPLICIT_POSITION_PAYLOAD_CANDIDATE"
    if flags["coordinate"] == "YES":
        return "GPS_COORDINATE_PAYLOAD_CANDIDATE"
    if flags["lane_path"] == "YES":
        return "LANE_PATH_PAYLOAD_CANDIDATE"
    if "REPLAY" in download_type or "REPLAY" in source_type:
        return "RUNNING_ORDER_PAYLOAD_CANDIDATE"
    if download_type != "NO_DOWNLOAD_HINT" or flags["gps_speed"] == "YES":
        return "WEAK_PAYLOAD_HINT"
    return "NO_PAYLOAD_HINT"


def risk_level(payload_type: str, flags: dict[str, str], download_type: str) -> str:
    if payload_type == "EXPLICIT_POSITION_PAYLOAD_CANDIDATE" and download_type != "NO_DOWNLOAD_HINT":
        return "MEDIUM_VERIFY_REQUIRED"
    if payload_type in {"GPS_COORDINATE_PAYLOAD_CANDIDATE", "LANE_PATH_PAYLOAD_CANDIDATE"}:
        return "MEDIUM_ENDPOINT_UNCONFIRMED"
    if payload_type == "RUNNING_ORDER_PAYLOAD_CANDIDATE":
        return "HIGH_REPLAY_STRUCTURE_UNPROVEN"
    if payload_type == "WEAK_PAYLOAD_HINT":
        return "HIGH_WEAK_OR_DERIVED_ONLY"
    return "LOW_NO_ACTIONABLE_HINT"


def followup(payload_type: str, track: str, download_type: str) -> str:
    if payload_type == "EXPLICIT_POSITION_PAYLOAD_CANDIDATE":
        return f"Inspect cached QLD file lineage for {track} and verify whether rank/order fields can be populated from the same source path."
    if payload_type == "GPS_COORDINATE_PAYLOAD_CANDIDATE":
        return f"Review existing QLD source pages for {track} for map/coordinate assets referenced alongside the known {download_type}; no endpoint brute force."
    if payload_type == "LANE_PATH_PAYLOAD_CANDIDATE":
        return f"Review QLD timing visualisation/source metadata for {track} to determine whether path/lane/distance-travelled payloads are exposed."
    if payload_type == "RUNNING_ORDER_PAYLOAD_CANDIDATE":
        return f"Inspect local/cached replay or timing metadata for {track}; only map named assets already referenced by source pages."
    if payload_type == "WEAK_PAYLOAD_HINT":
        return f"Keep {track} as a weak source hint; collect another official QLD CSV before deeper inspection."
    return f"No actionable payload hint found for {track}; do not expand collection from this row."


def extract_urls(discovery_rows: list[dict[str, str]], repair_rows: list[dict[str, str]], ingestion_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in discovery_rows + repair_rows:
        hints = split_hints(row.get("source_hint"))
        url_hints = [hint for hint in hints if is_url(hint)]
        if not url_hints:
            rows.append({**row, "source_url": "", "hint": clean(row.get("source_hint"))})
        for hint in url_hints:
            rows.append({**row, "source_url": hint, "hint": hint})
    seen_ingestion: set[tuple[str, str]] = set()
    for row in ingestion_rows:
        source_url = clean(row.get("source_url"))
        if not source_url:
            continue
        key = (normalise_track(row.get("track")), source_url)
        if key in seen_ingestion:
            continue
        seen_ingestion.add(key)
        rows.append(
            {
                "track": normalise_track(row.get("track")),
                "source_hint": source_url,
                "source_type": "INGESTED_Qld_SOURCE_URL",
                "positional_signal_type": "INGESTED_RACINGFILE_LINEAGE",
                "evidence_gap": "INGESTED_SOURCE_LINEAGE_INSPECTION",
                "expected_value": "SOURCE_LINEAGE_REVIEW",
                "risk": "",
                "recommended_followup": "",
                "notes": "",
                "source_url": source_url,
                "hint": source_url,
            }
        )
    return rows


def build_inspection() -> None:
    discovery_rows = safe_read_csv(IN_DISCOVERY)
    repair_rows = safe_read_csv(IN_REPAIR)
    ingestion_rows = safe_read_csv(IN_INGESTION, max_rows=50000)
    lineage_rows = safe_read_csv(IN_LINEAGE)

    candidate_inputs = extract_urls(discovery_rows, repair_rows, ingestion_rows)
    inspection_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for row in candidate_inputs:
        track = normalise_track(row.get("track")) or "QLD_UNKNOWN_TRACK"
        url = clean(row.get("source_url"))
        hint = clean(row.get("hint")) or clean(row.get("source_hint"))
        download_type = infer_download_type(url, hint)
        flags = signal_flags(row, ingestion_rows, url, hint)
        payload_type = classify_payload(flags, download_type, upper(row.get("source_type")))
        key = (track, url, payload_type, clean(row.get("positional_signal_type")))
        if key in seen:
            continue
        seen.add(key)
        download_candidate = "YES" if download_type != "NO_DOWNLOAD_HINT" else "NO"
        inspection_rows.append(
            {
                "track": track,
                "source_url": url,
                "source_hint": hint,
                "payload_candidate_type": payload_type,
                "coordinate_signal_detected": flags["coordinate"],
                "lane_path_signal_detected": flags["lane_path"],
                "running_order_signal_detected": flags["running_order"],
                "explicit_rank_signal_detected": flags["rank"],
                "download_candidate_detected": download_candidate,
                "risk_level": risk_level(payload_type, flags, download_type),
                "recommended_followup": followup(payload_type, track, download_type),
                "notes": f"{OFFLINE_NOTE} download_type={download_type}; lineage_sources={len(lineage_rows)}.",
            }
        )

    type_counts = Counter(row["payload_candidate_type"] for row in inspection_rows)
    risk_counts = Counter(row["risk_level"] for row in inspection_rows)
    explicit_candidates = [
        row
        for row in inspection_rows
        if row["payload_candidate_type"]
        in {
            "EXPLICIT_POSITION_PAYLOAD_CANDIDATE",
            "GPS_COORDINATE_PAYLOAD_CANDIDATE",
            "LANE_PATH_PAYLOAD_CANDIDATE",
            "RUNNING_ORDER_PAYLOAD_CANDIDATE",
        }
    ]

    summary = [
        {"metric": "inspection_rows", "value": str(len(inspection_rows))},
        {"metric": "explicit_candidate_rows", "value": str(len(explicit_candidates))},
        {"metric": "explicit_position_payload_candidates", "value": str(type_counts.get("EXPLICIT_POSITION_PAYLOAD_CANDIDATE", 0))},
        {"metric": "gps_coordinate_payload_candidates", "value": str(type_counts.get("GPS_COORDINATE_PAYLOAD_CANDIDATE", 0))},
        {"metric": "lane_path_payload_candidates", "value": str(type_counts.get("LANE_PATH_PAYLOAD_CANDIDATE", 0))},
        {"metric": "running_order_payload_candidates", "value": str(type_counts.get("RUNNING_ORDER_PAYLOAD_CANDIDATE", 0))},
        {"metric": "weak_payload_hints", "value": str(type_counts.get("WEAK_PAYLOAD_HINT", 0))},
        {"metric": "no_payload_hints", "value": str(type_counts.get("NO_PAYLOAD_HINT", 0))},
        {"metric": "download_candidate_rows", "value": str(sum(1 for row in inspection_rows if row["download_candidate_detected"] == "YES"))},
        {"metric": "coordinate_signal_rows", "value": str(sum(1 for row in inspection_rows if row["coordinate_signal_detected"] == "YES"))},
        {"metric": "lane_path_signal_rows", "value": str(sum(1 for row in inspection_rows if row["lane_path_signal_detected"] == "YES"))},
        {"metric": "running_order_signal_rows", "value": str(sum(1 for row in inspection_rows if row["running_order_signal_detected"] == "YES"))},
        {"metric": "explicit_rank_signal_rows", "value": str(sum(1 for row in inspection_rows if row["explicit_rank_signal_detected"] == "YES"))},
        {"metric": "medium_risk_rows", "value": str(sum(count for risk, count in risk_counts.items() if risk.startswith("MEDIUM")))},
        {"metric": "high_risk_rows", "value": str(sum(count for risk, count in risk_counts.items() if risk.startswith("HIGH")))},
        {"metric": "lineage_sources", "value": str(len(lineage_rows))},
        {"metric": "live_modelling_yes", "value": "0"},
        {"metric": "live_execution_yes", "value": "0"},
        {"metric": "offline_research_only", "value": "YES"},
    ]

    write_csv_atomic(OUT_INSPECTION, inspection_rows, INSPECTION_FIELDS)
    write_csv_atomic(OUT_SUMMARY, summary, SUMMARY_FIELDS)
    write_csv_atomic(OUT_CANDIDATES, explicit_candidates, INSPECTION_FIELDS)

    print(f"QLD GPS/path inspection rows: {len(inspection_rows)}")
    print(f"Explicit candidate rows: {len(explicit_candidates)}")
    print(f"GPS coordinate candidates: {type_counts.get('GPS_COORDINATE_PAYLOAD_CANDIDATE', 0)}")
    print(f"Lane/path candidates: {type_counts.get('LANE_PATH_PAYLOAD_CANDIDATE', 0)}")
    print("Live modelling: 0")
    print("Live execution: 0")


if __name__ == "__main__":
    build_inspection()
