from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
SCRIPTS = ROOT / "scripts"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUTPUT = DATA / "edgeiq_sectional_data_access_feasibility_v1.csv"
SUMMARY = DATA / "edgeiq_sectional_data_access_feasibility_v1_summary.csv"

TERMS_URL = "https://www.racing.com/about-us/terms-and-conditions"
GRAPHQL_ENDPOINT = "https://graphql.rmdprod.racing.com"
ROBOTS_URL = "https://www.racing.com/robots.txt"

COUNTRY_SUFFIXES = ("IRE", "USA", "JPN", "GER", "SAF", "NZ", "GB", "FR")

SECTIONAL_FILE_PATTERNS = re.compile(
    r"(sectional|section|split|velocity|physics|stride|pace|timing)",
    re.IGNORECASE,
)
SCRIPT_SEARCH_PATTERNS = {
    "racing.com": re.compile(r"racing\.com", re.IGNORECASE),
    "graphql.rmdprod": re.compile(r"graphql\.rmdprod", re.IGNORECASE),
    "headerAPIKey": re.compile(r"headerAPIKey", re.IGNORECASE),
    "X-Api-Key": re.compile(r"X-Api-Key", re.IGNORECASE),
    "sectional": re.compile(r"sectional", re.IGNORECASE),
    "sectionals": re.compile(r"sectionals", re.IGNORECASE),
    "splits": re.compile(r"\bsplits?\b", re.IGNORECASE),
}

OUTPUT_FIELDS = [
    "category",
    "item",
    "status",
    "evidence",
    "risk_level",
    "recommendation",
    "notes",
]

SUMMARY_FIELDS = ["metric", "value", "notes"]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "n/a", "-"} else text


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def canonical_horse(value: Any) -> str:
    text = clean(value).upper()
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    text = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^A-Z0-9]", "", text)
    for suffix in COUNTRY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix) + 3:
            return text[: -len(suffix)]
    return text


