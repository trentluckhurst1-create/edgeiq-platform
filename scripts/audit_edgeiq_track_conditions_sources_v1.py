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

FILES_CSV = OUTPUT_DIR / "track_conditions_source_files_v1.csv"
EVIDENCE_CSV = OUTPUT_DIR / "track_conditions_field_evidence_v1.csv"
URLS_CSV = OUTPUT_DIR / "track_conditions_source_urls_v1.csv"
TRACK_COVERAGE_CSV = OUTPUT_DIR / "track_conditions_track_coverage_v1.csv"

AUDIT_TXT = PUBLIC_DIR / "edgeiq_track_conditions_source_audit_v1.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_track_conditions_source_audit_v1.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "checkpoints",
    ".vite",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".json",
    ".csv",
    ".txt",
    ".md",
    ".html",
    ".htm",
}

FIELD_PATTERNS: dict[str, list[str]] = {
    "TRACK_CONDITION": [
        r"\btrack.?condition\b",
        r"\btrack.?rating\b",
        r"\bgoing.?report\b",
        r"\bgoing\b",
        r"\bsoft\s*[0-9]\b",
        r"\bheavy\s*[0-9]\b",
        r"\bgood\s*[0-9]\b",
    ],
    "RAIL_CURRENT": [
        r"\brail.?position\b",
        r"\bcurrent.?rail\b",
        r"\brail\b",
    ],
    "RAIL_PREVIOUS": [
        r"\bprevious.?rail\b",
        r"\blast.?rail\b",
        r"\bprior.?rail\b",
    ],
    "IRRIGATION_24H": [
        r"\birrigation.?24\b",
        r"\b24.?h(?:ours?)?.?irrigation\b",
    ],
    "IRRIGATION_7D": [
        r"\birrigation.?7.?d\b",
        r"\b7.?day.?irrigation\b",
    ],
    "IRRIGATION_GENERAL": [
        r"\birrigation\b",
        r"\bwatered\b",
    ],
    "RAINFALL_24H": [
        r"\brainfall.?24\b",
        r"\b24.?h(?:ours?)?.?rain\b",
        r"\brain.?24.?h\b",
    ],
    "RAINFALL_7D": [
        r"\brainfall.?7.?d\b",
        r"\b7.?day.?rain\b",
        r"\brain.?7.?day\b",
    ],
    "PENETROMETER": [
        r"\bpenetrometer\b",
        r"\bpenetro\b",
    ],
    "GOING_STICK": [
        r"\bgoing.?stick\b",
        r"\bgoingstick\b",
    ],
    "TRACK_MANAGER_COMMENT": [
        r"\btrack.?manager\b",
        r"\btrack.?comment\b",
        r"\bsteward.?comment\b",
        r"\bofficial.?comment\b",
    ],
    "UPDATED_TIME": [
        r"\blast.?updated\b",
        r"\bupdated.?at\b",
        r"\bupdate.?time\b",
        r"\binspection.?time\b",
    ],
    "MEETING_STATUS": [
        r"\babandoned\b",
        r"\bpostponed\b",
        r"\bmeeting.?status\b",
        r"\brace.?status\b",
    ],
}

URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>\\]+",
    re.IGNORECASE,
)

URL_AUTHORITY_HINTS = (
    "racingaustralia",
    "racing.com",
    "racingvictoria",
    "country.racing",
    "vrc.com.au",
    "mrc.racing.com",
    "southsideracing",
    "turftrax",
    "tab.com.au",
)

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


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > 8_000_000:
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
    if "racing.com" in lowered:
        return "RACING_COM"
    if "vrc.com.au" in lowered:
        return "VRC"
    if "mrc.racing.com" in lowered:
        return "MRC"
    if "southsideracing" in lowered:
        return "SOUTHSIDE_RACING"
    if "turftrax" in lowered:
        return "TURFTRAX"
    if "tab.com.au" in lowered:
        return "TAB"

    return "UNKNOWN"


