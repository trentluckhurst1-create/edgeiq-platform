from pathlib import Path
import csv,json,re
ROOT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")
print("ISSUE23 — FULL STAGE011 FEATURE + TRAINING PROVENANCE INVENTORY")
print("READ ONLY; NO MARKET; NO MODEL FIT; NO SEALED OUTCOMES")
dirs=[ROOT/"outputs"/"research"/"model_v2",ROOT/"edgeiq-platform"/"edgeiq-platform"/"outputs"/"research"/"model_v2"]
patterns=("stage011","stage006","pit_feature","feature_manifest")
for base in dirs:
 if not base.exists():continue
 print("ROOT="+str(base))
 paths=[]
 for p in base.rglob("*"):
  if not p.is_file():continue
  name=p.name.lower()
  if not any(k in name for k in patterns):continue
  if p.suffix.lower() not in (".json",".csv",".txt",".md",".py"):continue
  paths.append(p)
 for p in sorted(paths,key=lambda z:str(z))[:120]:
  print("FILE="+str(p)+" BYTES="+str(p.stat().st_size))
  if p.suffix.lower()==".csv":
   try:
    with p.open(encoding="utf-8-sig",errors="replace",newline="") as f:header=next(csv.reader(f))
    print("COLUMNS="+repr(header[:120]))
   except (OSError,StopIteration):pass
  if p.suffix.lower()==".json" and p.stat().st_size<500000:
   try:
    obj=json.loads(p.read_text(encoding="utf-8-sig"))
    if isinstance(obj,dict):
     print("JSON_KEYS="+repr(list(obj)[:60]))
     for key in ("features","feature_names","train_rows","years","status","source_stage006_sha256"):
      if key in obj:print("JSON_"+key.upper()+"="+repr(obj[key])[:3000])
   except (OSError,ValueError):pass
print("STOP: INVENTORY_ONLY — DO NOT CLAIM FULL-FEATURE COMPARABILITY UNTIL SOURCE VERIFIED")
