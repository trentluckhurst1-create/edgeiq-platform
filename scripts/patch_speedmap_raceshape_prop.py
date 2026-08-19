from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
"""  paceRows?: RawRow[];
  raceDistance?: string | number | null;""",
"""  paceRows?: RawRow[];
  raceShape?: RawRow | null;
  raceDistance?: string | number | null;"""
)

text = text.replace(
"""export default function SpeedMapTab({ data = [], selectedMeeting, selectedHorse, onSelectHorse, biasProfile = [], paceRows = [], raceDistance, trackCondition }: SpeedMapTabProps) {""",
"""export default function SpeedMapTab({ data = [], selectedMeeting, selectedHorse, onSelectHorse, biasProfile = [], paceRows = [], raceShape = null, raceDistance, trackCondition }: SpeedMapTabProps) {"""
)

path.write_text(text, encoding="utf-8")
print("PATCHED SpeedMapTab raceShape prop")