candidate_files: list[Path] = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if is_excluded(path):
        continue
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        continue

    lower_name = path.name.lower()
    lower_parent = str(path.parent).lower()

    if any(
        token in lower_name or token in lower_parent
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
        continue

    text = safe_read(path)

    if text and any(
        re.search(pattern, text, re.IGNORECASE)
        for patterns in FIELD_PATTERNS.values()
        for pattern in patterns
    ):
        candidate_files.append(path)

candidate_files = sorted(set(candidate_files))

file_rows: list[dict[str, Any]] = []
evidence_rows: list[dict[str, Any]] = []
url_rows: list[dict[str, Any]] = []

for path in candidate_files:
    text = safe_read(path)
    relative = str(path.relative_to(ROOT))

    categories_found: set[str] = set()

    for category, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            matches = list(
                re.finditer(
                    pattern,
                    text,
                    re.IGNORECASE,
                )
            )

            if not matches:
                continue

            categories_found.add(category)

            for match in matches[:30]:
                start = max(0, match.start() - 180)
                end = min(len(text), match.end() + 300)

                context = (
                    text[start:end]
                    .replace("\r", " ")
                    .replace("\n", " ")
                    .strip()
                )

                if len(context) > 700:
                    context = context[:700] + "..."

                evidence_rows.append(
                    {
                        "repository_file": relative,
                        "field_category": category,
                        "matched_text": match.group(0),
                        "context": context,
                        "line_estimate": (
                            text[: match.start()].count("\n") + 1
                        ),
                        "source_status": "DISCOVERED_UNVERIFIED",
                        "canonical_field": "",
                        "authority": "",
                        "track_name": "",
                        "meeting_date": "",
                        "notes": "",
                    }
                )

    urls_seen: set[str] = set()

    for url_match in URL_PATTERN.findall(text):
        cleaned = url_match.rstrip(".,);]}")

        if not any(
            hint in cleaned.lower()
            for hint in URL_AUTHORITY_HINTS
        ):
            continue

        if cleaned in urls_seen:
            continue

        urls_seen.add(cleaned)

        url_rows.append(
            {
                "repository_file": relative,
                "url": cleaned,
                "authority": authority_from_url(cleaned),
                "possible_role": (
                    "TRACK_CONDITIONS_OR_MEETING_SOURCE"
                ),
                "verification_status": "UNVERIFIED",
                "track_name": "",
                "endpoint_type": "",
                "notes": "",
            }
        )

    file_rows.append(
        {
            "repository_file": relative,
            "extension": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "modified_at": path.stat().st_mtime,
            "field_categories": "|".join(
                sorted(categories_found)
            ),
            "category_count": len(categories_found),
            "relevant_url_count": len(urls_seen),
            "candidate_status": (
                "HIGH_VALUE"
                if len(categories_found) >= 4
                else
                "REVIEW"
            ),
            "notes": "",
        }
    )

track_rows: list[dict[str, Any]] = []

combined_text_by_file = {
    str(path.relative_to(ROOT)): safe_read(path)
    for path in candidate_files
}

for track_id, track_name in TRACKS:
    matching_files: list[str] = []
    categories: set[str] = set()

    for relative, text in combined_text_by_file.items():
        if track_name.lower() not in text.lower():
            continue

        matching_files.append(relative)

        for category, patterns in FIELD_PATTERNS.items():
            if any(
                re.search(pattern, text, re.IGNORECASE)
                for pattern in patterns
            ):
                categories.add(category)

    track_rows.append(
        {
            "track_id": track_id,
            "track_name": track_name,
            "matching_file_count": len(matching_files),
            "field_categories_found": "|".join(
                sorted(categories)
            ),
            "track_condition_evidence": (
                "YES"
                if "TRACK_CONDITION" in categories
                else "NO"
            ),
            "rail_evidence": (
                "YES"
                if "RAIL_CURRENT" in categories
                else "NO"
            ),
            "irrigation_evidence": (
                "YES"
                if any(
                    value.startswith("IRRIGATION")
                    for value in categories
                )
                else "NO"
            ),
            "rainfall_evidence": (
                "YES"
                if any(
                    value.startswith("RAINFALL")
                    for value in categories
                )
                else "NO"
            ),
            "update_time_evidence": (
                "YES"
                if "UPDATED_TIME" in categories
                else "NO"
            ),
            "matching_files": "|".join(
                matching_files[:20]
            ),
            "status": (
                "EVIDENCE_FOUND"
                if matching_files
                else "SOURCE_DISCOVERY_REQUIRED"
            ),
            "notes": "",
        }
    )


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


write_csv(
    FILES_CSV,
    [
        "repository_file",
        "extension",
        "bytes",
        "modified_at",
        "field_categories",
        "category_count",
        "relevant_url_count",
        "candidate_status",
        "notes",
    ],
    file_rows,
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
    "status": (
        "EDGEIQ_TRACK_CONDITIONS_SOURCE_AUDIT_V1_PASS"
    ),
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "candidate_files": len(file_rows),
    "field_evidence_rows": len(evidence_rows),
    "source_urls": len(url_rows),
    "tracks_checked": len(track_rows),
    "tracks_with_evidence": sum(
        row["status"] == "EVIDENCE_FOUND"
        for row in track_rows
    ),
    "field_category_counts": dict(category_counts),
    "authority_counts": dict(authority_counts),
    "outputs": {
        "files": str(FILES_CSV.relative_to(ROOT)),
        "evidence": str(EVIDENCE_CSV.relative_to(ROOT)),
        "urls": str(URLS_CSV.relative_to(ROOT)),
        "track_coverage": str(
            TRACK_COVERAGE_CSV.relative_to(ROOT)
        ),
    },
    "notes": [
        "This is a read-only source-discovery audit.",
        "No UI, builder, feed or service was modified.",
        "Evidence remains unverified until traced to an authoritative current source.",
        "No track-condition values were fabricated.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    f"candidate_files={audit['candidate_files']}",
    f"field_evidence_rows={audit['field_evidence_rows']}",
    f"source_urls={audit['source_urls']}",
    f"tracks_checked={audit['tracks_checked']}",
    f"tracks_with_evidence={audit['tracks_with_evidence']}",
    "",
    "FIELD CATEGORY COUNTS",
]

for category, count in sorted(category_counts.items()):
    lines.append(f"{category}={count}")

lines.extend(
    [
        "",
        "AUTHORITY COUNTS",
    ]
)

for authority, count in sorted(authority_counts.items()):
    lines.append(f"{authority}={count}")

lines.extend(
    [
        "",
        "No UI or live builder files were modified.",
        "No track-condition values were fabricated.",
    ]
)

AUDIT_TXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"candidate_files={audit['candidate_files']}")
print(f"field_evidence_rows={audit['field_evidence_rows']}")
print(f"source_urls={audit['source_urls']}")
print(f"tracks_with_evidence={audit['tracks_with_evidence']}")
