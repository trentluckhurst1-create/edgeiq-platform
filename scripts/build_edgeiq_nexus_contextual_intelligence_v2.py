from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

HISTORICAL_RESULTS = DATA / "edgeiq_historical_results_warehouse_v2_graphql.csv"
CONTEXT_WAREHOUSE = DATA / "edgeiq_context_warehouse_v2_graphql.csv"
LIVE_NEXUS_V1 = DATA / "edgeiq_live_nexus_feature_feed_v1.csv"
TRAINER_RECENT_V1 = DATA / "edgeiq_trainer_recent_form_engine_v1.csv"
JOCKEY_RECENT_V1 = DATA / "edgeiq_jockey_recent_form_engine_v1.csv"
JOCKEY_STYLE_V1 = DATA / "edgeiq_jockey_run_style_engine_v1.csv"
TRAINER_STYLE_V1 = DATA / "edgeiq_trainer_run_style_engine_v1.csv"
PARTNERSHIP_V1 = DATA / "edgeiq_trainer_jockey_partnership_engine_v1.csv"
RACE_SHAPE_STORY = DATA / "edgeiq_race_shape_story_v1.csv"
LIVE_BOARD = DATA / "edgeiq_live_runner_board_v1.csv"
COMMAND_ENRICHMENT = DATA / "edgeiq_command_enrichment_feed_v3.csv"
RUNNERS_ENRICHMENT = DATA / "edgeiq_runners_enrichment_feed_v1_1.csv"

TRAINER_CONTEXT_OUT = DATA / "edgeiq_nexus_trainer_context_v2.csv"
JOCKEY_CONTEXT_OUT = DATA / "edgeiq_nexus_jockey_context_v2.csv"
PARTNERSHIP_CONTEXT_OUT = DATA / "edgeiq_nexus_partnership_context_v2.csv"
STYLE_ALIGNMENT_OUT = DATA / "edgeiq_nexus_style_alignment_v2.csv"
CONTEXTUAL_SCORE_OUT = DATA / "edgeiq_nexus_contextual_score_v2.csv"
LIVE_CONTEXTUAL_FEED_OUT = DATA / "edgeiq_live_nexus_contextual_feed_v2.csv"
SUMMARY_OUT = DATA / "edgeiq_nexus_contextual_intelligence_v2_summary.csv"

RUN_STYLE_ORDER = ["LEADER", "ON_PACE", "MIDFIELD", "OFF_PACE", "REAR", "UNKNOWN"]
STYLE_CONFLICTS = {
    ("LEADER", "REAR"),
    ("LEADER", "OFF_PACE"),
    ("ON_PACE", "REAR"),
    ("REAR", "LEADER"),
    ("OFF_PACE", "LEADER"),
    ("REAR", "ON_PACE"),
}


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def canon(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text(value).upper())


def to_float(value: Any) -> float | None:
    raw = text(value).replace("$", "").replace(",", "")
    if not raw:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    try:
        value_float = float(match.group(0))
    except ValueError:
        return None
    return value_float if math.isfinite(value_float) else None


def read_csv(path: Path, dtype: str = "string") -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=dtype, keep_default_na=False, encoding="utf-8-sig", low_memory=False)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sample_band(starts: int) -> str:
    if starts >= 200:
        return "ELITE_SAMPLE"
    if starts >= 100:
        return "STRONG_SAMPLE"
    if starts >= 50:
        return "MODERATE_SAMPLE"
    if starts >= 20:
        return "LIGHT_SAMPLE"
    return "LOW_SAMPLE"


def score_band(score: float) -> str:
    if score >= 90:
        return "ELITE"
    if score >= 80:
        return "STRONG"
    if score >= 70:
        return "POSITIVE"
    if score >= 55:
        return "NEUTRAL"
    if score >= 40:
        return "NEGATIVE"
    return "POOR"


def context_band(starts: int, win_pct: float, roi: float | None, ae: float | None) -> str:
    roi_value = roi if roi is not None else 0.0
    ae_value = ae if ae is not None else 1.0
    if starts >= 50 and ae_value >= 1.25 and roi_value >= 0.15 and win_pct >= 15:
        return "ELITE"
    if starts >= 30 and ae_value >= 1.12 and roi_value >= 0:
        return "STRONG"
    if starts >= 20 and (ae_value >= 1.0 or roi_value >= 0.05):
        return "POSITIVE"
    if starts >= 20 and ae_value <= 0.75 and roi_value <= -0.25:
        return "POOR"
    if starts >= 20 and (ae_value <= 0.9 or roi_value <= -0.1):
        return "NEGATIVE"
    if starts < 20 and ae_value >= 1.3 and roi_value > 0:
        return "POSITIVE"
    return "NEUTRAL"


def band_points(band: str) -> float:
    return {
        "ELITE": 94.0,
        "STRONG": 84.0,
        "POSITIVE": 73.0,
        "NEUTRAL": 58.0,
        "NEGATIVE": 44.0,
        "POOR": 30.0,
    }.get(text(band).upper(), 55.0)


def metric_score(row: dict[str, Any]) -> float:
    return band_points(row.get("context_band") or row.get("partnership_band"))


