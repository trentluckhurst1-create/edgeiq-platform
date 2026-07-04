from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
CLASS_CORRECTION = DATA / "edgeiq_current_race_class_correction_v5_1.csv"
HISTORY = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
CLASS_PARS = DATA / "edgeiq_class_pars_v5_2.csv"
DISTANCE_PARS = DATA / "edgeiq_distance_pars_v5_1.csv"
CONDITION_PARS = DATA / "edgeiq_condition_pars_v5_1.csv"

OUT = DATA / "edgeiq_current_field_projection_v5_2.csv"
AUDIT = DATA / "edgeiq_current_field_projection_v5_2_audit.csv"

TARGET_FORMULA = "0.70*class_par_rating_v5_2 + 0.15*distance_par_rating_v5_1 + 0.15*condition_par_rating_v5_1"


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def horse_key(value: object) -> str:
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


def clean_race_no(value: object) -> str:
    return re.sub(r"\.0$", "", str(value).strip())


def numeric(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.2f}"


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

    if "MAIDEN" in text or text == "MDN":
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


def distance_band(distance: object) -> str:
    value = numeric(distance)
    if pd.isna(value):
        return "UNKNOWN"
    if value < 800:
        return "UNDER_800"
    if value <= 999:
        return "800-999"
    if value <= 1199:
        return "1000-1199"
    if value <= 1399:
        return "1200-1399"
    if value <= 1599:
        return "1400-1599"
    if value <= 1799:
        return "1600-1799"
    if value <= 1999:
        return "1800-1999"
    if value <= 2199:
        return "2000-2199"
    if value <= 2399:
        return "2200-2399"
    if value <= 2799:
        return "2400-2799"
    return "2800+"


def condition_group(value: object) -> str:
    text = norm(value)
    if "FIRM" in text:
        return "FIRM"
    if "GOOD" in text:
        return "GOOD"
    if "SOFT" in text:
        return "SOFT"
    if "HEAVY" in text:
        return "HEAVY"
    if "SYNTH" in text or "POLY" in text:
        return "SYNTHETIC"
    return "UNKNOWN"


def is_scratched(row: pd.Series) -> bool:
    blob = " ".join(
        norm(row.get(column, ""))
        for column in ["is_scratched", "scratch_status", "runner_status", "ui_status"]
    )
    return "SCRATCH" in blob or blob in {"TRUE", "1", "YES"}


def build_race_key(df: pd.DataFrame, version: str) -> pd.Series:
    has_race_no = df["race_no"].astype(str).str.strip().ne("").any() if "race_no" in df.columns else False
    if has_race_no:
        return (
            df["race_date"].astype(str)
            + "|"
            + df["track"].astype(str)
            + "|R"
            + df["race_no"].astype(str).map(clean_race_no)
        )
    return (
        df["race_date"].astype(str)
        + "|"
        + df["track"].astype(str)
        + "|"
        + df["distance"].astype(str)
        + "|"
        + df["race_time"].astype(str)
    )


def projection_band(gap: object) -> str:
    value = numeric(gap)
    if pd.isna(value):
        return "NO_PROJECTION"
    if value >= 8.0:
        return "ELITE"
    if value >= 4.0:
        return "STRONG"
    if value >= 1.0:
        return "POSITIVE"
    if value > -1.0:
        return "NEUTRAL"
    if value > -4.0:
        return "NEGATIVE"
    return "POOR"


def confidence_weight(value: object) -> int:
    clean = norm(value)
    if clean in {"HIGH", "UNCHANGED"}:
        return 3
    if clean == "MEDIUM":
        return 2
    if clean in {"LOW", "VERY_LOW", "NO_TARGET", "MISSING", "UNRESOLVED", "EXCLUDED", ""}:
        return 1
    return 1


def confidence_label(weight: int) -> str:
    if weight >= 3:
        return "HIGH"
    if weight == 2:
        return "MEDIUM"
    return "LOW"


