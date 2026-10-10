import argparse
import hashlib
import json
import math
import subprocess
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


YEARS = (2022, 2023, 2024)
EVIDENCE_CLASS = "REUSED_DEVELOPMENT"
MASS_TOL = 1e-12
RNG_SEED = 42

warnings.filterwarnings("ignore", message="`sklearn.utils.parallel.delayed` should be used*")


STAGE016_FAMILY = [
    "current_weight_kg",
    "weight_change_kg",
    "distance_change_metres",
    "abs_distance_change_metres",
    "prior_same_class_starts",
    "prior_exact_distance_starts_031",
    "context_authority_missing",
    "weight_change_missing",
    "distance_change_missing",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--max-year", type=int, required=True)
    p.add_argument("--evidence-class", required=True)
    p.add_argument("--candidate-budget", required=True)
    p.add_argument("--stage011-report", required=True)
    p.add_argument("--stage011-scores-dir", required=True)
    p.add_argument("--stage004-universe", required=True)
    p.add_argument("--stage006-warehouse", required=True)
    p.add_argument("--d45-matrix", required=True)
    p.add_argument("--lab031-context", required=True)
    p.add_argument("--perf026", required=True)
    p.add_argument("--out", required=True)
    return p.parse_args()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def softmax(values):
    v = np.asarray(values, dtype=float)
    e = np.exp(v - np.max(v))
    return e / e.sum()


def forbid_market_columns(columns):
    bad = []
    for col in columns:
        lc = col.lower()
        tokens = lc.replace("-", "_").split("_")
        if "sp" in tokens or "bsp" in tokens:
            bad.append(col)
        elif any(term in lc for term in ["starting_price", "odds", "market", "bet", "stake", "return"]):
            bad.append(col)
    if bad:
        raise RuntimeError(f"STOP_FORBIDDEN_MARKET_COLUMNS: {bad[:20]}")


def build_matrix(args, stage011_features):
    stage006 = Path(args.stage006_warehouse)
    d45 = Path(args.d45_matrix)
    perf026 = Path(args.perf026)
    context = Path(args.lab031_context)
    for path in (stage006, d45, perf026):
        if not path.is_file():
            raise FileNotFoundError(path)

    w_cols = list(pd.read_csv(stage006, nrows=0).columns)
    d_cols = list(pd.read_csv(d45, nrows=0).columns)
    forbid_market_columns(w_cols)
    forbid_market_columns(d_cols)
    if not context.is_file():
        raise FileNotFoundError(context)
    c_cols = list(pd.read_csv(context, nrows=0).columns)
    forbid_market_columns(c_cols)

    x = pd.read_csv(stage006)
    x["race_date"] = pd.to_datetime(x["race_date"])
    x["year"] = x["race_date"].dt.year
    if not x["year"].between(2021, args.max_year).all():
        raise RuntimeError("STOP_STAGE006_OUT_OF_SCOPE_YEAR")

    ctx = [
        c
        for c in d_cols
        if any(k in c.lower() for k in ["barrier", "jockey_prior", "trainer_prior"])
    ]
    d = pd.read_csv(d45, usecols=["_race", "_horse"] + ctx)
    x = x.merge(d.drop_duplicates(["_race", "_horse"]), on=["_race", "_horse"], how="left", validate="one_to_one")

    need = {"canonical_horse_id", "race_date", "finish_position"}
    parts = []
    for z in pd.read_csv(perf026, usecols=lambda c: c in need, chunksize=500000):
        z["race_date"] = pd.to_datetime(z["race_date"], errors="coerce")
        z["finish_position"] = pd.to_numeric(z["finish_position"], errors="coerce")
        z = z[z["finish_position"].between(1, 99)].dropna(subset=["canonical_horse_id", "race_date"])
        z = z[z["race_date"].dt.year <= args.max_year]
        parts.append(z)
    if not parts:
        raise RuntimeError("STOP_NO_CLEAN_PLACING_HISTORY")
    h = pd.concat(parts, ignore_index=True).sort_values(["canonical_horse_id", "race_date"])
    h = (
        h.groupby(["canonical_horse_id", "race_date"], as_index=False)
        .agg(finish_position=("finish_position", lambda s: s.iloc[0] if s.nunique() == 1 else np.nan))
        .dropna()
    )
    by_horse = {k: g[["race_date", "finish_position"]].sort_values("race_date") for k, g in h.groupby("canonical_horse_id")}

    def clean_feats(row):
        g = by_horse.get(row["_horse"])
        if g is None:
            return pd.Series([np.nan] * 5)
        q = g[g["race_date"] < row["race_date"]].tail(5)["finish_position"].to_numpy(float)
        if len(q) == 0:
            return pd.Series([np.nan] * 5)
        return pd.Series([q.mean(), q[-1], float(q[-1] == 1), float(q[-1] <= 3), float(len(q))])

    clean = x[["_horse", "race_date"]].apply(clean_feats, axis=1)
    clean.columns = ["clean_finish_mean5", "clean_last_finish", "clean_last_won", "clean_last_top3", "clean_finish_hist_n"]
    x = pd.concat([x.reset_index(drop=True), clean.reset_index(drop=True)], axis=1)

    # The approved plan forbids row-level filtering of mixed sealed-year files.
    # LAB031 context is therefore header-audited only here; Stage016-family candidates
    # are marked fail-closed unless a sealed-year-free context partition is supplied
    # in a later, separately approved plan.
    x.attrs["context_status"] = "BLOCKED_MIXED_SEALED_YEAR_SOURCE"
    x.attrs["context_reason"] = "LAB031 context authority is not a sealed-year-free admitted artifact for this run"

    for col in stage011_features:
        if col not in x.columns:
            raise RuntimeError(f"STOP_FEATURE_MISSING: {col}")
    if x.duplicated(["_race", "_horse"]).any():
        raise RuntimeError("STOP_DUPLICATE_RUNNERS")
    if not x["y"].isin([0, 1]).all():
        raise RuntimeError("STOP_INVALID_TARGET")
    if (x.groupby("_race")["y"].sum() != 1).any():
        raise RuntimeError("STOP_MULTI_OR_ZERO_WINNER_RACE")
    return x


def model_for(candidate):
    if candidate in {"A", "B", "H"}:
        return HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=5, l2_regularization=1, random_state=42)
    if candidate in {"C", "E"}:
        return Pipeline(
            [
                ("imp", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("m", LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000, random_state=42)),
            ]
        )
    if candidate in {"D", "F"}:
        return Pipeline(
            [
                ("imp", SimpleImputer(strategy="median")),
                ("m", RandomForestClassifier(n_estimators=500, min_samples_leaf=20, max_features="sqrt", random_state=42, n_jobs=-1)),
            ]
        )
    raise KeyError(candidate)


