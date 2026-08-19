import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
DATA = ROOT / "public" / "data"
AUDIT_OUT = DATA / "edgeiq_demographic_field_nonblank_audit_v1.csv"
SUMMARY_OUT = DATA / "edgeiq_demographic_field_nonblank_audit_v1_summary.txt"
JOIN_OUT = DATA / "edgeiq_demographic_join_candidates_v1.csv"
BLOCKER_OUT = DATA / "EDGEIQ_WFA_BLOCKER_REPORT_V1.txt"

PATTERNS = ["age", "sex", "gender", "dob", "foaled", "birth", "colour", "horse_sex", "runner_sex", "runner_age", "age_sex_colour", "filly", "mare", "colt", "gelding"]
JOIN_KEYS = ["horse", "horse_name", "runner", "runner_name", "horse_code", "race_entry", "race_date", "track", "race_no"]
RATING_HINTS = ["rating", "rated", "score", "figure", "projection"]
WEIGHT_HINTS = ["weight", "wgt", "handicap", "kg"]
PLACEHOLDERS = {"", "-", "--", "---", "—", "nan", "none", "null", "n/a", "na", "unknown", "not loaded", "source gap", "undefined", "0", "0.0"}
MAX_EXAMPLES = 12
csv.field_size_limit(1024 * 1024 * 64)

def clean(v):
    return str(v or "").strip()

def is_nonblank(v):
    return clean(v).lower() not in PLACEHOLDERS

def col_matches(c):
    lower = c.lower().strip()
    compact = lower.replace(" ", "_").replace("-", "_")
    tokens = [t for t in re_split(compact) if t]
    if compact in {"age", "runner_age", "horse_age", "age_sex_colour", "age_sex_color"}:
        return True
    if "age" in tokens and not any(x in compact for x in ["average", "stage", "percentage", "vintage", "advantage"]):
        return True
    return any(p in compact for p in ["sex", "gender", "dob", "foaled", "birth", "colour", "color", "horse_sex", "runner_sex", "filly", "mare", "colt", "gelding"])

def is_age_column(c):
    lower = c.lower().strip()
    compact = lower.replace(" ", "_").replace("-", "_")
    tokens = [t for t in re_split(compact) if t]
    return compact in {"age", "runner_age", "horse_age", "age_sex_colour", "age_sex_color"} or ("age" in tokens and not any(x in compact for x in ["average", "stage", "percentage", "vintage", "advantage"]))
def is_horse_specific_demographic_column(c):
    lower = c.lower().strip()
    compact = lower.replace(" ", "_").replace("-", "_")
    invalid_fragments = [
        "restriction", "freshness", "age_seconds", "age_minutes", "output_age", "price_age",
        "environment_age", "message", "coverage", "status", "stage", "peak_age",
        "band_colour", "racing_colours", "silk", "colors", "colours",
        "has_age", "has_sex", "age_sex_missing",
    ]
    if any(fragment in compact for fragment in invalid_fragments):
        return False
    valid_exact = {
        "age", "horse_age", "runner_age", "sex", "horse_sex", "runner_sex",
        "gender", "dob", "date_of_birth", "foaled", "birth_date",
        "age_sex_colour", "age_sex_color", "colour", "color",
    }
    if compact in valid_exact:
        return True
    if compact.endswith("_age") and not any(x in compact for x in ["average", "stage"]):
        return True
    if compact.endswith("_sex") or compact.endswith("_gender"):
        return True
    if "dob" in compact or "foaled" in compact or "birth" in compact:
        return True
    return False

def re_split(value):
    import re
    return re.split(r"[^a-z0-9]+", value)

def join_key_match(column, target):
    lower = column.lower().strip()
    aliases = {
        "horse": ["horse", "horse_key"],
        "horse_name": ["horse_name", "runner_name", "name"],
        "runner": ["runner", "runner_name", "horse"],
        "runner_name": ["runner_name", "horse_name", "horse"],
        "horse_code": ["horse_code", "runner_code", "horse_id", "runner_id"],
        "race_entry": ["race_entry", "entry", "runner_key"],
        "race_date": ["race_date", "date", "meeting_date", "_date"],
        "track": ["track", "venue", "meeting_name", "_track"],
        "race_no": ["race_no", "race_number", "race", "_race"],
    }
    return lower == target.lower() or lower in aliases.get(target.lower(), [])

def open_reader(path):
    f = path.open("r", encoding="utf-8-sig", newline="", errors="replace")
    sample = f.read(8192)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except Exception:
        dialect = csv.excel
    return f, csv.DictReader(f, dialect=dialect)

def pct(part, whole):
    return round((part / whole) * 100, 4) if whole else 0.0

