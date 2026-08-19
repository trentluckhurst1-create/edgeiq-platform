from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

INPUT = DATA / "edgeiq_class_recovery_engine_v2.csv"
OUTPUT = DATA / "edgeiq_class_recovery_engine_v3.csv"
AUDIT = DATA / "edgeiq_class_recovery_engine_v3_audit.csv"
SUMMARY = DATA / "edgeiq_class_recovery_engine_v3_summary.csv"


NUMBER_WORDS = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
}

RECOVERABLE_ZERO_BANDS = {56, 58, 62, 64}
RECOVERABLE_RTG_PLUS = {66, 72}
HANDICAP_UNRESOLVED = "HANDICAP_UNRESOLVED"


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).upper()
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_cup_name(race_name: str) -> bool:
    return bool(re.search(r"\bCUP\b", race_name))


def class_number_from_token(token: str) -> int | None:
    token = token.strip().upper()
    if token.isdigit():
        value = int(token)
        return value if 1 <= value <= 6 else None
    return NUMBER_WORDS.get(token)


def recover_from_race_name(race_name_raw: object) -> tuple[str | None, str | None]:
    race_name = clean_text(race_name_raw)
    if not race_name:
        return None, None

    zero_band = re.search(r"\b0\s*-\s*(\d{2,3})\b", race_name)
    if zero_band:
        band = int(zero_band.group(1))
        if band >= 110:
            return "JUMPS_RATING_BAND", "race_name_jumps_rating_band_v3"
        if band in RECOVERABLE_ZERO_BANDS:
            return f"BM{band}", "race_name_zero_rating_band_v3"

    rtg_plus = re.search(r"\bRTG\s*(\d{2,3})\s*\+", race_name)
    if rtg_plus:
        band = int(rtg_plus.group(1))
        if band >= 110:
            return "JUMPS_RATING_BAND", "race_name_jumps_rating_band_v3"
        if band in RECOVERABLE_RTG_PLUS:
            return f"BM{band}", "race_name_rtg_plus_v3"

    class_match = re.search(
        r"CLASS\s*(ONE|TWO|THREE|FOUR|FIVE|SIX|[1-6])\b",
        race_name,
    )
    if class_match:
        class_no = class_number_from_token(class_match.group(1))
        if class_no:
            return f"CLASS {class_no}", "race_name_class_token_v3"

    c_hcp_match = re.search(r"\bC\s*([1-6])\s*(?:HCP|HANDICAP)\b", race_name)
    if c_hcp_match:
        return f"CLASS {int(c_hcp_match.group(1))}", "race_name_c_hcp_token_v3"

    cl_match = re.search(r"\bCL\s*([1-6])\b", race_name)
    if cl_match:
        return f"CLASS {int(cl_match.group(1))}", "race_name_cl_token_v3"

    if re.search(r"\bHIGHWAY\b", race_name):
        return "HIGHWAY", "race_name_highway_token_v3"

    if re.search(r"\bWESTSPEED\b", race_name):
        return "WESTSPEED", "race_name_westspeed_token_v3"

    if re.search(r"\bPROVINCIAL\b|\bPROV\b", race_name):
        return "PROVINCIAL", "race_name_provincial_token_v3"

    if re.search(r"\bCOUNTRY\b|\bCTRY\b", race_name):
        return "COUNTRY", "race_name_country_token_v3"

    if re.search(r"\bMIDWAY\b|\bMID\b", race_name):
        return "MIDWAY", "race_name_midway_token_v3"

    return None, None


def append_metric(rows: list[dict[str, object]], metric: str, value: object, section: str = "overall") -> None:
    rows.append(
        {
            "section": section,
            "metric": metric,
            "name": "",
            "count": "",
            "value": value,
            "notes": "",
        }
    )


