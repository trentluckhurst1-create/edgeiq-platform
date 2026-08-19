from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_v1.csv"
OUTPUT_CSV = ROOT / "public" / "data" / "edgeiq_runner_profile_match_audit_v1.csv"
OUTPUT_SUMMARY = ROOT / "public" / "data" / "edgeiq_runner_profile_match_summary_v1.txt"

CANDIDATE_SOURCES = [
    ROOT / "public" / "data" / "edgeiq_form_enrichment_feed_v4.csv",
    ROOT / "public" / "data" / "edgeiq_live_runner_board_v7_1_current_day_candidate.csv",
    ROOT / "public" / "data" / "edgeiq_live_runner_board_governed_v7_2g2_FRESH_CURRENT_EVIDENCE_MERGED.csv",
    ROOT / "src" / "edgeiq-os" / "services" / "live-race-data-snapshot.ts",
    ROOT / "src" / "edgeiq-os" / "services" / "race-file-v2.ts",
]

COUNTRY_SUFFIX_RE = re.compile(r"\s+\((?:NZ|IRE|GB|USA|FR|JPN|AUS|SAF|GER)\)\s*$", re.IGNORECASE)
PUNCT_RE = re.compile(r"[^A-Z0-9\s]+")
SPACE_RE = re.compile(r"\s+")