def normalise_track(value: Any) -> str:
    text = clean(value).upper()
    if "SANDOWN" in text:
        return "SANDOWN"
    if "KILMORE" in text:
        return "KILMORE"
    if "ECHUCA" in text:
        return "ECHUCA"
    text = re.sub(r"^(SPORTSBET|SPORTS BET|BET365|LADBROKES|TABTOUCH|TAB)\s+", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def first(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def source_horse_key(row: dict[str, str]) -> str:
    return canonical_horse(
        first(
            row,
            [
                "horse_key",
                "canonical_horse_key",
                "horse",
                "runner",
                "horse_name",
                "runner_name",
                "sectional_runner",
                "horse_name_norm",
                "horse_key_norm",
            ],
        )
    )


def source_track(row: dict[str, str]) -> str:
    return normalise_track(
        first(
            row,
            [
                "track",
                "track_name",
                "venue",
                "meeting",
                "track_norm",
                "meeting_name",
            ],
        )
    )


def source_date(row: dict[str, str]) -> str:
    value = first(
        row,
        [
            "race_date",
            "run_date",
            "date",
            "meeting_date",
            "snapshot_date",
        ],
    )
    return value[:10] if value else ""


def has_any_column(headers: list[str], candidates: list[str]) -> bool:
    lower = {header.lower() for header in headers}
    return any(candidate.lower() in lower for candidate in candidates)


def current_runner_context() -> tuple[set[str], dict[str, set[str]], int]:
    rows = read_csv(LIVE_FEED)
    all_horses: set[str] = set()
    by_meeting: dict[str, set[str]] = {"SANDOWN": set(), "KILMORE": set(), "ECHUCA": set()}
    for row in rows:
        horse = source_horse_key(row)
        track = source_track(row)
        if horse:
            all_horses.add(horse)
            for meeting in by_meeting:
                if meeting in track:
                    by_meeting[meeting].add(horse)
    return all_horses, by_meeting, len(rows)


def scan_csv_source(path: Path, current_horses: set[str], current_by_meeting: dict[str, set[str]]) -> dict[str, Any]:
    rows = 0
    unique_horses: set[str] = set()
    tracks: Counter[str] = Counter()
    dates: list[str] = []
    current_matches: set[str] = set()
    meeting_matches: dict[str, set[str]] = {meeting: set() for meeting in current_by_meeting}
    headers: list[str] = []

    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except UnicodeDecodeError:
        handle = path.open("r", encoding="latin-1", newline="")

    with handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        for row in reader:
            rows += 1
            horse = source_horse_key(row)
            if horse:
                unique_horses.add(horse)
                if horse in current_horses:
                    current_matches.add(horse)
                for meeting, horses in current_by_meeting.items():
                    if horse in horses:
                        meeting_matches[meeting].add(horse)
            track = source_track(row)
            if track:
                tracks[track] += 1
            date = source_date(row)
            if date:
                dates.append(date)

    usable_identifiers = []
    if has_any_column(headers, ["horse_key", "canonical_horse_key", "horse", "runner", "horse_name"]):
        usable_identifiers.append("HORSE")
    if has_any_column(headers, ["race_date", "run_date", "date", "meeting_date"]):
        usable_identifiers.append("DATE")
    if has_any_column(headers, ["track", "venue", "meeting", "track_name"]):
        usable_identifiers.append("TRACK")
    if has_any_column(headers, ["race_no", "race_number", "race_id", "sectional_race_key"]):
        usable_identifiers.append("RACE")

    has_meeting_ids = has_any_column(headers, ["meeting_id", "meetingId", "meeting_key", "meeting_code"])
    has_race_ids = has_any_column(headers, ["race_id", "raceId", "race_key", "sectional_race_key"])

    return {
        "file": path.name,
        "rows": rows,
        "unique_horses": len(unique_horses),
        "current_runner_matches": len(current_matches),
        "sandown_matches": len(meeting_matches["SANDOWN"]),
        "kilmore_matches": len(meeting_matches["KILMORE"]),
        "echuca_matches": len(meeting_matches["ECHUCA"]),
        "historical_horses_only": max(0, len(unique_horses) - len(current_matches)),
        "date_range": f"{min(dates)} -> {max(dates)}" if dates else "",
        "tracks_sample": "; ".join(track for track, _ in tracks.most_common(8)),
        "usable_identifiers": "|".join(usable_identifiers),
        "has_meeting_ids": "YES" if has_meeting_ids else "NO",
        "has_race_ids": "YES" if has_race_ids else "NO",
        "columns": "|".join(headers[:80]),
    }


def scan_sectional_files(current_horses: set[str], current_by_meeting: dict[str, set[str]]) -> tuple[list[dict[str, Any]], set[str]]:
    inventory: list[dict[str, Any]] = []
    union_matches: set[str] = set()
    for path in sorted(DATA.glob("*.csv")):
        if path in {OUTPUT, SUMMARY}:
            continue
        if not SECTIONAL_FILE_PATTERNS.search(path.name):
            continue
        try:
            info = scan_csv_source(path, current_horses, current_by_meeting)
        except Exception as exc:  # noqa: BLE001 - audit must continue source by source.
            info = {
                "file": path.name,
                "rows": "",
                "unique_horses": "",
                "current_runner_matches": "",
                "sandown_matches": "",
                "kilmore_matches": "",
                "echuca_matches": "",
                "historical_horses_only": "",
                "date_range": "",
                "tracks_sample": "",
                "usable_identifiers": "",
                "has_meeting_ids": "",
                "has_race_ids": "",
                "columns": "",
                "error": str(exc),
            }
        inventory.append(info)

        # Re-scan only matching horse keys for the union to avoid storing every row while the inventory function stays simple.
        if isinstance(info.get("current_runner_matches"), int) and info["current_runner_matches"] > 0:
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
                        horse = source_horse_key(row)
                        if horse in current_horses:
                            union_matches.add(horse)
            except UnicodeDecodeError:
                with path.open("r", encoding="latin-1", newline="") as handle:
                    for row in csv.DictReader(handle):
                        horse = source_horse_key(row)
                        if horse in current_horses:
                            union_matches.add(horse)
    return inventory, union_matches


def scan_scripts() -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    rows: list[dict[str, Any]] = []
    aggregate = Counter()
    graph_related_files: list[str] = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matches = {name: len(pattern.findall(text)) for name, pattern in SCRIPT_SEARCH_PATTERNS.items()}
        if not any(matches.values()):
            continue
        for name, count in matches.items():
            aggregate[name] += count
        if matches.get("graphql.rmdprod", 0) or matches.get("headerAPIKey", 0) or matches.get("X-Api-Key", 0):
            graph_related_files.append(path.name)
        rows.append(
            {
                "file": path.name,
                "matches": "; ".join(f"{name}:{count}" for name, count in matches.items() if count),
                "mentions_graphql_endpoint": "YES" if matches.get("graphql.rmdprod", 0) else "NO",
                "mentions_api_key_header": "YES" if matches.get("headerAPIKey", 0) or matches.get("X-Api-Key", 0) else "NO",
            }
        )
    return rows, dict(aggregate), graph_related_files


def single_row(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    return rows[0] if rows else {}


def int_from(row: dict[str, str], names: list[str], default: int = 0) -> int:
    for name in names:
        value = clean(row.get(name)).replace(",", "")
        if not value:
            continue
        try:
            return int(float(value))
        except ValueError:
            continue
    return default


def trusted_coverage_baseline() -> dict[str, Any]:
    strategy = single_row(DATA / "edgeiq_sectional_coverage_strategy_v1_summary.csv")
    expansion = single_row(DATA / "edgeiq_sectional_source_expansion_v1_summary.csv")

    current_runners = int_from(expansion, ["current_runners"]) or int_from(strategy, ["current_runners"])
    available_matches = int_from(expansion, ["all_available_sectional_current_matches"]) or int_from(strategy, ["sectional_source_matches"])
    missing = int_from(expansion, ["current_runners_still_missing_after_all_available_assets"]) or int_from(strategy, ["true_missing_history"])
    recommendation = clean(expansion.get("recommendation")) or clean(strategy.get("recommendation")) or "SECTIONAL_SOURCE_EXPANSION_REQUIRED"
    theoretical_pct = clean(expansion.get("theoretical_coverage_if_all_available_assets_used_pct")) or clean(strategy.get("sectional_source_coverage_pct"))
    dna_matches = int_from(expansion, ["horse_dna_v2_current_matches"]) or int_from(strategy, ["dna_matches"])
    gain = int_from(expansion, ["theoretical_coverage_gain_vs_horse_dna_v2"])

    if not current_runners:
        current_runners = 0
    coverage_pct = (available_matches / current_runners * 100.0) if current_runners else 0.0
    return {
        "current_runners": current_runners,
        "available_matches": available_matches,
        "missing": missing,
        "recommendation": recommendation,
        "coverage_pct": coverage_pct,
        "theoretical_pct": theoretical_pct,
        "dna_matches": dna_matches,
        "gain": gain,
        "strategy_source": "edgeiq_sectional_coverage_strategy_v1_summary.csv" if strategy else "",
        "expansion_source": "edgeiq_sectional_source_expansion_v1_summary.csv" if expansion else "",
    }


def add_row(
    rows: list[dict[str, Any]],
    category: str,
    item: str,
    status: str,
    evidence: str,
    risk_level: str,
    recommendation: str,
    notes: str = "",
) -> None:
    rows.append(
        {
            "category": category,
            "item": item,
            "status": status,
            "evidence": evidence,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "notes": notes,
        }
    )


def build_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_horses, current_by_meeting, current_runner_rows = current_runner_context()
    script_rows, script_pattern_counts, graph_related_files = scan_scripts()
    sectional_inventory, local_union_matches = scan_sectional_files(current_horses, current_by_meeting)
    trusted = trusted_coverage_baseline()

    broad_missing = max(0, len(current_horses) - len(local_union_matches))
    broad_coverage_pct = (len(local_union_matches) / len(current_horses) * 100.0) if current_horses else 0.0
    trusted_missing = trusted["missing"]
    trusted_matches = trusted["available_matches"]
    trusted_current_runners = trusted["current_runners"] or current_runner_rows
    trusted_coverage_pct = trusted["coverage_pct"]

    rows: list[dict[str, Any]] = []

    add_row(
        rows,
        "GOVERNANCE",
        "Racing.com terms page",
        "MANUAL_REVIEW_REQUIRED",
        TERMS_URL,
        "MEDIUM",
        "MANUAL_REVIEW_REQUIRED",
        "Terms URL identified for review. This script does not fetch or interpret legal terms automatically.",
    )
    add_row(
        rows,
        "GOVERNANCE",
        "Automated scraping/API access",
        "UNCLEAR_FROM_LOCAL_AUDIT",
        "No production permission or licence record found in local audit outputs.",
        "HIGH",
        "OFFICIAL_LICENSE",
        "Do not assume automated access is permitted. Seek written permission/licence before using Racing.com data operationally.",
    )
    add_row(
        rows,
        "GOVERNANCE",
        "GraphQL endpoint",
        "PRIVATE_OR_INTERNAL_ENDPOINT_RISK",
        GRAPHQL_ENDPOINT,
        "HIGH",
        "DO_NOT_USE_PRIVATE_ENDPOINT",
        "Endpoint appears internal/undocumented in local research context. No authenticated GraphQL probes were made.",
    )
    add_row(
        rows,
        "GOVERNANCE",
        "Robots and public-page policy",
        "NOT_FETCHED_READ_ONLY_LOCAL_AUDIT",
        ROBOTS_URL,
        "MEDIUM",
        "MANUAL_REVIEW_REQUIRED",
        "Public-page capture feasibility should be reviewed separately against robots.txt and terms before implementation.",
    )
    add_row(
        rows,
        "SAFE_PROBE_POLICY",
        "Authenticated GraphQL queries",
        "NOT_PERFORMED",
        "No network calls, no authenticated queries, no X-Api-Key extraction.",
        "HIGH",
        "DO_NOT_USE_PRIVATE_ENDPOINT",
        "One-off manual probes, if any, require explicit legal/governance approval and must not be productised without licence.",
    )

    if graph_related_files:
        add_row(
            rows,
            "TECHNICAL_ENDPOINT_INVENTORY",
            "Existing GraphQL-related scripts",
            "FOUND",
            "; ".join(graph_related_files),
            "HIGH",
            "AUDIT_EXISTING_SCRIPT_ONLY",
            "Existing files mention GraphQL/API-key patterns. This audit records file names only and does not expose keys or replay requests.",
        )
    else:
        add_row(
            rows,
            "TECHNICAL_ENDPOINT_INVENTORY",
            "Existing GraphQL-related scripts",
            "NOT_FOUND",
            "No local script mentions graphql.rmdprod/headerAPIKey/X-Api-Key.",
            "LOW",
            "NO_PRIVATE_API_ACTION",
            "",
        )

    for pattern, count in sorted(script_pattern_counts.items()):
        if count:
            add_row(
                rows,
                "TECHNICAL_ENDPOINT_INVENTORY",
                f"script_pattern::{pattern}",
                "FOUND",
                f"matches={count}",
                "HIGH" if pattern in {"graphql.rmdprod", "headerAPIKey", "X-Api-Key"} else "LOW",
                "AUDIT_EXISTING_SCRIPT_ONLY" if pattern in {"graphql.rmdprod", "headerAPIKey", "X-Api-Key"} else "LOCAL_SCRIPT_INVENTORY_ONLY",
                "",
            )

    for script in script_rows:
        add_row(
            rows,
            "TECHNICAL_ENDPOINT_INVENTORY",
            f"script::{script['file']}",
            "FOUND",
            script["matches"],
            "HIGH" if script["mentions_graphql_endpoint"] == "YES" or script["mentions_api_key_header"] == "YES" else "LOW",
            "AUDIT_EXISTING_SCRIPT_ONLY" if script["mentions_graphql_endpoint"] == "YES" or script["mentions_api_key_header"] == "YES" else "LOCAL_SCRIPT_INVENTORY_ONLY",
            f"mentions_graphql_endpoint={script['mentions_graphql_endpoint']}; mentions_api_key_header={script['mentions_api_key_header']}",
        )

    add_row(
        rows,
        "LOCAL_CAPABILITY",
        "trusted_current_sectional_coverage",
        "AUDITED",
        f"current_runners={trusted_current_runners}; all_available_sectional_current_matches={trusted_matches}; missing_current_runners={trusted_missing}; coverage_pct={trusted_coverage_pct:.2f}; dna_matches={trusted['dna_matches']}; theoretical_gain={trusted['gain']}",
        "MEDIUM",
        trusted["recommendation"],
        f"Trusted baseline comes from {trusted['strategy_source']} and {trusted['expansion_source']}. This avoids treating downstream audit/live files as fresh sectional sources.",
    )
    add_row(
        rows,
        "LOCAL_CAPABILITY",
        "broad_local_sectional_file_inventory_coverage",
        "INVENTORY_ONLY_NOT_SOURCE_GRADE",
        f"unique_current_horses={len(current_horses)}; broad_local_file_matches={len(local_union_matches)}; broad_missing_unique_horses={broad_missing}; broad_coverage_pct={broad_coverage_pct:.2f}",
        "MEDIUM",
        "DO_NOT_USE_AS_COVERAGE_BASELINE",
        "Broad inventory includes downstream/current-runner audit files and is not the trusted source-grade coverage metric.",
    )
    for meeting, horses in current_by_meeting.items():
        meeting_matches = sum(1 for horse in horses if horse in local_union_matches)
        add_row(
            rows,
            "LOCAL_CAPABILITY",
            f"meeting_coverage::{meeting}",
            "AUDITED",
            f"runners={len(horses)}; matches={meeting_matches}; missing={max(0, len(horses) - meeting_matches)}",
            "MEDIUM",
            "LOCAL_FILES_ONLY",
            "",
        )

    for item in sectional_inventory:
        status = "READ_ERROR" if item.get("error") else "INVENTORIED"
        risk = "LOW"
        recommendation = "LOCAL_FILE_AVAILABLE"
        if item.get("has_meeting_ids") == "NO" and item.get("has_race_ids") == "NO":
            recommendation = "MISSING_RACINGCOM_MATCH_IDS"
        add_row(
            rows,
            "LOCAL_SECTIONAL_FILE",
            item["file"],
            status,
            f"rows={item.get('rows')}; unique_horses={item.get('unique_horses')}; current_matches={item.get('current_runner_matches')}; date_range={item.get('date_range')}; tracks={item.get('tracks_sample')}",
            risk,
            recommendation,
            f"usable_identifiers={item.get('usable_identifiers')}; has_meeting_ids={item.get('has_meeting_ids')}; has_race_ids={item.get('has_race_ids')}; sandown={item.get('sandown_matches')}; kilmore={item.get('kilmore_matches')}; echuca={item.get('echuca_matches')}; historical_only={item.get('historical_horses_only')}; error={item.get('error', '')}",
        )

    private_endpoint_risk = "HIGH" if graph_related_files else "MEDIUM"
    if private_endpoint_risk == "HIGH":
        next_step = "SEEK_OFFICIAL_OR_PUBLIC_SECTIONAL_SOURCE"
    elif graph_related_files:
        next_step = "AUDIT_EXISTING_SCRIPT_ONLY"
    else:
        next_step = "MANUAL_REVIEW_REQUIRED"

    add_row(
        rows,
        "RECOMMENDATION",
        "recommended_next_step",
        next_step,
        f"private_endpoint_risk={private_endpoint_risk}; trusted_local_coverage_pct={trusted_coverage_pct:.2f}; missing_current_runners={trusted_missing}",
        private_endpoint_risk,
        next_step,
        "No production scraper should be built from the private/internal GraphQL endpoint without official permission.",
    )

    summary = [
        {"metric": "local_sectional_coverage", "value": f"{trusted_coverage_pct:.2f}%", "notes": f"Trusted source-grade coverage: {trusted_matches} of {trusted_current_runners} current runners."},
        {"metric": "current_runner_rows", "value": str(trusted_current_runners), "notes": str(LIVE_FEED)},
        {"metric": "unique_current_horses", "value": str(len(current_horses)), "notes": ""},
        {"metric": "missing_current_runners", "value": str(trusted_missing), "notes": "Current runner rows still missing after all source-grade available sectional assets."},
        {"metric": "trusted_available_sectional_matches", "value": str(trusted_matches), "notes": f"Baseline recommendation: {trusted['recommendation']}"},
        {"metric": "broad_inventory_unique_horse_matches", "value": str(len(local_union_matches)), "notes": "Inventory-only count; includes downstream/current-runner files and is not the coverage baseline."},
        {"metric": "private_endpoint_risk", "value": private_endpoint_risk, "notes": f"GraphQL-related local files: {len(graph_related_files)}"},
        {"metric": "official_access_recommended", "value": "YES", "notes": "Official licence/permission is the safe path for Racing.com sectional access."},
        {"metric": "recommended_next_step", "value": next_step, "notes": "Do not build a private GraphQL scraper from this audit."},
        {"metric": "terms_page_url", "value": TERMS_URL, "notes": ""},
        {"metric": "graphql_endpoint", "value": GRAPHQL_ENDPOINT, "notes": "Recorded for risk classification only; not queried."},
        {"metric": "sectional_files_inventoried", "value": str(len(sectional_inventory)), "notes": ""},
        {"metric": "scripts_with_relevant_matches", "value": str(len(script_rows)), "notes": ""},
        {"metric": "status", "value": "SECTIONAL_DATA_ACCESS_FEASIBILITY_AUDITED", "notes": "Governance + local feasibility only."},
    ]
    return rows, summary


def main() -> None:
    rows, summary = build_audit()
    write_csv(OUTPUT, rows, OUTPUT_FIELDS)
    write_csv(SUMMARY, summary, SUMMARY_FIELDS)
    print("EDGEiQ Sectional Data Access Feasibility V1")
    print(f"rows written: {len(rows)}")
    print(f"output: {OUTPUT}")
    print(f"summary: {SUMMARY}")


if __name__ == "__main__":
    main()
