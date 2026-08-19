from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "weather-source-audit" / "turftrax"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "caulfield": "https://its.turftrax.co.uk/visualiser/caulfield/",
    "sandown": "https://its.turftrax.co.uk/visualiser/ladbrokes/",
    "mornington": "https://its.turftrax.co.uk/visualiser/mornington/",
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
    "api",
    "ajax",
    "fetch(",
    "axios",
    "graphql",
    "xmlhttprequest",
    "websocket",
    "signalr",
    "visualiser",
    "weather",
    "temperature",
    "humidity",
    "rain",
    "rainfall",
    "wind",
    "gust",
    "going",
    "goingstick",
    "going-stick",
    "rail",
    "irrigation",
    "evapotranspiration",
    "moisture",
    "station",
    "report",
    "refresh",
]

URL_PATTERN = re.compile(
    r'''(?:
        https?://[^\s"'<>\\]+
        |
        wss?://[^\s"'<>\\]+
        |
        /(?:api|ajax|data|weather|going|visualiser|station|report)[^\s"'<>\\]*
    )''',
    re.IGNORECASE | re.VERBOSE,
)

session = requests.Session()
session.headers.update(HEADERS)


def safe_name(url: str, index: int) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or f"asset_{index}"
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return f"{index:03d}_{name}"


def context(text: str, position: int, radius: int = 320) -> str:
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end].replace("\r", " ").replace("\n", " ")


all_results: dict[str, object] = {}

for source_name, page_url in SOURCES.items():
    print()
    print(f"[EDGEIQ] Inspecting TurfTrax {source_name}")

    source_dir = OUT / source_name
    source_dir.mkdir(parents=True, exist_ok=True)

    response = session.get(page_url, timeout=60)
    response.raise_for_status()

    html = response.text
    (source_dir / "page.html").write_text(
        html,
        encoding="utf-8",
        errors="ignore",
    )

    soup = BeautifulSoup(html, "html.parser")

    asset_urls: list[str] = []

    for tag in soup.find_all(["script", "link"]):
        url = tag.get("src") or tag.get("href")

        if not url:
            continue

        absolute = urljoin(page_url, url)

        if absolute not in asset_urls:
            asset_urls.append(absolute)

    documents = [
        {
            "name": "page.html",
            "url": page_url,
            "kind": "html",
            "text": html,
        }
    ]

    downloaded_assets: list[dict[str, object]] = []

    for index, asset_url in enumerate(asset_urls, start=1):
        print(
            f"[EDGEIQ] {source_name}: "
            f"downloading asset {index}/{len(asset_urls)}"
        )

        try:
            asset_response = session.get(
                asset_url,
                timeout=60,
                headers={"Referer": page_url},
            )
            asset_response.raise_for_status()
        except Exception as exc:
            downloaded_assets.append(
                {
                    "url": asset_url,
                    "status": "ERROR",
                    "error": str(exc),
                }
            )
            continue

        content_type = asset_response.headers.get("content-type", "")
        text = asset_response.text

        filename = safe_name(asset_url, index)
        output_path = source_dir / filename

        output_path.write_text(
            text,
            encoding="utf-8",
            errors="ignore",
        )

        downloaded_assets.append(
            {
                "url": asset_url,
                "status": asset_response.status_code,
                "content_type": content_type,
                "filename": filename,
                "bytes": len(asset_response.content),
            }
        )

        if any(
            marker in content_type.lower()
            for marker in ["javascript", "json", "text", "html"]
        ) or filename.lower().endswith((".js", ".json", ".html", ".txt")):
            documents.append(
                {
                    "name": filename,
                    "url": asset_url,
                    "kind": content_type,
                    "text": text,
                }
            )

    findings: list[dict[str, object]] = []

    for document in documents:
        text = str(document["text"])
        lower = text.lower()

        hits = []

        for keyword in KEYWORDS:
            start = 0

            while True:
                position = lower.find(keyword.lower(), start)

                if position == -1:
                    break

                hits.append(
                    {
                        "keyword": keyword,
                        "position": position,
                        "context": context(text, position),
                    }
                )

                start = position + len(keyword)

                if len(hits) >= 500:
                    break

            if len(hits) >= 500:
                break

        discovered_urls = sorted(
            {
                item.rstrip("),;]}\\")
                for item in URL_PATTERN.findall(text)
                if item
            }
        )

        likely_urls = [
            item
            for item in discovered_urls
            if any(
                token in item.lower()
                for token in [
                    "api",
                    "ajax",
                    "data",
                    "weather",
                    "going",
                    "station",
                    "report",
                    "visualiser",
                ]
            )
        ]

        if hits or likely_urls:
            findings.append(
                {
                    "document": document["name"],
                    "document_url": document["url"],
                    "kind": document["kind"],
                    "likely_urls": likely_urls,
                    "keyword_hits": hits,
                }
            )

    output = {
        "source": source_name,
        "page_url": page_url,
        "page_status": response.status_code,
        "asset_count": len(asset_urls),
        "downloaded_assets": downloaded_assets,
        "findings": findings,
    }

    all_results[source_name] = output

    (source_dir / "audit.json").write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    report = [
        f"EDGEIQ TURFTRAX AUDIT — {source_name.upper()}",
        "=" * 60,
        "",
        f"URL: {page_url}",
        f"Page status: {response.status_code}",
        f"Assets discovered: {len(asset_urls)}",
        f"Documents with findings: {len(findings)}",
        "",
    ]

    for finding in findings:
        report.extend(
            [
                "-" * 60,
                f"Document: {finding['document']}",
                f"URL: {finding['document_url']}",
                "",
            ]
        )

        likely_urls = finding.get("likely_urls", [])

        if likely_urls:
            report.append("LIKELY URLS:")

            for item in likely_urls:
                report.append(f"  {item}")

            report.append("")

        report.append("KEYWORD CONTEXT:")

        for hit in finding.get("keyword_hits", [])[:80]:
            report.append(f"  [{hit['keyword']}]")
            report.append(f"  {hit['context']}")
            report.append("")

    (source_dir / "audit_report.txt").write_text(
        "\n".join(report),
        encoding="utf-8",
    )

(OUT / "all_turftrax_audit.json").write_text(
    json.dumps(all_results, indent=2),
    encoding="utf-8",
)

print()
print("[EDGEIQ] TurfTrax visualiser audit complete")
print(f"[EDGEIQ] Output: {OUT}")
