from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
INPUT_HISTORY = DATA / "edgeiq_historical_run_ratings_master_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_recency_weighted_profile_engine_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_recency_weighted_profile_engine_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_recency_weighted_profile_engine_v1_audit.csv"

HALF_LIFE_DAYS = 730.5
DECAY_COEFFICIENT = 0.69315


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def clean_horse(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def to_float(value: object, default: Optional[float] = None) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return default
    try:
        return float(txt)
    except Exception:
        return default


def to_int(value: object, default: Optional[int] = None) -> Optional[int]:
    num = to_float(value, None)
    if num is None:
        return default
    try:
        return int(round(num))
    except Exception:
        return default


def parse_date(value: object) -> Optional[datetime]:
    txt = clean(value)
    if txt == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def is_scratched(row: Dict[str, str]) -> bool:
    flags = [
        upper(row.get("is_scratched")),
        upper(row.get("scratch_status")),
        upper(row.get("runner_status")),
    ]
    return any(flag in {"1", "TRUE", "YES", "Y", "SCRATCHED", "LATE_SCRATCHING"} for flag in flags)


def runner_key(row: Dict[str, str]) -> str:
    return clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))


def history_key(row: Dict[str, str]) -> str:
    return clean_horse(row.get("horse_key")) or clean_horse(row.get("horse"))


def weighted_average(values: List[Tuple[float, float]]) -> Optional[float]:
    usable = [(value, weight) for value, weight in values if value is not None and weight > 0]
    if not usable:
        return None
    total_weight = sum(weight for _, weight in usable)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in usable) / total_weight


def weighted_mode(values: List[Tuple[str, float]]) -> str:
    scores: Dict[str, float] = defaultdict(float)
    for value, weight in values:
        if clean(value) == "" or weight <= 0:
            continue
        scores[clean(value)] += weight
    if not scores:
        return ""
    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def race_date_of(row: Dict[str, str]) -> str:
    return clean(row.get("race_date")) or clean(row.get("_date"))


def track_of(row: Dict[str, str]) -> str:
    return upper(row.get("track")) or upper(row.get("_track"))


def race_no_of(row: Dict[str, str]) -> str:
    return clean(row.get("race_no")) or clean(row.get("_race"))


