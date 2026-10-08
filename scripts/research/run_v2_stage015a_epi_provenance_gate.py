from pathlib import Path
import re,json
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage015a");OUT.mkdir(parents=True,exist_ok=True)
need=("epi_value_026","model_lab_026","lab026","epi_026")
market=re.compile(r"\b(?:bsp|starting[_ ]?price|odds|market|betfair|tab|sp)\b",re.I)
hits=[]
print("V2_STAGE015A_CONTRACT EPI_PROVENANCE_GATE NO_MODEL NO_MARKET_INPUT_ALLOWED 2025_2026_SEALED")
for base in (ROOT/"scripts",ROOT/"docs",ROOT/"outputs"/"research"):
 if not base.exists(): continue
 for p in base.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in {".py",".md",".txt",".json",".yml",".yaml"}: continue
  try:
   if p.stat().st_size>5_000_000: continue
   t=p.read_text(encoding="utf-8",errors="ignore")
  except Exception: continue
  low=(str(p)+"\n"+t).lower()
  if not any(k in low for k in need): continue
  lines=t.splitlines()
  idx=[i for i,l in enumerate(lines) if any(k in l.lower() for k in need)]
  excerpts=[]
  for i in idx[:8]:
   excerpts.extend(lines[max(0,i-5):min(len(lines),i+6)])
  context="\n".join(excerpts)
  mt=sorted(set(m.group(0).lower() for m in market.finditer(context)))
  h={"path":str(p),"match_lines":[[i+1,lines[i][:500]] for i in idx[:20]],"market_terms":mt,"context":context[:16000]}
  hits.append(h)
  print("V2_STAGE015A_FILE",str(p),"MARKET_CONTEXT",",".join(mt) if mt else "NONE")
  for i in idx[:5]: print("  LINE",i+1,lines[i][:500])
print("V2_STAGE015A_FILES",len(hits))
(OUT/"V2_STAGE015A_EPI_PROVENANCE_SEARCH.json").write_text(json.dumps(hits,indent=2),encoding="utf-8")
print("V2_STAGE015A_COMPLETE")
