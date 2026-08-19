from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STEP_NAME = "STEP201 Repository Census Quality Profile"

WEAK_KEYWORDS = {
    "active",
    "benchmark",
    "canonical",
    "current",
    "fact table",
    "fact_table",
    "form guide",
    "form_guide",
    "historical performance",
    "identity",
    "momentum",
    "normalisation",
    "normalised",
    "normalization",
    "normalized",
    "pace",
    "performance index",
    "production",
    "provenance",
    "rated",
    "rating",
    "ratings",
    "recent form",
    "sectional",
    "source evidence",
    "tempo",
    "warehouse",
}

STRONG_KEYWORDS = {
    "early speed",
    "early-speed",
    "early_speed",
    "edgeiq performance index",
    "epi",
    "form momentum",
    "form_momentum",
    "late speed",
    "late-speed",
    "late_speed",
    "lengths v standard",
    "lengths vs standard",
    "lengths_v_standard",
    "lengths_vs_standard",
    "lvs",
    "performance fact",
    "performance intelligence",
    "performance_fact",
    "performance-intelligence",
    "performance_intelligence",
    "race shape",
    "race-shape",
    "race_shape",
    "standard time",
    "standard-time",
    "standard_time",
}

SUSPECT_PATH_TOKENS = {
    "archive",
    "backup",
    "backups",
    "candidate",
    "checkpoint",
    "coverage",
    "fixture",
    "fixtures",
    "generated",
    "history",
    "legacy",
    "logs",
    "node_modules",
    "output",
    "outputs",
    "public/data",
    "snapshot",
    "snapshots",
    "temp",
    "tmp",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile the quality and scope of the STEP201 census."
    )
    parser.add_argument(
        "--repository-root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--census",
        default=(
            "docs/performance-intelligence-discovery/"
            "STEP201_REPOSITORY_CENSUS.csv"
        ),
        help="STEP201 census CSV path relative to the repository.",
    )
    parser.add_argument(
        "--output-root",
        default="docs/performance-intelligence-discovery",
        help="Directory for profile outputs.",
    )
    return parser.parse_args()


def split_values(value: str) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").split(";")
        if item.strip()
    ]


def top_level(path_text: str, depth: int) -> str:
    parts = Path(path_text).parts
    if not parts:
        return "<root>"
    return "/".join(parts[:depth])


def classify_strength(row: dict[str, str]) -> str:
    keywords = {
        value.lower()
        for value in split_values(row.get("matched_keywords", ""))
    }

    path_text = row.get("repository_path", "").lower()

    if keywords & STRONG_KEYWORDS:
        return "STRONG"

    if any(
        token in path_text
        for token in (
            "performance-intelligence",
            "performance_intelligence",
            "standard-time",
            "standard_time",
            "lengths-v-standard",
            "lengths_v_standard",
            "race-shape",
            "race_shape",
            "form-momentum",
            "form_momentum",
        )
    ):
        return "STRONG_PATH"

    if keywords and keywords.issubset(WEAK_KEYWORDS):
        return "WEAK_ONLY"

    if len(keywords) >= 2:
        return "MULTI_SIGNAL"

    if len(keywords) == 1:
        return "SINGLE_SIGNAL"

    return "PATH_ONLY"


def suspect_path_tokens(path_text: str) -> list[str]:
    lowered = path_text.lower().replace("\\", "/")
    return sorted(token for token in SUSPECT_PATH_TOKENS if token in lowered)


