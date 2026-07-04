from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
PROFILES = DATA / "edgeiq_sectional_profiles_v2.csv"

OUT = DATA / "edgeiq_live_sectional_intelligence_v1.csv"
AUDIT_OUT = DATA / "edgeiq_live_sectional_intelligence_v1_audit.csv"

COUNTRY_SUFFIXES = ("NZ", "IRE", "GB", "FR", "USA", "JPN", "GER", "SAF")

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "runner_number",
    "barrier",
    "jockey",
    "trainer",
    "edgeiq_price",
    "market_price",
    "sectional_profile_found",
    "runs_with_sectionals",
    "profile_depth_status",
    "sectional_archetype",
    "sectional_evidence_type",
    "avg_early_speed",
    "avg_mid_speed",
    "avg_late_speed",
    "avg_peak_speed",
    "avg_speed",
    "avg_early_split_time",
    "avg_mid_split_time",
    "avg_late_split_time",
    "avg_closing_rank",
    "avg_early_rank",
    "avg_late_vs_early_delta",
    "avg_split_consistency_score",
    "sectional_intelligence_status",
    "sectional_comment",
]

AUDIT_COLUMNS = [
    "live_rows_loaded",
    "sectional_profiles_loaded",
    "live_unique_horses",
    "matched_profiles",
    "unmatched_profiles",
    "coverage_pct",
    "sample_too_small",
    "early_profiles",
    "strong_early_profiles",
    "dna_ready_profiles",
    "final_status",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"} else re.sub(r"\s+", " ", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def canonical_horse_key(value: Any) -> str:
    raw = clean(value).upper()
    if not raw:
        return ""
    suffix_pattern = "|".join(COUNTRY_SUFFIXES)
    raw = re.sub(rf"\s*\(({suffix_pattern})\)\s*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(rf"\s+({suffix_pattern})\s*$", "", raw, flags=re.IGNORECASE)
    raw = re.sub(rf"({suffix_pattern})$", "", raw, flags=re.IGNORECASE)
    return re.sub(r"[^A-Z0-9]+", "", raw)


def first(row: dict[str, str], columns: tuple[str, ...]) -> str:
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def status_comment(status: str) -> str:
    return {
        "NO_PROFILE": "No sectional profile yet",
        "SAMPLE_TOO_SMALL": "Limited sectional sample",
        "EARLY_PROFILE": "Early sectional profile available",
        "STRONG_EARLY_PROFILE": "Strong early sectional profile",
        "DNA_READY": "DNA-ready sectional profile",
    }.get(status, "No sectional profile yet")


def profile_lookup(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        horse_key = canonical_horse_key(row.get("horse_key") or row.get("horse_name"))
        if horse_key:
            lookup[horse_key] = row
    return lookup


def build_rows(live_rows: list[dict[str, str]], profiles: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for live in live_rows:
        horse_name = first(live, ("horse", "horse_name", "runner"))
        horse_key = canonical_horse_key(first(live, ("horse_key",)) or horse_name)
        profile = profiles.get(horse_key)
        found = profile is not None
        status = clean(profile.get("profile_depth_status")) if profile else "NO_PROFILE"
        if not status:
            status = "NO_PROFILE"
        output.append(
            {
                "meeting_date": first(live, ("meeting_date", "race_date", "date")),
                "track": first(live, ("track", "venue")),
                "race_no": first(live, ("race_no", "race_number")),
                "horse_name": horse_name,
                "horse_key": horse_key,
                "runner_number": first(live, ("runner_number", "horse_no", "saddlecloth")),
                "barrier": first(live, ("barrier", "bar")),
                "jockey": first(live, ("jockey",)),
                "trainer": first(live, ("trainer",)),
                "edgeiq_price": first(live, ("ui_fair_price", "rated_price", "edgeiq_price")),
                "market_price": first(live, ("market_price", "sportsbet_price", "live_price", "ui_price")),
                "sectional_profile_found": "TRUE" if found else "FALSE",
                "runs_with_sectionals": clean(profile.get("runs_with_sectionals")) if profile else "",
                "profile_depth_status": status if found else "",
                "sectional_archetype": clean(profile.get("sectional_archetype")) if profile else "",
                "sectional_evidence_type": clean(profile.get("sectional_evidence_type")) if profile else "",
                "avg_early_speed": clean(profile.get("avg_early_speed")) if profile else "",
                "avg_mid_speed": clean(profile.get("avg_mid_speed")) if profile else "",
                "avg_late_speed": clean(profile.get("avg_late_speed")) if profile else "",
                "avg_peak_speed": clean(profile.get("avg_peak_speed")) if profile else "",
                "avg_speed": clean(profile.get("avg_speed")) if profile else "",
                "avg_early_split_time": clean(profile.get("avg_early_split_time")) if profile else "",
                "avg_mid_split_time": clean(profile.get("avg_mid_split_time")) if profile else "",
                "avg_late_split_time": clean(profile.get("avg_late_split_time")) if profile else "",
                "avg_closing_rank": clean(profile.get("avg_closing_rank")) if profile else "",
                "avg_early_rank": clean(profile.get("avg_early_rank")) if profile else "",
                "avg_late_vs_early_delta": clean(profile.get("avg_late_vs_early_delta")) if profile else "",
                "avg_split_consistency_score": clean(profile.get("avg_split_consistency_score")) if profile else "",
                "sectional_intelligence_status": status if found else "NO_PROFILE",
                "sectional_comment": status_comment(status if found else "NO_PROFILE"),
            }
        )
    return output


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return f"{(numerator / denominator) * 100:.2f}".rstrip("0").rstrip(".")


def main() -> None:
    live_rows = read_csv(LIVE_FEED)
    profile_rows = read_csv(PROFILES)
    profiles = profile_lookup(profile_rows)
    output = build_rows(live_rows, profiles) if live_rows and profile_rows else []
    status_counts = Counter(clean(row.get("sectional_intelligence_status")) for row in output)
    live_unique_horses = len({canonical_horse_key(row.get("horse_key") or row.get("horse")) for row in live_rows if canonical_horse_key(row.get("horse_key") or row.get("horse"))})
    matched = sum(1 for row in output if clean(row.get("sectional_profile_found")) == "TRUE")
    unmatched = len(output) - matched
    final_status = "LIVE_SECTIONAL_INTELLIGENCE_BUILT"
    if not live_rows:
        final_status = "NO_LIVE_FEED_FOUND"
    elif not profile_rows:
        final_status = "NO_SECTIONAL_PROFILES_FOUND"

    audit = [
        {
            "live_rows_loaded": len(live_rows),
            "sectional_profiles_loaded": len(profile_rows),
            "live_unique_horses": live_unique_horses,
            "matched_profiles": matched,
            "unmatched_profiles": unmatched,
            "coverage_pct": pct(matched, len(output)),
            "sample_too_small": status_counts.get("SAMPLE_TOO_SMALL", 0),
            "early_profiles": status_counts.get("EARLY_PROFILE", 0),
            "strong_early_profiles": status_counts.get("STRONG_EARLY_PROFILE", 0),
            "dna_ready_profiles": status_counts.get("DNA_READY", 0),
            "final_status": final_status,
        }
    ]

    write_csv(OUT, output, OUTPUT_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    row = audit[0]
    print("EDGEiQ live sectional intelligence V1 built")
    print(f"live_rows_loaded={row['live_rows_loaded']}")
    print(f"sectional_profiles_loaded={row['sectional_profiles_loaded']}")
    print(f"live_unique_horses={row['live_unique_horses']}")
    print(f"matched_profiles={row['matched_profiles']}")
    print(f"unmatched_profiles={row['unmatched_profiles']}")
    print(f"coverage_pct={row['coverage_pct']}")
    print(f"final_status={row['final_status']}")


if __name__ == "__main__":
    main()
