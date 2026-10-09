from pathlib import Path
import re
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE036_CONTRACT EPI_PROVENANCE_FINAL_GATE NO_MODEL NO_MARKET_FEATURES 2025_2026_SEALED")
# Target builders/audits likely to reveal actual EPI construction and source components.
names=["build_edgeiq_epi_parameter_fact_v1.py","build_edgeiq_epi_component_normalisation_parameter_fact_v1.py","audit_edgeiq_epi_performance_dependency_v1.py","audit_edgeiq_race_field_performance_epi_v1.py"]
for name in names:
 hits=list((P/"scripts").rglob(name))
 print("V2_STAGE036_FILE",name,"FOUND",len(hits))
 for f in hits[:2]:
  txt=f.read_text(encoding="utf-8",errors="ignore")
  print("V2_STAGE036_PATH",f)
  for i,line in enumerate(txt.splitlines(),1):
   lo=line.lower()
   if any(k in lo for k in ["epi","historical","suitability","race_context","market","price","sp","race_date","prior","projected_performance"]):
    print("V2_STAGE036_LINE",name,i,line[:500])
print("V2_STAGE036_COMPLETE")
