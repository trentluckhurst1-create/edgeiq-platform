from pathlib import Path
p=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_lab_045a\model_lab_045a_weight_semantics.py")
lines=p.read_text(encoding="utf-8",errors="ignore").splitlines()
print("V2_STAGE019C_CONTRACT LAB045A_BUILDER_EXACT_SEMANTICS NO_MODEL 2025_2026_SEALED")
for lo,hi in [(1,80),(80,140),(140,205)]:
 print("V2_STAGE019C_BLOCK",lo,hi)
 for i in range(lo-1,min(hi,len(lines))):print(f"{i+1:04d}",lines[i])
print("V2_STAGE019C_COMPLETE")
