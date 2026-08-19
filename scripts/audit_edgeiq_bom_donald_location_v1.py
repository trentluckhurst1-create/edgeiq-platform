from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]

OUT = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "bom-donald-location"
)

OUT.mkdir(parents=True, exist_ok=True)

PAGE_URL = (
    "https://www.bom.gov.au/location/"
    "australia/victoria/mallee/o283285303-donald"
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

session = requests.Session()
session.headers.update(HEADERS)

response = session.get(
    PAGE_URL,
    timeout=60,
)

response.raise_for_status()

html = response.text

(OUT / "donald_location_page.html").write_text(
    html,
    encoding="utf-8",
    errors="ignore",
)

soup = BeautifulSoup(
    html,
    "html.parser",
)

asset_urls: list[str] = []

for tag in soup.find_all(["script", "link"]):
    asset = tag.get("src") or tag.get("href")

    if not asset:
        continue

    absolute = urljoin(PAGE_URL, asset)

    if absolute not in asset_urls:
        asset_urls.append(absolute)

documents: list[tuple[str, str]] = [
    ("donald_location_page.html", html)
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
                "Referer": PAGE_URL,
            },
        )

        asset_response.raise_for_status()
    except Exception:
        continue

    content_type = asset_response.headers.get(
        "content-type",
        "",
    )

    name = Path(
        asset_url.split("?", 1)[0]
    ).name or f"asset_{index}"

    name = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        name,
    )

    output_path = OUT / f"{index:03d}_{name}"

    output_path.write_bytes(
        asset_response.content
    )

    if (
        "javascript" in content_type.lower()
        or "json" in content_type.lower()
        or "text" in content_type.lower()
        or output_path.suffix.lower()
        in {".js", ".json", ".txt", ".html"}
    ):
        documents.append(
            (
                output_path.name,
                asset_response.text,
            )
        )

patterns = {
    "place_ids": re.compile(
        r"\b[oap]\d{6,15}\b",
        re.IGNORECASE,
    ),
    "station_ids": re.compile(
        r"(?<!\d)\d{5,6}(?!\d)"
    ),
    "latitudes": re.compile(
        r'(?i)(?:latitude|lat_dec_deg|lat)["\':=\s]+'
        r'(-3[0-9]\.\d+)'
    ),
    "longitudes": re.compile(
        r'(?i)(?:longitude|long_dec_deg|lon|lng)'
        r'["\':=\s]+(14[0-9]\.\d+)'
    ),
    "observation_urls": re.compile(
        r'https?://[^"\'\s<>]+observations[^"\'\s<>]*',
        re.IGNORECASE,
    ),
    "station_urls": re.compile(
        r'https?://[^"\'\s<>]+weatherstation[^"\'\s<>]*',
        re.IGNORECASE,
    ),
}

matches: dict[str, set[str]] = {
    key: set()
    for key in patterns
}

contexts: list[dict[str, str]] = []

keywords = (
    "donald",
    "weatherstation",
    "bom_stn",
    "bom_stn_num",
    "station_id",
    "stationid",
    "observations/latest",
    "observations/recent",
    "nearby station",
    "nearest station",
    "placeid",
    "latitude",
    "longitude",
    "o283285303",
)

for document_name, text in documents:
    for key, pattern in patterns.items():
        for match in pattern.findall(text):
            value = (
                match
                if isinstance(match, str)
                else str(match)
            )

            matches[key].add(value)

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
                position - 500,
            )

            context_end = min(
                len(text),
                position + 1200,
            )

            contexts.append(
                {
                    "document": document_name,
                    "keyword": keyword,
                    "context": text[
                        context_start:context_end
                    ].replace("\r", " ").replace(
                        "\n",
                        " ",
                    ),
                }
            )

            start = position + len(keyword)
            hit_count += 1

            if hit_count >= 40:
                break

payload = {
    "page_url": PAGE_URL,
    "http_status": response.status_code,
    "html_bytes": len(response.content),
    "assets": asset_urls,
    "matches": {
        key: sorted(values)
        for key, values in matches.items()
    },
    "contexts": contexts,
}

(OUT / "donald_location_audit.json").write_text(
    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

report = [
    "EDGEIQ BOM DONALD LOCATION AUDIT",
    "=" * 48,
    "",
    f"Page: {PAGE_URL}",
    f"HTTP status: {response.status_code}",
    f"HTML bytes: {len(response.content)}",
    f"Assets: {len(asset_urls)}",
    "",
]

for key, values in matches.items():
    report.extend(
        [
            key.upper(),
            "-" * len(key),
        ]
    )

    report.extend(
        sorted(values) or ["None"]
    )

    report.append("")

report.extend(
    [
        "KEY CONTEXT",
        "-----------",
    ]
)

for item in contexts[:250]:
    report.extend(
        [
            "",
            (
                f"[{item['document']}] "
                f"{item['keyword']}"
            ),
            item["context"],
        ]
    )

(OUT / "EDGEIQ_BOM_DONALD_LOCATION_AUDIT.txt").write_text(
    "\n".join(report),
    encoding="utf-8",
)

print("[EDGEIQ] Donald BOM location audit complete")
print(f"[EDGEIQ] Output: {OUT}")
