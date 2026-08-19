from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "track-source-audit"
PUBLIC_DIR = ROOT / "public" / "data"

INDEX_CSV = OUTPUT_DIR / "track_conditions_file_index_v1.csv"
EVIDENCE_CSV = OUTPUT_DIR / "track_conditions_field_evidence_v1.csv"
URLS_CSV = OUTPUT_DIR / "track_conditions_source_urls_v1.csv"
TRACK_COVERAGE_CSV = OUTPUT_DIR / "track_conditions_track_coverage_v1.csv"

AUDIT_TXT = PUBLIC_DIR / "edgeiq_track_conditions_source_audit_v1.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_track_conditions_source_audit_v1.json"

SCAN_ROOTS = [
    ROOT / "public" / "data",
    ROOT / "data",
    ROOT / "scripts",
    ROOT / "docs",
    ROOT / "src",
]

EXCLUDED_PARTS = {
    "node_modules",
    ".git",
    "dist",
    "checkpoints",
    "visual_audits",
    ".vite",
}

ALLOWED_SUFFIXES = {
    ".py", ".ps1", ".ts", ".tsx", ".js",
    ".json", ".csv", ".txt", ".md", ".html", ".htm",
}

MAX_FILE_BYTES = 1_500_000

TRACKS = [
    ("FLEMINGTON", "Flemington"),
    ("CAULFIELD", "Caulfield"),
    ("CAULFIELD_HEATH", "Caulfield Heath"),
    ("SANDOWN_HILLSIDE", "Sandown Hillside"),
    ("SANDOWN_LAKESIDE", "Sandown Lakeside"),
    ("MOONEE_VALLEY", "Moonee Valley"),
    ("MORNINGTON", "Mornington"),
    ("CRANBOURNE", "Cranbourne"),
    ("PAKENHAM", "Pakenham"),
    ("PAKENHAM_SYNTHETIC", "Pakenham Synthetic"),
    ("BALLARAT", "Ballarat"),
    ("BALLARAT_SYNTHETIC", "Ballarat Synthetic"),
    ("BENDIGO", "Bendigo"),
    ("BENALLA", "Benalla"),
    ("CAMPERDOWN", "Camperdown"),
    ("CASTERTON", "Casterton"),
    ("COLAC", "Colac"),
    ("DONALD", "Donald"),
    ("ECHUCA", "Echuca"),
    ("GEELONG", "Geelong"),
    ("HAMILTON", "Hamilton"),
    ("HORSHAM", "Horsham"),
    ("KILMORE", "Kilmore"),
    ("KYNETON", "Kyneton"),
    ("MANSFIELD", "Mansfield"),
    ("MOE", "Moe"),
    ("MURTOA", "Murtoa"),
    ("SALE", "Sale"),
    ("SEYMOUR", "Seymour"),
    ("ST_ARNAUD", "St Arnaud"),
    ("SWAN_HILL", "Swan Hill"),
    ("TERANG", "Terang"),
    ("WANGARATTA", "Wangaratta"),
    ("WARRACKNABEAL", "Warracknabeal"),
    ("WARRNAMBOOL", "Warrnambool"),
    ("WERRIBEE", "Werribee"),
    ("WODONGA", "Wodonga"),
    ("YARRA_VALLEY", "Yarra Valley"),
]

FIELD_PATTERNS = {
    "TRACK_CONDITION": re.compile(
        r"track.?condition|track.?rating|going.?report|\bsoft\s*[0-9]\b|\bheavy\s*[0-9]\b|\bgood\s*[0-9]\b",
        re.I,
    ),
    "RAIL_CURRENT": re.compile(
        r"rail.?position|current.?rail",
        re.I,
    ),
    "RAIL_PREVIOUS": re.compile(
        r"previous.?rail|last.?rail|prior.?rail",
        re.I,
    ),
    "IRRIGATION_24H": re.compile(
        r"irrigation.?24|24.?h(?:ours?)?.?irrigation",
        re.I,
    ),
    "IRRIGATION_7D": re.compile(
        r"irrigation.?7.?d|7.?day.?irrigation",
        re.I,
    ),
    "IRRIGATION_GENERAL": re.compile(
        r"\birrigation\b|\bwatered\b",
        re.I,
    ),
    "RAINFALL_24H": re.compile(
        r"rainfall.?24|24.?h(?:ours?)?.?rain|rain.?24.?h",
        re.I,
    ),
    "RAINFALL_7D": re.compile(
        r"rainfall.?7.?d|7.?day.?rain|rain.?7.?day",
        re.I,
    ),
    "PENETROMETER": re.compile(
        r"penetrometer|penetro",
        re.I,
    ),
    "GOING_STICK": re.compile(
        r"going.?stick|goingstick",
        re.I,
    ),
    "TRACK_MANAGER_COMMENT": re.compile(
        r"track.?manager|track.?comment|official.?comment",
        re.I,
    ),
    "UPDATED_TIME": re.compile(
        r"last.?updated|updated.?at|update.?time|inspection.?time",
        re.I,
    ),
    "MEETING_STATUS": re.compile(
        r"abandoned|postponed|meeting.?status|race.?status",
        re.I,
    ),
}