def target_confidence(parts: list[object], no_target: bool) -> tuple[str, str]:
    clean = [norm(part) or "MISSING" for part in parts]
    if no_target:
        return "NO_TARGET", "no_target"
    weights = [confidence_weight(part) for part in clean]
    label = confidence_label(min(weights))
    return label, "target_confidence_stack: " + "|".join(clean)


def projection_confidence(
    target_parts: list[object],
    correction_confidence: object,
    target_status: str,
    starts_found: int,
) -> tuple[str, str]:
    if target_status != "TARGET_BUILT":
        return "LOW", "no_target"
    if starts_found == 0:
        return "LOW", "no_history"
    if starts_found <= 2:
        return "LOW", f"limited_history_starts={starts_found}"

    stack = [norm(part) or "MISSING" for part in [*target_parts, correction_confidence]]
    weights = [confidence_weight(part) for part in stack]
    if starts_found <= 4:
        weights.append(2)
        stack.append(f"STARTS={starts_found}")
    label = confidence_label(min(weights))
    return label, "projection_confidence_stack: " + "|".join(stack)


def projected_rating(metrics: dict[str, object]) -> tuple[float, str]:
    starts = int(metrics["starts_found"])
    last_rating = metrics["last_v5_1"]
    avg_last_3 = metrics["avg_last_3_v5_1"]
    avg_last_5 = metrics["avg_last_5_v5_1"]
    peak_last_6 = metrics["peak_last_6_v5_1"]

    if starts >= 5:
        return (
            (0.35 * last_rating) + (0.35 * avg_last_3) + (0.20 * peak_last_6) + (0.10 * avg_last_5),
            "0.35 last + 0.35 avg3 + 0.20 peak6 + 0.10 avg5",
        )
    if starts >= 3:
        return (
            (0.45 * last_rating) + (0.40 * avg_last_3) + (0.15 * peak_last_6),
            "0.45 last + 0.40 avg3 + 0.15 peak",
        )
    if starts >= 1:
        values = [value for value in [last_rating, avg_last_3, avg_last_5, peak_last_6] if pd.notna(value)]
        return float(np.mean(values)), "average available ratings"
    return np.nan, "NO_HISTORY"


def historical_metrics(history: pd.DataFrame, current_date: pd.Timestamp) -> dict[str, object]:
    if history.empty or pd.isna(current_date):
        eligible = history.iloc[0:0]
    else:
        eligible = history[history["race_date_dt"] < current_date]

    ratings = pd.to_numeric(eligible["performance_rating_v5_1"], errors="coerce").dropna().head(6)
    starts = int(len(ratings))
    last_date = eligible["race_date"].iloc[0] if len(eligible) else ""
    last_track = eligible["track"].iloc[0] if len(eligible) else ""

    return {
        "starts_found_v5_2": starts,
        "last_v5_1": float(ratings.iloc[0]) if starts >= 1 else np.nan,
        "avg_last_3_v5_1": float(ratings.head(3).mean()) if starts >= 1 else np.nan,
        "avg_last_5_v5_1": float(ratings.head(5).mean()) if starts >= 1 else np.nan,
        "peak_last_6_v5_1": float(ratings.max()) if starts >= 1 else np.nan,
        "history_last_run_date_v5_2": last_date,
        "history_last_track_v5_2": last_track,
    }


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    count: object = "",
    race_key: str = "",
    race_date: str = "",
    track: str = "",
    race_no: object = "",
    race_time: str = "",
    distance: object = "",
    horse: str = "",
    corrected_class: str = "",
    projection_band_value: str = "",
    confidence: str = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "value": value,
        "count": count,
        "race_key": race_key,
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_time": race_time,
        "distance": distance,
        "horse": horse,
        "corrected_race_class_v5_1": corrected_class,
        "projection_band": projection_band_value,
        "projection_confidence": confidence,
        "notes": notes,
    }


