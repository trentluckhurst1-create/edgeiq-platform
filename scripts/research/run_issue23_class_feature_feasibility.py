"""Issue23: inspect feasibility of NEW class-transition feature family.

Metadata/coverage only; does not access outcomes, fit models or touch sealed years.
A name match is NOT proof of point-in-time safety.
"""
from pathlib import Path
import re
import pandas as pd

ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
WAREHOUSE=ROOT/"outputs/research/model_v2/stage006/V2_STAGE006_PIT_FEATURE_WAREHOUSE.csv"
OUT=Path("outputs/research/issue23_top1_winner_selection")
TOKENS=("class","grade","benchmark","rating","handicap","level","strength")
EXCLUDE=("jockey","trainer","market","odds","price","sp","bsp","prob","pred")
def main():
    if not WAREHOUSE.is_file():raise FileNotFoundError(WAREHOUSE)
    header=pd.read_csv(WAREHOUSE,nrows=0).columns.tolist()
    candidate=[c for c in header if any(t in c.lower() for t in TOKENS)
               and not any(re.search(r"(^|_)"+re.escape(t)+r"(_|$)",c.lower()) for t in EXCLUDE)]
    print("ISSUE23 CLASS-TRANSITION FEATURE FEASIBILITY")
    print("Candidate columns:",candidate)
    if not candidate:
        print("STOP: No class/grade/benchmark/rating fields in Stage006; do not fabricate data.")
        return
    cols=["year","_race","_horse"]+candidate
    d=pd.read_csv(WAREHOUSE,usecols=cols)
    d=d[d.year.isin([2022,2023,2024])]
    if d.duplicated(["year","_race","_horse"]).any():
        raise RuntimeError("Duplicate runner identities")
    rows=[]
    for c in candidate:
        for year,g in d.groupby("year"):
            v=g[c]
            rows.append({"feature":c,"year":int(year),"runners":len(g),
                         "present":int(v.notna().sum()),"coverage":float(v.notna().mean()),
                         "distinct_values":int(v.nunique(dropna=True)),
                         "sample_values":" | ".join(str(x)[:55] for x in v.dropna().unique()[:5])})
    report=pd.DataFrame(rows)
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/"ISSUE23_CLASS_FEATURE_FEASIBILITY.csv"
    report.to_csv(target,index=False)
    print(report.to_string(index=False))
    print("\nSTOP before any model test: confirm each feature is non-market, pre-race,")
    print("historically point-in-time, and represents current vs prior class without leakage.")
    print("Saved:",target.resolve())
if __name__=="__main__":main()
