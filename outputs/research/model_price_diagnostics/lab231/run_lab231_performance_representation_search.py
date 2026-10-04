from pathlib import Path
import math
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
BASE = ROOT / "outputs" / "research" / "model_price_diagnostics"
OUT = BASE / "lab231"
OUT.mkdir(parents=True, exist_ok=True)

LAB179 = BASE / "run_lab179_dynamic_ability_representation.py"
LAB187 = BASE / "run_lab187_strict_elo_revalidation.py"
FORM = ROOT / "outputs/research/model_lab_120/LAB120D_FORM_LINE_FEATURES.csv"
STRICT_ELO = BASE / "lab186/LAB186_STRICT_PRE_ELO.csv"
NETWORK = ROOT / "outputs/research/model_lab_120/LAB120F_NETWORK_DEPTH.csv"
PERF026 = ROOT / "outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
LAB229_OOF = BASE / "lab229/LAB229_OOF_PREDICTIONS_CORRECTED.csv"
LAB230_OVERLAY = BASE / "lab230/LAB230_OVERLAY_TRANSITIONS.csv"
LAB205_CATA = BASE / "lab205/LAB205_CATASTROPHIC_WINNER_CASES.csv"
LAB179_OOF = BASE / "lab179/LAB179_OOF_PREDICTIONS.csv"

STRICT_LL = 2.0328310797721265
DROP_PAIR_LL = 2.0321077047495013
MARKET_LL = 1.835875937807869

HGB_PARAMS = {
    "loss": "log_loss",
    "learning_rate": 0.045,
    "max_leaf_nodes": 31,
    "l2_regularization": 0.15,
    "max_iter": 180,
    "random_state": 121,
}

WEIGHT_FEATURES = {
    "current_weight_kg",
    "weight_change_kg",
    "lab100_rel_current_weight_kg_rank_pct",
    "lab100_rel_weight_change_kg_rank_pct",
}


def dedupe(xs):
    return list(dict.fromkeys(xs))


def norm(s):
    return s.astype(str).str.strip()


def race_normalize(df, raw_col):
    raw = pd.to_numeric(df[raw_col], errors="coerce").clip(lower=1e-15)
    denom = raw.groupby(df["_race"], sort=False).transform("sum")
    count = df.groupby("_race", sort=False)["_race"].transform("size").astype(float)
    p = pd.Series(np.nan, index=df.index, dtype=float)
    good = raw.notna() & denom.notna() & np.isfinite(denom) & denom.gt(0)
    p.loc[good] = raw.loc[good] / denom.loc[good]
    p.loc[~good] = 1.0 / count.loc[~good]
    err = float((p.groupby(df["_race"], sort=False).sum() - 1.0).abs().max())
    if err > 1e-10:
        raise RuntimeError(f"Race normalization failed: {err}")
    return p


def winner_log_loss(df, pcol):
    winners = df.loc[df["_y"].eq(1)].copy()
    counts = winners.groupby("_race", sort=False).size()
    if not counts.eq(1).all():
        raise RuntimeError("Winner-count gate failed.")
    p = pd.to_numeric(winners[pcol], errors="coerce").clip(1e-15, 1.0)
    if p.isna().any():
        raise RuntimeError(f"Missing winner probability in {pcol}")
    return float(-np.log(p).mean())


def second_best(values):
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return np.nan
    return float(np.sort(values)[-2])


def slope(values):
    values = values[np.isfinite(values)]
    if len(values) < 3:
        return np.nan
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, values, 1)[0])


def share_near_peak(values, peak, tolerance=5.0):
    values = values[np.isfinite(values)]
    if len(values) == 0 or not np.isfinite(peak):
        return np.nan
    return float(np.mean(values >= peak - tolerance))


def std_diff(a, b):
    a = pd.to_numeric(a, errors="coerce").dropna()
    b = pd.to_numeric(b, errors="coerce").dropna()
    if len(a) < 20 or len(b) < 20:
        return np.nan
    v = 0.5 * (float(a.var(ddof=1)) + float(b.var(ddof=1)))
    if not np.isfinite(v) or v <= 0:
        return np.nan
    return float((a.mean() - b.mean()) / math.sqrt(v))


