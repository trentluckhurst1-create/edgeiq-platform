from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src/edgeiq-os/race/RaceFileV3.tsx"

text = PATH.read_text(encoding="utf-8-sig")

text = text.replace(
    'import { Fragment, type ReactNode, useMemo, useState } from "react";',
    'import { Fragment, type ReactNode, useMemo, useState } from "react";\n'
    'import type { ThreeDayMeeting, ThreeDayRace } from "./services/threeDayCatalog";',
    1,
)

text = text.replace(
    "const file = RaceFileService.buildRaceBook();\n"
    "const primary = file.field[0];",
    "const baseFile = RaceFileService.buildRaceBook();",
    1,
)

component_start = """export function RaceFileV3() {
    const [activeSection, setActiveSection] = useState<GlobalSection>("meetings");
    const [viewLevel, setViewLevel] = useState<ViewLevel>("meetings");
    const [selectedRunnerIndex, setSelectedRunnerIndex] = useState(0);
"""

component_replacement = """export function RaceFileV3() {
    const [activeSection, setActiveSection] = useState<GlobalSection>("meetings");
    const [viewLevel, setViewLevel] = useState<ViewLevel>("meetings");
    const [selectedMeeting, setSelectedMeeting] = useState<ThreeDayMeeting | null>(null);
    const [selectedRace, setSelectedRace] = useState<ThreeDayRace | null>(null);
    const [selectedRunnerIndex, setSelectedRunnerIndex] = useState(0);
"""

if component_start not in text:
    raise RuntimeError("RaceFileV3 state insertion point was not found.")

text = text.replace(
    component_start,
    component_replacement,
    1,
)

state_anchor = """    const [mode, setMode] = useState<WorkbenchMode>("profile");
    const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>("sameClass");
    const selectedRunner = file.field[selectedRunnerIndex] ?? primary;
"""

state_replacement = """    const [mode, setMode] = useState<WorkbenchMode>("profile");
    const [sectionalStandard, setSectionalStandard] = useState<SectionalStandard>("sameClass");

    const file = useMemo(() => {
      if (!selectedMeeting || !selectedRace) {
        return baseFile;
      }

      const catalogueField =
        selectedRace.runners?.length > 0
          ? selectedRace.runners
          : [];

      return {
        ...baseFile,
        raceBook: {
          ...baseFile.raceBook,
          official: {
            ...baseFile.raceBook.official,
            meeting: selectedMeeting.meeting,
            date: selectedMeeting.date,
            meetingDate: selectedMeeting.date,
            raceNumber: selectedRace.raceNumber,
            raceName: selectedRace.raceName,
            distance: selectedRace.distance ?? "",
            raceClass: selectedRace.raceClass ?? "",
            officialRaceTime: selectedRace.raceTime ?? "",
            trackCondition:
              selectedRace.trackCondition ??
              selectedMeeting.trackCondition ??
              "",
            rail:
              selectedRace.rail ??
              selectedMeeting.rail ??
              "",
            fieldSize: catalogueField.length,
          },
        },
        field: catalogueField,
      };
    }, [selectedMeeting, selectedRace]);

    const primary = file.field[0];
    const selectedRunner = file.field[selectedRunnerIndex] ?? primary;
"""

if state_anchor not in text:
    raise RuntimeError("RaceFileV3 active-file insertion point was not found.")

text = text.replace(
    state_anchor,
    state_replacement,
    1,
)

old_meetings = """          <MeetingsWorkspace
            raceBook={file.raceBook}
            field={file.field}
            clean={clean}
            onOpenMeeting={() => setViewLevel("meeting")}
          />"""

new_meetings = """          <MeetingsWorkspace
            clean={clean}
            onOpenMeeting={(meeting) => {
              setSelectedMeeting(meeting);
              setSelectedRace(null);
              setSelectedRunnerIndex(0);
              setViewLevel("meeting");
            }}
          />"""

if old_meetings not in text:
    raise RuntimeError("MeetingsWorkspace render block was not found.")

text = text.replace(
    old_meetings,
    new_meetings,
    1,
)

old_meeting = """          <MeetingWorkspace
            raceBook={file.raceBook}
            field={file.field}
            clean={clean}
            onBackToMeetings={() => setViewLevel("meetings")}
            onOpenRace={() => setViewLevel("race")}
          />"""

new_meeting = """          <MeetingWorkspace
            raceBook={file.raceBook}
            meeting={selectedMeeting!}
            clean={clean}
            onBackToMeetings={() => {
              setSelectedMeeting(null);
              setSelectedRace(null);
              setSelectedRunnerIndex(0);
              setViewLevel("meetings");
            }}
            onOpenRace={(race) => {
              setSelectedRace(race);
              setSelectedRunnerIndex(0);
              setMode("profile");
              setViewLevel("race");
            }}
          />"""

if old_meeting not in text:
    raise RuntimeError("MeetingWorkspace render block was not found.")

text = text.replace(
    old_meeting,
    new_meeting,
    1,
)

PATH.write_text(text, encoding="utf-8")

print("[EDGEIQ] RaceFileV3 selected meeting/race routing wired")
