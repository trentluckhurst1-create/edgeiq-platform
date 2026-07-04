from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_live_sectional_intelligence_v1.csv"
OUT = DATA / "edgeiq_sectional_intelligence_ui_feed_v1.csv"
AUDIT_OUT = DATA / "edgeiq_sectional_intelligence_ui_feed_v1_audit.csv"

OUTPUT_COLUMNS = [
    "meeting_date",
    "track",
    "race_no",
    "horse_name",
    "horse_key",
    "runner_number",
    "sectional_profile_found",
    "sectional_badge",
    "sectional_label",
    "sectional_archetype",
    "profile_depth_status",
    "sectional_evidence_type",
    "runs_with_sectionals",
    "sectional_strength_score",
    "sectional_confidence_score",
    "sectional_note",
    "sectional_risk_note",
    "sectional_display_status",
]

AUDIT_COLUMNS = [
    "input_rows_loaded",
    "output_rows",
    "profile_found_rows",
    "no_profile_rows",
    "sample_too_small_rows",
    "early_profile_rows",
    "strong_early_profile_rows",
    "dna_ready_rows",
    "final_status",
]

BADGE_BY_STATUS = {
    "NO_PROFILE": "NO DATA",
    "SAMPLE_TOO_SMALL": "LOW SAMPLE",
    "EARLY_PROFILE": "SECTIONAL",
    "STRONG_EARLY_PROFILE": "STRONG SECTIONAL",
    "DNA_READY": "DNA READY",
}

LABEL_BY_STATUS = {
    "NO_PROFILE": "No sectional data",
    "SAMPLE_TOO_SMALL": "Limited sectional sample",
    "EARLY_PROFILE": "Early sectional profile",
    "STRONG_EARLY_PROFILE": "Strong early sectional profile",
    "DNA_READY": "DNA-ready sectional profile",
}

BASE_STRENGTH_BY_STATUS = {
    "NO_PROFILE": 0,
    "SAMPLE_TOO_SMALL": 24,
    "EARLY_PROFILE": 56,
    "STRONG_EARLY_PROFILE": 76,
    "DNA_READY": 90,
}

BASE_CONFIDENCE_BY_STATUS = {
    "NO_PROFILE": 0,
    "SAMPLE_TOO_SMALL": 20,
    "EARLY_PROFILE": 44,
    "STRONG_EARLY_PROFILE": 64,
    "DNA_READY": 88,
}

EVIDENCE_STRENGTH_ADJUSTMENT = {
    "MIXED_SUMMARY_AND_SPLIT": 8,
    "SUMMARY_SPEED_ONLY": 4,
    "SPLIT_TIMING_ONLY": 3,
    "INSUFFICIENT": -10,
}

EVIDENCE_CONFIDENCE_ADJUSTMENT = {
    "MIXED_SUMMARY_AND_SPLIT": 10,
    "SUMMARY_SPEED_ONLY": 6,
    "SPLIT_TIMING_ONLY": 5,
    "INSUFFICIENT": -10,
}

ARCHETYPE_STRENGTH_ADJUSTMENT = {
    "FAST_STARTER": 4,
    "SUSTAINED_CRUISER": 5,
    "STRONG_CLOSER": 6,
    "PEAK_SPEED_HORSE": 6,
    "SPLIT_TIMING_CLOSER": 6,
    "SPLIT_TIMING_SPEED": 5,
    "CONSISTENT_SECTIONALIST": 6,
    "ONE_PACE_GRINDER": 1,
    "INSUFFICIENT_SAMPLE": -12,
}


