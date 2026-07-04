from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

old = ".sort((a, b) => a.spd - b.spd || a.barrier - b.barrier);"
new = ".sort((a, b) => b.barrier - a.barrier || a.spd - b.spd);"

if old not in text:
    old = ".sort((a, b) => b.barrier - a.barrier || a.spd - b.spd);"

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("SPEED MAP SORTED BY BARRIER: OUTSIDE TOP, BARRIER 1 BOTTOM")
