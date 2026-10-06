from pathlib import Path
root=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\parallel_lane_002")
print("D41_PL002_CONTRACT_LOCATOR")
print("FILES")
for p in sorted(root.glob("*")): print(p.name,p.stat().st_size)
for p in sorted(root.glob("*.py")):
 print("===== SCRIPT",p.name,"=====")
 lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
 for i,line in enumerate(lines,1):
  low=line.lower()
  if any(k in low for k in ["prep","recency","spell","days_since","run_number","first_up","second_up","third_up","architecture","pbc_plus","feature"]):
   lo=max(1,i-4);hi=min(len(lines),i+8)
   for j in range(lo,hi+1): print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