def metric_rows(df: pd.DataFrame, group_cols: list[str], entity_cols: list[str], label: str, band_col: str) -> list[dict[str, Any]]:
    if df.empty:
        return []
    work = df[df[group_cols].notna().all(axis=1)].copy()
    for col in group_cols:
        work[col] = work[col].astype(str)
    work["_valid_sp"] = work["_sp"].where(work["_sp"].notna() & (work["_sp"] > 0))
    work["_expected_wins"] = (1.0 / work["_valid_sp"]).fillna(0.0)
    work["_profit"] = -1.0
    winner_with_sp = (work["_won"] == 1) & work["_valid_sp"].notna()
    winner_without_sp = (work["_won"] == 1) & work["_valid_sp"].isna()
    work.loc[winner_with_sp, "_profit"] = work.loc[winner_with_sp, "_valid_sp"] - 1.0
    work.loc[winner_without_sp, "_profit"] = 0.0
    agg = (
        work.groupby(group_cols, dropna=False)
        .agg(
            starts=("_won", "size"),
            wins=("_won", "sum"),
            places=("_placed", "sum"),
            profit=("_profit", "sum"),
            expected_wins=("_expected_wins", "sum"),
            avg_sp=("_valid_sp", "mean"),
        )
        .reset_index()
    )
    out: list[dict[str, Any]] = []
    for _, agg_row in agg.iterrows():
        key_values = [text(agg_row[col]) for col in group_cols]
        starts = int(agg_row["starts"])
        wins = int(agg_row["wins"])
        places = int(agg_row["places"])
        expected = float(agg_row["expected_wins"])
        profit = float(agg_row["profit"])
        roi = profit / starts if starts else None
        ae = wins / expected if expected > 0 else None
        avg_sp = None if pd.isna(agg_row["avg_sp"]) else float(agg_row["avg_sp"])
        win_pct = wins / starts * 100.0 if starts else 0.0
        place_pct = places / starts * 100.0 if starts else 0.0
        row = {entity_cols[idx]: key_values[idx] for idx in range(len(entity_cols))}
        row.update(
            {
                "context_type": key_values[len(entity_cols)] if band_col == "context_band" else key_values[len(entity_cols)],
                "context_value": key_values[len(entity_cols) + 1],
                "starts": starts,
                "wins": wins,
                "places": places,
                "win_pct": round(win_pct, 2),
                "place_pct": round(place_pct, 2),
                "roi": round(roi, 4) if roi is not None else "",
                "ae": round(ae, 3) if ae is not None else "",
                "avg_sp": round(avg_sp, 2) if avg_sp is not None else "",
                "sample_band": sample_band(starts),
                band_col: context_band(starts, win_pct, roi, ae),
            }
        )
        out.append(row)
    return out


def distance_band(distance: Any) -> str:
    value = to_float(distance)
    if value is None:
        return "UNKNOWN"
    if 1000 <= value <= 1200:
        return "SPRINT"
    if 1201 <= value <= 1400:
        return "SHORT_MIDDLE"
    if 1401 <= value <= 1700:
        return "MILE"
    if 1701 <= value <= 2200:
        return "MIDDLE"
    if value >= 2201:
        return "EXTENDED"
    return "UNKNOWN"


def condition_band(value: Any) -> str:
    raw = text(value).upper()
    if "GOOD" in raw or raw in {"G", "3", "4"}:
        return "GOOD"
    if "SOFT" in raw or raw in {"S", "5", "6", "7"}:
        return "SOFT"
    if "HEAVY" in raw or raw in {"H", "8", "9", "10"}:
        return "HEAVY"
    if "SYNTH" in raw or "POLY" in raw or "TAPETA" in raw:
        return "SYNTHETIC"
    return "UNKNOWN"


def field_size_band(size: Any) -> str:
    value = to_float(size)
    if value is None:
        return "UNKNOWN"
    if value <= 7:
        return "SMALL"
    if value <= 11:
        return "MEDIUM"
    if value <= 15:
        return "LARGE"
    return "BIG"


def class_band(value: Any) -> str:
    raw = text(value).upper()
    if not raw:
        return "UNKNOWN"
    if "MAIDEN" in raw or re.search(r"\bMDN\b", raw):
        return "MAIDEN"
    if any(token in raw for token in ("GROUP", "LISTED", "G1", "G2", "G3", "LR")):
        return "LISTED_GROUP"
    if "OPEN" in raw or "QUALITY" in raw:
        return "OPEN"
    match = re.search(r"BM\s?(\d+)", raw)
    if match:
        rating = int(match.group(1))
        if rating <= 64:
            return "BM_LOW"
        if rating <= 78:
            return "BM_MID"
        return "BM_HIGH"
    if "BENCHMARK" in raw:
        return "BM_MID"
    return "UNKNOWN"


def run_style(value: Any) -> str:
    raw = text(value).upper().replace("-", "_").replace(" ", "_")
    raw = re.sub(r"_+", "_", raw)
    if raw in {"LEADER", "FRONT", "FRONT_RUNNER", "FRONTRUNNER", "LEAD"}:
        return "LEADER"
    if raw in {"ONPACE", "ON_PACE", "PROMINENT", "HANDY", "SPEED"}:
        return "ON_PACE"
    if raw in {"MIDFIELD", "MID_FIELD", "MID"}:
        return "MIDFIELD"
    if raw in {"OFFPACE", "OFF_PACE", "BACKMARKER", "BACK_MARKER", "BACK"}:
        return "OFF_PACE"
    if raw in {"REAR", "DEEP_BACKMARKER", "TAIL", "LAST"}:
        return "REAR"
    return "UNKNOWN"


