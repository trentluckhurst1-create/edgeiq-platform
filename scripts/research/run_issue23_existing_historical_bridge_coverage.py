"""Measure exact RCOM coverage in the pre-existing historical horse identity bridge."""
import argparse
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 p.add_argument("--bridge",default=r"C:\EDGEIQ_ISSUE23\public\data\edgeiq_current_historical_horse_identity_bridge_v2.csv")
 p.add_argument("--warehouse",default=r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245B_WAREHOUSE_RUNNER_LVS.csv")
 a=p.parse_args()
 f=pd.read_csv(a.form,dtype=str)
 h=pd.read_csv(a.bridge,dtype=str)
 w=pd.read_csv(a.warehouse,usecols=["canonical_horse_id"],dtype=str)
 ids=f[["horse_code","horse_name"]].drop_duplicates()
 if ids.horse_code.duplicated().any():raise RuntimeError("STOP conflicting live horse names")
 ids["current_canonical_runner_id"]="RCOM_HORSE_"+ids.horse_code.str.strip()
 if h.current_canonical_runner_id.duplicated().any():raise RuntimeError("STOP duplicate bridge current IDs")
 j=ids.merge(h,on="current_canonical_runner_id",how="left",validate="one_to_one",indicator=True)
 resolved=j.historical_canonical_horse_id.notna() & j.identity_resolution_status.fillna("").str.contains("RESOLVED",case=False) & ~j.identity_resolution_status.fillna("").str.contains("UNRESOLVED",case=False)
 available=set(w.canonical_horse_id.dropna())
 matched=resolved & j.historical_canonical_horse_id.isin(available)
 print("LIVE_HORSES",len(ids),"BRIDGE_ROWS",len(h))
 print("BRIDGE_ID_MATCHES",int(j._merge.eq("both").sum()))
 print("BRIDGE_RESOLVED",int(resolved.sum()))
 print("RESOLVED_IDS_PRESENT_IN_LVS_WAREHOUSE",int(matched.sum()))
 print("BRIDGE_STATUS_COUNTS",j.identity_resolution_status.fillna("NOT_IN_BRIDGE").value_counts().head(12).to_dict())
 print("SAMPLE_RESOLVED",j.loc[matched,["horse_name","horse_code","historical_canonical_horse_id"]].head(12).to_dict("records"))
 print("NO_AUTOMATIC_IDENTITY_PROMOTION_NO_SCORING")
if __name__=="__main__":main()