def clean(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if text.upper() in {"NAN", "NONE", "NULL", "N/A", "NA", "-"}:
        return ""
    return re.sub(r"\s+", " ", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    tmp.replace(path)


def to_int(value: Any) -> int:
    text = clean(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def profile_status(row: dict[str, str]) -> str:
    status = clean(row.get("sectional_intelligence_status") or row.get("profile_depth_status")).upper()
    if status in BADGE_BY_STATUS:
        return status
    if clean(row.get("sectional_profile_found")).upper() != "TRUE":
        return "NO_PROFILE"
    return "NO_PROFILE"


def strength_score(status: str, evidence_type: str, archetype: str) -> str:
    if status == "NO_PROFILE":
        return "0"
    score = BASE_STRENGTH_BY_STATUS.get(status, 0)
    score += EVIDENCE_STRENGTH_ADJUSTMENT.get(evidence_type, 0)
    score += ARCHETYPE_STRENGTH_ADJUSTMENT.get(archetype, 0)
    if status == "SAMPLE_TOO_SMALL":
        score = min(score, 34)
    return str(clamp(score))


def confidence_score(status: str, evidence_type: str, runs_with_sectionals: int) -> str:
    if status == "NO_PROFILE":
        return "0"
    score = BASE_CONFIDENCE_BY_STATUS.get(status, 0)
    score += min(18, runs_with_sectionals * 3)
    score += EVIDENCE_CONFIDENCE_ADJUSTMENT.get(evidence_type, 0)
    if status == "SAMPLE_TOO_SMALL":
        score = min(score, 38)
    return str(clamp(score))


def note_for(status: str, evidence_type: str) -> str:
    if status == "NO_PROFILE":
        return "No sectional profile yet"
    if status == "SAMPLE_TOO_SMALL":
        return "Limited sample - treat cautiously"
    if evidence_type == "MIXED_SUMMARY_AND_SPLIT":
        return "Mixed summary and split evidence"
    if evidence_type == "SPLIT_TIMING_ONLY":
        return "Split timing profile - watch race-shape fit"
    if status == "STRONG_EARLY_PROFILE":
        return "Strong early sectional evidence"
    if status == "DNA_READY":
        return "DNA-ready sectional profile"
    return "Early sectional profile available"


def risk_note_for(status: str, evidence_type: str) -> str:
    if status == "NO_PROFILE":
        return "No sectional evidence"
    if status == "SAMPLE_TOO_SMALL":
        return "Low sample confidence"
    if evidence_type == "SPLIT_TIMING_ONLY":
        return "Split timing only - no summary speed profile"
    if evidence_type == "INSUFFICIENT":
        return "Incomplete sectional evidence"
    return ""


def build_rows(input_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in input_rows:
        status = profile_status(row)
        evidence_type = clean(row.get("sectional_evidence_type")).upper()
        archetype = clean(row.get("sectional_archetype")).upper()
        runs = to_int(row.get("runs_with_sectionals"))
        output.append(
            {
                "meeting_date": clean(row.get("meeting_date")),
                "track": clean(row.get("track")),
                "race_no": clean(row.get("race_no")),
                "horse_name": clean(row.get("horse_name")),
                "horse_key": clean(row.get("horse_key")),
                "runner_number": clean(row.get("runner_number")),
                "sectional_profile_found": "FALSE" if status == "NO_PROFILE" else "TRUE",
                "sectional_badge": BADGE_BY_STATUS.get(status, "NO DATA"),
                "sectional_label": LABEL_BY_STATUS.get(status, "No sectional data"),
                "sectional_archetype": archetype,
                "profile_depth_status": status if status != "NO_PROFILE" else "",
                "sectional_evidence_type": evidence_type,
                "runs_with_sectionals": str(runs) if runs else "",
                "sectional_strength_score": strength_score(status, evidence_type, archetype),
                "sectional_confidence_score": confidence_score(status, evidence_type, runs),
                "sectional_note": note_for(status, evidence_type),
                "sectional_risk_note": risk_note_for(status, evidence_type),
                "sectional_display_status": status,
            }
        )
    return output


def main() -> None:
    input_rows = read_csv(INPUT)
    output_rows = build_rows(input_rows) if input_rows else []
    counts = Counter(row.get("sectional_display_status", "") for row in output_rows)
    profile_found_rows = sum(1 for row in output_rows if row.get("sectional_profile_found") == "TRUE")

    if not input_rows:
        final_status = "NO_LIVE_SECTIONAL_INTELLIGENCE_FOUND"
    elif not output_rows:
        final_status = "NO_OUTPUT_ROWS"
    else:
        final_status = "SECTIONAL_UI_FEED_BUILT"

    audit = [
        {
            "input_rows_loaded": len(input_rows),
            "output_rows": len(output_rows),
            "profile_found_rows": profile_found_rows,
            "no_profile_rows": counts.get("NO_PROFILE", 0),
            "sample_too_small_rows": counts.get("SAMPLE_TOO_SMALL", 0),
            "early_profile_rows": counts.get("EARLY_PROFILE", 0),
            "strong_early_profile_rows": counts.get("STRONG_EARLY_PROFILE", 0),
            "dna_ready_rows": counts.get("DNA_READY", 0),
            "final_status": final_status,
        }
    ]

    write_csv(OUT, output_rows, OUTPUT_COLUMNS)
    write_csv(AUDIT_OUT, audit, AUDIT_COLUMNS)

    print("EDGEiQ sectional intelligence UI feed V1")
    print(f"input_rows_loaded={len(input_rows)}")
    print(f"output_rows={len(output_rows)}")
    print(f"profile_found_rows={profile_found_rows}")
    print(f"no_profile_rows={counts.get('NO_PROFILE', 0)}")
    print(f"sample_too_small_rows={counts.get('SAMPLE_TOO_SMALL', 0)}")
    print(f"early_profile_rows={counts.get('EARLY_PROFILE', 0)}")
    print(f"strong_early_profile_rows={counts.get('STRONG_EARLY_PROFILE', 0)}")
    print(f"dna_ready_rows={counts.get('DNA_READY', 0)}")
    print(f"final_status={final_status}")


if __name__ == "__main__":
    main()
