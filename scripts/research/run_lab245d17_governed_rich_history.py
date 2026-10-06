from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\build_certified_current_context_031.py")
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
print("D36_TRACK_LAYOUT_CONTEXT_INVENTORY")
for lo,hi in [(1,55),(94,138),(240,275),(285,330)]:
 print(f"===== {lo}-{hi} =====")
 for j in range(lo,hi+1):
  print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
