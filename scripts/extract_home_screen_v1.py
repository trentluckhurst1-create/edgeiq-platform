from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

start_marker = ' if (productView === "HOME") {'
next_marker = 'if (productView === "MEETINGS") {'

start = text.index(start_marker)
next_start = text.index(next_marker, start)

home_block = text[start:next_start]

# Remove wrapping if statement and final closing brace
inner = home_block[len(start_marker):]
inner = re.sub(r'\n\s*\}\s*\n\s*$', '\n', inner)

home_file = root / "src" / "screens" / "HomeScreen.tsx"
home_file.write_text(
'''import React from "react";

type HomeScreenProps = {
  productShellMeetings: any[];
  updateProductView: (view: any) => void;
  shellTrack: any;
  shellRaceNo: any;
  setIntelMode: (mode: any) => void;
  openShellMeeting: (meetingKey: any) => void;
};

export function HomeScreen({
  productShellMeetings,
  updateProductView,
  shellTrack,
  shellRaceNo,
  setIntelMode,
  openShellMeeting,
}: HomeScreenProps) {
''' + inner + '''
}
''',
encoding="utf-8"
)

replacement = ''' if (productView === "HOME") {
  return (
    <HomeScreen
      productShellMeetings={productShellMeetings}
      updateProductView={updateProductView}
      shellTrack={shellTrack}
      shellRaceNo={shellRaceNo}
      setIntelMode={setIntelMode}
      openShellMeeting={openShellMeeting}
    />
  );
}

'''

text = text[:start] + replacement + text[next_start:]

if 'import { HomeScreen } from "../screens/HomeScreen";' not in text:
    text = text.replace('import React', 'import React')
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, 'import { HomeScreen } from "../screens/HomeScreen";')
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")

print("[HOME_EXTRACT] complete")
print(f"created={home_file}")
print(f"updated={path}")
