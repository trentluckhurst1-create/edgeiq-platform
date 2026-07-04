from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = """  isScratched: boolean;
  paceAdj: number;
"""

new = """  isScratched: boolean;

  runStyleCluster?: string;
  tempoFit?: string;
  sectionalWeaponScore?: number;
  latePowerIndex?: number;
  fatigueRiskIndex?: number;
  projectedTempoShape?: string;
  paceCollapseRisk?: string;

  paceAdj: number;
"""

if old not in text:
    raise SystemExit("Runner type anchor not found. Paste first 45 lines.")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("PATCHED Runner TYPE WITH SECTIONAL FIELDS")