def race_sort_key(value: object) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 999
    return int(parsed)


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT FIELD PROJECTION V5.2")
    print("=" * 90)

    for path in [LIVE_FEED, CLASS_CORRECTION, HISTORY, CLASS_PARS, DISTANCE_PARS, CONDITION_PARS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    live = pd.read_csv(LIVE_FEED, dtype=str, keep_default_na=False, low_memory=False)
    correction = pd.read_csv(CLASS_CORRECTION, dtype=str, keep_default_na=False, low_memory=False)
    history = pd.read_csv(HISTORY, dtype=str, keep_default_na=False, low_memory=False)
    class_pars = pd.read_csv(CLASS_PARS, dtype=str, keep_default_na=False, low_memory=False)
    distance_pars = pd.read_csv(DISTANCE_PARS, dtype=str, keep_default_na=False, low_memory=False)
    condition_pars = pd.read_csv(CONDITION_PARS, dtype=str, keep_default_na=False, low_memory=False)

    live_required = {
        "race_date",
        "track",
        "race_no",
        "race_time",
        "distance",
        "race_class",
        "track_condition",
        "horse",
    }
    correction_required = {
        "race_date",
        "track",
        "race_no",
        "horse",
        "corrected_race_class_v5_1",
        "corrected_class_family_v5_1",
        "class_correction_applied_v5_1",
        "class_correction_confidence_v5_1",
        "class_correction_reason_v5_1",
    }
    history_required = {"horse", "race_date", "track", "performance_rating_v5_1"}
    class_required = {
        "race_class_clean_v5_2",
        "class_par_rating_v5_2",
        "class_par_confidence_v5_2",
        "class_par_method_v5_2",
    }
    distance_required = {
        "distance_band_v5_1",
        "distance_par_rating_v5_1",
        "distance_par_confidence_v5_1",
        "distance_par_method_v5_1",
    }
    condition_required = {
        "condition_group_v5_1",
        "condition_par_rating_v5_1",
        "condition_par_confidence_v5_1",
        "condition_par_method_v5_1",
    }

    missing = {
        "live_feed": sorted(live_required.difference(live.columns)),
        "class_correction": sorted(correction_required.difference(correction.columns)),
        "history": sorted(history_required.difference(history.columns)),
        "class_pars": sorted(class_required.difference(class_pars.columns)),
        "distance_pars": sorted(distance_required.difference(distance_pars.columns)),
        "condition_pars": sorted(condition_required.difference(condition_pars.columns)),
    }
    missing = {name: columns for name, columns in missing.items() if columns}
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    live_rows_loaded = len(live)
    current = live[live["day_bucket"].eq("TODAY")].copy() if "day_bucket" in live.columns else live.copy()
    current["is_scratched_bool_v5_2"] = current.apply(is_scratched, axis=1)
    scratched_rows = int(current["is_scratched_bool_v5_2"].sum())
    current = current[~current["is_scratched_bool_v5_2"]].copy()

    current["race_no"] = current["race_no"].map(clean_race_no)
    current["distance"] = pd.to_numeric(current["distance"], errors="coerce")
    current["race_context_key_v5_2"] = build_race_key(current, "v5_2")
    current["current_field_size_v5_2"] = current.groupby("race_context_key_v5_2")["horse"].transform("size")
    current["horse_match_key_v5_2"] = current.apply(
        lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        axis=1,
    )
    current["race_class_raw_current_v5_2"] = current["race_class"]
    current["race_class_clean_raw_current_v5_2"] = current["race_class"].map(clean_class)
    current["distance_band_v5_2"] = current["distance"].apply(distance_band)
    current["condition_group_v5_2"] = current["track_condition"].apply(condition_group)
    current["race_date_dt"] = pd.to_datetime(current["race_date"], errors="coerce")

    correction["race_no"] = correction["race_no"].map(clean_race_no)
    correction["horse_match_key_v5_2"] = correction.apply(
        lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        axis=1,
    )
    correction_keep = correction[
        [
            "race_date",
            "track",
            "race_no",
            "horse_match_key_v5_2",
            "original_race_class_clean_v5_1",
            "corrected_race_class_v5_1",
            "corrected_class_family_v5_1",
            "class_correction_applied_v5_1",
            "class_correction_confidence_v5_1",
            "class_correction_source_v5_1",
            "class_correction_reason_v5_1",
        ]
    ].drop_duplicates(["race_date", "track", "race_no", "horse_match_key_v5_2"], keep="first")

    current = current.merge(
        correction_keep,
        on=["race_date", "track", "race_no", "horse_match_key_v5_2"],
        how="left",
    )
    current["class_correction_match_status_v5_2"] = np.where(
        current["corrected_race_class_v5_1"].astype(str).str.strip().ne(""),
        "MATCHED_CLASS_CORRECTION",
        "MISSING_CLASS_CORRECTION_USED_RAW_CLASS",
    )
    current["corrected_race_class_v5_1"] = current["corrected_race_class_v5_1"].where(
        current["corrected_race_class_v5_1"].astype(str).str.strip().ne(""),
        current["race_class_clean_raw_current_v5_2"],
    )
    current["corrected_race_class_v5_1"] = current["corrected_race_class_v5_1"].map(clean_class)
    current["corrected_class_family_v5_1"] = current["corrected_class_family_v5_1"].where(
        current["corrected_class_family_v5_1"].astype(str).str.strip().ne(""),
        current["corrected_race_class_v5_1"].map(class_family),
    )
    current["class_correction_confidence_v5_1"] = current["class_correction_confidence_v5_1"].where(
        current["class_correction_confidence_v5_1"].astype(str).str.strip().ne(""),
        "MISSING",
    )

    history["horse_match_key_v5_2"] = history["horse"].map(horse_key)
    history["race_date_dt"] = pd.to_datetime(history["race_date"], errors="coerce")
    history["performance_rating_v5_1"] = pd.to_numeric(history["performance_rating_v5_1"], errors="coerce")
    history = history[
        history["horse_match_key_v5_2"].ne("")
        & history["performance_rating_v5_1"].notna()
        & history["race_date_dt"].notna()
    ].sort_values(["horse_match_key_v5_2", "race_date_dt"], ascending=[True, False])
    history_by_key = {key: group.copy() for key, group in history.groupby("horse_match_key_v5_2", dropna=False)}

    class_keep = class_pars[
        [
            "race_class_clean_v5_2",
            "class_par_rating_v5_2",
            "class_par_confidence_v5_2",
            "class_par_method_v5_2",
        ]
    ].copy()
    class_keep["corrected_race_class_v5_1"] = class_keep["race_class_clean_v5_2"].map(clean_class)
    class_keep["class_par_rating_v5_2"] = pd.to_numeric(class_keep["class_par_rating_v5_2"], errors="coerce")
    class_keep = class_keep.drop(columns=["race_class_clean_v5_2"]).drop_duplicates("corrected_race_class_v5_1", keep="first")

    distance_keep = distance_pars[
        [
            "distance_band_v5_1",
            "distance_par_rating_v5_1",
            "distance_par_confidence_v5_1",
            "distance_par_method_v5_1",
        ]
    ].copy().rename(columns={"distance_band_v5_1": "distance_band_v5_2"})
    distance_keep["distance_par_rating_v5_1"] = pd.to_numeric(distance_keep["distance_par_rating_v5_1"], errors="coerce")

    condition_keep = condition_pars[
        [
            "condition_group_v5_1",
            "condition_par_rating_v5_1",
            "condition_par_confidence_v5_1",
            "condition_par_method_v5_1",
        ]
    ].copy().rename(columns={"condition_group_v5_1": "condition_group_v5_2"})
    condition_keep["condition_par_rating_v5_1"] = pd.to_numeric(condition_keep["condition_par_rating_v5_1"], errors="coerce")

    current = current.merge(class_keep, on="corrected_race_class_v5_1", how="left")
    current = current.merge(distance_keep, on="distance_band_v5_2", how="left")
    current = current.merge(condition_keep, on="condition_group_v5_2", how="left")

    rows: list[dict[str, object]] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, row in current.iterrows():
        hist = history_by_key.get(row["horse_match_key_v5_2"], history.iloc[0:0])
        metrics = historical_metrics(hist, row["race_date_dt"])
        projected, method = projected_rating(
            {
                "starts_found": metrics["starts_found_v5_2"],
                "last_v5_1": metrics["last_v5_1"],
                "avg_last_3_v5_1": metrics["avg_last_3_v5_1"],
                "avg_last_5_v5_1": metrics["avg_last_5_v5_1"],
                "peak_last_6_v5_1": metrics["peak_last_6_v5_1"],
            }
        )

        class_par = row.get("class_par_rating_v5_2")
        distance_par = row.get("distance_par_rating_v5_1")
        condition_par = row.get("condition_par_rating_v5_1")
        target_missing_parts = [
            name
            for name, value in [
                ("class_par", class_par),
                ("distance_par", distance_par),
                ("condition_par", condition_par),
            ]
            if pd.isna(value)
        ]

        if target_missing_parts:
            target = np.nan
            target_status = "NO_TARGET"
            target_method = "NO_TARGET"
            target_conf, target_reason = target_confidence([], no_target=True)
            target_notes = "missing " + ",".join(target_missing_parts)
        else:
            target = (0.70 * float(class_par)) + (0.15 * float(distance_par)) + (0.15 * float(condition_par))
            target_status = "TARGET_BUILT"
            target_method = "DIRECT_CORRECTED_CLASS_PAR_BLEND"
            target_conf, target_reason = target_confidence(
                [
                    row.get("class_par_confidence_v5_2", ""),
                    row.get("distance_par_confidence_v5_1", ""),
                    row.get("condition_par_confidence_v5_1", ""),
                ],
                no_target=False,
            )
            target_notes = target_reason

        gap = projected - target if pd.notna(projected) and pd.notna(target) else np.nan
        proj_conf, proj_reason = projection_confidence(
            [
                row.get("class_par_confidence_v5_2", ""),
                row.get("distance_par_confidence_v5_1", ""),
                row.get("condition_par_confidence_v5_1", ""),
                target_conf,
            ],
            row.get("class_correction_confidence_v5_1", ""),
            target_status,
            int(metrics["starts_found_v5_2"]),
        )

        out_row = row.to_dict()
        out_row.update(metrics)
        out_row.update(
            {
                "projected_rating_v5_2": projected,
                "projection_method_v5_2": method,
                "race_target_rating_v5_2": target,
                "target_method_v5_2": target_method,
                "target_status_v5_2": target_status,
                "target_confidence_v5_2": target_conf,
                "target_notes_v5_2": target_notes,
                "target_formula_v5_2": TARGET_FORMULA if target_status == "TARGET_BUILT" else "",
                "projection_gap_v5_2": gap,
                "projection_band_v5_2": projection_band(gap),
                "projection_confidence_v5_2": proj_conf,
                "projection_confidence_reason_v5_2": proj_reason,
                "history_match_status_v5_2": "MATCHED_HISTORY" if int(metrics["starts_found_v5_2"]) > 0 else "NO_HISTORY",
                "built_at_current_projection_v5_2": built_at,
            }
        )
        rows.append(out_row)

    out = pd.DataFrame(rows)

    numeric_cols = [
        "last_v5_1",
        "avg_last_3_v5_1",
        "avg_last_5_v5_1",
        "peak_last_6_v5_1",
        "projected_rating_v5_2",
        "class_par_rating_v5_2",
        "distance_par_rating_v5_1",
        "condition_par_rating_v5_1",
        "race_target_rating_v5_2",
        "projection_gap_v5_2",
    ]
    for column in numeric_cols:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").round(2)

    output_cols = [
        "race_date",
        "day_bucket",
        "track",
        "race_no",
        "race_time",
        "race_context_key_v5_2",
        "current_field_size_v5_2",
        "horse_no",
        "saddlecloth",
        "horse",
        "horse_key",
        "horse_match_key_v5_2",
        "barrier",
        "jockey",
        "trainer",
        "distance",
        "race_class_raw_current_v5_2",
        "race_class_clean_raw_current_v5_2",
        "original_race_class_clean_v5_1",
        "corrected_race_class_v5_1",
        "corrected_class_family_v5_1",
        "class_correction_applied_v5_1",
        "class_correction_confidence_v5_1",
        "class_correction_reason_v5_1",
        "class_correction_match_status_v5_2",
        "track_condition",
        "condition_group_v5_2",
        "distance_band_v5_2",
        "starts_found_v5_2",
        "last_v5_1",
        "avg_last_3_v5_1",
        "avg_last_5_v5_1",
        "peak_last_6_v5_1",
        "history_last_run_date_v5_2",
        "history_last_track_v5_2",
        "history_match_status_v5_2",
        "projected_rating_v5_2",
        "projection_method_v5_2",
        "class_par_rating_v5_2",
        "distance_par_rating_v5_1",
        "condition_par_rating_v5_1",
        "race_target_rating_v5_2",
        "target_method_v5_2",
        "target_confidence_v5_2",
        "target_status_v5_2",
        "target_notes_v5_2",
        "target_formula_v5_2",
        "projection_gap_v5_2",
        "projection_band_v5_2",
        "projection_confidence_v5_2",
        "projection_confidence_reason_v5_2",
        "class_par_confidence_v5_2",
        "distance_par_confidence_v5_1",
        "condition_par_confidence_v5_1",
        "class_par_method_v5_2",
        "distance_par_method_v5_1",
        "condition_par_method_v5_1",
        "built_at_current_projection_v5_2",
    ]
    output_cols = [column for column in output_cols if column in out.columns]
    out.to_csv(OUT, index=False, columns=output_cols)

    field_counts = out.drop_duplicates("race_context_key_v5_2")["current_field_size_v5_2"].astype(int)
    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "live_rows_loaded", live_rows_loaded),
        audit_row("overall", "today_rows_used", len(current)),
        audit_row("overall", "scratched_rows_excluded", scratched_rows),
        audit_row("overall", "class_correction_rows_loaded", len(correction)),
        audit_row("overall", "class_correction_matched_runners", int(out["class_correction_match_status_v5_2"].eq("MATCHED_CLASS_CORRECTION").sum())),
        audit_row("overall", "class_correction_unmatched_runners", int(out["class_correction_match_status_v5_2"].ne("MATCHED_CLASS_CORRECTION").sum())),
        audit_row("overall", "races", out["race_context_key_v5_2"].nunique()),
        audit_row("overall", "runners", len(out)),
        audit_row("overall", "target_built_runners", int(out["target_status_v5_2"].eq("TARGET_BUILT").sum())),
        audit_row("overall", "no_target_runners", int(out["target_status_v5_2"].eq("NO_TARGET").sum())),
        audit_row("overall", "no_history_runners", int(out["history_match_status_v5_2"].eq("NO_HISTORY").sum())),
        audit_row("overall", "projected_with_target_runners", int(out["projection_gap_v5_2"].notna().sum())),
        audit_row("field_size", "race_count", out["race_context_key_v5_2"].nunique()),
        audit_row("field_size", "runner_count", len(out)),
        audit_row("field_size", "min_runners_per_race", int(field_counts.min()) if len(field_counts) else ""),
        audit_row("field_size", "median_runners_per_race", float(field_counts.median()) if len(field_counts) else ""),
        audit_row("field_size", "max_runners_per_race", int(field_counts.max()) if len(field_counts) else ""),
        audit_row("field_size", "single_runner_current_races", int(field_counts.eq(1).sum()) if len(field_counts) else ""),
    ]

    for status, count in out["target_status_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("target_status_counts", status, count=count))

    for method, count in out["target_method_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("target_method_counts", method, count=count))

    for band, count in out["projection_band_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_band_counts", band, count=count, projection_band_value=band))

    for confidence, count in out["projection_confidence_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_confidence_counts", confidence, count=count, confidence=confidence))

    for status, count in out["history_match_status_v5_2"].value_counts().sort_index().items():
        audit_rows.append(audit_row("history_match_counts", status, count=count))

    race_table = (
        out.groupby("race_context_key_v5_2", dropna=False)
        .agg(
            race_date=("race_date", "first"),
            track=("track", "first"),
            race_no=("race_no", "first"),
            race_time=("race_time", "first"),
            distance=("distance", "first"),
            corrected_class=("corrected_race_class_v5_1", "first"),
            runners=("horse", "size"),
            target=("race_target_rating_v5_2", "first"),
            target_status=("target_status_v5_2", "first"),
            target_confidence=("target_confidence_v5_2", "first"),
            class_par=("class_par_rating_v5_2", "first"),
            distance_par=("distance_par_rating_v5_1", "first"),
            condition_par=("condition_par_rating_v5_1", "first"),
            avg_gap=("projection_gap_v5_2", lambda values: pd.to_numeric(values, errors="coerce").mean()),
            max_gap=("projection_gap_v5_2", lambda values: pd.to_numeric(values, errors="coerce").max()),
        )
        .reset_index()
    )
    race_table["race_sort"] = race_table["race_no"].map(race_sort_key)
    for _, row in race_table.sort_values(["race_date", "track", "race_sort"]).iterrows():
        audit_rows.append(
            audit_row(
                "race_target_table",
                "race_target_v5_2",
                value=fmt(row["target"]),
                count=row["runners"],
                race_key=row["race_context_key_v5_2"],
                race_date=row["race_date"],
                track=row["track"],
                race_no=row["race_no"],
                race_time=row["race_time"],
                distance=row["distance"],
                corrected_class=row["corrected_class"],
                confidence=row["target_confidence"],
                notes=(
                    f"target_status={row['target_status']}; class_par={fmt(row['class_par'])}; "
                    f"distance_par={fmt(row['distance_par'])}; condition_par={fmt(row['condition_par'])}; "
                    f"avg_gap={fmt(row['avg_gap'])}; max_gap={fmt(row['max_gap'])}"
                ),
            )
        )

    top = out[out["projection_gap_v5_2"].notna()].sort_values("projection_gap_v5_2", ascending=False).head(50)
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        audit_rows.append(
            audit_row(
                "top_positive_gaps",
                "projection_gap_v5_2",
                value=row["projection_gap_v5_2"],
                count=rank,
                race_key=row["race_context_key_v5_2"],
                race_date=row["race_date"],
                track=row["track"],
                race_no=row["race_no"],
                race_time=row["race_time"],
                distance=row["distance"],
                horse=row["horse"],
                corrected_class=row["corrected_race_class_v5_1"],
                projection_band_value=row["projection_band_v5_2"],
                confidence=row["projection_confidence_v5_2"],
                notes=f"projected={row['projected_rating_v5_2']}; target={row['race_target_rating_v5_2']}; starts={row['starts_found_v5_2']}",
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit["built_at"] = built_at
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "field_size", "target_status_counts", "projection_band_counts", "projection_confidence_counts"])].to_string(index=False))
    print()
    print(audit[audit["section"].eq("race_target_table")].to_string(index=False))
    print()
    print(audit[audit["section"].eq("top_positive_gaps")].head(20).to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