def raw_scores(model, x_test):
    if hasattr(model, "decision_function"):
        return model.decision_function(x_test)
    p = model.predict_proba(x_test)[:, 1]
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def validate_scores(df, candidate, year, expected_keys):
    got = df[["_race", "_horse", "y"]].sort_values(["_race", "_horse"]).reset_index(drop=True)
    exp = expected_keys.sort_values(["_race", "_horse"]).reset_index(drop=True)
    if len(got) != len(exp) or not got.equals(exp):
        raise RuntimeError(f"STOP_UNIVERSE_MISMATCH_{candidate}_{year}")
    if not np.isfinite(df["p"].to_numpy(float)).all() or not df["p"].between(0, 1).all():
        raise RuntimeError(f"STOP_INVALID_PROBABILITY_{candidate}_{year}")
    mass = (df.groupby("_race")["p"].sum() - 1).abs().max()
    if float(mass) > MASS_TOL:
        raise RuntimeError(f"STOP_RACE_MASS_{candidate}_{year}: {mass}")
    if (df.groupby("_race")["y"].sum() != 1).any():
        raise RuntimeError(f"STOP_WINNER_COUNT_{candidate}_{year}")


def score_model(candidate, model, train, test, features, feature_hash, source_hash, git, expected_keys, year):
    x_train = train[features].replace([np.inf, -np.inf], np.nan)
    x_test = test[features].replace([np.inf, -np.inf], np.nan)
    model.fit(x_train, train["y"].astype(int))
    raw = raw_scores(model, x_test)
    out = test[["_race", "_horse", "race_date", "year", "y"]].copy()
    out["raw"] = raw
    out["p"] = out.groupby("_race")["raw"].transform(lambda s: softmax(s.to_numpy(float)))
    out["model_id"] = f"CODEX_ISSUE5_{candidate}"
    out["git_sha"] = git
    out["random_state"] = 42
    out["train_year_lt"] = year
    out["feature_names_sha256"] = feature_hash
    out["input_file_sha256"] = source_hash
    out["n_train_rows"] = len(train)
    out["n_test_rows"] = len(test)
    out["evidence_class"] = EVIDENCE_CLASS
    validate_scores(out, candidate, year, expected_keys)
    return out


