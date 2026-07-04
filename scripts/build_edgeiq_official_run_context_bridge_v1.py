from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PROJECT_ROOT.parents[1]
PUBLIC_DATA = PROJECT_ROOT / "public" / "data"

OUT = PUBLIC_DATA / "edgeiq_official_run_context_bridge_v1.csv"
AUDIT_OUT = PUBLIC_DATA / "edgeiq_official_run_context_bridge_v1_audit.csv"

SOURCES = [
    ("run_context.csv", MODEL_ROOT / "outputs" / "enrichment" / "run_context.csv"),
    ("run_context_FIXED.csv", MODEL_ROOT / "outputs" / "enrichment" / "run_context_FIXED.csv"),
    ("ra_horse_runs.csv", MODEL_ROOT / "outputs" / "ra_careers" / "ra_horse_runs.csv"),
    ("horse_runs_ra.csv", MODEL_ROOT / "outputs" / "ra_form" / "horse_runs_ra.csv"),
]

BRIDGE_FIELDS = [
    "horse",
    "horse_key",
    "race_date",
    "track",
    "distance",
    "race_class",
    "track_condition",
    "finish_pos",
    "margin",
    "source_file",
    "real_field_size",
    "real_field_size_source",
    "race_name",
    "source_race_no",
    "race_entry",
    "source_url",
    "official_result_url",
    "recovery_confidence",
    "recovery_reason",
    "bridge_run_key",
    "duplicate_source_count",
]

AUDIT_FIELDS = [
    "section",
    "source_file",
    "metric",
    "value",
    "detail",
]


def clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null", "na", "n/a"} else text


def upper(value: object) -> str:
    return clean(value).upper()


