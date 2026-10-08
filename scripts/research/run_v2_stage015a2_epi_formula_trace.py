from pathlib import Path
P=Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM\outputs\research\model_price_diagnostics\forward_validation\LAB138_UPSTREAM_FORMULA_RECOVERY.txt")
t=P.read_text(encoding="utf-8",errors="ignore");lines=t.splitlines()
keys=("epi_value_026","target_epi_026","runner_lengths_v_standard_026","performance","standard_time","market","starting_price","bsp","odds")
print("V2_STAGE015A2_CONTRACT UPSTREAM_EPI_FORMULA_TRACE NO_MODEL 2025_2026_SEALED")
print("V2_STAGE015A2_LINES",len(lines))
for i,l in enumerate(lines):
 if any(k.lower() in l.lower() for k in keys):
  lo=max(0,i-3);hi=min(len(lines),i+4)
  print("V2_STAGE015A2_HIT",i+1)
  for j in range(lo,hi): print(f"{j+1:06d}: {lines[j][:700]}")
print("V2_STAGE015A2_COMPLETE")
