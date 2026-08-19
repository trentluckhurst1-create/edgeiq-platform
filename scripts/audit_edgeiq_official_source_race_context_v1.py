from __future__ import annotations

import csv
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PROJECT_ROOT.parents[1]
PUBLIC_DATA = PROJECT_ROOT / "public" / "data"

AUDIT_OUT = PUBLIC_DATA / "edgeiq_official_source_race_context_audit_v1.csv"
COLUMNS_OUT = PUBLIC_DATA / "edgeiq_official_source_race_context_columns_v1.csv"
SAMPLES_OUT = PUBLIC_DATA / "edgeiq_official_source_race_context_samples_v1.csv"

FILE_NAME_PATTERNS = [
    re.compile(r"^run_context.*\.csv$", re.IGNORECASE),
    re.compile(r"^ra_horse_runs.*\.csv$", re.IGNORECASE),
    re.compile(r"^horse_runs.*\.csv$", re.IGNORECASE),
    re.compile(r"^.*horse_runs.*\.csv$", re.IGNORECASE),
]

CONTEXT_PATTERNS = {
    "field_size": re.compile(r"(field.*size|field$|runners|starter|starters)", re.IGNORECASE),
    "race_id": re.compile(r"(race.*id|race.*key|race_entry|event.*id|source.*race.*key|meeting.*key)", re.IGNORECASE),
    "race_no": re.compile(r"(^race_no$|race_number|source_race_no|race_no_|_race_no$|^rno$)", re.IGNORECASE),
    "race_name": re.compile(r"(^race$|race_name|race_title|race.*title|event_name)", re.IGNORECASE),
    "class": re.compile(r"(race.*class|class_name|class$|class_band|class_clean|class_raw)", re.IGNORECASE),
    "benchmark": re.compile(r"(benchmark|^bm$|bm_rating|handicap_rating)", re.IGNORECASE),
    "prize_money": re.compile(r"(prize|prizemoney|stake|stakemoney)", re.IGNORECASE),
    "race_grade": re.compile(r"(grade|group|listed|race_grade|rating_band)", re.IGNORECASE),
    "condition": re.compile(r"(track_condition|condition|going|track_rating|surface)", re.IGNORECASE),
    "source_race_key": re.compile(r"(source.*race|race_entry|source_url|official_result_url|race_url|horse_all_form_url)", re.IGNORECASE),
    "finish_position": re.compile(r"(^finish$|finish_pos|finish_position|^placing$|^position$|result$)", re.IGNORECASE),
    "raw_context": re.compile(r"(raw_text|raw_run_text|left_summary|right_summary|comment|summary)", re.IGNORECASE),
}

SUMMARY_FIELDS = [
    "source_name",
    "path",
    "relative_path",
    "row_count",
    "column_count",
    "column_list",
    "has_field_size",
    "field_size_columns",
    "has_race_id",
    "race_id_columns",
    "has_race_no",
    "race_no_columns",
    "race_no_missing_count",
    "has_race_name",
    "race_name_columns",
    "has_class",
    "class_columns",
    "has_benchmark",
    "benchmark_columns",
    "has_prize_money",
    "prize_money_columns",
    "has_race_grade",
    "race_grade_columns",
    "has_condition",
    "condition_columns",
    "has_source_race_key",
    "source_race_key_columns",
    "finish_columns",
    "of_n_finish_count",
    "of_n_finish_examples",
    "finish_pos_examples",
    "context_fields",
]

COLUMN_FIELDS = [
    "source_name",
    "path",
    "column_index",
    "column_name",
    "context_categories",
    "is_race_context_field",
]

SAMPLE_FIELDS = [
    "source_name",
    "path",
    "sample_index",
    "horse",
    "horse_key",
    "run_date",
    "race_date",
    "track",
    "race_no",
    "source_race_no",
    "race_id",
    "race_entry",
    "race_name",
    "race_class",
    "class_name",
    "race_class_raw",
    "race_class_clean",
    "race_class_band",
    "benchmark",
    "distance",
    "track_condition",
    "field_size",
    "finish_pos",
    "margin",
    "sp",
    "barrier",
    "weight",
    "official_time",
    "source_url",
    "official_result_url",
    "raw_text",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(MODEL_ROOT))
    except ValueError:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)


def is_candidate(path: Path) -> bool:
    name = path.name
    if not name.lower().endswith(".csv"):
        return False
    return any(pattern.match(name) for pattern in FILE_NAME_PATTERNS)


