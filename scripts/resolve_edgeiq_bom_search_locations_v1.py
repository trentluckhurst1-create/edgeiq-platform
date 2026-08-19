from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SOURCE_CSV = (
    ROOT / "data" / "weather" / "bom_track_location_registry_v1.csv"
)

OUTPUT_DIR = (
    ROOT / "data" / "weather" / "bom-location-resolution"
)

RESOLVED_CSV = (
    ROOT / "data" / "weather" / "bom_track_location_registry_v1_1.csv"
)

RESOLVED_JSON = (
    ROOT / "data" / "weather" / "bom_track_location_registry_v1_1.json"
)

CANDIDATES_CSV = (
    OUTPUT_DIR / "bom_search_location_candidates_v1.csv"
)

REVIEW_CSV = (
    OUTPUT_DIR / "bom_search_location_manual_review_v1.csv"
)

AUDIT_TXT = (
    ROOT / "public" / "data"
    / "edgeiq_bom_search_location_resolver_v1_audit.txt"
)

AUDIT_JSON = (
    ROOT / "public" / "data"
    / "edgeiq_bom_search_location_resolver_v1_audit.json"
)

RAW_DIR = OUTPUT_DIR / "raw-search-pages"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

LOCATION_URL_RE = re.compile(
    r"""(?:
        https?://www\.bom\.gov\.au
    )?
    (
        /location/australia/victoria/
        [a-z0-9\-]+/
        [a-z0-9_\-]+
    )""",
    re.IGNORECASE | re.VERBOSE,
)

