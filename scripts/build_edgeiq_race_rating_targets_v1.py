from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
AUDITS = ROOT / "outputs" / "audits"

FORM_RUNS = DATA / "form_card_runs.csv"
CURRENT_FIELDS = DATA / "edgeiq_vic_three_day_race_fields.csv"
OUT = DATA / "edgeiq_race_rating_targets_v1.csv"
AUDIT_OUT = AUDITS / "edgeiq_race_rating_targets_v1_audit.csv"

OUTPUT_COLUMNS = [
    "race_date",
    "track",
    "race_no",
    "distance",
    "race_class",
    "track_condition",
    "target_rating",
    "target_method",
    "target_confidence",
    "sample_size",
    "class_distance_band",
    "notes",
]

AUDIT_EXTRA_COLUMNS = [
    "official_rated_runs",
    "official_winner_runs",
    "current_field_runners",
    "track_class_distance_condition_winners_sample",
    "class_distance_condition_winners_sample",
    "class_distance_winners_sample",
    "distance_condition_winners_sample",
    "distance_winners_sample",
]

TRACK_ALIASES = {
    "SANDOWN LAKESIDE": {"SANL", "SANH", "SANDOWN", "SANDOWN LAKESIDE", "SANDOWN HILLSIDE"},
    "SANDOWN HILLSIDE": {"SANH", "SANL", "SANDOWN", "SANDOWN LAKESIDE", "SANDOWN HILLSIDE"},
    "CAULFIELD": {"CAUL", "CAUH", "CAULFIELD"},
    "FLEMINGTON": {"FLEM", "FLEMINGTON"},
    "MOONEE VALLEY": {"M V", "MOONEE VALLEY"},
    "PAKENHAM": {"PAKM", "PAKENHAM"},
    "BALLARAT": {"BRAT", "BALLARAT"},
    "BENDIGO": {"BDGO", "BENDIGO"},
    "CRANBOURNE": {"CRAN", "CRANBOURNE"},
    "WARRNAMBOOL": {"WNBL", "WARRNAMBOOL"},
    "TERANG": {"TER", "TERANG"},
    "HAMILTON": {"HTON", "HAMILTON"},
    "CASTERTON": {"CAST", "CASTERTON"},
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper_clean(value: object) -> str:
    return clean_text(value).upper()


def to_num(value: object) -> float:
    text = clean_text(value).replace("$", "").replace(",", "")
    if not text or text == "-":
        return math.nan
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    try:
        return float(match.group(0))
    except ValueError:
        return math.nan


def parse_date(value: object) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            continue
    return None


def parse_bool(value: object) -> bool:
    return upper_clean(value) in {"TRUE", "1", "YES", "Y"}


def condition_group(value: object) -> str:
    text = upper_clean(value)
    if "HEAVY" in text:
        return "HEAVY"
    if "SOFT" in text:
        return "SOFT"
    if "GOOD" in text or "FIRM" in text:
        return "GOOD"
    if "SYNTH" in text or "POLY" in text:
        return "SYNTHETIC"
    return "UNKNOWN"


def class_band(value: object) -> str:
    text = upper_clean(value)
    if not text:
        return "UNKNOWN"
    bm = re.search(r"\bBM\s?(\d+)", text)
    if bm:
        return f"BM{bm.group(1)}"
    if "GROUP 1" in text or "G1" in text:
        return "GROUP1"
    if "GROUP 2" in text or "G2" in text:
        return "GROUP2"
    if "GROUP 3" in text or "G3" in text:
        return "GROUP3"
    if "LISTED" in text:
        return "LISTED"
    if "MAIDEN" in text or text == "MDN":
        return "MAIDEN"
    if "HANDICAP" in text or "HCP" in text:
        return "HANDICAP"
    if "OPEN" in text:
        return "OPEN"
    return text[:24]


def distance_band(distance: float) -> str:
    if math.isnan(distance):
        return "DIST_UNKNOWN"
    if distance <= 1200:
        return "SPRINT"
    if distance <= 1600:
        return "MILE"
    if distance <= 2200:
        return "MIDDLE"
    if distance < 3200:
        return "STAYING"
    return "EXTENDED_STAYING"


def distance_window(distance: float) -> float:
    if math.isnan(distance):
        return 999999.0
    if distance >= 3200:
        return 500.0
    if distance >= 2200:
        return 350.0
    return 200.0


def track_aliases(track: object) -> set[str]:
    text = upper_clean(track)
    return TRACK_ALIASES.get(text, {text})


def is_winner(value: object) -> bool:
    text = upper_clean(value)
    return bool(re.match(r"^1(ST)?(\b| OF|$)", text))


def is_trial_like(row: dict[str, object]) -> bool:
    combined = " ".join(
        upper_clean(row.get(col, ""))
        for col in ["run_type", "race_class", "class_name", "race_name", "raw_text"]
    )
    return any(token in combined for token in ["TRIAL", "JUMP OUT", "JUMPOUT", "BARRIER TRIAL"])


def quantile(values: list[float], q: float) -> float:
    clean = sorted(v for v in values if not math.isnan(v))
    if not clean:
        return math.nan
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return clean[int(pos)]
    return clean[lower] + ((clean[upper] - clean[lower]) * (pos - lower))


def target_from_ratings(ratings: list[float]) -> float:
    clean = [value for value in ratings if not math.isnan(value)]
    if not clean:
        return math.nan
    median = quantile(clean, 0.5)
    p75 = quantile(clean, 0.75)
    # Robust target: mostly median comparable winner, with a controlled pull toward stronger winners.
    return round((median * 0.65) + (p75 * 0.35), 2)


def confidence_for(method: str, sample_size: int) -> str:
    if method == "TRACK_CLASS_DISTANCE_CONDITION_WINNERS":
        if sample_size >= 12:
            return "HIGH"
        if sample_size >= 6:
            return "MEDIUM"
    if method == "CLASS_DISTANCE_CONDITION_WINNERS":
        if sample_size >= 18:
            return "HIGH"
        if sample_size >= 8:
            return "MEDIUM"
    if method == "CLASS_DISTANCE_WINNERS":
        if sample_size >= 25:
            return "HIGH"
        if sample_size >= 10:
            return "MEDIUM"
    if method in {"DISTANCE_CONDITION_WINNERS", "DISTANCE_WINNERS"}:
        if sample_size >= 25:
            return "MEDIUM"
        if sample_size >= 10:
            return "LOW"
    return "LOW"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare_runs() -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    for row in read_csv(FORM_RUNS):
        run_date = parse_date(row.get("run_date") or row.get("date"))
        rating = to_num(row.get("run_rating"))
        if run_date is None or math.isnan(rating):
            continue
        if not parse_bool(row.get("is_official_race")):
            continue
        if upper_clean(row.get("run_type")) != "RACE":
            continue
        if is_trial_like(row):
            continue
        prepared.append(
            {
                **row,
                "run_date_dt": run_date,
                "rating_num": rating,
                "distance_num": to_num(row.get("distance")),
                "track_key_norm": upper_clean(row.get("track")),
                "class_band": class_band(row.get("race_class")),
                "condition_group": condition_group(row.get("track_condition")),
                "horse_key_norm": upper_clean(row.get("horse_key") or row.get("horse")),
                "is_winner": is_winner(row.get("finish_pos")),
            }
        )
    return prepared


def prepare_current_fields() -> list[dict[str, object]]:
    fields: list[dict[str, object]] = []
    for row in read_csv(CURRENT_FIELDS):
        if parse_bool(row.get("is_scratched")):
            continue
        fields.append(
            {
                **row,
                "race_date_dt": parse_date(row.get("race_date")),
                "distance_num": to_num(row.get("distance")),
                "class_band": class_band(row.get("race_class")),
                "condition_group": condition_group(row.get("track_condition")),
                "track_key_norm": upper_clean(row.get("track")),
                "horse_key_norm": upper_clean(row.get("horse_key") or row.get("horse")),
            }
        )
    return fields


def race_sort_key(row: dict[str, object]) -> tuple[str, str, int]:
    race_no = int(to_num(row.get("race_no"))) if not math.isnan(to_num(row.get("race_no"))) else 999
    return (clean_text(row.get("race_date")), clean_text(row.get("track")), race_no)


def current_races(fields: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str]] = set()
    races: list[dict[str, object]] = []
    for row in sorted(fields, key=race_sort_key):
        key = (clean_text(row.get("race_date")), clean_text(row.get("track")), clean_text(row.get("race_no")))
        if key in seen:
            continue
        seen.add(key)
        races.append(row)
    return races


