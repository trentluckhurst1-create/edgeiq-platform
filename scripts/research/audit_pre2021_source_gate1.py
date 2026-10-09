#!/usr/bin/env python3
"""Gate 1: approved metadata-only single-warehouse pre-2021 certification."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

EXPECTED = "edgeiq_historical_results_warehouse_v2_graphql.csv"
REQUIRED = ("race_date", "race_id", "runner_id")
OPTIONAL = ("state", "race_class")
def parse_date(raw):
    try:
        return date.fromisoformat(raw.strip()[:10])
    except (ValueError, TypeError):
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", required=True)
    args = ap.parse_args()
    path = Path(args.warehouse)
    if path.name != EXPECTED or not path.is_file():
        raise SystemExit("STOP: only the approved named warehouse CSV is permitted")
    years = defaultdict(lambda: {"rows": 0, "races": set(), "duplicate_rows": 0})
    seen = set()
    total = parsed = pre_rows = duplicate = excluded = 0
    missing_identity = 0
    jurisdiction = Counter()
    race_class = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        if len(set(header)) != len(header):
            raise SystemExit("STOP: ambiguous duplicate header columns")
        absent = [c for c in REQUIRED if c not in header]
        if absent:
            raise SystemExit("STOP: missing required identity/date fields: " + ",".join(absent))
        cols = {c: header.index(c) for c in REQUIRED + OPTIONAL if c in header}
        for rowno, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise SystemExit(f"STOP: malformed CSV row {rowno}")
            # Only approved positions are ever accessed.
            d = parse_date(row[cols["race_date"]])
            total += 1
            if d is None:
                continue
            parsed += 1
            if d.year > 2020:
                excluded += 1
                continue
            pre_rows += 1
            race = row[cols["race_id"]].strip()
            runner = row[cols["runner_id"]].strip()
            if not race or not runner:
                missing_identity += 1
                continue
            k = (race, runner)
            if k in seen:
                duplicate += 1
                years[d.year]["duplicate_rows"] += 1
            else:
                seen.add(k)
            years[d.year]["rows"] += 1
            years[d.year]["races"].add(race)
            if "state" in cols:
                jurisdiction[row[cols["state"]].strip() or "<BLANK>"] += 1
            if "race_class" in cols:
                race_class[row[cols["race_class"]].strip() or "<BLANK>"] += 1
    rate = parsed / total if total else 0
    dup_rate = duplicate / pre_rows if pre_rows else 1
    race_count = len({(y, r) for y, v in years.items() for r in v["races"]})
    reasons = []
    if missing_identity: reasons.append("MISSING_IDENTIFIERS")
    if rate < 0.99: reasons.append("DATE_PARSE_BELOW_99_PERCENT")
    if dup_rate > 0.001: reasons.append("DUPLICATE_RATE_ABOVE_0_1_PERCENT")
    if race_count < 1000: reasons.append("FEWER_THAN_1000_PRE2021_RACES")
    result = {
        "contract": "ONE_NAMED_WAREHOUSE_APPROVED_METADATA_ONLY_NO_OUTCOMES_NO_JOIN_NO_FIT",
        "date_parse_rows": parsed, "total_rows": total,
        "date_parse_rate": round(rate, 8), "post2020_excluded_rows": excluded,
        "pre2021_rows_with_parsed_dates": pre_rows,
        "pre2021_missing_identity_rows": missing_identity,
        "pre2021_duplicate_key_rows": duplicate,
        "pre2021_duplicate_key_rate": round(dup_rate, 8),
        "pre2021_distinct_year_race_pairs": race_count,
        "yearly": [{"year": y, "races": len(years[y]["races"]),
                    "rows": years[y]["rows"], "duplicate_rows": years[y]["duplicate_rows"]}
                   for y in sorted(years)],
        "missing_2011": 2011 not in years, "missing_2017": 2017 not in years,
        "state_metadata": dict(sorted(jurisdiction.items())),
        "race_class_metadata": dict(sorted(race_class.items())),
        "status": "PASS_SOURCE_METADATA_ONLY_COLUMN_LINEAGE_REVIEW_REQUIRED" if not reasons else "STOP",
        "reasons": reasons,
        "limitations": "race_class is a classification proxy; targets, PIT features, V1 exposure and holdout eligibility NOT certified"
    }
    print("GATE1_METADATA_REPORT_JSON")
    print(json.dumps(result, indent=2))
    if reasons:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