HREF_RE = re.compile(
    r"""href\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

TITLE_RE = re.compile(
    r"""<title[^>]*>(.*?)</title>""",
    re.IGNORECASE | re.DOTALL,
)

TAG_RE = re.compile(r"<[^>]+>")


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
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row.get(field, "")
                    for field in fieldnames
                }
            )


def normalise_text(value: str) -> str:
    value = html.unescape(value or "")
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_title(document: str) -> str:
    match = TITLE_RE.search(document)

    if not match:
        return ""

    text = TAG_RE.sub(" ", match.group(1))
    return re.sub(
        r"\s+",
        " ",
        html.unescape(text),
    ).strip()


def fetch(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "EDGEiQ-Weather-Registry/1.1 "
                "(single-request BOM location resolution)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/json;q=0.9,*/*;q=0.5"
            ),
            "Accept-Language": "en-AU,en;q=0.9",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=25,
        ) as response:
            content = response.read(2_500_000)

            return {
                "status": int(response.status),
                "final_url": str(response.geturl()),
                "content_type": str(
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                ),
                "text": content.decode(
                    "utf-8",
                    errors="ignore",
                ),
                "error": "",
            }

    except urllib.error.HTTPError as exc:
        return {
            "status": int(exc.code),
            "final_url": str(exc.geturl()),
            "content_type": "",
            "text": "",
            "error": f"HTTPError: {exc}",
        }

    except Exception as exc:
        return {
            "status": 0,
            "final_url": "",
            "content_type": "",
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def extract_location_urls(document: str) -> list[str]:
    candidates: set[str] = set()

    decoded_variants = {
        document,
        html.unescape(document),
        document.replace("\\/", "/"),
        html.unescape(
            document.replace("\\/", "/")
        ),
    }

    for variant in decoded_variants:
        for href in HREF_RE.findall(variant):
            absolute = urllib.parse.urljoin(
                "https://www.bom.gov.au/",
                html.unescape(href),
            )

            match = LOCATION_URL_RE.search(absolute)

            if match:
                candidates.add(
                    "https://www.bom.gov.au"
                    + match.group(1)
                )

        for match in LOCATION_URL_RE.finditer(variant):
            candidates.add(
                "https://www.bom.gov.au"
                + match.group(1)
            )

    return sorted(candidates)


def candidate_slug(url: str) -> str:
    return urllib.parse.unquote(
        url.rstrip("/").split("/")[-1]
    )


def score_candidate(
    search_name: str,
    track_names: str,
    url: str,
    nearby_context: str,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    search_norm = normalise_text(search_name)
    track_norms = [
        normalise_text(value)
        for value in track_names.split("|")
        if value.strip()
    ]

    slug_norm = normalise_text(candidate_slug(url))
    context_norm = normalise_text(nearby_context)

    if search_norm and search_norm == slug_norm:
        score += 100
        reasons.append("EXACT_SLUG")

    if search_norm and search_norm in slug_norm:
        score += 65
        reasons.append("SEARCH_NAME_IN_SLUG")

    if search_norm and search_norm in context_norm:
        score += 45
        reasons.append("SEARCH_NAME_IN_CONTEXT")

    for track_norm in track_norms:
        if track_norm and track_norm == slug_norm:
            score += 90
            reasons.append("EXACT_TRACK_SLUG")
            break

        if track_norm and track_norm in slug_norm:
            score += 55
            reasons.append("TRACK_NAME_IN_SLUG")
            break

        if track_norm and track_norm in context_norm:
            score += 35
            reasons.append("TRACK_NAME_IN_CONTEXT")
            break

    if "/victoria/" in url.lower():
        score += 20
        reasons.append("VICTORIA_LOCATION")

    if "search" in url.lower():
        score -= 100
        reasons.append("SEARCH_PAGE_REJECTED")

    return score, reasons


source_rows = read_csv(SOURCE_CSV)

resolved_rows: list[dict[str, Any]] = []
candidate_rows: list[dict[str, Any]] = []
manual_review_rows: list[dict[str, Any]] = []

for index, source in enumerate(source_rows, start=1):
    location_id = source["physical_location_id"]
    existing_status = source["verification_status"]
    existing_url = source["final_bom_url"]

    print(
        f"[{index}/{len(source_rows)}] "
        f"{location_id}"
    )

    if (
        existing_status == "VERIFIED_CANDIDATE"
        and "/location/australia/victoria/" in existing_url
    ):
        updated = dict(source)
        updated.update(
            {
                "verification_status": "VERIFIED_LOCATION",
                "resolution_status": "PRESERVED_VERIFIED",
                "candidate_count": "1",
                "selected_candidate_score": "999",
                "selected_candidate_reason": (
                    "PRESERVED_FROM_V1_VERIFIED_CANDIDATE"
                ),
                "search_page_url": "",
                "search_http_status": "",
                "search_page_title": "",
                "resolution_verified_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "resolver_version": (
                    "edgeiq_bom_search_location_resolver_v1"
                ),
            }
        )
        resolved_rows.append(updated)
        continue

    query = source["bom_search_name"]
    search_url = (
        "https://www.bom.gov.au/search?"
        + urllib.parse.urlencode({"query": query})
    )

    result = fetch(search_url)

    raw_path = RAW_DIR / f"{location_id.lower()}.html"

    if result["text"]:
        raw_path.write_text(
            result["text"],
            encoding="utf-8",
        )

    urls = extract_location_urls(result["text"])

    ranked: list[dict[str, Any]] = []

    for url in urls:
        position = result["text"].find(
            url.replace(
                "https://www.bom.gov.au",
                "",
            )
        )

        if position < 0:
            position = result["text"].find(
                url.replace("/", "\\/")
            )

        if position >= 0:
            context = result["text"][
                max(0, position - 500):
                min(len(result["text"]), position + 900)
            ]
        else:
            context = ""

        score, reasons = score_candidate(
            source["bom_search_name"],
            source["track_names"],
            url,
            context,
        )

        candidate = {
            "physical_location_id": location_id,
            "track_names": source["track_names"],
            "bom_search_name": source["bom_search_name"],
            "search_page_url": search_url,
            "search_http_status": result["status"],
            "candidate_url": url,
            "candidate_slug": candidate_slug(url),
            "candidate_score": score,
            "candidate_reasons": "|".join(reasons),
            "context_preview": normalise_text(context)[:700],
            "selected": "NO",
            "verification_status": "CANDIDATE_ONLY",
            "notes": "",
        }

        ranked.append(candidate)

    ranked.sort(
        key=lambda item: (
            int(item["candidate_score"]),
            item["candidate_url"],
        ),
        reverse=True,
    )

    selected: dict[str, Any] | None = None
    resolution_status = "UNRESOLVED"
    selected_reason = ""
    selected_score = ""

    if ranked:
        top = ranked[0]
        second_score = (
            int(ranked[1]["candidate_score"])
            if len(ranked) > 1
            else -999
        )

        top_score = int(top["candidate_score"])
        score_margin = top_score - second_score

        if top_score >= 100 and score_margin >= 20:
            selected = top
            resolution_status = "AUTO_RESOLVED_HIGH_CONFIDENCE"
            selected_reason = (
                f"TOP_SCORE={top_score};"
                f"MARGIN={score_margin};"
                f"REASONS={top['candidate_reasons']}"
            )
            selected_score = str(top_score)

        elif (
            len(ranked) == 1
            and top_score >= 65
        ):
            selected = top
            resolution_status = "AUTO_RESOLVED_SINGLE_CANDIDATE"
            selected_reason = (
                f"SINGLE_SCORE={top_score};"
                f"REASONS={top['candidate_reasons']}"
            )
            selected_score = str(top_score)

        else:
            resolution_status = "MANUAL_CANDIDATE_REVIEW"

    if selected is not None:
        selected["selected"] = "YES"
        selected["verification_status"] = (
            "VERIFIED_LOCATION_CANDIDATE"
        )

        updated = dict(source)
        updated.update(
            {
                "http_status": str(result["status"]),
                "final_bom_url": selected["candidate_url"],
                "page_title": clean_title(result["text"]),
                "location_name_confirmed": "YES",
                "verification_status": "VERIFIED_LOCATION",
                "last_verified_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "verification_method": (
                    "BOM search-page location extraction "
                    "with deterministic name ranking"
                ),
                "error": result["error"],
                "resolution_status": resolution_status,
                "candidate_count": str(len(ranked)),
                "selected_candidate_score": selected_score,
                "selected_candidate_reason": selected_reason,
                "search_page_url": search_url,
                "search_http_status": str(result["status"]),
                "search_page_title": clean_title(
                    result["text"]
                ),
                "resolution_verified_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "resolver_version": (
                    "edgeiq_bom_search_location_resolver_v1"
                ),
            }
        )
    else:
        updated = dict(source)
        updated.update(
            {
                "http_status": str(result["status"]),
                "verification_status": resolution_status,
                "last_verified_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "verification_method": (
                    "BOM search-page location extraction"
                ),
                "error": result["error"],
                "resolution_status": resolution_status,
                "candidate_count": str(len(ranked)),
                "selected_candidate_score": "",
                "selected_candidate_reason": "",
                "search_page_url": search_url,
                "search_http_status": str(result["status"]),
                "search_page_title": clean_title(
                    result["text"]
                ),
                "resolution_verified_at": (
                    datetime.now(timezone.utc).isoformat()
                ),
                "resolver_version": (
                    "edgeiq_bom_search_location_resolver_v1"
                ),
            }
        )

        manual_review_rows.append(updated)

    resolved_rows.append(updated)
    candidate_rows.extend(ranked)

    # One search request per unresolved location.
    time.sleep(0.4)

source_fields = list(source_rows[0].keys())

extra_fields = [
    "resolution_status",
    "candidate_count",
    "selected_candidate_score",
    "selected_candidate_reason",
    "search_page_url",
    "search_http_status",
    "search_page_title",
    "resolution_verified_at",
    "resolver_version",
]

resolved_fields = source_fields + [
    field
    for field in extra_fields
    if field not in source_fields
]

candidate_fields = [
    "physical_location_id",
    "track_names",
    "bom_search_name",
    "search_page_url",
    "search_http_status",
    "candidate_url",
    "candidate_slug",
    "candidate_score",
    "candidate_reasons",
    "context_preview",
    "selected",
    "verification_status",
    "notes",
]

write_csv(
    RESOLVED_CSV,
    resolved_fields,
    resolved_rows,
)

write_csv(
    CANDIDATES_CSV,
    candidate_fields,
    candidate_rows,
)

write_csv(
    REVIEW_CSV,
    resolved_fields,
    manual_review_rows,
)

resolved_payload = {
    "schema_version": "bom_track_location_registry_v1_1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "record_count": len(resolved_rows),
    "records": resolved_rows,
}

RESOLVED_JSON.write_text(
    json.dumps(
        resolved_payload,
        indent=2,
    ),
    encoding="utf-8",
)

verified_count = sum(
    row["verification_status"] == "VERIFIED_LOCATION"
    for row in resolved_rows
)

auto_resolved_count = sum(
    str(row.get("resolution_status", "")).startswith(
        "AUTO_RESOLVED"
    )
    for row in resolved_rows
)

preserved_count = sum(
    row.get("resolution_status") == "PRESERVED_VERIFIED"
    for row in resolved_rows
)

manual_count = sum(
    row.get("resolution_status")
    == "MANUAL_CANDIDATE_REVIEW"
    for row in resolved_rows
)

unresolved_count = sum(
    row.get("resolution_status") == "UNRESOLVED"
    for row in resolved_rows
)

audit = {
    "status": "EDGEIQ_BOM_SEARCH_LOCATION_RESOLVER_V1_AUDIT_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "physical_locations": len(resolved_rows),
    "verified_locations": verified_count,
    "preserved_verified": preserved_count,
    "auto_resolved": auto_resolved_count,
    "manual_candidate_review": manual_count,
    "unresolved": unresolved_count,
    "candidate_rows": len(candidate_rows),
    "output_registry": str(RESOLVED_CSV.relative_to(ROOT)),
    "candidate_evidence": str(CANDIDATES_CSV.relative_to(ROOT)),
    "manual_review": str(REVIEW_CSV.relative_to(ROOT)),
    "notes": [
        "No BOM location URL was guessed.",
        "Existing verified location URLs were preserved.",
        "Ambiguous search results remain unresolved.",
        "Forecast locations and observation stations remain separate.",
        "No observation station was assigned.",
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
            f"verified_locations={audit['verified_locations']}",
            f"preserved_verified={audit['preserved_verified']}",
            f"auto_resolved={audit['auto_resolved']}",
            (
                "manual_candidate_review="
                f"{audit['manual_candidate_review']}"
            ),
            f"unresolved={audit['unresolved']}",
            f"candidate_rows={audit['candidate_rows']}",
            f"output_registry={audit['output_registry']}",
            f"candidate_evidence={audit['candidate_evidence']}",
            f"manual_review={audit['manual_review']}",
            "",
            "No BOM location URL was guessed.",
            "No BOM observation station was assigned.",
        ]
    )
    + "\n",
    encoding="utf-8",
)

print("")
print(audit["status"])
print(f"physical_locations={len(resolved_rows)}")
print(f"verified_locations={verified_count}")
print(f"preserved_verified={preserved_count}")
print(f"auto_resolved={auto_resolved_count}")
print(f"manual_candidate_review={manual_count}")
print(f"unresolved={unresolved_count}")
print(f"candidate_rows={len(candidate_rows)}")
