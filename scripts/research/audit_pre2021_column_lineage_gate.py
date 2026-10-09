#!/usr/bin/env python3
"""Approved column-lineage gate: one named warehouse, limited field access, no joins/fits."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

NAME = "edgeiq_historical_results_warehouse_v2_graphql.csv"
REQUIRED = ("race_id", "runner_id", "race_date", "race_class", "finish_num")
OPTIONAL = ("scratched", "finish_abv")
JUMP = re.compile(r"HDLE|HURDLE|STPL|STEEP|CHASE|JUMP|JMPR", re.I)
PICNIC = re.compile(r"PICNIC|(?:^|[\s-])PIC(?:-|\s|$)", re.I)
# Race-class labels other than explicitly identified jumps/picnic are provisional flat.
# Empty labels remain UNCLASSIFIED; report all strings so the rule is inspectable.
def classify(s):
    if not s.strip():
        return "UNCLASSIFIED"
    if JUMP.search(s):
        return "JUMPS"
    if PICNIC.search(s):
        return "PICNIC"
    return "FLAT_PROVISIONAL"

def finish_is_one(s):
    try:
        return float(s.strip()) == 1.0
    except (ValueError, TypeError):
        return False

def pit_status(column):
    n = column.lower()
    if any(t in n for t in ("starting_price", "odds", "market", "price", "sp_", "bsp")) or n in ("sp", "bsp"):
        return "MARKET"
    if any(t in n for t in ("finish", "margin", "winning_time", "race_time", "rating", "won", "placed", "comment_stewards")):
        return "POST_RACE"
    return "UNPROVEN"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", required=True)
    args = ap.parse_args()
    path = Path(args.warehouse)
    if path.name != NAME or not path.is_file():
        raise SystemExit("STOP: unexpected warehouse")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        print("WAREHOUSE_HEADER")
        print(",".join(header))
        if len(set(header)) != len(header):
            raise SystemExit("STOP: duplicate column names")
        absent = [c for c in REQUIRED if c not in header]
        if absent:
            raise SystemExit("STOP: required columns missing: " + ",".join(absent))
        pos = {c: header.index(c) for c in REQUIRED + OPTIONAL if c in header}
        races = {}
        classes = defaultdict(Counter)
        rows_pre = 0
        excluded_post = 0
        invalid_dates = 0
        for line, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise SystemExit(f"STOP: malformed row {line}")
            raw_date = row[pos["race_date"]].strip()
            try:
                d = date.fromisoformat(raw_date[:10])
            except ValueError:
                invalid_dates += 1
                continue
            if d.year > 2020:
                excluded_post += 1
                continue
            rows_pre += 1
            cls = row[pos["race_class"]].strip()
            kind = classify(cls)
            classes[kind][cls or "<BLANK>"] += 1
            race_id = row[pos["race_id"]].strip()
            runner_id = row[pos["runner_id"]].strip()
            if not race_id or not runner_id:
                raise SystemExit("STOP: missing identity")
            # Key race_id by year to preserve audit year boundaries.
            key = (d.year, race_id)
            r = races.setdefault(key, {"year": d.year, "class": kind, "class_text": cls, "seen": set(), "duplicates": 0, "winners": 0, "runners": 0, "scratched": 0})
            if r["class"] != kind or r["class_text"] != cls:
                raise SystemExit("STOP: inconsistent class within a race")
            if runner_id in r["seen"]:
                r["duplicates"] += 1
            else:
                r["seen"].add(runner_id)
            r["runners"] += 1
            scratched = row[pos["scratched"]].strip().lower() if "scratched" in pos else ""
            is_scratched = scratched in ("1", "true", "yes", "y")
            r["scratched"] += int(is_scratched)
            if not is_scratched and finish_is_one(row[pos["finish_num"]]):
                r["winners"] += 1
    per_year = defaultdict(lambda: Counter())
    for r in races.values():
        y = per_year[r["year"]]
        y["total"] += 1
        y[r["class"]] += 1
        if r["class"] == "FLAT_PROVISIONAL":
            y["flat"] += 1
            if r["winners"] == 1 and r["duplicates"] == 0:
                y["eligible"] += 1
            if r["winners"] == 0: y["zero_winner"] += 1
            if r["winners"] > 1: y["multiple_winner"] += 1
            if r["duplicates"] > 0: y["duplicate_key_races"] += 1
    flat = sum(v["flat"] for v in per_year.values())
    eligible = sum(v["eligible"] for v in per_year.values())
    rate = eligible / flat if flat else 0
    reasons = []
    if invalid_dates: reasons.append("UNPARSEABLE_DATES")
    if not flat: reasons.append("NO_SEPARABLE_FLAT_RACES")
    if rate < .95: reasons.append("SINGLE_WINNER_RATE_BELOW_95_PERCENT")
    if eligible < 1000: reasons.append("FEWER_THAN_1000_ELIGIBLE_FLAT_RACES")
    # No builder is inspected at this gate: no column can be certified as pre-race.
    # This is an explicit stop condition from Grok.
    reasons.append("NO_CERTIFIED_PRE_RACE_CANDIDATE_BUILDER")
    report = {
        "contract": "SINGLE_WAREHOUSE_PRE2021_LIMITED_FIELDS_NO_JOIN_NO_FIT",
        "fields_read": list(pos),
        "rows_pre2021": rows_pre,
        "post2020_excluded_by_date_only": excluded_post,
        "invalid_date_rows": invalid_dates,
        "flat_classification": "Exclude explicit jumps/picnic patterns; nonblank remainder provisional flat, not yet independently certified",
        "class_labels_by_category_runner_rows": {k: dict(sorted(v.items())) for k,v in sorted(classes.items())},
        "yearly_races": [{"year": y, **dict(per_year[y])} for y in sorted(per_year)],
        "flat_races": flat, "eligible_flat_single_winner_unique_key_races": eligible,
        "eligible_flat_rate": round(rate, 8),
        "header_pit_classification": {c: pit_status(c) for c in header},
        "pre_race_candidate_columns_certified": [],
        "status": "STOP" if reasons else "PASS",
        "reasons": reasons,
        "note": "Header classification only; outcome integrity does not certify point-in-time features or model population."
    }
    print("COLUMN_LINEAGE_GATE_REPORT_JSON")
    print(json.dumps(report, indent=2))
    if reasons:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