def load_strict_matrix():
    src179 = LAB179.read_text(encoding="utf-8-sig", errors="strict")
    marker179 = 'architectures = {"LAB174_RELIABILITY": base_arch}'
    cut179 = src179.find(marker179)
    if cut179 < 0:
        raise RuntimeError("LAB179 bootstrap marker missing.")
    ns179 = {"__name__": "__lab231_bootstrap179__", "__file__": str(LAB179)}
    exec(
        compile(
            src179[:cut179].replace(
                "model_price_diagnostics/lab179",
                "model_price_diagnostics/lab231/bootstrap179",
            ),
            str(LAB179),
            "exec",
        ),
        ns179,
        ns179,
    )
    model = ns179["model"].copy()
    locked278 = dedupe(
        list(ns179["base_features"])
        + list(ns179["reliability_all"])
        + list(ns179["recency_cols"])
    )
    if len(locked278) != 278:
        raise RuntimeError(f"LOCKED278 gate failed: {len(locked278)}")

    src187 = LAB187.read_text(encoding="utf-8-sig", errors="strict")
    marker187 = 'print("=" * 112)\nprint("LAB187 - STRICT GOVERNED ELO MODEL REVALIDATION")'
    cut187 = src187.find(marker187)
    if cut187 < 0:
        raise RuntimeError("LAB187 helper marker missing.")
    ns187 = {"__name__": "__lab231_helpers187__", "__file__": str(LAB187)}
    exec(compile(src187[:cut187], str(LAB187), "exec"), ns187, ns187)
    ns187["FORM"] = FORM
    ns187["STRICT_ELO"] = STRICT_ELO
    ns187["NETWORK"] = NETWORK

    model["_race"] = norm(model["_race"])
    model["_horse"] = norm(model["_horse"])
    model = ns187["load_form_identity"](model)
    model = ns187["join_strict_elo"](model)
    model, network_cols = ns187["load_source_features"](
        model,
        NETWORK,
        "network",
        ["network_effective_sample_last1"],
    )
    if len(network_cols) != 1:
        raise RuntimeError(f"Network gate failed: {network_cols}")
    features281 = dedupe(
        locked278
        + [
            "lab187_strict__pre_elo_basic",
            "lab187_strict__pre_elo_margin",
            network_cols[0],
        ]
    )
    if len(features281) != 281:
        raise RuntimeError(f"STRICT281 gate failed: {len(features281)}")
    missing = [c for c in features281 if c not in model.columns]
    if missing:
        raise RuntimeError(f"STRICT281 missing features: {missing[:20]}")
    if not WEIGHT_FEATURES.issubset(set(features281)):
        raise RuntimeError("Frozen weight-feature gate failed.")
    model["_year"] = pd.to_numeric(model["_year"], errors="raise").astype(int)
    model["_y"] = pd.to_numeric(model["_y"], errors="raise").astype(int)
    model["race_date"] = pd.to_datetime(model["race_date"], errors="raise")
    return model, features281


def load_reference_predictions():
    ref = pd.read_csv(
        LAB229_OOF,
        usecols=["_race", "_horse", "_year", "_y", "p_model", "architecture", "algorithm"],
        low_memory=False,
    )
    ref["_race"] = norm(ref["_race"])
    ref["_horse"] = norm(ref["_horse"])
    ref["architecture"] = norm(ref["architecture"])
    ref["algorithm"] = norm(ref["algorithm"])
    ref["_y"] = pd.to_numeric(ref["_y"], errors="raise").astype(int)
    ref["_year"] = pd.to_numeric(ref["_year"], errors="raise").astype(int)
    ref["p_model"] = pd.to_numeric(ref["p_model"], errors="raise")
    strict = ref.loc[
        ref["architecture"].eq("STRICT281_BASELINE") & ref["algorithm"].eq("ENSEMBLE")
    ].copy()
    ll = winner_log_loss(strict, "p_model")
    if abs(ll - STRICT_LL) > 1e-10:
        raise RuntimeError(f"STRICT reference LL gate failed: {ll}")
    return strict.rename(columns={"p_model": "p_strict"})


