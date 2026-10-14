from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


LOCAL_RESEARCH_ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
BAKEOFF_DIR = LOCAL_RESEARCH_ROOT / "outputs/research/codex_issue5_winning_model"
STAGE006 = LOCAL_RESEARCH_ROOT / "outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT_DIR = Path("outputs/research/issue23_top1_winner_selection")
CURRENT_STATE = Path("ai_review/CURRENT_STATE.md")

YEARS = [2022, 2023, 2024]
BASELINE = "CODEX_ISSUE5_A"
STAGE016 = "CODEX_ISSUE5_B"
ROUTER = "ISSUE23_TOP1_ROUTER_2022_LOCKED"
RNG_SEED = 23
BOOTSTRAPS = 10_000

MODEL_LABELS = {
    "CODEX_ISSUE5_A": "Stage011 champion",
    "CODEX_ISSUE5_B": "Stage016 context challenger",
    "CODEX_ISSUE5_C": "Issue5 candidate C",
    "CODEX_ISSUE5_D": "Issue5 candidate D",
    "CODEX_ISSUE5_E": "Issue5 candidate E",
    "CODEX_ISSUE5_F": "Issue5 candidate F",
    "CODEX_ISSUE5_G": "Issue5 candidate G",
    ROUTER: "Issue23 2022-locked Stage011/Stage016 router",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_scores(bakeoff_dir: Path) -> pd.DataFrame:
    parts = []
    for year in YEARS:
        path = bakeoff_dir / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(
            path,
            usecols=["_race", "_horse", "race_date", "year", "y", "p", "model_id", "evidence_class"],
        )
        if frame["year"].nunique() != 1 or int(frame["year"].iloc[0]) != year:
            raise RuntimeError(f"Year mismatch in {path}")
        parts.append(frame)
    scores = pd.concat(parts, ignore_index=True)
    if scores["year"].max() > 2024:
        raise RuntimeError("Sealed-year violation: score files include post-2024 rows")
    if scores["model_id"].str.contains("sp|bsp|market|odds|price", case=False, regex=True).any():
        raise RuntimeError("Forbidden market-like model identifier present")
    return scores


def load_race_context(stage006: Path) -> pd.DataFrame:
    wanted = [
        "_race",
        "_horse",
        "year",
        "current_distance",
        "represented_field_size",
        "hist_runs",
        "clean_finish_hist_n",
        "days_since_last",
        "dist200_runs",
    ]
    header = pd.read_csv(stage006, nrows=0).columns.tolist()
    usecols = [c for c in wanted if c in header]
    missing_optional = sorted(set(wanted) - set(usecols))
    required = {"_race", "_horse", "year", "current_distance", "represented_field_size", "hist_runs"}
    missing_required = sorted(required - set(usecols))
    if missing_required:
        raise RuntimeError(f"Stage006 missing required diagnostic columns: {missing_required}")
    ctx = pd.read_csv(stage006, usecols=usecols)
    for col in missing_optional:
        ctx[col] = np.nan
    if ctx["year"].max() > 2024:
        raise RuntimeError("Sealed-year violation: Stage006 context includes post-2024 rows")
    ctx = ctx[ctx["year"].isin(YEARS)].copy()
    for col in usecols[3:]:
        ctx[col] = pd.to_numeric(ctx[col], errors="coerce")
    race = (
        ctx.groupby(["_race", "year"], as_index=False)
        .agg(
            current_distance=("current_distance", "median"),
            represented_field_size=("represented_field_size", "max"),
            median_hist_runs=("hist_runs", "median"),
            mean_hist_runs=("hist_runs", "mean"),
            median_clean_finish_hist_n=("clean_finish_hist_n", "median"),
            mean_days_since_last=("days_since_last", "mean"),
            runners_with_no_hist=("hist_runs", lambda s: int((pd.to_numeric(s, errors="coerce").fillna(0) <= 0).sum())),
            runners=("hist_runs", "size"),
            dist200_coverage_rate=("dist200_runs", lambda s: float(pd.to_numeric(s, errors="coerce").gt(0).mean())),
        )
    )
    race["no_history_rate"] = race["runners_with_no_hist"] / race["runners"]
    race["field_size_band"] = pd.cut(
        race["represented_field_size"],
        bins=[0, 8, 12, 99],
        labels=["small_<=8", "medium_9_12", "large_13+"],
        include_lowest=True,
    ).astype(str)
    race["distance_band"] = pd.cut(
        race["current_distance"],
        bins=[0, 1200, 1600, 10000],
        labels=["sprint_<=1200", "middle_1201_1600", "staying_1601+"],
        include_lowest=True,
    ).astype(str)
    race["history_band"] = pd.cut(
        race["median_hist_runs"],
        bins=[-1, 2, 7, 999],
        labels=["thin_hist_0_2", "medium_hist_3_7", "deep_hist_8+"],
        include_lowest=True,
    ).astype(str)
    return race


def validate_scores(scores: pd.DataFrame) -> dict:
    checks = {}
    for model_id, group in scores.groupby("model_id", sort=True):
        mass = group.groupby(["year", "_race"])["p"].sum()
        winners = group.groupby(["year", "_race"])["y"].sum()
        checks[model_id] = {
            "rows": int(len(group)),
            "races": int(group["_race"].nunique()),
            "max_probability_mass_error": float((mass - 1.0).abs().max()),
            "single_winner_races": bool((winners == 1).all()),
        }
        if not np.allclose(mass.to_numpy(), 1.0, atol=1e-12, rtol=0):
            raise RuntimeError(f"Probability mass violation for {model_id}")
        if not (winners == 1).all():
            raise RuntimeError(f"Winner-count violation for {model_id}")
    return checks


def race_view(scores: pd.DataFrame) -> pd.DataFrame:
    ordered = scores.sort_values(["model_id", "year", "_race", "p", "_horse"], ascending=[True, True, True, False, True])
    ordered["rank"] = ordered.groupby(["model_id", "year", "_race"]).cumcount() + 1
    winner = ordered[ordered["y"].eq(1)][["_race", "year", "model_id", "_horse", "p", "rank"]].rename(
        columns={"_horse": "winner_horse", "p": "winner_probability", "rank": "winner_rank"}
    )
    top = ordered[ordered["rank"].eq(1)][["_race", "year", "model_id", "_horse", "p", "y"]].rename(
        columns={"_horse": "selected_horse", "p": "selected_probability", "y": "selected_won"}
    )
    view = top.merge(winner, on=["_race", "year", "model_id"], how="inner", validate="one_to_one")
    return view


def model_year_metrics(runner_scores: pd.DataFrame, race_scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model_id, year), group in race_scores.groupby(["model_id", "year"], sort=True):
        runner = runner_scores[(runner_scores["model_id"].eq(model_id)) & (runner_scores["year"].eq(year))]
        rows.append(
            {
                "model_id": model_id,
                "model_label": MODEL_LABELS.get(model_id, model_id),
                "year": int(year),
                "races": int(len(group)),
                "runners": int(len(runner)),
                "winner_in_field_coverage": float(runner.groupby("_race")["y"].sum().eq(1).mean()),
                "race_log_loss": float(-np.log(group["winner_probability"].clip(lower=1e-15)).mean()),
                "runner_brier": float(((runner["p"] - runner["y"]) ** 2).mean()),
                "top1": float(group["selected_won"].mean()),
                "top2": float((group["winner_rank"] <= 2).mean()),
                "top3": float((group["winner_rank"] <= 3).mean()),
                "mrr": float((1.0 / group["winner_rank"]).mean()),
                "mean_winner_rank": float(group["winner_rank"].mean()),
                "mean_winner_probability": float(group["winner_probability"].mean()),
            }
        )
    return pd.DataFrame(rows)


def wilson_ci(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (np.nan, np.nan)
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    return ((centre - margin) / denom, (centre + margin) / denom)


def calibration_table(scores: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model_id, year), group in scores.groupby(["model_id", "year"], sort=True):
        ranked = group.copy()
        ranked["bin"] = pd.qcut(ranked["p"].rank(method="first"), 10, labels=False) + 1
        for bin_id, b in ranked.groupby("bin", sort=True):
            rows.append(
                {
                    "model_id": model_id,
                    "year": int(year),
                    "bin": int(bin_id),
                    "runners": int(len(b)),
                    "mean_probability": float(b["p"].mean()),
                    "observed_win_rate": float(b["y"].mean()),
                    "calibration_gap": float(b["y"].mean() - b["p"].mean()),
                }
            )
    return pd.DataFrame(rows)


def learn_router_policy(race_scores: pd.DataFrame, race_ctx: pd.DataFrame) -> pd.DataFrame:
    dev = race_scores[race_scores["year"].eq(2022)].merge(
        race_ctx,
        on=["_race", "year"],
        how="left",
        validate="many_to_one",
    )
    a = dev[dev["model_id"].eq(BASELINE)].copy()
    b = dev[dev["model_id"].eq(STAGE016)].copy()
    paired = a.merge(
        b,
        on=["_race", "year", "field_size_band", "distance_band", "history_band"],
        suffixes=("_a", "_b"),
        validate="one_to_one",
    )
    rows = []
    for keys, g in paired.groupby(["field_size_band", "distance_band", "history_band"], dropna=False, sort=True):
        races = len(g)
        top1_a = float(g["selected_won_a"].mean())
        top1_b = float(g["selected_won_b"].mean())
        ll_a = float(-np.log(g["winner_probability_a"].clip(lower=1e-15)).mean())
        ll_b = float(-np.log(g["winner_probability_b"].clip(lower=1e-15)).mean())
        use_b = races >= 50 and (top1_b - top1_a) >= 0.03 and ll_b <= ll_a + 0.03
        rows.append(
            {
                "field_size_band": keys[0],
                "distance_band": keys[1],
                "history_band": keys[2],
                "development_year": 2022,
                "development_races": races,
                "stage011_top1": top1_a,
                "stage016_top1": top1_b,
                "stage016_minus_stage011_top1": top1_b - top1_a,
                "stage011_ll": ll_a,
                "stage016_ll": ll_b,
                "stage016_minus_stage011_ll": ll_b - ll_a,
                "router_choice": STAGE016 if use_b else BASELINE,
                "policy_rule": "use Stage016 only if 2022 slice has >=50 races, Top1 gain >=0.03, and LL no worse than +0.03",
            }
        )
    return pd.DataFrame(rows)


def apply_router(scores: pd.DataFrame, race_ctx: pd.DataFrame, policy: pd.DataFrame) -> pd.DataFrame:
    keys = ["field_size_band", "distance_band", "history_band"]
    choices = policy[keys + ["router_choice"]]
    ctx = race_ctx[["_race", "year"] + keys]
    ab = scores[scores["model_id"].isin([BASELINE, STAGE016])].merge(
        ctx,
        on=["_race", "year"],
        how="left",
        validate="many_to_one",
    )
    ab = ab.merge(choices, on=keys, how="left", validate="many_to_one")
    ab["router_choice"] = ab["router_choice"].fillna(BASELINE)
    routed = ab[ab["model_id"].eq(ab["router_choice"])].copy()
    routed["model_id"] = ROUTER
    routed["evidence_class"] = "REUSED_DEVELOPMENT_ROUTER_2022_LOCKED"
    return routed[scores.columns]


def paired_bootstrap(race_scores: pd.DataFrame, models: Iterable[str]) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    base = race_scores[race_scores["model_id"].eq(BASELINE)]
    for model_id in models:
        if model_id == BASELINE:
            continue
        model = race_scores[race_scores["model_id"].eq(model_id)]
        paired = base.merge(
            model,
            on=["_race", "year"],
            suffixes=("_base", "_model"),
            validate="one_to_one",
        )
        for year, g in paired.groupby("year", sort=True):
            n = len(g)
            top_diff = g["selected_won_model"].to_numpy(float) - g["selected_won_base"].to_numpy(float)
            ll_diff = (
                -np.log(g["winner_probability_base"].clip(lower=1e-15)).to_numpy(float)
                + np.log(g["winner_probability_model"].clip(lower=1e-15)).to_numpy(float)
            )
            # Positive ll_diff means model improves log loss over Stage011.
            idx = rng.integers(0, n, size=(BOOTSTRAPS, n))
            top_samples = top_diff[idx].mean(axis=1)
            ll_samples = ll_diff[idx].mean(axis=1)
            rows.append(
                {
                    "model_id": model_id,
                    "year": int(year),
                    "paired_races": int(n),
                    "top1_diff_vs_stage011": float(top_diff.mean()),
                    "top1_diff_ci_lower": float(np.quantile(top_samples, 0.025)),
                    "top1_diff_ci_upper": float(np.quantile(top_samples, 0.975)),
                    "ll_gain_vs_stage011": float(ll_diff.mean()),
                    "ll_gain_ci_lower": float(np.quantile(ll_samples, 0.025)),
                    "ll_gain_ci_upper": float(np.quantile(ll_samples, 0.975)),
                    "bootstrap_resamples": BOOTSTRAPS,
                    "seed": RNG_SEED,
                }
            )
    return pd.DataFrame(rows)


def error_slices(race_scores: pd.DataFrame, race_ctx: pd.DataFrame) -> pd.DataFrame:
    baseline = race_scores[race_scores["model_id"].eq(BASELINE)].merge(
        race_ctx,
        on=["_race", "year"],
        how="left",
        validate="many_to_one",
    )
    rows = []
    for year, ydf in baseline.groupby("year", sort=True):
        for family in ["field_size_band", "distance_band", "history_band"]:
            for value, g in ydf.groupby(family, dropna=False, sort=True):
                rows.append(
                    {
                        "year": int(year),
                        "slice_family": family,
                        "slice_value": str(value),
                        "races": int(len(g)),
                        "stage011_top1": float(g["selected_won"].mean()),
                        "stage011_errors": int((~g["selected_won"].astype(bool)).sum()),
                        "stage011_ll": float(-np.log(g["winner_probability"].clip(lower=1e-15)).mean()),
                        "mean_winner_rank": float(g["winner_rank"].mean()),
                        "mean_winner_probability": float(g["winner_probability"].mean()),
                        "mean_selected_probability": float(g["selected_probability"].mean()),
                    }
                )
    return pd.DataFrame(rows)


def top1_ci_table(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in metrics.itertuples(index=False):
        lo, hi = wilson_ci(round(row.top1 * row.races), row.races)
        rows.append(
            {
                "model_id": row.model_id,
                "year": int(row.year),
                "races": int(row.races),
                "top1": float(row.top1),
                "top1_ci_lower": lo,
                "top1_ci_upper": hi,
            }
        )
    return pd.DataFrame(rows)


def write_current_state(path: Path, summary: pd.DataFrame, bootstrap: pd.DataFrame, policy: pd.DataFrame) -> None:
    s2023 = summary[(summary["year"].eq(2023)) & (summary["model_id"].isin([BASELINE, STAGE016, ROUTER]))]
    def metric(model: str, col: str, year: int = 2023) -> float:
        return float(summary[(summary["model_id"].eq(model)) & (summary["year"].eq(year))][col].iloc[0])

    router_2023 = bootstrap[(bootstrap["model_id"].eq(ROUTER)) & (bootstrap["year"].eq(2023))].iloc[0]
    b_2023 = bootstrap[(bootstrap["model_id"].eq(STAGE016)) & (bootstrap["year"].eq(2023))].iloc[0]
    use_b_slices = int(policy["router_choice"].eq(STAGE016).sum())
    g_weighted_top1 = float(
        np.average(
            summary[summary["model_id"].eq("CODEX_ISSUE5_G")]["top1"],
            weights=summary[summary["model_id"].eq("CODEX_ISSUE5_G")]["races"],
        )
    )
    g_weighted_ll = float(
        np.average(
            summary[summary["model_id"].eq("CODEX_ISSUE5_G")]["race_log_loss"],
            weights=summary[summary["model_id"].eq("CODEX_ISSUE5_G")]["races"],
        )
    )
    a_weighted_ll = float(
        np.average(
            summary[summary["model_id"].eq(BASELINE)]["race_log_loss"],
            weights=summary[summary["model_id"].eq(BASELINE)]["races"],
        )
    )
    text = f"""# EDGEiQ Research - Current Decision

Date: 2026-10-13

## Champion

Stage011 remains the frozen research champion.

## Issue #23 Winner-Selection Experiment

Objective: improve race-level Top-1 winner selection without pricing, betting, market, SP/BSP, profitability research, production changes, or sealed 2025-2026 access.

Evidence class: REUSED_DEVELOPMENT. The experiment used existing admitted 2022-2024 Issue5 runner scores and Stage006 race-state diagnostics only.

Primary metric: one deterministic highest-probability runner per race, ties broken by probability descending then horse id ascending.

### Stage011 vs Stage016

- 2022 Stage011 Top-1: {metric(BASELINE, 'top1', 2022):.6f}; Stage016 Top-1: {metric(STAGE016, 'top1', 2022):.6f}.
- 2023 Stage011 Top-1: {metric(BASELINE, 'top1', 2023):.6f}; Stage016 Top-1: {metric(STAGE016, 'top1', 2023):.6f}.
- 2023 Stage016 paired Top-1 difference vs Stage011: {b_2023.top1_diff_vs_stage011:.6f} [{b_2023.top1_diff_ci_lower:.6f}, {b_2023.top1_diff_ci_upper:.6f}].
- 2023 Stage016 LL gain vs Stage011: {b_2023.ll_gain_vs_stage011:.6f} [{b_2023.ll_gain_ci_lower:.6f}, {b_2023.ll_gain_ci_upper:.6f}].

Candidate G had the highest weighted Top-1 across 2022-2024 ({g_weighted_top1:.6f}), but failed the log-loss guardrail badly: weighted LL {g_weighted_ll:.6f} versus Stage011 {a_weighted_ll:.6f}. It is not a defensible champion replacement.

### Controlled Challenger

Challenger: `ISSUE23_TOP1_ROUTER_2022_LOCKED`.

Predeclared rule: use Stage016 for a race-state slice only when 2022 development evidence has at least 50 races, Stage016 Top-1 exceeds Stage011 by at least 0.03, and Stage016 race log loss is no worse than Stage011 by more than 0.03. Otherwise use Stage011.

Router selected Stage016 in {use_b_slices} race-state slices.

- 2023 router Top-1: {metric(ROUTER, 'top1', 2023):.6f}.
- 2023 router paired Top-1 difference vs Stage011: {router_2023.top1_diff_vs_stage011:.6f} [{router_2023.top1_diff_ci_lower:.6f}, {router_2023.top1_diff_ci_upper:.6f}].
- 2023 router LL gain vs Stage011: {router_2023.ll_gain_vs_stage011:.6f} [{router_2023.ll_gain_ci_lower:.6f}, {router_2023.ll_gain_ci_upper:.6f}].

## Verdict

NO-GO for champion replacement.

Stage016 improved 2023 Top-1 and log loss on reused development evidence, but it lost Top-1 in 2022 and was already below the prior promotion threshold. The Issue23 router did not produce a robust enough 2023 Top-1 improvement to justify replacing Stage011.

## Files

- `scripts/research/run_issue23_top1_winner_selection.py`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_MODEL_SUMMARY.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_BY_YEAR.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_TOP1_CI.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_PAIRED_BOOTSTRAP.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_ROUTER_POLICY.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_PER_RACE_SELECTIONS.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_STAGE011_TOP1_ERROR_SLICES.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_CALIBRATION.csv`
- `outputs/research/issue23_top1_winner_selection/ISSUE23_AUDIT.json`

## Reproduction Command

`python scripts/research/run_issue23_top1_winner_selection.py`

## Next Work

Do not run another learner comparison on the same feature set. A future approved experiment should require a specifically named non-market, point-in-time feature family with certified coverage, or a genuinely unexposed evaluation window.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bakeoff-dir", type=Path, default=BAKEOFF_DIR)
    parser.add_argument("--stage006", type=Path, default=STAGE006)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--current-state", type=Path, default=CURRENT_STATE)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    scores = load_scores(args.bakeoff_dir)
    checks = validate_scores(scores)
    race_ctx = load_race_context(args.stage006)

    base_race_scores = race_view(scores)
    policy = learn_router_policy(base_race_scores, race_ctx)
    routed_scores = apply_router(scores, race_ctx, policy)
    combined_scores = pd.concat([scores, routed_scores], ignore_index=True)
    combined_race_scores = race_view(combined_scores)

    summary = model_year_metrics(combined_scores, combined_race_scores)
    top1_ci = top1_ci_table(summary)
    bootstrap = paired_bootstrap(combined_race_scores, [STAGE016, ROUTER])
    calibration = calibration_table(combined_scores[combined_scores["model_id"].isin([BASELINE, STAGE016, ROUTER])])
    errors = error_slices(combined_race_scores, race_ctx)

    per_race = combined_race_scores[
        combined_race_scores["model_id"].isin([BASELINE, STAGE016, ROUTER])
    ].merge(race_ctx, on=["_race", "year"], how="left", validate="many_to_one")

    summary.to_csv(args.output_dir / "ISSUE23_TOP1_BY_YEAR.csv", index=False)
    top1_ci.to_csv(args.output_dir / "ISSUE23_TOP1_CI.csv", index=False)
    bootstrap.to_csv(args.output_dir / "ISSUE23_PAIRED_BOOTSTRAP.csv", index=False)
    policy.to_csv(args.output_dir / "ISSUE23_ROUTER_POLICY.csv", index=False)
    per_race.to_csv(args.output_dir / "ISSUE23_PER_RACE_SELECTIONS.csv", index=False)
    errors.to_csv(args.output_dir / "ISSUE23_STAGE011_TOP1_ERROR_SLICES.csv", index=False)
    calibration.to_csv(args.output_dir / "ISSUE23_CALIBRATION.csv", index=False)

    baseline_by_year = summary[summary["model_id"].eq(BASELINE)].set_index("year")["top1"]
    summary_rows = []
    for model_id, g in summary.groupby("model_id", sort=True):
        top1_by_year = g.set_index("year")["top1"]
        summary_rows.append(
            {
                "model_id": model_id,
                "model_label": MODEL_LABELS.get(model_id, model_id),
                "weighted_races": int(g["races"].sum()),
                "weighted_top1": float(np.average(g["top1"], weights=g["races"])),
                "weighted_ll": float(np.average(g["race_log_loss"], weights=g["races"])),
                "weighted_brier": float(np.average(g["runner_brier"], weights=g["runners"])),
                "years_top1_beats_stage011": int((top1_by_year > baseline_by_year).sum())
                if model_id != BASELINE
                else 0,
            }
        )
    model_summary = pd.DataFrame(summary_rows)
    model_summary.to_csv(args.output_dir / "ISSUE23_TOP1_MODEL_SUMMARY.csv", index=False)

    audit = {
        "status": "PASS",
        "issue": 23,
        "objective": "race-level Top-1 winner selection",
        "evidence_class": "REUSED_DEVELOPMENT",
        "years": YEARS,
        "sealed_2025_2026_accessed": False,
        "market_sp_bsp_price_columns_used": False,
        "production_modified": False,
        "frozen_artifacts_modified": False,
        "source_files": {
            "bakeoff_dir": str(args.bakeoff_dir),
            "stage006": str(args.stage006),
            "stage006_sha256": sha256_file(args.stage006),
            "score_files_sha256": {
                str(year): sha256_file(args.bakeoff_dir / f"CODEX_BAKEOFF_RUNNER_SCORES_{year}.csv")
                for year in YEARS
            },
        },
        "score_validation": checks,
        "router_policy": {
            "development_year": 2022,
            "selection_rule": "Stage016 only when slice has >=50 races, Top1 gain >=0.03, and LL no worse than +0.03; otherwise Stage011",
            "stage016_slices_selected": int(policy["router_choice"].eq(STAGE016).sum()),
            "total_slices": int(len(policy)),
        },
        "verdict": "NO_GO_RETAIN_STAGE011",
    }
    (args.output_dir / "ISSUE23_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    write_current_state(args.current_state, summary, bootstrap, policy)
    print(json.dumps({"status": "PASS", "output_dir": str(args.output_dir), "verdict": audit["verdict"]}, indent=2))


if __name__ == "__main__":
    main()
