from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "weather-source-audit"
BUNDLES = AUDIT / "bundles"
BUNDLES.mkdir(parents=True, exist_ok=True)

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
    "Accept": "*/*",
    "Accept-Language": "en-AU,en;q=0.9",
}

KEYWORDS = [
    "weathertrax",
    "weather",
    "meteorological",
    "temperature",
    "humidity",
    "rainfall",
    "precipitation",
    "irrigation",
    "soilmoisture",
    "soil moisture",
    "moistureloss",
    "moisture loss",
    "goingstick",
    "going stick",
    "trackrating",
    "track rating",
    "railposition",
    "rail position",
    "windspeed",
    "winddirection",
    "graphql",
    "/api/",
    "axios",
    "fetch(",
    "xmlhttprequest",
    "signalr",
    "websocket",
    "wss://",
]

URL_PATTERN = re.compile(
    r'''(?:
        https?://[^\s"'<>\\]+
        |
        wss?://[^\s"'<>\\]+
        |
        /(?:api|graphql|weather|track|station|sensor)[^\s"'<>\\]*
    )''',
    re.IGNORECASE | re.VERBOSE,
)

session = requests.Session()
session.headers.update(HEADERS)

all_findings: list[dict[str, object]] = []

def safe_name(url: str, index: int) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or f"bundle_{index}.js"
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return f"{index:03d}_{name}"

def nearby_context(text: str, position: int, radius: int = 280) -> str:
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end].replace("\r", " ").replace("\n", " ")

for source_name, page_url in SOURCES.items():
    print()
    print(f"[EDGEIQ] Inspecting {source_name}")

    html_path = AUDIT / f"{source_name}.html"
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    else:
        response = session.get(page_url, timeout=45)
        response.raise_for_status()
        html = response.text
        html_path.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")

    script_urls = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            script_urls.append(urljoin(page_url, src))

    embedded_blocks = []

    for index, script in enumerate(soup.find_all("script")):
        if script.get("src"):
            continue

        content = script.string or script.get_text()
        if not content or not content.strip():
            continue

        embedded_blocks.append(
            {
                "index": index,
                "type": script.get("type"),
                "id": script.get("id"),
                "content": content,
            }
        )

    source_findings: list[dict[str, object]] = []

    documents = [
        {
            "kind": "html",
            "name": f"{source_name}.html",
            "url": page_url,
            "text": html,
        }
    ]

    source_bundle_dir = BUNDLES / source_name
    source_bundle_dir.mkdir(parents=True, exist_ok=True)

    for index, script_url in enumerate(dict.fromkeys(script_urls), start=1):
        print(f"[EDGEIQ] Downloading script {index}/{len(script_urls)}")

        try:
            response = session.get(
                script_url,
                timeout=60,
                headers={"Referer": page_url},
            )
            response.raise_for_status()
        except Exception as exc:
            source_findings.append(
                {
                    "source": source_name,
                    "document": script_url,
                    "kind": "download_error",
                    "error": str(exc),
                }
            )
            continue

        text = response.text
        filename = safe_name(script_url, index)
        output_path = source_bundle_dir / filename
        output_path.write_text(text, encoding="utf-8", errors="ignore")

        documents.append(
            {
                "kind": "javascript",
                "name": filename,
                "url": script_url,
                "text": text,
            }
        )

    for embedded in embedded_blocks:
        embedded_text = embedded["content"]
        embedded_name = f"inline_{embedded['index']:03d}.txt"

        (source_bundle_dir / embedded_name).write_text(
            embedded_text,
            encoding="utf-8",
            errors="ignore",
        )

        documents.append(
            {
                "kind": "inline_script",
                "name": embedded_name,
                "url": page_url,
                "text": embedded_text,
            }
        )

    for document in documents:
        text = str(document["text"])
        lower = text.lower()

        keyword_hits = []

        for keyword in KEYWORDS:
            start = 0

            while True:
                position = lower.find(keyword.lower(), start)

                if position == -1:
                    break

                keyword_hits.append(
                    {
                        "keyword": keyword,
                        "position": position,
                        "context": nearby_context(text, position),
                    }
                )

                start = position + len(keyword)

                if len(keyword_hits) >= 250:
                    break

            if len(keyword_hits) >= 250:
                break

        urls = sorted(
            {
                match.rstrip("),;]}\\")
                for match in URL_PATTERN.findall(text)
                if match
            }
        )

        likely_urls = [
            url
            for url in urls
            if any(
                keyword in url.lower()
                for keyword in [
                    "api",
                    "graphql",
                    "weather",
                    "track",
                    "station",
                    "sensor",
                    "going",
                    "rain",
                    "meteor",
                    "signalr",
                    "socket",
                ]
            )
        ]

        if keyword_hits or likely_urls:
            source_findings.append(
                {
                    "source": source_name,
                    "document": document["name"],
                    "document_url": document["url"],
                    "kind": document["kind"],
                    "keyword_hits": keyword_hits,
                    "likely_urls": likely_urls,
                }
            )

    all_findings.extend(source_findings)

    (AUDIT / f"{source_name}_deep_findings.json").write_text(
        json.dumps(source_findings, indent=2),
        encoding="utf-8",
    )

    report: list[str] = [
        f"EDGEIQ DEEP WEATHER SOURCE AUDIT — {source_name.upper()}",
        "=" * 70,
        "",
        f"Page: {page_url}",
        f"External scripts: {len(script_urls)}",
        f"Inline script blocks: {len(embedded_blocks)}",
        f"Documents with findings: {len(source_findings)}",
        "",
    ]

    for finding in source_findings:
        report.extend(
            [
                "-" * 70,
                f"Document: {finding.get('document')}",
                f"Kind: {finding.get('kind')}",
            ]
        )

        if finding.get("document_url"):
            report.append(f"URL: {finding.get('document_url')}")

        if finding.get("error"):
            report.append(f"Error: {finding.get('error')}")

        urls = finding.get("likely_urls", [])
        if urls:
            report.append("")
            report.append("LIKELY URLS:")
            for item in urls:
                report.append(f"  {item}")

        hits = finding.get("keyword_hits", [])
        if hits:
            report.append("")
            report.append("KEYWORD CONTEXT:")

            for hit in hits[:40]:
                report.append(f"  [{hit['keyword']}]")
                report.append(f"  {hit['context']}")
                report.append("")

    report_path = AUDIT / f"{source_name}_deep_report.txt"
    report_path.write_text("\n".join(report), encoding="utf-8")

(AUDIT / "all_deep_weather_findings.json").write_text(
    json.dumps(all_findings, indent=2),
    encoding="utf-8",
)

print()
print("[EDGEIQ] Deep source inspection complete")
print(f"[EDGEIQ] Output: {AUDIT}")
