import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
SCRIPTS = ROOT / "scripts"
FORM_FEED = ROOT / "public" / "data" / "edgeiq_form_guide_enriched_v2.json"
REPORT = ROOT / "docs" / "full-product-implementation" / "FORM_GUIDE_HISTORICAL_EPI_SOURCE_AND_BUILDER_AUDIT.txt"

TARGET_SOURCE_NAMES = [
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    "run_ratings_v1.csv",
    "edgeiq_speed_master_v1.csv",
    "edgeiq_form_sectional_profile_feed_v1.csv",
]

ASSIGNMENT_TERMS = [
    '"historicalEpi"',
    "'historicalEpi'",
    '"raceRating"',
    "'raceRating'",
    '"historicalSpeedRating"',
    "'historicalSpeedRating'",
    '"sectionalIndices"',
    "'sectionalIndices'",
    "edgeiq_form_guide_enriched_v2.json",
]

def clean(value):
    return str(value or "").strip()

def normalise(value):
    return re.sub(r"[^A-Z0-9]+", "", clean(value).upper())

def number_text(value):
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text)
        return str(int(number)) if number.is_integer() else str(number)
    except ValueError:
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return text
        number = float(match.group(0))
        return str(int(number)) if number.is_integer() else str(number)

def runner_key(value):
    text = normalise(value)
    for suffix in ["AUS", "NZ", "GB", "IRE", "USA", "FR", "JPN"]:
        if text.endswith(suffix) and len(text) > len(suffix) + 2:
            text = text[:-len(suffix)]
    return text

def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

lines = []
lines.append("EDGEIQ FORM GUIDE HISTORICAL EPI SOURCE AND BUILDER AUDIT")
lines.append("=" * 88)

# -------------------------------------------------------------------
# Locate candidate source files
# -------------------------------------------------------------------

lines.append("")
lines.append("CANDIDATE DATA SOURCES")
lines.append("-" * 88)

source_matches = {}

for target in TARGET_SOURCE_NAMES:
    matches = [
        path
        for path in ROOT.rglob(target)
        if ".git" not in path.parts
        and "node_modules" not in path.parts
        and "checkpoints" not in path.parts
    ]

    source_matches[target] = matches

    lines.append(f"\n{target}")
    if not matches:
        lines.append("  NOT FOUND")
    else:
        for path in matches:
            lines.append(f"  {path}")
            lines.append(f"    bytes={path.stat().st_size}")

            rows = read_csv_rows(path)
            lines.append(f"    rows={len(rows)}")

            if rows:
                lines.append(f"    columns={list(rows[0].keys())}")

# -------------------------------------------------------------------
# Locate actual builders and assignments
# -------------------------------------------------------------------

lines.append("")
lines.append("")
lines.append("FORM GUIDE BUILDER / ASSIGNMENT LOCATIONS")
lines.append("-" * 88)

builder_hits = []

for path in SCRIPTS.rglob("*.py"):
    if path.name.endswith("_tmp.py"):
        continue

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        continue

    hits = [term for term in ASSIGNMENT_TERMS if term in text]

    if hits:
        builder_hits.append((path, hits))

        lines.append(f"\n{path}")
        lines.append(f"  matched={hits}")

        source_lines = text.splitlines()

        for index, source_line in enumerate(source_lines):
            if any(term in source_line for term in hits):
                start = max(0, index - 8)
                end = min(len(source_lines), index + 18)

                lines.append(f"  --- context around line {index + 1} ---")
                for line_number in range(start, end):
                    lines.append(
                        f"  {line_number + 1:5d}: {source_lines[line_number]}"
                    )

# -------------------------------------------------------------------
# Load Form Guide historical-run identity set
# -------------------------------------------------------------------

if not FORM_FEED.exists():
    raise SystemExit(f"MISSING_FORM_FEED={FORM_FEED}")

with FORM_FEED.open("r", encoding="utf-8-sig") as handle:
    feed = json.load(handle)

form_runs = []
form_keys = Counter()

for race in feed.get("races", []):
    for runner in race.get("runners", []):
        horse_name = runner.get("runnerName")

        for run in runner.get("fullForm", []):
            identity = (
                runner_key(horse_name),
                clean(run.get("date")),
                normalise(run.get("track")),
                number_text(run.get("distance")),
            )

            form_keys[identity] += 1
            form_runs.append({
                "identity": identity,
                "runnerName": horse_name,
                "date": run.get("date"),
                "track": run.get("track"),
                "distance": run.get("distance"),
                "raceNumber": run.get("raceNumber"),
            })

lines.append("")
lines.append("")
lines.append("FORM GUIDE HISTORICAL IDENTITY SUMMARY")
lines.append("-" * 88)
lines.append(f"historical_runs={len(form_runs)}")
lines.append(f"unique_match_keys={len(form_keys)}")
lines.append(
    f"duplicate_form_match_keys={sum(1 for count in form_keys.values() if count > 1)}"
)

# -------------------------------------------------------------------
# Audit research historical EPI source
# -------------------------------------------------------------------

