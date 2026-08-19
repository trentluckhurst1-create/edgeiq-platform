import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "public" / "data" / "edgeiq_results_master_v1.csv"
OUTPUT = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_v1.csv"
SUMMARY = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_v1_summary.txt"
COVERAGE = ROOT / "public" / "data" / "edgeiq_runner_profile_stats_v1_coverage.csv"

KEY_PREFERENCE = ["horse_code", "horse_id", "horse_key", "normalized_runner", "normalised_runner", "runner"]
PLACE_POSITION_CUTOFF = 3
FIRST_UP_BREAK_DAYS = 60


OUTPUT_COLUMNS = [
    "resolved_runner_key",
    "source_key_method",
    "runner",
    "normalized_runner",
    "latest_runner_name",
    "latest_trainer",
    "latest_jockey",
    "latest_track",
    "latest_race_date",
    "latest_distance",
    "latest_class",
    "latest_condition",
    "career_starts",
    "career_wins",
    "career_seconds",
    "career_thirds",
    "career_places",
    "career_win_pct",
    "career_place_pct",
    "best_track_by_starts",
    "latest_track_starts",
    "latest_track_wins",
    "latest_track_seconds",
    "latest_track_thirds",
    "latest_track_places",
    "latest_track_win_pct",
    "latest_track_place_pct",
    "best_distance_by_starts",
    "latest_distance_starts",
    "latest_distance_wins",
    "latest_distance_seconds",
    "latest_distance_thirds",
    "latest_distance_places",
    "latest_distance_win_pct",
    "latest_distance_place_pct",
    "latest_track_distance_starts",
    "latest_track_distance_wins",
    "latest_track_distance_seconds",
    "latest_track_distance_thirds",
    "latest_track_distance_places",
    "good_starts",
    "good_wins",
    "good_seconds",
    "good_thirds",
    "good_places",
    "soft_starts",
    "soft_wins",
    "soft_seconds",
    "soft_thirds",
    "soft_places",
    "heavy_starts",
    "heavy_wins",
    "heavy_seconds",
    "heavy_thirds",
    "heavy_places",
    "firm_starts",
    "firm_wins",
    "firm_seconds",
    "firm_thirds",
    "firm_places",
    "synthetic_starts",
    "synthetic_wins",
    "synthetic_seconds",
    "synthetic_thirds",
    "synthetic_places",
    "latest_class_starts",
    "latest_class_wins",
    "latest_class_seconds",
    "latest_class_thirds",
    "latest_class_places",
    "latest_class_win_pct",
    "latest_class_place_pct",
    "latest_jockey_starts",
    "latest_jockey_wins",
    "latest_jockey_seconds",
    "latest_jockey_thirds",
    "latest_jockey_places",
    "first_up_starts",
    "first_up_wins",
    "first_up_seconds",
    "first_up_thirds",
    "first_up_places",
    "second_up_starts",
    "second_up_wins",
    "second_up_seconds",
    "second_up_thirds",
    "second_up_places",
    "third_up_starts",
    "third_up_wins",
    "third_up_seconds",
    "third_up_thirds",
    "third_up_places",
    "last_5_starts",
    "last_5_wins",
    "last_5_seconds",
    "last_5_thirds",
    "last_5_places",
    "last_5_avg_finish",
    "last_10_starts",
    "last_10_wins",
    "last_10_seconds",
    "last_10_thirds",
    "last_10_places",
    "last_10_avg_finish",
    "peak_epi",
    "avg_epi",
    "last_start_epi",
    "last_5_avg_epi",
    "best_eri",
    "avg_eri",
    "best_esi",
    "avg_esi",
    "last_start_esi",
    "avg_sp",
    "best_sp",
    "last_start_sp",
    "career_prize_money",
]