def count_domains(rows: list[dict[str, str]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for domain in split_values(row.get("domain", "")):
            counter[domain] += 1
    return counter


def serialise_counter(counter: Counter[str], limit: int = 100) -> list[dict[str, Any]]:
    return [
        {"value": key, "count": value}
        for key, value in counter.most_common(limit)
    ]


def markdown_table(
    title: str,
    header_name: str,
    counter: Counter[str],
    limit: int = 30,
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"| {header_name} | Count |",
        "|---|---:|",
    ]

    for key, value in counter.most_common(limit):
        safe_key = str(key).replace("|", "\\|")
        lines.append(f"| {safe_key} | {value:,} |")

    lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    root = Path(args.repository_root).resolve()
    census_path = (root / args.census).resolve()
    output_root = (root / args.output_root).resolve()

    if not census_path.exists():
        print(f"ERROR: Census not found: {census_path}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)

    with census_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        print("ERROR: Census contains no records.", file=sys.stderr)
        return 3

    strength_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    root_counts: Counter[str] = Counter()
    second_level_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()
    keyword_combo_counts: Counter[str] = Counter()
    domain_combo_counts: Counter[str] = Counter()
    suspect_token_counts: Counter[str] = Counter()
    name_counts: Counter[str] = Counter()

    weak_rows: list[dict[str, str]] = []
    suspect_rows: list[dict[str, str]] = []

    for row in rows:
        repository_path = row.get("repository_path", "")
        keywords = split_values(row.get("matched_keywords", ""))
        strength = classify_strength(row)
        suspects = suspect_path_tokens(repository_path)

        strength_counts[strength] += 1
        type_counts[row.get("asset_type", "Unknown")] += 1
        status_counts[row.get("status", "Unknown")] += 1
        root_counts[top_level(repository_path, 1)] += 1
        second_level_counts[top_level(repository_path, 2)] += 1
        extension_counts[row.get("extension", "<none>")] += 1
        name_counts[row.get("name", "<blank>").lower()] += 1

        keyword_combo = "; ".join(sorted(keywords)) if keywords else "<none>"
        keyword_combo_counts[keyword_combo] += 1

        for keyword in keywords:
            keyword_counts[keyword.lower()] += 1

        domain_combo_counts[row.get("domain", "Unknown")] += 1

        for token in suspects:
            suspect_token_counts[token] += 1

        profiled = dict(row)
        profiled["signal_strength"] = strength
        profiled["suspect_path_tokens"] = "; ".join(suspects)

        if strength in {"WEAK_ONLY", "SINGLE_SIGNAL", "PATH_ONLY"}:
            weak_rows.append(profiled)

        if suspects:
            suspect_rows.append(profiled)

    duplicate_name_groups = sum(1 for count in name_counts.values() if count > 1)
    duplicate_name_rows = sum(count for count in name_counts.values() if count > 1)

    profile_csv = output_root / "STEP201_QUALITY_PROFILE_CANDIDATES.csv"
    profile_json = output_root / "STEP201_QUALITY_PROFILE.json"
    profile_md = output_root / "STEP201_QUALITY_PROFILE.md"

    candidate_fields = list(rows[0].keys()) + [
        "signal_strength",
        "suspect_path_tokens",
    ]

    combined_candidates: dict[str, dict[str, str]] = {}

    for row in weak_rows + suspect_rows:
        combined_candidates[row["repository_path"]] = row

    ordered_candidates = sorted(
        combined_candidates.values(),
        key=lambda row: (
            row["signal_strength"],
            row["repository_path"],
        ),
    )

    with profile_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=candidate_fields)
        writer.writeheader()
        writer.writerows(ordered_candidates)

    payload = {
        "step": STEP_NAME,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "census_path": str(census_path),
        "total_assets": len(rows),
        "weak_candidate_assets": len(weak_rows),
        "suspect_path_assets": len(suspect_rows),
        "combined_review_candidates": len(ordered_candidates),
        "duplicate_name_groups": duplicate_name_groups,
        "duplicate_name_rows": duplicate_name_rows,
        "signal_strength": serialise_counter(strength_counts),
        "asset_types": serialise_counter(type_counts),
        "statuses": serialise_counter(status_counts),
        "top_level_paths": serialise_counter(root_counts),
        "second_level_paths": serialise_counter(second_level_counts),
        "extensions": serialise_counter(extension_counts),
        "keywords": serialise_counter(keyword_counts),
        "keyword_combinations": serialise_counter(keyword_combo_counts),
        "domain_combinations": serialise_counter(domain_combo_counts),
        "suspect_path_tokens": serialise_counter(suspect_token_counts),
    }

    profile_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    weak_percentage = (len(weak_rows) / len(rows)) * 100
    suspect_percentage = (len(suspect_rows) / len(rows)) * 100
    strong_total = (
        strength_counts["STRONG"]
        + strength_counts["STRONG_PATH"]
        + strength_counts["MULTI_SIGNAL"]
    )
    strong_percentage = (strong_total / len(rows)) * 100

    lines = [
        f"# {STEP_NAME}",
        "",
        f"- Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"- Census assets profiled: {len(rows):,}",
        f"- Strong or multi-signal assets: {strong_total:,} ({strong_percentage:.2f}%)",
        f"- Weak review candidates: {len(weak_rows):,} ({weak_percentage:.2f}%)",
        f"- Assets under suspect paths: {len(suspect_rows):,} ({suspect_percentage:.2f}%)",
        f"- Combined review candidates: {len(ordered_candidates):,}",
        f"- Duplicate filename groups: {duplicate_name_groups:,}",
        f"- Rows belonging to duplicate filename groups: {duplicate_name_rows:,}",
        "",
        "## Interpretation",
        "",
        "This profile does not delete or reclassify any census record.",
        "It identifies where the first-pass census may be over-inclusive.",
        "",
    ]

    lines.extend(
        markdown_table(
            "Signal Strength",
            "Classification",
            strength_counts,
            20,
        )
    )
    lines.extend(markdown_table("Top-Level Paths", "Path", root_counts, 40))
    lines.extend(
        markdown_table(
            "Second-Level Paths",
            "Path",
            second_level_counts,
            50,
        )
    )
    lines.extend(markdown_table("Asset Types", "Type", type_counts, 30))
    lines.extend(markdown_table("Statuses", "Status", status_counts, 20))
    lines.extend(markdown_table("Extensions", "Extension", extension_counts, 30))
    lines.extend(markdown_table("Matched Keywords", "Keyword", keyword_counts, 50))
    lines.extend(
        markdown_table(
            "Keyword Combinations",
            "Combination",
            keyword_combo_counts,
            50,
        )
    )
    lines.extend(
        markdown_table(
            "Domain Combinations",
            "Domain Combination",
            domain_combo_counts,
            50,
        )
    )
    lines.extend(
        markdown_table(
            "Suspect Path Tokens",
            "Path Token",
            suspect_token_counts,
            30,
        )
    )

    profile_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"STEP: {STEP_NAME}")
    print(f"CENSUS ASSETS: {len(rows):,}")
    print(
        "STRONG OR MULTI-SIGNAL: "
        f"{strong_total:,} ({strong_percentage:.2f}%)"
    )
    print(
        f"WEAK REVIEW CANDIDATES: "
        f"{len(weak_rows):,} ({weak_percentage:.2f}%)"
    )
    print(
        f"SUSPECT PATH ASSETS: "
        f"{len(suspect_rows):,} ({suspect_percentage:.2f}%)"
    )
    print(f"COMBINED REVIEW CANDIDATES: {len(ordered_candidates):,}")
    print(f"DUPLICATE NAME GROUPS: {duplicate_name_groups:,}")
    print(f"DUPLICATE NAME ROWS: {duplicate_name_rows:,}")
    print(f"CREATED: {profile_csv}")
    print(f"CREATED: {profile_json}")
    print(f"CREATED: {profile_md}")
    print("QUALITY PROFILE STATUS: PASS")

    print("")
    print("TOP SIGNAL CLASSIFICATIONS")
    for key, value in strength_counts.most_common():
        print(f"{key}: {value:,}")

    print("")
    print("TOP 20 ROOT PATHS")
    for key, value in root_counts.most_common(20):
        print(f"{key}: {value:,}")

    print("")
    print("TOP 20 MATCHED KEYWORDS")
    for key, value in keyword_counts.most_common(20):
        print(f"{key}: {value:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