def pace_scenario(value: Any) -> str:
    raw = text(value).upper()
    if not raw:
        return "UNKNOWN"
    if any(token in raw for token in ("EXTREME", "FEROCIOUS", "VERY HIGH")):
        return "EXTREME"
    if any(token in raw for token in ("HIGH", "PRESSURE", "FAST")):
        return "HIGH_PRESSURE"
    if "TACTICAL" in raw:
        return "TACTICAL"
    if any(token in raw for token in ("LOW", "SLOW", "SOFT")):
        return "LOW_PRESSURE"
    if "MODERATE" in raw or "EVEN" in raw:
        return "MODERATE"
    return "UNKNOWN"


def prep_and_freshness(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["horse_key", "race_date_dt", "race_no_num"]).copy()
    df["_previous_start_date"] = df.groupby("horse_key")["race_date_dt"].shift(1)
    df["_days_since_start"] = (df["race_date_dt"] - df["_previous_start_date"]).dt.days
    spell_break = df["_days_since_start"].isna() | (df["_days_since_start"] >= 60)
    df["_prep_id"] = spell_break.groupby(df["horse_key"]).cumsum()
    df["_start_in_prep"] = df.groupby(["horse_key", "_prep_id"]).cumcount() + 1
    df["_prep_freshness_band"] = df["_start_in_prep"].map(
        lambda n: "FIRST_UP" if n == 1 else "SECOND_UP" if n == 2 else "THIRD_UP" if n == 3 else "DEEP_PREP"
    )
    df["_freshness_band"] = df["_days_since_start"].map(
        lambda d: "FIRST_UP_OR_SPELL" if pd.isna(d) or d >= 60 else "FRESHENED" if d >= 35 else "NORMAL_BACKUP" if d > 10 else "QUICK_BACKUP"
    )
    return df


def prepare_historical() -> pd.DataFrame:
    cols = [
        "race_date",
        "track",
        "race_id",
        "race_no",
        "race_class",
        "distance",
        "track_condition",
        "horse",
        "horse_code",
        "trainer",
        "jockey",
        "scratched",
        "finish",
        "finish_num",
        "won",
        "placed",
        "starting_price_decimal",
    ]
    df = pd.read_csv(HISTORICAL_RESULTS, usecols=lambda c: c in cols, keep_default_na=False, encoding="utf-8-sig", low_memory=False)
    df = df[df["scratched"].astype(str).str.upper().ne("TRUE")].copy()
    df["race_date_dt"] = pd.to_datetime(df["race_date"], errors="coerce")
    df = df[df["race_date_dt"].notna()].copy()
    df["race_no_num"] = pd.to_numeric(df.get("race_no", ""), errors="coerce").fillna(0)
    df["_finish_num"] = pd.to_numeric(df.get("finish_num", ""), errors="coerce")
    if "_finish_num" not in df or df["_finish_num"].isna().all():
        df["_finish_num"] = pd.to_numeric(df.get("finish", ""), errors="coerce")
    df["_won"] = ((pd.to_numeric(df.get("won", ""), errors="coerce").fillna(0) == 1) | (df["_finish_num"] == 1)).astype(int)
    df["_placed"] = ((pd.to_numeric(df.get("placed", ""), errors="coerce").fillna(0) == 1) | (df["_finish_num"] <= 3)).astype(int)
    df["_sp"] = pd.to_numeric(df.get("starting_price_decimal", ""), errors="coerce")
    df.loc[df["_sp"] <= 0, "_sp"] = pd.NA
    df["trainer_key"] = df["trainer"].map(canon)
    df["jockey_key"] = df["jockey"].map(canon)
    horse_source = df["horse_code"].where(df["horse_code"].astype(str).str.strip().ne(""), df["horse"])
    df["horse_key"] = horse_source.map(canon)
    df["_track"] = df["track"].map(lambda v: text(v).upper() or "UNKNOWN")
    df["_distance_band"] = df["distance"].map(distance_band)
    df["_condition_band"] = df["track_condition"].map(condition_band)
    df["_class_band"] = df["race_class"].map(class_band)
    race_key_cols = ["race_date", "track", "race_no"]
    field_sizes = df.groupby(race_key_cols, dropna=False).size().rename("_field_size")
    df = df.join(field_sizes, on=race_key_cols)
    df["_field_size_band"] = df["_field_size"].map(field_size_band)
    df["_pace_scenario"] = "UNKNOWN"
    return prep_and_freshness(df)


def append_style_contexts(rows: list[dict[str, Any]], style_df: pd.DataFrame, entity_key: str, entity_name: str, output_key: str, output_name: str, starts_label: str, band_col: str) -> None:
    if style_df.empty:
        return
    for _, row in style_df.iterrows():
        starts = int(to_float(row.get("starts")) or 0)
        wins = int(to_float(row.get("wins")) or 0)
        places = int(to_float(row.get("places")) or 0)
        win_pct = to_float(row.get("win_pct")) or 0.0
        place_pct = to_float(row.get("place_pct")) or 0.0
        roi_pct = to_float(row.get("roi_pct"))
        roi = roi_pct / 100.0 if roi_pct is not None else None
        ae = to_float(row.get("ae"))
        avg_sp = to_float(row.get("avg_sp"))
        rows.append(
            {
                output_key: text(row.get(entity_name)) or text(row.get(output_name)),
                "context_type": "run_style",
                "context_value": run_style(row.get("run_style_band")),
                starts_label: starts,
                "wins": wins,
                "places": places,
                "win_pct": round(win_pct, 2),
                "place_pct": round(place_pct, 2),
                "roi": round(roi, 4) if roi is not None else "",
                "ae": round(ae, 3) if ae is not None else "",
                "avg_sp": round(avg_sp, 2) if avg_sp is not None else "",
                "sample_band": sample_band(starts),
                band_col: context_band(starts, win_pct, roi, ae),
            }
        )