URL_PATTERN = re.compile(r"https?://[^\s\"'<>\\]+", re.I)

AUTHORITY_HINTS = (
    "racingaustralia",
    "racingvictoria",
    "racing.com",
    "country.racing",
    "vrc.com.au",
    "mrc.racing.com",
    "southsideracing",
    "turftrax",
    "tab.com.au",
)


def excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def authority_from_url(url: str) -> str:
    lowered = url.lower()

    if "racingaustralia" in lowered:
        return "RACING_AUSTRALIA"
    if "racingvictoria" in lowered:
        return "RACING_VICTORIA"
    if "mrc.racing.com" in lowered:
        return "MRC"
    if "racing.com" in lowered:
        return "RACING_COM"
    if "vrc.com.au" in lowered:
        return "VRC"
    if "southsideracing" in lowered:
        return "SOUTHSIDE_RACING"
    if "turftrax" in lowered:
        return "TURFTRAX"
    if "tab.com.au" in lowered:
        return "TAB"

    return "UNKNOWN"


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


candidate_files: list[Path] = []

for scan_root in SCAN_ROOTS:
    if not scan_root.exists():
        continue

    for path in scan_root.rglob("*"):
        if not path.is_file():
            continue
        if excluded(path):
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue

        lowered_path = str(path).lower()

        if any(
            token in lowered_path
            for token in (
                "track",
                "rail",
                "condition",
                "going",
                "irrigation",
                "rainfall",
                "meeting",
                "racing-australia",
                "turftrax",
            )
        ):
            candidate_files.append(path)

candidate_files = sorted(set(candidate_files))

file_index_rows: list[dict[str, Any]] = []
evidence_rows: list[dict[str, Any]] = []
url_rows: list[dict[str, Any]] = []

track_lookup: dict[str, dict[str, Any]] = {
    track_id: {
        "track_id": track_id,
        "track_name": track_name,
        "matching_files": [],
        "categories": set(),
    }
    for track_id, track_name in TRACKS
}

for index, path in enumerate(candidate_files, start=1):
    text = safe_read(path)
    lowered_text = text.lower()
    relative = str(path.relative_to(ROOT))

    categories_found: set[str] = set()

    for category, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)

        if not match:
            continue

        categories_found.add(category)

        start = max(0, match.start() - 180)
        end = min(len(text), match.end() + 300)

        context = (
            text[start:end]
            .replace("\r", " ")
            .replace("\n", " ")
            .strip()
        )

        evidence_rows.append(
            {
                "repository_file": relative,
                "field_category": category,
                "matched_text": match.group(0),
                "context": context[:700],
                "line_estimate": text[:match.start()].count("\n") + 1,
                "source_status": "DISCOVERED_UNVERIFIED",
                "canonical_field": "",
                "authority": "",
                "track_name": "",
                "meeting_date": "",
                "notes": "",
            }
        )

    tracks_found: list[str] = []

    for track_id, track_name in TRACKS:
        if track_name.lower() not in lowered_text:
            continue

        tracks_found.append(track_id)
        track_lookup[track_id]["matching_files"].append(relative)
        track_lookup[track_id]["categories"].update(categories_found)

    urls_seen: set[str] = set()

    for raw_url in URL_PATTERN.findall(text):
        url = raw_url.rstrip(".,);]}")

        if not any(hint in url.lower() for hint in AUTHORITY_HINTS):
            continue

        if url in urls_seen:
            continue

        urls_seen.add(url)

        url_rows.append(
            {
                "repository_file": relative,
                "url": url,
                "authority": authority_from_url(url),
                "possible_role": "TRACK_CONDITIONS_OR_MEETING_SOURCE",
                "verification_status": "UNVERIFIED",
                "track_name": "",
                "endpoint_type": "",
                "notes": "",
            }
        )

    file_index_rows.append(
        {
            "repository_file": relative,
            "extension": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "field_categories": "|".join(sorted(categories_found)),
            "track_ids_found": "|".join(tracks_found),
            "relevant_url_count": len(urls_seen),
            "candidate_status": (
                "HIGH_VALUE"
                if len(categories_found) >= 4
                else "REVIEW"
            ),
            "notes": "",
        }
    )

    if index % 100 == 0 or index == len(candidate_files):
        print(f"indexed={index}/{len(candidate_files)}")

