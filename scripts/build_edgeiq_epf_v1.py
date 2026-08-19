from __future__ import annotations

import csv
import heapq
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
INPUT_VARIANT = DATA / "edgeiq_track_variant_engine_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_epf_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_epf_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_epf_v1_audit.csv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def clean_horse(value: object) -> str:
    txt = upper(value)
    return "".join(ch for ch in txt if ch.isalnum())


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "").replace("L", "").replace("l", "")
    try:
        return float(txt)
    except Exception:
        return None


def parse_time_to_seconds(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("s", "").replace("S", "")
    if ":" in txt:
        parts = txt.split(":")
        try:
            if len(parts) == 2:
                return (float(parts[0]) * 60.0) + float(parts[1])
            if len(parts) == 3:
                return (float(parts[0]) * 3600.0) + (float(parts[1]) * 60.0) + float(parts[2])
        except Exception:
            return None
    numeric = parse_float(txt)
    if numeric is None:
        return None
    if numeric > 1000:
        return numeric / 100.0
    return numeric


def parse_distance_m(value: object) -> Optional[int]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("m", "").replace("M", "").replace(",", "")
    try:
        return int(round(float(txt)))
    except Exception:
        return None


def parse_race_no(value: object) -> str:
    number = parse_float(value)
    if number is None:
        return clean(value)
    return str(int(round(number)))


def lengths_per_second(distance_m: Optional[int]) -> float:
    if distance_m is None:
        return 5.5
    if distance_m <= 1000:
        return 6.5
    if distance_m <= 1400:
        return 6.0
    if distance_m <= 1800:
        return 5.5
    if distance_m <= 2200:
        return 5.0
    return 4.5


def epf_band(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
    if value >= 10.0:
        return "EXCEPTIONAL"
    if value >= 7.0:
        return "ELITE"
    if value >= 4.0:
        return "STRONG"
    if value >= 2.0:
        return "ABOVE_AVG"
    if value > -2.0:
        return "STANDARD"
    if value > -5.0:
        return "BELOW_AVG"
    return "POOR"


def epf_narrative(epf_value: Optional[float], finish_position: str, variant_sec: Optional[float]) -> str:
    if epf_value is None:
        return "EPF unavailable because time, variant, or beaten-margin evidence was incomplete."
    direction = "above" if epf_value >= 0 else "below"
    variant_note = ""
    if variant_sec is not None:
        variant_note = f" after {variant_sec:+.2f}s track-variant adjustment"
    return (
        f"Finished {finish_position or 'N/A'} and rated {abs(epf_value):.1f}L {direction} historical standard"
        f"{variant_note}."
    )


def is_flat_race(row: Dict[str, str]) -> bool:
    raw = " ".join([upper(row.get("race_class")), upper(row.get("race_name"))]).strip()
    if raw == "":
        return True
    blocked_tokens = ["TRIAL", "HURDLE", "STEEPLE", "JUMP", "CHASE", "H'CAP HURDLE", "H'CAP STEEPLE"]
    return not any(token in raw for token in blocked_tokens)


def evidence_status(
    standard_time_sec: Optional[float],
    winning_time_sec: Optional[float],
    meeting_variant_sec: Optional[float],
    margin_l: Optional[float],
    finish_position: Optional[int],
) -> str:
    if standard_time_sec is None:
        return "NO_STANDARD"
    if winning_time_sec is None:
        return "NO_TIME"
    if meeting_variant_sec is None:
        return "NO_VARIANT"
    if finish_position == 1:
        return "READY"
    if margin_l is None:
        return "NO_MARGIN"
    return "READY"


def is_finished(row: Dict[str, str]) -> bool:
    scratched = upper(row.get("scratched"))
    if scratched in {"TRUE", "YES", "1"}:
        return False
    finish_num = parse_float(row.get("finish_num") or row.get("finish"))
    return finish_num is not None and finish_num > 0


def top_record_tuple(row: Dict[str, object]) -> Tuple[float, str]:
    value = float(row.get("epf_lengths") or 0.0)
    identity = "|".join([clean(row.get("race_date")), clean(row.get("track")), clean(row.get("race_no")), clean(row.get("horse"))])
    return (value, identity)


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not INPUT_RESULTS.exists():
        raise FileNotFoundError(INPUT_RESULTS)
    if not INPUT_VARIANT.exists():
        raise FileNotFoundError(INPUT_VARIANT)

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    race_meta: Dict[Tuple[str, str, str], Dict[str, str]] = {}
    with INPUT_VARIANT.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (clean(row.get("race_date")), upper(row.get("track")), parse_race_no(row.get("race_no")))
            race_meta[key] = row

    band_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    total_rows = 0
    ready_rows = 0
    top_heap: List[Tuple[float, str, Dict[str, object]]] = []
    bottom_heap: List[Tuple[float, str, Dict[str, object]]] = []

    fieldnames = [
        "race_date",
        "track",
        "race_no",
        "horse",
        "horse_key",
        "distance",
        "finish_position",
        "beaten_margin",
        "winner_time_sec",
        "estimated_runner_time_sec",
        "standard_time_sec",
        "track_variant_sec",
        "epf_lengths",
        "epf_band",
        "epf_narrative",
        "evidence_status",
        "condition_official",
        "rail_position",
        "source_file",
        "built_at",
    ]

    with OUTPUT_MAIN.open("w", encoding="utf-8", newline="") as out_handle:
        writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
        writer.writeheader()

        with INPUT_RESULTS.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if not is_finished(row):
                    continue
                if not is_flat_race(row):
                    continue

                race_date = clean(row.get("race_date"))
                track = upper(row.get("track"))
                race_no = parse_race_no(row.get("race_no"))
                key = (race_date, track, race_no)
                race_row = race_meta.get(key, {})

                distance_m = parse_distance_m(row.get("distance"))
                finish_position_num = int(round(parse_float(row.get("finish_num") or row.get("finish")) or 0))
                margin_l = parse_float(row.get("margin_l") or row.get("margin"))
                winning_time_sec = parse_time_to_seconds(race_row.get("actual_winner_time_sec"))
                if winning_time_sec is None:
                    winning_time_sec = parse_time_to_seconds(row.get("winning_time"))
                standard_time_sec = parse_float(race_row.get("standard_time_sec"))
                meeting_variant_sec = parse_float(race_row.get("meeting_variant_sec"))

                if finish_position_num == 1 and margin_l is None:
                    margin_l = 0.0

                lps = lengths_per_second(distance_m)
                estimated_runner_time_sec = None
                if winning_time_sec is not None:
                    if finish_position_num == 1:
                        estimated_runner_time_sec = winning_time_sec
                    elif margin_l is not None:
                        estimated_runner_time_sec = winning_time_sec + (margin_l / lps)

                status = evidence_status(
                    standard_time_sec=standard_time_sec,
                    winning_time_sec=winning_time_sec,
                    meeting_variant_sec=meeting_variant_sec,
                    margin_l=margin_l,
                    finish_position=finish_position_num,
                )

                epf_value = None
                if status == "READY" and estimated_runner_time_sec is not None and standard_time_sec is not None and meeting_variant_sec is not None:
                    adjusted_runner_time = estimated_runner_time_sec - meeting_variant_sec
                    epf_value = round((standard_time_sec - adjusted_runner_time) * lps, 3)

                epf_value_text = f"{epf_value:.3f}" if epf_value is not None else ""
                band = epf_band(epf_value)

                out_row: Dict[str, object] = {
                    "race_date": race_date,
                    "track": track,
                    "race_no": race_no,
                    "horse": clean(row.get("horse")),
                    "horse_key": clean_horse(row.get("horse")),
                    "distance": distance_m if distance_m is not None else clean(row.get("distance")),
                    "finish_position": finish_position_num if finish_position_num > 0 else "",
                    "beaten_margin": f"{margin_l:.3f}" if margin_l is not None else "",
                    "winner_time_sec": f"{winning_time_sec:.3f}" if winning_time_sec is not None else "",
                    "estimated_runner_time_sec": f"{estimated_runner_time_sec:.3f}" if estimated_runner_time_sec is not None else "",
                    "standard_time_sec": f"{standard_time_sec:.3f}" if standard_time_sec is not None else "",
                    "track_variant_sec": f"{meeting_variant_sec:.3f}" if meeting_variant_sec is not None else "",
                    "epf_lengths": epf_value_text,
                    "epf_band": band,
                    "epf_narrative": epf_narrative(epf_value, str(finish_position_num), meeting_variant_sec),
                    "evidence_status": status,
                    "condition_official": clean(race_row.get("condition_official")) or clean(row.get("track_condition")),
                    "rail_position": clean(race_row.get("rail_position")) or clean(row.get("rail_position")),
                    "source_file": clean(row.get("source_file")) or INPUT_RESULTS.name,
                    "built_at": built_at,
                }
                writer.writerow(out_row)

                total_rows += 1
                band_counts[band] += 1
                status_counts[status] += 1
                if status == "READY" and epf_value is not None:
                    ready_rows += 1
                    identity = "|".join([race_date, track, race_no, clean(row.get("horse"))])
                    heapq.heappush(top_heap, (epf_value, identity, out_row))
                    if len(top_heap) > 10:
                        heapq.heappop(top_heap)
                    heapq.heappush(bottom_heap, (-epf_value, identity, out_row))
                    if len(bottom_heap) > 10:
                        heapq.heappop(bottom_heap)

    top_examples = sorted(top_heap, key=lambda item: (item[0], item[1]), reverse=True)
    poor_examples = sorted([(-value, ident, row) for value, ident, row in bottom_heap], key=lambda item: (item[0], item[1]))

    summary_row = {
        "status": "EDGEIQ_EPF_V1_BUILT",
        "input_results_file": INPUT_RESULTS.name,
        "input_variant_file": INPUT_VARIANT.name,
        "total_finished_rows": total_rows,
        "ready_rows": ready_rows,
        "coverage_pct": f"{(ready_rows / total_rows * 100.0):.3f}" if total_rows else "",
        "exceptional_count": band_counts.get("EXCEPTIONAL", 0),
        "elite_count": band_counts.get("ELITE", 0),
        "strong_count": band_counts.get("STRONG", 0),
        "above_avg_count": band_counts.get("ABOVE_AVG", 0),
        "standard_count": band_counts.get("STANDARD", 0),
        "below_avg_count": band_counts.get("BELOW_AVG", 0),
        "poor_count": band_counts.get("POOR", 0),
        "unknown_count": band_counts.get("UNKNOWN", 0),
        "no_standard_rows": status_counts.get("NO_STANDARD", 0),
        "no_time_rows": status_counts.get("NO_TIME", 0),
        "no_variant_rows": status_counts.get("NO_VARIANT", 0),
        "no_margin_rows": status_counts.get("NO_MARGIN", 0),
        "readiness_verdict": "READY_FOR_CURRENT_FEED" if ready_rows > 50000 else "LIMITED",
        "built_at": built_at,
    }

    audit_rows: List[Dict[str, object]] = []
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "EPF_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(status_counts.items()):
        audit_rows.append({"audit_type": "EVIDENCE_STATUS", "audit_value": name, "count": count, "built_at": built_at})
    for rank, (_, _, row) in enumerate(top_examples, start=1):
        audit_rows.append(
            {
                "audit_type": "TOP_EPF_EXAMPLE",
                "audit_value": f"{rank}. {row['horse']} {row['epf_lengths']}L {row['race_date']} {row['track']} R{row['race_no']}",
                "count": "",
                "built_at": built_at,
            }
        )
    for rank, (_, _, row) in enumerate(poor_examples, start=1):
        audit_rows.append(
            {
                "audit_type": "POOR_EPF_EXAMPLE",
                "audit_value": f"{rank}. {row['horse']} {row['epf_lengths']}L {row['race_date']} {row['track']} R{row['race_no']}",
                "count": "",
                "built_at": built_at,
            }
        )

    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ EPF V1 built")
    print(f"Finished rows: {total_rows}")
    print(f"Ready rows: {ready_rows}")
    print(f"Readiness: {summary_row['readiness_verdict']}")


if __name__ == "__main__":
    main()
