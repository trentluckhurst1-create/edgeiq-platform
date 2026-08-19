from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

LIVE_FEED = DATA / "edgeiq_vic_live_terminal_feed_v1.csv"
HISTORY = DATA / "edgeiq_historical_performance_rating_v5_1.csv"
TARGETS = DATA / "edgeiq_race_rating_targets_v5_1.csv"
CLASS_LADDER = DATA / "edgeiq_class_ladder_v1.csv"
CLASS_PARS = DATA / "edgeiq_class_pars_v5_2.csv"
DISTANCE_PARS = DATA / "edgeiq_distance_pars_v5_1.csv"
CONDITION_PARS = DATA / "edgeiq_condition_pars_v5_1.csv"

OUT = DATA / "edgeiq_current_field_projection_v5_1.csv"
AUDIT = DATA / "edgeiq_current_field_projection_v5_1_audit.csv"

TARGET_FORMULA = "0.70*class_par_rating_v5_2 + 0.15*distance_par_rating_v5_1 + 0.15*condition_par_rating_v5_1"


def norm(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).upper().strip().split())


def horse_key(value: object) -> str:
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return re.sub(r"[^A-Z0-9]", "", text)


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

    if text in {"MAIDEN", "MDN"} or "MAIDEN" in text:
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
    if "SET WEIGHTS" in text and "PENALT" in text:
        return "SET WEIGHTS PENALTIES"
    if "SET WEIGHTS" in text:
        return "SET WEIGHTS"
    if text == "OPEN" or "OPEN" in text:
        return "OPEN"
    if "HIGHWAY" in text:
        return "HIGHWAY"
    if "MIDWAY" in text:
        return "MIDWAY"
    if "COUNTRY" in text:
        return "COUNTRY"
    if "PROVINCIAL" in text:
        return "PROVINCIAL"
    if text == "HANDICAP":
        return "HANDICAP"
    if text == "UNKNOWN":
        return "UNKNOWN"
    return text


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
        norm(row.get(col, ""))
        for col in ["is_scratched", "scratch_status", "runner_status", "ui_status"]
    )
    return "SCRATCH" in blob or blob in {"TRUE", "1", "YES"}


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


def combined_confidence(parts: list[str], no_target: bool, no_history: bool, starts_found: int) -> tuple[str, str]:
    clean = [norm(part) or "MISSING" for part in parts]
    if no_history:
        return "LOW", "no_history"
    if no_target:
        return "LOW", "no_target"
    if starts_found <= 2:
        return "LOW", f"limited_history_starts={starts_found}"
    if any(part in {"MISSING", "NO_TARGET", "VERY_LOW", "LOW", "UNRESOLVED", "EXCLUDED"} for part in clean):
        return "LOW", "weak_confidence_stack: " + "|".join(clean)
    if starts_found <= 4 or any(part == "MEDIUM" for part in clean):
        return "MEDIUM", "medium_confidence_stack: " + "|".join(clean)
    return "HIGH", "history_and_target_confidence_high"


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
        available = [value for value in [last_rating, avg_last_3, avg_last_5, peak_last_6] if pd.notna(value)]
        return float(np.mean(available)), "average available ratings"
    return np.nan, "NO_HISTORY"


def build_race_key(df: pd.DataFrame) -> pd.Series:
    has_race_no = df["race_no"].astype(str).str.strip().ne("").any() if "race_no" in df.columns else False
    if has_race_no:
        return (
            df["race_date"].astype(str)
            + "|"
            + df["track"].astype(str)
            + "|R"
            + df["race_no"].astype(str).str.replace(r"\.0$", "", regex=True)
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
        "starts_found": starts,
        "last_v5_1": float(ratings.iloc[0]) if starts >= 1 else np.nan,
        "avg_last_3_v5_1": float(ratings.head(3).mean()) if starts >= 1 else np.nan,
        "avg_last_5_v5_1": float(ratings.head(5).mean()) if starts >= 1 else np.nan,
        "peak_last_6_v5_1": float(ratings.max()) if starts >= 1 else np.nan,
        "history_last_run_date": last_date,
        "history_last_track": last_track,
        "history_confidence_stack": "|".join(eligible["race_class_confidence_v3_3"].astype(str).head(5)) if len(eligible) else "",
    }