def ensemble_scores(candidate, frames, git, feature_hash, source_hash, train_rows, year, expected_keys):
    base = frames[0][["_race", "_horse", "race_date", "year", "y"]].copy()
    probs = [f.sort_values(["_race", "_horse"])["p"].to_numpy(float) for f in frames]
    sorted_base = base.sort_values(["_race", "_horse"]).reset_index(drop=True)
    sorted_base["p"] = np.mean(np.vstack(probs), axis=0)
    sorted_base["p"] = sorted_base.groupby("_race")["p"].transform(lambda s: s / s.sum())
    sorted_base["raw"] = np.log(np.clip(sorted_base["p"], 1e-15, 1.0))
    sorted_base["model_id"] = f"CODEX_ISSUE5_{candidate}"
    sorted_base["git_sha"] = git
    sorted_base["random_state"] = 42
    sorted_base["train_year_lt"] = year
    sorted_base["feature_names_sha256"] = feature_hash
    sorted_base["input_file_sha256"] = source_hash
    sorted_base["n_train_rows"] = train_rows
    sorted_base["n_test_rows"] = len(sorted_base)
    sorted_base["evidence_class"] = EVIDENCE_CLASS
    validate_scores(sorted_base, candidate, year, expected_keys)
    return sorted_base


def race_metrics(df):
    losses = []
    ranks = []
    winner_ps = []
    for _, g in df.groupby("_race", sort=False):
        g = g.sort_values("p", ascending=False).reset_index(drop=True)
        winner_idx = np.flatnonzero(g["y"].to_numpy(int) == 1)
        if len(winner_idx) != 1:
            raise RuntimeError("STOP_METRIC_WINNER_COUNT")
        rank = int(winner_idx[0]) + 1
        p_win = float(g.loc[rank - 1, "p"])
        ranks.append(rank)
        winner_ps.append(p_win)
        losses.append(-math.log(max(p_win, 1e-15)))
    ranks = np.asarray(ranks)
    return {
        "races": int(df["_race"].nunique()),
        "runners": int(len(df)),
        "race_log_loss": float(np.mean(losses)),
        "runner_brier": float(np.mean((df["p"].to_numpy(float) - df["y"].to_numpy(float)) ** 2)),
        "top1": float(np.mean(ranks <= 1)),
        "top2": float(np.mean(ranks <= 2)),
        "top3": float(np.mean(ranks <= 3)),
        "mrr": float(np.mean(1.0 / ranks)),
        "mean_winner_rank": float(np.mean(ranks)),
        "mean_winner_probability": float(np.mean(winner_ps)),
        "max_race_mass_error": float((df.groupby("_race")["p"].sum() - 1).abs().max()),
    }


def race_losses(df):
    rows = []
    for race, g in df.groupby("_race", sort=False):
        p = float(g.loc[g["y"].eq(1), "p"].iloc[0])
        rows.append((race, -math.log(max(p, 1e-15))))
    return pd.DataFrame(rows, columns=["_race", "loss"])


def calibration_rows(df, candidate, year):
    out = []
    p = df["p"].to_numpy(float)
    bins = np.minimum(np.floor(p * 10).astype(int), 9)
    for i in range(10):
        s = df[bins == i]
        label = f"[{i/10:.1f},{(i+1)/10:.1f}{']' if i == 9 else ')'}"
        out.append(
            {
                "candidate": candidate,
                "year": year,
                "bin": label,
                "count": int(len(s)),
                "mean_predicted_probability": float(s["p"].mean()) if len(s) else np.nan,
                "observed_win_rate": float(s["y"].mean()) if len(s) else np.nan,
            }
        )
    return out


def cohort_rows(df, candidate, year):
    rows = []
    work = df.copy()
    work["field_size"] = work.groupby("_race")["_horse"].transform("count")
    work["field_size_band"] = pd.cut(work["field_size"], bins=[0, 8, 12, 16, 99], labels=["<=8", "9-12", "13-16", "17+"])
    if "hist_runs" in work.columns:
        work["history_depth_band"] = pd.cut(work["hist_runs"].fillna(-1), bins=[-2, 0, 2, 5, 999], labels=["0", "1-2", "3-5", "6+"])
    else:
        work["history_depth_band"] = "NA"
    work["probability_band"] = pd.cut(work["p"], bins=[0, 0.05, 0.1, 0.2, 1.0], labels=["0-5", "5-10", "10-20", "20+"], include_lowest=True)
    for col in ["field_size_band", "history_depth_band", "probability_band"]:
        for band, g in work.groupby(col, observed=False):
            if len(g) == 0:
                continue
            m = race_metrics(g) if (g.groupby("_race")["y"].sum() == 1).all() else None
            rows.append(
                {
                    "candidate": candidate,
                    "year": year,
                    "cohort": col,
                    "band": str(band),
                    "runners": int(len(g)),
                    "winner_rate": float(g["y"].mean()),
                    "mean_probability": float(g["p"].mean()),
                    "race_log_loss_if_complete_races": m["race_log_loss"] if m else np.nan,
                }
            )
    return rows