def build_history_features(model):
    usecols = [
        "canonical_race_id",
        "canonical_horse_id",
        "race_date",
        "distance_metres",
        "race_class_group",
        "track_condition_group",
        "finish_position",
        "finish_margin",
        "runner_lengths_v_standard_026",
        "epi_value_026",
        "epi_status_026",
    ]
    hist = pd.read_csv(PERF026, usecols=usecols, low_memory=False)
    hist = hist.loc[hist["canonical_horse_id"].notna()].copy()
    hist["canonical_horse_id"] = norm(hist["canonical_horse_id"])
    hist["canonical_race_id"] = norm(hist["canonical_race_id"])
    hist["race_date"] = pd.to_datetime(hist["race_date"], errors="coerce")
    hist = hist.loc[hist["race_date"].notna()].copy()
    for c in [
        "distance_metres",
        "finish_position",
        "finish_margin",
        "runner_lengths_v_standard_026",
        "epi_value_026",
    ]:
        hist[c] = pd.to_numeric(hist[c], errors="coerce")
    hist["race_class_group"] = hist["race_class_group"].astype(str).str.strip()
    hist["track_condition_group"] = hist["track_condition_group"].astype(str).str.strip()
    hist = hist.sort_values(
        ["canonical_horse_id", "race_date", "canonical_race_id"],
        kind="mergesort",
    ).reset_index(drop=True)

    target_class_col = next((c for c in ["race_class_group", "race_class"] if c in model.columns), None)
    target_condition_col = next((c for c in ["track_condition_group", "track_condition"] if c in model.columns), None)
    target_distance_col = "_current_distance" if "_current_distance" in model.columns else "distance_metres"

    target = model[
        [
            "_race",
            "_horse",
            "_year",
            "_y",
            "race_date",
            target_distance_col,
        ]
        + ([target_class_col] if target_class_col else [])
        + ([target_condition_col] if target_condition_col else [])
    ].copy()
    target = target.rename(columns={target_distance_col: "target_distance"})
    target["target_distance"] = pd.to_numeric(target["target_distance"], errors="coerce")
    target["target_class_group"] = (
        target[target_class_col].astype(str).str.strip() if target_class_col else ""
    )
    target["target_condition_group"] = (
        target[target_condition_col].astype(str).str.strip() if target_condition_col else ""
    )

    grouped_hist = {h: g for h, g in hist.groupby("canonical_horse_id", sort=False)}
    rows = []
    for i, r in enumerate(target.to_dict(orient="records"), 1):
        if i % 20000 == 0:
            print(f"  history feature rows={i:,}", flush=True)
        g = grouped_hist.get(r["_horse"])
        base = {
            "_race": r["_race"],
            "_horse": r["_horse"],
            "_year": r["_year"],
            "_y": r["_y"],
        }
        if g is None:
            rows.append(base)
            continue
        dates = g["race_date"].to_numpy(dtype="datetime64[ns]")
        target_date = pd.Timestamp(r["race_date"])
        cutoff = int(np.searchsorted(dates, np.datetime64(target_date), side="left"))
        prior = g.iloc[:cutoff]
        epi = prior["epi_value_026"].to_numpy(dtype=float)
        margin = prior["finish_margin"].to_numpy(dtype=float)
        pos = prior["finish_position"].to_numpy(dtype=float)
        dist = prior["distance_metres"].to_numpy(dtype=float)
        hdates = prior["race_date"].to_numpy(dtype="datetime64[D]")
        finite_epi = epi[np.isfinite(epi)]

        def tail(vals, k):
            vals = vals[np.isfinite(vals)]
            return vals[-k:] if len(vals) else vals

        e3 = tail(epi, 3)
        e5 = tail(epi, 5)
        e10 = tail(epi, 10)
        m5 = tail(margin, 5)
        p5 = tail(pos, 5)
        peak = float(np.nanmax(finite_epi)) if len(finite_epi) else np.nan
        if len(finite_epi):
            peak_pos = int(np.nanargmax(epi))
            peak_date = hdates[peak_pos]
            days_since_peak = float((np.datetime64(target_date.date()) - peak_date).astype("timedelta64[D]").astype(int))
            peak_age_runs = float(len(epi) - peak_pos)
        else:
            days_since_peak = np.nan
            peak_age_runs = np.nan
        days_since_last = (
            float((np.datetime64(target_date.date()) - hdates[-1]).astype("timedelta64[D]").astype(int))
            if len(hdates)
            else np.nan
        )
        target_distance = r["target_distance"]
        dist_mask = np.isfinite(dist) & np.isfinite(target_distance) & (np.abs(dist - target_distance) <= 200.0)
        class_mask = prior["race_class_group"].astype(str).eq(str(r["target_class_group"])).to_numpy()
        cond_mask = prior["track_condition_group"].astype(str).eq(str(r["target_condition_group"])).to_numpy()
        dist_epi = epi[dist_mask]
        class_epi = epi[class_mask]
        cond_epi = epi[cond_mask]

        base.update(
            {
                "h231_hist_perf_runs": float(len(prior)),
                "h231_epi_last1": float(e5[-1]) if len(e5) else np.nan,
                "h231_epi_last3_mean": float(np.nanmean(e3)) if len(e3) else np.nan,
                "h231_epi_last3_best": float(np.nanmax(e3)) if len(e3) else np.nan,
                "h231_epi_last5_mean": float(np.nanmean(e5)) if len(e5) else np.nan,
                "h231_epi_last5_best": float(np.nanmax(e5)) if len(e5) else np.nan,
                "h231_epi_last5_second_best": second_best(e5),
                "h231_epi_last5_median": float(np.nanmedian(e5)) if len(e5) else np.nan,
                "h231_epi_last5_worst": float(np.nanmin(e5)) if len(e5) else np.nan,
                "h231_epi_last5_std": float(np.nanstd(e5)) if len(e5) >= 2 else np.nan,
                "h231_epi_last10_median": float(np.nanmedian(e10)) if len(e10) else np.nan,
                "h231_epi_last10_best": float(np.nanmax(e10)) if len(e10) else np.nan,
                "h231_epi_last10_worst": float(np.nanmin(e10)) if len(e10) else np.nan,
                "h231_epi_last10_std": float(np.nanstd(e10)) if len(e10) >= 2 else np.nan,
                "h231_epi_peak_prior": peak,
                "h231_epi_peak_minus_last10_median": peak - float(np.nanmedian(e10)) if len(e10) and np.isfinite(peak) else np.nan,
                "h231_epi_last1_minus_peak": float(e5[-1] - peak) if len(e5) and np.isfinite(peak) else np.nan,
                "h231_epi_last1_minus_last5_median": float(e5[-1] - np.nanmedian(e5)) if len(e5) else np.nan,
                "h231_epi_last5_slope": slope(e5),
                "h231_margin_last5_mean": float(np.nanmean(m5)) if len(m5) else np.nan,
                "h231_margin_last5_worst": float(np.nanmax(m5)) if len(m5) else np.nan,
                "h231_margin_last5_std": float(np.nanstd(m5)) if len(m5) >= 2 else np.nan,
                "h231_finishpos_last5_mean": float(np.nanmean(p5)) if len(p5) else np.nan,
                "h231_days_since_last_perf": days_since_last,
                "h231_days_since_peak": days_since_peak,
                "h231_peak_age_runs": peak_age_runs,
                "h231_dist200_count": float(np.isfinite(dist_epi).sum()),
                "h231_dist200_mean": float(np.nanmean(dist_epi)) if np.isfinite(dist_epi).any() else np.nan,
                "h231_dist200_best": float(np.nanmax(dist_epi)) if np.isfinite(dist_epi).any() else np.nan,
                "h231_dist200_best_minus_peak": float(np.nanmax(dist_epi) - peak) if np.isfinite(dist_epi).any() and np.isfinite(peak) else np.nan,
                "h231_same_class_count": float(np.isfinite(class_epi).sum()),
                "h231_same_class_mean": float(np.nanmean(class_epi)) if np.isfinite(class_epi).any() else np.nan,
                "h231_same_class_best": float(np.nanmax(class_epi)) if np.isfinite(class_epi).any() else np.nan,
                "h231_same_condition_count": float(np.isfinite(cond_epi).sum()),
                "h231_same_condition_mean": float(np.nanmean(cond_epi)) if np.isfinite(cond_epi).any() else np.nan,
                "h231_near_peak_share_last10": share_near_peak(e10, peak),
                "h231_recent_above_last10_median_share": float(np.mean(e5 >= np.nanmedian(e10))) if len(e5) and len(e10) else np.nan,
            }
        )
        rows.append(base)
    feats = pd.DataFrame(rows)

    raw_new = [c for c in feats.columns if c.startswith("h231_")]
    for c in raw_new:
        vals = pd.to_numeric(feats[c], errors="coerce")
        feats[f"{c}_rank_pct"] = vals.groupby(feats["_race"], sort=False).rank(pct=True, method="average")
        mean = vals.groupby(feats["_race"], sort=False).transform("mean")
        sd = vals.groupby(feats["_race"], sort=False).transform("std")
        feats[f"{c}_z"] = np.where(sd.abs() < 1e-12, np.nan, (vals - mean) / sd)
    feats.to_csv(OUT / "LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv", index=False)
    return feats


