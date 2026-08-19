from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]

OUT = (
    ROOT
    / "data"
    / "weather-source-audit"
    / "bom-live"
    / "87184"
)

OUT.mkdir(parents=True, exist_ok=True)

STATION_ID = "87184"

PAGE_URL = (
    "https://www.bom.gov.au/"
    f"weatherstation/australia/victoria/{STATION_ID}"
)

CANDIDATES = [
    {
        "label": "public_api_latest",
        "url": (
            "https://api.bom.gov.au/"
            "apikey/v1/observations/"
            f"latest/{STATION_ID}/atm/surf_air"
        ),
    },
    {
        "label": "public_api_recent",
        "url": (
            "https://api.bom.gov.au/"
            "apikey/v1/observations/"
            f"recent/{STATION_ID}/atm/surf_air"
        ),
    },
    {
        "label": "www_proxy_latest",
        "url": (
            "https://www.bom.gov.au/"
            "observations/"
            f"latest/{STATION_ID}/atm/surf_air"
        ),
    },
    {
        "label": "www_proxy_recent",
        "url": (
            "https://www.bom.gov.au/"
            "observations/"
            f"recent/{STATION_ID}/atm/surf_air"
        ),
    },
    {
        "label": "accessible_observations",
        "url": (
            "https://www.bom.gov.au/"
            "weatherstation/australia/victoria/"
            f"{STATION_ID}/accessible-observations"
        ),
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json, text/plain, "
        "text/html, */*"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer": PAGE_URL,
    "Origin": "https://www.bom.gov.au",
}

session = requests.Session()
session.headers.update(HEADERS)

results: list[dict[str, Any]] = []

for index, candidate in enumerate(
    CANDIDATES,
    start=1,
):
    label = candidate["label"]
    url = candidate["url"]

    print(
        f"[EDGEIQ] BOM probe "
        f"{index}/{len(CANDIDATES)}: {label}"
    )

    record: dict[str, Any] = {
        "label": label,
        "url": url,
    }

    try:
        response = session.get(
            url,
            timeout=45,
            allow_redirects=True,
        )

        content_type = response.headers.get(
            "content-type",
            "",
        )

        text = response.text

        record.update(
            {
                "status": response.status_code,
                "final_url": response.url,
                "content_type": content_type,
                "bytes": len(response.content),
                "headers": dict(response.headers),
                "preview": text[:1500],
            }
        )

        suffix = (
            "json"
            if (
                "json" in content_type.lower()
                or text.lstrip().startswith(("{", "["))
            )
            else "html"
            if "html" in content_type.lower()
            else "txt"
        )

        raw_path = OUT / f"{index:02d}_{label}.{suffix}"

        raw_path.write_text(
            text,
            encoding="utf-8",
            errors="ignore",
        )

        record["saved"] = str(
            raw_path.relative_to(ROOT)
        )

        try:
            parsed = response.json()

            record["json"] = True
            record["json_type"] = type(
                parsed
            ).__name__

            json_path = (
                OUT
                / f"{index:02d}_{label}_parsed.json"
            )

            json_path.write_text(
                json.dumps(
                    parsed,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            record["parsed_saved"] = str(
                json_path.relative_to(ROOT)
            )

        except Exception:
            record["json"] = False

    except Exception as exc:
        record["error"] = str(exc)

    results.append(record)

results_path = OUT / "bom_endpoint_probe_results.json"

results_path.write_text(
    json.dumps(
        results,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

report = [
    "EDGEIQ BOM OBSERVATION ENDPOINT PROBE",
    "=" * 52,
    "",
    f"Station: {STATION_ID}",
    f"Page: {PAGE_URL}",
    "",
]

for record in results:
    report.extend(
        [
            "-" * 72,
            f"Label: {record['label']}",
            f"URL: {record['url']}",
            f"Final URL: {record.get('final_url')}",
            f"Status: {record.get('status')}",
            f"Type: {record.get('content_type')}",
            f"Bytes: {record.get('bytes')}",
            f"JSON: {record.get('json')}",
            f"Saved: {record.get('saved')}",
        ]
    )

    if record.get("error"):
        report.append(
            f"Error: {record['error']}"
        )

    report.extend(
        [
            "",
            "Preview:",
            str(record.get("preview") or ""),
            "",
        ]
    )

report_path = (
    OUT
    / "EDGEIQ_BOM_OBSERVATION_ENDPOINT_PROBE.txt"
)

report_path.write_text(
    "\n".join(report),
    encoding="utf-8",
)

print()
print("[EDGEIQ] BOM observation probe complete")
print(f"[EDGEIQ] Output: {OUT}")
