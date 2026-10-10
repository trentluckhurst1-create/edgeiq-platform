"""Read-only Stage011 baseline drift audit. Never fits or scores a model.

Only reads the existing Stage011 reproduction report and runner-probability CSVs
for 2022–2024. Winner target in these artifacts is named 'y', NOT 'winner'.
No market, SP, BSP, odds, prices, sealed-year or mixed-year inputs.
"""
from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
DIR = ROOT / "outputs/research/model_v2/stage011_reproduction"
EXPECTED = {2022: (612, 2.125060402398), 2023: (2396, 2.131427427909), 2024: (2402, 2.102222925037)}
NEEDED = {"_race", "_horse", "evaluation_year", "training_year_max", "y", "p", "evidence_class"}
TOL = 1e-12

def stop(message):
    raise RuntimeError("STOP: " + message)

def main():
    report_file = DIR / "STAGE011_REPRODUCTION_REPORT.json"
    if not report_file.is_file():
        stop("missing frozen reproduction report")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        stop("Stage011 reproduction report not PASS")
    print("===== STAGE011 BASELINE DRIFT AUDIT (READ ONLY) =====")
    for year, (expected_races, expected_ll) in EXPECTED.items():
        path = DIR / f"STAGE011_RUNNER_PROBABILITIES_{year}.csv"
        if not path.is_file():
            stop(f"missing frozen runner probabilities for {year}")
        # Explicit usecols prevents access to unrelated fields.
        frame = pd.read_csv(path, usecols=lambda c: c in NEEDED)
        missing = NEEDED - set(frame.columns)
        if missing:
            stop(f"{year} missing required columns {sorted(missing)}")
        if frame.empty or frame[NEEDED].isna().any().any():
            stop(f"{year} empty or null protocol fields")
        if not frame["evaluation_year"].eq(year).all():
            stop(f"{year} evaluation year mismatch")
        if not (frame["training_year_max"] < year).all():
            stop(f"{year} non-prior training year")
        if not frame["evidence_class"].eq("REUSED_DEVELOPMENT").all():
            stop(f"{year} evidence-class mismatch")
        if frame.duplicated(["_race", "_horse"]).any():
            stop(f"{year} duplicate runner")
        if not frame["y"].isin([0, 1]).all():
            stop(f"{year} invalid y winner indicator")
        grouped = frame.groupby("_race", sort=False)
        winners = grouped["y"].sum()
        if not winners.eq(1).all():
            stop(f"{year} race without exactly one winner")
        probs = pd.to_numeric(frame["p"], errors="coerce")
        if not probs.map(math.isfinite).all() or not probs.between(0, 1, inclusive="both").all():
            stop(f"{year} invalid probabilities")
        frame["p"] = probs
        mass_error = float((grouped["p"].sum() - 1).abs().max())
        if mass_error > TOL:
            stop(f"{year} race probability mass error {mass_error}")
        win_probs = frame.loc[frame["y"].eq(1), "p"]
        if (win_probs <= 0).any():
            stop(f"{year} zero winner probability")
        ll = float((-win_probs.map(math.log)).mean())
        if grouped.ngroups != expected_races:
            stop(f"{year} race count drift {grouped.ngroups} vs {expected_races}")
        delta = abs(ll - expected_ll)
        if delta > 1e-6:
            stop(f"{year} log loss drift {delta}")
        print(f"YEAR={year} RACES={grouped.ngroups} RUNNERS={len(frame)} LL={ll:.12f} DELTA={delta:.3g} MASS_ERROR={mass_error:.3g} STATUS=PASS")
    print("READ_ONLY_DRIFT_AUDIT_COMPLETE")

if __name__ == "__main__":
    main()
