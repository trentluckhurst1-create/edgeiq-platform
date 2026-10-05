from pathlib import Path
import json,os,re
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
keys=re.compile(r"(jockey|trainer|barrier|class|first.?starter|track|distance|map|speed|rating|form|warehouse|performance)",re.I)
ext={".csv",".parquet",".json",".jsonl",".pkl",".pickle",".feather"}
rows=[]
for base in [ROOT/"outputs",ROOT/"data",ROOT/"artifacts"]:
 if not base.exists(): continue
 for p in base.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in ext: continue
  s=str(p.relative_to(ROOT))
  if not keys.search(s): continue
  try: size=p.stat().st_size
  except: size=-1
  rows.append({"path":s,"bytes":size,"mb":round(size/1048576,3)})
rows.sort(key=lambda x:x["bytes"],reverse=True)
out=ROOT/"outputs/research/profitability_program/lab245b/LAB245D9_LOCAL_SIGNAL_INVENTORY.json"
out.write_text(json.dumps({"contract":"LAB245D9_LOCAL_SIGNAL_INVENTORY_V1","files":rows[:500],"count":len(rows)},indent=2),encoding="utf-8")
print("MATCHED_FILES=",len(rows))
for x in rows[:250]: print(f'{x["mb"]:10.3f} MB  {x["path"]}')