def compact(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", upper(value))


def first(row: dict[str, str], *names: str) -> str:
    lower_map = {key.lower(): key for key in row.keys() if key is not None}
    for name in names:
        actual = lower_map.get(name.lower())
        if actual is None:
            continue
        value = clean(row.get(actual))
        if value:
            return value
    return ""


def parse_float_text(value: object) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_int_text(value: object) -> int | None:
    number = parse_float_text(value)
    if number is None:
        return None
    rounded = int(round(number))
    return rounded if abs(number - rounded) < 0.001 else None


def normalize_date(value: object) -> str:
    text = clean(value)
    if not text:
        return ""
    text = text[:10]
    formats = ["%Y-%m-%d", "%d%b%y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def valid_field_size(value: object) -> int | None:
    size = parse_int_text(value)
    if size is None:
        return None
    return size if 2 <= size <= 30 else None


def numeric_key(value: object) -> str:
    number = parse_float_text(value)
    if number is None:
        return compact(value)
    if abs(number - round(number)) < 0.001:
        return str(int(round(number)))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def finish_key(value: object) -> str:
    number = parse_int_text(value)
    return str(number) if number is not None else compact(value)


def field_size_from_finish(value: object) -> int | None:
    match = re.search(r"\bof\s+(\d{1,2})\b", clean(value), re.IGNORECASE)
    if not match:
        return None
    return valid_field_size(match.group(1))


def official_or_blank(row: dict[str, str], source_name: str) -> bool:
    run_type = upper(first(row, "run_type", "run_type_code"))
    official = upper(first(row, "is_official_race", "is_official_run", "official_run_flag"))
    is_trial = upper(first(row, "is_trial", "trial_flag"))
    is_jumpout = upper(first(row, "is_jumpout", "jumpout_flag"))
    combined = " ".join(
        upper(first(row, field))
        for field in ["run_type", "race_class", "race_class_raw", "race_name", "raw_text", "raw_run_text"]
    )
    if is_trial in {"1", "TRUE", "YES"} or is_jumpout in {"1", "TRUE", "YES"}:
        return False
    if any(token in combined for token in ["TRIAL", "JUMPOUT", "JUMP OUT", "BARRIER TRIAL", "-BT", "TRL"]):
        return False
    if official in {"FALSE", "0", "NO"}:
        return False
    if run_type and run_type not in {"RACE", "R", "TRUE", "1"}:
        return False
    return True


def bridge_key(row: dict[str, str]) -> str:
    return "|".join(
        [
            compact(row.get("horse") or row.get("horse_key")),
            normalize_date(row.get("race_date")),
            compact(row.get("track")),
            numeric_key(row.get("distance")),
            finish_key(row.get("finish_pos")),
            numeric_key(row.get("margin")),
        ]
    )


def recover_field_size(row: dict[str, str]) -> tuple[str, str, str]:
    field_size = valid_field_size(row.get("field_size"))
    if field_size is not None:
        return str(field_size), "field_size", "HIGH"

    from_finish = field_size_from_finish(row.get("finish_pos"))
    if from_finish is not None:
        return str(from_finish), "finish_pos_of_n", "MEDIUM"

    return "", "unresolved", "LOW"


def map_row(source_name: str, source_path: Path, row: dict[str, str]) -> dict[str, str]:
    horse = first(row, "horse", "horse_name", "runner")
    horse_key = first(row, "horse_key", "horse_code", "runner_key") or compact(horse)
    race_date = normalize_date(first(row, "race_date", "run_date", "date"))
    track = first(row, "track", "track_code", "venue")
    distance = first(row, "distance", "dist")
    race_class = first(row, "race_class", "race_class_clean", "race_class_raw", "class_name")
    track_condition = first(row, "track_condition", "condition", "going")
    finish_pos = first(row, "finish_pos", "finish_position", "finish")
    margin = first(row, "margin", "margin_num", "beaten_margin")
    field_size = first(row, "field_size")
    race_name = first(row, "race_name")
    source_race_no = first(row, "source_race_no", "race_no", "race_number")
    race_entry = first(row, "race_entry", "race_key", "race_id")
    source_url = first(row, "source_url", "horse_all_form_url", "horse_url")
    official_result_url = first(row, "official_result_url")

    base = {
        "horse": horse,
        "horse_key": horse_key,
        "race_date": race_date,
        "track": track,
        "distance": distance,
        "race_class": race_class,
        "track_condition": track_condition,
        "finish_pos": finish_pos,
        "margin": margin,
        "source_file": source_name,
        "field_size": field_size,
        "race_name": race_name,
        "source_race_no": source_race_no,
        "race_entry": race_entry,
        "source_url": source_url,
        "official_result_url": official_result_url,
    }
    real_field_size, real_field_size_source, confidence = recover_field_size(base)
    reason_bits = []
    if real_field_size_source == "field_size":
        reason_bits.append("field_size column supplied valid real field size")
    elif real_field_size_source == "finish_pos_of_n":
        reason_bits.append("field size recovered directly from finish_pos 'of N'")
    else:
        reason_bits.append("no direct field_size or finish_pos 'of N' available")

    if source_race_no:
        reason_bits.append("source_race_no available")
    if race_entry:
        reason_bits.append("race_entry/race key available")
    if race_name:
        reason_bits.append("race_name available")

    return {
        **{key: base[key] for key in BRIDGE_FIELDS if key in base},
        "real_field_size": real_field_size,
        "real_field_size_source": real_field_size_source,
        "recovery_confidence": confidence,
        "recovery_reason": " | ".join(reason_bits),
        "bridge_run_key": bridge_key(base),
        "duplicate_source_count": "1",
    }


def read_source(source_name: str, source_path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    stats = Counter()
    rows: list[dict[str, str]] = []
    if not source_path.exists():
        stats["missing_file"] += 1
        return rows, stats

    with source_path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            stats["source_rows"] += 1
            mapped = map_row(source_name, source_path, raw)
            if not mapped["horse"] or not mapped["race_date"] or not mapped["track"]:
                stats["missing_core_identity"] += 1
                continue
            if not official_or_blank(raw, source_name):
                stats["non_official_or_trial_jumpout"] += 1
                continue
            rows.append(mapped)
            stats["candidate_rows"] += 1
            if mapped["real_field_size"]:
                stats["rows_with_real_field_size"] += 1
            else:
                stats["rows_without_real_field_size"] += 1
            stats[f"field_size_source::{mapped['real_field_size_source']}"] += 1
            stats[f"confidence::{mapped['recovery_confidence']}"] += 1
    return rows, stats


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit_row(section: str, source_file: str, metric: str, value: object, detail: object = "") -> dict[str, object]:
    return {
        "section": section,
        "source_file": source_file,
        "metric": metric,
        "value": value,
        "detail": detail,
    }


def main() -> None:
    all_candidates: list[dict[str, str]] = []
    source_stats: dict[str, Counter] = {}

    print("=" * 100)
    print("EDGEIQ OFFICIAL RUN CONTEXT BRIDGE V1")
    print("=" * 100)
    print(f"project_root={PROJECT_ROOT}")
    print(f"model_root={MODEL_ROOT}")
    print()

    for source_name, source_path in SOURCES:
        rows, stats = read_source(source_name, source_path)
        source_stats[source_name] = stats
        all_candidates.extend(rows)
        print(source_name)
        print(f"  path={source_path}")
        print(f"  source_rows={stats['source_rows']}")
        print(f"  candidate_rows={stats['candidate_rows']}")
        print(f"  rows_with_real_field_size={stats['rows_with_real_field_size']}")
        print(f"  rows_without_real_field_size={stats['rows_without_real_field_size']}")
        print()

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in all_candidates:
        grouped[row["bridge_run_key"]].append(row)

    selected_rows: list[dict[str, str]] = []
    duplicate_key_count = 0
    duplicate_candidate_rows = 0
    source_priority = {name: index for index, (name, _) in enumerate(SOURCES)}

    for key, rows in grouped.items():
        if len(rows) > 1:
            duplicate_key_count += 1
            duplicate_candidate_rows += len(rows)
        rows.sort(key=lambda item: source_priority.get(item["source_file"], 999))
        selected = dict(rows[0])
        selected["duplicate_source_count"] = str(len(rows))
        selected_rows.append(selected)

    selected_rows.sort(key=lambda row: (row["race_date"], row["track"], row["horse"], row["source_file"]))
    write_csv(OUT, selected_rows, BRIDGE_FIELDS)

    audit_rows: list[dict[str, object]] = []
    for source_name, _ in SOURCES:
        stats = source_stats[source_name]
        for metric in [
            "source_rows",
            "candidate_rows",
            "missing_core_identity",
            "non_official_or_trial_jumpout",
            "rows_with_real_field_size",
            "rows_without_real_field_size",
        ]:
            audit_rows.append(audit_row("source_summary", source_name, metric, stats.get(metric, 0)))

        for key, count in sorted(stats.items()):
            if key.startswith("field_size_source::"):
                audit_rows.append(audit_row("field_size_distribution_by_source", source_name, key.split("::", 1)[1], count))
            if key.startswith("confidence::"):
                audit_rows.append(audit_row("recovery_confidence_by_source", source_name, key.split("::", 1)[1], count))

    selected_source_counts = Counter(row["source_file"] for row in selected_rows)
    selected_field_sources = Counter(row["real_field_size_source"] for row in selected_rows)
    selected_confidence = Counter(row["recovery_confidence"] for row in selected_rows)
    selected_size_by_source = Counter((row["source_file"], row["real_field_size"] or "BLANK") for row in selected_rows)

    audit_rows.append(audit_row("bridge_summary", "ALL", "candidate_rows", len(all_candidates)))
    audit_rows.append(audit_row("bridge_summary", "ALL", "selected_rows", len(selected_rows)))
    audit_rows.append(audit_row("duplicate_key_risks", "ALL", "duplicate_bridge_keys", duplicate_key_count))
    audit_rows.append(audit_row("duplicate_key_risks", "ALL", "duplicate_candidate_rows", duplicate_candidate_rows))

    for source_file, count in sorted(selected_source_counts.items()):
        audit_rows.append(audit_row("selected_rows_per_source", source_file, "selected_rows", count))
    for field_source, count in sorted(selected_field_sources.items()):
        audit_rows.append(audit_row("selected_field_size_source_counts", "ALL", field_source, count))
    for confidence, count in sorted(selected_confidence.items()):
        audit_rows.append(audit_row("selected_recovery_confidence_counts", "ALL", confidence, count))
    for (source_file, field_size), count in sorted(selected_size_by_source.items()):
        audit_rows.append(audit_row("field_size_distribution_by_selected_source", source_file, field_size, count))

    write_csv(AUDIT_OUT, audit_rows, AUDIT_FIELDS)

    print("BRIDGE SUMMARY")
    print(f"candidate_rows={len(all_candidates)}")
    print(f"selected_rows={len(selected_rows)}")
    print(f"duplicate_bridge_keys={duplicate_key_count}")
    print(f"duplicate_candidate_rows={duplicate_candidate_rows}")
    print()
    print("SELECTED FIELD SIZE SOURCES")
    for name, count in selected_field_sources.most_common():
        print(f"  {name}: {count}")
    print()
    print("SELECTED CONFIDENCE COUNTS")
    for name, count in selected_confidence.most_common():
        print(f"  {name}: {count}")
    print()
    print("SAVED:")
    print(OUT)
    print(AUDIT_OUT)


if __name__ == "__main__":
    main()