def build_entity_contexts(historical: pd.DataFrame, trainer_style: pd.DataFrame, jockey_style: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_contexts = [
        ("overall", "ALL"),
        ("track", "_track"),
        ("distance_band", "_distance_band"),
        ("track_condition", "_condition_band"),
        ("class_band", "_class_band"),
        ("prep_freshness", "_prep_freshness_band"),
        ("freshness", "_freshness_band"),
        ("field_size_band", "_field_size_band"),
        ("pace_scenario", "_pace_scenario"),
    ]

    trainer_work = historical[historical["trainer_key"].ne("")].copy()
    jockey_work = historical[historical["jockey_key"].ne("")].copy()
    trainer_work["trainer"] = trainer_work["trainer"].map(text)
    jockey_work["jockey"] = jockey_work["jockey"].map(text)
    for context_type, source_col in base_contexts:
        trainer_work[f"_ctx_{context_type}"] = "ALL" if source_col == "ALL" else trainer_work[source_col]
        jockey_work[f"_ctx_{context_type}"] = "ALL" if source_col == "ALL" else jockey_work[source_col]

    trainer_rows: list[dict[str, Any]] = []
    jockey_rows: list[dict[str, Any]] = []
    for context_type, _ in base_contexts:
        t = trainer_work.copy()
        t["_context_type"] = context_type
        t["_context_value"] = t[f"_ctx_{context_type}"]
        trainer_rows.extend(
            metric_rows(t, ["trainer", "_context_type", "_context_value"], ["trainer"], "trainer", "context_band")
        )

        j = jockey_work.copy()
        j["_context_type"] = context_type
        j["_context_value"] = j[f"_ctx_{context_type}"]
        jockey_metric_rows = metric_rows(j, ["jockey", "_context_type", "_context_value"], ["jockey"], "jockey", "context_band")
        for row in jockey_metric_rows:
            row["rides"] = row.pop("starts")
        jockey_rows.extend(jockey_metric_rows)

    append_style_contexts(trainer_rows, trainer_style, "trainer_canonical", "trainer_name", "trainer", "trainer", "starts", "context_band")
    append_style_contexts(jockey_rows, jockey_style, "jockey_canonical", "jockey_name", "jockey", "jockey", "rides", "context_band")

    trainer_rows.sort(key=lambda r: (text(r.get("trainer")), text(r.get("context_type")), text(r.get("context_value"))))
    jockey_rows.sort(key=lambda r: (text(r.get("jockey")), text(r.get("context_type")), text(r.get("context_value"))))
    return trainer_rows, jockey_rows


def partnership_targets(live: list[dict[str, Any]], partnership_v1: pd.DataFrame) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()
    for row in live:
        trainer_key = canon(row.get("trainer"))
        jockey_key = canon(row.get("jockey"))
        if trainer_key and jockey_key:
            targets.add((trainer_key, jockey_key))
    if not partnership_v1.empty:
        for _, row in partnership_v1.iterrows():
            trainer_key = text(row.get("trainer_canonical")) or canon(row.get("trainer_name"))
            jockey_key = text(row.get("jockey_canonical")) or canon(row.get("jockey_name"))
            if trainer_key and jockey_key:
                targets.add((trainer_key, jockey_key))
    return targets


def build_partnership_contexts(historical: pd.DataFrame, targets: set[tuple[str, str]]) -> list[dict[str, Any]]:
    work = historical[historical["trainer_key"].ne("") & historical["jockey_key"].ne("")].copy()
    if targets:
        target_frame = pd.DataFrame(list(targets), columns=["trainer_key", "jockey_key"])
        work = work.merge(target_frame, on=["trainer_key", "jockey_key"], how="inner")
    work["trainer"] = work["trainer"].map(text)
    work["jockey"] = work["jockey"].map(text)
    contexts = [
        ("overall", "ALL"),
        ("track", "_track"),
        ("distance_band", "_distance_band"),
        ("track_condition", "_condition_band"),
        ("class_band", "_class_band"),
    ]
    out: list[dict[str, Any]] = []
    for context_type, source_col in contexts:
        context_work = work.copy()
        context_work["_context_type"] = context_type
        context_work["_context_value"] = "ALL" if source_col == "ALL" else context_work[source_col]
        rows = metric_rows(
            context_work,
            ["trainer", "jockey", "_context_type", "_context_value"],
            ["trainer", "jockey"],
            "partnership",
            "partnership_band",
        )
        out.extend(rows)
    out.sort(key=lambda r: (text(r.get("trainer")), text(r.get("jockey")), text(r.get("context_type")), text(r.get("context_value"))))
    return out


def partnership_contexts_from_v1(partnership_v1: pd.DataFrame) -> list[dict[str, Any]]:
    if partnership_v1.empty:
        return []
    context_specs = [
        ("overall", "ALL", "lifetime"),
        ("track", "current_track", "track_combo"),
        ("distance_band", "current_distance_bucket", "distance_combo"),
        ("class_band", "current_class_bucket", "class_combo"),
    ]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for _, source in partnership_v1.iterrows():
        trainer = text(source.get("trainer_name"))
        jockey = text(source.get("jockey_name"))
        if not trainer or not jockey:
            continue
        for context_type, value_col, prefix in context_specs:
            context_value = "ALL" if value_col == "ALL" else text(source.get(value_col)).upper()
            if not context_value:
                continue
            key = (canon(trainer), canon(jockey), context_type, context_value)
            if key in seen:
                continue
            seen.add(key)
            starts = int(to_float(source.get(f"{prefix}_starts")) or 0)
            wins = int(to_float(source.get(f"{prefix}_wins")) or 0)
            places = int(to_float(source.get(f"{prefix}_places")) or 0)
            win_pct = to_float(source.get(f"{prefix}_win_pct")) or 0.0
            place_pct = to_float(source.get(f"{prefix}_place_pct")) or 0.0
            roi_pct = to_float(source.get(f"{prefix}_roi_pct"))
            roi = roi_pct / 100.0 if roi_pct is not None else None
            ae = to_float(source.get(f"{prefix}_ae"))
            avg_sp = to_float(source.get(f"{prefix}_avg_sp"))
            rows.append(
                {
                    "trainer": trainer,
                    "jockey": jockey,
                    "context_type": context_type,
                    "context_value": context_value,
                    "starts": starts,
                    "wins": wins,
                    "places": places,
                    "win_pct": round(win_pct, 2),
                    "place_pct": round(place_pct, 2),
                    "roi": round(roi, 4) if roi is not None else "",
                    "ae": round(ae, 3) if ae is not None else "",
                    "avg_sp": round(avg_sp, 2) if avg_sp is not None else "",
                    "sample_band": sample_band(starts),
                    "partnership_band": context_band(starts, win_pct, roi, ae),
                }
            )
    rows.sort(key=lambda r: (text(r.get("trainer")), text(r.get("jockey")), text(r.get("context_type")), text(r.get("context_value"))))
    return rows


def index_context(rows: list[dict[str, Any]], entity_field: str, starts_field: str = "starts") -> dict[tuple[str, str, str], dict[str, Any]]:
    idx: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (canon(row.get(entity_field)), text(row.get("context_type")), text(row.get("context_value")).upper())
        current = idx.get(key)
        if current is None or int(to_float(row.get(starts_field)) or 0) > int(to_float(current.get(starts_field)) or 0):
            idx[key] = row
    return idx


def best_style(rows: list[dict[str, Any]], entity_field: str, starts_field: str) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if text(row.get("context_type")) != "run_style" or text(row.get("context_value")) == "UNKNOWN":
            continue
        key = canon(row.get(entity_field))
        starts = int(to_float(row.get(starts_field)) or 0)
        if starts < 10:
            continue
        score = metric_score(row) + min(starts, 100) / 100.0
        if key not in best or score > best[key]["_best_score"]:
            best[key] = dict(row) | {"_best_score": score}
    return best


def live_rows() -> list[dict[str, Any]]:
    board = read_csv(LIVE_BOARD)
    if board.empty:
        return []
    shape = read_csv(RACE_SHAPE_STORY)
    pace_by_race: dict[tuple[str, str, str], str] = {}
    if not shape.empty:
        for _, row in shape.iterrows():
            pace_by_race[(text(row.get("race_date")), canon(row.get("track")), text(row.get("race_no")))] = pace_scenario(
                row.get("tempo") or row.get("race_shape_label") or row.get("race_shape_story")
            )
    out: list[dict[str, Any]] = []
    for _, row in board.iterrows():
        key = (text(row.get("race_date")), canon(row.get("track")), text(row.get("race_no")))
        horse_style = run_style(row.get("projected_run_style") or row.get("run_style") or row.get("settling_band") or row.get("speed_map_bucket"))
        out.append(
            {
                "runner_key": text(row.get("runner_key")) or "|".join([text(row.get("race_date")), text(row.get("track")), text(row.get("race_no")), text(row.get("horse"))]),
                "runner_name": text(row.get("horse")),
                "race_date": text(row.get("race_date")),
                "track": text(row.get("track")),
                "race_no": text(row.get("race_no")),
                "trainer": text(row.get("trainer")),
                "jockey": text(row.get("jockey")),
                "horse_run_style": horse_style,
                "distance_band": distance_band(row.get("distance")),
                "track_condition": condition_band(row.get("track_condition")),
                "class_band": class_band(row.get("race_class")),
                "field_size_band": "UNKNOWN",
                "pace_scenario": pace_by_race.get(key, "UNKNOWN"),
            }
        )
    race_counts: dict[tuple[str, str, str], int] = {}
    for row in out:
        key = (row["race_date"], canon(row["track"]), row["race_no"])
        race_counts[key] = race_counts.get(key, 0) + 1
    for row in out:
        key = (row["race_date"], canon(row["track"]), row["race_no"])
        row["field_size_band"] = field_size_band(race_counts.get(key))
    return out


def style_alignment(live: list[dict[str, Any]], trainer_best: dict[str, dict[str, Any]], jockey_best: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in live:
        t_best = trainer_best.get(canon(row.get("trainer")), {})
        j_best = jockey_best.get(canon(row.get("jockey")), {})
        horse_style = text(row.get("horse_run_style")) or "UNKNOWN"
        trainer_style = text(t_best.get("context_value")) or "UNKNOWN"
        jockey_style = text(j_best.get("context_value")) or "UNKNOWN"
        matches = int(horse_style != "UNKNOWN" and horse_style == trainer_style) + int(horse_style != "UNKNOWN" and horse_style == jockey_style)
        conflict_count = int((horse_style, trainer_style) in STYLE_CONFLICTS) + int((horse_style, jockey_style) in STYLE_CONFLICTS)
        if matches == 2:
            score = 94.0
            summary = f"{horse_style} profile aligns with both trainer and jockey strengths."
        elif matches == 1:
            score = 78.0
            summary = f"{horse_style} profile aligns with one key connection."
        elif trainer_style != "UNKNOWN" and trainer_style == jockey_style:
            score = 58.0
            summary = f"Trainer and jockey both rate best with {trainer_style}; runner maps as {horse_style}."
        elif conflict_count >= 2:
            score = 38.0
            summary = f"{horse_style} profile conflicts with both connection style profiles."
        elif conflict_count == 1:
            score = 46.0
            summary = f"{horse_style} profile has one style conflict."
        else:
            score = 55.0
            summary = "Style evidence is mixed or incomplete."
        rows.append(
            {
                **{k: row[k] for k in ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey"]},
                "horse_run_style": horse_style,
                "trainer_best_style": trainer_style,
                "trainer_best_style_win_pct": t_best.get("win_pct", ""),
                "trainer_best_style_roi": t_best.get("roi", ""),
                "trainer_best_style_ae": t_best.get("ae", ""),
                "jockey_best_style": jockey_style,
                "jockey_best_style_win_pct": j_best.get("win_pct", ""),
                "jockey_best_style_roi": j_best.get("roi", ""),
                "jockey_best_style_ae": j_best.get("ae", ""),
                "style_alignment_score": round(score, 1),
                "style_alignment_band": score_band(score),
                "style_alignment_summary": summary,
            }
        )
    return rows


def average_scores(values: list[tuple[float, float]]) -> float:
    filtered = [(score, weight) for score, weight in values if score > 0 and weight > 0]
    if not filtered:
        return 55.0
    return sum(score * weight for score, weight in filtered) / sum(weight for _, weight in filtered)


def score_component(matches: list[dict[str, Any]], starts_field: str) -> float:
    values: list[tuple[float, float]] = []
    for row in matches:
        starts = int(to_float(row.get(starts_field)) or 0)
        weight = 1.0 + min(starts, 100) / 100.0
        values.append((metric_score(row), weight))
    return round(average_scores(values), 1)


def row_label(row: dict[str, Any], entity: str) -> str:
    return f"{entity} {text(row.get('context_type')).replace('_', ' ')} {text(row.get('context_value'))}: {text(row.get('context_band') or row.get('partnership_band'))}"


def build_contextual_scores(
    live: list[dict[str, Any]],
    trainer_idx: dict[tuple[str, str, str], dict[str, Any]],
    jockey_idx: dict[tuple[str, str, str], dict[str, Any]],
    partnership_idx: dict[tuple[str, str, str, str], dict[str, Any]],
    style_rows: list[dict[str, Any]],
    trainer_recent: pd.DataFrame,
    jockey_recent: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    style_idx = {row["runner_key"]: row for row in style_rows}
    trainer_recent_idx = {canon(row.get("trainer_name")): row for _, row in trainer_recent.iterrows()} if not trainer_recent.empty else {}
    jockey_recent_idx = {canon(row.get("jockey_name")): row for _, row in jockey_recent.iterrows()} if not jockey_recent.empty else {}
    scores: list[dict[str, Any]] = []
    live_feed: list[dict[str, Any]] = []
    for row in live:
        trainer_key = canon(row.get("trainer"))
        jockey_key = canon(row.get("jockey"))
        context_pairs = [
            ("overall", "ALL"),
            ("track", text(row.get("track")).upper()),
            ("distance_band", row.get("distance_band")),
            ("track_condition", row.get("track_condition")),
            ("class_band", row.get("class_band")),
            ("run_style", row.get("horse_run_style")),
            ("field_size_band", row.get("field_size_band")),
            ("pace_scenario", row.get("pace_scenario")),
        ]
        trainer_matches = [trainer_idx[k] for k in [(trainer_key, c, text(v).upper()) for c, v in context_pairs] if k in trainer_idx]
        jockey_matches = [jockey_idx[k] for k in [(jockey_key, c, text(v).upper()) for c, v in context_pairs] if k in jockey_idx]
        partnership_pairs = [
            ("overall", "ALL"),
            ("track", text(row.get("track")).upper()),
            ("distance_band", row.get("distance_band")),
            ("track_condition", row.get("track_condition")),
            ("class_band", row.get("class_band")),
        ]
        partnership_matches = [partnership_idx[k] for k in [(trainer_key, jockey_key, c, text(v).upper()) for c, v in partnership_pairs] if k in partnership_idx]

        trainer_score = score_component(trainer_matches, "starts")
        jockey_score = score_component(jockey_matches, "rides")
        partnership_score = score_component(partnership_matches, "starts") if partnership_matches else 55.0
        style_score = to_float(style_idx.get(row["runner_key"], {}).get("style_alignment_score")) or 55.0

        roi_values = [to_float(match.get("roi")) for match in trainer_matches + jockey_matches + partnership_matches]
        roi_values = [value for value in roi_values if value is not None]
        roi_avg = sum(roi_values) / len(roi_values) if roi_values else 0.0
        roi_score = max(20.0, min(95.0, 58.0 + roi_avg * 65.0))
        ae_values = [to_float(match.get("ae")) for match in trainer_matches + jockey_matches + partnership_matches]
        ae_values = [value for value in ae_values if value is not None]
        ae_avg = sum(ae_values) / len(ae_values) if ae_values else 1.0
        ae_score = max(20.0, min(95.0, 58.0 + (ae_avg - 1.0) * 42.0))

        t_recent = trainer_recent_idx.get(trainer_key, {})
        j_recent = jockey_recent_idx.get(jockey_key, {})
        trainer_recent_ae = to_float(t_recent.get("last_25_ae")) or 1.0
        jockey_recent_ae = to_float(j_recent.get("last_25_ae")) or 1.0
        trainer_recent_roi_pct = to_float(t_recent.get("last_25_roi_pct")) or 0.0
        jockey_recent_roi_pct = to_float(j_recent.get("last_25_roi_pct")) or 0.0
        trainer_recent_score = max(35.0, min(90.0, 55.0 + (trainer_recent_ae - 1.0) * 25.0 + trainer_recent_roi_pct * 0.15))
        jockey_recent_score = max(35.0, min(90.0, 55.0 + (jockey_recent_ae - 1.0) * 25.0 + jockey_recent_roi_pct * 0.15))

        nexus_score = round(
            average_scores(
                [
                    (trainer_recent_score, 0.8),
                    (jockey_recent_score, 0.8),
                    (trainer_score, 1.2),
                    (jockey_score, 1.2),
                    (partnership_score, 1.0 if partnership_matches else 0.4),
                    (style_score, 1.1),
                    (roi_score, 0.8),
                    (ae_score, 0.8),
                ]
            ),
            1,
        )
        positive_candidates = sorted(
            [m for m in trainer_matches + jockey_matches + partnership_matches if metric_score(m) >= 70],
            key=lambda r: metric_score(r),
            reverse=True,
        )
        risk_candidates = sorted(
            [m for m in trainer_matches + jockey_matches + partnership_matches if metric_score(m) < 55],
            key=lambda r: metric_score(r),
        )
        positives = [row_label(m, "Partnership" if "partnership_band" in m else "Context") for m in positive_candidates[:3]]
        risks = [row_label(m, "Partnership" if "partnership_band" in m else "Context") for m in risk_candidates[:3]]
        while len(positives) < 3:
            positives.append("")
        while len(risks) < 3:
            risks.append("")

        best_trainer = max(trainer_matches, key=metric_score, default={})
        best_jockey = max(jockey_matches, key=metric_score, default={})
        best_partnership = max(partnership_matches, key=metric_score, default={})
        band = score_band(nexus_score)
        summary = f"{band} contextual Nexus read: trainer {score_band(trainer_score)}, jockey {score_band(jockey_score)}, partnership {score_band(partnership_score)}, style {score_band(style_score)}."
        score_row = {
            **{k: row[k] for k in ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey"]},
            "trainer_context_score": trainer_score,
            "jockey_context_score": jockey_score,
            "partnership_score": round(partnership_score, 1),
            "style_alignment_score": round(style_score, 1),
            "roi_score": round(roi_score, 1),
            "ae_score": round(ae_score, 1),
            "nexus_context_score": nexus_score,
            "nexus_context_band": band,
            "top_positive_1": positives[0],
            "top_positive_2": positives[1],
            "top_positive_3": positives[2],
            "top_risk_1": risks[0],
            "top_risk_2": risks[1],
            "top_risk_3": risks[2],
            "nexus_summary": summary,
        }
        scores.append(score_row)
        live_feed.append(
            {
                **{k: score_row[k] for k in ["runner_key", "runner_name", "race_date", "track", "race_no", "trainer", "jockey", "nexus_context_score", "nexus_context_band"]},
                "trainer_recent_25_win_pct": t_recent.get("last_25_win_pct", ""),
                "trainer_recent_50_win_pct": t_recent.get("last_50_win_pct", ""),
                "trainer_recent_100_win_pct": t_recent.get("last_100_win_pct", ""),
                "jockey_recent_25_win_pct": j_recent.get("last_25_win_pct", ""),
                "jockey_recent_50_win_pct": j_recent.get("last_50_win_pct", ""),
                "jockey_recent_100_win_pct": j_recent.get("last_100_win_pct", ""),
                "trainer_best_context": row_label(best_trainer, "Trainer") if best_trainer else "",
                "jockey_best_context": row_label(best_jockey, "Jockey") if best_jockey else "",
                "partnership_band": best_partnership.get("partnership_band", "NEUTRAL") if best_partnership else "NEUTRAL",
                "style_alignment_score": score_row["style_alignment_score"],
                "style_alignment_band": score_band(score_row["style_alignment_score"]),
                "top_positive_1": positives[0],
                "top_positive_2": positives[1],
                "top_positive_3": positives[2],
                "top_risk_1": risks[0],
                "top_risk_2": risks[1],
                "top_risk_3": risks[2],
                "nexus_summary": summary,
            }
        )
    return scores, live_feed


def main() -> None:
    historical = prepare_historical()
    trainer_recent = read_csv(TRAINER_RECENT_V1)
    jockey_recent = read_csv(JOCKEY_RECENT_V1)
    trainer_style = read_csv(TRAINER_STYLE_V1)
    jockey_style = read_csv(JOCKEY_STYLE_V1)

    trainer_context, jockey_context = build_entity_contexts(historical, trainer_style, jockey_style)
    live = live_rows()
    partnership_v1 = read_csv(PARTNERSHIP_V1)
    partnership_context = build_partnership_contexts(historical, partnership_targets(live, partnership_v1))
    if not partnership_context:
        partnership_context = partnership_contexts_from_v1(partnership_v1)
    trainer_best = best_style(trainer_context, "trainer", "starts")
    jockey_best = best_style(jockey_context, "jockey", "rides")
    style_rows = style_alignment(live, trainer_best, jockey_best)

    trainer_idx = index_context(trainer_context, "trainer", "starts")
    jockey_idx = index_context(jockey_context, "jockey", "rides")
    partnership_idx = {
        (canon(row.get("trainer")), canon(row.get("jockey")), text(row.get("context_type")), text(row.get("context_value")).upper()): row
        for row in partnership_context
    }
    contextual_scores, live_feed = build_contextual_scores(
        live,
        trainer_idx,
        jockey_idx,
        partnership_idx,
        style_rows,
        trainer_recent,
        jockey_recent,
    )

    trainer_fields = ["trainer", "context_type", "context_value", "starts", "wins", "places", "win_pct", "place_pct", "roi", "ae", "avg_sp", "sample_band", "context_band"]
    jockey_fields = ["jockey", "context_type", "context_value", "rides", "wins", "places", "win_pct", "place_pct", "roi", "ae", "avg_sp", "sample_band", "context_band"]
    partnership_fields = ["trainer", "jockey", "context_type", "context_value", "starts", "wins", "places", "win_pct", "place_pct", "roi", "ae", "avg_sp", "sample_band", "partnership_band"]
    style_fields = [
        "runner_key",
        "runner_name",
        "race_date",
        "track",
        "race_no",
        "trainer",
        "jockey",
        "horse_run_style",
        "trainer_best_style",
        "trainer_best_style_win_pct",
        "trainer_best_style_roi",
        "trainer_best_style_ae",
        "jockey_best_style",
        "jockey_best_style_win_pct",
        "jockey_best_style_roi",
        "jockey_best_style_ae",
        "style_alignment_score",
        "style_alignment_band",
        "style_alignment_summary",
    ]
    score_fields = [
        "runner_key",
        "runner_name",
        "race_date",
        "track",
        "race_no",
        "trainer",
        "jockey",
        "trainer_context_score",
        "jockey_context_score",
        "partnership_score",
        "style_alignment_score",
        "roi_score",
        "ae_score",
        "nexus_context_score",
        "nexus_context_band",
        "top_positive_1",
        "top_positive_2",
        "top_positive_3",
        "top_risk_1",
        "top_risk_2",
        "top_risk_3",
        "nexus_summary",
    ]
    live_fields = [
        "runner_key",
        "runner_name",
        "race_date",
        "track",
        "race_no",
        "trainer",
        "jockey",
        "nexus_context_score",
        "nexus_context_band",
        "trainer_recent_25_win_pct",
        "trainer_recent_50_win_pct",
        "trainer_recent_100_win_pct",
        "jockey_recent_25_win_pct",
        "jockey_recent_50_win_pct",
        "jockey_recent_100_win_pct",
        "trainer_best_context",
        "jockey_best_context",
        "partnership_band",
        "style_alignment_score",
        "style_alignment_band",
        "top_positive_1",
        "top_positive_2",
        "top_positive_3",
        "top_risk_1",
        "top_risk_2",
        "top_risk_3",
        "nexus_summary",
    ]

    write_csv(TRAINER_CONTEXT_OUT, trainer_context, trainer_fields)
    write_csv(JOCKEY_CONTEXT_OUT, jockey_context, jockey_fields)
    write_csv(PARTNERSHIP_CONTEXT_OUT, partnership_context, partnership_fields)
    write_csv(STYLE_ALIGNMENT_OUT, style_rows, style_fields)
    write_csv(CONTEXTUAL_SCORE_OUT, contextual_scores, score_fields)
    write_csv(LIVE_CONTEXTUAL_FEED_OUT, live_feed, live_fields)

    summary_rows = [
        {"metric": "built_at", "value": datetime.now().isoformat(timespec="seconds")},
        {"metric": "historical_result_rows_used", "value": len(historical)},
        {"metric": "trainer_context_rows", "value": len(trainer_context)},
        {"metric": "jockey_context_rows", "value": len(jockey_context)},
        {"metric": "partnership_context_rows", "value": len(partnership_context)},
        {"metric": "style_alignment_rows", "value": len(style_rows)},
        {"metric": "contextual_score_rows", "value": len(contextual_scores)},
        {"metric": "live_contextual_feed_rows", "value": len(live_feed)},
        {"metric": "live_rows_with_nexus_context_score", "value": sum(1 for row in contextual_scores if text(row.get("nexus_context_score")))},
        {"metric": "barrier_specialist_logic_built", "value": "NO"},
        {"metric": "pricing_probability_rating_model_math_changed", "value": "NO"},
    ]
    write_csv(SUMMARY_OUT, summary_rows, ["metric", "value"])

    print("EDGEiQ Nexus contextual intelligence V2 built.")
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")


if __name__ == "__main__":
    main()
