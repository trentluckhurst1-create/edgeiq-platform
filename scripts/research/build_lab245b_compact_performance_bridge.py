from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/research/model_price_diagnostics"
LAB026 = ROOT / "outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
LAB231 = BASE / "lab231/LAB231_HISTORICAL_PERFORMANCE_FEATURES.csv"
OUTDIR = ROOT / "outputs/research/profitability_program/lab245b"
OUT = OUTDIR / "LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"

def norm_id(s):
    return s.astype("string").str.strip()

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not LAB026.exists():
        raise FileNotFoundError(LAB026)
    if not LAB231.exists():
        raise FileNotFoundError(LAB231)

    # Current-race outcome only. No SP and no post-2024 rows enter this bridge.
    target = pd.read_csv(
        LAB026,
        usecols=["canonical_race_id","canonical_horse_id","race_date","runner_lengths_v_standard_026"],
        low_memory=False,
    )
    target["race_date"] = pd.to_datetime(target["race_date"], errors="coerce")
    target = target[target["race_date"].dt.year.between(2021, 2024)].copy()
    target = target.rename(columns={
        "canonical_race_id":"_race",
        "canonical_horse_id":"_horse",
        "runner_lengths_v_standard_026":"target_lvs",
    })
    target["_race"] = norm_id(target["_race"])
    target["_horse"] = norm_id(target["_horse"])
    target["target_lvs"] = pd.to_numeric(target["target_lvs"], errors="coerce")
    target = target.drop_duplicates(["_race","_horse"], keep=False)

    hist = pd.read_csv(LAB231, low_memory=False)
    hist["_race"] = norm_id(hist["_race"])
    hist["_horse"] = norm_id(hist["_horse"])
    hist = hist[hist["_year"].between(2021, 2024)].copy()
    if hist.duplicated(["_race","_horse"]).any():
        raise RuntimeError("LAB231 duplicate race/horse keys.")

    model = hist.merge(
        target[["_race","_horse","race_date","target_lvs"]],
        on=["_race","_horse"], how="left", validate="one_to_one"
    )
    if not model["_year"].between(2021, 2024).all():
        raise RuntimeError("Sealed-year breach.")
    if model["target_lvs"].notna().sum() == 0:
        raise RuntimeError("No observed current-race performance targets.")

    # B-1 is performance forecasting only: market/SP columns are forbidden.
    forbidden = [c for c in model.columns if c.lower() in {"_sp","sp","final_sp","odds","market_probability"}]
    if forbidden:
        raise RuntimeError(f"Market columns leaked into B-1 bridge: {forbidden}")

    model.to_csv(OUT, index=False)
    print(f"ROWS={len(model):,}")
    print(f"RACES={model['_race'].nunique():,}")
    print(f"OBSERVED_TARGETS={model['target_lvs'].notna().sum():,}")
    print(f"TARGET_COVERAGE_PCT={100*model['target_lvs'].notna().mean():.4f}")
    print(f"YEARS={sorted(model['_year'].dropna().astype(int).unique().tolist())}")
    print(f"OUT={OUT}")

if __name__ == "__main__":
    main()
