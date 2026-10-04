from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"outputs/research/model_price_diagnostics"
LAB026=ROOT/"outputs/research/model_lab_026/edgeiq_certified_flat_walk_forward_epi_026.csv"
LAB179=BASE/"lab179/LAB179_DYNAMIC_ABILITY_FEATURES.csv"
YEAR_SOURCE=BASE/"lab229/LAB229_OOF_PREDICTIONS_CORRECTED.csv"
OUTDIR=ROOT/"outputs/research/profitability_program/lab245b"
OUT=OUTDIR/"LAB245B_COMPACT_PERFORMANCE_BRIDGE.csv"

def norm(s): return s.astype("string").str.strip()

def main():
    OUTDIR.mkdir(parents=True,exist_ok=True)
    for p in [LAB026,LAB179,YEAR_SOURCE]:
        if not p.exists(): raise FileNotFoundError(p)

    # Evaluation keys/year only; probabilities and market fields are never read.
    yrs=pd.read_csv(YEAR_SOURCE,usecols=["_race","_horse","_year"],low_memory=False)
    yrs["_race"],yrs["_horse"]=norm(yrs["_race"]),norm(yrs["_horse"])
    yrs=yrs[yrs["_year"].between(2021,2024)].drop_duplicates(["_race","_horse"])
    if yrs.duplicated(["_race","_horse"]).any(): raise RuntimeError("Duplicate evaluation keys.")

    hist=pd.read_csv(LAB179,low_memory=False)
    hist["_race"],hist["_horse"]=norm(hist["_race"]),norm(hist["_horse"])
    if hist.duplicated(["_race","_horse"]).any(): raise RuntimeError("LAB179 duplicate keys.")
    hist=hist.merge(yrs,on=["_race","_horse"],how="inner",validate="one_to_one")

    target=pd.read_csv(LAB026,usecols=[
      "canonical_race_id","canonical_horse_id","race_date","runner_lengths_v_standard_026"
    ],low_memory=False).rename(columns={
      "canonical_race_id":"_race","canonical_horse_id":"_horse",
      "runner_lengths_v_standard_026":"target_lvs"})
    target["_race"],target["_horse"]=norm(target["_race"]),norm(target["_horse"])
    target["race_date"]=pd.to_datetime(target["race_date"],errors="coerce")
    target["target_lvs"]=pd.to_numeric(target["target_lvs"],errors="coerce")
    target=target[target["race_date"].dt.year.between(2021,2024)]
    target=target.drop_duplicates(["_race","_horse"],keep=False)

    model=hist.merge(target[["_race","_horse","race_date","target_lvs"]],
                     on=["_race","_horse"],how="left",validate="one_to_one")
    if not model["_year"].between(2021,2024).all(): raise RuntimeError("Sealed-year breach.")
    forbidden=[c for c in model if c.lower() in {"_sp","sp","final_sp","odds","p_model","market_probability"}]
    if forbidden: raise RuntimeError(f"Forbidden B-1 columns: {forbidden}")
    if model["target_lvs"].notna().sum()==0: raise RuntimeError("No observed target performance.")

    model.to_csv(OUT,index=False)
    print(f"ROWS={len(model):,}")
    print(f"RACES={model['_race'].nunique():,}")
    print(f"OBSERVED_TARGETS={model.target_lvs.notna().sum():,}")
    print(f"TARGET_COVERAGE_PCT={100*model.target_lvs.notna().mean():.4f}")
    print(f"YEARS={sorted(model._year.astype(int).unique())}")
    print(f"OUT={OUT}")

if __name__=="__main__": main()
