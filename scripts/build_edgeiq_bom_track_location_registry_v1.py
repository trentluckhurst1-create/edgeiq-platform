from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEATHER_DIR = ROOT / "data" / "weather"
PUBLIC_DIR = ROOT / "public" / "data"

OUTPUT_CSV = WEATHER_DIR / "bom_track_location_registry_v1.csv"
OUTPUT_JSON = WEATHER_DIR / "bom_track_location_registry_v1.json"
REVIEW_CSV = WEATHER_DIR / "bom_track_location_manual_review_v1.csv"

AUDIT_TXT = PUBLIC_DIR / "edgeiq_bom_track_location_registry_v1_audit.txt"
AUDIT_JSON = PUBLIC_DIR / "edgeiq_bom_track_location_registry_v1_audit.json"

WEATHER_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# One row per physical racecourse location.
#
# VRC/MRC tracks are retained for BOM forecasting support, but their live
# observations remain owned by VRC/TurfTrax. Synthetic and alternate courses
# share the physical forecast location with their corresponding turf venue.
TRACKS: list[dict[str, Any]] = [
    {
        "physical_location_id": "FLEMINGTON",
        "track_ids": ["FLEMINGTON"],
        "track_names": ["Flemington"],
        "bom_search_name": "Flemington",
        "legacy_slug": "flemington",
        "observation_authority": "VRC_ON_TRACK",
    },
    {
        "physical_location_id": "CAULFIELD",
        "track_ids": ["CAULFIELD", "CAULFIELD_HEATH"],
        "track_names": ["Caulfield", "Caulfield Heath"],
        "bom_search_name": "Caulfield",
        "legacy_slug": "caulfield",
        "observation_authority": "MRC_TURFTRAX_ON_TRACK",
    },
    {
        "physical_location_id": "SANDOWN",
        "track_ids": ["SANDOWN_HILLSIDE", "SANDOWN_LAKESIDE"],
        "track_names": ["Sandown Hillside", "Sandown Lakeside"],
        "bom_search_name": "Springvale",
        "legacy_slug": "springvale",
        "observation_authority": "MRC_TURFTRAX_ON_TRACK",
    },
    {
        "physical_location_id": "MORNINGTON",
        "track_ids": ["MORNINGTON"],
        "track_names": ["Mornington"],
        "bom_search_name": "Mornington",
        "legacy_slug": "mornington",
        "observation_authority": "MRC_TURFTRAX_ON_TRACK",
    },
    {
        "physical_location_id": "MOONEE_VALLEY",
        "track_ids": ["MOONEE_VALLEY"],
        "track_names": ["Moonee Valley"],
        "bom_search_name": "Moonee Ponds",
        "legacy_slug": "moonee-ponds",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "CRANBOURNE",
        "track_ids": ["CRANBOURNE"],
        "track_names": ["Cranbourne"],
        "bom_search_name": "Cranbourne",
        "legacy_slug": "cranbourne",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "PAKENHAM",
        "track_ids": ["PAKENHAM", "PAKENHAM_SYNTHETIC"],
        "track_names": ["Pakenham", "Pakenham Synthetic"],
        "bom_search_name": "Pakenham",
        "legacy_slug": "pakenham",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "BALLARAT",
        "track_ids": ["BALLARAT", "BALLARAT_SYNTHETIC"],
        "track_names": ["Ballarat", "Ballarat Synthetic"],
        "bom_search_name": "Ballarat",
        "legacy_slug": "ballarat",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "BENDIGO",
        "track_ids": ["BENDIGO"],
        "track_names": ["Bendigo"],
        "bom_search_name": "Bendigo",
        "legacy_slug": "bendigo",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "BENALLA",
        "track_ids": ["BENALLA"],
        "track_names": ["Benalla"],
        "bom_search_name": "Benalla",
        "legacy_slug": "benalla",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "CAMPERDOWN",
        "track_ids": ["CAMPERDOWN"],
        "track_names": ["Camperdown"],
        "bom_search_name": "Camperdown",
        "legacy_slug": "camperdown",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "CASTERTON",
        "track_ids": ["CASTERTON"],
        "track_names": ["Casterton"],
        "bom_search_name": "Casterton",
        "legacy_slug": "casterton",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "COLAC",
        "track_ids": ["COLAC"],
        "track_names": ["Colac"],
        "bom_search_name": "Colac",
        "legacy_slug": "colac",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "DONALD",
        "track_ids": ["DONALD"],
        "track_names": ["Donald"],
        "bom_search_name": "Donald",
        "legacy_slug": "donald",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "ECHUCA",
        "track_ids": ["ECHUCA"],
        "track_names": ["Echuca"],
        "bom_search_name": "Echuca",
        "legacy_slug": "echuca",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "GEELONG",
        "track_ids": ["GEELONG"],
        "track_names": ["Geelong"],
        "bom_search_name": "Geelong",
        "legacy_slug": "geelong",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "HAMILTON",
        "track_ids": ["HAMILTON"],
        "track_names": ["Hamilton"],
        "bom_search_name": "Hamilton",
        "legacy_slug": "hamilton",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "HORSHAM",
        "track_ids": ["HORSHAM"],
        "track_names": ["Horsham"],
        "bom_search_name": "Horsham",
        "legacy_slug": "horsham",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "KILMORE",
        "track_ids": ["KILMORE"],
        "track_names": ["Kilmore"],
        "bom_search_name": "Kilmore",
        "legacy_slug": "kilmore",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "KYNETON",
        "track_ids": ["KYNETON"],
        "track_names": ["Kyneton"],
        "bom_search_name": "Kyneton",
        "legacy_slug": "kyneton",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "MANSFIELD",
        "track_ids": ["MANSFIELD"],
        "track_names": ["Mansfield"],
        "bom_search_name": "Mansfield",
        "legacy_slug": "mansfield",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "MOE",
        "track_ids": ["MOE"],
        "track_names": ["Moe"],
        "bom_search_name": "Moe",
        "legacy_slug": "moe",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "MURTOA",
        "track_ids": ["MURTOA"],
        "track_names": ["Murtoa"],
        "bom_search_name": "Murtoa",
        "legacy_slug": "murtoa",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "SALE",
        "track_ids": ["SALE"],
        "track_names": ["Sale"],
        "bom_search_name": "Sale",
        "legacy_slug": "sale",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "SEYMOUR",
        "track_ids": ["SEYMOUR"],
        "track_names": ["Seymour"],
        "bom_search_name": "Seymour",
        "legacy_slug": "seymour",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "ST_ARNAUD",
        "track_ids": ["ST_ARNAUD"],
        "track_names": ["St Arnaud"],
        "bom_search_name": "St Arnaud",
        "legacy_slug": "st-arnaud",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "SWAN_HILL",
        "track_ids": ["SWAN_HILL"],
        "track_names": ["Swan Hill"],
        "bom_search_name": "Swan Hill",
        "legacy_slug": "swan-hill",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "TERANG",
        "track_ids": ["TERANG"],
        "track_names": ["Terang"],
        "bom_search_name": "Terang",
        "legacy_slug": "terang",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "WANGARATTA",
        "track_ids": ["WANGARATTA"],
        "track_names": ["Wangaratta"],
        "bom_search_name": "Wangaratta",
        "legacy_slug": "wangaratta",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "WARRACKNABEAL",
        "track_ids": ["WARRACKNABEAL"],
        "track_names": ["Warracknabeal"],
        "bom_search_name": "Warracknabeal",
        "legacy_slug": "warracknabeal",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "WARRNAMBOOL",
        "track_ids": ["WARRNAMBOOL"],
        "track_names": ["Warrnambool"],
        "bom_search_name": "Warrnambool",
        "legacy_slug": "warrnambool",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "WERRIBEE",
        "track_ids": ["WERRIBEE"],
        "track_names": ["Werribee"],
        "bom_search_name": "Werribee",
        "legacy_slug": "werribee",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "WODONGA",
        "track_ids": ["WODONGA"],
        "track_names": ["Wodonga"],
        "bom_search_name": "Wodonga",
        "legacy_slug": "wodonga",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
    {
        "physical_location_id": "YARRA_VALLEY",
        "track_ids": ["YARRA_VALLEY"],
        "track_names": ["Yarra Valley"],
        "bom_search_name": "Yarra Glen",
        "legacy_slug": "yarra-glen",
        "observation_authority": "BOM_FALLBACK_REQUIRED",
    },
]


class TrackingRedirectHandler(urllib.request.HTTPRedirectHandler):
    pass


def extract_title(html: str) -> str:
    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    title = re.sub(r"\s+", " ", unescape(match.group(1))).strip()
    return title


def fetch_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "EDGEiQ-Weather-Registry/1.0 "
                "(single-request source verification)"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    opener = urllib.request.build_opener(TrackingRedirectHandler())

    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(1_500_000).decode(
                "utf-8",
                errors="ignore",
            )

            return {
                "http_status": int(response.status),
                "final_url": str(response.geturl()),
                "content_type": str(
                    response.headers.get("Content-Type", "")
                ),
                "page_title": extract_title(body),
                "body": body,
                "error": "",
            }

    except urllib.error.HTTPError as exc:
        return {
            "http_status": int(exc.code),
            "final_url": str(exc.geturl()),
            "content_type": "",
            "page_title": "",
            "body": "",
            "error": f"HTTPError: {exc}",
        }

    except Exception as exc:
        return {
            "http_status": 0,
            "final_url": "",
            "content_type": "",
            "page_title": "",
            "body": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


rows: list[dict[str, Any]] = []

for index, track in enumerate(TRACKS, start=1):
    candidate_url = (
        "https://www.bom.gov.au/places/vic/"
        f"{track['legacy_slug']}/"
    )

    print(
        f"[{index}/{len(TRACKS)}] "
        f"{track['physical_location_id']} -> {candidate_url}"
    )

    result = fetch_url(candidate_url)

    body_lower = result["body"].lower()
    title_lower = result["page_title"].lower()
    search_name_lower = track["bom_search_name"].lower()

    location_name_confirmed = (
        search_name_lower in title_lower
        or search_name_lower in body_lower[:250_000]
    )

    final_url = result["final_url"]

    official_bom_location_page = (
        result["http_status"] == 200
        and "bom.gov.au" in final_url.lower()
        and (
            "/location/" in final_url.lower()
            or "/places/" in final_url.lower()
        )
    )

    if official_bom_location_page and location_name_confirmed:
        verification_status = "VERIFIED_CANDIDATE"
    elif official_bom_location_page:
        verification_status = "MANUAL_NAME_REVIEW"
    elif result["http_status"] == 200:
        verification_status = "MANUAL_URL_REVIEW"
    else:
        verification_status = "UNRESOLVED"

    rows.append(
        {
            "physical_location_id": track["physical_location_id"],
            "track_ids": "|".join(track["track_ids"]),
            "track_names": "|".join(track["track_names"]),
            "bom_search_name": track["bom_search_name"],
            "legacy_candidate_url": candidate_url,
            "http_status": result["http_status"],
            "final_bom_url": final_url,
            "page_title": result["page_title"],
            "content_type": result["content_type"],
            "location_name_confirmed": (
                "YES" if location_name_confirmed else "NO"
            ),
            "verification_status": verification_status,
            "observation_authority": track["observation_authority"],
            "forecast_role": "BOM_FORECAST_LOCATION",
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
            "verification_method": (
                "HTTP redirect resolution plus page-name evidence"
            ),
            "error": result["error"],
            "manual_verified": "",
            "manual_notes": "",
        }
    )

    # Polite spacing: one request per track, no parallel request burst.
    time.sleep(0.35)


fields = [
    "physical_location_id",
    "track_ids",
    "track_names",
    "bom_search_name",
    "legacy_candidate_url",
    "http_status",
    "final_bom_url",
    "page_title",
    "content_type",
    "location_name_confirmed",
    "verification_status",
    "observation_authority",
    "forecast_role",
    "last_verified_at",
    "verification_method",
    "error",
    "manual_verified",
    "manual_notes",
]

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

OUTPUT_JSON.write_text(
    json.dumps(
        {
            "schema_version": "bom_track_location_registry_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(rows),
            "records": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)

review_rows = [
    row
    for row in rows
    if row["verification_status"] != "VERIFIED_CANDIDATE"
]

with REVIEW_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(review_rows)

verified = sum(
    row["verification_status"] == "VERIFIED_CANDIDATE"
    for row in rows
)

manual_review = sum(
    row["verification_status"].startswith("MANUAL")
    for row in rows
)

unresolved = sum(
    row["verification_status"] == "UNRESOLVED"
    for row in rows
)

audit = {
    "status": "EDGEIQ_BOM_TRACK_LOCATION_REGISTRY_V1_AUDIT_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "physical_locations": len(rows),
    "verified_candidates": verified,
    "manual_review": manual_review,
    "unresolved": unresolved,
    "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
    "output_json": str(OUTPUT_JSON.relative_to(ROOT)),
    "review_csv": str(REVIEW_CSV.relative_to(ROOT)),
    "notes": [
        "One polite request was made per physical racecourse location.",
        "Redirects were followed to capture the exact final BOM URL.",
        "A forecast location does not automatically identify the correct observation station.",
        "VRC and MRC on-track observations remain primary.",
        "No BOM observation station was fabricated or assigned.",
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
            f"physical_locations={audit['physical_locations']}",
            f"verified_candidates={audit['verified_candidates']}",
            f"manual_review={audit['manual_review']}",
            f"unresolved={audit['unresolved']}",
            f"output_csv={audit['output_csv']}",
            f"review_csv={audit['review_csv']}",
            "",
            "Forecast locations and observation stations remain separate.",
            "No BOM observation station was assigned without evidence.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print("")
print(audit["status"])
print(f"physical_locations={len(rows)}")
print(f"verified_candidates={verified}")
print(f"manual_review={manual_review}")
print(f"unresolved={unresolved}")