def contrast(frame, population_col, features):
    rows = []
    groups = frame[population_col].dropna().unique().tolist()
    if len(groups) < 2:
        return pd.DataFrame()
    for a in groups:
        for b in groups:
            if str(a) >= str(b):
                continue
            aa = frame.loc[frame[population_col].eq(a)]
            bb = frame.loc[frame[population_col].eq(b)]
            for f in features:
                rows.append(
                    {
                        "comparison": f"{a}_minus_{b}",
                        "feature": f,
                        "n_a": int(aa[f].notna().sum()),
                        "n_b": int(bb[f].notna().sum()),
                        "mean_a": float(pd.to_numeric(aa[f], errors="coerce").mean()),
                        "mean_b": float(pd.to_numeric(bb[f], errors="coerce").mean()),
                        "standardized_difference": std_diff(aa[f], bb[f]),
                    }
                )
    return pd.DataFrame(rows)


def add_final_sp(df):
    sp = pd.read_csv(LAB179_OOF, usecols=["_race", "_horse", "_sp"], low_memory=False)
    sp["_race"] = norm(sp["_race"])
    sp["_horse"] = norm(sp["_horse"])
    sp["_sp"] = pd.to_numeric(sp["_sp"], errors="coerce")
    sp = sp.dropna(subset=["_sp"]).drop_duplicates(["_race", "_horse"], keep="first")
    return df.merge(sp.rename(columns={"_sp": "final_sp"}), on=["_race", "_horse"], how="left", validate="one_to_one")


def fit_oof(model, architectures):
    oof_parts = []
    for year in range(2021, 2027):
        train = model.loc[model["_year"] < year].copy()
        test = model.loc[model["_year"].eq(year)].copy()
        if train.empty or test.empty:
            continue
        print(f"FIT_YEAR={year} TRAIN={len(train):,} TEST={len(test):,}", flush=True)
        ytr = train["_y"].astype(int)
        for arch_name, features in architectures.items():
            print(f"  ARCH={arch_name} FEATURES={len(features)}", flush=True)
            Xtr = train[features].apply(pd.to_numeric, errors="coerce")
            Xte = test[features].apply(pd.to_numeric, errors="coerce")
            med = Xtr.median(axis=0, skipna=True).fillna(0.0)
            Xtr = Xtr.fillna(med).fillna(0.0)
            Xte = Xte.fillna(med).fillna(0.0)

            hgb = HistGradientBoostingClassifier(**HGB_PARAMS)
            hgb.fit(Xtr, ytr)
            h = test[["_race", "_horse", "_year", "_y"]].copy()
            h["_raw"] = hgb.predict_proba(Xte)[:, 1]
            h["p_model"] = race_normalize(h, "_raw")
            h["architecture"] = arch_name
            h["algorithm"] = "HGB"
            oof_parts.append(h.drop(columns=["_raw"]))

            scaler = StandardScaler()
            Xtr_s = scaler.fit_transform(Xtr)
            Xte_s = scaler.transform(Xte)
            logit = LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs", random_state=121)
            logit.fit(Xtr_s, ytr)
            l = test[["_race", "_horse", "_year", "_y"]].copy()
            l["_raw"] = logit.predict_proba(Xte_s)[:, 1]
            l["p_model"] = race_normalize(l, "_raw")
            l["architecture"] = arch_name
            l["algorithm"] = "LOGISTIC"
            oof_parts.append(l.drop(columns=["_raw"]))
    oof = pd.concat(oof_parts, ignore_index=True)
    keys = ["_race", "_horse", "_year", "_y", "architecture"]
    hgb = oof.loc[oof["algorithm"].eq("HGB"), keys + ["p_model"]].rename(columns={"p_model": "p_hgb"})
    logit = oof.loc[oof["algorithm"].eq("LOGISTIC"), keys + ["p_model"]].rename(columns={"p_model": "p_logistic"})
    ens = hgb.merge(logit, on=keys, how="inner", validate="one_to_one")
    ens["p_model"] = 0.5 * ens["p_hgb"] + 0.5 * ens["p_logistic"]
    ens["algorithm"] = "ENSEMBLE"
    oof = pd.concat([oof, ens[keys + ["algorithm", "p_model"]]], ignore_index=True)
    err = float(
        (
            oof.loc[oof["algorithm"].eq("ENSEMBLE")]
            .groupby(["architecture", "_race"], sort=False)["p_model"]
            .sum()
            - 1.0
        )
        .abs()
        .max()
    )
    if err > 1e-10:
        raise RuntimeError(f"Ensemble sum gate failed: {err}")
    return oof


