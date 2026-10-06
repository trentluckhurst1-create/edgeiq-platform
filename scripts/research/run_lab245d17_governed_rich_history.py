from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\parallel_lane_001\run_parallel_lane_001_new_pit_information_search.py")
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
print("D39_LOCATE_PL001_DATA_AUTHORITIES_AND_ENCODER")
for lo,hi in [(1,130),(185,258),(384,405)]:
 print(f"===== {lo}-{hi} =====")
 for j in range(lo,hi+1): print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
