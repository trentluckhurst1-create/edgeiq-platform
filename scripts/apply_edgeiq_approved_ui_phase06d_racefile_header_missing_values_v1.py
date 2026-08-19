from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE06D_RACEFILE_HEADER_MISSING_VALUES_{STAMP}"
TARGET = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"

CHECKPOINT.mkdir(parents=True, exist_ok=True)
shutil.copy2(TARGET, CHECKPOINT / TARGET.name)

text = TARGET.read_text(encoding="utf-8")

old = '''  const raceNumber = clean(official.raceNumber);
  const meetingName = clean(official.meeting);
  const raceClass = clean(official.class) || clean(official.raceClass);
  const distance = clean(official.distance);
  const trackCondition = clean(official.trackCondition) || clean(official.condition);
  const raceDate = clean(official.date) || clean(official.raceDate);
  const raceTime = clean(official.time) || clean(official.localTime);
  const surface = clean(official.surface) || clean(official.trackType);
  const prizeMoneyRaw = clean(official.prizeMoney) || clean(official.totalPrizeMoney);
  const prizeMoney = /^race file$/i.test(prizeMoneyRaw) ? "" : prizeMoneyRaw;
  const raceTitle = clean(official.raceName) || clean(official.name);
'''

new = '''  const headerValue = (value: any) => {
    const text = clean(value);
    if (!text || text === "-" || /^not supplied$/i.test(text) || /^unavailable$/i.test(text)) return "";
    if (/^race file$/i.test(text)) return "";
    return text;
  };
  const raceNumber = headerValue(official.raceNumber);
  const meetingName = headerValue(official.meeting);
  const raceClass = headerValue(official.class) || headerValue(official.raceClass);
  const distance = headerValue(official.distance);
  const trackCondition = headerValue(official.trackCondition) || headerValue(official.condition);
  const raceDate = headerValue(official.date) || headerValue(official.raceDate);
  const raceTime = headerValue(official.time) || headerValue(official.localTime);
  const surface = headerValue(official.surface) || headerValue(official.trackType);
  const prizeMoney = headerValue(official.prizeMoney) || headerValue(official.totalPrizeMoney);
  const raceTitle = headerValue(official.raceName) || headerValue(official.name);
'''

if old not in text:
    raise SystemExit("Expected RaceWorkspace header value block not found; source changed unexpectedly.")

TARGET.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

print(f"Checkpoint: {CHECKPOINT}")
print(f"Changed: {TARGET}")
print("EDGEIQ_APPROVED_UI_PHASE06D_RACEFILE_HEADER_MISSING_VALUES_PASS")
