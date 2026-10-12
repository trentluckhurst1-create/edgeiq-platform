"""Issue23: inspect acquired live field identity and form schemas without touching outcome payloads."""
from pathlib import Path
import pandas as pd,json
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\live_acquisition_v1")
files=["structured_runners_20261012T052256Z.csv","october_graphql_field_identities.csv","caulfield_browser_form.csv","caulfield_recent_timing_manifest.csv"]
for name in files:
 p=P/name
 print("\nFILE="+name+" EXISTS="+str(p.is_file()))
 if not p.is_file():continue
 d=pd.read_csv(p,nrows=1000,low_memory=False)
 print("SAMPLE_ROWS="+str(len(d))+" COLUMNS="+repr(list(d.columns)))
 for c in d.columns:
  if any(k in c.lower() for k in ("id","code","name","date","race","venue","horse","runner","time","status","source","url")):
   print(f"COL={c} NON_NULL={int(d[c].notna().sum())} DISTINCT={d[c].nunique(dropna=True)} EXAMPLES={d[c].dropna().astype(str).head(3).tolist()}")
print("\nCERTIFICATION=NOT_ESTABLISHED; READ_ONLY; NO_RESULTS_READ")
