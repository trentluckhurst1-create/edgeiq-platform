from pathlib import Path
import re,json
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
terms=[re.compile(x,re.I) for x in [r"LAB231_HISTORICAL_PERFORMANCE_FEATURES",r"h231_epi_last10_median",r"h231_same_class_mean",r"LAB231"]]
ext={".py",".ps1",".md",".json",".txt",".yml",".yaml"}
hits=[]
for root in roots:
 for p in root.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in ext: continue
  try:
   if p.stat().st_size>5_000_000: continue
   t=p.read_text(encoding="utf-8",errors="ignore")
  except Exception: continue
  if any(rx.search(t) for rx in terms):
   lines=t.splitlines();m=[]
   for i,line in enumerate(lines):
    if any(rx.search(line) for rx in terms):
     m.append({"line":i+1,"context":"\n".join(lines[max(0,i-4):min(len(lines),i+7)])})
   hits.append({"path":str(p),"matches":m[:20]})
print("HITS",len(hits))
for h in hits:
 print("\n"+"="*120);print(h["path"])
 for m in h["matches"]: print(f'--- line {m["line"]} ---\n{m["context"]}')
out=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245D16_LAB231_LINEAGE.json")
out.write_text(json.dumps({"contract":"LAB245D16_LAB231_LINEAGE_V1","hits":hits},indent=2),encoding="utf-8")