def candidate_files() -> list[Path]:
    roots = [
        PUBLIC_DATA,
        PROJECT_ROOT,
        MODEL_ROOT / "outputs",
    ]
    found: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if is_candidate(path):
                found[str(path.resolve()).lower()] = path.resolve()
    return sorted(found.values(), key=lambda item: str(item).lower())


def categories_for_column(column: str) -> list[str]:
    return [category for category, pattern in CONTEXT_PATTERNS.items() if pattern.search(column)]


def matching_columns(columns: list[str], category: str) -> list[str]:
    pattern = CONTEXT_PATTERNS[category]
    return [column for column in columns if pattern.search(column)]


def first_existing(row: dict[str, str], names: list[str]) -> str:
    lower_map = {key.lower(): key for key in row.keys()}
    for name in names:
        actual = lower_map.get(name.lower())
        if actual is not None:
            value = clean(row.get(actual))
            if value:
                return value
    return ""


def selected_value(row: dict[str, str], category: str) -> str:
    columns = [column for column in row.keys() if CONTEXT_PATTERNS[category].search(column)]
    for column in columns:
        value = clean(row.get(column))
        if value:
            return value
    return ""


def row_sample(source_name: str, path: Path, row: dict[str, str], sample_index: int) -> dict[str, str]:
    return {
        "source_name": source_name,
        "path": str(path),
        "sample_index": str(sample_index),
        "horse": first_existing(row, ["horse", "horse_name", "runner"]),
        "horse_key": first_existing(row, ["horse_key", "horse_code", "runner_key"]),
        "run_date": first_existing(row, ["run_date", "date"]),
        "race_date": first_existing(row, ["race_date"]),
        "track": first_existing(row, ["track", "track_code", "venue"]),
        "race_no": selected_value(row, "race_no"),
        "source_race_no": first_existing(row, ["source_race_no"]),
        "race_id": selected_value(row, "race_id"),
        "race_entry": first_existing(row, ["race_entry"]),
        "race_name": selected_value(row, "race_name"),
        "race_class": first_existing(row, ["race_class"]),
        "class_name": first_existing(row, ["class_name"]),
        "race_class_raw": first_existing(row, ["race_class_raw"]),
        "race_class_clean": first_existing(row, ["race_class_clean"]),
        "race_class_band": first_existing(row, ["race_class_band"]),
        "benchmark": selected_value(row, "benchmark"),
        "distance": first_existing(row, ["distance", "dist"]),
        "track_condition": selected_value(row, "condition"),
        "field_size": selected_value(row, "field_size"),
        "finish_pos": selected_value(row, "finish_position"),
        "margin": first_existing(row, ["margin", "beaten_margin", "margin_num"]),
        "sp": first_existing(row, ["sp", "starting_price", "price_raw", "odds"]),
        "barrier": first_existing(row, ["barrier", "gate", "draw"]),
        "weight": first_existing(row, ["weight", "weight_carried", "carried_weight"]),
        "official_time": first_existing(row, ["official_time", "race_time"]),
        "source_url": first_existing(row, ["source_url", "horse_url", "horse_all_form_url"]),
        "official_result_url": first_existing(row, ["official_result_url"]),
        "raw_text": first_existing(row, ["raw_text", "raw_run_text"]),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_file(path: Path) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        source_name = path.name

        column_rows = []
        for index, column in enumerate(columns, start=1):
            categories = categories_for_column(column)
            column_rows.append(
                {
                    "source_name": source_name,
                    "path": str(path),
                    "column_index": index,
                    "column_name": column,
                    "context_categories": " | ".join(categories),
                    "is_race_context_field": "YES" if categories else "NO",
                }
            )

        race_no_columns = matching_columns(columns, "race_no")
        finish_columns = matching_columns(columns, "finish_position")
        context_fields = [
            column
            for column in columns
            if categories_for_column(column)
        ]

        row_count = 0
        race_no_missing = 0
        finish_examples: list[str] = []
        of_n_examples: list[str] = []
        of_n_count = 0
        sample_rows: list[dict[str, object]] = []

        for row in reader:
            row_count += 1

            if race_no_columns:
                if not any(clean(row.get(column)) for column in race_no_columns):
                    race_no_missing += 1

            for column in finish_columns:
                value = clean(row.get(column))
                if not value:
                    continue
                if value not in finish_examples and len(finish_examples) < 12:
                    finish_examples.append(value)
                if re.search(r"\bof\s+\d+\b", value, re.IGNORECASE):
                    of_n_count += 1
                    if value not in of_n_examples and len(of_n_examples) < 12:
                        of_n_examples.append(value)

            if len(sample_rows) < 8:
                sample_rows.append(row_sample(source_name, path, row, len(sample_rows) + 1))

    def yes(category: str) -> str:
        return "YES" if matching_columns(columns, category) else "NO"

    summary = {
        "source_name": source_name,
        "path": str(path),
        "relative_path": rel(path),
        "row_count": row_count,
        "column_count": len(columns),
        "column_list": " | ".join(columns),
        "has_field_size": yes("field_size"),
        "field_size_columns": " | ".join(matching_columns(columns, "field_size")),
        "has_race_id": yes("race_id"),
        "race_id_columns": " | ".join(matching_columns(columns, "race_id")),
        "has_race_no": yes("race_no"),
        "race_no_columns": " | ".join(race_no_columns),
        "race_no_missing_count": race_no_missing if race_no_columns else "",
        "has_race_name": yes("race_name"),
        "race_name_columns": " | ".join(matching_columns(columns, "race_name")),
        "has_class": yes("class"),
        "class_columns": " | ".join(matching_columns(columns, "class")),
        "has_benchmark": yes("benchmark"),
        "benchmark_columns": " | ".join(matching_columns(columns, "benchmark")),
        "has_prize_money": yes("prize_money"),
        "prize_money_columns": " | ".join(matching_columns(columns, "prize_money")),
        "has_race_grade": yes("race_grade"),
        "race_grade_columns": " | ".join(matching_columns(columns, "race_grade")),
        "has_condition": yes("condition"),
        "condition_columns": " | ".join(matching_columns(columns, "condition")),
        "has_source_race_key": yes("source_race_key"),
        "source_race_key_columns": " | ".join(matching_columns(columns, "source_race_key")),
        "finish_columns": " | ".join(finish_columns),
        "of_n_finish_count": of_n_count,
        "of_n_finish_examples": " | ".join(of_n_examples),
        "finish_pos_examples": " | ".join(finish_examples),
        "context_fields": " | ".join(context_fields),
    }
    return summary, column_rows, sample_rows


def main() -> None:
    files = candidate_files()
    if not files:
        raise SystemExit("No candidate source files found.")

    audit_rows: list[dict[str, object]] = []
    column_rows: list[dict[str, object]] = []
    sample_rows: list[dict[str, object]] = []

    print("=" * 100)
    print("EDGEIQ OFFICIAL SOURCE RACE CONTEXT AUDIT V1")
    print("=" * 100)
    print(f"project_root={PROJECT_ROOT}")
    print(f"model_root={MODEL_ROOT}")
    print(f"candidate_files={len(files)}")
    print()

    for path in files:
        summary, columns, samples = audit_file(path)
        audit_rows.append(summary)
        column_rows.extend(columns)
        sample_rows.extend(samples)

        print(summary["source_name"])
        print(f"  path={summary['relative_path']}")
        print(f"  rows={summary['row_count']} columns={summary['column_count']}")
        print(f"  field_size={summary['field_size_columns'] or '-'}")
        print(f"  race_id={summary['race_id_columns'] or '-'}")
        print(f"  race_no={summary['race_no_columns'] or '-'} missing={summary['race_no_missing_count'] or '-'}")
        print(f"  race_name={summary['race_name_columns'] or '-'}")
        print(f"  class={summary['class_columns'] or '-'}")
        print(f"  condition={summary['condition_columns'] or '-'}")
        print(f"  finish={summary['finish_columns'] or '-'} of_n={summary['of_n_finish_count']}")
        print(f"  finish_examples={summary['finish_pos_examples'] or '-'}")
        print()

    write_csv(AUDIT_OUT, audit_rows, SUMMARY_FIELDS)
    write_csv(COLUMNS_OUT, column_rows, COLUMN_FIELDS)
    write_csv(SAMPLES_OUT, sample_rows, SAMPLE_FIELDS)

    print("SAVED:")
    print(AUDIT_OUT)
    print(COLUMNS_OUT)
    print(SAMPLES_OUT)


if __name__ == "__main__":
    main()
