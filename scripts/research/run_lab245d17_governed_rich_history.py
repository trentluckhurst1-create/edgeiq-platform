from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\parallel_lane_001\run_parallel_lane_001_new_pit_information_search.py")
print("D37_CODEX_CONNECTION_CONTRACT_EXTRACTION",p.exists())
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
keys=("connection","jockey","trainer","prior_date","strict","carry","shift","expanding")
seen=set()
for i,line in enumerate(lines,1):
 if any(k in line.lower() for k in keys):
  lo=max(1,i-5);hi=min(len(lines),i+8)
  if (lo,hi) in seen: continue
  seen.add((lo,hi));print(f"===== {lo}-{hi} =====")
  for j in range(lo,hi+1):print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
