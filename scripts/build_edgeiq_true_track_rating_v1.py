from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_VARIANT = DATA / "edgeiq_track_variant_engine_v1.csv"
INPUT_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"

OUTPUT_MAIN = DATA / "edgeiq_true_track_rating_v1.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_true_track_rating_v1_summary.csv"
OUTPUT_AUDIT = DATA / "edgeiq_true_track_rating_v1_audit.csv"

TRACK_LADDER = [
    "FIRM1",
    "FIRM2",
    "GOOD3",
    "GOOD4",
    "SOFT5",
    "SOFT6",
    "SOFT7",
    "HEAVY8",
    "HEAVY9",
    "HEAVY10",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upper(value: object) -> str:
    return clean(value).upper()


def parse_float(value: object) -> Optional[float]:
    txt = clean(value)
    if txt == "":
        return None
    txt = txt.replace("$", "").replace("kg", "").replace(",", "")
    try:
        return float(txt)
    except Exception:
        return None


def normalize_condition_family(value: object) -> str:
    txt = upper(value)
    if txt == "":
        return "UNKNOWN"
    if "HEAVY" in txt:
        return "HEAVY"
    if "SOFT" in txt:
        return "SOFT"
    if "GOOD" in txt:
        return "GOOD"
    if "FIRM" in txt:
        return "FIRM"
    if "SYNTH" in txt or "POLY" in txt or "TAPETA" in txt or "ALL WEATHER" in txt:
        return "SYNTH"
    if txt in {"3", "4"}:
        return "GOOD"
    if txt in {"5", "6", "7"}:
        return "SOFT"
    if txt in {"8", "9", "10"}:
        return "HEAVY"
    return "UNKNOWN"


def official_notch(condition_text: str, track_rating_value: str) -> Tuple[str, Optional[int]]:
    family = normalize_condition_family(condition_text)
    numeric = parse_float(track_rating_value)
    if numeric is None:
        digits = "".join(ch for ch in clean(condition_text) if ch.isdigit())
        numeric = parse_float(digits) if digits else None

    if family == "SYNTH":
        return "SYNTH", None

    if numeric is None:
        defaults = {"FIRM": 2, "GOOD": 4, "SOFT": 6, "HEAVY": 8}
        numeric = defaults.get(family)

    if numeric is None:
        return family, None

    number = int(round(numeric))
    label = f"{family}{number}"
    if label not in TRACK_LADDER:
        if family == "GOOD":
            label = "GOOD4" if number >= 4 else "GOOD3"
        elif family == "SOFT":
            label = "SOFT7" if number >= 7 else "SOFT5" if number <= 5 else "SOFT6"
        elif family == "HEAVY":
            label = "HEAVY10" if number >= 10 else "HEAVY9" if number == 9 else "HEAVY8"
        elif family == "FIRM":
            label = "FIRM2" if number >= 2 else "FIRM1"
    return label, int(round(numeric))


def shift_notches(meeting_variant_sec: Optional[float]) -> int:
    if meeting_variant_sec is None:
        return 0
    if meeting_variant_sec <= -1.0:
        return -2
    if meeting_variant_sec <= -0.35:
        return -1
    if meeting_variant_sec < 0.35:
        return 0
    if meeting_variant_sec < 1.0:
        return 1
    return 2


def true_track_from_official(official_label: str, meeting_variant_sec: Optional[float]) -> str:
    if official_label == "SYNTH":
        return "SYNTH"
    if official_label not in TRACK_LADDER:
        return official_label or "UNKNOWN"
    index = TRACK_LADDER.index(official_label)
    shifted = max(0, min(len(TRACK_LADDER) - 1, index + shift_notches(meeting_variant_sec)))
    return TRACK_LADDER[shifted]


def true_track_band(official_label: str, true_label: str) -> str:
    if official_label == "" or true_label == "":
        return "UNKNOWN"
    if official_label == "SYNTH" and true_label == "SYNTH":
        return "SYNTHETIC"
    if official_label not in TRACK_LADDER or true_label not in TRACK_LADDER:
        return "UNKNOWN"
    diff = TRACK_LADDER.index(true_label) - TRACK_LADDER.index(official_label)
    if diff <= -2:
        return "MUCH_FIRMER_THAN_OFFICIAL"
    if diff == -1:
        return "FIRMER_THAN_OFFICIAL"
    if diff == 0:
        return "ALIGNED_WITH_OFFICIAL"
    if diff == 1:
        return "SOFTER_THAN_OFFICIAL"
    return "MUCH_SOFTER_THAN_OFFICIAL"


def confidence_band(evidence_status: str, timed_races: int, meeting_variant_sec: Optional[float]) -> str:
    if evidence_status == "NO_STANDARD" or meeting_variant_sec is None:
        return "LOW"
    magnitude = abs(meeting_variant_sec)
    if timed_races >= 6 and magnitude >= 0.35:
        return "HIGH"
    if timed_races >= 4:
        return "MEDIUM"
    return "LOW"


def narrative(official: str, true_track: str, meeting_variant_sec: Optional[float], timed_races: int) -> str:
    if meeting_variant_sec is None:
        return "Track reading unavailable because meeting variant evidence was missing."
    direction = "faster" if meeting_variant_sec < 0 else "slower" if meeting_variant_sec > 0 else "in line with"
    return (
        f"Official reading was {official or 'UNKNOWN'}. Meeting played {abs(meeting_variant_sec):.2f}s {direction} "
        f"historical expectation across {timed_races} timed races, giving a true read of {true_track or 'UNKNOWN'}."
    )


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    if not INPUT_VARIANT.exists():
        raise FileNotFoundError(INPUT_VARIANT)
    if not INPUT_RESULTS.exists():
        raise FileNotFoundError(INPUT_RESULTS)

    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    variant_meetings: Dict[Tuple[str, str], Dict[str, object]] = {}
    with INPUT_VARIANT.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (clean(row.get("race_date")), upper(row.get("track")))
            if key not in variant_meetings:
                variant_meetings[key] = {
                    "race_date": key[0],
                    "track": key[1],
                    "meeting_variant_sec": parse_float(row.get("meeting_variant_sec")),
                    "evidence_status": clean(row.get("evidence_status")),
                    "timed_races_in_meeting": int(parse_float(row.get("timed_races_in_meeting")) or 0),
                    "condition_votes": Counter(),
                }
            cond = clean(row.get("condition_official"))
            if cond:
                variant_meetings[key]["condition_votes"][cond] += 1

    meeting_meta: DefaultDict[Tuple[str, str], Dict[str, Counter]] = defaultdict(lambda: {"track_condition": Counter(), "track_rating": Counter()})
    with INPUT_RESULTS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (clean(row.get("race_date")), upper(row.get("track")))
            if key not in variant_meetings:
                continue
            condition = clean(row.get("track_condition"))
            rating = clean(row.get("track_rating"))
            if condition:
                meeting_meta[key]["track_condition"][condition] += 1
            if rating:
                meeting_meta[key]["track_rating"][rating] += 1

    output_rows: List[Dict[str, object]] = []
    for key, row in sorted(variant_meetings.items()):
        condition_votes = row["condition_votes"]
        condition_mode = condition_votes.most_common(1)[0][0] if condition_votes else ""
        track_condition_mode = meeting_meta[key]["track_condition"].most_common(1)[0][0] if meeting_meta[key]["track_condition"] else condition_mode
        track_rating_mode = meeting_meta[key]["track_rating"].most_common(1)[0][0] if meeting_meta[key]["track_rating"] else ""
        official_label, _ = official_notch(track_condition_mode or condition_mode, track_rating_mode)
        meeting_variant_sec = row["meeting_variant_sec"]
        true_label = true_track_from_official(official_label, meeting_variant_sec)
        band = true_track_band(official_label, true_label)
        confidence = confidence_band(clean(row.get("evidence_status")), int(row.get("timed_races_in_meeting") or 0), meeting_variant_sec)

        output_rows.append(
            {
                "race_date": row["race_date"],
                "track": row["track"],
                "official_condition": official_label or track_condition_mode or condition_mode or "UNKNOWN",
                "edgeiq_true_track_rating": true_label or "UNKNOWN",
                "true_track_band": band,
                "variant_sec": f"{meeting_variant_sec:.3f}" if meeting_variant_sec is not None else "",
                "confidence_band": confidence,
                "track_rating_narrative": narrative(
                    official=official_label or track_condition_mode or condition_mode or "UNKNOWN",
                    true_track=true_label or "UNKNOWN",
                    meeting_variant_sec=meeting_variant_sec,
                    timed_races=int(row.get("timed_races_in_meeting") or 0),
                ),
                "timed_races_in_meeting": row["timed_races_in_meeting"],
                "variant_evidence_status": row["evidence_status"],
                "built_at": built_at,
            }
        )

    band_counts = Counter(clean(row.get("true_track_band")) for row in output_rows)
    confidence_counts = Counter(clean(row.get("confidence_band")) for row in output_rows)

    summary_row = {
        "status": "EDGEIQ_TRUE_TRACK_RATING_V1_BUILT",
        "meeting_rows": len(output_rows),
        "aligned_count": band_counts.get("ALIGNED_WITH_OFFICIAL", 0),
        "firmer_count": band_counts.get("FIRMER_THAN_OFFICIAL", 0) + band_counts.get("MUCH_FIRMER_THAN_OFFICIAL", 0),
        "softer_count": band_counts.get("SOFTER_THAN_OFFICIAL", 0) + band_counts.get("MUCH_SOFTER_THAN_OFFICIAL", 0),
        "unknown_count": band_counts.get("UNKNOWN", 0),
        "high_confidence_count": confidence_counts.get("HIGH", 0),
        "medium_confidence_count": confidence_counts.get("MEDIUM", 0),
        "low_confidence_count": confidence_counts.get("LOW", 0),
        "readiness_verdict": "READY_FOR_EPF" if len(output_rows) > 0 and confidence_counts.get("HIGH", 0) + confidence_counts.get("MEDIUM", 0) > 0 else "LIMITED",
        "built_at": built_at,
    }

    audit_rows = []
    for name, count in sorted(band_counts.items()):
        audit_rows.append({"audit_type": "TRUE_TRACK_BAND", "audit_value": name, "count": count, "built_at": built_at})
    for name, count in sorted(confidence_counts.items()):
        audit_rows.append({"audit_type": "CONFIDENCE_BAND", "audit_value": name, "count": count, "built_at": built_at})

    output_fields = [
        "race_date",
        "track",
        "official_condition",
        "edgeiq_true_track_rating",
        "true_track_band",
        "variant_sec",
        "confidence_band",
        "track_rating_narrative",
        "timed_races_in_meeting",
        "variant_evidence_status",
        "built_at",
    ]
    write_csv(OUTPUT_MAIN, output_rows, output_fields)
    write_csv(OUTPUT_SUMMARY, [summary_row], list(summary_row.keys()))
    write_csv(OUTPUT_AUDIT, audit_rows, ["audit_type", "audit_value", "count", "built_at"])

    print("EDGEiQ True Track Rating V1 built")
    print(f"Meeting rows: {len(output_rows)}")
    print(f"Readiness: {summary_row['readiness_verdict']}")


if __name__ == "__main__":
    main()
