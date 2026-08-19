from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = re.sub(
r'const laneHeight = .*?;',
'''const laneHeight = 78;
const railOffset = 90;
const wideOffset = 880;
const verticalSpacing = 42;''',
text,
count=1,
flags=re.S
)

text = re.sub(
r'const x = .*?;\s*const y = .*?;',
'''const x =
  runStyle === "LEADER"
    ? railOffset + (idx * 38)
    : runStyle === "ON PACE"
    ? railOffset + 140 + (idx * 34)
    : runStyle === "MIDFIELD"
    ? railOffset + 260 + (idx * 28)
    : railOffset + 420 + (idx * 20);

const y =
  90 +
  (laneIndex * laneHeight) +
  ((idx % 4) * verticalSpacing);''',
text,
count=1,
flags=re.S
)

text = text.replace(
'className={`speedmap-runner ${laneClass}`}',
'className={`speedmap-runner ${laneClass} ${selectedHorse === r.horse ? "selected" : ""}`}'
)

path.write_text(text, encoding="utf-8")

print("FIXED SPEED MAP POSITIONING + STACKING")
