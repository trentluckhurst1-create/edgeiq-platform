import { useState } from "react";
import { EdgeiqOsHome } from "../home/EdgeiqOsHome";
import { type GlobalSection } from "./components/AppNavigation";
import { MeetingsWorkspace } from "./components/MeetingsWorkspace";
import { WorkspaceShell } from "./components/WorkspaceShell";
import type { ThreeDayMeeting } from "./services/threeDayCatalog";
import type { MeetingsDayKey } from "./services/meetingsFeed";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  return text || "-";
}

export function RaceFileV3() {
  const [activeSection, setActiveSection] = useState<GlobalSection>("home");
  const [selectedDayKey, setSelectedDayKey] = useState<MeetingsDayKey>("TODAY");
  const [selectedMeeting, setSelectedMeeting] = useState<ThreeDayMeeting | null>(null);

  return (
    <WorkspaceShell activeSection={activeSection} onSectionChange={setActiveSection}>
      {activeSection === "home" ? (
        <EdgeiqOsHome onOpenMeetings={() => setActiveSection("meetings")} />
      ) : (
        <MeetingsWorkspace
          selectedDayKey={selectedDayKey}
          selectedMeetingKey={selectedMeeting?.meetingKey ?? null}
          clean={clean}
          onDayChange={setSelectedDayKey}
          onSelectMeeting={setSelectedMeeting}
          onOpenMeeting={(meeting) => setSelectedMeeting(meeting)}
          onOpenRace={(meeting) => setSelectedMeeting(meeting)}
        />
      )}
    </WorkspaceShell>
  );
}
