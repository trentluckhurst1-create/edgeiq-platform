"""Research-only Stage011 live feature pipeline for the Caulfield dry run.

This builder consolidates the live field, Racing.com-native historical form,
and existing LAB245B candidate evidence into one 35-feature Stage011 matrix.
It does not retrain, score incomplete rows, read target-race outcomes, or use
market data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


FEATURES = [
    "current_distance",
    "hist_runs",
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "dist200_lvs_mean",
    "dist200_lvs_best",
    "represented_field_size",
    "barrier_position_pct",
    "jockey_prior_starts",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "trainer_prior_starts",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
]

LVS_FEATURES = {
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "dist200_lvs_mean",
    "dist200_lvs_best",
}

RCOM_NATIVE_CERTIFIED_FEATURES = {
    "current_distance",
    "hist_runs",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "represented_field_size",
    "barrier_position_pct",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
}

PERSONNEL_FEATURES = {
    "jockey_prior_starts",
    "jockey_prior_win_rate",
    "jockey_prior_top3_rate",
    "trainer_prior_starts",
    "trainer_prior_win_rate",
    "trainer_prior_top3_rate",
}

LAB245B_HISTORY_FEATURES = {
    "hist_runs",
    "lvs_last1",
    "lvs_mean3",
    "lvs_mean5",
    "lvs_median5",
    "lvs_std5",
    "lvs_peak",
    "lvs_worst5",
    "margin_mean5",
    "margin_std5",
    "margin_worst5",
    "margin_last1",
    "margin_last2",
    "last_distance",
    "margin_change_l1_l2",
    "margin_per_runner_last1",
    "margin_per_runner_last2",
    "days_since_last",
    "dist200_runs",
    "dist200_lvs_mean",
    "dist200_lvs_best",
    "clean_finish_mean5",
    "clean_last_finish",
    "clean_last_won",
    "clean_last_top3",
    "clean_finish_hist_n",
}

FORBIDDEN_LOWER = {
    "y",
    "winner",
    "won",
    "outcome",
    "sp",
    "bsp",
    "starting_price",
    "closing_price",
    "profit",
    "return",
}


@dataclass(frozen=True)
class Paths:
    field: Path
    form: Path
    public_snapshot: Path
    lab245b_candidates: Path
    lab245b_warehouse: Path
    output_dir: Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_distance(value: object) -> float:
    if pd.isna(value):
        return math.nan
    m = re.search(r"(\d+(?:\.\d+)?)\s*m", str(value), flags=re.I)
    return float(m.group(1)) if m else math.nan


def parse_margin(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "-"}:
        return math.nan
    m = re.search(r"(-?\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else math.nan


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "scratched", "scr"}


def stats_last(values: Iterable[float], n: int) -> tuple[float, float, float]:
    arr = np.asarray(list(values)[-n:], dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return math.nan, math.nan, math.nan
    return float(np.mean(arr)), float(np.median(arr)), float(np.std(arr))


def clean_columns(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy()
    d.columns = [str(c).strip() for c in d.columns]
    forbidden = sorted(c for c in d.columns if c.lower() in FORBIDDEN_LOWER)
    if forbidden:
        raise RuntimeError(f"Forbidden outcome/market columns present: {forbidden}")
    return d


def load_field(path: Path, target_date: str, venue: str) -> pd.DataFrame:
    d = clean_columns(pd.read_csv(path, dtype="string"))
    need = {
        "race_date",
        "venue",
        "race_no",
        "race_id",
        "horse_name",
        "horse_code",
        "eiq_horse_id",
        "race_entry_id",
        "barrier",
        "scratched",
        "trainer_code",
        "jockey_code",
    }
    missing = sorted(need - set(d.columns))
    if missing:
        raise RuntimeError(f"Field source missing columns: {missing}")
    d = d[d["race_date"].eq(target_date) & d["venue"].str.upper().eq(venue.upper())].copy()
    if d.empty:
        raise RuntimeError(f"No live field rows found for {venue} {target_date}")
    if d.duplicated(["race_id", "race_entry_id"]).any():
        dup = d[d.duplicated(["race_id", "race_entry_id"], keep=False)][["race_id", "race_entry_id"]].head(10)
        raise RuntimeError(f"Duplicate live runners: {dup.to_dict('records')}")
    d["race_no_num"] = pd.to_numeric(d["race_no"], errors="coerce")
    d["barrier_num"] = pd.to_numeric(d["barrier"], errors="coerce")
    d["is_scratched"] = d["scratched"].map(parse_bool)
    return d.sort_values(["race_no_num", "race_entry_id"], kind="stable").reset_index(drop=True)


def load_form(path: Path, target_date: str) -> pd.DataFrame:
    d = clean_columns(pd.read_csv(path, dtype="string"))
    need = {
        "horse_code",
        "horse_name",
        "race_date",
        "race_code",
        "distance",
        "field_size",
        "finish",
        "margin",
        "jockey_id",
        "trainer_id",
    }
    missing = sorted(need - set(d.columns))
    if missing:
        raise RuntimeError(f"Form source missing columns: {missing}")
    d["race_date_dt"] = pd.to_datetime(d["race_date"], errors="coerce")
    target = pd.Timestamp(target_date)
    d = d[d["race_date_dt"].notna() & d["race_date_dt"].lt(target)].copy()
    d["distance_m"] = d["distance"].map(parse_distance)
    d["field_size_num"] = pd.to_numeric(d["field_size"], errors="coerce")
    d["finish_num"] = pd.to_numeric(d["finish"], errors="coerce")
    d["margin_len"] = d["margin"].map(parse_margin)
    d["race_code_sort"] = pd.to_numeric(d["race_code"], errors="coerce")
    return d.sort_values(["horse_code", "race_date_dt", "race_code_sort"], kind="stable").reset_index(drop=True)


def scheduled_utc(target_date: str, local_time_text: str) -> str:
    text = str(local_time_text or "").strip().lower()
    if not text:
        return ""
    parsed = pd.to_datetime(f"{target_date} {text}", format="%Y-%m-%d %I:%M%p", errors="coerce")
    if pd.isna(parsed):
        return ""
    local = parsed.to_pydatetime().replace(tzinfo=ZoneInfo("Australia/Melbourne"))
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_race_metadata(path: Path, target_date: str, venue: str) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["race_date", "venue", "race_no", "current_distance"])
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = []
    seen = set()
    for race in payload.get("races", []):
        if str(race.get("race_date")) != target_date or str(race.get("venue", "")).upper() != venue.upper():
            continue
        race_no = str(race.get("race_no"))
        key = (target_date, venue.upper(), race_no)
        if key in seen:
            continue
        seen.add(key)
        raw_text = str(race.get("raw_text", ""))
        distance = math.nan
        scheduled = ""
        for line in [x.strip() for x in raw_text.splitlines() if x.strip()]:
            if math.isnan(distance) and re.fullmatch(r"\d{3,4}m", line, flags=re.I):
                distance = parse_distance(line)
            if not scheduled and re.fullmatch(r"\d{1,2}:\d{2}\s*(am|pm)", line, flags=re.I):
                scheduled = line.lower().replace(" ", "")
            if not math.isnan(distance) and scheduled:
                break
        rows.append(
            {
                "race_date": target_date,
                "venue": venue,
                "race_no": race_no,
                "current_distance": distance,
                "scheduled_local_time_text": scheduled,
                "scheduled_start_time_utc": scheduled_utc(target_date, scheduled),
            }
        )
    return pd.DataFrame(rows)


def load_lab245b_candidates(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["race_date", "race_no", "horse_name", "canonical_horse_id"])
    d = clean_columns(pd.read_csv(path, dtype="string"))
    keep = [c for c in ["race_date", "race_no", "horse_name", "canonical_horse_id", "feature_status"] if c in d.columns]
    return d[keep].drop_duplicates(keep).copy()


def load_lab245b_warehouse(path: Path, target_date: str, canonical_ids: set[str]) -> pd.DataFrame:
    need = [
        "canonical_race_id",
        "canonical_horse_id",
        "race_date",
        "distance_metres",
        "field_size",
        "finish_position",
        "finish_margin",
        "runner_lvs",
    ]
    if not path.is_file() or not canonical_ids:
        return pd.DataFrame(columns=need + ["dt"])
    rows = []
    target = pd.Timestamp(target_date)
    wanted = {str(x).strip() for x in canonical_ids if str(x).strip()}
    for chunk in pd.read_csv(path, usecols=need, dtype="string", chunksize=250000):
        chunk["canonical_horse_id"] = chunk["canonical_horse_id"].astype("string").str.strip()
        chunk = chunk[chunk["canonical_horse_id"].isin(wanted)].copy()
        if chunk.empty:
            continue
        chunk["dt"] = pd.to_datetime(chunk["race_date"], errors="coerce")
        chunk = chunk[chunk["dt"].notna() & chunk["dt"].lt(target)].copy()
        if not chunk.empty:
            rows.append(chunk)
    if not rows:
        return pd.DataFrame(columns=need + ["dt"])
    d = pd.concat(rows, ignore_index=True)
    for col in ["distance_metres", "field_size", "finish_position", "finish_margin", "runner_lvs"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    return d.sort_values(["canonical_horse_id", "dt", "canonical_race_id"], kind="stable").reset_index(drop=True)


def personnel_prior(form: pd.DataFrame, code: object, code_col: str, target_date: str) -> tuple[float, float, float]:
    if pd.isna(code):
        return math.nan, math.nan, math.nan
    text = str(code).strip()
    if not text or text.lower() in {"nan", "<na>", "none"}:
        return math.nan, math.nan, math.nan
    target = pd.Timestamp(target_date)
    g = form[(form[code_col].astype("string").str.strip().eq(text)) & (form["race_date_dt"].lt(target))].copy()
    g = g[g["finish_num"].notna()]
    starts = int(len(g))
    if starts == 0:
        return math.nan, math.nan, math.nan
    wins = int((g["finish_num"] == 1).sum())
    top3 = int((g["finish_num"] <= 3).sum())
    return float(starts), float((wins + 1) / (starts + 10)), float((top3 + 3) / (starts + 10))


def original_history_stats(values: list[float], n: int) -> tuple[float, float, float]:
    arr = np.asarray(values[-n:], dtype=float)
    if len(arr) == 0:
        return math.nan, math.nan, math.nan
    return float(np.mean(arr)), float(np.median(arr)), float(np.std(arr))


def finite_scalar(value: object) -> bool:
    return pd.notna(value) and bool(np.isfinite(float(value)))


def lab245b_features_from_history(hist: pd.DataFrame, target_date: str, current_distance: float) -> dict:
    hist = hist.sort_values(["dt", "canonical_race_id"], kind="stable").copy()
    rec = {feature: math.nan for feature in LAB245B_HISTORY_FEATURES}
    if hist.empty:
        return rec
    lvs = [float(x) for x in hist["runner_lvs"] if np.isfinite(x)]
    margins = [float(x) for x in hist["finish_margin"] if np.isfinite(x)]
    poss = [float(x) for x in hist["finish_position"] if np.isfinite(x)]
    dates = pd.to_datetime(hist["dt"], errors="coerce").dropna()
    l3 = original_history_stats(lvs, 3)
    l5 = original_history_stats(lvs, 5)
    m5 = original_history_stats(margins, 5)
    p5 = original_history_stats(poss, 5)
    rec["hist_runs"] = float(len(hist))
    rec["lvs_last1"] = lvs[-1] if lvs else math.nan
    rec["lvs_mean3"] = l3[0]
    rec["lvs_mean5"] = l5[0]
    rec["lvs_median5"] = l5[1]
    rec["lvs_std5"] = l5[2]
    rec["lvs_peak"] = max(lvs) if lvs else math.nan
    rec["lvs_worst5"] = min(lvs[-5:]) if lvs else math.nan
    rec["margin_mean5"] = m5[0]
    rec["margin_std5"] = m5[2]
    rec["margin_worst5"] = max(margins[-5:]) if margins else math.nan
    rec["margin_last1"] = margins[-1] if len(margins) >= 1 else math.nan
    rec["margin_last2"] = margins[-2] if len(margins) >= 2 else math.nan
    if len(margins) >= 2:
        rec["margin_change_l1_l2"] = margins[-1] - margins[-2]
    rec["last_distance"] = float(hist.iloc[-1]["distance_metres"]) if pd.notna(hist.iloc[-1]["distance_metres"]) else math.nan
    if len(hist) >= 1 and finite_scalar(hist.iloc[-1]["finish_margin"]) and finite_scalar(hist.iloc[-1]["field_size"]):
        rec["margin_per_runner_last1"] = float(hist.iloc[-1]["finish_margin"] / max(hist.iloc[-1]["field_size"] - 1.0, 1.0))
    if len(hist) >= 2 and finite_scalar(hist.iloc[-2]["finish_margin"]) and finite_scalar(hist.iloc[-2]["field_size"]):
        rec["margin_per_runner_last2"] = float(hist.iloc[-2]["finish_margin"] / max(hist.iloc[-2]["field_size"] - 1.0, 1.0))
    if len(dates):
        rec["days_since_last"] = float((pd.Timestamp(target_date) - dates.max()).days)
    if np.isfinite(current_distance):
        near = hist[np.abs(pd.to_numeric(hist["distance_metres"], errors="coerce") - current_distance) <= 200]
        nl = [float(x) for x in near["runner_lvs"] if np.isfinite(x)]
        rec["dist200_runs"] = float(len(near))
        rec["dist200_lvs_mean"] = float(np.mean(nl)) if nl else math.nan
        rec["dist200_lvs_best"] = max(nl) if nl else math.nan
    rec["clean_finish_mean5"] = p5[0]
    rec["clean_last_finish"] = poss[-1] if poss else math.nan
    rec["clean_last_won"] = float(poss[-1] == 1) if poss else math.nan
    rec["clean_last_top3"] = float(poss[-1] <= 3) if poss else math.nan
    rec["clean_finish_hist_n"] = float(min(len(poss), 5)) if poss else math.nan
    return rec


def count_matching_prior_records(form_hist: pd.DataFrame, warehouse_hist: pd.DataFrame) -> int:
    if form_hist.empty or warehouse_hist.empty:
        return 0
    wh = warehouse_hist.copy()
    wh["date_key"] = pd.to_datetime(wh["dt"], errors="coerce").dt.date.astype("string")
    wh["distance_key"] = pd.to_numeric(wh["distance_metres"], errors="coerce").round().astype("Int64").astype("string")
    wh["finish_key"] = pd.to_numeric(wh["finish_position"], errors="coerce").round().astype("Int64").astype("string")
    wh["margin_key"] = pd.to_numeric(wh["finish_margin"], errors="coerce")
    used = set()
    matches = 0
    for r in form_hist.itertuples(index=False):
        if pd.isna(r.race_date_dt) or pd.isna(r.distance_m) or pd.isna(r.finish_num):
            continue
        mask = (
            wh["date_key"].eq(r.race_date_dt.date().isoformat())
            & wh["distance_key"].eq(str(int(round(float(r.distance_m)))))
            & wh["finish_key"].eq(str(int(round(float(r.finish_num)))))
        )
        cand = wh[mask].copy()
        if cand.empty:
            continue
        if pd.notna(r.margin_len):
            cand = cand[(cand["margin_key"] - float(r.margin_len)).abs().le(0.25)]
            if cand.empty:
                continue
        for idx in cand.index:
            if idx not in used:
                used.add(idx)
                matches += 1
                break
    return matches


def live_source_eiq_horse_id(horse_code: object) -> str:
    """Acquisition convention: SHA256 of numeric Racing.com horse code with .0 suffix."""
    code = str(horse_code).strip()
    if not re.fullmatch(r"\\d+", code):
        return ""
    return "EIQ_HORSE_" + hashlib.sha256((code + ".0").encode("utf-8")).hexdigest()[:16].upper()


def build_identity_bridge(field: pd.DataFrame, form: pd.DataFrame, warehouse: pd.DataFrame, target_date: str) -> pd.DataFrame:
    rows = []
    histories = {k: g.copy() for k, g in warehouse.groupby("canonical_horse_id", sort=False)}
    for row in field.itertuples(index=False):
        canonical = str(getattr(row, "eiq_horse_id", "") or "").strip()
        horse_code = str(row.horse_code)
        rform = form[form["horse_code"].astype("string").eq(horse_code)].copy()
        whist = histories.get(canonical, pd.DataFrame(columns=warehouse.columns))
        matched = count_matching_prior_records(rform, whist)
        # Multiple observations from the same historical race cannot certify identity.
        distinct_races = int(whist["canonical_race_id"].dropna().nunique()) if len(whist) else 0
        expected_canonical = live_source_eiq_horse_id(horse_code)
        status = "NOT_CERTIFIED"
        if not canonical or canonical.lower() in {"nan", "<na>", "none"}:
            status = "NO_EIQ_CANONICAL_ID"
        elif not expected_canonical or canonical != expected_canonical:
            status = "EIQ_ID_PROVENANCE_MISMATCH"
        elif whist.empty:
            status = "NO_STRICT_PRIOR_LAB245B_HISTORY"
        elif distinct_races < 2:
            status = "INSUFFICIENT_DISTINCT_HISTORICAL_RACES"
        elif whist["canonical_race_id"].duplicated().any():
            status = "DUPLICATE_HISTORICAL_RACE_ID"
        elif matched >= 2:
            status = "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
        elif matched == 1:
            status = "ONE_PRIOR_MATCH_INSUFFICIENT"
        else:
            status = "NO_PRIOR_FORM_MATCH"
        current_distance = float(getattr(row, "current_distance")) if pd.notna(getattr(row, "current_distance")) else math.nan
        feats = lab245b_features_from_history(whist, target_date, current_distance) if status == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH" else {}
        rows.append(
            {
                "race_id": row.race_id,
                "runner_id": row.race_entry_id,
                "horse_code": row.horse_code,
                "horse_name": row.horse_name,
                "canonical_horse_id": canonical,
                "rcom_prior_records": int(len(rform)),
                "lab245b_prior_records": int(len(whist)),
                "matched_prior_records": int(matched),
                "distinct_historical_races": distinct_races,
                "expected_source_derived_eiq_id": expected_canonical,
                "latest_lab245b_date": str(pd.to_datetime(whist["dt"]).max().date()) if len(whist) else "",
                "identity_bridge_status": status,
                **feats,
            }
        )
    return pd.DataFrame(rows)


def build_runner_features(row: pd.Series, form: pd.DataFrame, active_field_sizes: dict, target_date: str) -> dict:
    horse_code = str(row["horse_code"])
    hist = form[form["horse_code"].astype("string").eq(horse_code)].copy()
    hist = hist.sort_values(["race_date_dt", "race_code_sort"], kind="stable")
    margins = pd.to_numeric(hist["margin_len"], errors="coerce").to_numpy(float)
    finishes = pd.to_numeric(hist["finish_num"], errors="coerce").to_numpy(float)
    distances = pd.to_numeric(hist["distance_m"], errors="coerce").to_numpy(float)
    field_sizes = pd.to_numeric(hist["field_size_num"], errors="coerce").to_numpy(float)
    race_dates = pd.to_datetime(hist["race_date_dt"], errors="coerce")

    rec = {feature: math.nan for feature in FEATURES}
    race_id = str(row["race_id"])
    current_distance = float(row.get("current_distance")) if pd.notna(row.get("current_distance")) else math.nan
    active_field_size = active_field_sizes.get(race_id, math.nan)
    barrier = float(row["barrier_num"]) if pd.notna(row["barrier_num"]) else math.nan

    rec["current_distance"] = current_distance
    rec["hist_runs"] = float(len(hist))
    rec["represented_field_size"] = float(active_field_size) if pd.notna(active_field_size) else math.nan
    if pd.notna(barrier) and pd.notna(active_field_size) and active_field_size > 1:
        rec["barrier_position_pct"] = float((barrier - 1.0) / (active_field_size - 1.0))

    finite_margins = [float(x) for x in margins if np.isfinite(x)]
    finite_finishes = [float(x) for x in finishes if np.isfinite(x)]
    if finite_margins:
        m5 = np.asarray(finite_margins[-5:], dtype=float)
        rec["margin_mean5"] = float(np.mean(m5))
        rec["margin_std5"] = float(np.std(m5))
        rec["margin_worst5"] = float(np.max(m5))
        rec["margin_last1"] = float(finite_margins[-1])
        if len(finite_margins) >= 2:
            rec["margin_last2"] = float(finite_margins[-2])
            rec["margin_change_l1_l2"] = float(finite_margins[-1] - finite_margins[-2])

    if len(hist):
        rec["last_distance"] = float(distances[-1]) if np.isfinite(distances[-1]) else math.nan
        valid_dates = race_dates.dropna()
        if len(valid_dates):
            rec["days_since_last"] = float((pd.Timestamp(target_date) - valid_dates.max()).days)
    if finite_finishes:
        f5 = np.asarray(finite_finishes[-5:], dtype=float)
        rec["clean_finish_mean5"] = float(np.mean(f5))
        rec["clean_last_finish"] = float(finite_finishes[-1])
        rec["clean_last_won"] = float(finite_finishes[-1] == 1)
        rec["clean_last_top3"] = float(finite_finishes[-1] <= 3)
        rec["clean_finish_hist_n"] = float(len(f5))

    if len(hist) >= 1 and np.isfinite(margins[-1]) and np.isfinite(field_sizes[-1]):
        rec["margin_per_runner_last1"] = float(margins[-1] / max(field_sizes[-1] - 1.0, 1.0))
    if len(hist) >= 2 and np.isfinite(margins[-2]) and np.isfinite(field_sizes[-2]):
        rec["margin_per_runner_last2"] = float(margins[-2] / max(field_sizes[-2] - 1.0, 1.0))

    if np.isfinite(current_distance):
        near = hist[np.abs(pd.to_numeric(hist["distance_m"], errors="coerce") - current_distance) <= 200]
        rec["dist200_runs"] = float(len(near))

    js = personnel_prior(form, row.get("jockey_code"), "jockey_id", target_date)
    ts = personnel_prior(form, row.get("trainer_code"), "trainer_id", target_date)
    rec["jockey_prior_starts"], rec["jockey_prior_win_rate"], rec["jockey_prior_top3_rate"] = js
    rec["trainer_prior_starts"], rec["trainer_prior_win_rate"], rec["trainer_prior_top3_rate"] = ts
    return rec


def feature_reason(feature: str, value: object, has_form: bool, source: str = "") -> tuple[str, str]:
    if source == "LAB245B_CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH" and pd.notna(value):
        return "POPULATED_CERTIFIED_LAB245B_BRIDGE", "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
    if feature in LVS_FEATURES:
        return "MISSING", "NO_CERTIFIED_LIVE_LVS_TIMING_IDENTITY"
    if feature in PERSONNEL_FEATURES:
        if pd.notna(value):
            return "POPULATED_UNCERTIFIED", "RCOM_NATIVE_PARTIAL_PERSONNEL_HISTORY"
        return "MISSING", "NO_CERTIFIED_PERSONNEL_HISTORY"
    if pd.notna(value):
        return "POPULATED_CERTIFIED_RCOM_NATIVE", "RCOM_NATIVE_STRICT_PRIOR_FORM_OR_FIELD"
    if not has_form and feature not in {"current_distance", "represented_field_size", "barrier_position_pct"}:
        return "MISSING", "FIRST_STARTER_OR_NO_RCOM_HISTORY"
    return "MISSING", "SOURCE_FIELD_UNAVAILABLE"


def build_matrix(
    paths: Paths, target_date: str, venue: str, expected_rows: int | None = 104
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    field = load_field(paths.field, target_date, venue)
    if expected_rows is not None and len(field) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} declared runners, found {len(field)}")
    form = load_form(paths.form, target_date)
    metadata = load_race_metadata(paths.public_snapshot, target_date, venue)
    candidates = load_lab245b_candidates(paths.lab245b_candidates)

    field = field.merge(
        metadata[["race_no", "current_distance", "scheduled_local_time_text", "scheduled_start_time_utc"]],
        on="race_no",
        how="left",
    )
    canonical_ids = set(field["eiq_horse_id"].dropna().astype(str).str.strip())
    warehouse = load_lab245b_warehouse(paths.lab245b_warehouse, target_date, canonical_ids)
    identity_bridge = build_identity_bridge(field, form, warehouse, target_date)
    bridge_features = identity_bridge.set_index(["race_id", "runner_id"]).to_dict("index")
    active_field_sizes = field[~field["is_scratched"]].groupby("race_id")["race_entry_id"].nunique().to_dict()
    candidate_keys = {
        (str(r.race_date), str(r.race_no), str(r.horse_name).strip().upper())
        for r in candidates.itertuples(index=False)
        if hasattr(r, "race_date") and hasattr(r, "race_no") and hasattr(r, "horse_name")
    }

    rows = []
    feature_status_rows = []
    for src in field.itertuples(index=False):
        row = pd.Series(src._asdict())
        race_no = str(row["race_no"])
        horse_name = str(row["horse_name"])
        hist = form[form["horse_code"].astype("string").eq(str(row["horse_code"]))]
        features = build_runner_features(row, form, active_field_sizes, target_date)
        feature_sources = {feature: "RCOM_NATIVE_STRICT_PRIOR_FORM_OR_FIELD" for feature in RCOM_NATIVE_CERTIFIED_FEATURES}
        feature_sources.update({feature: "RCOM_NATIVE_PARTIAL_PERSONNEL_HISTORY" for feature in PERSONNEL_FEATURES})
        feature_sources.update({feature: "" for feature in LVS_FEATURES})
        bridge_key = (row["race_id"], row["race_entry_id"])
        bridge_row = bridge_features.get(bridge_key, {})
        if bridge_row.get("identity_bridge_status") == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH":
            for feature in LAB245B_HISTORY_FEATURES:
                if feature in bridge_row and pd.notna(bridge_row[feature]):
                    features[feature] = bridge_row[feature]
                    feature_sources[feature] = "LAB245B_CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
        candidate_key = (target_date, race_no, horse_name.strip().upper())
        has_candidate = candidate_key in candidate_keys
        has_form = len(hist) > 0
        reason_codes = []
        populated = 0
        certified_populated = 0
        uncertified_populated = 0
        for feature in FEATURES:
            status, reason = feature_reason(feature, features[feature], has_form, feature_sources.get(feature, ""))
            feature_status_rows.append(
                {
                    "race_id": row["race_id"],
                    "runner_id": row["race_entry_id"],
                    "horse_code": row["horse_code"],
                    "feature": feature,
                    "value_populated": bool(pd.notna(features[feature])),
                    "feature_status": status,
                    "reason_code": reason,
                    "feature_source": feature_sources.get(feature, ""),
                }
            )
            if pd.notna(features[feature]):
                populated += 1
                if status in {"POPULATED_CERTIFIED_RCOM_NATIVE", "POPULATED_CERTIFIED_LAB245B_BRIDGE"}:
                    certified_populated += 1
                elif status == "POPULATED_UNCERTIFIED":
                    uncertified_populated += 1
            if status == "MISSING":
                reason_codes.append(f"{feature}:{reason}")
        if has_candidate:
            history_status = "HISTORICAL_LVS_CANDIDATE_UNCERTIFIED"
        elif has_form:
            history_status = "RACINGCOM_NATIVE_FORM_AVAILABLE"
        else:
            history_status = "FIRST_STARTER_OR_INSUFFICIENT_HISTORY"
        if bridge_row.get("identity_bridge_status") == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH":
            history_status = "LAB245B_IDENTITY_BRIDGE_CERTIFIED"
        complete_values = populated == len(FEATURES)
        certified_complete = certified_populated == len(FEATURES)
        eligible = bool(complete_values and certified_complete and not row["is_scratched"])
        rows.append(
            {
                "race_date": target_date,
                "venue": venue,
                "race_no": race_no,
                "race_id": row["race_id"],
                "runner_id": row["race_entry_id"],
                "horse_code": row["horse_code"],
                "horse_name": horse_name,
                "barrier": row["barrier"],
                "scratched": bool(row["is_scratched"]),
                "jockey_code": row.get("jockey_code"),
                "trainer_code": row.get("trainer_code"),
                "scheduled_local_time_text": row.get("scheduled_local_time_text"),
                "scheduled_start_time_utc": row.get("scheduled_start_time_utc"),
                "rcom_form_runs": int(len(hist)),
                "canonical_horse_id": row.get("eiq_horse_id"),
                "identity_bridge_status": bridge_row.get("identity_bridge_status", "NOT_EVALUATED"),
                "identity_bridge_matched_prior_records": bridge_row.get("matched_prior_records", 0),
                "lab245b_prior_records": bridge_row.get("lab245b_prior_records", 0),
                "historical_identity_status": history_status,
                "feature_status": "ELIGIBLE_FOR_SCORING" if eligible else "INCOMPLETE_OR_UNCERTIFIED_DO_NOT_SCORE",
                "eligible_for_stage011_scoring": eligible,
                "populated_feature_count": populated,
                "certified_populated_feature_count": certified_populated,
                "uncertified_populated_feature_count": uncertified_populated,
                "missing_feature_count": len(FEATURES) - populated,
                "missing_reason_codes": "|".join(reason_codes[:80]),
                **features,
            }
        )

    matrix = pd.DataFrame(rows)
    feature_status = pd.DataFrame(feature_status_rows)
    family_rows = []
    family_map = {
        "CURRENT_CONTEXT": ["current_distance", "represented_field_size", "barrier_position_pct"],
        "RCOM_NATIVE_HISTORY": [
            "hist_runs",
            "margin_mean5",
            "margin_std5",
            "margin_worst5",
            "margin_last1",
            "margin_last2",
            "last_distance",
            "margin_change_l1_l2",
            "margin_per_runner_last1",
            "margin_per_runner_last2",
            "days_since_last",
            "dist200_runs",
            "clean_finish_mean5",
            "clean_last_finish",
            "clean_last_won",
            "clean_last_top3",
            "clean_finish_hist_n",
        ],
        "LVS_TIMING": sorted(LVS_FEATURES),
        "PERSONNEL_PARTIAL": sorted(PERSONNEL_FEATURES),
    }
    for family, cols in family_map.items():
        vals = matrix[cols].notna()
        family_rows.append(
            {
                "family": family,
                "features": len(cols),
                "populated_cells": int(vals.sum().sum()),
                "total_cells": int(vals.size),
                "rows_all_features_populated": int(vals.all(axis=1).sum()),
                "coverage_pct": round(float(vals.sum().sum() / vals.size * 100), 2) if vals.size else 0.0,
            }
        )
    coverage = pd.DataFrame(family_rows)
    audit = {
        "status": "PASS" if len(matrix) == expected_rows else "FAIL",
        "target_date": target_date,
        "venue": venue,
        "declared_runners": int(len(matrix)),
        "races": int(matrix["race_id"].nunique()),
        "eligible_for_stage011_scoring": int(matrix["eligible_for_stage011_scoring"].sum()),
        "rcom_native_form_available": int(matrix["rcom_form_runs"].gt(0).sum()),
        "lab245b_identity_bridge_status_counts": identity_bridge["identity_bridge_status"].value_counts().to_dict(),
        "lab245b_identity_bridge_certified": int(identity_bridge["identity_bridge_status"].eq("CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH").sum()),
        "historical_identity_status_counts": matrix["historical_identity_status"].value_counts().to_dict(),
        "feature_status_counts": matrix["feature_status"].value_counts().to_dict(),
        "feature_manifest": FEATURES,
        "feature_manifest_sha256": hashlib.sha256(json.dumps(FEATURES, separators=(",", ":")).encode()).hexdigest(),
        "stage011_semantics": {
            "margin_winner_handling": "PRESERVE_SOURCE_FINISH_MARGIN_NO_WINNER_ZEROING",
            "lab245b_history_aggregate_policy": "FINITE_VALUES_THEN_LAST_N_FOR_LVS_MARGIN_FINISH_AGGREGATES",
            "margin_per_runner_policy": "MOST_RECENT_RAW_PRIOR_STARTS_REQUIRE_MARGIN_AND_FIELD_SIZE",
            "personnel_prior_policy": "(wins+1)/(starts+10) and (top3+3)/(starts+10) per D45 source; live values remain partial_uncertified",
            "identity_bridge_certification": "exact EIQ horse id plus at least two matching strict-prior Racing.com/LAB245B records on date/distance/finish/margin",
        },
        "sources": {
            "field": str(paths.field),
            "field_sha256": file_sha256(paths.field),
            "form": str(paths.form),
            "form_sha256": file_sha256(paths.form),
            "public_snapshot": str(paths.public_snapshot),
            "public_snapshot_sha256": file_sha256(paths.public_snapshot) if paths.public_snapshot.is_file() else None,
            "lab245b_candidates": str(paths.lab245b_candidates),
            "lab245b_candidates_sha256": file_sha256(paths.lab245b_candidates) if paths.lab245b_candidates.is_file() else None,
            "lab245b_warehouse": str(paths.lab245b_warehouse),
            "lab245b_warehouse_sha256": file_sha256(paths.lab245b_warehouse) if paths.lab245b_warehouse.is_file() else None,
        },
        "no_market_features": True,
        "no_current_race_outcomes": True,
        "no_stage011_retraining": True,
        "model_ready_for_prospective_scoring": bool(matrix["eligible_for_stage011_scoring"].sum() > 0),
        "primary_blockers": [
            "Only runners with exact EIQ identity plus at least two matching strict-prior Racing.com/LAB245B records are certified for LAB245B timing features.",
            "Personnel prior statistics from Caulfield browser form are partial to the 98 captured horses, not the full historical jockey/trainer universe.",
            "Historical LAB245B candidate links are preserved as candidate evidence only and are not promoted to certified identity.",
        ],
    }
    return matrix, coverage, feature_status, identity_bridge, audit


def write_outputs(
    matrix: pd.DataFrame,
    coverage: pd.DataFrame,
    feature_status: pd.DataFrame,
    identity_bridge: pd.DataFrame,
    audit: dict,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "matrix": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_MATRIX.csv",
        "coverage": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_COVERAGE_BY_FAMILY.csv",
        "feature_status": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_STATUS_LONG.csv",
        "identity_bridge": output_dir / "EDGEIQ_STAGE011_LIVE_IDENTITY_BRIDGE_AUDIT.csv",
        "audit": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json",
        "score_input": output_dir / "EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv",
    }
    matrix.to_csv(paths["matrix"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    feature_status.to_csv(paths["feature_status"], index=False)
    identity_bridge.to_csv(paths["identity_bridge"], index=False)
    paths["audit"].write_text(json.dumps(audit, indent=2), encoding="utf-8")
    eligible_cols = ["race_id", "runner_id", "scratch_status", "scoring_timestamp", "scheduled_start_time"] + FEATURES
    eligible = matrix[matrix["eligible_for_stage011_scoring"]].copy()
    score = pd.DataFrame(columns=eligible_cols)
    if not eligible.empty:
        score = eligible.rename(columns={"scratched": "scratch_status"})[["race_id", "runner_id"] + FEATURES].copy()
        score["scratch_status"] = "ACTIVE"
        score["scoring_timestamp"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        score["scheduled_start_time"] = eligible["scheduled_start_time_utc"].fillna("")
        score = score[eligible_cols]
    score.to_csv(paths["score_input"], index=False)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", default="2026-10-14")
    parser.add_argument("--venue", default="Caulfield")
    parser.add_argument("--expected-runners", type=int, default=104)
    parser.add_argument(
        "--field",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\october_graphql_field_identities.csv"),
    )
    parser.add_argument(
        "--form",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv"),
    )
    parser.add_argument(
        "--public-snapshot",
        type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\public_race_snapshot_20261012T051330Z.json"),
    )
    parser.add_argument(
        "--lab245b-candidates",
        type=Path,
        default=Path(r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_FEATURE_CANDIDATES_V3.csv"),
    )
    parser.add_argument(
        "--lab245b-warehouse",
        type=Path,
        default=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/research/stage011_live_completion"),
    )
    args = parser.parse_args()
    paths = Paths(args.field, args.form, args.public_snapshot, args.lab245b_candidates, args.lab245b_warehouse, args.output_dir)
    matrix, coverage, feature_status, identity_bridge, audit = build_matrix(
        paths, args.target_date, args.venue, args.expected_runners
    )
    outputs = write_outputs(matrix, coverage, feature_status, identity_bridge, audit, args.output_dir)
    print("EDGEIQ_STAGE011_LIVE_FEATURE_PIPELINE")
    print("RUNNERS", len(matrix), "RACES", matrix["race_id"].nunique())
    print("ELIGIBLE_FOR_STAGE011_SCORING", int(matrix["eligible_for_stage011_scoring"].sum()))
    print("IDENTITY_STATUS", matrix["historical_identity_status"].value_counts().to_dict())
    print("LAB245B_IDENTITY_BRIDGE", identity_bridge["identity_bridge_status"].value_counts().to_dict())
    print("COVERAGE_BY_FAMILY", coverage.to_dict("records"))
    for key, value in outputs.items():
        print(key.upper(), value)
    print("NO_MARKET; NO_TARGET_OUTCOMES; NO_STAGE011_RETRAINING; FAIL_CLOSED_SCORING")


if __name__ == "__main__":
    main()
