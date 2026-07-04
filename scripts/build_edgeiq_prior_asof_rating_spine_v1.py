import csv
import math
import statistics
import re
import unicodedata
from bisect import bisect_left
from collections import defaultdict, Counter
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

RATING_PATH = DATA / "edgeiq_historical_performance_rating_v6_1_research.csv"
RESULTS_PATH = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
LEAKAGE_INPUT_PATH = DATA / "edgeiq_rating_engine_leakage_audit_v1.csv"
INVENTORY_INPUT_PATH = DATA / "edgeiq_rating_engine_input_inventory_v1.csv"

OUT_SPINE = DATA / "edgeiq_prior_asof_rating_spine_v1.csv"
OUT_SUMMARY = DATA / "edgeiq_prior_asof_rating_spine_v1_summary.csv"
OUT_LEAKAGE = DATA / "edgeiq_prior_asof_rating_spine_v1_leakage_audit.csv"
OUT_UNMATCHED = DATA / "edgeiq_prior_asof_rating_spine_v1_unmatched.csv"
OUT_REPORT = DATA / "edgeiq_prior_asof_rating_spine_v1_report.txt"

RATING_COL = "performance_rating_v6_1_research"

SPINE_FIELDS = [
    "target_race_date",
    "target_year",
    "track",
    "state",
    "race_no",
    "race_id",
    "race_name",
    "distance",
    "distance_m",
    "distance_band",
    "race_class",
    "horse",
    "horse_code",
    "runner_id",
    "barrier",
    "weight",
    "jockey",
    "trainer",
    "prior_v6_1_rating",
    "prior_rating_date",
    "days_since_prior_rating",
    "prior_rating_recency_band",
    "prior_rating_source_race",
    "prior_rating_track",
    "prior_rating_distance",
    "prior_rating_distance_delta",
    "prior_rating_class",
    "prior_rating_class_delta",
    "prior_finish",
    "prior_margin",
    "prior_rating_available_flag",
    "prior_rating_quality_flag",
    "prior_rating_match_status",
    "same_date_rating_blocked_flag",
    "future_rating_available_flag",
    "ambiguous_prior_rating_flag",
    "ambiguous_prior_same_date_count",
    "safe_predictive_spine_flag",
]

UNMATCHED_FIELDS = [
    "target_race_date",
    "track",
    "race_no",
    "race_id",
    "distance",
    "distance_m",
    "race_class",
    "horse",
    "horse_code",
    "runner_id",
    "unmatched_reason",
    "same_date_rating_blocked_flag",
    "future_rating_available_flag",
    "candidate_rating_count_for_horse",
]


def clean_str(value):
    if value is None:
        return ""
    return str(value).strip()


