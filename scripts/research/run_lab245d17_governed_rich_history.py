from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\build_certified_current_context_031.py")
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
print("D34_EXACT_BARRIER_PROVENANCE")
for lo,hi in [(55,95),(138,150),(405,425)]:
 print(f"===== {lo}-{hi} =====")
 for j in range(lo,hi+1):
  q=(f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii")
  print(q)
