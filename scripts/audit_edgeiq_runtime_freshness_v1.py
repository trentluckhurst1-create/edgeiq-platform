from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_PRODUCTION_HOST = "https://edgeiq-platform.pages.dev"
TIMEZONE = "Australia/Melbourne"
USER_AGENT = "EDGEiQ-Runtime-Freshness/1.0 (+https://edgeiq-platform.pages.dev)"


def clean(value: object) -> str:
    return str(value if value is not None else "").strip()


def present(value: object) -> bool:
    return clean(value) not in {"", "-", "NA", "N/A", "None", "null"}


def source_value(value: object) -> object:
    if isinstance(value, dict):
        return value.get("value")
    return value


def cache_busted(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("edgeiq_runtime_freshness", str(int(time.time()))))
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )


def join_url(origin: str, path: str) -> str:
    return f"{origin.rstrip('/')}/{path.lstrip('/')}"


def print_kv(key: str, value: object) -> None:
    print(f"{key}={value}")


class CheckFailure(Exception):
    pass


def http_get(url: str, accept: str, timeout: int) -> tuple[int, str, str, bytes]:
    request = urllib.request.Request(
        cache_busted(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", response.getcode()))
        content_type = clean(response.headers.get("content-type"))
        cache_control = clean(response.headers.get("cache-control"))
        body = response.read()
    return status, content_type, cache_control, body


def fixture_read(root: Path, path: str) -> tuple[int, str, str, bytes]:
    file_path = root / path.lstrip("/")
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    content_type = "application/json" if file_path.suffix.lower() == ".json" else "text/csv"
    return 200, content_type, "fixture", file_path.read_bytes()


def read_endpoint(
    *,
    label: str,
    url: str,
    path: str,
    accept: str,
    timeout: int,
    fixture_root: Path | None,
) -> tuple[int, str, str, bytes]:
    try:
        if fixture_root is not None and path != "/":
            status, content_type, cache_control, body = fixture_read(fixture_root, path)
        else:
            status, content_type, cache_control, body = http_get(url, accept, timeout)
    except urllib.error.HTTPError as exc:
        print_kv(f"{label}_HTTP", exc.code)
        print_kv(f"{label}_FAILURE_REASON", f"HTTP_ERROR_{exc.code}")
        raise CheckFailure(f"{label}_HTTP_ERROR_{exc.code}") from exc
    except Exception as exc:
        print_kv(f"{label}_HTTP", "FETCH_ERROR")
        print_kv(f"{label}_FAILURE_REASON", f"{type(exc).__name__}: {exc}")
        raise CheckFailure(f"{label}_FETCH_ERROR") from exc

    print_kv(f"{label}_URL", url)
    print_kv(f"{label}_HTTP", status)
    print_kv(f"{label}_CONTENT_TYPE", content_type or "NONE")
    print_kv(f"{label}_CACHE_CONTROL", cache_control or "NONE")

    if status < 200 or status >= 300:
        raise CheckFailure(f"{label}_HTTP_NOT_2XX_{status}")

    return status, content_type, cache_control, body


def parse_json(label: str, body: bytes) -> dict[str, object]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except Exception as exc:
        print_kv(f"{label}_JSON", "FAIL")
        raise CheckFailure(f"{label}_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise CheckFailure(f"{label}_JSON_NOT_OBJECT")
    return payload


def parse_published_at(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def count_form_guide(body: bytes, expected_date: str) -> tuple[int, int, int, int, str]:
    payload = json.loads(body.decode("utf-8-sig"))
    races = payload.get("races") if isinstance(payload, dict) else None
    if not isinstance(races, list):
        raise CheckFailure("FORM_GUIDE_RACES_MISSING")

    active = 0
    declared = 0
    epr_populated = 0
    price_populated = 0

    for race in races:
        if not isinstance(race, dict):
            continue
        race_date = clean(race.get("raceDate"))
        if race_date != expected_date:
            continue
        runners = race.get("runners")
        if not isinstance(runners, list):
            continue
        for runner in runners:
            if not isinstance(runner, dict):
                continue
            declared += 1
            scratched = runner.get("scratched") is True or "SCRATCH" in clean(
                runner.get("runner_status") or runner.get("status") or runner.get("scratch_status")
            ).upper()
            if scratched:
                continue
            active += 1
            if present(source_value(runner.get("epi"))):
                epr_populated += 1
            if present(source_value(runner.get("edgeiqPrice"))):
                price_populated += 1

    generated_at = clean(payload.get("generatedAt")) if isinstance(payload, dict) else ""
    return declared, active, epr_populated, price_populated, generated_at


def count_terminal_feed(body: bytes, expected_date: str) -> tuple[int, int]:
    rows = list(csv.DictReader(body.decode("utf-8-sig").splitlines()))
    if not rows:
        raise CheckFailure("TERMINAL_FEED_EMPTY")
    date_columns = ["race_date", "date", "meeting_date"]
    row_date = next((column for column in date_columns if column in rows[0]), None)
    if row_date is None:
        raise CheckFailure("TERMINAL_FEED_DATE_COLUMN_MISSING")
    today_rows = [row for row in rows if clean(row.get(row_date)) == expected_date]
    return len(rows), len(today_rows)


def run(args: argparse.Namespace) -> int:
    data_origin = args.data_origin.rstrip("/")
    production_host = args.production_host.rstrip("/")
    expected_date = args.expected_date or datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
    expected = datetime.fromisoformat(expected_date).date()
    expected_tomorrow = (expected + timedelta(days=1)).isoformat()
    expected_day2 = (expected + timedelta(days=2)).isoformat()
    fixture_root = Path(args.fixture_root).resolve() if args.fixture_root else None
    failures: list[str] = []

    print_kv("EDGEIQ_RUNTIME_FRESHNESS", "START")
    print_kv("CURRENT_MELBOURNE_DATE", expected_date)
    print_kv("PRODUCTION_HOST", production_host)
    print_kv("DATA_ORIGIN", data_origin)
    print_kv("MAX_AGE_MINUTES", args.max_age_minutes)

    try:
        if not args.skip_production_host:
            read_endpoint(
                label="PRODUCTION_ROOT",
                url=join_url(production_host, "/"),
                path="/",
                accept="text/html,*/*",
                timeout=args.timeout,
                fixture_root=None,
            )
            read_endpoint(
                label="HEALTHZ",
                url=join_url(production_host, "/healthz"),
                path="/healthz",
                accept="text/html,application/json,*/*",
                timeout=args.timeout,
                fixture_root=None,
            )

        _, _, _, runtime_body = read_endpoint(
            label="RUNTIME_FRESHNESS",
            url=join_url(data_origin, "/data/edgeiq_runtime_freshness_v1.json"),
            path="/data/edgeiq_runtime_freshness_v1.json",
            accept="application/json,*/*",
            timeout=args.timeout,
            fixture_root=fixture_root,
        )
        runtime = parse_json("RUNTIME_FRESHNESS", runtime_body)
        operating_date = clean(runtime.get("operating_date"))
        audit_status = clean(runtime.get("audit_status"))
        published_at = parse_published_at(runtime.get("published_at_utc"))
        age_minutes = ""
        if published_at is not None:
            age_minutes = round((datetime.now(timezone.utc) - published_at).total_seconds() / 60, 2)

        print_kv("DATA_BUILD_TIMESTAMP", clean(runtime.get("published_at_utc")) or "MISSING")
        print_kv("AGE_MINUTES", age_minutes if age_minutes != "" else "UNPARSEABLE")
        print_kv("RUNTIME_OPERATING_DATE", operating_date)
        print_kv("RUNTIME_AUDIT_STATUS", audit_status)

        if operating_date != expected_date:
            failures.append(f"OPERATING_DATE_MISMATCH expected={expected_date} actual={operating_date}")
        if audit_status != "PASS":
            failures.append(f"RUNTIME_AUDIT_NOT_PASS actual={audit_status}")
        if published_at is None:
            failures.append("PUBLISHED_AT_UNPARSEABLE")
        elif age_minutes != "" and float(age_minutes) > args.max_age_minutes:
            failures.append(f"RUNTIME_AGE_TOO_OLD minutes={age_minutes}")

        _, _, _, window_body = read_endpoint(
            label="WINDOW",
            url=join_url(data_origin, "/data/edgeiq_three_day_window_v1.json"),
            path="/data/edgeiq_three_day_window_v1.json",
            accept="application/json,*/*",
            timeout=args.timeout,
            fixture_root=fixture_root,
        )
        window = parse_json("WINDOW", window_body)
        window_today = clean(window.get("today"))
        window_tomorrow = clean(window.get("tomorrow"))
        window_day2 = clean(window.get("dayPlus2"))
        print_kv("WINDOW_TODAY", window_today)
        print_kv("WINDOW_TOMORROW", window_tomorrow)
        print_kv("WINDOW_DAY2", window_day2)
        if window_today != expected_date:
            failures.append(f"WINDOW_TODAY_MISMATCH expected={expected_date} actual={window_today}")
        if window_tomorrow != expected_tomorrow:
            failures.append(f"WINDOW_TOMORROW_MISMATCH expected={expected_tomorrow} actual={window_tomorrow}")
        if window_day2 != expected_day2:
            failures.append(f"WINDOW_DAY2_MISMATCH expected={expected_day2} actual={window_day2}")

        _, _, _, terminal_body = read_endpoint(
            label="TERMINAL_FEED",
            url=join_url(data_origin, "/data/edgeiq_vic_live_terminal_feed_v1.csv"),
            path="/data/edgeiq_vic_live_terminal_feed_v1.csv",
            accept="text/csv,*/*",
            timeout=args.timeout,
            fixture_root=fixture_root,
        )
        terminal_rows, terminal_today_rows = count_terminal_feed(terminal_body, expected_date)
        print_kv("TERMINAL_FEED_ROWS", terminal_rows)
        print_kv("TERMINAL_FEED_TODAY_ROWS", terminal_today_rows)
        if terminal_today_rows <= 0:
            failures.append("TERMINAL_FEED_HAS_NO_CURRENT_DATE_ROWS")

        _, _, _, form_body = read_endpoint(
            label="FORM_GUIDE",
            url=join_url(data_origin, "/data/edgeiq_form_guide_enriched_v2.json"),
            path="/data/edgeiq_form_guide_enriched_v2.json",
            accept="application/json,*/*",
            timeout=args.timeout,
            fixture_root=fixture_root,
        )
        declared, active, epr_populated, price_populated, form_generated_at = count_form_guide(
            form_body,
            expected_date,
        )
        print_kv("FORM_GUIDE_GENERATED_AT", form_generated_at or "MISSING")
        print_kv("DECLARED_RUNNERS", declared)
        print_kv("ACTIVE_RUNNERS", active)
        print_kv("EPR_POPULATED", epr_populated)
        print_kv("EDGEIQ_PRICE_POPULATED", price_populated)
        print_kv("LEGITIMATE_GOVERNED_EXCLUSIONS", active - epr_populated)

        if active <= 0:
            failures.append("FORM_GUIDE_HAS_NO_ACTIVE_CURRENT_RUNNERS")
        if epr_populated < args.min_epr_populated:
            failures.append(f"EPR_POPULATED_BELOW_MIN min={args.min_epr_populated} actual={epr_populated}")
        if price_populated < args.min_price_populated:
            failures.append(
                f"EDGEIQ_PRICE_POPULATED_BELOW_MIN min={args.min_price_populated} actual={price_populated}"
            )
        if present(runtime.get("active_current_runners")) and int(runtime["active_current_runners"]) != active:
            failures.append(f"ACTIVE_RUNNER_SENTINEL_MISMATCH sentinel={runtime['active_current_runners']} actual={active}")
        if present(runtime.get("epr_populated_current_runners")) and int(runtime["epr_populated_current_runners"]) != epr_populated:
            failures.append(
                f"EPR_SENTINEL_MISMATCH sentinel={runtime['epr_populated_current_runners']} actual={epr_populated}"
            )
        if present(runtime.get("edgeiq_price_populated_current_runners")) and int(
            runtime["edgeiq_price_populated_current_runners"]
        ) != price_populated:
            failures.append(
                "EDGEIQ_PRICE_SENTINEL_MISMATCH "
                f"sentinel={runtime['edgeiq_price_populated_current_runners']} actual={price_populated}"
            )

    except CheckFailure as exc:
        failures.append(str(exc))

    if failures:
        print_kv("FRESHNESS_STATUS", "FAIL")
        print_kv("FAILURE_REASON", " | ".join(failures))
        return 1

    print_kv("FRESHNESS_STATUS", "PASS")
    print_kv("FAILURE_REASON", "NONE")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit EDGEiQ production runtime freshness.")
    parser.add_argument("--data-origin", required=True)
    parser.add_argument("--production-host", default=DEFAULT_PRODUCTION_HOST)
    parser.add_argument("--expected-date")
    parser.add_argument("--fixture-root")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-age-minutes", type=float, default=2160)
    parser.add_argument("--min-epr-populated", type=int, default=1)
    parser.add_argument("--min-price-populated", type=int, default=1)
    parser.add_argument("--skip-production-host", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(run(parse_args()))
