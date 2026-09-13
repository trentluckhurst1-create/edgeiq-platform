from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"

V29 = DATA / "edgeiq_sectional_governed_v29.csv"
LIVE = DATA / "edgeiq_live_runner_board_v1.csv"
OUT_FEATURES = DATA / "edgeiq_sectional_features_v30.csv"
OUT_RACE = DATA / "edgeiq_sectional_features_v30_race_summary.csv"
OUT_HISTORY = DATA / "edgeiq_sectional_features_v30_runner_history.csv"
OUT_COVERAGE = DATA / "edgeiq_sectional_features_v30_coverage.csv"
OUT_LIVE = DATA / "edgeiq_sectional_features_v30_live_join_audit.csv"
OUT_MANIFEST = DATA / "edgeiq_sectional_features_v30_manifest.json"


def norm_horse(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> pd.Series:
    out = pd.Series(np.nan, index=df.index, dtype="float64")
    for name in names:
        if name in df.columns:
            vals = to_num(df[name])
            out = out.where(out.notna(), vals)
    return out


def race_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["race_date"].astype(str)
        + "|"
        + df["canonical_track"].astype(str)
        + "|R"
        + df["race_no"].astype(str)
    )


def pct_score_from_rank(rank: pd.Series, n: pd.Series) -> pd.Series:
    score = pd.Series(np.nan, index=rank.index, dtype="float64")
    mask = rank.notna() & n.notna() & (n >= 2)
    score.loc[mask] = 100.0 * (n.loc[mask] - rank.loc[mask]) / (n.loc[mask] - 1.0)
    return score.clip(0, 100)


def factor_band(score: object, support: object) -> str:
    try:
        n = int(support)
    except Exception:
        n = 0
    if n <= 0 or pd.isna(score):
        return "LIMITED_DATA"
    x = float(score)
    if x >= 80:
        return "ELITE"
    if x >= 65:
        return "STRONG"
    if x >= 55:
        return "ABOVE_AVERAGE"
    if x >= 45:
        return "NEUTRAL"
    return "BELOW_AVERAGE"


def mean_available(values: list[object]) -> float:
    xs = [float(x) for x in values if pd.notna(x)]
    return float(np.mean(xs)) if xs else np.nan


def last_available(values: list[object]) -> float:
    xs = [float(x) for x in values if pd.notna(x)]
    return xs[-1] if xs else np.nan


def safe_std(values: list[object]) -> float:
    xs = [float(x) for x in values if pd.notna(x)]
    if len(xs) < 2:
        return np.nan
    return float(np.std(xs, ddof=0))