def append_count_rows(
    rows: list[dict[str, object]],
    section: str,
    metric: str,
    counts: pd.Series,
    limit: int | None = None,
) -> None:
    view = counts.head(limit) if limit else counts
    for name, count in view.items():
        rows.append(
            {
                "section": section,
                "metric": metric,
                "name": name if str(name).strip() else "[blank]",
                "count": int(count),
                "value": "",
                "notes": "",
            }
        )


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CLASS RECOVERY ENGINE V3")
    print("=" * 90)

    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input: {INPUT}")

    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, low_memory=False)

    required = {"race_name", "race_class_recovered", "class_recovery_status", "class_recovery_reason"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required input columns: {missing}")

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    df["race_class_recovered_v2"] = df["race_class_recovered"].astype(str)
    df["class_recovery_status_v2"] = df["class_recovery_status"].astype(str)
    df["class_recovery_reason_v2"] = df["class_recovery_reason"].astype(str)
    df["cup_name_detected_v3"] = df["race_name"].map(lambda value: "TRUE" if has_cup_name(clean_text(value)) else "FALSE")
    df["race_name_recovery_applied_v3"] = "FALSE"
    df["race_name_recovery_reason_v3"] = ""

    previous_handicap_mask = df["race_class_recovered"].eq(HANDICAP_UNRESOLVED)
    previous_handicap_count = int(previous_handicap_mask.sum())

    for idx in df.index[previous_handicap_mask]:
        recovered_class, reason = recover_from_race_name(df.at[idx, "race_name"])
        if not recovered_class:
            continue

        df.at[idx, "race_class_recovered"] = recovered_class
        df.at[idx, "class_recovery_status"] = "RECOVERED"
        df.at[idx, "class_recovery_reason"] = reason
        df.at[idx, "race_name_recovery_applied_v3"] = "TRUE"
        df.at[idx, "race_name_recovery_reason_v3"] = reason

    df["class_recovery_engine_version"] = "V3"
    df["built_at"] = built_at

    new_handicap_count = int(df["race_class_recovered"].eq(HANDICAP_UNRESOLVED).sum())
    newly_recovered_mask = previous_handicap_mask & ~df["race_class_recovered"].eq(HANDICAP_UNRESOLVED)
    newly_recovered_count = int(newly_recovered_mask.sum())

    df.to_csv(OUTPUT, index=False)

    audit_rows: list[dict[str, object]] = []
    append_metric(audit_rows, "rows_loaded", len(df))
    append_metric(audit_rows, "rows_written", len(df))
    append_metric(audit_rows, "previous_HANDICAP_UNRESOLVED_count", previous_handicap_count)
    append_metric(audit_rows, "new_HANDICAP_UNRESOLVED_count", new_handicap_count)
    append_metric(audit_rows, "newly_recovered_from_handicap_count", newly_recovered_count)
    append_metric(audit_rows, "cup_name_detected_count", int(df["cup_name_detected_v3"].eq("TRUE").sum()))

    append_count_rows(
        audit_rows,
        "newly_recovered_from_handicap_by_class",
        "race_class_recovered",
        df.loc[newly_recovered_mask, "race_class_recovered"].value_counts(dropna=False),
    )
    append_count_rows(
        audit_rows,
        "newly_recovered_from_handicap_by_reason",
        "class_recovery_reason",
        df.loc[newly_recovered_mask, "class_recovery_reason"].value_counts(dropna=False),
    )
    append_count_rows(
        audit_rows,
        "remaining_HANDICAP_UNRESOLVED_top_100_race_name",
        "race_name",
        df.loc[df["race_class_recovered"].eq(HANDICAP_UNRESOLVED), "race_name"].value_counts(dropna=False),
        limit=100,
    )

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT, index=False)

    summary = (
        df.groupby(
            [
                "race_class_recovered_v2",
                "race_class_recovered",
                "class_recovery_status",
                "class_recovery_reason",
                "race_name_recovery_applied_v3",
                "cup_name_detected_v3",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(["race_name_recovery_applied_v3", "rows"], ascending=[False, False])
    )
    summary.to_csv(SUMMARY, index=False)

    print(f"rows_loaded: {len(df)}")
    print(f"rows_written: {len(df)}")
    print(f"previous HANDICAP_UNRESOLVED count: {previous_handicap_count}")
    print(f"new HANDICAP_UNRESOLVED count: {new_handicap_count}")
    print(f"newly recovered from handicap count: {newly_recovered_count}")
    print()
    print("Count by recovered class:")
    print(df.loc[newly_recovered_mask, "race_class_recovered"].value_counts().to_string())
    print()
    print("Count by recovery reason:")
    print(df.loc[newly_recovered_mask, "class_recovery_reason"].value_counts().to_string())
    print()
    print("Remaining top 100 HANDICAP_UNRESOLVED race_name:")
    remaining = df.loc[df["race_class_recovered"].eq(HANDICAP_UNRESOLVED), "race_name"].value_counts().head(100)
    print(remaining.to_string())
    print()
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {AUDIT}")
    print(f"wrote: {SUMMARY}")
    print("=" * 90)


if __name__ == "__main__":
    main()
