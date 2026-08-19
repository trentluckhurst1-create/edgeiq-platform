from pathlib import Path
import re

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = re.sub(
    r"type SpeedMapTabProps = \{",
    """type SpeedMapTabProps = {
  biasProfile?: any[];
  raceDistance?: string | number | null;
  trackCondition?: string;
""",
    text,
    count=1,
)

path.write_text(text, encoding="utf-8")

print("PATCHED SPEEDMAP PROP TYPES")