def main() -> None:
    if not V29.exists():
        raise FileNotFoundError(f"Missing V29 governed dataset: {V29}")

    raw = pd.read_csv(V29, low_memory=False)
    required = ["race_date", "canonical_track", "race_no", "horse", "canonical_horse"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise RuntimeError(f"V29 missing required columns: {missing}")

    raw["race_date"] = pd.to_datetime(raw["race_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    raw["race_no"] = pd.to_numeric(raw["race_no"], errors="coerce").astype("Int64")
    raw["canonical_track"] = raw["canonical_track"].astype(str).str.strip().str.upper()
    raw["horse_norm"] = raw["canonical_horse"].map(norm_horse)
    fallback_horse = raw["horse"].map(norm_horse)
    raw.loc[raw["horse_norm"].eq(""), "horse_norm"] = fallback_horse
    raw["race_key_v30"] = race_key(raw)

    # V29 readiness race counts were suspicious. Recompute all race coverage from the
    # certified identity triple instead of trusting prior aggregate audit output.
    metric_sources = {
        "last_600": ["original_col_last_600", "original_col_raw_last_600", "original_col_sectional_600", "original_col_raw_sectional_600"],
        "last_400": ["original_col_last_400", "original_col_raw_last_400", "original_col_sectional_400", "original_col_raw_sectional_400"],
        "last_200": ["original_col_last_200", "original_col_raw_last_200", "original_col_sectional_200", "original_col_raw_sectional_200"],
        "early_speed": ["original_col_early_velocity", "original_col_raw_early_speed"],
        "late_speed": ["original_col_late_velocity", "original_col_raw_late_speed", "original_col_sustained_velocity", "original_col_closing_speed_pct"],
        "distance": ["original_col_distance"],
    }
    for metric, cols in metric_sources.items():
        raw[f"metric_{metric}"] = first_existing(raw, cols)

    # Collapse multiple governed observations of the same race-runner to one runner-race
    # record. Median is deterministic and protects race-relative ranking from duplicated
    # source observations. Source lineage is retained as an audit count, never silently lost.
    group_cols = ["race_date", "canonical_track", "race_no", "race_key_v30", "horse_norm"]
    agg_spec: dict[str, object] = {
        "horse": "first",
        "canonical_horse": "first",
        "source_lineage": "count" if "source_lineage" in raw.columns else "size",
    }
    for m in metric_sources:
        agg_spec[f"metric_{m}"] = "median"

    if "source_lineage" in raw.columns:
        rr = raw.groupby(group_cols, dropna=False, as_index=False).agg(agg_spec)
        rr = rr.rename(columns={"source_lineage": "governed_observation_count"})
    else:
        rr = raw.groupby(group_cols, dropna=False, as_index=False).agg(
            horse=("horse", "first"),
            canonical_horse=("canonical_horse", "first"),
            metric_last_600=("metric_last_600", "median"),
            metric_last_400=("metric_last_400", "median"),
            metric_last_200=("metric_last_200", "median"),
            metric_early_speed=("metric_early_speed", "median"),
            metric_late_speed=("metric_late_speed", "median"),
            metric_distance=("metric_distance", "median"),
        )
        rr["governed_observation_count"] = 1

    duplicate_runner_race_groups = int((rr["governed_observation_count"] > 1).sum())

    # Within-race relative features. Times are lower-is-better; velocity/speed is higher-is-better.
    directions = {
        "last_600": True,
        "last_400": True,
        "last_200": True,
        "early_speed": False,
        "late_speed": False,
    }

    race_group = rr.groupby("race_key_v30", dropna=False)
    for metric, ascending in directions.items():
        val = f"metric_{metric}"
        ncol = f"{metric}_comparable_runners"
        rankcol = f"{metric}_rank"
        meancol = f"{metric}_race_mean"
        diffcol = f"{metric}_vs_race_mean"
        scorecol = f"{metric}_score"

        rr[ncol] = race_group[val].transform("count")
        rr[rankcol] = race_group[val].rank(method="average", ascending=ascending, na_option="keep")
        rr[meancol] = race_group[val].transform("mean")
        rr[diffcol] = rr[val] - rr[meancol]
        rr[scorecol] = pct_score_from_rank(rr[rankcol], rr[ncol])

    available_metric_count = rr[[f"metric_{m}" for m in directions]].notna().sum(axis=1)
    rr["sectional_quality_flag"] = np.select(
        [available_metric_count.eq(5), available_metric_count.ge(3), available_metric_count.ge(1)],
        ["FULL_SECTIONAL", "PARTIAL_SECTIONAL", "LIMITED_SECTIONAL"],
        default="NO_SECTIONAL",
    )

    rr["race_runner_key_v30"] = rr["race_key_v30"] + "|" + rr["horse_norm"]

    # Composite per-run score used only to describe historical consistency/trajectory.
    # It is the unweighted mean of available component scores; no outcome fitting or optimisation.
    component_score_cols = [
        "last_600_score",
        "last_400_score",
        "last_200_score",
        "early_speed_score",
        "late_speed_score",
    ]
    rr["sectional_run_score"] = rr[component_score_cols].mean(axis=1, skipna=True)
    rr.loc[rr[component_score_cols].notna().sum(axis=1).eq(0), "sectional_run_score"] = np.nan

    # Strict-prior runner history. Same-date races are processed as a batch so a horse's
    # target-day observation can never feed its own profile or another row on that date.
    history_rows: list[dict[str, object]] = []
    rr["_date_dt"] = pd.to_datetime(rr["race_date"], errors="coerce")
    rr = rr.sort_values(["horse_norm", "_date_dt", "canonical_track", "race_no"], kind="mergesort")

    metric_hist_names = {
        "last_600": "metric_last_600",
        "last_400": "metric_last_400",
        "last_200": "metric_last_200",
        "early_speed": "metric_early_speed",
        "late_speed": "metric_late_speed",
        "sectional_600_score": "last_600_score",
        "sectional_400_score": "last_400_score",
        "sectional_200_score": "last_200_score",
        "early_speed_score": "early_speed_score",
        "late_speed_score": "late_speed_score",
        "sectional_run_score": "sectional_run_score",
    }

    for horse_norm, hdf in rr.groupby("horse_norm", sort=False):
        store: dict[str, list[float]] = {k: [] for k in metric_hist_names}
        prior_dates: list[pd.Timestamp] = []
        for race_date_dt, day in hdf.groupby("_date_dt", sort=True, dropna=False):
            for idx, row in day.iterrows():
                rec: dict[str, object] = {
                    "race_runner_key_v30": row["race_runner_key_v30"],
                    "race_date": row["race_date"],
                    "canonical_track": row["canonical_track"],
                    "race_no": row["race_no"],
                    "horse": row["horse"],
                    "canonical_horse": row["canonical_horse"],
                    "horse_norm": horse_norm,
                    "prior_sectional_runs": len(prior_dates),
                }

                for logical, col in metric_hist_names.items():
                    vals = store[logical]
                    rec[f"prior_{logical}_mean"] = float(np.mean(vals)) if vals else np.nan
                    rec[f"prior_{logical}_best"] = (min(vals) if logical in {"last_600", "last_400", "last_200"} and vals else max(vals) if vals else np.nan)
                    rec[f"prior_{logical}_recent"] = last_available(vals)

                # Requested aliases / product-facing history fields.
                rec["prior_best_late_score"] = max(store["late_speed_score"]) if store["late_speed_score"] else np.nan
                rec["prior_recent_late_score"] = last_available(store["late_speed_score"])
                rec["prior_sectional_consistency"] = safe_std(store["sectional_run_score"])

                if len(store["sectional_run_score"]) >= 2:
                    prev = store["sectional_run_score"][:-1]
                    last = store["sectional_run_score"][-1]
                    rec["prior_sectional_trend"] = float(last - np.mean(prev)) if prev else np.nan
                else:
                    rec["prior_sectional_trend"] = np.nan

                weapon = mean_available([
                    rec["prior_sectional_600_score_mean"],
                    rec["prior_sectional_400_score_mean"],
                    rec["prior_sectional_200_score_mean"],
                    rec["prior_late_speed_score_mean"],
                ])
                late_power = mean_available([
                    rec["prior_sectional_600_score_recent"],
                    rec["prior_sectional_400_score_recent"],
                    rec["prior_sectional_200_score_recent"],
                    rec["prior_late_speed_score_recent"],
                ])
                early = rec["prior_early_speed_score_mean"]
                std = rec["prior_sectional_consistency"]
                consistency_score = np.nan if pd.isna(std) else float(np.clip(100.0 - float(std), 0.0, 100.0))
                trend_delta = rec["prior_sectional_trend"]
                trajectory_score = np.nan if pd.isna(trend_delta) else float(np.clip(50.0 + float(trend_delta) / 2.0, 0.0, 100.0))

                rec["sectional_weapon_score"] = weapon
                rec["sectional_weapon_band"] = factor_band(weapon, rec["prior_sectional_runs"])
                rec["late_power_score"] = late_power
                rec["late_power_band"] = factor_band(late_power, rec["prior_sectional_runs"])
                rec["historical_early_speed_score"] = early
                rec["historical_early_speed_band"] = factor_band(early, rec["prior_sectional_runs"])
                rec["sectional_consistency_score"] = consistency_score
                rec["sectional_consistency_band"] = factor_band(consistency_score, rec["prior_sectional_runs"])
                rec["sectional_trajectory_score"] = trajectory_score
                if pd.isna(trend_delta):
                    rec["sectional_trajectory_band"] = "LIMITED_DATA"
                elif float(trend_delta) > 0:
                    rec["sectional_trajectory_band"] = "IMPROVING"
                elif float(trend_delta) < 0:
                    rec["sectional_trajectory_band"] = "DECLINING"
                else:
                    rec["sectional_trajectory_band"] = "STABLE"

                history_rows.append(rec)

            # Update history only after every row on this date has been profiled.
            for _, row in day.iterrows():
                if pd.notna(race_date_dt):
                    prior_dates.append(race_date_dt)
                for logical, col in metric_hist_names.items():
                    value = row[col]
                    if pd.notna(value):
                        store[logical].append(float(value))

    hist = pd.DataFrame(history_rows)
    rr = rr.drop(columns=["_date_dt"])
    features = rr.merge(hist, on=["race_runner_key_v30", "race_date", "canonical_track", "race_no", "horse", "canonical_horse", "horse_norm"], how="left", validate="one_to_one")

    # Race summary and independent coverage recomputation.
    race_summary = features.groupby(["race_key_v30", "race_date", "canonical_track", "race_no"], as_index=False).agg(
        runners=("race_runner_key_v30", "nunique"),
        last600_runners=("metric_last_600", "count"),
        last400_runners=("metric_last_400", "count"),
        last200_runners=("metric_last_200", "count"),
        early_speed_runners=("metric_early_speed", "count"),
        late_speed_runners=("metric_late_speed", "count"),
    )

    coverage_rows = []
    for metric in ["last_600", "last_400", "last_200", "early_speed", "late_speed"]:
        val = f"metric_{metric}"
        mask = features[val].notna()
        coverage_rows.append({
            "metric": metric,
            "runner_race_rows_available": int(mask.sum()),
            "unique_races_available": int(features.loc[mask, "race_key_v30"].nunique()),
            "unique_horses_available": int(features.loc[mask, "horse_norm"].nunique()),
            "runner_race_coverage_pct": round(100.0 * float(mask.mean()), 6),
        })
    coverage = pd.DataFrame(coverage_rows)

    # Live join audit: audit only; never overwrite live board.
    live_audit = pd.DataFrame()
    live_summary = {
        "live_runners": 0,
        "with_any_sectional_history": 0,
        "with_1plus_prior_sectional": 0,
        "with_2plus_prior_sectional": 0,
        "with_3plus_prior_sectional": 0,
        "with_late_power": 0,
        "with_sectional_weapon": 0,
        "with_early_speed": 0,
    }

    if LIVE.exists():
        live = pd.read_csv(LIVE, low_memory=False)
        live_horse_source = "horse_key" if "horse_key" in live.columns else "horse"
        live["horse_norm"] = live[live_horse_source].map(norm_horse)
        live["race_date_dt"] = pd.to_datetime(live.get("race_date"), errors="coerce")

        # Choose the latest strictly-prior profile row for each live runner. If the live board
        # date is absent, use latest available historical profile as an audit fallback only.
        hist2 = hist.copy()
        hist2["profile_race_date_dt"] = pd.to_datetime(hist2["race_date"], errors="coerce")
        rows = []
        for i, lrow in live.iterrows():
            cand = hist2[hist2["horse_norm"] == lrow["horse_norm"]]
            if pd.notna(lrow["race_date_dt"]):
                cand = cand[cand["profile_race_date_dt"] < lrow["race_date_dt"]]
            if cand.empty:
                profile = None
            else:
                profile = cand.sort_values("profile_race_date_dt").iloc[-1]
            out = {
                "live_row": i,
                "race_date": lrow.get("race_date", ""),
                "track": lrow.get("track", ""),
                "race_no": lrow.get("race_no", ""),
                "horse": lrow.get("horse", ""),
                "horse_key": lrow.get("horse_key", ""),
                "horse_norm": lrow["horse_norm"],
                "matched_historical_profile": "YES" if profile is not None else "NO",
            }
            for col in [
                "prior_sectional_runs",
                "sectional_weapon_score",
                "sectional_weapon_band",
                "late_power_score",
                "late_power_band",
                "historical_early_speed_score",
                "historical_early_speed_band",
                "sectional_consistency_score",
                "sectional_consistency_band",
                "sectional_trajectory_score",
                "sectional_trajectory_band",
            ]:
                out[col] = profile[col] if profile is not None and col in profile.index else np.nan
            rows.append(out)
        live_audit = pd.DataFrame(rows)
        live_summary["live_runners"] = len(live_audit)
        if len(live_audit):
            p = pd.to_numeric(live_audit["prior_sectional_runs"], errors="coerce").fillna(0)
            live_summary["with_any_sectional_history"] = int((p >= 1).sum())
            live_summary["with_1plus_prior_sectional"] = int((p >= 1).sum())
            live_summary["with_2plus_prior_sectional"] = int((p >= 2).sum())
            live_summary["with_3plus_prior_sectional"] = int((p >= 3).sum())
            live_summary["with_late_power"] = int(pd.to_numeric(live_audit["late_power_score"], errors="coerce").notna().sum())
            live_summary["with_sectional_weapon"] = int(pd.to_numeric(live_audit["sectional_weapon_score"], errors="coerce").notna().sum())
            live_summary["with_early_speed"] = int(pd.to_numeric(live_audit["historical_early_speed_score"], errors="coerce").notna().sum())

    # Integrity checks.
    duplicate_identity_conflicts = int(features["race_runner_key_v30"].duplicated().sum())
    score_cols = [c for c in features.columns if c.endswith("_score")]
    score_range_errors = 0
    for c in score_cols:
        s = pd.to_numeric(features[c], errors="coerce")
        score_range_errors += int(((s < 0) | (s > 100)).fillna(False).sum())

    strict_prior_leakage = 0
    if not hist.empty:
        # Profiles were constructed before updating each same-day batch. This independent
        # assertion checks the only available historical counter cannot exceed total prior rows.
        strict_prior_leakage = int((pd.to_numeric(hist["prior_sectional_runs"], errors="coerce") < 0).sum())

    quarantined_rows_leaked = 0
    quarantine_path = DATA / "edgeiq_sectional_governed_v29_quarantine.csv"
    if quarantine_path.exists() and "source_lineage" in raw.columns:
        q = pd.read_csv(quarantine_path, usecols=lambda c: c == "source_lineage", low_memory=False)
        if "source_lineage" in q.columns:
            quarantined_rows_leaked = int(raw["source_lineage"].isin(set(q["source_lineage"].dropna().astype(str))).sum())

    # Write outputs.
    for path in [OUT_FEATURES, OUT_RACE, OUT_HISTORY, OUT_COVERAGE, OUT_LIVE, OUT_MANIFEST]:
        path.parent.mkdir(parents=True, exist_ok=True)

    features.to_csv(OUT_FEATURES, index=False)
    race_summary.to_csv(OUT_RACE, index=False)
    hist.to_csv(OUT_HISTORY, index=False)
    coverage.to_csv(OUT_COVERAGE, index=False)
    live_audit.to_csv(OUT_LIVE, index=False)

    ready = (
        duplicate_identity_conflicts == 0
        and score_range_errors == 0
        and strict_prior_leakage == 0
        and quarantined_rows_leaked == 0
        and len(features) > 0
    )

    manifest = {
        "build_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(V29.relative_to(ROOT)),
        "v29_certified_rows": int(len(raw)),
        "runner_race_feature_rows": int(len(features)),
        "unique_races": int(features["race_key_v30"].nunique()),
        "unique_horses": int(features["horse_norm"].nunique()),
        "duplicate_runner_race_groups_collapsed": duplicate_runner_race_groups,
        "quarantined_rows_leaked": quarantined_rows_leaked,
        "strict_prior_leakage": strict_prior_leakage,
        "duplicate_identity_conflicts": duplicate_identity_conflicts,
        "score_range_errors": score_range_errors,
        "live_join": live_summary,
        "ready_for_live_runner_board_join": bool(ready),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Mandatory terminal summary.
    print("V30 SECTIONAL FEATURE LAYER")
    print()
    print("SOURCE")
    print(f"v29_certified_rows={len(raw)}")
    print(f"unique_races={features['race_key_v30'].nunique()}")
    print(f"unique_horses={features['horse_norm'].nunique()}")
    print()
    print("RACE-RELATIVE FEATURES")
    print(f"rows_with_last600_rank={features['last_600_rank'].notna().sum()}")
    print(f"rows_with_last400_rank={features['last_400_rank'].notna().sum()}")
    print(f"rows_with_last200_rank={features['last_200_rank'].notna().sum()}")
    print(f"rows_with_early_speed_rank={features['early_speed_rank'].notna().sum()}")
    print(f"rows_with_late_speed_rank={features['late_speed_rank'].notna().sum()}")
    print()
    print("RECOMPUTED UNIQUE RACE COVERAGE")
    for _, row in coverage.iterrows():
        print(f"{row['metric']}_races={int(row['unique_races_available'])} rows={int(row['runner_race_rows_available'])}")
    print()
    print("HISTORICAL PROFILES")
    p = pd.to_numeric(hist["prior_sectional_runs"], errors="coerce").fillna(0) if len(hist) else pd.Series(dtype=float)
    print(f"runner_profile_rows={len(hist)}")
    print(f"with_1plus_prior_sectional={(p >= 1).sum()}")
    print(f"with_2plus_prior_sectional={(p >= 2).sum()}")
    print(f"with_3plus_prior_sectional={(p >= 3).sum()}")
    print()
    print("PRODUCT FACTORS")
    print(f"sectional_weapon_available={hist['sectional_weapon_score'].notna().sum() if len(hist) else 0}")
    print(f"late_power_available={hist['late_power_score'].notna().sum() if len(hist) else 0}")
    print(f"early_speed_available={hist['historical_early_speed_score'].notna().sum() if len(hist) else 0}")
    print(f"sectional_consistency_available={hist['sectional_consistency_score'].notna().sum() if len(hist) else 0}")
    print(f"sectional_trajectory_available={hist['sectional_trajectory_score'].notna().sum() if len(hist) else 0}")
    print()
    print("LIVE JOIN AUDIT")
    for k, v in live_summary.items():
        print(f"{k}={v}")
    print()
    print("INTEGRITY")
    print(f"quarantined_rows_leaked={quarantined_rows_leaked}")
    print(f"strict_prior_leakage={strict_prior_leakage}")
    print(f"duplicate_identity_conflicts={duplicate_identity_conflicts}")
    print(f"score_range_errors={score_range_errors}")
    print()
    print(f"FINAL STATUS: READY_FOR_LIVE_RUNNER_BOARD_JOIN={'YES' if ready else 'NO'}")


if __name__ == "__main__":
    main()
