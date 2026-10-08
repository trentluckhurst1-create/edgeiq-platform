from pathlib import Path
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
print("V2_STAGE019B_CONTRACT LAB045A_PROVENANCE_TRACE NO_MODEL 2025_2026_SEALED")
terms=["weight_features_045a","change_from_recent_average","prior_recent_weight_average","LAB045A"]
n=0
for root in [P/"scripts",P/"docs",P/"outputs"/"research"]:
 for fp in root.rglob("*"):
  if not fp.is_file() or fp.suffix.lower() not in [".py",".txt",".md",".json"]:continue
  try:
   if fp.stat().st_size>5000000:continue
   t=fp.read_text(encoding="utf-8",errors="ignore")
  except:continue
  if not any(q.lower() in t.lower() for q in terms):continue
  n+=1; low=t.lower()
  print("V2_STAGE019B_FILE",fp)
  print("V2_STAGE019B_FLAGS","MARKET",int("market" in low),"ODDS",int("odds" in low),"EPI",int("epi" in low),"SHIFT",int("shift(" in low),"ROLLING",int("rolling(" in low))
  for i,line in enumerate(t.splitlines()):
   if any(q.lower() in line.lower() for q in terms):
    print("V2_STAGE019B_LINE",i+1,line[:800])
print("V2_STAGE019B_HITS",n)
print("V2_STAGE019B_COMPLETE")