def inspect_csv(path):
    records = []
    joins = []
    rows = 0
    status = "OK"
    error = ""
    weight_nonblank = 0
    rating_nonblank = 0
    join_any_nonblank = 0
    try:
        f, reader = open_reader(path)
        with f:
            fields = reader.fieldnames or []
            matching = [c for c in fields if col_matches(c)]
            if not matching:
                return records, joins, rows, status, error, weight_nonblank, rating_nonblank, join_any_nonblank, False

            rating_cols = [c for c in fields if any(h in c.lower() for h in RATING_HINTS)]
            weight_cols = [c for c in fields if any(h in c.lower() for h in WEIGHT_HINTS)]
            join_cols = {key: [c for c in fields if join_key_match(c, key)] for key in JOIN_KEYS}
            nonblank = defaultdict(int)
            examples = defaultdict(list)
            join_nonblank = defaultdict(int)
            for row in reader:
                rows += 1
                if rating_cols and any(is_nonblank(row.get(c, "")) for c in rating_cols):
                    rating_nonblank += 1
                if weight_cols and any(is_nonblank(row.get(c, "")) for c in weight_cols):
                    weight_nonblank += 1
                if any(any(is_nonblank(row.get(c, "")) for c in cols) for cols in join_cols.values()):
                    join_any_nonblank += 1
                for col in matching:
                    val = clean(row.get(col, ""))
                    if is_nonblank(val):
                        nonblank[col] += 1
                        if len(examples[col]) < MAX_EXAMPLES and val not in examples[col]:
                            examples[col].append(val[:140])
                for key, cols in join_cols.items():
                    if cols and any(is_nonblank(row.get(c, "")) for c in cols):
                        join_nonblank[key] += 1
            for col in matching:
                records.append({
                    "source_file": path.name,
                    "column_name": col,
                    "rows": rows,
                    "nonblank_count": nonblank[col],
                    "coverage_pct": pct(nonblank[col], rows),
                    "example_values": " | ".join(examples[col]),
                    "status": status,
                    "error": error,
                })
            demo_cols = [col for col in matching if nonblank[col] > 0]
            if demo_cols:
                for key, cols in join_cols.items():
                    cov = pct(join_nonblank[key], rows)
                    joins.append({
                        "source_file": path.name,
                        "demographic_columns": "|".join(demo_cols),
                        "rows": rows,
                        "join_key_candidate": key,
                        "matching_columns": "|".join(cols),
                        "nonblank_count": join_nonblank[key],
                        "coverage_pct": cov,
                        "join_quality": "STRONG" if cov >= 95 else "PARTIAL" if join_nonblank[key] else "MISSING",
                    })
            return records, joins, rows, status, error, weight_nonblank, rating_nonblank, join_any_nonblank, True
    except Exception as exc:
        status = "ERROR"
        error = str(exc)
        return [{"source_file": path.name, "column_name": "", "rows": rows, "nonblank_count": 0, "coverage_pct": 0.0, "example_values": "", "status": status, "error": error}], joins, rows, status, error, weight_nonblank, rating_nonblank, join_any_nonblank, False