def clean(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.upper() in {"", "NA", "N/A", "NULL", "NONE", "UNKNOWN", "MISSING"}:
        return ""
    return value


def normalize_name(value):
    value = clean(value).upper()
    return re.sub(r"[^A-Z0-9]+", "", value)


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            pass
    match = re.search(r"(20\d{2}|19\d{2})[-/](\d{1,2})[-/](\d{1,2})", value)
    if match:
        year, month, day = match.groups()
        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            return None
    return None


def parse_float(value):
    value = clean(value)
    if not value:
        return None
    value = value.replace("$", "").replace(",", "").replace("L", "")
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_sp(value):
    parsed = parse_float(value)
    if parsed is None or parsed <= 1:
        return None
    return parsed


def fmt_pct(numerator, denominator):
    if not denominator:
        return ""
    return f"{round((numerator / denominator) * 100, 1):.1f}"


def fmt_float(value, digits=2):
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{round(value, digits):.{digits}f}"


def fmt_one(value):
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    return f"{round(value, 1):.1f}"


def avg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def condition_bucket(value):
    value = clean(value).upper()
    if "FIRM" in value or re.match(r"^F\d*$", value):
        return "firm"
    if "GOOD" in value or re.match(r"^G\d*$", value):
        return "good"
    if "SOFT" in value or re.match(r"^S\d*$", value):
        return "soft"
    if "HEAVY" in value or re.match(r"^H\d*$", value):
        return "heavy"
    if "SYNTH" in value or "POLY" in value or "TAPETA" in value:
        return "synthetic"
    return ""


def distance_value(value):
    raw = clean(value)
    if not raw:
        return ""
    match = re.search(r"\d+", raw)
    return match.group(0) if match else raw


def choose_key(row, fieldnames):
    for field in KEY_PREFERENCE:
        if field in fieldnames and clean(row.get(field)):
            method = field
            value = clean(row.get(field))
            if field in {"normalized_runner", "normalised_runner", "runner"}:
                value = normalize_name(value)
            return value, method
    return "", ""


def empty_bucket():
    return {"starts": 0, "wins": 0, "seconds": 0, "thirds": 0, "places": 0}


def inc_bucket(bucket, position):
    bucket["starts"] += 1
    if position == 1:
        bucket["wins"] += 1
    if position == 2:
        bucket["seconds"] += 1
    if position == 3:
        bucket["thirds"] += 1
    if position is not None and position <= PLACE_POSITION_CUTOFF:
        bucket["places"] += 1


def best_key_by_starts(counter):
    if not counter:
        return ""
    return sorted(counter.items(), key=lambda item: (-item[1]["starts"], item[0]))[0][0]


def build():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    runners = {}
    input_rows = 0
    min_date = None
    max_date = None
    source_key_counts = Counter()
    epi_fields_found = []
    esi_fields_found = []
    eri_fields_found = []
    prize_fields_found = []

    with INPUT.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        fieldset = set(fieldnames)

        if "epi_post" in fieldset:
            epi_fields_found.append("epi_post")
        for candidate in ["eri", "eri_post", "race_strength", "race_index", "edgeiq_race_index"]:
            if candidate in fieldset:
                eri_fields_found.append(candidate)
        for candidate in ["sectional_finish", "std_finish_len", "esi", "esi_overall"]:
            if candidate in fieldset:
                esi_fields_found.append(candidate)
        for candidate in ["career_prize_money", "prizemoney", "prize_money", "prizemoney_earned"]:
            if candidate in fieldset:
                prize_fields_found.append(candidate)

        for row in reader:
            input_rows += 1
            key, method = choose_key(row, fieldset)
            if not key:
                continue
            source_key_counts[method] += 1

            race_date = parse_date(row.get("race_date"))
            if race_date:
                min_date = race_date if min_date is None or race_date < min_date else min_date
                max_date = race_date if max_date is None or race_date > max_date else max_date

            position = parse_float(row.get("position"))
            is_win = position == 1
            is_place = position is not None and position <= PLACE_POSITION_CUTOFF
            track = clean(row.get("track"))
            dist = distance_value(row.get("distance"))
            race_class = clean(row.get("class"))
            cond = condition_bucket(row.get("condition"))
            epi = parse_float(row.get("epi_post"))
            eri = None
            for field in eri_fields_found:
                eri = parse_float(row.get(field))
                if eri is not None:
                    break
            esi = None
            for field in esi_fields_found:
                esi = parse_float(row.get(field))
                if esi is not None:
                    break
            sp = parse_sp(row.get("sp") or row.get("starting_price"))
            prize = None
            for field in prize_fields_found:
                prize = parse_float(row.get(field))
                if prize is not None:
                    break

            if key not in runners:
                runners[key] = {
                    "resolved_runner_key": key,
                    "source_key_method": method,
                    "runner": clean(row.get("runner")),
                    "normalized_runner": clean(row.get("normalized_runner")) or key,
                    "latest": None,
                    "runs": [],
                    "track": defaultdict(empty_bucket),
                    "distance": defaultdict(empty_bucket),
                    "track_distance": defaultdict(empty_bucket),
                    "condition": defaultdict(empty_bucket),
                    "class": defaultdict(empty_bucket),
                    "jockey": defaultdict(empty_bucket),
                    "epis": [],
                    "eris": [],
                    "esis": [],
                    "sps": [],
                    "prize_money": [],
                }

            runner = runners[key]
            if clean(row.get("runner")):
                runner["runner"] = clean(row.get("runner"))
            if clean(row.get("normalized_runner")):
                runner["normalized_runner"] = clean(row.get("normalized_runner"))

            run = {
                "date": race_date,
                "runner": clean(row.get("runner")),
                "trainer": clean(row.get("trainer")),
                "jockey": clean(row.get("jockey")),
                "track": track,
                "distance": dist,
                "class": race_class,
                "condition": clean(row.get("condition")),
                "position": position,
                "is_win": is_win,
                "is_place": is_place,
                "epi": epi,
                "eri": eri,
                "esi": esi,
                "sp": sp,
                "prize": prize,
            }
            runner["runs"].append(run)
            if race_date and (runner["latest"] is None or race_date > runner["latest"]["date"]):
                runner["latest"] = run

            if track:
                inc_bucket(runner["track"][track], position)
            if dist:
                inc_bucket(runner["distance"][dist], position)
            if track and dist:
                inc_bucket(runner["track_distance"][f"{track}|{dist}"], position)
            if cond in {"firm", "good", "soft", "heavy", "synthetic"}:
                inc_bucket(runner["condition"][cond], position)
            if race_class:
                inc_bucket(runner["class"][race_class], position)
            if clean(row.get("jockey")):
                inc_bucket(runner["jockey"][clean(row.get("jockey"))], position)
            if epi is not None:
                runner["epis"].append(epi)
            if eri is not None:
                runner["eris"].append(eri)
            if esi is not None:
                runner["esis"].append(esi)
            if sp is not None:
                runner["sps"].append(sp)
            if prize is not None:
                runner["prize_money"].append(prize)

    output_rows = []
    for key, runner in runners.items():
        runs = sorted([r for r in runner["runs"] if r["date"]], key=lambda r: r["date"])
        career_starts = len(runner["runs"])
        career_wins = sum(1 for r in runner["runs"] if r["is_win"])
        career_seconds = sum(1 for r in runner["runs"] if r["position"] == 2)
        career_thirds = sum(1 for r in runner["runs"] if r["position"] == 3)
        career_places = sum(1 for r in runner["runs"] if r["is_place"])
        latest = runner["latest"] or (runs[-1] if runs else {})

        prep_counts = {
            1: empty_bucket(),
            2: empty_bucket(),
            3: empty_bucket(),
        }
        previous_date = None
        prep_start = 0
        for run in runs:
            if previous_date is None or (run["date"] - previous_date).days >= FIRST_UP_BREAK_DAYS:
                prep_start = 1
            else:
                prep_start += 1
            if prep_start in prep_counts:
                inc_bucket(prep_counts[prep_start], run["position"])
            previous_date = run["date"]

        latest_track = latest.get("track", "")
        latest_distance = latest.get("distance", "")
        latest_class = latest.get("class", "")
        latest_jockey = latest.get("jockey", "")
        latest_track_distance = f"{latest_track}|{latest_distance}" if latest_track and latest_distance else ""
        latest_track_stats = runner["track"].get(latest_track, empty_bucket())
        latest_distance_stats = runner["distance"].get(latest_distance, empty_bucket())
        latest_track_distance_stats = runner["track_distance"].get(latest_track_distance, empty_bucket())
        latest_class_stats = runner["class"].get(latest_class, empty_bucket())
        latest_jockey_stats = runner["jockey"].get(latest_jockey, empty_bucket())

        last_runs = sorted(runner["runs"], key=lambda r: r["date"] or datetime.min.date(), reverse=True)
        last5 = last_runs[:5]
        last10 = last_runs[:10]
        last_start = last_runs[0] if last_runs else {}

        row = {
            "resolved_runner_key": runner["resolved_runner_key"],
            "source_key_method": runner["source_key_method"],
            "runner": runner["runner"],
            "normalized_runner": runner["normalized_runner"],
            "latest_runner_name": latest.get("runner", runner["runner"]),
            "latest_trainer": latest.get("trainer", ""),
            "latest_jockey": latest.get("jockey", ""),
            "latest_track": latest_track,
            "latest_race_date": latest.get("date", "").isoformat() if latest.get("date") else "",
            "latest_distance": latest_distance,
            "latest_class": latest_class,
            "latest_condition": latest.get("condition", ""),
            "career_starts": career_starts,
            "career_wins": career_wins,
            "career_seconds": career_seconds,
            "career_thirds": career_thirds,
            "career_places": career_places,
            "career_win_pct": fmt_pct(career_wins, career_starts),
            "career_place_pct": fmt_pct(career_places, career_starts),
            "best_track_by_starts": best_key_by_starts(runner["track"]),
            "latest_track_starts": latest_track_stats["starts"],
            "latest_track_wins": latest_track_stats["wins"],
            "latest_track_seconds": latest_track_stats["seconds"],
            "latest_track_thirds": latest_track_stats["thirds"],
            "latest_track_places": latest_track_stats["places"],
            "latest_track_win_pct": fmt_pct(latest_track_stats["wins"], latest_track_stats["starts"]),
            "latest_track_place_pct": fmt_pct(latest_track_stats["places"], latest_track_stats["starts"]),
            "best_distance_by_starts": best_key_by_starts(runner["distance"]),
            "latest_distance_starts": latest_distance_stats["starts"],
            "latest_distance_wins": latest_distance_stats["wins"],
            "latest_distance_seconds": latest_distance_stats["seconds"],
            "latest_distance_thirds": latest_distance_stats["thirds"],
            "latest_distance_places": latest_distance_stats["places"],
            "latest_distance_win_pct": fmt_pct(latest_distance_stats["wins"], latest_distance_stats["starts"]),
            "latest_distance_place_pct": fmt_pct(latest_distance_stats["places"], latest_distance_stats["starts"]),
            "latest_track_distance_starts": latest_track_distance_stats["starts"],
            "latest_track_distance_wins": latest_track_distance_stats["wins"],
            "latest_track_distance_seconds": latest_track_distance_stats["seconds"],
            "latest_track_distance_thirds": latest_track_distance_stats["thirds"],
            "latest_track_distance_places": latest_track_distance_stats["places"],
            "good_starts": runner["condition"]["good"]["starts"],
            "good_wins": runner["condition"]["good"]["wins"],
            "good_seconds": runner["condition"]["good"]["seconds"],
            "good_thirds": runner["condition"]["good"]["thirds"],
            "good_places": runner["condition"]["good"]["places"],
            "soft_starts": runner["condition"]["soft"]["starts"],
            "soft_wins": runner["condition"]["soft"]["wins"],
            "soft_seconds": runner["condition"]["soft"]["seconds"],
            "soft_thirds": runner["condition"]["soft"]["thirds"],
            "soft_places": runner["condition"]["soft"]["places"],
            "heavy_starts": runner["condition"]["heavy"]["starts"],
            "heavy_wins": runner["condition"]["heavy"]["wins"],
            "heavy_seconds": runner["condition"]["heavy"]["seconds"],
            "heavy_thirds": runner["condition"]["heavy"]["thirds"],
            "heavy_places": runner["condition"]["heavy"]["places"],
            "firm_starts": runner["condition"]["firm"]["starts"],
            "firm_wins": runner["condition"]["firm"]["wins"],
            "firm_seconds": runner["condition"]["firm"]["seconds"],
            "firm_thirds": runner["condition"]["firm"]["thirds"],
            "firm_places": runner["condition"]["firm"]["places"],
            "synthetic_starts": runner["condition"]["synthetic"]["starts"],
            "synthetic_wins": runner["condition"]["synthetic"]["wins"],
            "synthetic_seconds": runner["condition"]["synthetic"]["seconds"],
            "synthetic_thirds": runner["condition"]["synthetic"]["thirds"],
            "synthetic_places": runner["condition"]["synthetic"]["places"],
            "latest_class_starts": latest_class_stats["starts"],
            "latest_class_wins": latest_class_stats["wins"],
            "latest_class_seconds": latest_class_stats["seconds"],
            "latest_class_thirds": latest_class_stats["thirds"],
            "latest_class_places": latest_class_stats["places"],
            "latest_class_win_pct": fmt_pct(latest_class_stats["wins"], latest_class_stats["starts"]),
            "latest_class_place_pct": fmt_pct(latest_class_stats["places"], latest_class_stats["starts"]),
            "latest_jockey_starts": latest_jockey_stats["starts"],
            "latest_jockey_wins": latest_jockey_stats["wins"],
            "latest_jockey_seconds": latest_jockey_stats["seconds"],
            "latest_jockey_thirds": latest_jockey_stats["thirds"],
            "latest_jockey_places": latest_jockey_stats["places"],
            "first_up_starts": prep_counts[1]["starts"],
            "first_up_wins": prep_counts[1]["wins"],
            "first_up_seconds": prep_counts[1]["seconds"],
            "first_up_thirds": prep_counts[1]["thirds"],
            "first_up_places": prep_counts[1]["places"],
            "second_up_starts": prep_counts[2]["starts"],
            "second_up_wins": prep_counts[2]["wins"],
            "second_up_seconds": prep_counts[2]["seconds"],
            "second_up_thirds": prep_counts[2]["thirds"],
            "second_up_places": prep_counts[2]["places"],
            "third_up_starts": prep_counts[3]["starts"],
            "third_up_wins": prep_counts[3]["wins"],
            "third_up_seconds": prep_counts[3]["seconds"],
            "third_up_thirds": prep_counts[3]["thirds"],
            "third_up_places": prep_counts[3]["places"],
            "last_5_starts": len(last5),
            "last_5_wins": sum(1 for r in last5 if r["is_win"]),
            "last_5_seconds": sum(1 for r in last5 if r["position"] == 2),
            "last_5_thirds": sum(1 for r in last5 if r["position"] == 3),
            "last_5_places": sum(1 for r in last5 if r["is_place"]),
            "last_5_avg_finish": fmt_float(avg([r["position"] for r in last5]), 2),
            "last_10_starts": len(last10),
            "last_10_wins": sum(1 for r in last10 if r["is_win"]),
            "last_10_seconds": sum(1 for r in last10 if r["position"] == 2),
            "last_10_thirds": sum(1 for r in last10 if r["position"] == 3),
            "last_10_places": sum(1 for r in last10 if r["is_place"]),
            "last_10_avg_finish": fmt_float(avg([r["position"] for r in last10]), 2),
            "peak_epi": fmt_one(max(runner["epis"]) if runner["epis"] else None),
            "avg_epi": fmt_one(avg(runner["epis"])),
            "last_start_epi": fmt_one(last_start.get("epi")),
            "last_5_avg_epi": fmt_one(avg([r["epi"] for r in last5])),
            "best_eri": fmt_one(max(runner["eris"]) if runner["eris"] else None),
            "avg_eri": fmt_one(avg(runner["eris"])),
            "best_esi": fmt_one(min(runner["esis"]) if runner["esis"] else None),
            "avg_esi": fmt_one(avg(runner["esis"])),
            "last_start_esi": fmt_one(last_start.get("esi")),
            "avg_sp": fmt_float(avg(runner["sps"]), 2),
            "best_sp": fmt_float(min(runner["sps"]) if runner["sps"] else None, 2),
            "last_start_sp": fmt_float(last_start.get("sp"), 2),
            "career_prize_money": fmt_float(sum(runner["prize_money"]) if runner["prize_money"] else None, 2),
        }
        output_rows.append(row)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output_rows.sort(key=lambda r: r["resolved_runner_key"])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    coverage_rows = []
    total_rows = len(output_rows)
    for column in OUTPUT_COLUMNS:
        non_empty = sum(1 for row in output_rows if clean(row.get(column)))
        pct = (non_empty / total_rows * 100) if total_rows else 0
        recommendation = "KEEP" if pct >= 75 else "DETAIL_ONLY" if pct >= 25 else "HIDE_UNTIL_CONNECTED"
        coverage_rows.append(
            {
                "column": column,
                "non_empty_count": non_empty,
                "total_rows": total_rows,
                "coverage_pct": f"{pct:.1f}",
                "recommendation": recommendation,
            }
        )

    with COVERAGE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["column", "non_empty_count", "total_rows", "coverage_pct", "recommendation"])
        writer.writeheader()
        writer.writerows(coverage_rows)

    keep_columns = [row["column"] for row in coverage_rows if row["recommendation"] == "KEEP"]
    hide_columns = [row["column"] for row in coverage_rows if row["recommendation"] == "HIDE_UNTIL_CONNECTED"]
    detail_columns = [row["column"] for row in coverage_rows if row["recommendation"] == "DETAIL_ONLY"]

    summary_lines = [
        "EDGEIQ RUNNER PROFILE STATS V1",
        "",
        f"Input file: {INPUT.relative_to(ROOT).as_posix()}",
        f"Input rows: {input_rows}",
        f"Output file: {OUTPUT.relative_to(ROOT).as_posix()}",
        f"Output rows: {len(output_rows)}",
        f"Date coverage: {min_date.isoformat() if min_date else ''} to {max_date.isoformat() if max_date else ''}",
        "",
        "Key method counts:",
    ]
    for method, count in source_key_counts.most_common():
        summary_lines.append(f"- {method}: {count}")
    summary_lines.extend(
        [
            "",
            f"Runners with career starts: {sum(1 for row in output_rows if int(row['career_starts'] or 0) > 0)}",
            "",
            f"EPI fields found: {', '.join(epi_fields_found) if epi_fields_found else 'NOT FOUND'}",
            f"ERI fields found: {', '.join(eri_fields_found) if eri_fields_found else 'NOT FOUND'}",
            f"ESI fields found: {', '.join(esi_fields_found) if esi_fields_found else 'NOT FOUND'}",
            f"Prize money fields found: {', '.join(prize_fields_found) if prize_fields_found else 'NOT FOUND'}",
            "",
            "Coverage highlights:",
            f"- KEEP columns ({len(keep_columns)}): {', '.join(keep_columns)}",
            f"- DETAIL_ONLY columns ({len(detail_columns)}): {', '.join(detail_columns)}",
            f"- HIDE_UNTIL_CONNECTED columns ({len(hide_columns)}): {', '.join(hide_columns)}",
            "",
            "Recommended UI fields to show immediately:",
            ", ".join(keep_columns),
            "",
            "Recommended UI fields to hide until connected:",
            ", ".join(hide_columns),
            "",
            "Caveats:",
            "- v1 resolved_runner_key uses the best available key in edgeiq_results_master_v1.csv.",
            "- This source does not contain horse_code / horse_id / horse_key, so normalized_runner is the practical v1 key where available.",
            "- normalized_runner can merge different horses with the same normalized name. Key ambiguity risk is real and should be repaired with a horse identity bridge before high-stakes display.",
            "- Places use simple Australian-style position <= 3 for v1.",
            "- First-up / second-up / third-up are derived from sorted runs with a 60-day break rule; first recorded run is treated as first-up.",
            "- ESI uses non-raw sectional length/index fields only. Raw sectional times are not emitted.",
            "- ERI and prize money remain blank if not present in the canonical source.",
        ]
    )
    SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Input rows: {input_rows}")
    print(f"Output rows: {len(output_rows)}")
    print(f"Output: {OUTPUT}")
    print(f"Coverage: {COVERAGE}")
    print(f"Summary: {SUMMARY}")


if __name__ == "__main__":
    build()