def score_outputs(oof):
    rows = []
    for (arch, alg), z in oof.groupby(["architecture", "algorithm"], sort=False):
        rows.append(
            {
                "architecture": arch,
                "algorithm": alg,
                "runners": int(len(z)),
                "races": int(z["_race"].nunique()),
                "race_winner_log_loss": winner_log_loss(z, "p_model"),
            }
        )
    scores = pd.DataFrame(rows)
    ens_scores = scores.loc[scores["algorithm"].eq("ENSEMBLE")].copy()
    ens_scores["gain_vs_strict281"] = STRICT_LL - ens_scores["race_winner_log_loss"]
    ens_scores["gain_vs_drop_pair"] = DROP_PAIR_LL - ens_scores["race_winner_log_loss"]
    ens_scores.to_csv(OUT / "LAB231_PRIMARY_RESULTS.csv", index=False)

    year_rows = []
    ens = oof.loc[oof["algorithm"].eq("ENSEMBLE")].copy()
    for (arch, year), z in ens.groupby(["architecture", "_year"], sort=False):
        year_rows.append(
            {
                "architecture": arch,
                "_year": int(year),
                "races": int(z["_race"].nunique()),
                "race_winner_log_loss": winner_log_loss(z, "p_model"),
                "gain_vs_strict281": np.nan,
            }
        )
    yearly = pd.DataFrame(year_rows)
    strict_ref = pd.read_csv(
        BASE / "lab229/LAB229_YEAR_STABILITY_CORRECTED.csv",
        low_memory=False,
    )
    strict_ref = strict_ref.loc[
        strict_ref["architecture"].astype(str).eq("STRICT281_BASELINE"),
        ["_year", "race_winner_log_loss"],
    ].rename(columns={"race_winner_log_loss": "strict_year_ll"})
    yearly = yearly.merge(strict_ref, on="_year", how="left", validate="many_to_one")
    yearly["gain_vs_strict281"] = yearly["strict_year_ll"] - yearly["race_winner_log_loss"]
    yearly.to_csv(OUT / "LAB231_YEAR_RESULTS.csv", index=False)
    return scores, ens_scores, yearly


