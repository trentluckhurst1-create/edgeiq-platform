from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from edgeiq_racing_com_public_common_v1 import *

ENV_NAME = "RACINGCOM_CHAMPION_DATA_ENDPOINT_KEY"
COMPLETION = DOC / "completion"


def known_probe_row() -> dict:
    for row in read_csv(PUB / "edgeiq_racingcom_speed_network_probe_v1.csv"):
        url = row.get("response_url", "")
        if "graphql.rmdprod.racing.com" in url and "sectionaltimes_callback" in url:
            return row
    return {}


def query_from_url(url: str) -> str:
    raw = urllib.parse.parse_qs(urllib.parse.urlparse(url or "").query).get("query", [""])[0]
    return urllib.parse.unquote(raw)


def build_query(meeting_code: str, race_number: str) -> str:
    query_path = COMPLETION / "graphql" / "runner_sectionals.graphql"
    query = query_path.read_text(encoding="utf-8") if query_path.exists() else query_from_url(known_probe_row().get("response_url", ""))
    if meeting_code:
        query = query.replace('meetCode: "5191101"', f'meetCode: "{meeting_code}"')
    if race_number:
        query = query.replace("raceNumber:1", f"raceNumber:{race_number}").replace("raceNumber: 1", f"raceNumber: {race_number}")
    return query


def request_url(args: argparse.Namespace) -> tuple[str, dict]:
    row = known_probe_row()
    meet_code = args.meeting_code or "5191101"
    race_no = args.race_number or "1"
    if args.meeting_code or args.race_number:
        return GRAPHQL_ENDPOINT + "/?query=" + urllib.parse.quote(build_query(meet_code, race_no)), {"meetCode": meet_code, "raceNumber": race_no, "page_url": row.get("page_url", "")}
    return row.get("response_url", ""), {"meetCode": meet_code, "raceNumber": race_no, "page_url": row.get("page_url", "")}


def perform_request(url: str, headers: dict, timeout: int) -> dict:
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
            content_type = resp.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        content_type = exc.headers.get("content-type", "")
    except Exception as exc:
        return {"status_code": "ERROR", "response_content_type": "", "response_schema_match": "NO", "contains_sectionaltimes_callback": "NO", "horse_count": 0, "sectional_time_count": 0, "split_time_count": 0, "response_hash": "", "body": b"", "error": type(exc).__name__ + ": " + str(exc)}
    contains = False
    horses = []
    error = ""
    try:
        obj = json.loads(body.decode("utf-8", "ignore"))
        callback = (obj.get("data") or {}).get("sectionaltimes_callback")
        contains = callback is not None
        horses = (callback or {}).get("Horses") or []
    except Exception as exc:
        error = type(exc).__name__
    return {"status_code": status, "response_content_type": content_type, "response_schema_match": "YES" if contains and isinstance(horses, list) else "NO", "contains_sectionaltimes_callback": "YES" if contains else "NO", "horse_count": len(horses), "sectional_time_count": sum(len(h.get("SectionalTimes") or []) for h in horses if isinstance(h, dict)), "split_time_count": sum(len(h.get("SplitTimes") or []) for h in horses if isinstance(h, dict)), "response_hash": sha_bytes(body) if body else "", "body": body, "error": error}


def mode_headers(mode: str, page_url: str) -> tuple[dict, str]:
    headers = {"User-Agent": "EDGEiQ-runner-sectionals-live-access-v1", "Accept": "application/json"}
    state = "ABSENT"
    if mode in {"ANONYMOUS_BROWSER_HEADERS", "APPROVED_CREDENTIAL"}:
        headers.update({"Accept-Language": "en-AU,en;q=0.9", "Origin": "https://www.racing.com", "Referer": page_url or "https://www.racing.com/"})
    if mode == "APPROVED_CREDENTIAL":
        value = os.environ.get(ENV_NAME, "")
        if value:
            headers["x-api-key"] = value
            state = "PRESENT"
    return headers, state


