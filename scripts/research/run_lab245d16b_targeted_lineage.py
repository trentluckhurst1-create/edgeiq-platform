from pathlib import Path
import os,re,json
roots=[Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH"),Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")]
name_rx=re.compile(r"(lab.?231|historical.*performance|performance.*feature|model.*price|feature.*builder|build.*feature)",re.I)
text_rx=re.compile(r"(LAB231_HISTORICAL_PERFORMANCE_FEATURES|h231_epi_|h231_same_class|h231_same_condition|h231_dist200|LAB231)",re.I)
cand=[];hits=[]
for root in roots:
 for dp,dn,fn in os.walk(root):
  # prune bulky/non-source trees
  dn[:]=[x for x in dn if x.lower() not in {".git","node_modules","__pycache__",".next","dist","build"}]
  for n in fn:
   p=Path(dp)/n
   if name_rx.search(n): cand.append(str(p))
   if p.suffix.lower() not in {".py",".ps1",".md",".json",".txt",".yml",".yaml"}: continue
   if not (name_rx.search(n) or "scripts" in {x.lower() for x in p.parts}): continue
   try:
    if p.stat().st_size>3_000_000: continue
    t=p.read_text(encoding="utf-8",errors="ignore")
   except Exception: continue
   if text_rx.search(t):
    lines=t.splitlines();mm=[]
    for i,line in enumerate(lines):
     if text_rx.search(line): mm.append({"line":i+1,"context":"\n".join(lines[max(0,i-5):min(len(lines),i+9)])})
    hits.append({"path":str(p),"matches":mm[:30]})
print("CANDIDATE_FILENAMES",len(cand))
for x in cand[:300]: print("CAND",x)
print("TEXT_HITS",len(hits))
for h in hits:
 print("\n"+"="*110+"\n"+h["path"])
 for m in h["matches"]: print(f'---L{m["line"]}---\n{m["context"]}')
out=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\profitability_program\lab245b\LAB245D16B_TARGETED_LINEAGE.json")
out.write_text(json.dumps({"contract":"LAB245D16B_TARGETED_LINEAGE_V1","candidates":cand,"hits":hits},indent=2),encoding="utf-8")