def rank_and_economics(best_oof, strict_ref):
    z = best_oof.loc[best_oof["algorithm"].eq("ENSEMBLE")].copy()
    z = add_final_sp(z)
    z["edge"] = z["p_model"] * z["final_sp"]
    z["extreme"] = z["edge"].ge(2.0)
    z["positive_edge"] = z["edge"].gt(1.0)
    econ_rows = []
    for label, mask in [("POSITIVE_EDGE", z["positive_edge"]), ("OVERLAY_100PCT_PLUS", z["extreme"])]:
        zz = z.loc[mask].copy()
        wins = int(zz["_y"].sum())
        expected = float(zz["p_model"].sum())
        profit = float(np.where(zz["_y"].eq(1), zz["final_sp"] - 1.0, -1.0).sum())
        econ_rows.append(
            {
                "model": z["architecture"].iloc[0],
                "bet_definition": label,
                "bets": int(len(zz)),
                "wins": wins,
                "expected_wins": expected,
                "phantom_wins": expected - wins,
                "profit_units": profit,
                "POT": profit / len(zz) if len(zz) else np.nan,
            }
        )
    strict = strict_ref[["_race", "_horse", "_year", "_y", "p_strict"]].copy()
    strict = add_final_sp(strict)
    strict["edge"] = strict["p_strict"] * strict["final_sp"]
    strict["extreme"] = strict["edge"].ge(2.0)
    zz = strict.loc[strict["extreme"]].copy()
    strict_phantom = float(zz["p_strict"].sum() - zz["_y"].sum())

    winners = z.loc[z["_y"].eq(1), ["_race", "_horse"]].copy()
    rank_best = z.sort_values(["_race", "p_model", "_horse"], ascending=[True, False, True]).copy()
    rank_best["rank_best"] = rank_best.groupby("_race", sort=False).cumcount() + 1
    rank_strict = strict_ref.sort_values(["_race", "p_strict", "_horse"], ascending=[True, False, True]).copy()
    rank_strict["rank_strict"] = rank_strict.groupby("_race", sort=False).cumcount() + 1
    wr = winners.merge(rank_best[["_race", "_horse", "rank_best"]], on=["_race", "_horse"], how="left")
    wr = wr.merge(rank_strict[["_race", "_horse", "rank_strict"]], on=["_race", "_horse"], how="left")
    winner_rank_effect = int((wr["rank_best"] < wr["rank_strict"]).sum() - (wr["rank_best"] > wr["rank_strict"]).sum())

    fav_best = rank_best.drop_duplicates("_race", keep="first")[["_race", "_horse"]].rename(columns={"_horse": "best_fav"})
    fav_strict = rank_strict.drop_duplicates("_race", keep="first")[["_race", "_horse"]].rename(columns={"_horse": "strict_fav"})
    fav = winners.rename(columns={"_horse": "winner"}).merge(fav_best, on="_race").merge(fav_strict, on="_race")
    favourite_effect = int(((fav["best_fav"].eq(fav["winner"])) & (~fav["strict_fav"].eq(fav["winner"]))).sum() - ((~fav["best_fav"].eq(fav["winner"])) & (fav["strict_fav"].eq(fav["winner"]))).sum())

    cata = pd.read_csv(LAB205_CATA, low_memory=False)
    cata["race"] = norm(cata["race"])
    cata["winner_horse"] = norm(cata["winner_horse"])
    cr = cata[["race", "winner_horse"]].rename(columns={"race": "_race", "winner_horse": "_horse"})
    cr = cr.merge(rank_best[["_race", "_horse", "rank_best"]], on=["_race", "_horse"], how="left")
    cr = cr.merge(rank_strict[["_race", "_horse", "rank_strict"]], on=["_race", "_horse"], how="left")
    catastrophic_recovered = int((cr["rank_best"] < cr["rank_strict"]).sum())

    econ = pd.DataFrame(econ_rows)
    econ["strict_extreme_phantom_wins"] = strict_phantom
    econ.to_csv(OUT / "LAB231_ECONOMICS_AND_RANKING.csv", index=False)
    return {
        "winner_rank_effect": winner_rank_effect,
        "favourite_effect": favourite_effect,
        "catastrophic_winners_recovered": catastrophic_recovered,
        "strict_extreme_phantom_wins": strict_phantom,
        "best_extreme_phantom_wins": float(
            econ.loc[econ["bet_definition"].eq("OVERLAY_100PCT_PLUS"), "phantom_wins"].iloc[0]
        ),
    }


print("=" * 118)
print("LAB231 - HISTORICAL PERFORMANCE REPRESENTATION SEARCH")
print("=" * 118)
print("STRICT_PIT=YES")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")
print("WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED=NO")
print("PRODUCTION_MODIFIED=NO")

model, features281 = load_strict_matrix()
strict_ref = load_reference_predictions()
hist_features = build_history_features(model)

model = model.merge(hist_features.drop(columns=["_year", "_y"]), on=["_race", "_horse"], how="left", validate="one_to_one")
new_raw = [c for c in hist_features.columns if c.startswith("h231_")]
feature_manifest_rows = []

strict_eval = strict_ref[["_race", "_horse", "_year", "_y", "p_strict"]].copy()
strict_eval = add_final_sp(strict_eval)
strict_eval["edge"] = strict_eval["p_strict"] * strict_eval["final_sp"]
strict_eval["persistent_extreme"] = strict_eval["edge"].ge(2.0)
strict_eval["phantom_population"] = np.select(
    [strict_eval["persistent_extreme"] & strict_eval["_y"].eq(1), strict_eval["persistent_extreme"] & strict_eval["_y"].eq(0)],
    ["TRUE_EXTREME_WINNER", "FALSE_EXTREME_LOSER"],
    default="NON_EXTREME_REFERENCE",
)
contrast_frame = strict_eval.merge(hist_features, on=["_race", "_horse", "_year", "_y"], how="left", validate="one_to_one")
phantom_contrast = contrast(
    contrast_frame.loc[contrast_frame["phantom_population"].isin(["TRUE_EXTREME_WINNER", "FALSE_EXTREME_LOSER"])],
    "phantom_population",
    new_raw,
)
phantom_contrast.to_csv(OUT / "LAB231_PHANTOM_OVERLAY_CONTRAST.csv", index=False)

