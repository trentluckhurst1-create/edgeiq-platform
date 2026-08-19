from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"

text = PATH.read_text(encoding="utf-8-sig")

meetings_pattern = re.compile(
    r'''<MeetingsWorkspace\s+
        raceBook=\{file\.raceBook\}\s+
        field=\{file\.field\}\s+
        clean=\{clean\}\s+
        onOpenMeeting=\{\(\)\s*=>\s*setViewLevel\("meeting"\)\}\s*
        />''',
    re.VERBOSE,
)

meetings_replacement = '''<MeetingsWorkspace
            clean={clean}
            onOpenMeeting={(meeting) => {
              setSelectedMeeting(meeting);
              setSelectedRace(null);
              setSelectedRunnerIndex(0);
              setViewLevel("meeting");
            }}
          />'''

text, meetings_count = meetings_pattern.subn(
    meetings_replacement,
    text,
    count=1,
)

meeting_pattern = re.compile(
    r'''<MeetingWorkspace\s+
        raceBook=\{file\.raceBook\}\s+
        field=\{file\.field\}\s+
        clean=\{clean\}\s+
        onBackToMeetings=\{\(\)\s*=>\s*setViewLevel\("meetings"\)\}\s+
        onOpenRace=\{\(\)\s*=>\s*setViewLevel\("race"\)\}\s*
        />''',
    re.VERBOSE,
)

meeting_replacement = '''<MeetingWorkspace
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
          />'''

text, meeting_count = meeting_pattern.subn(
    meeting_replacement,
    text,
    count=1,
)

# Fallback replacements if formatting prevented the regex match.
if meetings_count == 0:
    start = text.find("<MeetingsWorkspace")

    if start >= 0:
        end = text.find("/>", start)

        if end >= 0:
            block = text[start:end + 2]

            if "raceBook={file.raceBook}" in block:
                text = text[:start] + meetings_replacement + text[end + 2:]
                meetings_count = 1

if meeting_count == 0:
    start = text.find("<MeetingWorkspace")

    if start >= 0:
        end = text.find("/>", start)

        if end >= 0:
            block = text[start:end + 2]

            if "field={file.field}" in block:
                text = text[:start] + meeting_replacement + text[end + 2:]
                meeting_count = 1

if meetings_count != 1:
    raise RuntimeError(
        "Could not repair the MeetingsWorkspace render block."
    )

if meeting_count != 1:
    raise RuntimeError(
        "Could not repair the MeetingWorkspace render block."
    )

PATH.write_text(text, encoding="utf-8")

print("[EDGEIQ] MeetingsWorkspace props repaired")
print("[EDGEIQ] MeetingWorkspace props repaired")
