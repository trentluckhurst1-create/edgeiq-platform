import { useState } from "react";
import { EdgeiqOsHome } from "../home/EdgeiqOsHome";
import { type GlobalSection } from "./components/AppNavigation";
import { EpiRatingsWorkspace } from "./components/EpiRatingsWorkspace";
import { FieldWorkspace } from "./components/FieldWorkspace";
import { FormWorkspace } from "./components/FormWorkspace";
import { MarketWorkspace } from "./components/MarketWorkspace";
import { MeetingsWorkspace } from "./components/MeetingsWorkspace";
import { OverviewWorkspace } from "./components/OverviewWorkspace";
import { PerformanceWorkspace } from "./components/PerformanceWorkspace";
import { RaceWorkspace } from "./components/RaceWorkspace";
import {
  CompareWorkspace,
  InsightsWorkspace,
  ResearchLabWorkspace,
  ResultsWorkspace,
  ReviewWorkspace,
  SettingsWorkspace,
} from "./components/RemainingWorkspaces";
import { SpeedMapWorkspace } from "./components/SpeedMapWorkspace";
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
  const [selectedRaceKey, setSelectedRaceKey] = useState<string | null>(null);

  function selectMeeting(meeting: ThreeDayMeeting | null) {
    setSelectedMeeting(meeting);
    if (!meeting) {
      setSelectedRaceKey(null);
      return;
    }
    if (!selectedRaceKey || !meeting.races.some((race) => race.raceKey === selectedRaceKey)) {
      setSelectedRaceKey(meeting.races[0]?.raceKey ?? null);
    }
  }

  const raceProps = { meeting: selectedMeeting, selectedRaceKey, onRaceChange: setSelectedRaceKey };

  return (
    <WorkspaceShell activeSection={activeSection} onSectionChange={setActiveSection}>
      {activeSection === "home" ? (
        <EdgeiqOsHome onOpenMeetings={() => setActiveSection("meetings")} />
      ) : activeSection === "meetings" ? (
        <MeetingsWorkspace
          selectedDayKey={selectedDayKey}
          selectedMeetingKey={selectedMeeting?.meetingKey ?? null}
          clean={clean}
          onDayChange={setSelectedDayKey}
          onSelectMeeting={selectMeeting}
          onOpenMeeting={selectMeeting}
          onOpenRace={(meeting, race) => {
            setSelectedMeeting(meeting);
            setSelectedRaceKey(race.raceKey);
            setActiveSection("race");
          }}
        />
      ) : activeSection === "race" ? (
        <RaceWorkspace {...raceProps} onBackToMeetings={() => setActiveSection("meetings")} />
      ) : activeSection === "field" ? (
        <FieldWorkspace {...raceProps} />
      ) : activeSection === "formGuide" ? (
        <FormWorkspace {...raceProps} />
      ) : activeSection === "performance" ? (
        <PerformanceWorkspace {...raceProps} />
      ) : activeSection === "epi" ? (
        <EpiRatingsWorkspace {...raceProps} />
      ) : activeSection === "map" ? (
        <SpeedMapWorkspace {...raceProps} />
      ) : activeSection === "market" ? (
        <MarketWorkspace {...raceProps} />
      ) : activeSection === "overview" ? (
        <OverviewWorkspace {...raceProps} />
      ) : activeSection === "insights" ? (
        <InsightsWorkspace {...raceProps} />
      ) : activeSection === "results" ? (
        <ResultsWorkspace {...raceProps} />
      ) : activeSection === "review" ? (
        <ReviewWorkspace {...raceProps} />
      ) : activeSection === "lab" ? (
        <ResearchLabWorkspace />
      ) : activeSection === "compare" ? (
        <CompareWorkspace />
      ) : activeSection === "settings" ? (
        <SettingsWorkspace />
      ) : null}
    </WorkspaceShell>
  );
}