cata = pd.read_csv(LAB205_CATA, low_memory=False)
cata["race"] = norm(cata["race"])
cata["winner_horse"] = norm(cata["winner_horse"])
cata_key = cata[["race", "winner_horse"]].rename(columns={"race": "_race", "winner_horse": "_horse"})
cat_frame = strict_eval[["_race", "_horse", "_year", "_y"]].merge(hist_features, on=["_race", "_horse", "_year", "_y"], how="left")
cat_frame["cat_population"] = np.where(
    cat_frame.set_index(["_race", "_horse"]).index.isin(cata_key.set_index(["_race", "_horse"]).index),
    "CATASTROPHIC_WINNER",
    "OTHER_OOF_RUNNER",
)
cat_contrast = contrast(cat_frame, "cat_population", new_raw)
cat_contrast.to_csv(OUT / "LAB231_CATASTROPHIC_CONTRAST.csv", index=False)

blocks = {
    "H231_DISTRIBUTION_SHAPE": [
        "h231_epi_last5_best",
        "h231_epi_last5_second_best",
        "h231_epi_last5_median",
        "h231_epi_last5_worst",
        "h231_epi_last5_std",
        "h231_epi_last10_median",
        "h231_epi_peak_minus_last10_median",
    ],
    "H231_PEAK_DECAY_REBOUND": [
        "h231_epi_peak_prior",
        "h231_epi_last1_minus_peak",
        "h231_epi_last1_minus_last5_median",
        "h231_epi_last5_slope",
        "h231_days_since_peak",
        "h231_peak_age_runs",
        "h231_near_peak_share_last10",
    ],
    "H231_DOWNSIDE_VOLATILITY": [
        "h231_epi_last10_worst",
        "h231_epi_last10_std",
        "h231_margin_last5_mean",
        "h231_margin_last5_worst",
        "h231_margin_last5_std",
        "h231_finishpos_last5_mean",
    ],
    "H231_DISTANCE_CLASS_CONDITIONED": [
        "h231_dist200_count",
        "h231_dist200_mean",
        "h231_dist200_best",
        "h231_dist200_best_minus_peak",
        "h231_same_class_count",
        "h231_same_class_mean",
        "h231_same_class_best",
    ],
    "H231_EVIDENCE_DEPTH_REPRODUCTION": [
        "h231_hist_perf_runs",
        "h231_days_since_last_perf",
        "h231_same_condition_count",
        "h231_same_condition_mean",
        "h231_near_peak_share_last10",
        "h231_recent_above_last10_median_share",
    ],
}

def expand_block(cols):
    expanded = []
    for c in cols:
        expanded.extend([c, f"{c}_rank_pct", f"{c}_z"])
    return [c for c in expanded if c in model.columns]

for name, cols in blocks.items():
    expanded = expand_block(cols)
    feature_manifest_rows.append(
        {
            "architecture": f"STRICT281_PLUS_{name}",
            "concept": name,
            "new_feature_count": len(expanded),
            "base_feature_count": len(features281),
            "total_feature_count": len(features281) + len(expanded),
            "new_features": " | ".join(expanded),
            "pit_construction": "Horse-level performances with race_date strictly less than target race_date; no same-day inclusion.",
            "leakage_audit": "Uses only 026 historical rows before target race_date; final SP not used.",
        }
    )

candidate_manifest = pd.DataFrame(feature_manifest_rows)
candidate_manifest.to_csv(OUT / "LAB231_CANDIDATE_MANIFEST.csv", index=False)

architectures = {
    f"STRICT281_PLUS_{name}": dedupe(features281 + expand_block(cols))
    for name, cols in blocks.items()
}
architectures["STRICT281_PLUS_ALL_H231_PERFORMANCE"] = dedupe(
    features281 + [c for cols in blocks.values() for c in expand_block(cols)]
)

oof = fit_oof(model, architectures)
oof.to_csv(OUT / "LAB231_OOF_PREDICTIONS.csv", index=False)
scores, ens_scores, yearly = score_outputs(oof)

best = ens_scores.sort_values("race_winner_log_loss", ascending=True).iloc[0]
best_arch = str(best["architecture"])
rank_econ = rank_and_economics(oof.loc[oof["architecture"].eq(best_arch)].copy(), strict_ref)
best_year = yearly.loc[yearly["architecture"].eq(best_arch)].copy()
years_improved = int(best_year["gain_vs_strict281"].gt(0).sum())
recent_improved = int(best_year.loc[best_year["_year"].isin([2024, 2025, 2026]), "gain_vs_strict281"].gt(0).sum())

best_ll = float(best["race_winner_log_loss"])
gain = STRICT_LL - best_ll
material = bool(
    gain >= 0.002
    and years_improved >= 4
    and recent_improved >= 2
)
major = bool(gain >= 0.005 and recent_improved >= 2)
phantom_reduction = rank_econ["strict_extreme_phantom_wins"] - rank_econ["best_extreme_phantom_wins"]

if material:
    next_action = "LOCK_DOWN_AND_REPLAY_BEST_H231_ARCHITECTURE_WITH_PARITY_AUDITS"
elif gain > 0:
    next_action = "TREAT_AS_MINOR_INTERNAL_REPRESENTATION_GAIN_AND_MAP_REMAINING_DATA_GAP"
else:
    next_action = "CURRENT_INTERNAL_PERFORMANCE_REPRESENTATIONS_FAILED_MATERIAL_GATE_BUILD_DATA_GAP_MAP"

