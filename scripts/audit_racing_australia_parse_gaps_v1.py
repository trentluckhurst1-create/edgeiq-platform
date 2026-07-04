from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RA_RAW = DATA / "racing_australia_sandown_2026_05_31_raw_results_v1.csv"
RA_NORMALISED = DATA / "racing_australia_sandown_2026_05_31_normalised_results_v1.csv"
PRICE_TRUTH = DATA / "edgeiq_price_truth_history_v1.csv"

DETAIL_OUT = DATA / "racing_australia_parse_gaps_v1.csv"
SUMMARY_OUT = DATA / "racing_australia_parse_gaps_v1_summary.csv"

TARGET_DATE = "2026-05-31"
TARGET_TRACK = "SANDOWN LAKESIDE"
TARGET_RACES = {str(number) for number in range(1, 9)}
SPECIFIC_HORSES = {
    "WINTERNIGHTS",
    "POUNDING",
    "ROSAAOTEAROA",
    "PRINCESSONPALM",
}

DETAIL_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "horse",
    "horse_key",
    "audit_subject",
    "status",
    "exists_in_price_truth",
    "exists_in_raw_ra_results",
    "exists_in_normalised_results",
    "lost_during_normalisation",
    "failed_matching",
    "never_existed_in_ra_raw_results",
    "specific_runner_audit",
    "raw_ra_horse",
    "normalised_ra_horse",
    "fuzzy_match_candidates",
    "best_fuzzy_score",
    "bracketed_suffix_difference",
    "bracketed_suffix_candidate",
    "country_suffix_difference",
    "country_suffix_candidate",
    "race_expected_count",
    "race_raw_count",
    "race_normalised_count",
    "race_missing_count",
    "notes",
]

SUMMARY_COLUMNS = ["section", "metric", "value", "source_path", "notes", "built_at"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "-", "nan", "none", "null", "undefined", "n/a"}:
        return ""
    return text


