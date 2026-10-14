"""Consolidate live horse and race-history coverage into one read-only ledger."""
import argparse
from pathlib import Path
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 p.add_argument("--linkage",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\issue23_live_features\ISSUE23_LAB245B_HISTORY_LINKAGE.csv")
 p.add_argument("--date",default="2026-10-14")
 p.add_argument("--out",default=r"C:\EDGEIQ_ISSUE23\outputs\research\ISSUE23_LIVE_HISTORY_COVERAGE_LEDGER_V1.csv")
 a=p.parse_args()
 f=pd.read_csv(a.form,dtype="string")
 l=pd.read_csv(a.linkage,dtype="string")
 f["dt"]=pd.to_datetime(f.race_date,errors="coerce")
 f=f[f.dt.lt(pd.Timestamp(a.date))].copy()
 l=l[l.race_date.eq(a.date)].copy()
 if f.horse_code.isna().any():raise RuntimeError("STOP null Racing.com horse code")
 if f.groupby("horse_code").horse_name.nunique().gt(1).any():raise RuntimeError("STOP conflicting names for Racing.com horse ID")
 if l.duplicated(["race_no","horse_name"]).any():raise RuntimeError("STOP duplicate live linkage")
 grouped=f.groupby(["horse_code","horse_name"],dropna=False).agg(form_runs=("race_code","size"),last_form_date=("dt","max"),field_size_non_null=("field_size",lambda v:int(pd.to_numeric(v,errors="coerce").gt(0).sum())),distinct_races=("race_code","nunique")).reset_index()
 grouped["last_form_date"]=grouped.last_form_date.dt.strftime("%Y-%m-%d")
 # Name comparison is informational only, never identity proof.
 grouped["linked_name_candidate"]=grouped.horse_name.str.strip().str.casefold().isin(set(l.horse_name.dropna().str.strip().str.casefold()))
 print("RACINGCOM_HORSES",len(grouped),"FORM_ROWS",len(f))
 print("FORM_FIELD_SIZE_AVAILABLE",int(grouped.field_size_non_null.sum()))
 print("LINKAGE_ROWS",len(l),"LINKAGE_UNIQUE_HORSE_NAMES",l.horse_name.nunique())
 print("NAME_OVERLAP_DISCOVERY_ONLY",int(grouped.linked_name_candidate.sum()))
 print("FORM_LATEST",str(f.dt.max().date()) if len(f) else "NONE")
 print("FORM_HORSES_WITH_2026_RECORDS",int(f.loc[f.dt.dt.year.eq(2026),"horse_code"].nunique()))
 print("FORM_HORSES_WITH_HISTORY_AFTER_JUNE_13",int(f.loc[f.dt.gt(pd.Timestamp("2026-06-13")),"horse_code"].nunique()))
 dest=Path(a.out)
 if dest.exists():raise RuntimeError("STOP immutable output exists; pass --out")
 dest.parent.mkdir(parents=True,exist_ok=True)
 grouped.to_csv(dest,index=False)
 print("OUTPUT",dest)
 print("NO NAME-ONLY IDENTITY PROMOTION; NO SCORING")
if __name__=="__main__":main()