def audit_row(
    section: str,
    metric: str,
    value: object = "",
    race_key: str = "",
    race_date: str = "",
    track: str = "",
    race_no: object = "",
    race_time: str = "",
    horse: str = "",
    projection_band_value: str = "",
    confidence: str = "",
    count: object = "",
    notes: str = "",
) -> dict[str, object]:
    return {
        "section": section,
        "metric": metric,
        "race_key": race_key,
        "race_date": race_date,
        "track": track,
        "race_no": race_no,
        "race_time": race_time,
        "horse": horse,
        "projection_band": projection_band_value,
        "projection_confidence": confidence,
        "value": value,
        "count": count,
        "notes": notes,
    }


def main() -> None:
    print("=" * 90)
    print("EDGEIQ CURRENT FIELD PROJECTION AUDIT V5.1")
    print("=" * 90)

    for path in [LIVE_FEED, HISTORY, TARGETS, CLASS_LADDER, CLASS_PARS, DISTANCE_PARS, CONDITION_PARS]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")

    live = pd.read_csv(LIVE_FEED, dtype=str, keep_default_na=False, low_memory=False)
    history = pd.read_csv(HISTORY, dtype=str, keep_default_na=False, low_memory=False)
    targets = pd.read_csv(TARGETS, dtype=str, keep_default_na=False, low_memory=False)
    class_ladder = pd.read_csv(CLASS_LADDER, dtype=str, keep_default_na=False, low_memory=False)
    class_pars = pd.read_csv(CLASS_PARS, dtype=str, keep_default_na=False, low_memory=False)
    distance_pars = pd.read_csv(DISTANCE_PARS, dtype=str, keep_default_na=False, low_memory=False)
    condition_pars = pd.read_csv(CONDITION_PARS, dtype=str, keep_default_na=False, low_memory=False)

    live_required = {"race_date", "track", "distance", "race_class", "track_condition", "horse", "race_time"}
    history_required = {"horse", "race_date", "track", "performance_rating_v5_1", "race_class_confidence_v3_3"}
    missing_live = sorted(live_required.difference(live.columns))
    missing_history = sorted(history_required.difference(history.columns))
    if missing_live:
        raise ValueError(f"Missing live feed columns: {missing_live}")
    if missing_history:
        raise ValueError(f"Missing history columns: {missing_history}")

    rows_loaded_live = len(live)
    today = live[live["day_bucket"].eq("TODAY")].copy() if "day_bucket" in live.columns else live.copy()
    today["is_scratched_bool_v5_1"] = today.apply(is_scratched, axis=1)
    scratched_rows = int(today["is_scratched_bool_v5_1"].sum())
    current = today[~today["is_scratched_bool_v5_1"]].copy()

    current["distance"] = pd.to_numeric(current["distance"], errors="coerce")
    current["race_no"] = current.get("race_no", "").astype(str)
    current["race_context_key_v5_1"] = build_race_key(current)
    current["current_field_size_v5_1"] = current.groupby("race_context_key_v5_1")["horse"].transform("size")
    current["horse_match_key_v5_1"] = current.apply(
        lambda row: horse_key(row.get("horse_key", "")) or horse_key(row.get("horse", "")),
        axis=1,
    )
    current["race_class_clean_v5_1_current"] = current["race_class"].map(clean_class)
    current["distance_band_v5_1_current"] = current["distance"].apply(distance_band)
    current["condition_group_v5_1_current"] = current["track_condition"].apply(condition_group)
    current["race_date_dt"] = pd.to_datetime(current["race_date"], errors="coerce")

    history["horse_match_key_v5_1"] = history["horse"].map(horse_key)
    history["race_date_dt"] = pd.to_datetime(history["race_date"], errors="coerce")
    history["performance_rating_v5_1"] = pd.to_numeric(history["performance_rating_v5_1"], errors="coerce")
    history = history[
        history["horse_match_key_v5_1"].ne("")
        & history["performance_rating_v5_1"].notna()
        & history["race_date_dt"].notna()
    ].sort_values(["horse_match_key_v5_1", "race_date_dt"], ascending=[True, False])
    history_by_key = {key: group.copy() for key, group in history.groupby("horse_match_key_v5_1", dropna=False)}

    class_keep = class_pars[
        [
            "race_class_clean_v5_2",
            "class_par_rating_v5_2",
            "class_par_confidence_v5_2",
            "class_par_method_v5_2",
            "class_par_hierarchy_adjustment_v5_2",
        ]
    ].copy()
    class_keep["race_class_clean_v5_1_current"] = class_keep["race_class_clean_v5_2"].map(norm)
    class_keep["class_par_rating_v5_2"] = pd.to_numeric(class_keep["class_par_rating_v5_2"], errors="coerce")

    ladder_keep = class_ladder[["race_class", "class_ladder_score_v1", "sample_confidence_v1"]].copy()
    ladder_keep["race_class_clean_v5_1_current"] = ladder_keep["race_class"].map(norm)
    ladder_keep = ladder_keep.drop(columns=["race_class"]).drop_duplicates("race_class_clean_v5_1_current", keep="first")

    distance_keep = distance_pars[
        [
            "distance_band_v5_1",
            "distance_par_rating_v5_1",
            "distance_par_confidence_v5_1",
            "distance_par_method_v5_1",
        ]
    ].copy().rename(columns={"distance_band_v5_1": "distance_band_v5_1_current"})
    distance_keep["distance_par_rating_v5_1"] = pd.to_numeric(distance_keep["distance_par_rating_v5_1"], errors="coerce")

    condition_keep = condition_pars[
        [
            "condition_group_v5_1",
            "condition_par_rating_v5_1",
            "condition_par_confidence_v5_1",
            "condition_par_method_v5_1",
        ]
    ].copy().rename(columns={"condition_group_v5_1": "condition_group_v5_1_current"})
    condition_keep["condition_par_rating_v5_1"] = pd.to_numeric(condition_keep["condition_par_rating_v5_1"], errors="coerce")

    current = current.merge(class_keep, on="race_class_clean_v5_1_current", how="left")
    current = current.merge(ladder_keep, on="race_class_clean_v5_1_current", how="left")
    current = current.merge(distance_keep, on="distance_band_v5_1_current", how="left")
    current = current.merge(condition_keep, on="condition_group_v5_1_current", how="left")

    exact_target_keep = targets.copy()
    exact_target_keep["distance"] = pd.to_numeric(exact_target_keep["distance"], errors="coerce")
    exact_target_keep["real_field_size"] = pd.to_numeric(exact_target_keep["real_field_size"], errors="coerce")
    exact_target_keep["race_target_rating_v5_1"] = pd.to_numeric(exact_target_keep["race_target_rating_v5_1"], errors="coerce")
    exact_target_keep = exact_target_keep[
        [
            "race_date",
            "track",
            "distance",
            "race_class_clean_v5_1",
            "condition_group_v5_1",
            "real_field_size",
            "race_target_rating_v5_1",
            "target_confidence_v5_1",
            "target_status_v5_1",
        ]
    ].rename(
        columns={
            "race_class_clean_v5_1": "race_class_clean_v5_1_current",
            "condition_group_v5_1": "condition_group_v5_1_current",
            "real_field_size": "current_field_size_v5_1",
            "race_target_rating_v5_1": "exact_race_target_rating_v5_1",
            "target_confidence_v5_1": "exact_target_confidence_v5_1",
            "target_status_v5_1": "exact_target_status_v5_1",
        }
    ).drop_duplicates(
        [
            "race_date",
            "track",
            "distance",
            "race_class_clean_v5_1_current",
            "condition_group_v5_1_current",
            "current_field_size_v5_1",
        ],
        keep="first",
    )

    current = current.merge(
        exact_target_keep,
        on=[
            "race_date",
            "track",
            "distance",
            "race_class_clean_v5_1_current",
            "condition_group_v5_1_current",
            "current_field_size_v5_1",
        ],
        how="left",
    )

    projection_rows: list[dict[str, object]] = []
    for _, row in current.iterrows():
        key = row["horse_match_key_v5_1"]
        hist = history_by_key.get(key, history.iloc[0:0])
        metrics = historical_metrics(hist, row["race_date_dt"])
        projected, projection_method = projected_rating(metrics)

        direct_target = np.nan
        if pd.notna(row.get("class_par_rating_v5_2")) and pd.notna(row.get("distance_par_rating_v5_1")) and pd.notna(row.get("condition_par_rating_v5_1")):
            direct_target = (
                0.70 * float(row["class_par_rating_v5_2"])
                + 0.15 * float(row["distance_par_rating_v5_1"])
                + 0.15 * float(row["condition_par_rating_v5_1"])
            )

        if pd.notna(row.get("exact_race_target_rating_v5_1")):
            target_rating = float(row["exact_race_target_rating_v5_1"])
            target_method = "EXACT_HISTORICAL_TARGET"
            target_conf = row.get("exact_target_confidence_v5_1", "")
        elif pd.notna(direct_target):
            target_rating = float(direct_target)
            target_method = "DIRECT_PAR_BLEND"
            target_conf = combined_confidence(
                [
                    row.get("class_par_confidence_v5_2", ""),
                    row.get("distance_par_confidence_v5_1", ""),
                    row.get("condition_par_confidence_v5_1", ""),
                ],
                no_target=False,
                no_history=False,
                starts_found=999,
            )[0]
        else:
            target_rating = np.nan
            target_method = "NO_TARGET"
            target_conf = "NO_TARGET"

        no_history = int(metrics["starts_found"]) == 0
        no_target = pd.isna(target_rating)
        gap = projected - target_rating if pd.notna(projected) and pd.notna(target_rating) else np.nan
        confidence, confidence_reason = combined_confidence(
            [
                row.get("class_par_confidence_v5_2", ""),
                row.get("distance_par_confidence_v5_1", ""),
                row.get("condition_par_confidence_v5_1", ""),
                target_conf,
            ],
            no_target=no_target,
            no_history=no_history,
            starts_found=int(metrics["starts_found"]),
        )

        out_row = row.to_dict()
        out_row.update(metrics)
        out_row.update(
            {
                "projected_rating_v5_1": projected,
                "projection_method_v5_1": projection_method,
                "race_target_rating_v5_1": target_rating,
                "target_method_v5_1": target_method,
                "target_confidence_v5_1": target_conf,
                "target_formula_v5_1": TARGET_FORMULA if pd.notna(target_rating) else "",
                "projection_gap_v5_1": gap,
                "projection_band_v5_1": projection_band(gap),
                "projection_confidence_v5_1": confidence,
                "projection_confidence_reason_v5_1": confidence_reason,
                "history_match_status_v5_1": "MATCHED_HISTORY" if not no_history else "NO_HISTORY",
                "target_status_v5_1": "TARGET_BUILT" if not no_target else "NO_TARGET",
                "built_at_current_projection_v5_1": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
        projection_rows.append(out_row)

    out = pd.DataFrame(projection_rows)

    numeric_cols = [
        "last_v5_1",
        "avg_last_3_v5_1",
        "avg_last_5_v5_1",
        "peak_last_6_v5_1",
        "projected_rating_v5_1",
        "race_target_rating_v5_1",
        "projection_gap_v5_1",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    output_cols = [
        "race_date",
        "day_bucket",
        "track",
        "race_no",
        "race_time",
        "race_context_key_v5_1",
        "current_field_size_v5_1",
        "horse_no",
        "saddlecloth",
        "horse",
        "horse_key",
        "horse_match_key_v5_1",
        "barrier",
        "jockey",
        "trainer",
        "distance",
        "race_class",
        "race_class_clean_v5_1_current",
        "class_ladder_score_v1",
        "sample_confidence_v1",
        "track_condition",
        "condition_group_v5_1_current",
        "distance_band_v5_1_current",
        "starts_found",
        "last_v5_1",
        "avg_last_3_v5_1",
        "avg_last_5_v5_1",
        "peak_last_6_v5_1",
        "history_last_run_date",
        "history_last_track",
        "history_match_status_v5_1",
        "projected_rating_v5_1",
        "projection_method_v5_1",
        "class_par_rating_v5_2",
        "distance_par_rating_v5_1",
        "condition_par_rating_v5_1",
        "race_target_rating_v5_1",
        "target_method_v5_1",
        "target_confidence_v5_1",
        "target_status_v5_1",
        "projection_gap_v5_1",
        "projection_band_v5_1",
        "projection_confidence_v5_1",
        "projection_confidence_reason_v5_1",
        "class_par_confidence_v5_2",
        "distance_par_confidence_v5_1",
        "condition_par_confidence_v5_1",
        "class_par_method_v5_2",
        "distance_par_method_v5_1",
        "condition_par_method_v5_1",
        "target_formula_v5_1",
        "built_at_current_projection_v5_1",
    ]
    output_cols = [col for col in output_cols if col in out.columns]
    out.to_csv(OUT, index=False, columns=output_cols)

    field_counts = out.drop_duplicates("race_context_key_v5_1")["current_field_size_v5_1"].astype(int)
    audit_rows: list[dict[str, object]] = [
        audit_row("overall", "live_rows_loaded", rows_loaded_live),
        audit_row("overall", "today_rows_loaded", len(today)),
        audit_row("overall", "scratched_rows_excluded", scratched_rows),
        audit_row("overall", "races", out["race_context_key_v5_1"].nunique()),
        audit_row("overall", "runners", len(out)),
        audit_row("field_size", "race_count", out["race_context_key_v5_1"].nunique()),
        audit_row("field_size", "runner_count", len(out)),
        audit_row("field_size", "min_runners_per_race", int(field_counts.min()) if len(field_counts) else ""),
        audit_row("field_size", "median_runners_per_race", float(field_counts.median()) if len(field_counts) else ""),
        audit_row("field_size", "max_runners_per_race", int(field_counts.max()) if len(field_counts) else ""),
        audit_row("field_size", "single_runner_current_races", int(field_counts.eq(1).sum()) if len(field_counts) else ""),
        audit_row("coverage", "no_history_runners", int(out["history_match_status_v5_1"].eq("NO_HISTORY").sum())),
        audit_row("coverage", "no_target_runners", int(out["target_status_v5_1"].eq("NO_TARGET").sum())),
        audit_row("coverage", "projected_with_target_runners", int(out["projection_gap_v5_1"].notna().sum())),
    ]

    for band, count in out["projection_band_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_band_counts", band, count=count, projection_band_value=band))

    for confidence, count in out["projection_confidence_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("projection_confidence_counts", confidence, count=count, confidence=confidence))

    for status, count in out["history_match_status_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("history_match_counts", status, count=count))

    for method, count in out["target_method_v5_1"].value_counts().sort_index().items():
        audit_rows.append(audit_row("target_method_counts", method, count=count))

    race_level = (
        out.groupby("race_context_key_v5_1", dropna=False)
        .agg(
            race_date=("race_date", "first"),
            track=("track", "first"),
            race_no=("race_no", "first"),
            race_time=("race_time", "first"),
            runner_count=("horse", "size"),
            no_history=("history_match_status_v5_1", lambda s: int((s == "NO_HISTORY").sum())),
            no_target=("target_status_v5_1", lambda s: int((s == "NO_TARGET").sum())),
            avg_gap=("projection_gap_v5_1", lambda s: pd.to_numeric(s, errors="coerce").mean()),
            max_gap=("projection_gap_v5_1", lambda s: pd.to_numeric(s, errors="coerce").max()),
        )
        .reset_index()
    )
    for _, row in race_level.sort_values(["race_date", "track", "race_no"]).iterrows():
        audit_rows.append(
            audit_row(
                "race_level_runner_counts",
                "race_runner_count",
                race_key=row["race_context_key_v5_1"],
                race_date=row["race_date"],
                track=row["track"],
                race_no=row["race_no"],
                race_time=row["race_time"],
                value=row["runner_count"],
                notes=f"no_history={row['no_history']}; no_target={row['no_target']}; avg_gap={fmt(row['avg_gap'])}; max_gap={fmt(row['max_gap'])}",
            )
        )

    top = out[out["projection_gap_v5_1"].notna()].sort_values("projection_gap_v5_1", ascending=False).head(50)
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        audit_rows.append(
            audit_row(
                "top_50_projected_runners",
                "projection_gap_v5_1",
                value=row["projection_gap_v5_1"],
                race_key=row["race_context_key_v5_1"],
                race_date=row["race_date"],
                track=row["track"],
                race_no=row.get("race_no", ""),
                race_time=row.get("race_time", ""),
                horse=row["horse"],
                projection_band_value=row["projection_band_v5_1"],
                confidence=row["projection_confidence_v5_1"],
                count=rank,
                notes=f"projected={row['projected_rating_v5_1']}; target={row['race_target_rating_v5_1']}; starts={row['starts_found']}",
            )
        )

    audit = pd.DataFrame(audit_rows)
    audit["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    audit.to_csv(AUDIT, index=False)

    print(f"wrote: {OUT}")
    print(f"wrote: {AUDIT}")
    print()
    print(audit[audit["section"].isin(["overall", "field_size", "coverage", "projection_band_counts", "projection_confidence_counts", "target_method_counts"])].to_string(index=False))
    print("=" * 90)


if __name__ == "__main__":
    main()
