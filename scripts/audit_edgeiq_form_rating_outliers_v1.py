
import csv
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
INPUTS = [
    DATA / "edgeiq_form_enrichment_feed_v4.csv",
    DATA / "edgeiq_live_runner_board_v1.csv",
    DATA / "edgeiq_live_runner_board_governed_v1.csv",
]
OUT = DATA / "edgeiq_form_rating_outliers_v1.csv"
SUM = DATA / "edgeiq_form_rating_outliers_v1_summary.csv"
REP = DATA / "edgeiq_form_rating_outliers_v1_report.txt"


def clean(v):
    return str(v or "").strip()


def num(v):
    s = clean(v)
    if not s or s in {"?", "--"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def norm(v):
    return re.sub(r"[^A-Z0-9]+", "", clean(v).upper())


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def finish_num(row, p):
    for c in [p+"position_display_v2", p+"position_display", p+"finish", p+"finishing_position", p+"position"]:
        x = num(row.get(c))
        if x is not None:
            return x
    return None


def rating_num(row, p):
    # Audit raw first, then display. Raw is what can poison later display rebuilds.
    for c in [p+"rating", p+"rating_display_v2", p+"rating_display"]:
        x = num(row.get(c))
        if x is not None:
            return x
    return None


def suspicious_source(row, p, rating):
    text = " ".join(clean(row.get(p+c)) for c in ["source", "comment_display_v2", "comment_display", "reason", "rating_source"])
    upper = text.upper()
    reasons = []
    if rating is not None and rating < 15:
        reasons.append("rating_scale_too_low")
    if "RECOVERED RATING" in upper and rating is not None and rating < 30:
        reasons.append("low_recovered_rating")
    if "RESULTS WAREHOUSE" in upper and rating is not None and rating < 15:
        reasons.append("results_warehouse_low_rating")
    if "UNKNOWN" in upper or "SOURCE GAP" in upper or "NOT LOADED" in upper:
        reasons.append("raw_placeholder_source")
    cond = clean(row.get(p+"condition") or row.get(p+"condition_display_v2") or row.get(p+"condition_display"))
    cond_digit = num(cond)
    if rating is not None and cond_digit is not None and abs(rating-cond_digit) < 0.01 and rating < 15:
        reasons.append("rating_matches_track_condition_token")
    return ";".join(reasons)

records = []
file_rows = {}
for path in INPUTS:
    if path.exists():
        file_rows[path.name] = read_csv(path)

for file_name, rows in file_rows.items():
    med_by_horse = {}
    all_ratings = defaultdict(list)
    for row in rows:
        h = norm(row.get("horse_key") or row.get("horse"))
        if not h:
            continue
        for n in range(1, 6):
            p = f"last_start_{n}_"
            r = rating_num(row, p)
            if r is not None and 15 <= r <= 110:
                all_ratings[h].append(r)
    for h, vals in all_ratings.items():
        med_by_horse[h] = statistics.median(vals) if vals else None

    for row in rows:
        h = norm(row.get("horse_key") or row.get("horse"))
        horse = clean(row.get("horse"))
        if not h:
            continue
        med = med_by_horse.get(h)
        for n in range(1, 6):
            p = f"last_start_{n}_"
            run_date = clean(row.get(p+"date"))
            run_track = clean(row.get(p+"track"))
            if not any(clean(row.get(p+c)) for c in ["date", "track", "rating", "rating_display_v2", "rating_display"]):
                continue
            rating = rating_num(row, p)
            finish = finish_num(row, p)
            issues = []
            if rating is None:
                continue
            if rating < 15:
                issues.append("RATING_BELOW_15")
            if rating > 110:
                issues.append("RATING_ABOVE_110")
            if med is not None and abs(rating - med) >= 45:
                issues.append("RATING_DIFFERS_45_FROM_HORSE_MEDIAN")
            susp = suspicious_source(row, p, rating)
            if susp:
                issues.append("SUSPICIOUS_RATING_SOURCE:" + susp)
            if finish == 1 and rating < 30:
                issues.append("WINNING_RUN_RATING_BELOW_30")
            if finish is not None and 1 <= finish <= 3 and rating < 25:
                issues.append("TOP_THREE_RATING_BELOW_25")
            if issues:
                action = "RECOVER_ALTERNATE_RATING_OR_HIDE_UNRELIABLE"
                if rating < 15 or (finish == 1 and rating < 30):
                    action = "HIGH_PRIORITY_HIDE_OR_RECOVER"
                records.append({
                    "source_file": file_name,
                    "horse": horse,
                    "race_date": clean(row.get("race_date") or row.get("current_race_date")),
                    "track": clean(row.get("track")),
                    "race_no": clean(row.get("race_no")),
                    "last_start_n": n,
                    "run_date": run_date,
                    "run_track": run_track,
                    "run_distance": clean(row.get(p+"distance_display_v2") or row.get(p+"distance_display") or row.get(p+"distance")),
                    "run_class": clean(row.get(p+"class_display_v2") or row.get(p+"class_display") or row.get(p+"class")),
                    "finish": clean(row.get(p+"position_display_v2") or row.get(p+"position_display") or row.get(p+"finish") or row.get(p+"finishing_position")),
                    "margin": clean(row.get(p+"margin_display_v2") or row.get(p+"margin_display") or row.get(p+"margin") or row.get(p+"beaten_margin")),
                    "rating": f"{rating:.3f}".rstrip("0").rstrip("."),
                    "horse_median_last5_rating": "" if med is None else f"{med:.3f}".rstrip("0").rstrip("."),
                    "rating_source_comment": clean(row.get(p+"comment_display_v2") or row.get(p+"comment_display") or row.get(p+"source") or row.get(p+"reason")),
                    "issue": ";".join(issues),
                    "recommended_action": action,
                })

# Also produce a de-duplicated count by horse/start/run date for headline numbers.
dedup_keys = {(r["horse"], r["race_date"], r["track"], r["race_no"], r["last_start_n"], r["run_date"], r["run_track"], r["rating"]) for r in records}
bankers = [r for r in records if norm(r["horse"]) == "BANKERSCHOICE"]

with OUT.open("w", encoding="utf-8", newline="") as f:
    fields = ["source_file","horse","race_date","track","race_no","last_start_n","run_date","run_track","run_distance","run_class","finish","margin","rating","horse_median_last5_rating","rating_source_comment","issue","recommended_action"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(records)

issue_counts = Counter()
for r in records:
    for issue in r["issue"].split(";"):
        issue_counts[issue.split(":")[0]] += 1
summary = [
    ("input_files", len(file_rows)),
    ("rows_audited", sum(len(v) for v in file_rows.values())),
    ("outlier_rows", len(records)),
    ("outlier_unique_runner_starts", len(dedup_keys)),
    ("bankers_choice_outlier_rows", len(bankers)),
]
summary += sorted(issue_counts.items())
summary += [("pricing_maths_changed", "NO"), ("v6_1_changed", "NO"), ("v7_2g2_changed", "NO"), ("status", "FORM_RATING_OUTLIER_AUDIT_COMPLETE")]
with SUM.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","value"])
    w.writeheader(); w.writerows({"metric":k,"value":v} for k,v in summary)
lines = ["EDGEiQ FORM RATING OUTLIERS V1"] + [f"{k}={v}" for k,v in summary]
REP.write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
