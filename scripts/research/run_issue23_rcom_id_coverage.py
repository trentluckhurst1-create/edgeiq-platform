"""Read-only Racing.com to approved RCOM ID coverage report. No EIQ promotion."""
import argparse
import pandas as pd

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--form",default=r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1\caulfield_browser_form.csv")
 p.add_argument("--mapping",default=r"C:\EDGEIQ_ISSUE23\config\performance-intelligence\edgeiq_horse_performance_identity_map_v1.csv")
 a=p.parse_args()
 f=pd.read_csv(a.form,dtype=str)
 m=pd.read_csv(a.mapping,dtype=str)
 for col in ["horse_code","horse_name"]:
  if col not in f:raise RuntimeError("STOP missing form column "+col)
 for col in ["canonical_horse_id","identity_status"]:
  if col not in m:raise RuntimeError("STOP missing map column "+col)
 f["rcom_id"]="RCOM_HORSE_"+f.horse_code.str.strip()
 m=m[m.canonical_horse_id.str.startswith("RCOM_HORSE_",na=False)].copy()
 m["rcom_id"]=m.canonical_horse_id.str.strip()
 approvals=m.groupby("rcom_id").identity_status.agg(lambda s:sorted(set(s.dropna())))
 bad=approvals[approvals.map(len).gt(1)]
 if len(bad):raise RuntimeError("STOP conflicting identity status for "+str(len(bad))+" IDs")
 approved=set(m.loc[m.identity_status.eq("APPROVED"),"rcom_id"])
 ids=f[["horse_code","horse_name","rcom_id"]].drop_duplicates()
 print("FORM_ROWS",len(f))
 print("FORM_UNIQUE_HORSE_IDS",ids.horse_code.nunique())
 print("RCOM_APPROVED_UNIQUE_IDS",ids.loc[ids.rcom_id.isin(approved),"horse_code"].nunique())
 print("RCOM_UNMAPPED_UNIQUE_IDS",ids.loc[~ids.rcom_id.isin(set(m.rcom_id)),"horse_code"].nunique())
 print("RCOM_NOT_APPROVED_UNIQUE_IDS",ids.loc[ids.rcom_id.isin(set(m.rcom_id)-approved),"horse_code"].nunique())
 print("SAMPLE_UNMAPPED",ids.loc[~ids.rcom_id.isin(approved),["horse_code","horse_name"]].head(12).to_dict("records"))
 print("NO_EIQ_IDENTITY_BRIDGE_CERTIFIED_NO_SCORING")
if __name__=="__main__":main()