def build_narrative(
    history_runs_used: int,
    rated_runs_used: int,
    recent_evidence_band: str,
    recency_weighted_rating: Optional[float],
    recency_weighted_class: str,
    recency_weighted_distance: Optional[float],
) -> str:
    if recent_evidence_band == "NO_HISTORY":
        return "No rated historical runs matched for the recency-weighted profile."

    rating_txt = f"{recency_weighted_rating:.1f}" if recency_weighted_rating is not None else "N/A"
    distance_txt = f"{recency_weighted_distance:.0f}m" if recency_weighted_distance is not None else "distance N/A"
    class_txt = recency_weighted_class if recency_weighted_class else "class mixed"

    if recent_evidence_band == "STRONG":
        return (
            f"Recency profile draws on {rated_runs_used} rated runs ({history_runs_used} total), "
            f"with weighted figure {rating_txt}, dominant class {class_txt}, and weighted distance {distance_txt}."
        )

    if recent_evidence_band == "MODERATE":
        return (
            f"Recency profile is usable from {rated_runs_used} rated runs; weighted figure {rating_txt}, "
            f"class lean {class_txt}, weighted distance {distance_txt}."
        )

    return (
        f"Recency profile is limited from {max(rated_runs_used, history_runs_used)} matched runs; "
        f"weighted figure {rating_txt}, class lean {class_txt}."
    )


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    board_rows = [row for row in csv_rows(INPUT_BOARD) if not is_scratched(row)]
    history_rows = csv_rows(INPUT_HISTORY)

    history_by_key: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    history_by_name: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for row in history_rows:
        key = clean_horse(row.get("horse_key"))
        name_key = clean_horse(row.get("horse"))
        if key:
            history_by_key[key].append(row)
        if name_key:
            history_by_name[name_key].append(row)

    output_rows: List[Dict[str, object]] = []
    audit_rows: List[Dict[str, object]] = []

    for board_row in board_rows:
        current_runner_key = runner_key(board_row)
        current_name_key = clean_horse(board_row.get("horse"))
        current_race_date = parse_date(race_date_of(board_row))

        candidates: List[Dict[str, str]] = []
        match_method = "NONE"

        if current_runner_key and current_runner_key in history_by_key:
            candidates.extend(history_by_key[current_runner_key])
            match_method = "HORSE_KEY"
        elif current_name_key and current_name_key in history_by_name:
            candidates.extend(history_by_name[current_name_key])
            match_method = "HORSE_NAME"

        if current_runner_key and current_name_key and current_runner_key != current_name_key:
            seen = {
                (
                    clean(row.get("race_date")),
                    upper(row.get("track")),
                    clean(row.get("race_no")),
                    clean_horse(row.get("horse")),
                )
                for row in candidates
            }
            for row in history_by_name.get(current_name_key, []):
                key = (
                    clean(row.get("race_date")),
                    upper(row.get("track")),
                    clean(row.get("race_no")),
                    clean_horse(row.get("horse")),
                )
                if key not in seen:
                    candidates.append(row)
                    seen.add(key)
                    if match_method == "HORSE_KEY":
                        match_method = "HORSE_KEY+NAME"

        usable_rows: List[Tuple[Dict[str, str], datetime, float]] = []
        for hist_row in candidates:
            hist_date = parse_date(hist_row.get("race_date"))
            if hist_date is None or current_race_date is None:
                continue
            if hist_date >= current_race_date:
                continue
            days_diff = (current_race_date - hist_date).days
            if days_diff < 0:
                continue
            weight = math.exp((-days_diff / HALF_LIFE_DAYS) * DECAY_COEFFICIENT)
            usable_rows.append((hist_row, hist_date, weight))

        usable_rows.sort(key=lambda item: item[1], reverse=True)

        history_runs_used = len(usable_rows)
        rated_rows = [(row, dt, weight) for row, dt, weight in usable_rows if to_float(row.get("performance_rating"), None) is not None]
        rated_runs_used = len(rated_rows)

        recency_weighted_rating = weighted_average(
            [(to_float(row.get("performance_rating"), None), weight) for row, _, weight in rated_rows]
        )
        recency_weighted_lbw = weighted_average(
            [(to_float(row.get("margin"), None), weight) for row, _, weight in usable_rows]
        )
        recency_weighted_finish_position = weighted_average(
            [(to_float(row.get("finish_pos"), None), weight) for row, _, weight in usable_rows]
        )
        recency_weighted_distance = weighted_average(
            [(to_float(row.get("distance"), None), weight) for row, _, weight in usable_rows]
        )
        recency_weighted_field_size = weighted_average(
            [(to_float(row.get("field_size"), None), weight) for row, _, weight in usable_rows]
        )
        recency_weighted_class = weighted_mode(
            [(clean(row.get("class_name")), weight) for row, _, weight in usable_rows]
        )
        history_weight_total = round(sum(weight for _, _, weight in usable_rows), 6)

        if rated_runs_used >= 8 and history_weight_total >= 2.5:
            recent_evidence_band = "STRONG"
        elif rated_runs_used >= 4 and history_weight_total >= 1.25:
            recent_evidence_band = "MODERATE"
        elif rated_runs_used >= 1:
            recent_evidence_band = "LIMITED"
        else:
            recent_evidence_band = "NO_HISTORY"

        latest_history_date = usable_rows[0][1].date().isoformat() if usable_rows else ""
        earliest_history_date = usable_rows[-1][1].date().isoformat() if usable_rows else ""
        days_since_last_run = (current_race_date - usable_rows[0][1]).days if usable_rows and current_race_date else ""

        recency_profile_narrative = build_narrative(
            history_runs_used=history_runs_used,
            rated_runs_used=rated_runs_used,
            recent_evidence_band=recent_evidence_band,
            recency_weighted_rating=recency_weighted_rating,
            recency_weighted_class=recency_weighted_class,
            recency_weighted_distance=recency_weighted_distance,
        )

        output_rows.append(
            {
                "race_date": race_date_of(board_row),
                "track": track_of(board_row),
                "race_no": race_no_of(board_row),
                "horse": clean(board_row.get("horse")),
                "horse_key": clean(board_row.get("horse_key")),
                "recency_weighted_rating": round(recency_weighted_rating, 4) if recency_weighted_rating is not None else "",
                "recency_weighted_lbw": round(recency_weighted_lbw, 4) if recency_weighted_lbw is not None else "",
                "recency_weighted_finish_position": round(recency_weighted_finish_position, 4) if recency_weighted_finish_position is not None else "",
                "recency_weighted_class": recency_weighted_class,
                "recency_weighted_distance": round(recency_weighted_distance, 4) if recency_weighted_distance is not None else "",
                "recency_weighted_field_size": round(recency_weighted_field_size, 4) if recency_weighted_field_size is not None else "",
                "history_weight_total": history_weight_total,
                "history_runs_used": history_runs_used,
                "rated_runs_used": rated_runs_used,
                "recent_evidence_band": recent_evidence_band,
                "recency_profile_narrative": recency_profile_narrative,
                "history_match_method": match_method,
                "latest_history_date": latest_history_date,
                "built_at": built_at,
            }
        )

        audit_rows.append(
            {
                "race_date": race_date_of(board_row),
                "track": track_of(board_row),
                "race_no": race_no_of(board_row),
                "horse": clean(board_row.get("horse")),
                "horse_key": clean(board_row.get("horse_key")),
                "history_rows_found": history_runs_used,
                "rated_history_rows": rated_runs_used,
                "latest_history_date": latest_history_date,
                "earliest_history_date": earliest_history_date,
                "days_since_last_run": days_since_last_run,
                "history_match_method": match_method,
                "recent_evidence_band": recent_evidence_band,
                "source_status": "MATCHED" if history_runs_used > 0 else "NO_HISTORY",
                "built_at": built_at,
            }
        )

    avg_weighted_rating = weighted_average(
        [
            (to_float(row.get("recency_weighted_rating"), None), 1.0)
            for row in output_rows
            if clean(row.get("recency_weighted_rating")) != ""
        ]
    )

    summary_rows = [
        {"metric": "status", "value": "READY_FOR_UI" if output_rows else "FAIL_NO_OUTPUT"},
        {"metric": "input_board_file", "value": str(INPUT_BOARD)},
        {"metric": "input_history_file", "value": str(INPUT_HISTORY)},
        {"metric": "built_at", "value": built_at},
        {"metric": "active_runner_rows", "value": len(board_rows)},
        {"metric": "history_rows", "value": len(history_rows)},
        {"metric": "output_rows", "value": len(output_rows)},
        {"metric": "matched_runners", "value": sum(1 for row in output_rows if int(row["history_runs_used"]) > 0)},
        {"metric": "rated_runners", "value": sum(1 for row in output_rows if int(row["rated_runs_used"]) > 0)},
        {"metric": "no_history_runners", "value": sum(1 for row in output_rows if row["recent_evidence_band"] == "NO_HISTORY")},
        {"metric": "strong_evidence_runners", "value": sum(1 for row in output_rows if row["recent_evidence_band"] == "STRONG")},
        {"metric": "moderate_evidence_runners", "value": sum(1 for row in output_rows if row["recent_evidence_band"] == "MODERATE")},
        {"metric": "limited_evidence_runners", "value": sum(1 for row in output_rows if row["recent_evidence_band"] == "LIMITED")},
        {"metric": "avg_recency_weighted_rating", "value": round(avg_weighted_rating, 4) if avg_weighted_rating is not None else ""},
    ]

    main_fields = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "recency_weighted_rating",
        "recency_weighted_lbw",
        "recency_weighted_finish_position",
        "recency_weighted_class",
        "recency_weighted_distance",
        "recency_weighted_field_size",
        "history_weight_total",
        "history_runs_used",
        "rated_runs_used",
        "recent_evidence_band",
        "recency_profile_narrative",
        "history_match_method",
        "latest_history_date",
        "built_at",
    ]
    audit_fields = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "history_rows_found",
        "rated_history_rows",
        "latest_history_date",
        "earliest_history_date",
        "days_since_last_run",
        "history_match_method",
        "recent_evidence_band",
        "source_status",
        "built_at",
    ]

    write_csv(OUTPUT_MAIN, output_rows, main_fields)
    write_csv(OUTPUT_AUDIT, audit_rows, audit_fields)
    write_csv(OUTPUT_SUMMARY, summary_rows, ["metric", "value"])

    print("[EDGEIQ_RECENCY_WEIGHTED_PROFILE_ENGINE_V1] COMPLETE")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")
    print(f"wrote={OUTPUT_AUDIT}")
    print(f"matched_runners={sum(1 for row in output_rows if int(row['history_runs_used']) > 0)}")
    print(f"rated_runners={sum(1 for row in output_rows if int(row['rated_runs_used']) > 0)}")


if __name__ == "__main__":
    main()
