from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\parallel_lane_001\run_parallel_lane_001_new_pit_information_search.py")
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
print("D38_CODEX_EXACT_CONNECTION_IMPLEMENTATION")
for lo,hi in [(250,325),(334,385),(400,475),(475,545)]:
 print(f"===== {lo}-{hi} =====")
 for j in range(lo,hi+1):
  print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