def normalise_runner_name(value: object) -> str:
    text = str(value or "")
    text = text.replace("’", "'").replace("`", "'").replace("´", "'")
    text = COUNTRY_SUFFIX_RE.sub("", text.strip())
    text = text.upper().strip()
    text = PUNCT_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def compact_key(value: object) -> str:
    return normalise_runner_name(value).replace(" ", "")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def first_present(row: dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def read_csv_runners(path: Path) -> list[str]:
    runner_keys = [
        "runner",
        "horse",
        "_horse",
        "latest_runner_name",
        "normalized_runner",
        "runner_name",
        "horse_name",
        "name",
    ]
    runners: list[str] = []
    for row in read_csv_rows(path):
        runner = first_present(row, runner_keys)
        status = first_present(row, ["runner_status", "ui_status", "scratch_status", "result_status"]).upper()
        if runner and status != "SCRATCHED":
            runners.append(runner)
    return runners


def read_ts_snapshot_runners(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [match.group(1).strip() for match in re.finditer(r"runner:\s*['\"]([^'\"]+)['\"]", text)]


def read_source_runners(path: Path) -> list[str]:
    if path.suffix.lower() == ".csv":
        return read_csv_runners(path)
    if path.suffix.lower() in {".ts", ".tsx"}:
        return read_ts_snapshot_runners(path)
    return []


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = normalise_runner_name(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def load_profile_index() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], Counter[str], Counter[str]]:
    exact_index: dict[str, dict[str, str]] = {}
    compact_index: dict[str, dict[str, str]] = {}
    exact_counts: Counter[str] = Counter()
    compact_counts: Counter[str] = Counter()

    for row in read_csv_rows(PROFILE_FILE):
        candidates = [
            row.get("normalized_runner", ""),
            row.get("runner", ""),
            row.get("latest_runner_name", ""),
            row.get("resolved_runner_key", ""),
        ]
        row_exact_keys: set[str] = set()
        row_compact_keys: set[str] = set()
        for candidate in candidates:
            exact = normalise_runner_name(candidate)
            compact = compact_key(candidate)
            if exact:
                row_exact_keys.add(exact)
                exact_index.setdefault(exact, row)
            if compact:
                row_compact_keys.add(compact)
                compact_index.setdefault(compact, row)
        exact_counts.update(row_exact_keys)
        compact_counts.update(row_compact_keys)

    return exact_index, compact_index, exact_counts, compact_counts


def choose_active_source(source_rows: dict[str, list[str]]) -> str:
    for source in source_rows:
        if source.endswith("src/edgeiq-os/services/live-race-data-snapshot.ts".replace("/", "\\")) or source.endswith(
            "src/edgeiq-os/services/live-race-data-snapshot.ts"
        ):
            return source
    best_source = ""
    best_score = -1
    for source, runners in source_rows.items():
        score = len(unique_preserve_order(runners))
        if score > best_score:
            best_source = source
            best_score = score
    return best_source


def profile_runner(row: dict[str, str] | None) -> str:
    if not row:
        return ""
    return first_present(row, ["runner", "latest_runner_name", "normalized_runner", "resolved_runner_key"])


def audit_runner(
    source_file: str,
    runner: str,
    exact_index: dict[str, dict[str, str]],
    compact_index: dict[str, dict[str, str]],
) -> dict[str, str]:
    normalised = normalise_runner_name(runner)
    compact = compact_key(runner)

    if normalised in exact_index:
        row = exact_index[normalised]
        return {
            "source_file": source_file,
            "runner": runner,
            "normalised_runner": normalised,
            "matched": "YES",
            "matched_profile_runner": profile_runner(row),
            "match_method": "NORMALISED_EXACT",
            "reason": "Matched by frontend-safe normalised runner name",
            "suggested_fix": "",
        }

    if compact in compact_index:
        row = compact_index[compact]
        return {
            "source_file": source_file,
            "runner": runner,
            "normalised_runner": normalised,
            "matched": "YES",
            "matched_profile_runner": profile_runner(row),
            "match_method": "COMPACT_NO_SPACE",
            "reason": "Matched after removing internal spaces",
            "suggested_fix": "Frontend can safely compare compact normalised key as fallback",
        }

    return {
        "source_file": source_file,
        "runner": runner,
        "normalised_runner": normalised,
        "matched": "NO",
        "matched_profile_runner": "",
        "match_method": "UNMATCHED",
        "reason": "No profile stats row found by exact or compact normalised key",
        "suggested_fix": "If present in results warehouse, rebuild profile feed; otherwise require horse identity bridge/source coverage",
    }


def main() -> int:
    exact_index, compact_index, exact_counts, compact_counts = load_profile_index()

    source_rows: dict[str, list[str]] = {}
    scanned_lines: list[str] = []
    for path in CANDIDATE_SOURCES:
        source = str(path.relative_to(ROOT))
        runners = unique_preserve_order(read_source_runners(path))
        source_rows[source] = runners
        scanned_lines.append(f"- {source}: {len(runners)} unique runners")

    active_source = choose_active_source(source_rows)
    active_runners = source_rows.get(active_source, [])

    audit_rows = [
        audit_runner(active_source, runner, exact_index, compact_index)
        for runner in active_runners
    ]

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "source_file",
            "runner",
            "normalised_runner",
            "matched",
            "matched_profile_runner",
            "match_method",
            "reason",
            "suggested_fix",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    total = len(audit_rows)
    matched = sum(1 for row in audit_rows if row["matched"] == "YES")
    unmatched = [row["runner"] for row in audit_rows if row["matched"] != "YES"]
    match_pct = round((matched / total) * 100, 1) if total else 0.0
    method_counts = Counter(row["match_method"] for row in audit_rows)
    reason_counts = Counter(row["reason"] for row in audit_rows if row["matched"] != "YES")
    duplicate_profile_exact = sum(1 for count in exact_counts.values() if count > 1)
    duplicate_profile_compact = sum(1 for count in compact_counts.values() if count > 1)
    current_counts = Counter(normalise_runner_name(runner) for runner in active_runners)
    duplicate_current = sum(1 for count in current_counts.values() if count > 1)

    if match_pct >= 98 and duplicate_profile_compact == 0:
        recommendation = "KEEP normalized_runner matching; compact fallback is not required for current active runners."
    elif match_pct >= 98:
        recommendation = "IMPROVE normalisation cautiously; match rate is high but duplicate profile key risk remains."
    else:
        recommendation = "BUILD HORSE IDENTITY BRIDGE if this source remains active; match rate or duplicate risk is below production target."

    summary = [
        "EDGEIQ RUNNER PROFILE MATCH AUDIT V1",
        "",
        "Candidate current runner sources scanned:",
        *scanned_lines,
        "",
        f"Selected likely active runner source: {active_source}",
        f"Total current runners: {total}",
        f"Matched runners: {matched}",
        f"Match percentage: {match_pct}%",
        f"Unmatched runners: {', '.join(unmatched) if unmatched else 'NONE'}",
        "",
        "Match methods:",
        *(f"- {method}: {count}" for method, count in method_counts.items()),
        "",
        "Top failure reasons:",
        *(f"- {reason}: {count}" for reason, count in reason_counts.items()),
        *(["- NONE"] if not reason_counts else []),
        "",
        f"Duplicate normalised profile keys count: {duplicate_profile_exact}",
        f"Duplicate compact profile keys count: {duplicate_profile_compact}",
        f"Duplicate current runner keys count: {duplicate_current}",
        "",
        f"Recommendation: {recommendation}",
        "",
        "Direct check notes:",
        "- KING TAGALOA should match the profile feed by runner/latest_runner_name exact normalisation.",
        "- If the UI still shows empty for KING TAGALOA, check browser fetch path/cache rather than source coverage.",
    ]

    OUTPUT_SUMMARY.write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
