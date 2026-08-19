from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SEARCH_ROOTS = [
    ROOT / "data" / "weather-source-audit" / "bom-donald-location",
    ROOT / "data" / "weather-source-audit" / "bom-stations",
    ROOT / "data" / "weather-source-audit" / "bom-live",
    ROOT / "data" / "weather-source-audit",
]

OUTPUT_DIR = ROOT / "data" / "weather" / "bom-location-api"
OUTPUT_CSV = OUTPUT_DIR / "bom_location_api_contract_evidence_v1.csv"
OUTPUT_TXT = ROOT / "public" / "data" / "edgeiq_bom_location_api_contract_trace_v1.txt"
OUTPUT_JSON = ROOT / "public" / "data" / "edgeiq_bom_location_api_contract_trace_v1.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_TXT.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_SUFFIXES = {
    ".js",
    ".json",
    ".txt",
    ".html",
    ".htm",
}

MAX_BYTES = 10_000_000

PATTERNS = [
    re.compile(r"/apikey/v1/locations", re.I),
    re.compile(r"api\.test2\.bom\.gov\.au", re.I),
    re.compile(r"fastapi-location", re.I),
    re.compile(r"\blocations\b", re.I),
    re.compile(r"locationSearch", re.I),
    re.compile(r"searchLocation", re.I),
    re.compile(r"location.*query", re.I),
    re.compile(r"query.*location", re.I),
]

URL_RE = re.compile(
    r"https?://[^\"'\s<>\\]+",
    re.I,
)


def safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_BYTES:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


files: list[Path] = []

for root in SEARCH_ROOTS:
    if not root.exists():
        continue

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue

        if path.stat().st_size > MAX_BYTES:
            continue

        files.append(path)

files = sorted(set(files))

rows: list[dict[str, Any]] = []

for path in files:
    text = safe_read(path)

    if not text:
        continue

    relative = str(path.relative_to(ROOT))

    seen_offsets: set[int] = set()

    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            if match.start() in seen_offsets:
                continue

            seen_offsets.add(match.start())

            start = max(0, match.start() - 1500)
            end = min(len(text), match.end() + 2500)
            context = text[start:end]

            nearby_urls = sorted(
                set(URL_RE.findall(context))
            )

            request_method_evidence = []

            for method_pattern in (
                r"\bfetch\s*\(",
                r"\baxios\.",
                r"\bXMLHttpRequest\b",
                r"\bmethod\s*:\s*[\"'](GET|POST)[\"']",
                r"\bheaders\s*:",
                r"\bparams\s*:",
                r"\bquery\s*:",
            ):
                if re.search(
                    method_pattern,
                    context,
                    re.I,
                ):
                    request_method_evidence.append(
                        method_pattern
                    )

            rows.append(
                {
                    "repository_file": relative,
                    "match_offset": match.start(),
                    "matched_text": match.group(0),
                    "context_before_after": context,
                    "nearby_urls": "|".join(nearby_urls),
                    "request_code_evidence": "|".join(
                        request_method_evidence
                    ),
                    "contains_get": (
                        "YES"
                        if re.search(
                            r"[\"']GET[\"']",
                            context,
                            re.I,
                        )
                        else "NO"
                    ),
                    "contains_post": (
                        "YES"
                        if re.search(
                            r"[\"']POST[\"']",
                            context,
                            re.I,
                        )
                        else "NO"
                    ),
                    "contains_query": (
                        "YES"
                        if re.search(
                            r"\bquery\b",
                            context,
                            re.I,
                        )
                        else "NO"
                    ),
                    "contains_search_term": (
                        "YES"
                        if re.search(
                            r"searchTerm|searchQuery|searchText",
                            context,
                            re.I,
                        )
                        else "NO"
                    ),
                    "verification_status": "REQUIRES_REVIEW",
                    "notes": "",
                }
            )

fields = [
    "repository_file",
    "match_offset",
    "matched_text",
    "context_before_after",
    "nearby_urls",
    "request_code_evidence",
    "contains_get",
    "contains_post",
    "contains_query",
    "contains_search_term",
    "verification_status",
    "notes",
]

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=fields,
    )
    writer.writeheader()
    writer.writerows(rows)

exact_endpoint_rows = [
    row
    for row in rows
    if (
        "/apikey/v1/locations"
        in row["context_before_after"]
        or "fastapi-location"
        in row["context_before_after"]
        or "api.test2.bom.gov.au"
        in row["context_before_after"]
    )
]

audit = {
    "status": "EDGEIQ_BOM_LOCATION_API_CONTRACT_TRACE_V1_PASS",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "files_checked": len(files),
    "evidence_rows": len(rows),
    "exact_endpoint_rows": len(exact_endpoint_rows),
    "output_csv": str(OUTPUT_CSV.relative_to(ROOT)),
    "notes": [
        "This was a repository-only trace.",
        "No network request was made.",
        "No endpoint parameters were guessed.",
        "No BOM location or station was assigned.",
    ],
}

OUTPUT_JSON.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8",
)

lines = [
    audit["status"],
    f"generated_at={audit['generated_at']}",
    f"files_checked={audit['files_checked']}",
    f"evidence_rows={audit['evidence_rows']}",
    f"exact_endpoint_rows={audit['exact_endpoint_rows']}",
    f"output_csv={audit['output_csv']}",
    "",
    "EXACT ENDPOINT EVIDENCE",
]

for row in exact_endpoint_rows[:30]:
    lines.extend(
        [
            "",
            f"file={row['repository_file']}",
            f"match={row['matched_text']}",
            f"nearby_urls={row['nearby_urls']}",
            (
                "request_code_evidence="
                f"{row['request_code_evidence']}"
            ),
            (
                "context="
                + row["context_before_after"]
                .replace("\r", " ")
                .replace("\n", " ")[:3000]
            ),
        ]
    )

lines.extend(
    [
        "",
        "No network request was made.",
        "No endpoint parameters were guessed.",
    ]
)

OUTPUT_TXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print(audit["status"])
print(f"files_checked={len(files)}")
print(f"evidence_rows={len(rows)}")
print(f"exact_endpoint_rows={len(exact_endpoint_rows)}")