def normalise_text(value: object, *, remove_brackets: bool = True) -> str:
    text = clean(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    if remove_brackets:
        text = re.sub(r"\([^)]*\)", " ", text)
    text = text.replace("&", " AND ")
    text = re.sub(r"['`]", "", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def horse_key(value: object) -> str:
    return normalise_text(value).replace(" ", "")


def horse_base(value: object) -> str:
    return horse_key(value)


def horse_key_with_country(value: object) -> str:
    return normalise_text(value, remove_brackets=False).replace(" ", "")


def country_suffix(value: object) -> str:
    match = re.search(r"\(([A-Z]{2,3})\)", clean(value).upper())
    return match.group(1) if match else ""


def normalise_track(value: object) -> str:
    track = normalise_text(value)
    track = re.sub(r"\bSPORTS\s*BET\b", "SPORTSBET", track)
    track = re.sub(r"\bVIC\b|\bPROFESSIONAL\b|\bMETRO\b|\bTAB\b|\bMEETING\b", " ", track)
    track = re.sub(r"\bMELBOURNE\b|\bRACING\b|\bCLUB\b", " ", track)
    track = re.sub(r"\s+", " ", track).strip()
    if "SANDOWN" in track and "LAKESIDE" in track:
        return TARGET_TRACK
    if track.startswith("SPORTSBET "):
        track = track.replace("SPORTSBET ", "", 1)
    return track


def clean_race_no(value: object) -> str:
    match = re.search(r"\d+", clean(value))
    return str(int(match.group(0))) if match else ""


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def key_for(row: dict[str, str], horse_column: str, key_column: str = "") -> str:
    return "|".join(
        [
            clean(row.get("race_date")),
            normalise_track(row.get("track")),
            clean_race_no(row.get("race_no")),
            horse_key(row.get(key_column)) if key_column and clean(row.get(key_column)) else horse_key(row.get(horse_column)),
        ]
    )


def load_truth_targets() -> dict[str, dict[str, str]]:
    columns, rows = read_csv(PRICE_TRUTH)
    required = {"race_date", "track", "race_no", "horse", "horse_key"}
    missing = sorted(required.difference(columns))
    if missing:
        raise ValueError(f"{PRICE_TRUTH} missing required columns: {missing}")

    targets: dict[str, dict[str, str]] = {}
    for row in rows:
        race_date = clean(row.get("race_date"))
        track = normalise_track(row.get("track"))
        race_no = clean_race_no(row.get("race_no"))
        if race_date != TARGET_DATE or track != TARGET_TRACK or race_no not in TARGET_RACES:
            continue
        key = key_for(
            {
                "race_date": race_date,
                "track": track,
                "race_no": race_no,
                "horse": clean(row.get("horse")),
                "horse_key": clean(row.get("horse_key")),
            },
            "horse",
            "horse_key",
        )
        targets[key] = {
            "race_date": race_date,
            "track": TARGET_TRACK,
            "race_no": race_no,
            "horse": clean(row.get("horse")),
            "horse_key": horse_key(row.get("horse_key")) or horse_key(row.get("horse")),
        }
    return targets


def load_raw_rows() -> dict[str, dict[str, str]]:
    _, rows = read_csv(RA_RAW)
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        key = key_for(row, "horse_raw")
        output[key] = row
    return output


def load_normalised_rows() -> dict[str, dict[str, str]]:
    _, rows = read_csv(RA_NORMALISED)
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        key = key_for(row, "horse", "horse_key")
        output[key] = row
    return output


def group_by_race(rows: dict[str, dict[str, str]], horse_column: str, key_column: str = "") -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows.values():
        race_no = clean_race_no(row.get("race_no"))
        grouped[race_no].append(row)
    return grouped


def fuzzy_candidates(target: dict[str, str], raw_race_rows: list[dict[str, str]]) -> tuple[str, float]:
    target_name = clean(target.get("horse"))
    target_key = horse_base(target_name)
    scored = []
    for row in raw_race_rows:
        candidate_name = clean(row.get("horse_raw"))
        candidate_key = horse_base(candidate_name)
        score = difflib.SequenceMatcher(None, target_key, candidate_key).ratio()
        scored.append((score, candidate_name))
    scored.sort(reverse=True)
    top = scored[:5]
    formatted = " | ".join(f"{name}:{score:.3f}" for score, name in top)
    best = top[0][0] if top else 0.0
    return formatted, best


def suffix_candidate(target: dict[str, str], raw_race_rows: list[dict[str, str]]) -> tuple[str, str, str, str]:
    target_name = clean(target.get("horse"))
    target_base = horse_base(target_name)
    target_country = country_suffix(target_name)
    bracket_candidate = ""
    country_candidate = ""
    bracket_diff = "FALSE"
    country_diff = "FALSE"
    for row in raw_race_rows:
        raw_name = clean(row.get("horse_raw"))
        raw_base = horse_base(raw_name)
        raw_country = country_suffix(raw_name)
        if raw_base == target_base and raw_name != target_name:
            bracket_diff = "TRUE"
            bracket_candidate = raw_name
        if raw_base == target_base and raw_country != target_country:
            country_diff = "TRUE"
            country_candidate = raw_name
    return bracket_diff, bracket_candidate, country_diff, country_candidate


def build_detail_rows() -> tuple[list[dict[str, object]], dict[str, int], dict[str, int], dict[str, int]]:
    truth = load_truth_targets()
    raw = load_raw_rows()
    normalised = load_normalised_rows()
    raw_by_race = group_by_race(raw, "horse_raw")

    truth_keys = set(truth)
    raw_keys = set(raw)
    normalised_keys = set(normalised)
    unmatched_truth = sorted(truth_keys - normalised_keys, key=lambda key: (int(truth[key]["race_no"]), truth[key]["horse_key"]))
    lost_normalisation = sorted(raw_keys - normalised_keys)

    expected_counts = Counter(row["race_no"] for row in truth.values())
    raw_counts = Counter(clean_race_no(row.get("race_no")) for row in raw.values())
    normalised_counts = Counter(clean_race_no(row.get("race_no")) for row in normalised.values())

    detail_rows: list[dict[str, object]] = []
    for key in unmatched_truth:
        target = truth[key]
        race_no = target["race_no"]
        raw_exists = key in raw_keys
        normalised_exists = key in normalised_keys
        lost = raw_exists and not normalised_exists
        candidates, best_score = fuzzy_candidates(target, raw_by_race.get(race_no, []))
        bracket_diff, bracket_candidate, country_diff, country_candidate = suffix_candidate(target, raw_by_race.get(race_no, []))
        matching_gap = (not raw_exists and best_score >= 0.92) or bracket_diff == "TRUE" or country_diff == "TRUE"

        if lost:
            status = "PARSE_GAP_FOUND"
            notes = "Runner exists in RA raw-results CSV but not in the normalised results file."
        elif matching_gap:
            status = "MATCHING_GAP_FOUND"
            notes = "Runner did not exact-match normalised results but has a strong same-race fuzzy/suffix candidate."
        else:
            status = "NO_GAP_FOUND"
            notes = "Runner exists in price truth but not in RA raw-results CSV or RA normalised results; no parser/matching gap found in available CSV outputs."

        detail_rows.append(
            {
                "race_date": target["race_date"],
                "track": target["track"],
                "race_no": race_no,
                "horse": target["horse"],
                "horse_key": target["horse_key"],
                "audit_subject": "UNMATCHED_TRUTH_RUNNER",
                "status": status,
                "exists_in_price_truth": "TRUE",
                "exists_in_raw_ra_results": "TRUE" if raw_exists else "FALSE",
                "exists_in_normalised_results": "TRUE" if normalised_exists else "FALSE",
                "lost_during_normalisation": "TRUE" if lost else "FALSE",
                "failed_matching": "TRUE" if matching_gap else "FALSE",
                "never_existed_in_ra_raw_results": "FALSE" if raw_exists else "TRUE",
                "specific_runner_audit": "TRUE" if target["horse_key"] in SPECIFIC_HORSES else "FALSE",
                "raw_ra_horse": clean(raw.get(key, {}).get("horse_raw")),
                "normalised_ra_horse": clean(normalised.get(key, {}).get("horse")),
                "fuzzy_match_candidates": candidates,
                "best_fuzzy_score": f"{best_score:.3f}",
                "bracketed_suffix_difference": bracket_diff,
                "bracketed_suffix_candidate": bracket_candidate,
                "country_suffix_difference": country_diff,
                "country_suffix_candidate": country_candidate,
                "race_expected_count": expected_counts.get(race_no, 0),
                "race_raw_count": raw_counts.get(race_no, 0),
                "race_normalised_count": normalised_counts.get(race_no, 0),
                "race_missing_count": expected_counts.get(race_no, 0) - normalised_counts.get(race_no, 0),
                "notes": notes,
            }
        )

    for key in lost_normalisation:
        raw_row = raw[key]
        race_no = clean_race_no(raw_row.get("race_no"))
        detail_rows.append(
            {
                "race_date": clean(raw_row.get("race_date")),
                "track": normalise_track(raw_row.get("track")),
                "race_no": race_no,
                "horse": clean(raw_row.get("horse_raw")),
                "horse_key": horse_key(raw_row.get("horse_raw")),
                "audit_subject": "RAW_ROW_LOST_DURING_NORMALISATION",
                "status": "PARSE_GAP_FOUND",
                "exists_in_price_truth": "TRUE" if key in truth_keys else "FALSE",
                "exists_in_raw_ra_results": "TRUE",
                "exists_in_normalised_results": "FALSE",
                "lost_during_normalisation": "TRUE",
                "failed_matching": "FALSE",
                "never_existed_in_ra_raw_results": "FALSE",
                "specific_runner_audit": "TRUE" if horse_key(raw_row.get("horse_raw")) in SPECIFIC_HORSES else "FALSE",
                "raw_ra_horse": clean(raw_row.get("horse_raw")),
                "normalised_ra_horse": "",
                "fuzzy_match_candidates": "",
                "best_fuzzy_score": "",
                "bracketed_suffix_difference": "",
                "bracketed_suffix_candidate": "",
                "country_suffix_difference": "",
                "country_suffix_candidate": "",
                "race_expected_count": expected_counts.get(race_no, 0),
                "race_raw_count": raw_counts.get(race_no, 0),
                "race_normalised_count": normalised_counts.get(race_no, 0),
                "race_missing_count": expected_counts.get(race_no, 0) - normalised_counts.get(race_no, 0),
                "notes": "RA raw-results CSV row did not survive into normalised results.",
            }
        )

    return detail_rows, expected_counts, raw_counts, normalised_counts


def summary_row(section: str, metric: str, value: object, source_path: Path | str = "", notes: str = "") -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "source_path": str(source_path),
        "notes": notes,
        "built_at": now_utc(),
    }


def build_summary(detail_rows: list[dict[str, object]], expected_counts: dict[str, int], raw_counts: dict[str, int], normalised_counts: dict[str, int]) -> list[dict[str, object]]:
    status_counts = Counter(str(row["status"]) for row in detail_rows)
    subject_counts = Counter(str(row["audit_subject"]) for row in detail_rows)
    unmatched_rows = [row for row in detail_rows if row["audit_subject"] == "UNMATCHED_TRUTH_RUNNER"]
    lost_rows = [row for row in detail_rows if row["audit_subject"] == "RAW_ROW_LOST_DURING_NORMALISATION"]
    fuzzy_rows = [row for row in unmatched_rows if str(row["failed_matching"]) == "TRUE"]
    bracket_rows = [row for row in unmatched_rows if str(row["bracketed_suffix_difference"]) == "TRUE"]
    country_rows = [row for row in unmatched_rows if str(row["country_suffix_difference"]) == "TRUE"]

    raw_runner_count = sum(raw_counts.values())
    normalised_runner_count = sum(normalised_counts.values())
    expected_runner_count = sum(expected_counts.values())

    if lost_rows:
        overall_status = "PARSE_GAP_FOUND"
    elif fuzzy_rows or bracket_rows or country_rows:
        overall_status = "MATCHING_GAP_FOUND"
    else:
        overall_status = "NO_GAP_FOUND"

    rows = [
        summary_row("input", "raw_results_source", RA_RAW.exists(), RA_RAW),
        summary_row("input", "normalised_results_source", RA_NORMALISED.exists(), RA_NORMALISED),
        summary_row("input", "price_truth_source", PRICE_TRUTH.exists(), PRICE_TRUTH),
        summary_row("counts", "expected_truth_runners_deduped", expected_runner_count, PRICE_TRUTH),
        summary_row("counts", "runners_in_raw_results", raw_runner_count, RA_RAW),
        summary_row("counts", "runners_in_normalised_results", normalised_runner_count, RA_NORMALISED),
        summary_row("counts", "runners_lost_during_normalisation", len(lost_rows), DETAIL_OUT),
        summary_row("counts", "unmatched_truth_runners", len(unmatched_rows), DETAIL_OUT),
        summary_row("counts", "fuzzy_match_candidates", len(fuzzy_rows), DETAIL_OUT, "Same-race candidates with score >= 0.92 or suffix-only candidate."),
        summary_row("counts", "bracketed_suffix_differences", len(bracket_rows), DETAIL_OUT),
        summary_row("counts", "country_suffix_differences", len(country_rows), DETAIL_OUT),
        summary_row("status", "overall_status", overall_status, DETAIL_OUT),
        summary_row("scope", "raw_source_scope", "RA raw-results CSV generated by prior parser", RA_RAW, "This audit does not re-fetch the full HTML page; it audits the available raw-results CSV."),
    ]

    for race_no in sorted(TARGET_RACES, key=int):
        expected = expected_counts.get(race_no, 0)
        raw = raw_counts.get(race_no, 0)
        normalised = normalised_counts.get(race_no, 0)
        rows.append(summary_row("race_expected_count", f"R{race_no}", expected, PRICE_TRUTH))
        rows.append(summary_row("race_raw_count", f"R{race_no}", raw, RA_RAW))
        rows.append(summary_row("race_normalised_count", f"R{race_no}", normalised, RA_NORMALISED))
        rows.append(summary_row("race_missing_count", f"R{race_no}", expected - normalised, DETAIL_OUT))

    for status, count in sorted(status_counts.items()):
        rows.append(summary_row("status_count", status, count, DETAIL_OUT))
    for subject, count in sorted(subject_counts.items()):
        rows.append(summary_row("subject_count", subject, count, DETAIL_OUT))

    for horse_key_value in sorted(SPECIFIC_HORSES):
        matches = [row for row in detail_rows if str(row["horse_key"]) == horse_key_value]
        if matches:
            row = matches[0]
            rows.append(
                summary_row(
                    "specific_runner",
                    str(row["horse"]),
                    str(row["status"]),
                    DETAIL_OUT,
                    f"raw={row['exists_in_raw_ra_results']}; normalised={row['exists_in_normalised_results']}; discarded={row['lost_during_normalisation']}; failed_matching={row['failed_matching']}; never_raw={row['never_existed_in_ra_raw_results']}",
                )
            )
        else:
            rows.append(summary_row("specific_runner", horse_key_value, "NOT_IN_UNMATCHED_AUDIT", DETAIL_OUT))
    return rows


def main() -> None:
    detail_rows, expected_counts, raw_counts, normalised_counts = build_detail_rows()
    summary_rows = build_summary(detail_rows, expected_counts, raw_counts, normalised_counts)

    write_csv(DETAIL_OUT, detail_rows, DETAIL_COLUMNS)
    write_csv(SUMMARY_OUT, summary_rows, SUMMARY_COLUMNS)

    print("=" * 96)
    print("RACING AUSTRALIA PARSE GAPS AUDIT V1 - READ ONLY")
    print("=" * 96)
    for row in summary_rows:
        if row["section"] in {"counts", "status", "specific_runner"}:
            print(f"{row['section']},{row['metric']},{row['value']},{row['notes']}")
    print(f"wrote: {DETAIL_OUT}")
    print(f"wrote: {SUMMARY_OUT}")
    print("=" * 96)


if __name__ == "__main__":
    main()