def classify(mode: str, result: dict) -> str:
    if result.get("contains_sectionaltimes_callback") == "YES" and int(result.get("horse_count") or 0) > 0:
        if mode == "APPROVED_CREDENTIAL":
            return "CREDENTIAL_CONFIRMED"
        if mode == "ANONYMOUS_BROWSER_HEADERS":
            return "PUBLIC_ANONYMOUS_HEADER_SENSITIVE"
        return "PUBLIC_ANONYMOUS_CONFIRMED"
    if str(result.get("status_code")) == "DRY_RUN":
        return "CREDENTIAL_REQUIRED"
    if str(result.get("status_code")) in {"401", "403"}:
        return "CREDENTIAL_REQUIRED"
    if str(result.get("status_code")).startswith("2"):
        return "SOURCE_SCHEMA_CHANGED"
    if str(result.get("status_code")) == "ERROR":
        return "SOURCE_UNAVAILABLE"
    return "ACCESS_FORBIDDEN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--meeting-code", default="")
    parser.add_argument("--race-number", default="")
    parser.add_argument("--race-id", default="")
    parser.add_argument("--meet-url-segment", default="")
    parser.add_argument("--mode", default="ALL", choices=["ANONYMOUS_MINIMAL", "ANONYMOUS_BROWSER_HEADERS", "APPROVED_CREDENTIAL", "ALL"])
    parser.add_argument("--output-root", default=str(COMPLETION))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ensure()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    live_dir = output_root / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    url, variables = request_url(args)
    modes = ["ANONYMOUS_MINIMAL", "ANONYMOUS_BROWSER_HEADERS", "APPROVED_CREDENTIAL"] if args.mode == "ALL" else [args.mode]
    rows = []
    for mode in modes:
        headers, credential_state = mode_headers(mode, variables.get("page_url", ""))
        result = {"status_code": "DRY_RUN", "response_content_type": "", "response_schema_match": "NO", "contains_sectionaltimes_callback": "NO", "horse_count": 0, "sectional_time_count": 0, "split_time_count": 0, "response_hash": "", "body": b"", "error": ""} if args.dry_run else perform_request(url, headers, args.timeout)
        access = classify(mode, result)
        raw_path = ""
        if result.get("body") and result.get("contains_sectionaltimes_callback") == "YES":
            raw_file = live_dir / f"{mode.lower()}_{result['response_hash'][:16]}.json"
            write_text(raw_file, redact_text(result["body"].decode("utf-8", "ignore")))
            raw_path = str(raw_file.relative_to(ROOT))
        rows.append({"mode": mode, "endpoint": GRAPHQL_ENDPOINT + "/", "method": "GET", "query_variables": json.dumps({"meetCode": variables.get("meetCode"), "raceNumber": variables.get("raceNumber")}, sort_keys=True), "status_code": result.get("status_code"), "response_content_type": result.get("response_content_type"), "response_schema_match": result.get("response_schema_match"), "contains_sectionaltimes_callback": result.get("contains_sectionaltimes_callback"), "horse_count": result.get("horse_count"), "sectional_time_count": result.get("sectional_time_count"), "split_time_count": result.get("split_time_count"), "credential_state": credential_state, "cookie_state": "ABSENT", "access_classification": access, "response_hash": result.get("response_hash"), "raw_response_path": raw_path, "error": result.get("error", "")})
        time.sleep(args.delay_seconds)
    write_csv(output_root / "runner_sectionals_access_matrix.csv", rows)
    write_json(output_root / "runner_sectionals_access_matrix.json", rows)
    classes = {row["access_classification"] for row in rows}
    if "CREDENTIAL_CONFIRMED" in classes:
        decision = "CREDENTIAL_CONFIRMED"
    elif "PUBLIC_ANONYMOUS_CONFIRMED" in classes or "PUBLIC_ANONYMOUS_HEADER_SENSITIVE" in classes:
        decision = "PUBLIC_ANONYMOUS_CONFIRMED"
    elif "CREDENTIAL_REQUIRED" in classes:
        decision = "CREDENTIAL_REQUIRED"
    else:
        decision = sorted(classes)[0] if classes else "SOURCE_UNAVAILABLE"
    decision_md = f"""# Runner Sectionals Access Decision

Decision: `{decision}`

Clean Python replay uses no cookies or retained browser state. Approved credential mode uses `{ENV_NAME}` only when supplied by environment.

```json
{json.dumps(rows, indent=2)}
```
"""
    write_text(output_root / "runner_sectionals_access_decision.md", decision_md)
    print(json.dumps({"decision": decision, "rows": rows}, indent=2))
    return 0 if decision in {"PUBLIC_ANONYMOUS_CONFIRMED", "PUBLIC_ANONYMOUS_HEADER_SENSITIVE", "CREDENTIAL_CONFIRMED", "CREDENTIAL_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