def rows_for_race(fields: list[dict[str, object]], race: dict[str, object]) -> list[dict[str, object]]:
    return [
        row
        for row in fields
        if clean_text(row.get("race_date")) == clean_text(race.get("race_date"))
        and clean_text(row.get("track")) == clean_text(race.get("track"))
        and clean_text(row.get("race_no")) == clean_text(race.get("race_no"))
    ]


def field_strength_target(
    race_rows: list[dict[str, object]], official_runs: list[dict[str, object]], race_date: datetime
) -> tuple[float, int, str]:
    strengths: list[float] = []
    for horse_key in sorted({upper_clean(row.get("horse_key_norm")) for row in race_rows if upper_clean(row.get("horse_key_norm"))}):
        horse_runs = [
            run
            for run in official_runs
            if upper_clean(run.get("horse_key_norm")) == horse_key and run["run_date_dt"] < race_date
        ]
        horse_runs.sort(key=lambda item: item["run_date_dt"], reverse=True)
        recent = [float(run["rating_num"]) for run in horse_runs[:6]]
        if recent:
            strengths.append(max(recent))

    if len(strengths) < 3:
        return math.nan, len(strengths), "fewer than three current runners have official recent ratings"

    target = round(quantile(strengths, 0.75), 2)
    return target, len(strengths), "field fallback uses 75th percentile of each runner's best last-six official rating"