def main():
    files = sorted(DATA.glob("*.csv"))
    all_records = []
    all_joins = []
    matching_file_count = 0
    scanned_rows = 0
    skipped_no_match = 0
    weight_total = rating_total = join_total = 0
    for path in files:
        records, joins, rows, status, error, weight_nonblank, rating_nonblank, join_any_nonblank, had_match = inspect_csv(path)
        all_records.extend(records)
        all_joins.extend(joins)
        if had_match:
            matching_file_count += 1
            scanned_rows += rows
            weight_total += weight_nonblank
            rating_total += rating_nonblank
            join_total += join_any_nonblank
        else:
            skipped_no_match += 1

    fields = ["source_file", "column_name", "rows", "nonblank_count", "coverage_pct", "example_values", "status", "error"]
    with AUDIT_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(all_records)

    join_fields = ["source_file", "demographic_columns", "rows", "join_key_candidate", "matching_columns", "nonblank_count", "coverage_pct", "join_quality"]
    with JOIN_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=join_fields)
        writer.writeheader(); writer.writerows(all_joins)

    nonblank = [r for r in all_records if int(r.get("nonblank_count") or 0) > 0]
    top = sorted(nonblank, key=lambda r: (int(r["nonblank_count"]), float(r["coverage_pct"])), reverse=True)[:40]
    likely = sorted({r["source_file"] for r in nonblank}, key=lambda name: sum(int(r["nonblank_count"]) for r in nonblank if r["source_file"] == name), reverse=True)
    files_with_dob = sorted({r["source_file"] for r in nonblank if any(x in r["column_name"].lower() for x in ["dob", "birth", "foaled"])})
    files_with_sex = sorted({r["source_file"] for r in nonblank if any(x in r["column_name"].lower() for x in ["sex", "gender", "filly", "mare", "colt", "gelding", "age_sex_colour"])})
    files_with_age = sorted({r["source_file"] for r in nonblank if is_age_column(r["column_name"])})
    horse_specific_nonblank = [r for r in nonblank if is_horse_specific_demographic_column(r["column_name"])]
    horse_specific_age = [
        r for r in horse_specific_nonblank
        if is_age_column(r["column_name"]) or any(x in r["column_name"].lower() for x in ["dob", "birth", "foaled", "age_sex_colour"])
    ]
    horse_specific_sex = [
        r for r in horse_specific_nonblank
        if any(x in r["column_name"].lower() for x in ["sex", "gender", "age_sex_colour"])
    ]
    enough = bool(horse_specific_age and horse_specific_sex)
    answer = "YES_RESEARCH_SPINE_AVAILABLE" if enough else "NO_CURRENT_DATA_BLOCKER"

    lines = [
        "EDGEIQ_DEMOGRAPHIC_FIELD_NONBLANK_AUDIT_V1",
        f"csv_files_header_scanned={len(files)}",
        f"files_with_matching_demographic_columns={matching_file_count}",
        f"files_without_matching_demographic_columns={skipped_no_match}",
        f"rows_scanned_in_matching_files={scanned_rows}",
        f"matching_demographic_fields={len(all_records)}",
        f"nonblank_demographic_fields={len(nonblank)}",
        f"horse_specific_nonblank_demographic_fields={len(horse_specific_nonblank)}",
        "",
        "TOP_NONBLANK_DEMOGRAPHIC_FIELDS",
    ]
    lines.extend([f"{r['source_file']}::{r['column_name']} rows={r['rows']} nonblank={r['nonblank_count']} coverage={r['coverage_pct']} examples={r['example_values']}" for r in top] or ["NONE"])
    lines += ["", "LIKELY_DEMOGRAPHIC_SOURCES"]
    lines.extend(likely[:40] or ["NONE"])
    lines += ["", "FILES_WITH_DOB"]
    lines.extend(files_with_dob or ["NONE"])
    lines += ["", "FILES_WITH_SEX"]
    lines.extend(files_with_sex or ["NONE"])
    lines += ["", "FILES_WITH_AGE"]
    lines.extend(files_with_age or ["NONE"])
    lines += ["", "JOIN_CANDIDATES_OUTPUT", str(JOIN_OUT), "", "WFA_RECOVERY_ANSWER", answer]
    if answer == "YES_RESEARCH_SPINE_AVAILABLE":
        lines.append("Can recover candidate horse-specific age/sex evidence from existing CSV estate. Review join candidates and source reliability before any WFA modelling.")
    else:
        lines.append("Cannot recover horse-specific age/sex sufficiently from existing CSV estate. Nonblank age/sex fields found are race restrictions, source flags, colours, or freshness metadata, not horse demographics. WFA remains blocked by missing horse demographics.")
    SUMMARY_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not enough:
        BLOCKER_OUT.write_text("\n".join([
            "EDGEIQ_WFA_BLOCKER_REPORT_V1",
            f"weight_coverage=nonblank_weight_like_rows_in_matching_files:{weight_total}",
            f"rating_coverage=nonblank_rating_like_rows_in_matching_files:{rating_total}",
            f"join_key_coverage=nonblank_join_key_rows_in_matching_files:{join_total}",
            "missing_fields=horse_age|horse_sex|dob",
            "demographic_like_fields_found=YES_BUT_NOT_HORSE_SPECIFIC",
            "recommended_next_steps=Locate upstream source with horse age/sex/DOB; inspect raw race-entry harvests and official starter profiles; do not use age_restriction/sex_restriction as horse demographics; enrich horses_master.csv only after evidence-backed source is found.",
            "answer=NO_CURRENT_DATA_BLOCKER",
        ]) + "\n", encoding="utf-8")
    else:
        BLOCKER_OUT.write_text("EDGEIQ_WFA_BLOCKER_REPORT_V1\nstatus=NOT_CREATED_FOR_THIS_RUN_DEMOGRAPHICS_FOUND\n", encoding="utf-8")

    print(SUMMARY_OUT)
    print(f"answer={answer}")
    print(f"nonblank_demographic_fields={len(nonblank)}")
    print(f"horse_specific_nonblank_demographic_fields={len(horse_specific_nonblank)}")

if __name__ == "__main__":
    main()


