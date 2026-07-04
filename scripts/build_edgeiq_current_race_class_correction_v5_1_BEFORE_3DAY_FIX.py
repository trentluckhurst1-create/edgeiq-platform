from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
OUT = DATA / "edgeiq_current_race_class_correction_v5_1.csv"
AUDIT = DATA / "edgeiq_current_race_class_correction_v5_1_audit.csv"

def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())

def clean_race_no(value: object) -> str:
    return re.sub(r"\.0$", "", str(value).strip())

def clean_class(value: object) -> str:
    text = norm(value)
    if not text:
        return "UNKNOWN"

    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()

    bm = re.search(r"\bBM\s*(\d{2,3})\b", text)
    if bm:
        return f"BM{bm.group(1)}"

    rating_band = re.search(r"\b0\s*(?:TO|-)\s*(\d{2,3})\b", text)
    if rating_band:
        return f"BM{rating_band.group(1)}"

    if text in {"MDN", "MAIDEN"} or "MAIDEN" in text:
        return "MAIDEN"

    if text in {"2YO MDN", "2YO MAIDEN", "TWO YEAR OLD MAIDEN"}:
        return "MAIDEN"

    if "2YO" in text and ("MDN" in text or "MAIDEN" in text):
        return "MAIDEN"

    class_match = re.search(r"\b(?:CLASS|CL|C)\s*([1-6])\b", text)
    if class_match:
        return f"CLASS {class_match.group(1)}"

    group_match = re.search(r"\bGROUP\s*([123])\b|\bG([123])\b", text)
    if group_match:
        group_no = group_match.group(1) or group_match.group(2)
        return f"GROUP {group_no}"

    if "LISTED" in text:
        return "LISTED"
    if "HANDICAP" in text:
        return "HANDICAP"
    if text == "UNKNOWN":
        return "UNKNOWN"
    return text

def class_family(clean: str) -> str:
    if clean in {"GROUP 1", "GROUP 2", "GROUP 3", "LISTED"}:
        return "BLACKTYPE"
    if clean.startswith("BM"):
        return "JUMPS_OR_HIGHWEIGHT" if clean == "BM120" else "BENCHMARK"
    if clean.startswith("CLASS "):
        return "CLASS"
    if clean == "MAIDEN":
        return "MAIDEN"
    if clean in {"HIGHWAY", "MIDWAY", "COUNTRY", "PROVINCIAL", "WESTSPEED"}:
        return "REGIONAL_RESTRICTED"
    if clean in {"HANDICAP", "UNKNOWN"}:
        return "UNRESOLVED"
    return "OTHER"

def bool_text(value: bool) -> str:
    return "TRUE" if value else "FALSE"

def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT RACE CLASS CORRECTION V5.1 - LIVE FEED REBUILD")
    print("=" * 90)

    if not LIVE_FEED.exists():
        raise FileNotFoundError(f"Missing input: {LIVE_FEED}")

    live = pd.read_csv(LIVE_FEED, dtype=str, keep_default_na=False, low_memory=False)

    if "day_bucket" in live.columns:
        live = live[live["day_bucket"].eq("TODAY")].copy()

    required = {"race_date", "track", "race_no", "horse", "race_class"}
    missing = sorted(required.difference(live.columns))
    if missing:
        raise ValueError(f"Missing live feed columns: {missing}")

    live["race_no"] = live["race_no"].map(clean_race_no)
    live["original_race_class_clean_v5_1"] = live["race_class"].map(clean_class)
    live["corrected_race_class_v5_1"] = live["original_race_class_clean_v5_1"]
    live["corrected_class_family_v5_1"] = live["corrected_race_class_v5_1"].map(class_family)
    live["class_correction_applied_v5_1"] = "FALSE"
    live["class_correction_confidence_v5_1"] = "UNCHANGED"
    live["class_correction_source_v5_1"] = "LIVE_FEED_REBUILD"
    live["class_correction_reason_v5_1"] = "current live feed race_class used directly"
    live["target_status_after_estimate_v5_1"] = live["corrected_race_class_v5_1"].map(
        lambda value: "TARGET_POSSIBLE_AFTER_CLASS_CORRECTION"
        if str(value).strip().upper() not in {"UNKNOWN", "HANDICAP", ""}
        else "NO_TARGET_ESTIMATE"
    )
    live["no_target_before_v5_1"] = live["original_race_class_clean_v5_1"].isin(["UNKNOWN", "HANDICAP"]).map(bool_text)
    live["no_target_after_estimate_v5_1"] = live["corrected_race_class_v5_1"].isin(["UNKNOWN", "HANDICAP"]).map(bool_text)
    live["built_at_class_correction_v5_1"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    keep = [
        "race_date",
        "track",
        "race_no",
        "race_time",
        "distance",
        "horse",
        "race_class",
        "original_race_class_clean_v5_1",
        "corrected_race_class_v5_1",
        "corrected_class_family_v5_1",
        "class_correction_applied_v5_1",
        "class_correction_confidence_v5_1",
        "class_correction_source_v5_1",
        "class_correction_reason_v5_1",
        "target_status_after_estimate_v5_1",
        "no_target_before_v5_1",
        "no_target_after_estimate_v5_1",
        "built_at_class_correction_v5_1",
    ]

    for col in keep:
        if col not in live.columns:
            live[col] = ""

    out = live[keep].copy()
    out.to_csv(OUT, index=False, encoding="utf-8")

    audit_rows = [
        {"section": "overall", "metric": "live_rows_loaded", "value": len(live), "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        {"section": "overall", "metric": "rows_written", "value": len(out), "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        {"section": "overall", "metric": "current_races", "value": out[["race_date", "track", "race_no"]].drop_duplicates().shape[0], "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        {"section": "overall", "metric": "unknown_class_rows", "value": int(out["corrected_race_class_v5_1"].eq("UNKNOWN").sum()), "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ]

    for cls, count in out["corrected_race_class_v5_1"].value_counts().sort_index().items():
        audit_rows.append({"section": "class_counts", "metric": cls, "value": int(count), "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})

    pd.DataFrame(audit_rows).to_csv(AUDIT, index=False, encoding="utf-8")

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print(out[["race_date", "track", "race_no", "horse", "race_class", "corrected_race_class_v5_1"]].head(30).to_string(index=False))
    print("=" * 90)

if __name__ == "__main__":
    main()