def select_target(
    race: dict[str, object],
    race_rows: list[dict[str, object]],
    official_runs: list[dict[str, object]],
    winner_runs: list[dict[str, object]],
) -> dict[str, object]:
    race_date = race.get("race_date_dt")
    if not isinstance(race_date, datetime):
        race_date = parse_date(race.get("race_date")) or datetime.max

    track = clean_text(race.get("track"))
    distance = to_num(race.get("distance"))
    klass_band = class_band(race.get("race_class"))
    cond_group = condition_group(race.get("track_condition"))
    aliases = track_aliases(track)
    window = distance_window(distance)

    history = [run for run in winner_runs if run["run_date_dt"] < race_date]

    def near_distance(run: dict[str, object]) -> bool:
        run_distance = float(run.get("distance_num", math.nan))
        return not math.isnan(run_distance) and not math.isnan(distance) and abs(run_distance - distance) <= window

    def same_class(run: dict[str, object]) -> bool:
        return run.get("class_band") == klass_band

    def same_cond(run: dict[str, object]) -> bool:
        return run.get("condition_group") == cond_group

    def same_track(run: dict[str, object]) -> bool:
        return upper_clean(run.get("track_key_norm")) in aliases

    samples: list[tuple[str, list[dict[str, object]], int]] = [
        (
            "TRACK_CLASS_DISTANCE_CONDITION_WINNERS",
            [run for run in history if same_track(run) and same_class(run) and near_distance(run) and same_cond(run)],
            6,
        ),
        (
            "CLASS_DISTANCE_CONDITION_WINNERS",
            [run for run in history if same_class(run) and near_distance(run) and same_cond(run)],
            8,
        ),
        ("CLASS_DISTANCE_WINNERS", [run for run in history if same_class(run) and near_distance(run)], 10),
        ("DISTANCE_CONDITION_WINNERS", [run for run in history if near_distance(run) and same_cond(run)], 10),
        ("DISTANCE_WINNERS", [run for run in history if near_distance(run)], 12),
    ]

    audit_counts = {f"{name.lower()}_sample": len(sample) for name, sample, _ in samples}

    for method, sample, minimum in samples:
        if len(sample) >= minimum:
            ratings = [float(run["rating_num"]) for run in sample]
            return {
                "target_rating": target_from_ratings(ratings),
                "target_method": method,
                "target_confidence": confidence_for(method, len(sample)),
                "sample_size": len(sample),
                "notes": (
                    f"official winner sample; distance_window={int(window)}m; "
                    f"condition_group={cond_group}; track_aliases={','.join(sorted(aliases))}"
                ),
                **audit_counts,
            }

    field_target, field_sample, field_note = field_strength_target(race_rows, official_runs, race_date)
    if not math.isnan(field_target):
        return {
            "target_rating": field_target,
            "target_method": "CURRENT_FIELD_RECENT_OFFICIAL_RATINGS",
            "target_confidence": "LOW",
            "sample_size": field_sample,
            "notes": field_note,
            **audit_counts,
        }

    global_ratings = [float(run["rating_num"]) for run in history]
    global_target = target_from_ratings(global_ratings) if len(global_ratings) >= 20 else math.nan
    return {
        "target_rating": global_target if not math.isnan(global_target) else "",
        "target_method": "GLOBAL_OFFICIAL_WINNERS" if not math.isnan(global_target) else "NO_TARGET",
        "target_confidence": "LOW",
        "sample_size": len(global_ratings) if not math.isnan(global_target) else 0,
        "notes": "weak transparent fallback; no comparable sample or field-strength sample available",
        **audit_counts,
    }


