import csv
import statistics
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
INPUT = DATA / "edgeiq_prior_asof_rating_spine_v1.csv"
OUT_AUDIT = DATA / "edgeiq_prior_asof_rating_spine_v1_2026_focus_audit.csv"
OUT_SUMMARY = DATA / "edgeiq_prior_asof_rating_spine_v1_2026_focus_summary.csv"
OUT_REPORT = DATA / "edgeiq_prior_asof_rating_spine_v1_2026_focus_report.txt"

CURRENT_YEAR = "2026"

AUDIT_FIELDS = [
    "race_key",
    "race_date",
    "track",
    "race_no",
    "race_id",
    "race_name",
    "race_class",
    "distance_m",
    "distance_band",
    "field_size",
    "prior_rating_covered_runners",
    "prior_rating_missing_runners",
    "coverage_pct",
    "coverage_status",
    "same_date_blocked_rows",
    "future_rating_available_rows",
    "ambiguous_prior_rows",
    "avg_days_since_prior",
    "median_days_since_prior",
    "stale_or_review_rows",
    "current_day_research_ready_flag",
]

SUMMARY_FIELDS = ["section", "metric", "value", "extra"]


def clean(value):
    return "" if value is None else str(value).strip()


def to_float(value):
    try:
        text = clean(value)
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def race_key(row):
    parts = [
        clean(row.get("target_race_date")),
        clean(row.get("track")),
        clean(row.get("race_no")),
        clean(row.get("race_id")),
    ]
    return "|".join(parts)


def coverage_status(covered, total):
    if total <= 0:
        return "UNUSABLE"
    if covered == total:
        return "FULL_FIELD_PRIOR_COVERAGE"
    if covered > 0:
        return "PARTIAL_PRIOR_COVERAGE"
    return "UNUSABLE"


def weak_band(coverage_pct):
    if coverage_pct >= 95:
        return "STRONG"
    if coverage_pct >= 75:
        return "USABLE"
    if coverage_pct >= 50:
        return "WEAK_PARTIAL"
    if coverage_pct > 0:
        return "VERY_WEAK"
    return "UNUSABLE"


def add_summary(rows, section, metric, value, extra=""):
    rows.append({"section": section, "metric": metric, "value": value, "extra": extra})


