from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH") / "outputs/research/model_v2/stage011_reproduction"
YEARS = (2022, 2023, 2024)
EDGES = np.linspace(0.0, 1.0, 11)
LABELS = [f"[{EDGES[i]:.1f},{EDGES[i+1]:.1f}{']' if i == 9 else ')'}" for i in range(10)]
REQUIRED = {"_race", "_horse", "race_date", "evaluation_year", "training_year_max", "y", "raw", "p", "evidence_class", "model_name", "model_seed", "feature_manifest_sha256", "source_stage006_sha256", "source_d45_sha256", "source_perf026_sha256"}

def main():
    report_path = ROOT / "STAGE011_REPRODUCTION_REPORT.json"
    paths = {year: ROOT / f"STAGE011_RUNNER_PROBABILITIES_{year}.csv" for year in YEARS}
    for p in (report_path, *paths.values()):
        if not p.is_file():
            raise RuntimeError(f"STOP_MISSING_FILE: {p}")
    protocol = json.loads(report_path.read_text())
    if protocol.get("status") != "PASS" or protocol.get("scope") != "REUSED_DEVELOPMENT_ONLY":
        raise RuntimeError("STOP_PROTOCOL_NOT_REPRODUCED")
    results = []
    all_bins = []
    for year in YEARS:
        df = pd.read_csv(paths[year])
        if not REQUIRED.issubset(df.columns):
            raise RuntimeError(f"STOP_MISSING_PROTOCOL_FIELDS_{year}: {sorted(REQUIRED - set(df.columns))}")
        if df.empty or df[list(REQUIRED)].isna().any().any():
            raise RuntimeError(f"STOP_MISSING_VALUES_{year}")
        if not df.evaluation_year.eq(year).all() or not df.evidence_class.eq("REUSED_DEVELOPMENT").all():
            raise RuntimeError(f"STOP_SCOPE_{year}")
        if not df.model_seed.eq(42).all() or not (df.training_year_max < year).all():
            raise RuntimeError(f"STOP_TRAINING_PROTOCOL_{year}")
        if not df.y.isin([0, 1]).all():
            raise RuntimeError(f"STOP_OUTCOMES_{year}")
        if not np.isfinite(df.p.to_numpy(dtype=float)).all() or not df.p.between(0, 1).all():
            raise RuntimeError(f"STOP_PROBABILITY_RANGE_{year}")
        if df.duplicated(["_race", "_horse"]).any() or (df.groupby("_race").y.sum() != 1).any():
            raise RuntimeError(f"STOP_RACE_IDENTITY_{year}")
        mass_error = float((df.groupby("_race").p.sum() - 1).abs().max())
        if mass_error > 1e-12:
            raise RuntimeError(f"STOP_RACE_MASS_{year}: {mass_error}")
        df["bin_idx"] = np.minimum(np.floor(df.p.to_numpy(dtype=float) * 10).astype(int), 9)
        bins = []
        for i, label in enumerate(LABELS):
            s = df[df.bin_idx == i]
            bins.append(dict(year=year, bin=label, count=len(s),
                             mean_predicted_probability=float(s.p.mean()) if len(s) else None,
                             observed_win_rate=float(s.y.mean()) if len(s) else None))
        gaps = [abs(b["mean_predicted_probability"] - b["observed_win_rate"]) for b in bins if b["count"]]
        ll = float(np.mean([-np.log(max(float(g.loc[g.y.eq(1), "p"].iloc[0]), 1e-15))
                            for _, g in df.groupby("_race")]))
        top1 = float(np.mean([int(g.loc[g.p.idxmax(), "y"] == 1) for _, g in df.groupby("_race")]))
        results.append(dict(year=year, evidence_class="REUSED_DEVELOPMENT",
                            races=int(df._race.nunique()), runners=len(df),
                            log_loss=ll, top_probability_winner_share=top1,
                            max_absolute_bin_calibration_gap=max(gaps),
                            max_race_probability_mass_error=mass_error))
        all_bins.extend(bins)
    pd.DataFrame(all_bins).to_csv(ROOT / "STAGE011_CALIBRATION_TEN_BINS.csv", index=False)
    out = dict(status="PASS", audit="READ_ONLY_STAGE011_CALIBRATION",
               evidence_class="REUSED_DEVELOPMENT", bin_edges=[float(x) for x in EDGES],
               year_results=results, bins=all_bins,
               no_refit=True, no_threshold_search=True, no_independent_validation=True,
               no_profitability_claim=True)
    (ROOT / "STAGE011_CALIBRATION_AUDIT.json").write_text(json.dumps(out, indent=2))
    for r in results:
        print(f"YEAR={r['year']} RACES={r['races']} RUNNERS={r['runners']} LL={r['log_loss']:.12f} TOP1={r['top_probability_winner_share']:.6f} MAX_BIN_GAP={r['max_absolute_bin_calibration_gap']:.6f} MASS_ERROR={r['max_race_probability_mass_error']:.3g}")
    print("AUDIT_STATUS=PASS EVIDENCE_CLASS=REUSED_DEVELOPMENT")
    print("BIN_REPORT=" + str(ROOT / "STAGE011_CALIBRATION_TEN_BINS.csv"))
    print("AUDIT_REPORT=" + str(ROOT / "STAGE011_CALIBRATION_AUDIT.json"))

if __name__ == "__main__":
    main()
