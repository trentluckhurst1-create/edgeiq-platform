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

LAB245B_WAREHOUSE_EXPECTED_SHA256 = "169652f38b830a4d2337975d65d9cead16fe306373ac4802bc57b7b33793a8fb"


@dataclass(frozen=True)
class Paths:
    field: Path
    form: Path
    public_snapshot: Path
    lab245b_candidates: Path
    lab245b_warehouse: Path
    perf026: Path
    output_dir: Path


@dataclass(frozen=True)
class SourceResolution:
    name: str
    requested_path: str
    resolved_path: str
    status: str
    required: bool
    sha256: str | None
    expected_sha256: str | None
    alternatives: list[str]


def sha_text(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16].upper()


def rcom_current_id(domain: str, code: object) -> str:
    if pd.isna(code):
        return ""
    text = str(code).strip()
    if not text or text.lower() in {"nan", "<na>", "none"}:
        return ""
    return f"EIQ_{domain.upper()}_" + sha_text(f"{text}.0")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def resolve_source(name: str, requested: Path, roots: list[Path], required: bool, expected_sha256: str | None = None) -> SourceResolution:
    requested = Path(requested)
    alternatives: list[str] = []
    resolved = requested if requested.is_file() else None
    if resolved is None:
        for root in roots:
            if not root.exists():
                continue
            alternatives.extend(str(p) for p in root.rglob(requested.name) if p.is_file())
        unique = sorted(set(alternatives))
        alternatives = unique[:25]
        if len(unique) == 1:
            resolved = Path(unique[0])
    if resolved is None:
        return SourceResolution(
            name,
            str(requested),
            "",
            "MISSING_SOURCE" if required else "MISSING_OPTIONAL_SOURCE",
            required,
            None,
            expected_sha256,
            alternatives,
        )
    actual = file_sha256(resolved)
    status = "PASS"
    if expected_sha256 and actual.lower() != expected_sha256.lower():
        status = "HASH_MISMATCH"
    elif resolved != requested:
        status = "RESOLVED_BY_UNIQUE_BASENAME"
    return SourceResolution(name, str(requested), str(resolved), status, required, actual, expected_sha256, alternatives)


def resolution_records(resolutions: list[SourceResolution]) -> list[dict]:
    return [
        {
            "name": r.name,
            "requested_path": r.requested_path,
            "resolved_path": r.resolved_path,
            "status": r.status,
            "required": r.required,
            "sha256": r.sha256,
            "expected_sha256": r.expected_sha256,
            "alternatives": r.alternatives,
        }
        for r in resolutions
    ]