research_paths = source_matches.get(
    "edgeiq_historical_performance_rating_v6_1_research.csv",
    [],
)

lines.append("")
lines.append("")
lines.append("HISTORICAL EPI RESEARCH SOURCE MATCH AUDIT")
lines.append("-" * 88)

if not research_paths:
    lines.append("SOURCE_NOT_FOUND")
else:
    research_path = research_paths[0]
    research_rows = read_csv_rows(research_path)

    lines.append(f"source={research_path}")
    lines.append(f"rows={len(research_rows)}")

    if not research_rows:
        lines.append("SOURCE_HAS_NO_ROWS")
    else:
        columns = list(research_rows[0].keys())
        lines.append(f"columns={columns}")

        candidate_name_columns = [
            "runner_name",
            "horse_name",
            "horse",
            "runnerName",
            "horseName",
        ]
        candidate_date_columns = [
            "race_date",
            "date",
            "run_date",
            "raceDate",
        ]
        candidate_track_columns = [
            "track",
            "meeting",
            "venue",
            "race_track",
        ]
        candidate_distance_columns = [
            "distance",
            "distance_m",
            "race_distance",
        ]
        candidate_rating_columns = [
            "performance_rating_v6_1_research",
            "historical_epi",
            "epi",
            "rating",
        ]

        def choose(candidates):
            return next((column for column in candidates if column in columns), None)

        name_col = choose(candidate_name_columns)
        date_col = choose(candidate_date_columns)
        track_col = choose(candidate_track_columns)
        distance_col = choose(candidate_distance_columns)
        rating_col = choose(candidate_rating_columns)

        lines.append(f"name_column={name_col}")
        lines.append(f"date_column={date_col}")
        lines.append(f"track_column={track_col}")
        lines.append(f"distance_column={distance_col}")
        lines.append(f"rating_column={rating_col}")

        required = [name_col, date_col, track_col, distance_col, rating_col]

        if any(column is None for column in required):
            lines.append("MATCH_AUDIT_BLOCKED_MISSING_REQUIRED_COLUMNS")
        else:
            research_index = defaultdict(list)

            for row_number, row in enumerate(research_rows, start=2):
                key = (
                    runner_key(row.get(name_col)),
                    clean(row.get(date_col)),
                    normalise(row.get(track_col)),
                    number_text(row.get(distance_col)),
                )

                research_index[key].append({
                    "row_number": row_number,
                    "rating": row.get(rating_col),
                    "row": row,
                })

            matched = 0
            matched_with_rating = 0
            ambiguous = 0
            unmatched = 0
            duplicate_source_keys = sum(
                1 for rows in research_index.values() if len(rows) > 1
            )

            examples_matched = []
            examples_ambiguous = []
            examples_unmatched = []

            for form_run in form_runs:
                matches = research_index.get(form_run["identity"], [])

                if not matches:
                    unmatched += 1
                    if len(examples_unmatched) < 15:
                        examples_unmatched.append(form_run)
                    continue

                matched += 1

                if len(matches) > 1:
                    ambiguous += 1
                    if len(examples_ambiguous) < 15:
                        examples_ambiguous.append({
                            "form_run": form_run,
                            "matches": matches,
                        })
                    continue

                rating = clean(matches[0]["rating"])
                if rating:
                    matched_with_rating += 1

                if len(examples_matched) < 15:
                    examples_matched.append({
                        "form_run": form_run,
                        "source_row_number": matches[0]["row_number"],
                        "rating": matches[0]["rating"],
                    })

            lines.append(f"source_unique_keys={len(research_index)}")
            lines.append(f"source_duplicate_keys={duplicate_source_keys}")
            lines.append(f"matched_form_runs={matched}/{len(form_runs)}")
            lines.append(
                f"matched_form_runs_with_rating={matched_with_rating}/{len(form_runs)}"
            )
            lines.append(f"ambiguous_form_runs={ambiguous}")
            lines.append(f"unmatched_form_runs={unmatched}")

            lines.append("")
            lines.append("MATCHED EXAMPLES")
            for example in examples_matched:
                lines.append(json.dumps(example, ensure_ascii=False, indent=2))

            lines.append("")
            lines.append("AMBIGUOUS EXAMPLES")
            if not examples_ambiguous:
                lines.append("NONE")
            else:
                for example in examples_ambiguous:
                    lines.append(json.dumps(example, ensure_ascii=False, indent=2))

            lines.append("")
            lines.append("UNMATCHED EXAMPLES")
            for example in examples_unmatched:
                lines.append(json.dumps(example, ensure_ascii=False, indent=2))

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"WROTE={REPORT}")
print(f"FORM_HISTORICAL_RUNS={len(form_runs)}")
print(f"BUILDER_FILES_FOUND={len(builder_hits)}")

for target, matches in source_matches.items():
    print(f"{target}={len(matches)}")

print("EDGEIQ_FORM_GUIDE_HISTORICAL_EPI_SOURCE_AND_BUILDER_AUDIT_PASS")