summary = pd.DataFrame(
    [
        {"metric": "REFERENCE_LL", "value": STRICT_LL},
        {"metric": "DROP_PAIR_RESEARCH_LL", "value": DROP_PAIR_LL},
        {"metric": "FINAL_MARKET_LL", "value": MARKET_LL},
        {"metric": "BEST_NEW_ARCHITECTURE", "value": best_arch},
        {"metric": "BEST_NEW_LL", "value": best_ll},
        {"metric": "LL_GAIN", "value": gain},
        {"metric": "YEARS_IMPROVED", "value": years_improved},
        {"metric": "RECENT_2024_2026_IMPROVED", "value": recent_improved},
        {"metric": "WINNER_RANK_EFFECT", "value": rank_econ["winner_rank_effect"]},
        {"metric": "FAVOURITE_EFFECT", "value": rank_econ["favourite_effect"]},
        {"metric": "CATASTROPHIC_WINNERS_RECOVERED", "value": rank_econ["catastrophic_winners_recovered"]},
        {"metric": "STRICT_EXTREME_PHANTOM_WINS", "value": rank_econ["strict_extreme_phantom_wins"]},
        {"metric": "BEST_MODEL_EXTREME_PHANTOM_WINS", "value": rank_econ["best_extreme_phantom_wins"]},
        {"metric": "PHANTOM_WIN_REDUCTION", "value": phantom_reduction},
        {"metric": "BEST_NEW_INFORMATION_CONCEPT", "value": best_arch.replace("STRICT281_PLUS_", "")},
        {"metric": "PERFORMANCE_REPRESENTATION_GAP", "value": "PARTIALLY_TESTED_WITH_026_STRICT_PIT_DISTRIBUTION_TRAJECTORY_DISTANCE_CLASS_VOLATILITY_REPRESENTATIONS"},
        {"metric": "INTERNAL_INFORMATION_REMAINING", "value": "YES_IF_MATERIAL_GATE_FAILS_ONLY_SMALL_SIGNAL_IN_HISTORICAL_PERFORMANCE_SHAPE"},
        {"metric": "EXTERNAL_INFORMATION_GAP", "value": "LIKELY_REMAINS_IF_PHANTOM_OVERLAY_AND_CATASTROPHIC_FAILURES_PERSIST"},
        {"metric": "MATERIAL_MODEL_IMPROVEMENT", "value": "YES" if material else "NO"},
        {"metric": "MAJOR_MODEL_IMPROVEMENT", "value": "YES" if major else "NO"},
        {"metric": "NEXT_MAJOR_ACTION", "value": next_action},
        {"metric": "STRICT_PIT", "value": "YES"},
        {"metric": "MARKET_AS_FEATURE", "value": "NO"},
        {"metric": "FINAL_SP_EVALUATION_ONLY", "value": "YES"},
        {"metric": "WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED", "value": "NO"},
        {"metric": "PRODUCTION_MODIFIED", "value": "NO"},
        {"metric": "LAB231", "value": "PASS"},
    ]
)
summary.to_csv(OUT / "LAB231_SUMMARY.csv", index=False)

print(f"REFERENCE_LL={STRICT_LL}")
print(f"BEST_NEW_LL={best_ll}")
print(f"LL_GAIN={gain}")
print(f"YEARS_IMPROVED={years_improved}")
print(f"RECENT_2024_2026_IMPROVED={recent_improved}")
print(f"WINNER_RANK_EFFECT={rank_econ['winner_rank_effect']}")
print(f"FAVOURITE_EFFECT={rank_econ['favourite_effect']}")
print(f"CATASTROPHIC_WINNERS_RECOVERED={rank_econ['catastrophic_winners_recovered']}")
print(f"STRICT_EXTREME_PHANTOM_WINS={rank_econ['strict_extreme_phantom_wins']}")
print(f"BEST_MODEL_EXTREME_PHANTOM_WINS={rank_econ['best_extreme_phantom_wins']}")
print(f"PHANTOM_WIN_REDUCTION={phantom_reduction}")
print(f"BEST_NEW_INFORMATION_CONCEPT={best_arch.replace('STRICT281_PLUS_', '')}")
print("PERFORMANCE_REPRESENTATION_GAP=PARTIALLY_TESTED_WITH_026_STRICT_PIT_DISTRIBUTION_TRAJECTORY_DISTANCE_CLASS_VOLATILITY_REPRESENTATIONS")
print("INTERNAL_INFORMATION_REMAINING=YES_IF_MATERIAL_GATE_FAILS_ONLY_SMALL_SIGNAL_IN_HISTORICAL_PERFORMANCE_SHAPE")
print("EXTERNAL_INFORMATION_GAP=LIKELY_REMAINS_IF_PHANTOM_OVERLAY_AND_CATASTROPHIC_FAILURES_PERSIST")
print(f"MATERIAL_MODEL_IMPROVEMENT={'YES' if material else 'NO'}")
print(f"NEXT_MAJOR_ACTION={next_action}")
print("STRICT_PIT=YES")
print("MARKET_AS_FEATURE=NO")
print("FINAL_SP_EVALUATION_ONLY=YES")
print("WEIGHT_FEATURES_ATTRIBUTED_OR_INTERPRETED=NO")
print("PRODUCTION_MODIFIED=NO")
print("LAB231=PASS")
