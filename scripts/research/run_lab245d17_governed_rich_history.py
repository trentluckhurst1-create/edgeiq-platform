from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_031\build_certified_current_context_031.py")
lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
print("D33_LAB031_TARGET_AND_FIELD_SIZE_AUDIT")
for lo,hi in [(1,140),(140,205),(405,430)]:
 print(f"===== LINES {lo}-{hi} =====")
 for j in range(lo,min(hi,len(lines))+1): print((f"{j}: {lines[j-1]}").encode("ascii","backslashreplace").decode("ascii"))
