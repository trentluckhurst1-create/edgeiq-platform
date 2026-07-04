from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT_PRIMARY = DATA / "edgeiq_environment_score_v1.csv"
INPUT_FALLBACK = DATA / "edgeiq_trust_profile_live_audit_v1.csv"

OUTPUT_MAIN = DATA / "edgeiq_environment_v2_trust_field_core.csv"
OUTPUT_SUMMARY = DATA / "edgeiq_environment_v2_trust_field_core_summary.csv"

TRUST_POINTS = {
    "ELITE": 30,
    "STRONG": 20,
    "STANDARD": 5,
    "CHAOTIC": -10,
    "UNKNOWN": 0,
}

FIELD_POINTS = {
    "FIELD_LE_7": 25,
    "FIELD_8_10": 10,
    "FIELD_11_13": -5,
    "FIELD_14_PLUS": -15,
    "UNKNOWN": 0,
}

BAND_ORDER = ["POOR", "NEGATIVE", "NEUTRAL", "POSITIVE", "ELITE"]
BAND_RANK = {band: index for index, band in enumerate(BAND_ORDER)}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def parse_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "").replace("$", "")
    if text.upper() in {"NA", "N/A", "NULL", "NONE", "-", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalise_text(value: object) -> str:
    text = clean_text(value).upper()
    text = re.sub(r"\s+", " ", text)
    return text


def normalise_track(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalise_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        return match.group(1) if match else text


def normalise_race_no(value: object) -> str:
    text = clean_text(value)
    match = re.search(r"(\d+)", text)
    return str(int(match.group(1))) if match else ""


def normalise_horse_key(value: object) -> str:
    text = normalise_text(value)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def normalise_trust_profile(value: object) -> str:
    text = normalise_text(value)
    return text if text in TRUST_POINTS else "UNKNOWN"


def derive_field_bucket(field_size_value: object, existing_bucket: object) -> str:
    existing = normalise_text(existing_bucket)
    if existing in FIELD_POINTS:
        return existing
    number = parse_float(field_size_value)
    if number is None:
        return "UNKNOWN"
    if number <= 7:
        return "FIELD_LE_7"
    if number <= 10:
        return "FIELD_8_10"
    if number <= 13:
        return "FIELD_11_13"
    return "FIELD_14_PLUS"


def derive_band(score: float) -> str:
    if score <= -15:
        return "POOR"
    if score <= 4:
        return "NEGATIVE"
    if score <= 24:
        return "NEUTRAL"
    if score <= 44:
        return "POSITIVE"
    return "ELITE"


def derive_reason(trust_profile: str, field_bucket: str) -> str:
    trust_points = TRUST_POINTS.get(trust_profile, 0)
    field_points = FIELD_POINTS.get(field_bucket, 0)
    return f"TRUST_{trust_profile}:{trust_points:+d}; {field_bucket}:{field_points:+d}"


def pick_source() -> tuple[Path, str]:
    if INPUT_PRIMARY.exists():
        return INPUT_PRIMARY, "ENVIRONMENT_V1_BASE"
    if INPUT_FALLBACK.exists():
        return INPUT_FALLBACK, "TRUST_PROFILE_LIVE_FALLBACK"
    raise FileNotFoundError(
        f"Missing both source files: {INPUT_PRIMARY} and {INPUT_FALLBACK}"
    )


def compare_band(v1_band: object, v2_band: object) -> tuple[str, object]:
    left = normalise_text(v1_band)
    right = normalise_text(v2_band)
    if left not in BAND_RANK or right not in BAND_RANK:
        return "UNKNOWN", ""
    delta = BAND_RANK[right] - BAND_RANK[left]
    if delta > 0:
        return "STRONGER", delta
    if delta < 0:
        return "WEAKER", delta
    return "UNCHANGED", delta


def main() -> None:
    source_path, source_mode = pick_source()
    df = pd.read_csv(source_path, low_memory=False)

    missing = [column for column in ["trust_profile_v1", "field_size"] if column not in df.columns]
    if missing:
        raise SystemExit("Missing required columns: " + ", ".join(missing))

    df["meeting_date"] = df.get("meeting_date", "").map(normalise_date)
    df["track"] = df.get("track", "").map(normalise_track)
    df["race_no"] = df.get("race_no", "").map(normalise_race_no)

    horse_source = None
    for candidate in ["rank1_horse_key", "top_pick_horse", "rank1_horse", "horse", "top_horse_v6"]:
        if candidate in df.columns:
            horse_source = candidate
            break

    if horse_source is not None:
        df["environment_horse_key_v2"] = df[horse_source].map(normalise_horse_key)
    else:
        df["environment_horse_key_v2"] = ""

    df["environment_row_key_v2"] = (
        df["meeting_date"].astype(str)
        + "|"
        + df["track"].astype(str)
        + "|R"
        + df["race_no"].astype(str)
        + "|"
        + df["environment_horse_key_v2"].astype(str)
    )

    df["trust_profile_core_v2"] = df["trust_profile_v1"].map(normalise_trust_profile)
    df["field_size_num_v2"] = df["field_size"].map(parse_float)
    df["field_size_bucket_v2"] = [
        derive_field_bucket(field_size, existing_bucket)
        for field_size, existing_bucket in zip(df["field_size"], df.get("field_size_bucket_v1", ""))
    ]

    df["trust_points_v2"] = df["trust_profile_core_v2"].map(lambda value: TRUST_POINTS.get(value, 0))
    df["field_points_v2"] = df["field_size_bucket_v2"].map(lambda value: FIELD_POINTS.get(value, 0))
    df["environment_score_v2"] = df["trust_points_v2"] + df["field_points_v2"]
    df["environment_band_v2"] = df["environment_score_v2"].map(derive_band)
    df["environment_reason_v2"] = [
        derive_reason(trust_profile, field_bucket)
        for trust_profile, field_bucket in zip(df["trust_profile_core_v2"], df["field_size_bucket_v2"])
    ]
    df["environment_model_v2"] = "TRUST_FIELD_CORE"

    if "environment_score_v1" in df.columns:
        df["environment_score_v1"] = pd.to_numeric(df["environment_score_v1"], errors="coerce")
        df["environment_score_delta_v2_minus_v1"] = df["environment_score_v2"] - df["environment_score_v1"]
    else:
        df["environment_score_delta_v2_minus_v1"] = pd.NA

    comparison = [compare_band(left, right) for left, right in zip(df.get("environment_band_v1", ""), df["environment_band_v2"])]
    df["environment_band_comparison_v2_vs_v1"] = [item[0] for item in comparison]
    df["environment_band_delta_v2_vs_v1"] = [item[1] for item in comparison]
    df["environment_v1_present_v2"] = "YES" if "environment_band_v1" in df.columns else "NO"
    df["environment_source_mode_v2"] = source_mode

    preferred_columns = [
        "environment_source_mode_v2",
        "meeting_date",
        "track",
        "race_no",
        "race_key",
        "environment_row_key_v2",
        "rank1_horse",
        "top_pick_horse",
        "horse",
        "environment_horse_key_v2",
        "trust_profile_v1",
        "trust_profile_core_v2",
        "field_size",
        "field_size_num_v2",
        "field_size_bucket_v1",
        "field_size_bucket_v2",
        "trust_points_v2",
        "field_points_v2",
        "environment_score_v2",
        "environment_band_v2",
        "environment_reason_v2",
        "environment_score_v1",
        "environment_band_v1",
        "environment_reason_v1",
        "environment_score_delta_v2_minus_v1",
        "environment_band_comparison_v2_vs_v1",
        "environment_band_delta_v2_vs_v1",
        "trust_band_v1",
        "trust_index_v1",
    ]
    existing_preferred = [column for column in preferred_columns if column in df.columns]
    remaining_columns = [column for column in df.columns if column not in existing_preferred]
    df[existing_preferred + remaining_columns].to_csv(OUTPUT_MAIN, index=False)

    rows = int(len(df))
    changed_rows = int((df["environment_band_comparison_v2_vs_v1"] != "UNKNOWN").sum()) if "environment_band_v1" in df.columns else 0
    unchanged_rows = int((df["environment_band_comparison_v2_vs_v1"] == "UNCHANGED").sum()) if "environment_band_v1" in df.columns else 0
    stronger_rows = int((df["environment_band_comparison_v2_vs_v1"] == "STRONGER").sum()) if "environment_band_v1" in df.columns else 0
    weaker_rows = int((df["environment_band_comparison_v2_vs_v1"] == "WEAKER").sum()) if "environment_band_v1" in df.columns else 0

    summary_rows: list[dict[str, object]] = [
        {"metric": "source_file", "value": str(source_path)},
        {"metric": "source_mode", "value": source_mode},
        {"metric": "rows", "value": rows},
        {"metric": "v1_comparison_available", "value": "YES" if "environment_band_v1" in df.columns else "NO"},
        {"metric": "unchanged_band_rows", "value": unchanged_rows},
        {"metric": "stronger_band_rows_v2", "value": stronger_rows},
        {"metric": "weaker_band_rows_v2", "value": weaker_rows},
        {"metric": "comparable_band_rows", "value": changed_rows},
        {"metric": "output_main", "value": str(OUTPUT_MAIN)},
    ]

    for band in BAND_ORDER:
        summary_rows.append({
            "metric": f"environment_v2_{band.lower()}_rows",
            "value": int((df["environment_band_v2"] == band).sum()),
        })

    if "environment_band_v1" in df.columns:
        for band in BAND_ORDER:
            summary_rows.append({
                "metric": f"environment_v1_{band.lower()}_rows",
                "value": int((df["environment_band_v1"] == band).sum()),
            })

    pd.DataFrame(summary_rows).to_csv(OUTPUT_SUMMARY, index=False)

    print("[ENVIRONMENT_V2_TRUST_FIELD_CORE] COMPLETE")
    print(f"source_mode={source_mode}")
    print(f"rows={rows}")
    print(f"v1_comparison_available={'YES' if 'environment_band_v1' in df.columns else 'NO'}")
    print(f"unchanged_band_rows={unchanged_rows}")
    print(f"stronger_band_rows_v2={stronger_rows}")
    print(f"weaker_band_rows_v2={weaker_rows}")
    print(f"wrote={OUTPUT_MAIN}")
    print(f"wrote={OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
