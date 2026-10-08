from pathlib import Path
import re,json
ROOT=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
OUT=Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH\outputs\research\model_v2\stage015a");OUT.mkdir(parents=True,exist_ok=True)
terms=["epi_value_026","model_lab_026","LAB026","epi_026"]
market=re.compile(r"\b(sp|bsp|starting[_ ]?price|odds|market|price|betfair|tab)\b",re.I)
hits=[]
for base in [ROOT/"scripts",ROOT/"docs",ROOT/"outputs"/"research"]:
 if not base.exists(): continue
 for p in base.rglob("*"):
  if not p.is_file() or p.suffix.lower() not in {".py",".md",".txt",".json",".csv",".yml",".yaml"}: continue
  try:
   if p.stat().st_size>5_000_000: continue
   t=p.read_text(encoding="utf-8",errors="ignore")
  except: continue
  if any(x.lower() in t.lower() or x.lower() in p.name.lower() for x in terms):
   lines=t.splitlines(); matched=[(i+1,l[:500]) for i,l in enumerate(lines) if any(x.lower() in l.lower() for x in terms)]
   context="\n".join(lines[max(0,i-6):min(len(lines),i+6)] for i,_ in matched[:8])
   hits.append({"path":str(p),"matches":matched[:20],"market_terms":sorted(set(m.group(0).lower() for m in market.finditer(context))),"context":context[:12000]})
print("V2_STAGE015A_CONTRACT EPI_PROVENANCE_GATE NO_MODEL NO_MARKET_INPUT_ALLOWED 2025_2026_SEALED")
print("V2_STAGE015A_FILES",len(hits))
for h in hits[:40]:
 print("V2_STAGE015A_FILE",h["path"],"MARKET_CONTEXT",",".join(h["market_terms"]) or "NONE")
 for n,l in h["matches"][:6]: print("  LINE",n,l)
(OUT/"V2_STAGE015A_EPI_PROVENANCE_SEARCH.json").write_text(json.dumps(hits,indent=2),encoding="utf-8")
print("V2_STAGE015A_COMPLETE")
