"""Issue23: diagnose zero code overlap without fuzzy matching or outcomes."""
from pathlib import Path
import pandas as pd
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
live=pd.read_csv(P/"outputs/research/live_acquisition_v1/october_graphql_field_identities.csv",dtype="string")
cross=pd.read_csv(P/"outputs/research/model_lab_075e/proven_horse_code_to_lab026_identity_075eb.csv",dtype="string")
form=pd.read_csv(P/"outputs/research/live_acquisition_v1/caulfield_browser_form.csv",dtype="string",usecols=["horse_code","horse_name","race_date"])
def codes(df,col):
 s=df[col].dropna().str.strip()
 return s[s.ne("")]
a=set(codes(live,"horse_code"));b=set(codes(cross,"horse_code"));c=set(codes(form,"horse_code"))
print("ISSUE23 CODE NAMESPACE DIAGNOSTIC")
for name,s in [("LIVE",a),("HISTORICAL_CROSSWALK",b),("BROWSER_FORM",c)]:
 lengths=pd.Series([len(x) for x in s]).value_counts().sort_index().to_dict()
 numeric=pd.to_numeric(pd.Series(list(s)),errors="coerce")
 print(f"{name} N={len(s)} LENGTHS={lengths} MIN={numeric.min()} MAX={numeric.max()} SAMPLE={sorted(s)[:8]}")
print(f"OVERLAP LIVE_CROSSWALK={len(a&b)} LIVE_FORM={len(a&c)} FORM_CROSSWALK={len(b&c)}")
print("CROSSWALK_COLUMNS="+repr(list(cross.columns)))
print("LIVE_COLUMNS="+repr(list(live.columns)))
print("FORM_DATE_MIN="+str(form.race_date.min())+" FORM_DATE_MAX="+str(form.race_date.max()))
print("DIAGNOSIS_ONLY; NO_OUTCOMES_READ; NO_FUZZY_MATCH")
