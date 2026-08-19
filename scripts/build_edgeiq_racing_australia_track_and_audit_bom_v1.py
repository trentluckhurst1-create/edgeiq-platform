from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

RA_URL = (
    "https://www.racingaustralia.horse/"
    "InteractiveForm/TrackCondition.aspx?State=VIC"
)

BOM_STATIONS = {
    "87184": (
        "https://www.bom.gov.au/"
        "weatherstation/australia/victoria/87184"
    ),
}

RA_RAW_DIR = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "racing-australia-vic"
)

BOM_RAW_DIR = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "bom-stations"
)

RA_OUTPUT = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_vic_official_track_conditions_v1.json"
)

RA_SUMMARY = (
    ROOT
    / "public"
    / "data"
    / "edgeiq_vic_official_track_conditions_v1_summary.txt"
)

AUDIT_SUMMARY = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "EDGEIQ_RACING_AUSTRALIA_BOM_SOURCE_AUDIT.txt"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}

RA_RAW_DIR.mkdir(parents=True, exist_ok=True)
BOM_RAW_DIR.mkdir(parents=True, exist_ok=True)
RA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()

    if not text:
        return None

    if text.lower() in {
        "-",
        "—",
        "n/a",
        "na",
        "none",
        "null",
        "nil",
    }:
        return None

    return text


def number_or_none(value: Any) -> float | None:
    text = clean_text(value)

    if not text:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text.replace(",", ""),
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def canonical_venue(value: Any) -> str:
    text = clean_text(value) or ""

    text = text.upper()

    text = re.sub(
        r"^(SPORTSBET|BET365|LADBROKES|SOUTHSIDE)"
        r"[-\s]+",
        "",
        text,
    )

    text = re.sub(r"\s+", " ", text).strip()

    aliases = {
        "CAULFIELD HEATH": "CAULFIELD",
        "SANDOWN HILLSIDE": "SANDOWN",
        "SANDOWN LAKESIDE": "SANDOWN",
        "LADBROKES PARK": "SANDOWN",
        "BALLARAT SYNTHETIC": "BALLARAT SYNTHETIC",
        "GEELONG SYNTHETIC": "GEELONG SYNTHETIC",
    }

    return aliases.get(text, text)


