from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "weather-source-audit" / "turftrax-stream"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://its.turftrax.co.uk"
STREAM = urljoin(BASE, "/visualiser/stream/")

CLIENTS = {
    "caulfield": "https://its.turftrax.co.uk/visualiser/caulfield/",
    "ladbrokes": "https://its.turftrax.co.uk/visualiser/ladbrokes/",
    "mornington": "https://its.turftrax.co.uk/visualiser/mornington/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

PARAMETER_NAMES = [
    "client",
    "clientName",
    "name",
    "venue",
    "course",
    "track",
    "visualiser",
]

METHODS: list[dict[str, Any]] = []

for client, referer in CLIENTS.items():
    METHODS.append(
        {
            "label": f"{client}_get_plain",
            "method": "GET",
            "params": {},
            "data": None,
            "json": None,
            "client": client,
            "referer": referer,
        }
    )

    METHODS.append(
        {
            "label": f"{client}_get_path",
            "method": "GET",
            "url": urljoin(STREAM, f"{client}/"),
            "params": {},
            "data": None,
            "json": None,
            "client": client,
            "referer": referer,
        }
    )

    for param_name in PARAMETER_NAMES:
        METHODS.append(
            {
                "label": f"{client}_get_{param_name}",
                "method": "GET",
                "params": {param_name: client},
                "data": None,
                "json": None,
                "client": client,
                "referer": referer,
            }
        )

        METHODS.append(
            {
                "label": f"{client}_post_form_{param_name}",
                "method": "POST",
                "params": {},
                "data": {param_name: client},
                "json": None,
                "client": client,
                "referer": referer,
            }
        )

        METHODS.append(
            {
                "label": f"{client}_post_json_{param_name}",
                "method": "POST",
                "params": {},
                "data": None,
                "json": {param_name: client},
                "client": client,
                "referer": referer,
            }
        )

session = requests.Session()
session.headers.update(HEADERS)

results: list[dict[str, Any]] = []


def serialise_preview(text: str, limit: int = 1200) -> str:
    return text[:limit].replace("\r", " ").replace("\n", " ")


def looks_interesting(
    status_code: int,
    content_type: str,
    text: str,
) -> bool:
    lower = text.lower()

    markers = [
        "temperature",
        "humidity",
        "rain",
        "wind",
        "going",
        "rail",
        "irrigation",
        "station",
        "report",
        "caulfield",
        "ladbrokes",
        "mornington",
        "weather",
        "content",
    ]

    return (
        status_code == 200
        and len(text.strip()) > 2
        and (
            "json" in content_type.lower()
            or text.lstrip().startswith(("{", "["))
            or any(marker in lower for marker in markers)
        )
    )


for index, request_spec in enumerate(METHODS, start=1):
    label = request_spec["label"]
    method = request_spec["method"]
    client = request_spec["client"]
    referer = request_spec["referer"]
    url = request_spec.get("url", STREAM)

    print(
        f"[EDGEIQ] Probe {index}/{len(METHODS)} "
        f"{method} {label}"
    )

    headers = {
        "Referer": referer,
        "Origin": BASE,
    }

    try:
        response = session.request(
            method=method,
            url=url,
            params=request_spec.get("params"),
            data=request_spec.get("data"),
            json=request_spec.get("json"),
            headers=headers,
            timeout=20,
            allow_redirects=True,
        )

        content_type = response.headers.get("content-type", "")
        text = response.text

        suffix = "json" if "json" in content_type.lower() else "txt"
        output_file = OUT / f"{index:03d}_{label}.{suffix}"
        output_file.write_text(
            text,
            encoding="utf-8",
            errors="ignore",
        )

        parsed_json = None

        try:
            parsed_json = response.json()
        except Exception:
            parsed_json = None

        record = {
            "index": index,
            "label": label,
            "client": client,
            "method": method,
            "url": response.url,
            "status_code": response.status_code,
            "content_type": content_type,
            "response_bytes": len(response.content),
            "interesting": looks_interesting(
                response.status_code,
                content_type,
                text,
            ),
            "preview": serialise_preview(text),
            "headers": dict(response.headers),
            "parsed_json": parsed_json,
            "output_file": str(output_file.relative_to(ROOT)),
        }

        results.append(record)

    except Exception as exc:
        results.append(
            {
                "index": index,
                "label": label,
                "client": client,
                "method": method,
                "url": url,
                "status_code": None,
                "content_type": None,
                "response_bytes": 0,
                "interesting": False,
                "preview": None,
                "error": str(exc),
            }
        )

(OUT / "turftrax_stream_probe_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

interesting = [row for row in results if row.get("interesting")]

report = [
    "EDGEIQ TURFTRAX STREAM PROBE",
    "=" * 40,
    "",
    f"Endpoint: {STREAM}",
    f"Requests tested: {len(results)}",
    f"Interesting responses: {len(interesting)}",
    "",
]

for row in interesting:
    report.extend(
        [
            "-" * 70,
            f"Label: {row['label']}",
            f"Client: {row['client']}",
            f"Method: {row['method']}",
            f"URL: {row['url']}",
            f"Status: {row['status_code']}",
            f"Content-Type: {row['content_type']}",
            f"Bytes: {row['response_bytes']}",
            f"Saved: {row['output_file']}",
            "",
            "PREVIEW",
            row["preview"] or "",
            "",
        ]
    )

if not interesting:
    report.extend(
        [
            "No direct GET or POST pattern returned a clearly usable payload.",
            "",
            "Next step:",
            "Inspect common.js and visualiser JavaScript to recover the exact",
            "AJAX request body, headers, event-stream format, or polling logic.",
        ]
    )

(OUT / "EDGEIQ_TURFTRAX_STREAM_PROBE.txt").write_text(
    "\n".join(report),
    encoding="utf-8",
)

print()
print("[EDGEIQ] TurfTrax stream probe complete")
print(f"[EDGEIQ] Requests tested: {len(results)}")
print(f"[EDGEIQ] Interesting responses: {len(interesting)}")
print(f"[EDGEIQ] Output: {OUT}")
