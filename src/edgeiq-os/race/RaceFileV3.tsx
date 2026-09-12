import { useEffect, useRef, useState } from "react";
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
import { loadRaceDetail } from "./services/raceDetailFeed";
import type { ThreeDayMeeting } from "./services/threeDayCatalog";
import type { MeetingsDayKey } from "./services/meetingsFeed";

const RACE_SCOPED_SECTIONS: GlobalSection[] = ["race", "field", "formGuide", "performance", "epi", "map", "market", "overview", "insights", "results", "review"];

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  return text || "-";
}

export function RaceFileV3() {
  const [activeSection, setActiveSection] = useState<GlobalSection>("home");
  const [selectedDayKey, setSelectedDayKey] = useState<MeetingsDayKey>("TODAY");
  const [selectedMeeting, setSelectedMeeting] = useState<ThreeDayMeeting | null>(null);
  const [selectedRaceKey, setSelectedRaceKey] = useState<string | null>(null);
  const hydrationRef = useRef("");

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

  useEffect(() => {
    if (!selectedMeeting || !selectedRaceKey || !RACE_SCOPED_SECTIONS.includes(activeSection)) return;
    const currentRace = selectedMeeting.races.find((race) => race.raceKey === selectedRaceKey);
    if (!currentRace || currentRace.runners.length > 0) return;

    const hydrationKey = `${selectedMeeting.date}|${selectedMeeting.meetingKey}|${selectedRaceKey}`;
    if (hydrationRef.current === hydrationKey) return;
    hydrationRef.current = hydrationKey;

    let active = true;
    loadRaceDetail(selectedMeeting.date, selectedMeeting.meetingKey, selectedRaceKey)
      .then((raceDetail) => {
        if (!active) return;
        setSelectedMeeting((current) => {
          if (!current || current.meetingKey !== selectedMeeting.meetingKey) return current;
          return { ...current, races: current.races.map((race) => race.raceKey === raceDetail.raceKey ? raceDetail : race) };
        });
      })
      .catch(() => undefined)
      .finally(() => {
        if (hydrationRef.current === hydrationKey) hydrationRef.current = "";
      });

    return () => { active = false; };
  }, [activeSection, selectedMeeting, selectedRaceKey]);

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
