from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCE_REGISTRY = (
    ROOT / "data" / "weather"
    / "bom_track_location_registry_v1_1.csv"
)

OUTPUT_DIR = (
    ROOT / "data" / "weather"
    / "bom-towns-registry"
)

RAW_JSON = OUTPUT_DIR / "bom_towns_cities_raw_v1.json"
FLAT_CSV = OUTPUT_DIR / "bom_towns_cities_flat_v1.csv"
SCHEMA_JSON = OUTPUT_DIR / "bom_towns_cities_schema_v1.json"

MATCHES_CSV = (
    ROOT / "data" / "weather"
    / "bom_track_location_matches_v1.csv"
)

RESOLVED_CSV = (
    ROOT / "data" / "weather"
    / "bom_track_location_registry_v1_2.csv"
)

REVIEW_CSV = (
    OUTPUT_DIR / "bom_track_location_manual_review_v1.csv"
)

AUDIT_TXT = (
    ROOT / "public" / "data"
    / "edgeiq_bom_towns_registry_v1_audit.txt"
)

AUDIT_JSON = (
    ROOT / "public" / "data"
    / "edgeiq_bom_towns_registry_v1_audit.json"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_TXT.parent.mkdir(parents=True, exist_ok=True)

SOURCE_URLS = [
    "https://www.bom.gov.au/config/towns_places/towns-cities.json",
    "https://www.bom.gov.au/themes/custom/bom_theme/bom-react/dist/data/drupal/towns-cities.json",
]

ALIASES: dict[str, list[str]] = {
    "FLEMINGTON": ["Flemington"],
    "CAULFIELD": ["Caulfield"],
    "SANDOWN": ["Springvale", "Noble Park"],
    "MORNINGTON": ["Mornington"],
    "MOONEE_VALLEY": ["Moonee Ponds"],
    "CRANBOURNE": ["Cranbourne"],
    "PAKENHAM": ["Pakenham"],
    "BALLARAT": ["Ballarat"],
    "BENDIGO": ["Bendigo"],
    "BENALLA": ["Benalla"],
    "CAMPERDOWN": ["Camperdown"],
    "CASTERTON": ["Casterton"],
    "COLAC": ["Colac"],
    "DONALD": ["Donald"],
    "ECHUCA": ["Echuca"],
    "GEELONG": ["Geelong"],
    "HAMILTON": ["Hamilton"],
    "HORSHAM": ["Horsham"],
    "KILMORE": ["Kilmore"],
    "KYNETON": ["Kyneton"],
    "MANSFIELD": ["Mansfield"],
    "MOE": ["Moe"],
    "MURTOA": ["Murtoa"],
    "SALE": ["Sale"],
    "SEYMOUR": ["Seymour"],
    "ST_ARNAUD": ["St Arnaud", "Saint Arnaud"],
    "SWAN_HILL": ["Swan Hill"],
    "TERANG": ["Terang"],
    "WANGARATTA": ["Wangaratta"],
    "WARRACKNABEAL": ["Warracknabeal"],
    "WARRNAMBOOL": ["Warrnambool"],
    "WERRIBEE": ["Werribee"],
    "WODONGA": ["Wodonga"],
    "YARRA_VALLEY": ["Yarra Glen"],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return [
            {
                str(key): str(value or "")
                for key, value in row.items()
            }
            for row in csv.DictReader(handle)
        ]


def write_csv(
    path: Path,
    fields: list[str],
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def normalise(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_json() -> tuple[str, Any, dict[str, str]]:
    last_error = ""

    for url in SOURCE_URLS:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "EDGEiQ-Weather-Registry/1.2 "
                    "(single public BOM configuration fetch)"
                ),
                "Accept": "application/json,text/plain,*/*",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=30,
            ) as response:
                raw = response.read(8_000_000)
                text = raw.decode(
                    "utf-8",
                    errors="strict",
                )
                payload = json.loads(text)

                headers = {
                    str(key): str(value)
                    for key, value
                    in response.headers.items()
                }

                return (
                    str(response.geturl()),
                    payload,
                    headers,
                )

        except Exception as exc:
            last_error = (
                f"{url}: {type(exc).__name__}: {exc}"
            )

    raise RuntimeError(
        "No public BOM towns registry could be loaded. "
        + last_error
    )


def discover_schema(
    value: Any,
    path: str = "$",
    rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if rows is None:
        rows = []

    if isinstance(value, dict):
        rows.append(
            {
                "path": path,
                "type": "object",
                "size": len(value),
                "keys": "|".join(
                    sorted(str(key) for key in value.keys())
                ),
            }
        )

        for key, child in value.items():
            discover_schema(
                child,
                f"{path}.{key}",
                rows,
            )

    elif isinstance(value, list):
        rows.append(
            {
                "path": path,
                "type": "array",
                "size": len(value),
                "keys": "",
            }
        )

        for index, child in enumerate(value[:30]):
            discover_schema(
                child,
                f"{path}[{index}]",
                rows,
            )

    else:
        rows.append(
            {
                "path": path,
                "type": type(value).__name__,
                "size": "",
                "keys": "",
            }
        )

    return rows


def walk_records(
    value: Any,
    path: str = "$",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if isinstance(value, dict):
        lowered = {
            str(key).lower(): child
            for key, child in value.items()
        }

        name_keys = (
            "name",
            "title",
            "location_name",
            "locality",
            "town",
            "place",
            "label",
        )

        url_keys = (
            "url",
            "path",
            "href",
            "canonical",
            "location_url",
        )

        state_keys = (
            "state",
            "state_code",
            "state_name",
        )

        lat_keys = (
            "lat",
            "latitude",
        )

        lon_keys = (
            "lon",
            "lng",
            "longitude",
        )

        name = next(
            (
                lowered[key]
                for key in name_keys
                if key in lowered
                and isinstance(
                    lowered[key],
                    (str, int, float),
                )
            ),
            "",
        )

        url = next(
            (
                lowered[key]
                for key in url_keys
                if key in lowered
                and isinstance(
                    lowered[key],
                    (str, int, float),
                )
            ),
            "",
        )

        state = next(
            (
                lowered[key]
                for key in state_keys
                if key in lowered
                and isinstance(
                    lowered[key],
                    (str, int, float),
                )
            ),
            "",
        )

        latitude = next(
            (
                lowered[key]
                for key in lat_keys
                if key in lowered
                and isinstance(
                    lowered[key],
                    (str, int, float),
                )
            ),
            "",
        )

        longitude = next(
            (
                lowered[key]
                for key in lon_keys
                if key in lowered
                and isinstance(
                    lowered[key],
                    (str, int, float),
                )
            ),
            "",
        )

        serialised = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if name or "/location/" in serialised:
            records.append(
                {
                    "source_path": path,
                    "name": str(name),
                    "state": str(state),
                    "url_or_path": str(url),
                    "latitude": str(latitude),
                    "longitude": str(longitude),
                    "raw_json": serialised,
                }
            )

        for key, child in value.items():
            records.extend(
                walk_records(
                    child,
                    f"{path}.{key}",
                )
            )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            records.extend(
                walk_records(
                    child,
                    f"{path}[{index}]",
                )
            )

    return records


def extract_canonical_path(record: dict[str, Any]) -> str:
    direct = str(record.get("url_or_path", ""))

    if "/location/" in direct:
        return direct

    raw_json = str(record.get("raw_json", ""))

    match = re.search(
        r"""(?:https?://www\.bom\.gov\.au)?
        (/location/australia/victoria/
        [a-z0-9\-]+/[a-z0-9_\-]+)""",
        raw_json,
        re.IGNORECASE | re.VERBOSE,
    )

    if match:
        return match.group(1)

    return ""


def absolute_bom_url(path_or_url: str) -> str:
    value = str(path_or_url or "").strip()

    if not value:
        return ""

    if value.startswith("http://"):
        return "https://" + value[len("http://"):]

    if value.startswith("https://"):
        return value

    if value.startswith("/"):
        return "https://www.bom.gov.au" + value

    return (
        "https://www.bom.gov.au/"
        + value.lstrip("/")
    )


source_url, payload, headers = fetch_json()

RAW_JSON.write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

schema_rows = discover_schema(payload)

SCHEMA_JSON.write_text(
    json.dumps(
        {
            "source_url": source_url,
            "schema_rows": schema_rows,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

raw_records = walk_records(payload)

flat_rows: list[dict[str, Any]] = []
seen: set[tuple[str, str, str]] = set()

for record in raw_records:
    canonical_path = extract_canonical_path(record)
    canonical_url = absolute_bom_url(canonical_path)

    row = {
        **record,
        "canonical_path": canonical_path,
        "canonical_url": canonical_url,
        "normalised_name": normalise(record["name"]),
    }

    key = (
        row["normalised_name"],
        row["canonical_url"],
        row["source_path"],
    )

    if key in seen:
        continue

    seen.add(key)
    flat_rows.append(row)

flat_fields = [
    "source_path",
    "name",
    "normalised_name",
    "state",
    "canonical_path",
    "canonical_url",
    "url_or_path",
    "latitude",
    "longitude",
    "raw_json",
]

write_csv(
    FLAT_CSV,
    flat_fields,
    flat_rows,
)

source_registry = read_csv(SOURCE_REGISTRY)

match_rows: list[dict[str, Any]] = []
resolved_rows: list[dict[str, Any]] = []
review_rows: list[dict[str, Any]] = []

for source in source_registry:
    location_id = source["physical_location_id"]

    if (
        source.get("verification_status")
        == "VERIFIED_LOCATION"
        and "/location/australia/victoria/"
        in source.get("final_bom_url", "")
    ):
        updated = dict(source)
        updated.update(
            {
                "registry_resolution_status": (
                    "PRESERVED_VERIFIED"
                ),
                "registry_match_name": "",
                "registry_match_url": (
                    source["final_bom_url"]
                ),
                "registry_match_score": "999",
                "registry_source_url": source_url,
                "registry_verified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
        )
        resolved_rows.append(updated)
        continue

    aliases = ALIASES.get(
        location_id,
        [source.get("bom_search_name", "")],
    )

    alias_norms = {
        normalise(alias)
        for alias in aliases
        if normalise(alias)
    }

    candidates: list[dict[str, Any]] = []

    for row in flat_rows:
        row_name = row["normalised_name"]

        score = 0
        reasons: list[str] = []

        if row_name in alias_norms:
            score += 100
            reasons.append("EXACT_ALIAS")

        for alias_norm in alias_norms:
            if (
                alias_norm
                and alias_norm in row_name
                and row_name != alias_norm
            ):
                score += 50
                reasons.append(
                    "ALIAS_IN_NAME"
                )
                break

            if (
                row_name
                and row_name in alias_norm
                and row_name != alias_norm
            ):
                score += 35
                reasons.append(
                    "NAME_IN_ALIAS"
                )
                break

        state_norm = normalise(row["state"])

        if state_norm in {
            "vic",
            "victoria",
        }:
            score += 20
            reasons.append("VICTORIA")

        if row["canonical_url"]:
            score += 20
            reasons.append("CANONICAL_URL")

        if score <= 0:
            continue

        candidates.append(
            {
                "physical_location_id": location_id,
                "track_names": source["track_names"],
                "aliases": "|".join(aliases),
                "candidate_name": row["name"],
                "candidate_state": row["state"],
                "candidate_url": row["canonical_url"],
                "candidate_latitude": row["latitude"],
                "candidate_longitude": row["longitude"],
                "candidate_score": score,
                "candidate_reasons": "|".join(
                    sorted(set(reasons))
                ),
                "source_path": row["source_path"],
                "selected": "NO",
                "notes": "",
            }
        )

    candidates.sort(
        key=lambda item: (
            int(item["candidate_score"]),
            bool(item["candidate_url"]),
            item["candidate_name"],
        ),
        reverse=True,
    )

    match_rows.extend(candidates)

    selected = None

    if candidates:
        top = candidates[0]
        second_score = (
            int(candidates[1]["candidate_score"])
            if len(candidates) > 1
            else -999
        )

        top_score = int(top["candidate_score"])
        margin = top_score - second_score

        if (
            top_score >= 120
            and margin >= 20
            and top["candidate_url"]
        ):
            selected = top

        elif (
            len(candidates) == 1
            and top_score >= 100
            and top["candidate_url"]
        ):
            selected = top

    updated = dict(source)

    if selected:
        selected["selected"] = "YES"

        updated.update(
            {
                "http_status": "200",
                "final_bom_url": (
                    selected["candidate_url"]
                ),
                "page_title": (
                    selected["candidate_name"]
                    + ", Victoria"
                ),
                "location_name_confirmed": "YES",
                "verification_status": (
                    "VERIFIED_LOCATION"
                ),
                "resolution_status": (
                    "PUBLIC_TOWNS_REGISTRY_MATCH"
                ),
                "registry_resolution_status": (
                    "AUTO_RESOLVED"
                ),
                "registry_match_name": (
                    selected["candidate_name"]
                ),
                "registry_match_url": (
                    selected["candidate_url"]
                ),
                "registry_match_score": str(
                    selected["candidate_score"]
                ),
                "registry_latitude": (
                    selected["candidate_latitude"]
                ),
                "registry_longitude": (
                    selected["candidate_longitude"]
                ),
                "registry_source_url": source_url,
                "registry_verified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "verification_method": (
                    "Exact or high-confidence match "
                    "against BOM public towns-cities registry"
                ),
                "error": "",
            }
        )
    else:
        updated.update(
            {
                "verification_status": (
                    "MANUAL_REGISTRY_REVIEW"
                    if candidates
                    else "UNRESOLVED"
                ),
                "registry_resolution_status": (
                    "MANUAL_REVIEW"
                    if candidates
                    else "NO_MATCH"
                ),
                "registry_match_name": "",
                "registry_match_url": "",
                "registry_match_score": "",
                "registry_source_url": source_url,
                "registry_verified_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
        )
        review_rows.append(updated)

    resolved_rows.append(updated)

match_fields = [
    "physical_location_id",
    "track_names",
    "aliases",
    "candidate_name",
    "candidate_state",
    "candidate_url",
    "candidate_latitude",
    "candidate_longitude",
    "candidate_score",
    "candidate_reasons",
    "source_path",
    "selected",
    "notes",
]

write_csv(
    MATCHES_CSV,
    match_fields,
    match_rows,
)

resolved_fields = sorted(
    {
        key
        for row in resolved_rows
        for key in row.keys()
    }
)

write_csv(
    RESOLVED_CSV,
    resolved_fields,
    resolved_rows,
)

write_csv(
    REVIEW_CSV,
    resolved_fields,
    review_rows,
)

verified = sum(
    row.get("verification_status")
    == "VERIFIED_LOCATION"
    for row in resolved_rows
)

preserved = sum(
    row.get("registry_resolution_status")
    == "PRESERVED_VERIFIED"
    for row in resolved_rows
)

auto_resolved = sum(
    row.get("registry_resolution_status")
    == "AUTO_RESOLVED"
    for row in resolved_rows
)

manual_review = sum(
    row.get("registry_resolution_status")
    == "MANUAL_REVIEW"
    for row in resolved_rows
)

unresolved = sum(
    row.get("registry_resolution_status")
    == "NO_MATCH"
    for row in resolved_rows
)

audit = {
    "status": (
        "EDGEIQ_BOM_TOWNS_REGISTRY_V1_AUDIT_PASS"
    ),
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "source_url": source_url,
    "http_header_count": len(headers),
    "flat_registry_rows": len(flat_rows),
    "track_locations": len(resolved_rows),
    "verified_locations": verified,
    "preserved_verified": preserved,
    "auto_resolved": auto_resolved,
    "manual_review": manual_review,
    "unresolved": unresolved,
    "candidate_matches": len(match_rows),
    "raw_json": str(RAW_JSON.relative_to(ROOT)),
    "flat_csv": str(FLAT_CSV.relative_to(ROOT)),
    "resolved_registry": str(
        RESOLVED_CSV.relative_to(ROOT)
    ),
    "review_csv": str(
        REVIEW_CSV.relative_to(ROOT)
    ),
    "notes": [
        "One public BOM town registry request was made.",
        "No private API key was requested or used.",
        "Existing verified locations were preserved.",
        "Ambiguous matches remain manual review.",
        "No observation station was assigned.",
    ],
}

AUDIT_JSON.write_text(
    json.dumps(
        audit,
        indent=2,
    ),
    encoding="utf-8",
)

AUDIT_TXT.write_text(
    "\n".join(
        [
            audit["status"],
            f"generated_at={audit['generated_at']}",
            f"source_url={audit['source_url']}",
            (
                "flat_registry_rows="
                f"{audit['flat_registry_rows']}"
            ),
            (
                "track_locations="
                f"{audit['track_locations']}"
            ),
            (
                "verified_locations="
                f"{audit['verified_locations']}"
            ),
            (
                "preserved_verified="
                f"{audit['preserved_verified']}"
            ),
            (
                "auto_resolved="
                f"{audit['auto_resolved']}"
            ),
            (
                "manual_review="
                f"{audit['manual_review']}"
            ),
            f"unresolved={audit['unresolved']}",
            (
                "candidate_matches="
                f"{audit['candidate_matches']}"
            ),
            "",
            "No API key was requested or used.",
            "No observation station was assigned.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"source_url={source_url}")
print(f"flat_registry_rows={len(flat_rows)}")
print(f"verified_locations={verified}")
print(f"preserved_verified={preserved}")
print(f"auto_resolved={auto_resolved}")
print(f"manual_review={manual_review}")
print(f"unresolved={unresolved}")
print(f"candidate_matches={len(match_rows)}")