def parse_meeting_label(
    value: str,
) -> tuple[str | None, str | None, str | None]:
    text = clean_text(value) or ""

    match = re.match(
        r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
        r"\s+(\d{1,2})-([A-Za-z]{3})\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None, None, clean_text(text)

    weekday = match.group(1).title()
    day = int(match.group(2))
    month_text = match.group(3).title()
    venue = clean_text(match.group(4))

    current_year = datetime.now().year

    try:
        meeting_date = datetime.strptime(
            f"{day:02d}-{month_text}-{current_year}",
            "%d-%b-%Y",
        ).date().isoformat()
    except ValueError:
        meeting_date = None

    return weekday, meeting_date, venue


def classify_rainfall(
    value: str | None,
) -> dict[str, float | None]:
    text = value or ""

    last_24h = None
    last_7d = None

    match_24 = re.search(
        r"([\d.]+)\s*mm\s+last\s+24\s+hours",
        text,
        flags=re.IGNORECASE,
    )

    match_7 = re.search(
        r"([\d.]+)\s*mm\s+last\s+7\s+days",
        text,
        flags=re.IGNORECASE,
    )

    if match_24:
        last_24h = number_or_none(match_24.group(1))

    if match_7:
        last_7d = number_or_none(match_7.group(1))

    if re.search(
        r"\bnil\s+last\s+24\s+hours",
        text,
        flags=re.IGNORECASE,
    ):
        last_24h = 0.0

    if re.search(
        r"\bnil\s+last\s+7\s+days",
        text,
        flags=re.IGNORECASE,
    ):
        last_7d = 0.0

    return {
        "rainfall_24h_mm": last_24h,
        "rainfall_7day_mm": last_7d,
    }


def find_track_table(
    soup: BeautifulSoup,
):
    best_table = None
    best_score = -1

    required_terms = {
        "condition",
        "rail",
        "irrigation",
        "rainfall",
    }

    for table in soup.find_all("table"):
        table_text = table.get_text(
            " ",
            strip=True,
        ).lower()

        score = sum(
            term in table_text
            for term in required_terms
        )

        if score > best_score:
            best_score = score
            best_table = table

    return best_table, best_score


def build_racing_australia_feed(
) -> tuple[list[dict[str, Any]], list[str]]:
    response = session.get(
        RA_URL,
        timeout=60,
    )

    response.raise_for_status()

    html = response.text

    (RA_RAW_DIR / "track_conditions_page.html").write_text(
        html,
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    table, score = find_track_table(soup)

    audit_lines = [
        "RACING AUSTRALIA VICTORIAN TRACK CONDITIONS",
        "=" * 55,
        "",
        f"URL: {RA_URL}",
        f"HTTP status: {response.status_code}",
        f"HTML bytes: {len(response.content)}",
        f"Track table score: {score}",
        "",
    ]

    if table is None:
        raise RuntimeError(
            "Racing Australia track-condition table was not found."
        )

    rows = table.find_all("tr")

    if not rows:
        raise RuntimeError(
            "Racing Australia table contained no rows."
        )

    header_cells = rows[0].find_all(
        ["th", "td"],
    )

    headers = [
        clean_text(cell.get_text(" ", strip=True))
        or f"column_{index + 1}"
        for index, cell in enumerate(header_cells)
    ]

    audit_lines.append(
        "HEADERS: " + " | ".join(headers)
    )

    records: list[dict[str, Any]] = []

    for row_index, row in enumerate(
        rows[1:],
        start=1,
    ):
        cells = row.find_all(
            ["td", "th"],
        )

        values = [
            clean_text(cell.get_text(" ", strip=True))
            for cell in cells
        ]

        if not values:
            continue

        while len(values) < len(headers):
            values.append(None)

        mapping = {
            headers[index]: values[index]
            for index in range(
                min(len(headers), len(values))
            )
        }

        lowered = {
            str(key).lower(): value
            for key, value in mapping.items()
        }

        meeting_raw = (
            lowered.get("meeting details")
            or lowered.get("meeting")
            or values[0]
        )

        weekday, meeting_date, venue = (
            parse_meeting_label(
                meeting_raw or "",
            )
        )

        if not venue:
            continue

        rainfall_text = (
            lowered.get("rainfall")
            or next(
                (
                    value
                    for key, value in lowered.items()
                    if "rainfall" in key
                ),
                None,
            )
        )

        rainfall = classify_rainfall(
            rainfall_text,
        )

        track_type = (
            lowered.get("track type")
            or next(
                (
                    value
                    for key, value in lowered.items()
                    if key == "type"
                ),
                None,
            )
        )

        track_condition = (
            lowered.get("track condition")
            or next(
                (
                    value
                    for key, value in lowered.items()
                    if "condition" in key
                ),
                None,
            )
        )

        record = {
            "meeting_key": canonical_venue(venue),
            "meeting": venue,
            "meeting_date": meeting_date,
            "meeting_weekday": weekday,
            "state": "VIC",

            "provider": "RACING_AUSTRALIA",
            "source_name": "Racing Australia",
            "source_url": RA_URL,

            "fetched_at_utc": datetime.now(
                timezone.utc,
            ).isoformat(),

            "track_type": track_type,
            "official_track_rating": track_condition,

            "penetrometer": clean_text(
                lowered.get("penetrometer")
            ),

            "weather_forecast": clean_text(
                lowered.get("weather forecast")
                or lowered.get("weather")
            ),

            "official_rail": clean_text(
                lowered.get("rail")
            ),

            "irrigation": clean_text(
                lowered.get("irrigation")
            ),

            "rainfall_report": rainfall_text,
            "rainfall_24h_mm": rainfall[
                "rainfall_24h_mm"
            ],
            "rainfall_7day_mm": rainfall[
                "rainfall_7day_mm"
            ],

            "comment": clean_text(
                lowered.get("comment")
            ),

            "additional_information": clean_text(
                lowered.get("additional information")
            ),

            "source_status": "LIVE",
            "raw": mapping,
        }

        records.append(record)

        audit_lines.append(
            f"{row_index}: "
            f"{record['meeting_date']} | "
            f"{record['meeting']} | "
            f"{record['official_track_rating']} | "
            f"{record['official_rail']} | "
            f"{record['rainfall_24h_mm']} | "
            f"{record['rainfall_7day_mm']}"
        )

    return records, audit_lines


URL_PATTERN = re.compile(
    r'''(?:
        https?://[^\s"'<>\\]+
        |
        /(?:api|weather|observations|forecast|station|data)
        [^\s"'<>\\]*
    )''',
    re.IGNORECASE | re.VERBOSE,
)


def safe_asset_name(
    url: str,
    index: int,
) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name

    if not name:
        name = f"asset_{index}"

    name = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        name,
    )

    return f"{index:03d}_{name}"


def audit_bom_station(
    station_id: str,
    page_url: str,
) -> list[str]:
    station_dir = BOM_RAW_DIR / station_id
    station_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    response = session.get(
        page_url,
        timeout=60,
    )

    response.raise_for_status()

    html = response.text

    (station_dir / "page.html").write_text(
        html,
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    asset_urls: list[str] = []

    for tag in soup.find_all(
        ["script", "link"],
    ):
        asset = (
            tag.get("src")
            or tag.get("href")
        )

        if not asset:
            continue

        absolute = urljoin(
            page_url,
            asset,
        )

        if absolute not in asset_urls:
            asset_urls.append(absolute)

    findings: list[dict[str, Any]] = []

    documents: list[
        tuple[str, str, str]
    ] = [
        (
            "page.html",
            page_url,
            html,
        )
    ]

    for index, asset_url in enumerate(
        asset_urls,
        start=1,
    ):
        try:
            asset_response = session.get(
                asset_url,
                timeout=60,
                headers={
                    "Referer": page_url,
                },
            )

            asset_response.raise_for_status()
        except Exception as exc:
            findings.append(
                {
                    "asset_url": asset_url,
                    "error": str(exc),
                }
            )
            continue

        content_type = (
            asset_response.headers.get(
                "content-type",
                "",
            )
        )

        name = safe_asset_name(
            asset_url,
            index,
        )

        output_path = station_dir / name

        output_path.write_bytes(
            asset_response.content,
        )

        if any(
            marker in content_type.lower()
            for marker in (
                "javascript",
                "json",
                "text",
                "html",
            )
        ) or output_path.suffix.lower() in {
            ".js",
            ".json",
            ".txt",
            ".html",
        }:
            documents.append(
                (
                    name,
                    asset_url,
                    asset_response.text,
                )
            )

    endpoint_candidates: set[str] = set()

    keywords = (
        "observation",
        "observations",
        "station",
        "temperature",
        "rain",
        "rainfall",
        "humidity",
        "wind",
        "gust",
        "forecast",
        "api",
        "fetch(",
        "graphql",
        "weatherstation",
        station_id,
    )

    keyword_contexts: list[dict[str, Any]] = []

    for document_name, document_url, text in documents:
        for match in URL_PATTERN.findall(text):
            candidate = match.rstrip(
                "),;]}\\"
            )

            if any(
                token in candidate.lower()
                for token in (
                    "api",
                    "weather",
                    "observation",
                    "station",
                    "forecast",
                    "data",
                )
            ):
                endpoint_candidates.add(
                    urljoin(
                        document_url,
                        candidate,
                    )
                )

        lower = text.lower()

        for keyword in keywords:
            start = 0
            hit_count = 0

            while True:
                position = lower.find(
                    keyword.lower(),
                    start,
                )

                if position < 0:
                    break

                context_start = max(
                    0,
                    position - 300,
                )

                context_end = min(
                    len(text),
                    position + 700,
                )

                keyword_contexts.append(
                    {
                        "document": document_name,
                        "url": document_url,
                        "keyword": keyword,
                        "context": text[
                            context_start:context_end
                        ].replace(
                            "\r",
                            " ",
                        ).replace(
                            "\n",
                            " ",
                        ),
                    }
                )

                start = position + len(keyword)
                hit_count += 1

                if hit_count >= 30:
                    break

    audit_payload = {
        "station_id": station_id,
        "page_url": page_url,
        "page_status": response.status_code,
        "page_bytes": len(response.content),
        "asset_count": len(asset_urls),
        "endpoint_candidates": sorted(
            endpoint_candidates
        ),
        "keyword_contexts": keyword_contexts,
        "findings": findings,
    }

    (
        station_dir
        / "bom_station_source_audit.json"
    ).write_text(
        json.dumps(
            audit_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report_lines = [
        f"BOM STATION AUDIT — {station_id}",
        "=" * 45,
        "",
        f"URL: {page_url}",
        f"HTTP status: {response.status_code}",
        f"HTML bytes: {len(response.content)}",
        f"Assets: {len(asset_urls)}",
        (
            "Endpoint candidates: "
            f"{len(endpoint_candidates)}"
        ),
        "",
        "ENDPOINT CANDIDATES",
        "-------------------",
    ]

    report_lines.extend(
        sorted(endpoint_candidates)
    )

    report_lines.extend(
        [
            "",
            "KEYWORD CONTEXT",
            "---------------",
        ]
    )

    for item in keyword_contexts[:160]:
        report_lines.extend(
            [
                "",
                (
                    f"[{item['document']}] "
                    f"{item['keyword']}"
                ),
                item["context"],
            ]
        )

    (
        station_dir
        / "bom_station_source_audit.txt"
    ).write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    return [
        f"BOM station: {station_id}",
        f"HTTP status: {response.status_code}",
        f"Assets: {len(asset_urls)}",
        (
            "Endpoint candidates: "
            f"{len(endpoint_candidates)}"
        ),
    ]


def main() -> int:
    all_audit_lines: list[str] = [
        "EDGEIQ RACING AUSTRALIA + BOM SOURCE AUDIT",
        "=" * 58,
        "",
        (
            "Generated: "
            f"{datetime.now(timezone.utc).isoformat()}"
        ),
        "",
    ]

    print(
        "[EDGEIQ] Fetching Racing Australia "
        "Victorian track conditions"
    )

    records, ra_audit = (
        build_racing_australia_feed()
    )

    output_payload = {
        "schema_version": (
            "edgeiq_vic_official_track_conditions_v1"
        ),
        "generated_at_utc": datetime.now(
            timezone.utc,
        ).isoformat(),
        "records": records,
    }

    RA_OUTPUT.write_text(
        json.dumps(
            output_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary_lines = [
        "EDGEIQ VICTORIAN OFFICIAL TRACK CONDITIONS V1",
        "=" * 52,
        "",
        (
            "Generated: "
            f"{output_payload['generated_at_utc']}"
        ),
        f"Records: {len(records)}",
        "",
    ]

    for record in records:
        summary_lines.extend(
            [
                (
                    f"{record['meeting_date']} | "
                    f"{record['meeting']} | "
                    f"{record['official_track_rating']} | "
                    f"{record['official_rail']}"
                ),
                (
                    "  Rainfall 24h: "
                    f"{record['rainfall_24h_mm']} mm"
                ),
                (
                    "  Rainfall 7d: "
                    f"{record['rainfall_7day_mm']} mm"
                ),
                (
                    "  Forecast: "
                    f"{record['weather_forecast']}"
                ),
                (
                    "  Irrigation: "
                    f"{record['irrigation']}"
                ),
            ]
        )

    summary_lines.extend(
        [
            "",
            "PRODUCT GOVERNANCE",
            "------------------",
            "Official Racing Australia values only.",
            "No projected future track rating.",
            "No inferred track downgrade or upgrade.",
        ]
    )

    RA_SUMMARY.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    all_audit_lines.extend(
        ra_audit
    )

    for station_id, page_url in (
        BOM_STATIONS.items()
    ):
        print(
            "[EDGEIQ] Auditing BOM station "
            f"{station_id}"
        )

        bom_lines = audit_bom_station(
            station_id,
            page_url,
        )

        all_audit_lines.extend(
            [
                "",
                *bom_lines,
            ]
        )

    AUDIT_SUMMARY.write_text(
        "\n".join(all_audit_lines),
        encoding="utf-8",
    )

    print()
    print(
        "[EDGEIQ] Racing Australia feed built"
    )
    print(
        f"[EDGEIQ] Track records: {len(records)}"
    )
    print(
        f"[EDGEIQ] Output: {RA_OUTPUT}"
    )
    print()
    print(
        "[EDGEIQ] BOM source audit complete"
    )
    print(
        f"[EDGEIQ] Output: {BOM_RAW_DIR}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
