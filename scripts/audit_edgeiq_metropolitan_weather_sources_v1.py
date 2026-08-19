from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "weather-source-audit"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "vrc_flemington": "https://www.vrc.com.au/track-and-weather-conditions/",
    "mrc_metropolitan": "https://mrc.racing.com/racing/raceday-track-weather-live",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
}

API_PATTERNS = (
    "api",
    "graphql",
    "weather",
    "track",
    "meteo",
    "station",
    "going",
    "sensor",
    "rain",
    "irrigation",
)

session = requests.Session()
session.headers.update(HEADERS)

summary: list[dict[str, object]] = []

for source_name, url in SOURCES.items():
    print(f"[EDGEIQ] Fetching {source_name}: {url}")

    response = session.get(url, timeout=45)
    response.raise_for_status()

    html = response.text
    (OUT / f"{source_name}.html").write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")

    scripts: list[str] = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            scripts.append(urljoin(url, src))

    links: list[str] = []
    for tag in soup.find_all(["a", "link"]):
        href = tag.get("href")
        if href:
            links.append(urljoin(url, href))

    inline_script_text = "\n".join(
        script.get_text("\n", strip=False)
        for script in soup.find_all("script")
        if not script.get("src")
    )

    discovered_urls = sorted(
        set(
            re.findall(
                r'https?://[^"\'<>\s\\]+',
                html,
                flags=re.IGNORECASE,
            )
        )
    )

    candidates = sorted(
        set(
            item
            for item in scripts + links + discovered_urls
            if any(pattern in item.lower() for pattern in API_PATTERNS)
        )
    )

    text = soup.get_text("\n", strip=True)
    text_lines = [line.strip() for line in text.splitlines() if line.strip()]

    interesting_lines = [
        line
        for line in text_lines
        if any(pattern in line.lower() for pattern in API_PATTERNS)
    ]

    record = {
        "source": source_name,
        "url": url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "html_bytes": len(response.content),
        "script_count": len(scripts),
        "link_count": len(links),
        "candidate_count": len(candidates),
        "scripts": scripts,
        "candidate_urls": candidates,
        "interesting_text": interesting_lines,
    }

    summary.append(record)

    (OUT / f"{source_name}_scripts.json").write_text(
        json.dumps(scripts, indent=2),
        encoding="utf-8",
    )

    (OUT / f"{source_name}_candidates.json").write_text(
        json.dumps(candidates, indent=2),
        encoding="utf-8",
    )

    (OUT / f"{source_name}_interesting_text.txt").write_text(
        "\n".join(interesting_lines),
        encoding="utf-8",
    )

    (OUT / f"{source_name}_inline_scripts.txt").write_text(
        inline_script_text,
        encoding="utf-8",
    )

(OUT / "weather_source_audit_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

report_lines = [
    "EDGEIQ METROPOLITAN WEATHER SOURCE AUDIT",
    "=" * 44,
    "",
]

for row in summary:
    report_lines.extend(
        [
            f"Source: {row['source']}",
            f"URL: {row['url']}",
            f"Status: {row['status_code']}",
            f"HTML bytes: {row['html_bytes']}",
            f"Scripts: {row['script_count']}",
            f"Candidate endpoints/assets: {row['candidate_count']}",
            "",
        ]
    )

report_lines.extend(
    [
        "NEXT STEP",
        "---------",
        "Inspect candidate URLs and JavaScript bundles for JSON, GraphQL,",
        "WeatherTrax, station, sensor, track-condition and rainfall endpoints.",
        "",
        "Do not build the production weather feed until the source and",
        "refresh behaviour are confirmed.",
    ]
)

(OUT / "EDGEIQ_METRO_WEATHER_SOURCE_AUDIT.txt").write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print()
print("[EDGEIQ] Weather source audit complete")
print(f"[EDGEIQ] Output: {OUT}")