def parse_date(value):
    value = clean_str(value)
    if not value:
        return None
    value = value[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def date_iso(d):
    return d.isoformat() if isinstance(d, date) else ""


def norm_horse(value):
    text = clean_str(value).upper()
    if not text:
        return ""
    text = text.replace("�", " ")
    text = text.replace("’", "'").replace("`", "'")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\([^)]{1,5}\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("$", "").replace(",", "").replace("m", "").replace("M", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in ("", ".", "-", "-."):
        return None
    try:
        number = float(text)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    except ValueError:
        return None


def parse_intish(value):
    number = parse_float(value)
    if number is None:
        return ""
    return str(int(round(number)))


def distance_band(distance_m):
    if distance_m is None:
        return "UNKNOWN"
    if distance_m <= 1200:
        return "SPRINT"
    if distance_m <= 1600:
        return "MILE"
    if distance_m <= 2000:
        return "MIDDLE"
    return "STAYING"


def recency_band(days):
    if days is None:
        return "MISSING"
    if days <= 0:
        return "INVALID"
    if days <= 21:
        return "RECENT_1_21"
    if days <= 45:
        return "STANDARD_22_45"
    if days <= 90:
        return "STALE_46_90"
    return "VERY_STALE_91_PLUS"


def quality_flag(days, ambiguous):
    if days is None:
        return "MISSING_PRIOR_HISTORY"
    if days <= 0:
        return "INVALID_PRIOR_DATE"
    if ambiguous:
        return "AMBIGUOUS_PRIOR_DATE_REVIEW"
    if days <= 45:
        return "GOOD_PRIOR_RATING"
    if days <= 90:
        return "STALE_BUT_USABLE_PRIOR_RATING"
    return "VERY_STALE_PRIOR_RATING"


def class_delta(target_class, prior_class):
    target = clean_str(target_class).upper()
    prior = clean_str(prior_class).upper()
    if not target or target in {"UNKNOWN", "NAN", "NONE"} or not prior or prior in {"UNKNOWN", "NAN", "NONE"}:
        return "UNKNOWN_CLASS_DELTA"
    if target == prior:
        return "SAME_CLASS_LABEL"
    return "DIFFERENT_CLASS_LABEL"


def safe_get(row, *names):
    for name in names:
        if name in row and clean_str(row.get(name)):
            return clean_str(row.get(name))
    return ""


def load_rating_history():
    histories = defaultdict(list)
    same_horse_date_counts = Counter()
    source_rows = 0
    usable_rows = 0
    bad_date_rows = 0
    missing_horse_rows = 0
    missing_rating_rows = 0

    with RATING_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            source_rows += 1
            horse = clean_str(row.get("horse"))
            horse_key = norm_horse(horse)
            if not horse_key:
                missing_horse_rows += 1
                continue
            rdate = parse_date(row.get("race_date"))
            if rdate is None:
                bad_date_rows += 1
                continue
            rating = parse_float(row.get(RATING_COL))
            if rating is None:
                missing_rating_rows += 1
                continue
            distance = parse_float(row.get("distance"))
            race_class = safe_get(row, "race_class_clean_v3_3", "race_class_clean", "race_class_recovered", "race_class_raw")
            source_race = " | ".join(part for part in [
                date_iso(rdate),
                safe_get(row, "track"),
                str(int(distance)) + "m" if distance is not None else "",
                race_class,
                safe_get(row, "race_name"),
            ] if part)
            item = {
                "date": rdate,
                "horse": horse,
                "rating": rating,
                "track": safe_get(row, "track"),
                "distance": distance,
                "race_class": race_class,
                "source_race": source_race,
                "finish": safe_get(row, "finish_position", "finish_pos_raw"),
                "margin": safe_get(row, "margin", "margin_raw"),
            }
            histories[horse_key].append(item)
            same_horse_date_counts[(horse_key, rdate)] += 1
            usable_rows += 1

    for horse_key, items in histories.items():
        items.sort(key=lambda item: item["date"])
        dates = [item["date"] for item in items]
        for item in items:
            item["same_horse_date_count"] = same_horse_date_counts[(horse_key, item["date"])]
        # Keep dates attached once for bisect lookup.
        histories[horse_key] = {"dates": dates, "items": items}

    stats = {
        "rating_source_rows": source_rows,
        "rating_usable_rows": usable_rows,
        "rating_bad_date_rows": bad_date_rows,
        "rating_missing_horse_rows": missing_horse_rows,
        "rating_missing_rating_rows": missing_rating_rows,
        "rating_horse_count": len(histories),
        "rating_horse_date_duplicate_keys": sum(1 for count in same_horse_date_counts.values() if count > 1),
    }
    return histories, stats


def lookup_prior(histories, horse_key, target_date):
    record = histories.get(horse_key)
    if not record:
        return None, False, False, 0
    dates = record["dates"]
    items = record["items"]
    idx = bisect_left(dates, target_date)
    same_date_blocked = idx < len(dates) and dates[idx] == target_date
    future_available = idx < len(dates) and dates[idx] > target_date
    if idx == 0:
        return None, same_date_blocked, future_available, len(items)
    prior = items[idx - 1]
    return prior, same_date_blocked, future_available, len(items)


def read_prior_audit_context():
    context = {
        "leakage_audit_rows": 0,
        "leakage_high_or_blocked_rows": 0,
        "inventory_rows": 0,
        "inventory_rating_pipeline_rows": 0,
    }
    if LEAKAGE_INPUT_PATH.exists():
        with LEAKAGE_INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                context["leakage_audit_rows"] += 1
                status = clean_str(row.get("status")).upper()
                severity = clean_str(row.get("severity")).upper()
                if status not in {"PASS", "OK", "LOW", ""} or severity in {"HIGH", "CRITICAL"}:
                    context["leakage_high_or_blocked_rows"] += 1
    if INVENTORY_INPUT_PATH.exists():
        with INVENTORY_INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                context["inventory_rows"] += 1
                text = " ".join(clean_str(row.get(c)) for c in row.keys()).lower()
                if any(term in text for term in ["v6.1", "v6_1", "rating", "probability", "pricing"]):
                    context["inventory_rating_pipeline_rows"] += 1
    return context


def build_spine():
    histories, rating_stats = load_rating_history()
    prior_context = read_prior_audit_context()

    target_rows = 0
    scratched_excluded = 0
    bad_target_date_rows = 0
    missing_target_horse_rows = 0
    matched_rows = 0
    unmatched_rows = 0
    same_date_blocked_rows = 0
    future_available_rows = 0
    ambiguous_prior_rows = 0
    bad_prior_date_rows = 0
    same_race_rating_use_rows = 0
    future_rating_use_rows = 0
    target_rows_written = 0

    days_values = []
    coverage_by_year = defaultdict(lambda: [0, 0])
    coverage_by_track = defaultdict(lambda: [0, 0])
    coverage_by_class = defaultdict(lambda: [0, 0])
    coverage_by_distance_band = defaultdict(lambda: [0, 0])
    quality_counts = Counter()
    recency_counts = Counter()
    unmatched_reasons = Counter()

    with RESULTS_PATH.open("r", encoding="utf-8-sig", newline="") as results_fh, \
            OUT_SPINE.open("w", encoding="utf-8", newline="") as spine_fh, \
            OUT_UNMATCHED.open("w", encoding="utf-8", newline="") as unmatched_fh:
        reader = csv.DictReader(results_fh)
        spine_writer = csv.DictWriter(spine_fh, fieldnames=SPINE_FIELDS, extrasaction="ignore")
        unmatched_writer = csv.DictWriter(unmatched_fh, fieldnames=UNMATCHED_FIELDS, extrasaction="ignore")
        spine_writer.writeheader()
        unmatched_writer.writeheader()

        for row in reader:
            scratched = clean_str(row.get("scratched")).upper()
            if scratched in {"TRUE", "1", "Y", "YES"}:
                scratched_excluded += 1
                continue

            target_date = parse_date(row.get("race_date"))
            if target_date is None:
                bad_target_date_rows += 1
                continue
            horse = clean_str(row.get("horse"))
            horse_key = norm_horse(horse)
            if not horse_key:
                missing_target_horse_rows += 1
                continue

            target_rows += 1
            target_year = str(target_date.year)
            track = safe_get(row, "track")
            race_class = safe_get(row, "race_class")
            distance_raw = safe_get(row, "distance")
            distance_m = parse_float(distance_raw)
            dist_band = distance_band(distance_m)

            coverage_by_year[target_year][0] += 1
            coverage_by_track[track or "UNKNOWN"][0] += 1
            coverage_by_class[race_class or "UNKNOWN"][0] += 1
            coverage_by_distance_band[dist_band][0] += 1

            prior, same_date_blocked, future_available, candidate_count = lookup_prior(histories, horse_key, target_date)
            if same_date_blocked:
                same_date_blocked_rows += 1
            if future_available:
                future_available_rows += 1

            base_output = {
                "target_race_date": date_iso(target_date),
                "target_year": target_year,
                "track": track,
                "state": safe_get(row, "state"),
                "race_no": parse_intish(row.get("race_no")),
                "race_id": parse_intish(row.get("race_id")),
                "race_name": safe_get(row, "race_name"),
                "distance": distance_raw,
                "distance_m": str(int(distance_m)) if distance_m is not None else "",
                "distance_band": dist_band,
                "race_class": race_class,
                "horse": horse,
                "horse_code": parse_intish(row.get("horse_code")),
                "runner_id": parse_intish(row.get("runner_id")),
                "barrier": parse_intish(row.get("barrier")),
                "weight": safe_get(row, "weight"),
                "jockey": safe_get(row, "jockey"),
                "trainer": safe_get(row, "trainer"),
                "same_date_rating_blocked_flag": "YES" if same_date_blocked else "NO",
                "future_rating_available_flag": "YES" if future_available else "NO",
            }

            if prior is None:
                unmatched_rows += 1
                reason = "NO_RATING_HISTORY_FOR_HORSE" if candidate_count == 0 else "NO_PRIOR_RATING_BEFORE_TARGET_DATE"
                if same_date_blocked:
                    reason = "ONLY_SAME_DATE_RATING_BLOCKED"
                elif future_available and candidate_count > 0:
                    reason = "ONLY_FUTURE_RATING_AVAILABLE"
                unmatched_reasons[reason] += 1
                unmatched_writer.writerow({
                    "target_race_date": base_output["target_race_date"],
                    "track": track,
                    "race_no": base_output["race_no"],
                    "race_id": base_output["race_id"],
                    "distance": distance_raw,
                    "distance_m": base_output["distance_m"],
                    "race_class": race_class,
                    "horse": horse,
                    "horse_code": base_output["horse_code"],
                    "runner_id": base_output["runner_id"],
                    "unmatched_reason": reason,
                    "same_date_rating_blocked_flag": "YES" if same_date_blocked else "NO",
                    "future_rating_available_flag": "YES" if future_available else "NO",
                    "candidate_rating_count_for_horse": candidate_count,
                })
                spine_writer.writerow({
                    **base_output,
                    "prior_rating_available_flag": "NO",
                    "prior_rating_quality_flag": "MISSING_PRIOR_HISTORY",
                    "prior_rating_match_status": reason,
                    "prior_rating_recency_band": "MISSING",
                    "ambiguous_prior_rating_flag": "NO",
                    "ambiguous_prior_same_date_count": "0",
                    "safe_predictive_spine_flag": "NO",
                })
                quality_counts["MISSING_PRIOR_HISTORY"] += 1
                recency_counts["MISSING"] += 1
                target_rows_written += 1
                continue

            days = (target_date - prior["date"]).days
            if days <= 0:
                bad_prior_date_rows += 1
            ambiguous = int(prior.get("same_horse_date_count") or 0) > 1
            if ambiguous:
                ambiguous_prior_rows += 1
            if prior["date"] == target_date:
                same_race_rating_use_rows += 1
            if prior["date"] > target_date:
                future_rating_use_rows += 1
            days_values.append(days)
            matched_rows += 1
            coverage_by_year[target_year][1] += 1
            coverage_by_track[track or "UNKNOWN"][1] += 1
            coverage_by_class[race_class or "UNKNOWN"][1] += 1
            coverage_by_distance_band[dist_band][1] += 1

            prior_distance = prior.get("distance")
            distance_delta = ""
            if distance_m is not None and prior_distance is not None:
                distance_delta = str(int(round(distance_m - prior_distance)))
            rec_band = recency_band(days)
            q_flag = quality_flag(days, ambiguous)
            if days > 180:
                q_flag = "VERY_STALE_PRIOR_RATING_REVIEW"
            quality_counts[q_flag] += 1
            recency_counts[rec_band] += 1

            spine_writer.writerow({
                **base_output,
                "prior_v6_1_rating": f"{prior['rating']:.6f}",
                "prior_rating_date": date_iso(prior["date"]),
                "days_since_prior_rating": days,
                "prior_rating_recency_band": rec_band,
                "prior_rating_source_race": prior.get("source_race", ""),
                "prior_rating_track": prior.get("track", ""),
                "prior_rating_distance": str(int(prior_distance)) if prior_distance is not None else "",
                "prior_rating_distance_delta": distance_delta,
                "prior_rating_class": prior.get("race_class", ""),
                "prior_rating_class_delta": class_delta(race_class, prior.get("race_class", "")),
                "prior_finish": prior.get("finish", ""),
                "prior_margin": prior.get("margin", ""),
                "prior_rating_available_flag": "YES",
                "prior_rating_quality_flag": q_flag,
                "prior_rating_match_status": "MATCHED_STRICT_PRIOR_DATE",
                "ambiguous_prior_rating_flag": "YES" if ambiguous else "NO",
                "ambiguous_prior_same_date_count": prior.get("same_horse_date_count", 0),
                "safe_predictive_spine_flag": "YES" if days > 0 and prior["date"] < target_date else "NO",
            })
            target_rows_written += 1

    coverage_pct = (matched_rows / target_rows * 100.0) if target_rows else 0.0
    avg_days = statistics.mean(days_values) if days_values else None
    median_days = statistics.median(days_values) if days_values else None

    if bad_prior_date_rows or same_race_rating_use_rows or future_rating_use_rows:
        verdict = "LEAKAGE_RISK_BLOCKED"
    elif target_rows == 0 or rating_stats["rating_usable_rows"] == 0:
        verdict = "DATA_INTEGRITY_BLOCKED"
    elif coverage_pct >= 80.0:
        verdict = "SAFE_ASOF_SPINE_BUILT"
    elif matched_rows > 0:
        verdict = "PARTIAL_ASOF_SPINE_BUILT"
    else:
        verdict = "DATA_INTEGRITY_BLOCKED"

    summary_rows = []
    def add(section, metric, value, extra=""):
        summary_rows.append({"section": section, "metric": metric, "value": value, "extra": extra})

    add("overall", "verdict", verdict)
    add("overall", "target_rows", target_rows)
    add("overall", "target_rows_written", target_rows_written)
    add("overall", "matched_prior_rating_rows", matched_rows)
    add("overall", "unmatched_rows", unmatched_rows)
    add("overall", "coverage_pct", f"{coverage_pct:.4f}")
    add("overall", "scratched_excluded", scratched_excluded)
    add("overall", "bad_target_date_rows", bad_target_date_rows)
    add("overall", "missing_target_horse_rows", missing_target_horse_rows)
    add("overall", "same_date_blocked_rows", same_date_blocked_rows)
    add("overall", "future_date_blocked_rows", future_available_rows)
    add("overall", "ambiguous_joins", ambiguous_prior_rows)
    add("overall", "average_days_since_prior", f"{avg_days:.4f}" if avg_days is not None else "")
    add("overall", "median_days_since_prior", f"{median_days:.4f}" if median_days is not None else "")
    add("leakage", "bad_prior_dates", bad_prior_date_rows)
    add("leakage", "same_race_rating_use", same_race_rating_use_rows)
    add("leakage", "future_rating_use", future_rating_use_rows)
    add("leakage", "target_post_race_fields_used_for_features", 0, "target result fields deliberately excluded from spine features")
    for k, v in rating_stats.items():
        add("rating_source", k, v)
    for k, v in prior_context.items():
        add("input_audit_context", k, v)
    for reason, count in unmatched_reasons.most_common():
        add("unmatched_reason", reason, count)
    for flag, count in quality_counts.most_common():
        add("quality_flag", flag, count)
    for band, count in recency_counts.most_common():
        add("recency_band", band, count)

    def add_coverage(section, data):
        for key, (total, matched) in sorted(data.items(), key=lambda kv: (-kv[1][0], str(kv[0])))[:250]:
            pct = (matched / total * 100.0) if total else 0.0
            add(section, key, f"{matched}/{total}", f"coverage_pct={pct:.4f}")

    add_coverage("coverage_by_year", coverage_by_year)
    add_coverage("coverage_by_track", coverage_by_track)
    add_coverage("coverage_by_class", coverage_by_class)
    add_coverage("coverage_by_distance_band", coverage_by_distance_band)

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["section", "metric", "value", "extra"])
        writer.writeheader()
        writer.writerows(summary_rows)

    leakage_rows = [
        {"check": "strict_prior_date_rule", "value": bad_prior_date_rows, "status": "PASS" if bad_prior_date_rows == 0 else "FAIL", "details": "All selected prior ratings must have prior_rating_date < target_race_date."},
        {"check": "same_race_rating_use", "value": same_race_rating_use_rows, "status": "PASS" if same_race_rating_use_rows == 0 else "FAIL", "details": "No same-date rating was selected as prior evidence."},
        {"check": "future_rating_use", "value": future_rating_use_rows, "status": "PASS" if future_rating_use_rows == 0 else "FAIL", "details": "No future-dated rating was selected as prior evidence."},
        {"check": "same_date_ratings_blocked", "value": same_date_blocked_rows, "status": "PASS", "details": "Same-date ratings were detected only as blocked candidates, never selected."},
        {"check": "future_ratings_blocked", "value": future_available_rows, "status": "PASS", "details": "Future ratings were detected only as blocked candidates, never selected."},
        {"check": "target_post_race_feature_exclusion", "value": 0, "status": "PASS", "details": "Target finish, margin, won, placed, SP and comments are not used as predictive rating fields."},
        {"check": "ambiguous_prior_same_date_rows", "value": ambiguous_prior_rows, "status": "WARN" if ambiguous_prior_rows else "PASS", "details": "Rows where the selected horse had multiple historical V6.1 ratings on the same prior date are flagged for review."},
    ]
    with OUT_LEAKAGE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["check", "value", "status", "details"])
        writer.writeheader()
        writer.writerows(leakage_rows)

    report_lines = [
        "EDGEIQ_PRIOR_ASOF_RATING_SPINE_V1",
        "===================================",
        f"Verdict: {verdict}",
        "",
        "Purpose:",
        "Build a strict pre-race/as-of rating spine for predictive research use. The selected rating for each target runner is the latest available V6.1 performance rating dated strictly before the target race.",
        "",
        "Core counts:",
        f"- Target rows: {target_rows}",
        f"- Matched prior-rating rows: {matched_rows}",
        f"- Unmatched rows: {unmatched_rows}",
        f"- Coverage: {coverage_pct:.2f}%",
        f"- Same-date blocked rows: {same_date_blocked_rows}",
        f"- Future-date blocked rows: {future_available_rows}",
        f"- Ambiguous prior-date rows: {ambiguous_prior_rows}",
        f"- Average days since prior: {avg_days:.2f}" if avg_days is not None else "- Average days since prior: n/a",
        f"- Median days since prior: {median_days:.2f}" if median_days is not None else "- Median days since prior: n/a",
        "",
        "Leakage audit:",
        f"- Bad prior dates selected: {bad_prior_date_rows}",
        f"- Same-race rating use: {same_race_rating_use_rows}",
        f"- Future rating use: {future_rating_use_rows}",
        "- Target post-race result fields used as predictive features: 0",
        "",
        "Interpretation:",
    ]
    if verdict == "SAFE_ASOF_SPINE_BUILT":
        report_lines.append("The as-of spine is safe for research staging: strict prior-date selection passed, same-race/future rating usage is zero, and prior-rating coverage is high enough to support predictive replay work.")
    elif verdict == "PARTIAL_ASOF_SPINE_BUILT":
        report_lines.append("The as-of spine is leakage-safe but only partially covered. It can support targeted research slices, but broad replay work should account for unmatched runners and stale prior ratings.")
    elif verdict == "LEAKAGE_RISK_BLOCKED":
        report_lines.append("The spine is blocked because at least one selected rating violated the strict prior-date rule. Do not use for predictive research until fixed.")
    else:
        report_lines.append("The spine could not be built to useful quality from available inputs. Data integrity remediation is required before predictive replay use.")
    report_lines.extend([
        "",
        "Important boundaries:",
        "- Production pricing not changed.",
        "- V6.1 ratings not changed.",
        "- V7.2G2 not changed.",
        "- UI not changed.",
        "- No prices or probabilities calculated.",
    ])
    OUT_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Verdict: {verdict}")
    print(f"Target rows: {target_rows}")
    print(f"Matched prior-rating rows: {matched_rows}")
    print(f"Unmatched rows: {unmatched_rows}")
    print(f"Coverage pct: {coverage_pct:.4f}")
    print(f"Same-race rating use: {same_race_rating_use_rows}")
    print(f"Future rating use: {future_rating_use_rows}")


if __name__ == "__main__":
    build_spine()