def main():
    races = {}
    target_rows = 0

    with INPUT.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            race_date = clean(row.get("target_race_date"))
            if not race_date.startswith(CURRENT_YEAR + "-"):
                continue
            target_rows += 1
            key = race_key(row)
            rec = races.get(key)
            if rec is None:
                rec = {
                    "race_key": key,
                    "race_date": race_date,
                    "track": clean(row.get("track")) or "UNKNOWN",
                    "race_no": clean(row.get("race_no")),
                    "race_id": clean(row.get("race_id")),
                    "race_name": clean(row.get("race_name")),
                    "race_class": clean(row.get("race_class")) or "UNKNOWN",
                    "distance_m": clean(row.get("distance_m")),
                    "distance_band": clean(row.get("distance_band")) or "UNKNOWN",
                    "field_size": 0,
                    "covered": 0,
                    "same_date_blocked": 0,
                    "future_available": 0,
                    "ambiguous": 0,
                    "days": [],
                    "stale_or_review": 0,
                }
                races[key] = rec
            rec["field_size"] += 1
            available = clean(row.get("prior_rating_available_flag")).upper() == "YES" and clean(row.get("safe_predictive_spine_flag")).upper() == "YES"
            if available:
                rec["covered"] += 1
                days = to_float(row.get("days_since_prior_rating"))
                if days is not None:
                    rec["days"].append(days)
            if clean(row.get("same_date_rating_blocked_flag")).upper() == "YES":
                rec["same_date_blocked"] += 1
            if clean(row.get("future_rating_available_flag")).upper() == "YES":
                rec["future_available"] += 1
            if clean(row.get("ambiguous_prior_rating_flag")).upper() == "YES":
                rec["ambiguous"] += 1
            q = clean(row.get("prior_rating_quality_flag")).upper()
            if any(term in q for term in ["STALE", "REVIEW", "AMBIGUOUS", "INVALID"]):
                rec["stale_or_review"] += 1

    audit_rows = []
    status_counts = Counter()
    readiness_counts = Counter()
    track_stats = defaultdict(lambda: {"races": 0, "full": 0, "partial": 0, "unusable": 0, "runners": 0, "covered": 0})
    class_stats = defaultdict(lambda: {"races": 0, "full": 0, "partial": 0, "unusable": 0, "runners": 0, "covered": 0})
    dist_stats = defaultdict(lambda: {"races": 0, "full": 0, "partial": 0, "unusable": 0, "runners": 0, "covered": 0})
    coverage_values = []
    full_field_races = partial_races = unusable_races = 0
    current_ready_races = 0

    for key, rec in sorted(races.items(), key=lambda kv: (kv[1]["race_date"], kv[1]["track"], kv[1]["race_no"], kv[1]["race_id"])):
        total = rec["field_size"]
        covered = rec["covered"]
        missing = total - covered
        pct = covered / total * 100 if total else 0.0
        status = coverage_status(covered, total)
        status_counts[status] += 1
        if status == "FULL_FIELD_PRIOR_COVERAGE":
            full_field_races += 1
        elif status == "PARTIAL_PRIOR_COVERAGE":
            partial_races += 1
        else:
            unusable_races += 1
        coverage_values.append(pct)

        ready_flag = "YES" if pct >= 80.0 and covered >= 4 else "NO"
        if ready_flag == "YES":
            current_ready_races += 1
        readiness_counts[ready_flag] += 1

        avg_days = statistics.mean(rec["days"]) if rec["days"] else None
        med_days = statistics.median(rec["days"]) if rec["days"] else None
        audit_row = {
            "race_key": rec["race_key"],
            "race_date": rec["race_date"],
            "track": rec["track"],
            "race_no": rec["race_no"],
            "race_id": rec["race_id"],
            "race_name": rec["race_name"],
            "race_class": rec["race_class"],
            "distance_m": rec["distance_m"],
            "distance_band": rec["distance_band"],
            "field_size": total,
            "prior_rating_covered_runners": covered,
            "prior_rating_missing_runners": missing,
            "coverage_pct": f"{pct:.4f}",
            "coverage_status": status,
            "same_date_blocked_rows": rec["same_date_blocked"],
            "future_rating_available_rows": rec["future_available"],
            "ambiguous_prior_rows": rec["ambiguous"],
            "avg_days_since_prior": f"{avg_days:.4f}" if avg_days is not None else "",
            "median_days_since_prior": f"{med_days:.4f}" if med_days is not None else "",
            "stale_or_review_rows": rec["stale_or_review"],
            "current_day_research_ready_flag": ready_flag,
        }
        audit_rows.append(audit_row)

        for bucket, stats in [(rec["track"], track_stats), (rec["race_class"], class_stats), (rec["distance_band"], dist_stats)]:
            s = stats[bucket or "UNKNOWN"]
            s["races"] += 1
            s["runners"] += total
            s["covered"] += covered
            if status == "FULL_FIELD_PRIOR_COVERAGE":
                s["full"] += 1
            elif status == "PARTIAL_PRIOR_COVERAGE":
                s["partial"] += 1
            else:
                s["unusable"] += 1

    with OUT_AUDIT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(audit_rows)

    summary = []
    race_count = len(races)
    avg_cov = statistics.mean(coverage_values) if coverage_values else 0.0
    med_cov = statistics.median(coverage_values) if coverage_values else 0.0
    runner_covered = sum(r["covered"] for r in races.values())
    runner_cov_pct = runner_covered / target_rows * 100 if target_rows else 0.0

    add_summary(summary, "overall", "year", CURRENT_YEAR)
    add_summary(summary, "overall", "races_audited", race_count)
    add_summary(summary, "overall", "runners_audited", target_rows)
    add_summary(summary, "overall", "prior_rating_covered_runners", runner_covered)
    add_summary(summary, "overall", "runner_coverage_pct", f"{runner_cov_pct:.4f}")
    add_summary(summary, "overall", "full_field_prior_coverage_races", full_field_races)
    add_summary(summary, "overall", "partial_prior_coverage_races", partial_races)
    add_summary(summary, "overall", "unusable_races", unusable_races)
    add_summary(summary, "overall", "average_race_coverage_pct", f"{avg_cov:.4f}")
    add_summary(summary, "overall", "median_race_coverage_pct", f"{med_cov:.4f}")
    add_summary(summary, "overall", "current_day_research_ready_races_80pct_plus", current_ready_races)
    support_verdict = "YES_TARGETED_RESEARCH" if current_ready_races >= max(1, race_count * 0.5) and runner_cov_pct >= 60 else "LIMITED_TARGETED_RESEARCH_ONLY" if runner_covered > 0 else "NO"
    add_summary(summary, "overall", "can_support_current_day_prediction_research", support_verdict)

    def add_slice(section, stats, min_races=3):
        rows = []
        for bucket, s in stats.items():
            if s["races"] < min_races:
                continue
            cov = s["covered"] / s["runners"] * 100 if s["runners"] else 0.0
            full_pct = s["full"] / s["races"] * 100 if s["races"] else 0.0
            weakness = weak_band(cov)
            rows.append((weakness, cov, bucket, s, full_pct))
        rank = {"UNUSABLE": 0, "VERY_WEAK": 1, "WEAK_PARTIAL": 2, "USABLE": 3, "STRONG": 4}
        rows.sort(key=lambda item: (rank.get(item[0], 9), item[1], -item[3]["races"], str(item[2])))
        for weakness, cov, bucket, s, full_pct in rows:
            add_summary(
                summary,
                section,
                bucket,
                f"coverage_pct={cov:.4f}",
                f"weakness={weakness}; races={s['races']}; runners={s['runners']}; covered={s['covered']}; full={s['full']}; partial={s['partial']}; unusable={s['unusable']}; full_race_pct={full_pct:.4f}",
            )

    add_slice("weak_coverage_by_track", track_stats, min_races=2)
    add_slice("weak_coverage_by_class", class_stats, min_races=3)
    add_slice("weak_coverage_by_distance_band", dist_stats, min_races=1)

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary)

    weak_tracks = [r for r in summary if r["section"] == "weak_coverage_by_track" and any(t in r["extra"] for t in ["weakness=UNUSABLE", "weakness=VERY_WEAK", "weakness=WEAK_PARTIAL"])]
    weak_classes = [r for r in summary if r["section"] == "weak_coverage_by_class" and any(t in r["extra"] for t in ["weakness=UNUSABLE", "weakness=VERY_WEAK", "weakness=WEAK_PARTIAL"])]
    weak_distances = [r for r in summary if r["section"] == "weak_coverage_by_distance_band" and any(t in r["extra"] for t in ["weakness=UNUSABLE", "weakness=VERY_WEAK", "weakness=WEAK_PARTIAL"])]

    def top_lines(rows, limit=12):
        if not rows:
            return ["- None at configured threshold."]
        return [f"- {r['metric']}: {r['value']} ({r['extra']})" for r in rows[:limit]]

    report = []
    report.extend([
        "EDGEIQ_PRIOR_ASOF_RATING_SPINE_V1_2026_FOCUS_AUDIT",
        "====================================================",
        f"Races audited: {race_count}",
        f"Runners audited: {target_rows}",
        f"Runner prior-rating coverage: {runner_covered}/{target_rows} ({runner_cov_pct:.2f}%)",
        "",
        "Race coverage:",
        f"- Full-field prior rating coverage: {full_field_races}",
        f"- Partial prior rating coverage: {partial_races}",
        f"- Unusable races: {unusable_races}",
        f"- Average race coverage: {avg_cov:.2f}%",
        f"- Median race coverage: {med_cov:.2f}%",
        f"- Research-ready races at >=80% runner coverage: {current_ready_races}",
        "",
        "Can this spine support current-day prediction research?",
    ])
    if support_verdict == "YES_TARGETED_RESEARCH":
        report.append("YES for targeted current-day prediction research and replay slices, provided low-coverage races are filtered or explicitly downweighted. It is not yet a universal all-history spine.")
    elif support_verdict == "LIMITED_TARGETED_RESEARCH_ONLY":
        report.append("LIMITED. The 2026 window has usable covered rows, but race-level coverage is too uneven for broad current-day prediction without strict coverage gates.")
    else:
        report.append("NO. The 2026 focus set does not have enough prior-rating coverage for predictive research.")
    report.extend([
        "",
        "Weak track coverage:",
        *top_lines(weak_tracks),
        "",
        "Weak class coverage:",
        *top_lines(weak_classes),
        "",
        "Weak distance coverage:",
        *top_lines(weak_distances),
        "",
        "Recommended research gate:",
        "- Use races with >=80% prior-rating runner coverage first.",
        "- Flag partial races and exclude unusable races from probability/pricing replay until coverage is improved.",
        "- Keep same-race and future ratings blocked exactly as in the parent as-of spine.",
        "",
        "No production, pricing, or UI changes made.",
    ])
    OUT_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"Races audited: {race_count}")
    print(f"Runners audited: {target_rows}")
    print(f"Full-field races: {full_field_races}")
    print(f"Partial races: {partial_races}")
    print(f"Unusable races: {unusable_races}")
    print(f"Runner coverage pct: {runner_cov_pct:.4f}")
    print(f"Current-day research support: {support_verdict}")

if __name__ == "__main__":
    main()
