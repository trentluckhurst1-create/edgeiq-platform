from pathlib import Path
import pandas as pd, os, json
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
U=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage004\V2_CERTIFIED_SINGLE_WINNER_UNIVERSE.csv")
A=P/"outputs"/"research"/"model_lab_031"/"certified_current_race_context_031.csv"
print("V2_STAGE018_CONTRACT DENSE_GAP_INVENTORY_AND_LAB031_PIT_AUDIT NO_MODEL NO_MARKET 2025_2026_SEALED")
u=pd.read_csv(U);a=pd.read_csv(A)
for d in (u,a):d["race_date"]=pd.to_datetime(d["race_date"],errors="coerce")
print("V2_STAGE018_LAB031_ROWS",len(a),"DATE_MIN",a.race_date.min(),"DATE_MAX",a.race_date.max())
print("V2_STAGE018_LAB031_DUP_KEYS",int(a.duplicated(["canonical_race_id","canonical_horse_id","race_date"]).sum()))
# Semantic sanity: no negative prior counts; change fields should be unavailable where no prior-history counts indicate no evidence.
for c in ["prior_same_class_starts","prior_exact_distance_starts_031"]:
 if c in a:
  q=pd.to_numeric(a[c],errors="coerce")
  print("V2_STAGE018_COUNT",c,"NONNULL",int(q.notna().sum()),"NEGATIVE",int((q<0).sum()),"MIN",q.min(),"MAX",q.max())
for c in ["weight_change_kg","distance_change_metres","abs_distance_change_metres"]:
 if c in a:
  q=pd.to_numeric(a[c],errors="coerce")
  print("V2_STAGE018_CHANGE",c,"NONNULL",int(q.notna().sum()),"ZERO",int((q==0).sum()))
# Locate candidate CSV authorities by schema only, avoiding market/SP/EPI-derived candidates.
roots=[P/"outputs"/"research"]
tokens=["age","sex","gender","class","prize","track","condition","going","weight","rating"]
bad=["market","price","odds","bsp","sp_","starting_price","epi"]
cands=[]
for root in roots:
 for fp in root.rglob("*.csv"):
  s=str(fp).lower()
  if not any(t in s for t in tokens):continue
  if any(b in s for b in bad):continue
  try:
   cols=list(pd.read_csv(fp,nrows=0).columns)
  except Exception:continue
  low="|".join(cols).lower()
  has_race=("canonical_race_id" in cols or "_race" in cols)
  has_horse=("canonical_horse_id" in cols or "horse_id" in cols or "_horse" in cols)
  has_date=("race_date" in cols)
  interesting=[c for c in cols if any(t in c.lower() for t in tokens) and not any(b in c.lower() for b in bad)]
  if has_race and has_horse and has_date and interesting:
   cands.append((str(fp),interesting[:20]))
print("V2_STAGE018_CANDIDATE_COUNT",len(cands))
for fp,cols in cands[:100]:print("V2_STAGE018_CANDIDATE",fp,"FIELDS","|".join(cols))
print("V2_STAGE018_COMPLETE")