def write_source_resolution_audit(output_dir: Path, resolutions: list[SourceResolution]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "EDGEIQ_STAGE011_SOURCE_RESOLUTION_AUDIT.json"
    payload = {
        "status": "PASS"
        if all((not r.required) or r.status in {"PASS", "RESOLVED_BY_UNIQUE_BASENAME"} for r in resolutions)
        else "FAIL",
        "sources": resolution_records(resolutions),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def require_admitted_sources(resolutions: list[SourceResolution]) -> None:
    bad = [
        r
        for r in resolutions
        if r.required and r.status not in {"PASS", "RESOLVED_BY_UNIQUE_BASENAME"}
    ]
    if bad:
        details = [
            {
                "name": r.name,
                "status": r.status,
                "requested_path": r.requested_path,
                "resolved_path": r.resolved_path,
                "alternatives": r.alternatives[:5],
            }
            for r in bad
        ]
        raise RuntimeError(f"Required source admission failed: {details}")


def resolved_path(resolutions: list[SourceResolution], name: str, fallback: Path) -> Path:
    for r in resolutions:
        if r.name == name:
            return Path(r.resolved_path) if r.resolved_path else fallback
    return fallback


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


def load_lab245b_warehouse_all(path: Path, target_date: str) -> pd.DataFrame:
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
    if not path.is_file():
        return pd.DataFrame(columns=need + ["dt"])
    rows = []
    target = pd.Timestamp(target_date)
    for chunk in pd.read_csv(path, usecols=need, dtype="string", chunksize=250000):
        chunk["canonical_horse_id"] = chunk["canonical_horse_id"].astype("string").str.strip()
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


def load_lab245b_warehouse(path: Path, target_date: str, canonical_ids: set[str]) -> pd.DataFrame:
    all_rows = load_lab245b_warehouse_all(path, target_date)
    wanted = {str(x).strip() for x in canonical_ids if str(x).strip()}
    return all_rows[all_rows["canonical_horse_id"].isin(wanted)].copy()


def load_perf026_history(
    path: Path, target_date: str, horse_ids: set[str], jockey_ids: set[str], trainer_ids: set[str]
) -> pd.DataFrame:
    need = [
        "canonical_race_id",
        "canonical_horse_id",
        "canonical_jockey_id",
        "canonical_trainer_id",
        "race_date",
        "finish_position",
        "epi_status_026",
    ]
    if not path.is_file():
        return pd.DataFrame(columns=need + ["dt"])
    target = pd.Timestamp(target_date)
    horse_ids = {str(x).strip() for x in horse_ids if str(x).strip()}
    jockey_ids = {str(x).strip() for x in jockey_ids if str(x).strip()}
    trainer_ids = {str(x).strip() for x in trainer_ids if str(x).strip()}
    rows = []
    for chunk in pd.read_csv(path, usecols=need, dtype="string", chunksize=300000):
        for col in ["canonical_horse_id", "canonical_jockey_id", "canonical_trainer_id"]:
            chunk[col] = chunk[col].astype("string").str.strip()
        mask = (
            chunk["canonical_horse_id"].isin(horse_ids)
            | chunk["canonical_jockey_id"].isin(jockey_ids)
            | chunk["canonical_trainer_id"].isin(trainer_ids)
        )
        chunk = chunk[mask].copy()
        if chunk.empty:
            continue
        chunk["dt"] = pd.to_datetime(chunk["race_date"], errors="coerce")
        chunk = chunk[chunk["dt"].notna() & chunk["dt"].lt(target)].copy()
        if chunk.empty:
            continue
        chunk["finish_position_num"] = pd.to_numeric(chunk["finish_position"], errors="coerce")
        rows.append(chunk)
    if not rows:
        return pd.DataFrame(columns=need + ["dt", "finish_position_num"])
    return pd.concat(rows, ignore_index=True)


def original_history_stats(values: list[float], n: int) -> tuple[float, float, float]:
    arr = np.asarray(values[-n:], dtype=float)
    if len(arr) == 0:
        return math.nan, math.nan, math.nan
    return float(np.mean(arr)), float(np.median(arr)), float(np.std(arr))


def finite_scalar(value: object) -> bool:
    return pd.notna(value) and bool(np.isfinite(float(value)))


def clean_finish_from_perf(perf: pd.DataFrame, canonical_horse_id: str) -> dict:
    rec = {
        "clean_finish_mean5": math.nan,
        "clean_last_finish": math.nan,
        "clean_last_won": math.nan,
        "clean_last_top3": math.nan,
        "clean_finish_hist_n": math.nan,
    }
    if not canonical_horse_id:
        return rec
    h = perf[perf["canonical_horse_id"].eq(canonical_horse_id)].copy()
    h = h[h["finish_position_num"].between(1, 99)].dropna(subset=["dt", "finish_position_num"])
    if h.empty:
        return rec
    h = (
        h.groupby(["canonical_horse_id", "dt"], as_index=False)
        .agg(finish_position_num=("finish_position_num", lambda s: s.iloc[0] if s.nunique() == 1 else np.nan))
        .dropna(subset=["finish_position_num"])
        .sort_values(["dt"], kind="stable")
    )
    q = h["finish_position_num"].tail(5).to_numpy(float)
    if len(q) == 0:
        return rec
    rec["clean_finish_mean5"] = float(q.mean())
    rec["clean_last_finish"] = float(q[-1])
    rec["clean_last_won"] = float(q[-1] == 1)
    rec["clean_last_top3"] = float(q[-1] <= 3)
    rec["clean_finish_hist_n"] = float(len(q))
    return rec


def personnel_lookup_from_perf(perf: pd.DataFrame, key_col: str) -> dict[str, tuple[float, float, float]]:
    h = perf[perf["epi_status_026"].eq("CALCULATED")].copy()
    h = h[h["finish_position_num"].notna()].dropna(subset=[key_col, "dt"])
    if h.empty:
        return {}
    h["win"] = h["finish_position_num"].eq(1).astype(int)
    h["top3"] = h["finish_position_num"].le(3).astype(int)
    d = (
        h.groupby([key_col, "dt"], as_index=False)
        .agg(starts=("win", "size"), wins=("win", "sum"), top3=("top3", "sum"))
        .sort_values([key_col, "dt"], kind="stable")
    )
    for col in ["starts", "wins", "top3"]:
        d[col] = d.groupby(key_col)[col].cumsum()
    d["prior_starts"] = d["starts"].astype(float)
    d["prior_win_rate"] = (d["wins"] + 1) / (d["starts"] + 10)
    d["prior_top3_rate"] = (d["top3"] + 3) / (d["starts"] + 10)
    out = {}
    for key, g in d.groupby(key_col, sort=False):
        r = g.sort_values("dt", kind="stable").iloc[-1]
        out[str(key)] = (float(r["prior_starts"]), float(r["prior_win_rate"]), float(r["prior_top3_rate"]))
    return out


def build_personnel_priors(field: pd.DataFrame, perf: pd.DataFrame) -> pd.DataFrame:
    jockey_lookup = personnel_lookup_from_perf(perf, "canonical_jockey_id")
    trainer_lookup = personnel_lookup_from_perf(perf, "canonical_trainer_id")
    rows = []
    for row in field.itertuples(index=False):
        jockey_id = rcom_current_id("JOCKEY", getattr(row, "jockey_code", ""))
        trainer_id = rcom_current_id("TRAINER", getattr(row, "trainer_code", ""))
        js = jockey_lookup.get(jockey_id, (math.nan, math.nan, math.nan))
        ts = trainer_lookup.get(trainer_id, (math.nan, math.nan, math.nan))
        rows.append(
            {
                "race_id": row.race_id,
                "runner_id": row.race_entry_id,
                "jockey_canonical_id": jockey_id,
                "trainer_canonical_id": trainer_id,
                "jockey_prior_status": "D45_FULL_HISTORY_PRIOR" if jockey_id and jockey_id in jockey_lookup else "D45_FULL_HISTORY_NO_PRIOR",
                "trainer_prior_status": "D45_FULL_HISTORY_PRIOR" if trainer_id and trainer_id in trainer_lookup else "D45_FULL_HISTORY_NO_PRIOR",
                "jockey_prior_starts": js[0],
                "jockey_prior_win_rate": js[1],
                "jockey_prior_top3_rate": js[2],
                "trainer_prior_starts": ts[0],
                "trainer_prior_win_rate": ts[1],
                "trainer_prior_top3_rate": ts[2],
            }
        )
    return pd.DataFrame(rows)


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


def match_prior_records(form_hist: pd.DataFrame, warehouse_hist: pd.DataFrame) -> tuple[list[dict], int]:
    if form_hist.empty or warehouse_hist.empty:
        return [], 0
    wh = warehouse_hist.copy()
    wh["date_key"] = pd.to_datetime(wh["dt"], errors="coerce").dt.date.astype("string")
    wh["distance_key"] = pd.to_numeric(wh["distance_metres"], errors="coerce").round().astype("Int64").astype("string")
    wh["finish_key"] = pd.to_numeric(wh["finish_position"], errors="coerce").round().astype("Int64").astype("string")
    wh["margin_key"] = pd.to_numeric(wh["finish_margin"], errors="coerce")
    used = set()
    matched = []
    ambiguous_candidates = 0
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
        if len(cand) > 1:
            ambiguous_candidates += int(len(cand) - 1)
        for idx in cand.index:
            race_id = str(cand.loc[idx, "canonical_race_id"])
            if idx not in used and race_id not in {x["canonical_race_id"] for x in matched}:
                used.add(idx)
                matched.append(
                    {
                        "form_race_date": r.race_date_dt.date().isoformat(),
                        "form_race_code": str(getattr(r, "race_code", "")),
                        "form_distance": float(r.distance_m),
                        "form_finish": float(r.finish_num),
                        "form_margin": float(r.margin_len) if pd.notna(r.margin_len) else math.nan,
                        "canonical_race_id": race_id,
                    }
                )
                break
    return matched, ambiguous_candidates


def prior_fact_key(date_value: object, distance: object, finish: object, margin: object) -> tuple[str, str, str, str] | None:
    dt = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(dt) or pd.isna(distance) or pd.isna(finish) or pd.isna(margin):
        return None
    return (
        dt.date().isoformat(),
        str(int(round(float(distance)))),
        str(int(round(float(finish)))),
        f"{round(float(margin), 2):.2f}",
    )


def enrich_missing_field_size_from_form(warehouse_hist: pd.DataFrame, form_hist: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    if warehouse_hist.empty or form_hist.empty:
        return warehouse_hist.copy(), []
    d = warehouse_hist.copy()
    form_rows: dict[tuple[str, str, str, str], list[dict]] = {}
    for r in form_hist.itertuples(index=False):
        key = prior_fact_key(r.race_date_dt, r.distance_m, r.finish_num, r.margin_len)
        if key is None or pd.isna(r.field_size_num):
            continue
        form_rows.setdefault(key, []).append(
            {
                "field_size": float(r.field_size_num),
                "form_race_code": str(getattr(r, "race_code", "")),
                "form_race_date": key[0],
            }
        )
    recovered = []
    for idx, r in d.iterrows():
        if pd.notna(r.get("field_size")):
            continue
        key = prior_fact_key(r.get("dt"), r.get("distance_metres"), r.get("finish_position"), r.get("finish_margin"))
        if key is None or key not in form_rows:
            continue
        values = form_rows[key]
        sizes = {v["field_size"] for v in values}
        race_codes = {v["form_race_code"] for v in values}
        if len(sizes) != 1 or len(race_codes) != 1:
            continue
        field_size = next(iter(sizes))
        d.at[idx, "field_size"] = field_size
        recovered.append(
            {
                "canonical_race_id": str(r.get("canonical_race_id")),
                "race_date": key[0],
                "distance_metres": key[1],
                "finish_position": key[2],
                "finish_margin": key[3],
                "field_size": field_size,
                "source": "RCOM_STRICT_PRIOR_FORM_EXACT_FACT_MATCH",
                "form_race_code": next(iter(race_codes)),
            }
        )
    return d, recovered


def count_matching_prior_records(form_hist: pd.DataFrame, warehouse_hist: pd.DataFrame) -> int:
    matched, _ = match_prior_records(form_hist, warehouse_hist)
    return len(matched)


def competing_identity_matches(form_hist: pd.DataFrame, warehouse_all: pd.DataFrame, canonical_horse_id: str) -> tuple[int, int, str]:
    if form_hist.empty or warehouse_all.empty:
        return 0, 0, ""
    wh = warehouse_all.copy()
    wh = wh[~wh["canonical_horse_id"].astype("string").eq(str(canonical_horse_id))]
    if wh.empty:
        return 0, 0, ""
    wh["date_key"] = pd.to_datetime(wh["dt"], errors="coerce").dt.date.astype("string")
    wh["distance_key"] = pd.to_numeric(wh["distance_metres"], errors="coerce").round().astype("Int64").astype("string")
    wh["finish_key"] = pd.to_numeric(wh["finish_position"], errors="coerce").round().astype("Int64").astype("string")
    wh["margin_key"] = pd.to_numeric(wh["finish_margin"], errors="coerce")
    hits: dict[str, set[str]] = {}
    for r in form_hist.itertuples(index=False):
        if pd.isna(r.race_date_dt) or pd.isna(r.distance_m) or pd.isna(r.finish_num):
            continue
        cand = wh[
            wh["date_key"].eq(r.race_date_dt.date().isoformat())
            & wh["distance_key"].eq(str(int(round(float(r.distance_m)))))
            & wh["finish_key"].eq(str(int(round(float(r.finish_num)))))
        ].copy()
        if cand.empty:
            continue
        if pd.notna(r.margin_len):
            cand = cand[(cand["margin_key"] - float(r.margin_len)).abs().le(0.25)]
        for c in cand.itertuples(index=False):
            hits.setdefault(str(c.canonical_horse_id), set()).add(str(c.canonical_race_id))
    if not hits:
        return 0, 0, ""
    counts = {k: len(v) for k, v in hits.items()}
    return len(counts), max(counts.values()), "|".join(sorted(k for k, v in counts.items() if v >= 2)[:20])


def build_identity_bridge(
    field: pd.DataFrame, form: pd.DataFrame, warehouse: pd.DataFrame, target_date: str, warehouse_all: pd.DataFrame | None = None
) -> pd.DataFrame:
    rows = []
    histories = {k: g.copy() for k, g in warehouse.groupby("canonical_horse_id", sort=False)}
    all_history = warehouse_all if warehouse_all is not None else warehouse
    live_eiq_counts = field["eiq_horse_id"].astype("string").str.strip().value_counts(dropna=False).to_dict()
    live_code_counts = field["horse_code"].astype("string").str.strip().value_counts(dropna=False).to_dict()
    for row in field.itertuples(index=False):
        canonical = str(getattr(row, "eiq_horse_id", "") or "").strip()
        horse_code = str(row.horse_code)
        expected_eiq = rcom_current_id("HORSE", horse_code)
        eiq_source_status = "SOURCE_GRAPHQL_HORSE_CODE_HASH_MATCH" if expected_eiq == canonical else "SOURCE_GRAPHQL_HORSE_CODE_HASH_MISMATCH"
        rform = form[form["horse_code"].astype("string").eq(horse_code)].copy()
        whist_raw = histories.get(canonical, pd.DataFrame(columns=warehouse.columns))
        whist, field_size_recovered = enrich_missing_field_size_from_form(whist_raw, rform)
        matches, ambiguous_candidates = match_prior_records(rform, whist)
        competing_count, competing_max_races, competing_ids = competing_identity_matches(rform, all_history, canonical)
        matched = len(matches)
        distinct_races = len({x["canonical_race_id"] for x in matches})
        duplicate_prior_races = int(whist.duplicated(["canonical_race_id", "canonical_horse_id"]).sum()) if len(whist) else 0
        status = "NOT_CERTIFIED"
        if eiq_source_status != "SOURCE_GRAPHQL_HORSE_CODE_HASH_MATCH":
            status = "FIELD_EIQ_PROVENANCE_FAIL"
        elif live_eiq_counts.get(canonical, 0) != 1 or live_code_counts.get(horse_code, 0) != 1:
            status = "LIVE_FIELD_IDENTITY_NOT_UNIQUE"
        elif not canonical or canonical.lower() in {"nan", "<na>", "none"}:
            status = "NO_EIQ_CANONICAL_ID"
        elif whist.empty:
            status = "NO_STRICT_PRIOR_LAB245B_HISTORY"
        elif duplicate_prior_races:
            status = "DUPLICATE_PRIOR_RACE_RECORDS"
        elif ambiguous_candidates:
            status = "AMBIGUOUS_PRIOR_RACE_MATCH"
        elif competing_max_races >= 2:
            status = "COMPETING_HISTORICAL_IDENTITY"
        elif distinct_races >= 2:
            status = "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
        elif matched == 1:
            status = "ONE_PRIOR_MATCH_INSUFFICIENT"
        else:
            status = "NO_PRIOR_FORM_MATCH"
        current_distance = float(getattr(row, "current_distance")) if pd.notna(getattr(row, "current_distance")) else math.nan
        feats = lab245b_features_from_history(whist, target_date, current_distance) if status == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH" else {}
        latest_recovery = ""
        if status == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH" and field_size_recovered and len(whist):
            latest = whist.sort_values(["dt", "canonical_race_id"], kind="stable").iloc[-1]
            latest_id = str(latest.get("canonical_race_id"))
            for item in field_size_recovered:
                if item["canonical_race_id"] == latest_id:
                    latest_recovery = json.dumps(item, separators=(",", ":"))
                    break
        if status != "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH":
            timing_status = "NO_CERTIFIED_IDENTITY"
            dist_timing_status = "NO_CERTIFIED_IDENTITY"
        elif len(whist) == 0:
            timing_status = "INSUFFICIENT_HISTORY"
            dist_timing_status = "INSUFFICIENT_HISTORY"
        else:
            timing_status = "DIRECT_LVS_AVAILABLE" if pd.notna(feats.get("lvs_last1")) else "HISTORY_WITH_MISSING_LVS"
            dist_timing_status = (
                "DISTANCE_NEAR_LVS_AVAILABLE" if pd.notna(feats.get("dist200_lvs_mean")) else "NO_DISTANCE_NEAR_LVS_HISTORY"
            )
        rows.append(
            {
                "race_id": row.race_id,
                "runner_id": row.race_entry_id,
                "horse_code": row.horse_code,
                "horse_name": row.horse_name,
                "canonical_horse_id": canonical,
                "expected_eiq_horse_id": expected_eiq,
                "eiq_source_status": eiq_source_status,
                "rcom_prior_records": int(len(rform)),
                "lab245b_prior_records": int(len(whist)),
                "matched_prior_records": int(matched),
                "matched_distinct_prior_races": int(distinct_races),
                "ambiguous_match_candidates": int(ambiguous_candidates),
                "competing_identity_count": int(competing_count),
                "competing_identity_max_distinct_races": int(competing_max_races),
                "competing_identity_ids": competing_ids,
                "duplicate_prior_race_records": int(duplicate_prior_races),
                "field_size_recovered_from_form_records": int(len(field_size_recovered)),
                "latest_prior_field_size_recovery": latest_recovery,
                "matched_prior_race_ids": "|".join(x["canonical_race_id"] for x in matches),
                "latest_lab245b_date": str(pd.to_datetime(whist["dt"]).max().date()) if len(whist) else "",
                "identity_bridge_status": status,
                "timing_status": timing_status,
                "distance_timing_status": dist_timing_status,
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

    return rec


def feature_reason(feature: str, value: object, has_form: bool, source: str = "") -> tuple[str, str]:
    if source == "LAB245B_CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH" and pd.notna(value):
        return "POPULATED_CERTIFIED_LAB245B_BRIDGE", "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
    if source == "LAB245B_CERTIFIED_NO_DISTANCE_NEAR_HISTORY" and feature in {"dist200_lvs_mean", "dist200_lvs_best"}:
        return "CERTIFIED_MISSING_ALLOWED", "CERTIFIED_IDENTITY_NO_DISTANCE_NEAR_LVS_HISTORY"
    if feature in LVS_FEATURES:
        return "MISSING", "NO_CERTIFIED_LIVE_LVS_TIMING_IDENTITY"
    if feature in PERSONNEL_FEATURES:
        if source == "PERF026_FULL_HISTORY_PERSONNEL" and pd.notna(value):
            return "POPULATED_CERTIFIED_PERSONNEL", "PERF026_D45_FULL_HISTORY_PRIOR"
        if source == "PERF026_FULL_HISTORY_PERSONNEL_NO_PRIOR":
            return "CERTIFIED_MISSING_ALLOWED", "PERF026_D45_FULL_HISTORY_NO_PRIOR"
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
    warehouse_all = load_lab245b_warehouse_all(paths.lab245b_warehouse, target_date)
    warehouse = warehouse_all[warehouse_all["canonical_horse_id"].isin(canonical_ids)].copy()
    identity_bridge = build_identity_bridge(field, form, warehouse, target_date, warehouse_all)
    perf = load_perf026_history(
        paths.perf026, target_date,
        set(field["eiq_horse_id"].dropna().astype(str)),
        {rcom_current_id("JOCKEY", x) for x in field["jockey_code"].dropna()},
        {rcom_current_id("TRAINER", x) for x in field["trainer_code"].dropna()},
    )
    personnel = build_personnel_priors(field, perf)
    personnel_by_runner = personnel.set_index(["race_id", "runner_id"]).to_dict("index")
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
        personnel_row = personnel_by_runner.get((row["race_id"], row["race_entry_id"]), {})
        feature_sources = {feature: "RCOM_NATIVE_STRICT_PRIOR_FORM_OR_FIELD" for feature in RCOM_NATIVE_CERTIFIED_FEATURES}
        feature_sources.update({feature: "RCOM_NATIVE_PARTIAL_PERSONNEL_HISTORY" for feature in PERSONNEL_FEATURES})
        for feature in PERSONNEL_FEATURES:
            group = "jockey" if feature.startswith("jockey_") else "trainer"
            status_key = group + "_prior_status"
            if personnel_row.get(status_key) == "D45_FULL_HISTORY_PRIOR" and pd.notna(personnel_row.get(feature)):
                features[feature] = personnel_row[feature]
                feature_sources[feature] = "PERF026_FULL_HISTORY_PERSONNEL"
            elif personnel_row.get(status_key) == "D45_FULL_HISTORY_NO_PRIOR":
                feature_sources[feature] = "PERF026_FULL_HISTORY_PERSONNEL_NO_PRIOR"
        feature_sources.update({feature: "" for feature in LVS_FEATURES})
        bridge_key = (row["race_id"], row["race_entry_id"])
        bridge_row = bridge_features.get(bridge_key, {})
        if bridge_row.get("identity_bridge_status") == "CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH":
            for feature in LAB245B_HISTORY_FEATURES:
                if feature in bridge_row and pd.notna(bridge_row[feature]):
                    features[feature] = bridge_row[feature]
                    feature_sources[feature] = "LAB245B_CERTIFIED_EXACT_ID_MULTI_PRIOR_MATCH"
                elif feature in {"dist200_lvs_mean", "dist200_lvs_best"} and bridge_row.get("distance_timing_status") == "NO_DISTANCE_NEAR_LVS_HISTORY":
                    feature_sources[feature] = "LAB245B_CERTIFIED_NO_DISTANCE_NEAR_HISTORY"
        candidate_key = (target_date, race_no, horse_name.strip().upper())
        has_candidate = candidate_key in candidate_keys
        has_form = len(hist) > 0
        reason_codes = []
        populated = 0
        certified_populated = 0
        uncertified_populated = 0
        certified_missing = 0
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
                if status in {"POPULATED_CERTIFIED_RCOM_NATIVE", "POPULATED_CERTIFIED_LAB245B_BRIDGE", "POPULATED_CERTIFIED_PERSONNEL"}:
                    certified_populated += 1
                elif status == "POPULATED_UNCERTIFIED":
                    uncertified_populated += 1
            elif status == "CERTIFIED_MISSING_ALLOWED":
                certified_missing += 1
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
        certified_complete = (certified_populated + certified_missing) == len(FEATURES)
        eligible = bool(certified_complete and not row["is_scratched"])
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
                "jockey_canonical_id": personnel_row.get("jockey_canonical_id"),
                "trainer_canonical_id": personnel_row.get("trainer_canonical_id"),
                "jockey_prior_status": personnel_row.get("jockey_prior_status"),
                "trainer_prior_status": personnel_row.get("trainer_prior_status"),
                "historical_identity_status": history_status,
                "feature_status": "ELIGIBLE_FOR_SCORING" if eligible else "INCOMPLETE_OR_UNCERTIFIED_DO_NOT_SCORE",
                "eligible_for_stage011_scoring": eligible,
                "populated_feature_count": populated,
                "certified_populated_feature_count": certified_populated,
                "certified_missing_feature_count": certified_missing,
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
        "PERSONNEL_FULL_HISTORY": sorted(PERSONNEL_FEATURES),
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
        "feature_certification_status_counts": feature_status["feature_status"].value_counts().to_dict(),
        "jockey_prior_status_counts": matrix["jockey_prior_status"].value_counts(dropna=False).to_dict(),
        "trainer_prior_status_counts": matrix["trainer_prior_status"].value_counts(dropna=False).to_dict(),
        "timing_status_counts": identity_bridge["timing_status"].value_counts(dropna=False).to_dict(),
        "distance_timing_status_counts": identity_bridge["distance_timing_status"].value_counts(dropna=False).to_dict(),
        "feature_manifest": FEATURES,
        "feature_manifest_sha256": hashlib.sha256(json.dumps(FEATURES, separators=(",", ":")).encode()).hexdigest(),
        "stage011_semantics": {
            "margin_winner_handling": "PRESERVE_SOURCE_FINISH_MARGIN_NO_WINNER_ZEROING",
            "lab245b_history_aggregate_policy": "FINITE_VALUES_THEN_LAST_N_FOR_LVS_MARGIN_FINISH_AGGREGATES",
            "margin_per_runner_policy": "MOST_RECENT_RAW_PRIOR_STARTS_REQUIRE_MARGIN_AND_FIELD_SIZE",
            "personnel_prior_policy": "(wins+1)/(starts+10) and (top3+3)/(starts+10) from strict-prior PERF026 records, matching the frozen D45 source/formula contract",
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
            "perf026": str(paths.perf026),
            "perf026_sha256": file_sha256(paths.perf026) if paths.perf026.is_file() else None,
        },
        "no_market_features": True,
        "no_current_race_outcomes": True,
        "no_stage011_retraining": True,
        "model_ready_for_prospective_scoring": bool(matrix["eligible_for_stage011_scoring"].sum() > 0),
        "primary_blockers": [
            "Only runners with exact EIQ identity plus at least two matching strict-prior Racing.com/LAB245B records are certified for LAB245B timing features.",
            "Seven certified identities have no distance-near LVS history; these are retained as certified missing values rather than fabricated timing substitutes.",
            "One active certified identity remains blocked by an uncertified missing margin_per_runner_last1 value.",
        ],
    }
    return matrix, coverage, feature_status, identity_bridge, audit


def build_runner_blockers(matrix: pd.DataFrame, feature_status: pd.DataFrame) -> pd.DataFrame:
    blocked = feature_status[
        feature_status["feature_status"].isin(["MISSING", "POPULATED_UNCERTIFIED"])
    ].copy()
    rows = []
    for (race_id, runner_id), g in blocked.groupby(["race_id", "runner_id"], sort=False):
        meta = matrix[(matrix["race_id"].eq(race_id)) & (matrix["runner_id"].eq(runner_id))].iloc[0]
        rows.append(
            {
                "race_no": meta["race_no"],
                "horse_name": meta["horse_name"],
                "race_id": race_id,
                "runner_id": runner_id,
                "historical_identity_status": meta["historical_identity_status"],
                "identity_bridge_status": meta["identity_bridge_status"],
                "jockey_prior_status": meta.get("jockey_prior_status"),
                "trainer_prior_status": meta.get("trainer_prior_status"),
                "blocking_feature_count": int(len(g)),
                "blocking_features": "|".join(g["feature"].astype(str)),
                "blocking_reasons": "|".join((g["feature"].astype(str) + ":" + g["reason_code"].astype(str)).tolist()),
            }
        )
    return pd.DataFrame(rows)


def build_runner_certification_report(
    matrix: pd.DataFrame, identity_bridge: pd.DataFrame, feature_status: pd.DataFrame
) -> pd.DataFrame:
    blocked = build_runner_blockers(matrix, feature_status)
    blocker_lookup = blocked.set_index(["race_id", "runner_id"]).to_dict("index") if not blocked.empty else {}
    bridge_lookup = identity_bridge.set_index(["race_id", "runner_id"]).to_dict("index")
    rows = []
    for row in matrix.sort_values(["race_no", "horse_name"], kind="stable").itertuples(index=False):
        key = (row.race_id, row.runner_id)
        bridge = bridge_lookup.get(key, {})
        blocker = blocker_lookup.get(key, {})
        if bool(row.eligible_for_stage011_scoring):
            decision = "FEATURE_PROVENANCE_ELIGIBLE_RESEARCH_ONLY"
        elif bool(row.scratched):
            decision = "WITHHELD_SCRATCHED"
        elif blocker:
            decision = "WITHHELD_FEATURE_OR_PROVENANCE_BLOCKER"
        else:
            decision = "WITHHELD_UNRESOLVED"
        rows.append(
            {
                "race_no": row.race_no,
                "horse_name": row.horse_name,
                "race_id": row.race_id,
                "runner_id": row.runner_id,
                "horse_code": row.horse_code,
                "canonical_horse_id": row.canonical_horse_id,
                "scratched": bool(row.scratched),
                "certification_decision": decision,
                "eligible_for_stage011_scoring": bool(row.eligible_for_stage011_scoring),
                "identity_bridge_status": row.identity_bridge_status,
                "eiq_source_status": bridge.get("eiq_source_status", ""),
                "matched_distinct_prior_races": bridge.get("matched_distinct_prior_races", ""),
                "matched_prior_race_ids": bridge.get("matched_prior_race_ids", ""),
                "lab245b_prior_records": row.lab245b_prior_records,
                "timing_status": bridge.get("timing_status", ""),
                "distance_timing_status": bridge.get("distance_timing_status", ""),
                "field_size_recovered_from_form_records": bridge.get("field_size_recovered_from_form_records", 0),
                "latest_prior_field_size_recovery": bridge.get("latest_prior_field_size_recovery", ""),
                "jockey_prior_status": row.jockey_prior_status,
                "trainer_prior_status": row.trainer_prior_status,
                "populated_feature_count": row.populated_feature_count,
                "certified_populated_feature_count": row.certified_populated_feature_count,
                "certified_missing_feature_count": row.certified_missing_feature_count,
                "uncertified_populated_feature_count": row.uncertified_populated_feature_count,
                "missing_feature_count": row.missing_feature_count,
                "blocking_feature_count": blocker.get("blocking_feature_count", 0),
                "blocking_features": blocker.get("blocking_features", ""),
                "blocking_reasons": blocker.get("blocking_reasons", ""),
            }
        )
    return pd.DataFrame(rows)


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
        "blockers": output_dir / "STAGE011_RUNNER_FEATURE_BLOCKERS.csv",
        "runner_certification": output_dir / "EDGEIQ_STAGE011_RUNNER_CERTIFICATION_REPORT.csv",
        "audit": output_dir / "EDGEIQ_STAGE011_LIVE_FEATURE_AUDIT.json",
        "score_input": output_dir / "EDGEIQ_STAGE011_LIVE_SCORE_ELIGIBLE_INPUT.csv",
    }
    matrix.to_csv(paths["matrix"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    feature_status.to_csv(paths["feature_status"], index=False)
    identity_bridge.to_csv(paths["identity_bridge"], index=False)
    build_runner_blockers(matrix, feature_status).to_csv(paths["blockers"], index=False)
    build_runner_certification_report(matrix, identity_bridge, feature_status).to_csv(paths["runner_certification"], index=False)
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


def resolve_runtime_sources(args: argparse.Namespace) -> tuple[Paths, list[SourceResolution]]:
    roots = [Path(p) for p in args.source_search_root]
    resolutions = [
        resolve_source("field", args.field, roots, required=True),
        resolve_source("form", args.form, roots, required=True),
        resolve_source("public_snapshot", args.public_snapshot, roots, required=True),
        resolve_source("lab245b_candidates", args.lab245b_candidates, roots, required=False),
        resolve_source(
            "lab245b_warehouse",
            args.lab245b_warehouse,
            roots,
            required=True,
            expected_sha256=LAB245B_WAREHOUSE_EXPECTED_SHA256,
        ),
        resolve_source("perf026", args.perf026, roots, required=True),
    ]
    write_source_resolution_audit(args.output_dir, resolutions)
    require_admitted_sources(resolutions)
    paths = Paths(
        resolved_path(resolutions, "field", args.field),
        resolved_path(resolutions, "form", args.form),
        resolved_path(resolutions, "public_snapshot", args.public_snapshot),
        resolved_path(resolutions, "lab245b_candidates", args.lab245b_candidates),
        resolved_path(resolutions, "lab245b_warehouse", args.lab245b_warehouse),
        resolved_path(resolutions, "perf026", args.perf026),
        args.output_dir,
    )
    return paths, resolutions


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
        "--perf026", type=Path,
        default=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_026\edgeiq_certified_flat_walk_forward_epi_026.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/research/stage011_live_completion"),
    )
    parser.add_argument(
        "--source-search-root",
        type=Path,
        action="append",
        default=[
            Path(r"C:\EDGEIQ_ISSUE23"),
            Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),
            Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"),
        ],
        help="Root searched by basename if a configured source path is absent.",
    )
    args = parser.parse_args()
    paths, source_resolutions = resolve_runtime_sources(args)
    matrix, coverage, feature_status, identity_bridge, audit = build_matrix(
        paths, args.target_date, args.venue, args.expected_runners
    )
    audit["source_resolution_status"] = "PASS"
    audit["source_resolution"] = resolution_records(source_resolutions)
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
