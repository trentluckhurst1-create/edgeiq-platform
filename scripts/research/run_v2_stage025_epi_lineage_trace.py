from pathlib import Path
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\scripts")
files=[
"build_edgeiq_historical_performance_rating_v1.py",
"audit_edgeiq_horse_performance_rating_builder_trace_v1.py",
"audit_edgeiq_horse_performance_rating_builder_defects_v1.py",
"build_edgeiq_epi_parameter_fact_v1.py",
"build_edgeiq_epi_component_normalisation_parameter_fact_v1.py",
"audit_edgeiq_epi_performance_dependency_v1.py",
"build_edgeiq_race_field_performance_epi_v1.py",
"audit_edgeiq_race_field_performance_epi_v1.py"]
print("V2_STAGE025_CONTRACT PERFORMANCE_RATING_TO_EPI_LINEAGE NO_MODEL 2025_2026_SEALED")
market=["market","starting_price","starting price","bsp","odds","sp_","price"]
pit=["race_date","asof","as_of","prior","shift(","< target","strict"]
formula=["rating","epi","length","standard","normal","weight","class"]
for fn in files:
 p=ROOT/fn
 print("V2_STAGE025_FILE",fn,"EXISTS",p.exists())
 if not p.exists():continue
 txt=p.read_text(encoding="utf-8",errors="ignore");lo=txt.lower()
 print("V2_STAGE025_MARKET_TERMS",fn,"|".join(k for k in market if k in lo) or "NONE")
 print("V2_STAGE025_PIT_TERMS",fn,"|".join(k for k in pit if k in lo) or "NONE")
 lines=txt.splitlines()
 shown=0
 for i,line in enumerate(lines):
  l=line.lower()
  if any(k in l for k in formula) and any(x in l for x in ["=","merge","read_csv","to_csv"]):
   print("V2_STAGE025_LINE",fn,i+1,line.strip()[:1000]);shown+=1
   if shown>=40:break
print("V2_STAGE025_COMPLETE")
