from pathlib import Path
import pandas as pd,numpy as np
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM");R=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
A=P/"outputs"/"research"/"model_lab_026"/"edgeiq_certified_flat_walk_forward_epi_026.csv";OUT=R/"outputs"/"research"/"model_v2"/"stage014";OUT.mkdir(parents=True,exist_ok=True)
cols=["canonical_horse_id","race_date","finish_position","epi_value_026"]
parts=[]
for z in pd.read_csv(A,usecols=lambda c:c in cols,chunksize=500000):
 z["race_date"]=pd.to_datetime(z.race_date,errors="coerce");z["finish_position"]=pd.to_numeric(z.finish_position,errors="coerce");z["epi_value_026"]=pd.to_numeric(z.epi_value_026,errors="coerce");parts.append(z)
h=pd.concat(parts,ignore_index=True);valid=h.finish_position.between(1,99);bad=~valid
print("V2_STAGE014_CONTRACT CLEAN_EPI_LINEAGE_FORENSIC NO_MODEL NO_MARKET 2025_2026_SEALED")
print("V2_STAGE014_ROWS",len(h),"VALID_FINISH",int(valid.sum()),"INVALID_FINISH",int(bad.sum()))
print("V2_STAGE014_EPI_NONNULL_VALID",int(h.loc[valid].epi_value_026.notna().sum()),"EPI_NONNULL_INVALID",int(h.loc[bad].epi_value_026.notna().sum()))
for yr,g in h.assign(year=h.race_date.dt.year).groupby("year"):
 if yr<=2024: print("V2_STAGE014_YEAR",int(yr),"ROWS",len(g),"INVALID_RATE",repr(float((~g.finish_position.between(1,99)).mean())),"INVALID_EPI_NONNULL",int(g.loc[~g.finish_position.between(1,99),"epi_value_026"].notna().sum()))
# Certified clean history authority: only valid actual finishes, strict-date usable in next stage.
clean=h[valid & h.canonical_horse_id.notna() & h.race_date.notna()].copy()
clean=clean.sort_values(["canonical_horse_id","race_date"])
clean.to_csv(OUT/"V2_STAGE014_CLEAN_EPI_HISTORY_AUTHORITY.csv",index=False)
print("V2_STAGE014_COMPLETE",len(clean))