def main() -> None:
    official_runs = prepare_runs()
    winner_runs = [run for run in official_runs if run.get("is_winner")]
    fields = prepare_current_fields()

    output_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []

    for race in current_races(fields):
        race_rows = rows_for_race(fields, race)
        selected = select_target(race, race_rows, official_runs, winner_runs)
        distance = to_num(race.get("distance"))
        class_distance_band = f"{class_band(race.get('race_class'))}_{distance_band(distance)}"
        row = {
            "race_date": clean_text(race.get("race_date")),
            "track": clean_text(race.get("track")),
            "race_no": clean_text(race.get("race_no")),
            "distance": clean_text(race.get("distance")),
            "race_class": clean_text(race.get("race_class")),
            "track_condition": clean_text(race.get("track_condition")),
            "target_rating": selected["target_rating"],
            "target_method": selected["target_method"],
            "target_confidence": selected["target_confidence"],
            "sample_size": selected["sample_size"],
            "class_distance_band": class_distance_band,
            "notes": selected["notes"],
        }
        output_rows.append(row)
        audit_rows.append(
            {
                **row,
                "official_rated_runs": len(official_runs),
                "official_winner_runs": len(winner_runs),
                "current_field_runners": len(race_rows),
                "track_class_distance_condition_winners_sample": selected.get(
                    "track_class_distance_condition_winners_sample", 0
                ),
                "class_distance_condition_winners_sample": selected.get(
                    "class_distance_condition_winners_sample", 0
                ),
                "class_distance_winners_sample": selected.get("class_distance_winners_sample", 0),
                "distance_condition_winners_sample": selected.get("distance_condition_winners_sample", 0),
                "distance_winners_sample": selected.get("distance_winners_sample", 0),
            }
        )

    write_csv(OUT, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_OUT, audit_rows, OUTPUT_COLUMNS + AUDIT_EXTRA_COLUMNS)

    sandown_r1 = [
        row
        for row in output_rows
        if upper_clean(row.get("track")) == "SANDOWN LAKESIDE" and clean_text(row.get("race_no")) == "1"
    ]

    print("=" * 100)
    print("EDGEIQ RACE RATING TARGETS V1")
    print("=" * 100)
    print(f"official_rated_runs={len(official_runs)}")
    print(f"official_winner_runs={len(winner_runs)}")
    print(f"target_rows={len(output_rows)}")
    print()
    if sandown_r1:
        row = sandown_r1[0]
        print("SANDOWN LAKESIDE R1")
        print(
            "race_date={race_date} track={track} race_no={race_no} "
            "target_rating={target_rating} method={target_method} "
            "confidence={target_confidence} sample_size={sample_size}".format(**row)
        )
        print()

    method_counts: dict[tuple[str, str], int] = {}
    for row in output_rows:
        key = (clean_text(row["target_method"]), clean_text(row["target_confidence"]))
        method_counts[key] = method_counts.get(key, 0) + 1
    print("TARGET METHOD COUNTS")
    for (method, confidence), count in sorted(method_counts.items()):
        print(f"{method},{confidence},{count}")
    print()
    print(f"SAVED: {OUT}")
    print(f"SAVED: {AUDIT_OUT}")


if __name__ == "__main__":
    main()