track_rows: list[dict[str, Any]] = []

for track_id, data in track_lookup.items():
    categories = data["categories"]
    matching_files = data["matching_files"]

    track_rows.append(
        {
            "track_id": track_id,
            "track_name": data["track_name"],
            "matching_file_count": len(matching_files),
            "field_categories_found": "|".join(sorted(categories)),
            "track_condition_evidence": (
                "YES" if "TRACK_CONDITION" in categories else "NO"
            ),
            "rail_evidence": (
                "YES" if "RAIL_CURRENT" in categories else "NO"
            ),
            "irrigation_evidence": (
                "YES"
                if any(value.startswith("IRRIGATION") for value in categories)
                else "NO"
            ),
            "rainfall_evidence": (
                "YES"
                if any(value.startswith("RAINFALL") for value in categories)
                else "NO"
            ),
            "update_time_evidence": (
                "YES" if "UPDATED_TIME" in categories else "NO"
            ),
            "matching_files": "|".join(matching_files[:20]),
            "status": (
                "EVIDENCE_FOUND"
                if matching_files
                else "SOURCE_DISCOVERY_REQUIRED"
            ),
            "notes": "",
        }
    )

write_csv(
    INDEX_CSV,
    [
        "repository_file",
        "extension",
        "bytes",
        "field_categories",
        "track_ids_found",
        "relevant_url_count",
        "candidate_status",
        "notes",
    ],
    file_index_rows,
)

write_csv(
    EVIDENCE_CSV,
    [
        "repository_file",
        "field_category",
        "matched_text",
        "context",
        "line_estimate",
        "source_status",
        "canonical_field",
        "authority",
        "track_name",
        "meeting_date",
        "notes",
    ],
    evidence_rows,
)

write_csv(
    URLS_CSV,
    [
        "repository_file",
        "url",
        "authority",
        "possible_role",
        "verification_status",
        "track_name",
        "endpoint_type",
        "notes",
    ],
    url_rows,
)

write_csv(
    TRACK_COVERAGE_CSV,
    [
        "track_id",
        "track_name",
        "matching_file_count",
        "field_categories_found",
        "track_condition_evidence",
        "rail_evidence",
        "irrigation_evidence",
        "rainfall_evidence",
        "update_time_evidence",
        "matching_files",
        "status",
        "notes",
    ],
    track_rows,
)

category_counts = Counter(
    row["field_category"]
    for row in evidence_rows
)

authority_counts = Counter(
    row["authority"]
    for row in url_rows
)

audit = {
    "status": "EDGEIQ_TRACK_CONDITIONS_SOURCE_AUDIT_V1_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "candidate_files": len(file_index_rows),
    "field_evidence_rows": len(evidence_rows),
    "source_urls": len(url_rows),
    "tracks_checked": len(track_rows),
    "tracks_with_evidence": sum(
        row["status"] == "EVIDENCE_FOUND"
        for row in track_rows
    ),
    "field_category_counts": dict(category_counts),
    "authority_counts": dict(authority_counts),
    "notes": [
        "Indexed read-only audit.",
        "Each candidate file was read once.",
        "No UI, builder, service or governed feed modified.",
        "No track-condition values fabricated.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

AUDIT_TXT.write_text(
    "\n".join(
        [
            audit["status"],
            f"generated_at={audit['generated_at']}",
            f"candidate_files={audit['candidate_files']}",
            f"field_evidence_rows={audit['field_evidence_rows']}",
            f"source_urls={audit['source_urls']}",
            f"tracks_checked={audit['tracks_checked']}",
            f"tracks_with_evidence={audit['tracks_with_evidence']}",
            "",
            "Each candidate file was read once.",
            "No UI, builder, service or governed feed modified.",
            "No track-condition values fabricated.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"candidate_files={audit['candidate_files']}")
print(f"field_evidence_rows={audit['field_evidence_rows']}")
print(f"source_urls={audit['source_urls']}")
print(f"tracks_with_evidence={audit['tracks_with_evidence']}")