def bootstrap_ci(loss_by_candidate):
    rng = np.random.default_rng(RNG_SEED)
    baseline = loss_by_candidate["A"].rename(columns={"loss": "loss_A"})
    rows = []
    for cand, losses in loss_by_candidate.items():
        if cand == "A":
            continue
        merged = baseline.merge(losses.rename(columns={"loss": "loss_c"}), on=["year", "_race"], validate="one_to_one")
        merged["delta"] = merged["loss_A"] - merged["loss_c"]
        point = float(merged["delta"].mean())
        by_year = {y: g["delta"].to_numpy(float) for y, g in merged.groupby("year")}
        draws = []
        for _ in range(10000):
            vals = []
            for arr in by_year.values():
                vals.append(rng.choice(arr, size=len(arr), replace=True))
            draws.append(float(np.concatenate(vals).mean()))
        lo, hi = np.quantile(draws, [0.025, 0.975])
        rows.append({"candidate": cand, "delta_ll": point, "ci_lower": float(lo), "ci_upper": float(hi), "bootstrap_resamples": 10000, "seed": RNG_SEED})
    return rows


def markdown_table(df):
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.12g}")
        else:
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else str(x))
    cols = list(display.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(lines)


def main():
    args = parse_args()
    if args.max_year != 2024 or args.evidence_class != EVIDENCE_CLASS:
        raise RuntimeError("STOP_SCOPE_NOT_APPROVED")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage011 = json.loads(Path(args.stage011_report).read_text())
    if stage011.get("status") != "PASS":
        raise RuntimeError("STOP_STAGE011_REPORT_NOT_PASS")
    stage011_features = list(stage011["features"])
    x = build_matrix(args, stage011_features)
    f0 = stage011_features
    f1 = stage011_features + STAGE016_FAMILY
    feature_sets = {"A": f0, "B": f1, "C": f0, "D": f0, "E": f1, "F": f1}
    candidates = [c.strip() for c in args.candidate_budget.split(",") if c.strip()]
    git = git_sha()
    source_hash = sha256_json(
        {
            "stage006": sha256_file(args.stage006_warehouse),
            "d45": sha256_file(args.d45_matrix),
            "context": x.attrs.get("context_status", "UNKNOWN"),
            "perf026": sha256_file(args.perf026),
        }
    )

    expected = {}
    for year in YEARS:
        path = Path(args.stage011_scores_dir) / f"STAGE011_RUNNER_PROBABILITIES_{year}.csv"
        e = pd.read_csv(path, usecols=["_race", "_horse", "y"])
        expected[year] = e

    all_scores = {year: {} for year in YEARS}
    year_rows = []
    manifest_rows = []
    calibration = []
    cohorts = []
    loss_frames = {}
    status_rows = []

    for candidate in candidates:
        if candidate == "G":
            continue
        if candidate == "H":
            status_rows.append({"candidate": "H", "status": "NOT_RUN_NO_FROZEN_FIELDS", "reason": "LAB239_FROZEN_ARCHITECTURE_NO_CHALLENGER"})
            continue
        if candidate in {"B", "E", "F"} and x.attrs.get("context_status") != "PASS":
            status_rows.append({"candidate": candidate, "status": "FAIL_CLOSED_CONTEXT_BLOCKED", "reason": x.attrs.get("context_reason", "context blocked")})
            continue
        features = feature_sets[candidate]
        feature_hash = sha256_json(features)
        status_rows.append({"candidate": candidate, "status": "RUN", "reason": ""})
        for year in YEARS:
            train = x[x["year"] < year].copy()
            test = x[x["year"] == year].copy()
            scored = score_model(candidate, model_for(candidate), train, test, features, feature_hash, source_hash, git, expected[year], year)
            all_scores[year][candidate] = scored
            m = race_metrics(scored)
            year_rows.append({"candidate": candidate, "year": year, **m})
            calibration.extend(calibration_rows(scored, candidate, year))
            cohorts.extend(cohort_rows(scored.merge(test[["_race", "_horse", "hist_runs"]], on=["_race", "_horse"], how="left"), candidate, year))
            lf = race_losses(scored)
            lf["year"] = year
            loss_frames.setdefault(candidate, []).append(lf)
        manifest_rows.append(
            {
                "candidate": candidate,
                "features": "|".join(features),
                "feature_count": len(features),
                "feature_names_sha256": feature_hash,
                "learner": "HGB" if candidate in {"A", "B"} else "LOGIT" if candidate in {"C", "E"} else "RF",
                "status": "RUN",
            }
        )

    if {"B", "E", "F"}.issubset(all_scores[2022].keys()):
        status_rows.append({"candidate": "G", "status": "RUN", "reason": ""})
        fhash = sha256_json({"ensemble": ["B", "E", "F"], "weights": [1 / 3, 1 / 3, 1 / 3]})
        for year in YEARS:
            train_rows = int(x[x["year"] < year].shape[0])
            frames = [all_scores[year][c] for c in ["B", "E", "F"]]
            scored = ensemble_scores("G", frames, git, fhash, source_hash, train_rows, year, expected[year])
            all_scores[year]["G"] = scored
            m = race_metrics(scored)
            year_rows.append({"candidate": "G", "year": year, **m})
            calibration.extend(calibration_rows(scored, "G", year))
            cohorts.extend(cohort_rows(scored.merge(x[x["year"] == year][["_race", "_horse", "hist_runs"]], on=["_race", "_horse"], how="left"), "G", year))
            lf = race_losses(scored)
            lf["year"] = year
            loss_frames.setdefault("G", []).append(lf)
        manifest_rows.append({"candidate": "G", "features": "ENSEMBLE_B_E_F", "feature_count": len(f1), "feature_names_sha256": fhash, "learner": "ENSEMBLE_EQUAL_WEIGHT", "status": "RUN"})
    else:
        status_rows.append({"candidate": "G", "status": "NOT_RUN_DEPENDENCY_FAILED", "reason": "B_E_F_NOT_ALL_AVAILABLE"})

    for cand, frames in loss_frames.items():
        loss_frames[cand] = pd.concat(frames, ignore_index=True)

    year_metrics = pd.DataFrame(year_rows).sort_values(["candidate", "year"])
    baseline = year_metrics[year_metrics["candidate"] == "A"][["year", "race_log_loss", "top1"]].rename(columns={"race_log_loss": "stage011_ll", "top1": "stage011_top1"})
    year_metrics = year_metrics.merge(baseline, on="year", how="left")
    year_metrics["delta_ll_vs_stage011"] = year_metrics["stage011_ll"] - year_metrics["race_log_loss"]
    year_metrics["delta_top1_vs_stage011"] = year_metrics["top1"] - year_metrics["stage011_top1"]

    bootstrap = pd.DataFrame(bootstrap_ci(loss_frames))
    weighted = (
        year_metrics.groupby("candidate")
        .apply(lambda g: pd.Series({
            "weighted_ll": np.average(g["race_log_loss"], weights=g["races"]),
            "weighted_brier": np.average(g["runner_brier"], weights=g["runners"]),
            "weighted_top1": np.average(g["top1"], weights=g["races"]),
            "weighted_top2": np.average(g["top2"], weights=g["races"]),
            "weighted_top3": np.average(g["top3"], weights=g["races"]),
            "years_beating_stage011": int((g["delta_ll_vs_stage011"] > 0).sum()),
            "max_yearly_ll_worse_than_stage011": float((-g["delta_ll_vs_stage011"]).max()),
        }))
        .reset_index()
    )
    weighted = weighted.merge(bootstrap, on="candidate", how="left")
    weighted["passes_promotion"] = False
    for idx, row in weighted.iterrows():
        if row["candidate"] == "A":
            continue
        g = year_metrics[year_metrics["candidate"] == row["candidate"]]
        passes = (
            row["years_beating_stage011"] >= 2
            and row["max_yearly_ll_worse_than_stage011"] <= 0.005
            and (year_metrics[year_metrics["candidate"] == "A"]["race_log_loss"].mean() - row["weighted_ll"]) >= 0.005
            and pd.notna(row.get("ci_lower"))
            and row["ci_lower"] > 0.0
            and row["weighted_top1"] >= float(weighted.loc[weighted["candidate"] == "A", "weighted_top1"].iloc[0]) - 0.01
            and (g["races"].to_numpy() == year_metrics[year_metrics["candidate"] == "A"]["races"].to_numpy()).all()
            and (g["runners"].to_numpy() == year_metrics[year_metrics["candidate"] == "A"]["runners"].to_numpy()).all()
        )
        weighted.loc[idx, "passes_promotion"] = bool(passes)

    passing = weighted[weighted["passes_promotion"]].sort_values("weighted_ll")
    if len(passing):
        best_candidate = str(passing.iloc[0]["candidate"])
        verdict = "PROMOTE_RESEARCH_CHALLENGER"
    else:
        best_candidate = "A"
        verdict = "RETAIN_STAGE011"

    manifest = pd.DataFrame(manifest_rows).merge(pd.DataFrame(status_rows), on="candidate", how="outer", suffixes=("", "_budget"))
    manifest["status"] = manifest["status"].fillna(manifest["status_budget"])
    manifest = manifest.drop(columns=[c for c in ["status_budget"] if c in manifest.columns])

    year_metrics.to_csv(out_dir / "CODEX_BAKEOFF_YEAR_METRICS_20261010.csv", index=False)
    weighted.to_csv(out_dir / "CODEX_BAKEOFF_MODEL_SUMMARY_20261010.csv", index=False)
    pd.DataFrame(calibration).to_csv(out_dir / "CODEX_BAKEOFF_CALIBRATION_20261010.csv", index=False)
    pd.DataFrame(cohorts).to_csv(out_dir / "CODEX_BAKEOFF_COHORTS_20261010.csv", index=False)
    bootstrap.to_csv(out_dir / "CODEX_BAKEOFF_BOOTSTRAP_CI_20261010.csv", index=False)
    manifest.to_csv(out_dir / "CODEX_BAKEOFF_MODEL_MANIFEST_20261010.csv", index=False)

    score_cols = ["_race", "_horse", "race_date", "year", "y", "p", "model_id", "git_sha", "random_state", "train_year_lt", "feature_names_sha256", "input_file_sha256", "n_train_rows", "n_test_rows", "evidence_class"]
    for year in YEARS:
        pd.concat([all_scores[year][c][score_cols] for c in sorted(all_scores[year])], ignore_index=True).to_csv(out_dir / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv", index=False)

    audit = {
        "status": "PASS",
        "verdict": verdict,
        "best_candidate": best_candidate,
        "evidence_class": EVIDENCE_CLASS,
        "market_access": False,
        "profitability_tested": False,
        "sealed_2025_2026_access_in_successful_scoring": False,
        "sealed_year_note": "Final successful scoring admitted no 2025-2026 rows. LAB031 context was header-audited only in the successful run and Stage016-family candidates were fail-closed because the context authority is not a sealed-year-free admitted artifact.",
        "candidate_budget": candidates,
        "stage011_reference": stage011,
        "source_hash": source_hash,
        "git_sha": git,
    }
    (out_dir / "CODEX_BAKEOFF_AUDIT_20261010.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    report_lines = [
        "# CODEX Issue #5 Winning Model Results",
        "",
        f"Status: `{verdict}`",
        f"Best defensible model: `{best_candidate}`",
        "",
        "Evidence class: `REUSED_DEVELOPMENT`. These are not untouched holdout results.",
        "",
        "## Governance",
        "",
        "- Final successful scoring admitted no 2025-2026 rows. LAB031 context was header-audited only in the successful run and Stage016-family candidates were fail-closed because the context authority is not a sealed-year-free admitted artifact.",
        "- No market, SP, BSP, odds, profitability, threshold, staking, or return data were used.",
        "- All scored candidates were required to match 100% of the Stage011 primary race/runner universe.",
        "",
        "## Weighted Summary",
        "",
        markdown_table(weighted.sort_values("weighted_ll")),
        "",
        "## Year Metrics",
        "",
        markdown_table(year_metrics.sort_values(["year", "race_log_loss"])),
        "",
        "## Verdict",
        "",
    ]
    if verdict == "PROMOTE_RESEARCH_CHALLENGER":
        report_lines.append(f"`{best_candidate}` passes the predeclared reused-development promotion gates and is the strongest research challenger.")
    else:
        report_lines.append("No challenger passes the predeclared reused-development promotion gates. Stage011 remains the defensible retained model.")
    (Path("ai_review") / "CODEX_WINNING_MODEL_RESULTS.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"CODEX_ISSUE5_BAKEOFF=PASS VERDICT={verdict} BEST={best_candidate}")
    print(f"OUT={out_dir}")


if __name__ == "__main__":
    main()
