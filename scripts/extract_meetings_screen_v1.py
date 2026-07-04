from pathlib import Path
import re

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

start_marker = 'if (productView === "MEETINGS") {'
next_marker = ' if (!raceRows.length || !header) {'

start = text.index(start_marker)
next_start = text.index(next_marker, start)

meetings_block = text[start:next_start]

inner = meetings_block[len(start_marker):]
inner = re.sub(r'\n\s*\}\s*\n\s*$', '\n', inner)

meetings_file = root / "src" / "screens" / "MeetingsScreen.tsx"
meetings_file.write_text(
'''import React from "react";

type MeetingsScreenProps = {
  productShellMeetings: any[];
  productShellRaces: any[];
  selectedShellMeeting: any;
  selectedShellMeetingRaces: any[];
  runnerRows: any[];
  shellTrack: any;
  shellRaceNo: any;
  pageStyle: React.CSSProperties;
  intelModeTabs: any[];
  updateProductView: (view: any) => void;
  openShellMeeting: (meetingKey: any) => void;
  openShellRace: (race: any) => void;
  setShellMeetingKey: (meetingKey: any) => void;
  setIntelMode: (mode: any) => void;
};

export function MeetingsScreen({
  productShellMeetings,
  productShellRaces,
  selectedShellMeeting,
  selectedShellMeetingRaces,
  runnerRows,
  shellTrack,
  shellRaceNo,
  pageStyle,
  intelModeTabs,
  updateProductView,
  openShellMeeting,
  openShellRace,
  setShellMeetingKey,
  setIntelMode,
}: MeetingsScreenProps) {
''' + inner + '''
}
''',
encoding="utf-8"
)

replacement = '''if (productView === "MEETINGS") {
  return (
    <MeetingsScreen
      productShellMeetings={productShellMeetings}
      productShellRaces={productShellRaces}
      selectedShellMeeting={selectedShellMeeting}
      selectedShellMeetingRaces={selectedShellMeetingRaces}
      runnerRows={runnerRows}
      shellTrack={shellTrack}
      shellRaceNo={shellRaceNo}
      pageStyle={pageStyle}
      intelModeTabs={intelModeTabs}
      updateProductView={updateProductView}
      openShellMeeting={openShellMeeting}
      openShellRace={openShellRace}
      setShellMeetingKey={setShellMeetingKey}
      setIntelMode={setIntelMode}
    />
  );
}

'''

text = text[:start] + replacement + text[next_start:]

if 'import { MeetingsScreen } from "../screens/MeetingsScreen";' not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, 'import { MeetingsScreen } from "../screens/MeetingsScreen";')
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")

print("[MEETINGS_EXTRACT] complete")
print(f"created={meetings_file}")
print(f"updated={path}")
