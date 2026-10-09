"""Read-only LAB031 count-field lineage gate: local builder discovery and strict-prior diagnostics. No fitting."""
from pathlib import Path
import re
ROOTS=[Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM"),Path(r"C:\EDGEIQ_PROFITABILITY_RESEARCH")]
TARGETS=["prior_same_jockey_starts","prior_same_trainer_starts"]
print("CONTRACT LAB031_COUNT_BUILDER_TRACE READ_ONLY NO_MODEL NO_MARKET SEALED_2025_2026")
print("BUILDER_SEARCH scripts and docs only; source datasets never read")
found=0
for root in ROOTS:
 if not root.exists():continue
 for folder in ["scripts","docs","LIVE_PERFORMANCE_BUILDERS"]:
  base=root/folder
  if not base.exists():continue
  for p in base.rglob("*"):
   if not p.is_file() or p.suffix.lower() not in {".py",".md",".json",".txt",".ps1"}:continue
   if p.stat().st_size>1_500_000:continue
   try:s=p.read_text(encoding="utf-8")
   except (UnicodeError,OSError):continue
   for token in TARGETS:
    if token not in s:continue
    lines=s.splitlines()
    for i,line in enumerate(lines):
     if token in line:
      found+=1
      lo=max(0,i-5);hi=min(len(lines),i+6)
      print("BUILDER_HIT",p,"FIELD",token,"LINE",i+1)
      for j in range(lo,hi):print("CONTEXT",j+1,lines[j][:250])
print("TOTAL_REFERENCES",found)
print("REQUIRED STRICT_PRIOR_DATE_EXCLUSION, SAME_DAY_EXCLUSION, IDENTITY_MATCH, NO_MARKET_EPI_RATING, DISTINCT_FROM_STAGE008")
print("STATUS MANUAL_BUILDER_REVIEW_REQUIRED; NO_FIT_AUTHORISED")
