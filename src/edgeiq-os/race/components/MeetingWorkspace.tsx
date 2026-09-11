import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import { loadRaceDetail } from "../services/raceDetailFeed";
import {
  MEETING_DETAIL_TAB_ORDER,
  buildMeetingConditionStripForRace,
  buildMeetingDetailSelectedRace,
  buildMeetingDetailViewModel,
  type MeetingDetailSelectedRace,
  type MeetingDetailTab,
  type MeetingDetailValue,
} from "../services/meetingDetailFeed";
import { MeetingGearChangesWorkspace } from "./MeetingGearChangesWorkspace";
import { MeetingResultsWorkspace } from "./MeetingResultsWorkspace";
import { MeetingScratchingsWorkspace } from "./MeetingScratchingsWorkspace";
import { MeetingTrackWorkspace } from "./MeetingTrackWorkspace";
import { MeetingWeatherWorkspace } from "./MeetingWeatherWorkspace";

type MeetingWorkspaceProps = {
  raceBook: any;
  meeting: ThreeDayMeeting;
  clean: (value: any) => string;
  onBackToMeetings: () => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
};

const meetingMountedComponentByTab: Record<MeetingDetailTab, string> = {
  RACES: "MeetingWorkspace",
  SCRATCHINGS: "MeetingScratchingsWorkspace",
  GEAR_CHANGES: "MeetingGearChangesWorkspace",
  TRACK: "MeetingTrackWorkspace",
  WEATHER: "MeetingWeatherWorkspace",
  RESULTS: "MeetingResultsWorkspace",
};

function DetailGrid({ details }: { details: MeetingDetailValue[] }) {
  return (
    <dl className="eiq-meeting-v1-detail-grid">
      {details.map((detail) => (
        <div key={detail.label} className={detail.tone ? `is-${detail.tone}` : ""}>
          <dt>{detail.label}</dt>
          <dd>{detail.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function SummaryStrip({ items }: { items: MeetingDetailValue[] }) {
  return (
    <section className="eiq-meeting-v1-summary-strip" aria-label="Meeting summary">
      {items.map((item) => (
        <div key={item.label} className={item.tone ? `is-${item.tone}` : ""}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}

function PendingTab({ label, message }: { label: string; message: string }) {
  return (
    <section className="eiq-meeting-v1-pending" aria-label={`${label} pending`}>
      <span>{label}</span>
      <strong>{message}</strong>
    </section>
  );
}

function formatMeetingConditionLabel(label: string): string {
  const displayLabels: Record<string, string> = {
    TEMPERATURE: "TEMP",
    "RAIN 24H": "RAIN",
    "IRRIGATION 24H": "IRRIGATION",
  };
  return displayLabels[label.trim().toUpperCase()] ?? label;
}

function trackConditionClass(value: string): string {
  const text = value.toLowerCase();
  if (/firm\s*[12]|\bfirm\b/.test(text)) return "is-firm";
  if (/good\s*[34]|\bgood\b/.test(text)) return "is-good";
  if (/soft\s*[5-7]|\bsoft\b/.test(text)) return "is-soft";
  if (/heavy\s*(8|9|10)|\bheavy\b/.test(text)) return "is-heavy";
  return "";
}

function MeetingConditionStrip({ meeting, selected }: { meeting: ThreeDayMeeting; selected: MeetingDetailSelectedRace | null }) {
  const conditionStrip = buildMeetingConditionStripForRace(meeting, selected?.row.race ?? null);
  return (
    <section className="eiq-meeting-v1-condition-strip" aria-label="Meeting condition strip">
      {conditionStrip.filter((item) => item.label.trim().toUpperCase() !== "OFFICIAL UPDATE").map((item) => {
        const isTrack = item.label.trim().toUpperCase() === "TRACK";
        return (
          <div key={item.label} className={[item.tone ? `is-${item.tone}` : "", isTrack ? trackConditionClass(item.value) : ""].filter(Boolean).join(" ")}>
            <span>{formatMeetingConditionLabel(item.label)}</span>
            <strong>{item.value}</strong>
          </div>
        );
      })}
    </section>
  );
}

function RacesTable({ model, selectedRaceKey, onSelectRace, onOpenRace, loadingRaceKey }: {
  model: ReturnType<typeof buildMeetingDetailViewModel>;
  selectedRaceKey: string;
  onSelectRace: (raceKey: string) => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
  loadingRaceKey: string;
}) {
  return (
    <section className="eiq-meeting-v1-panel">
      <header><div><span>RACES</span><strong>Meeting race list</strong></div></header>
      <div className="eiq-meeting-v1-table-scroll">
        <table className="eiq-meeting-v1-table">
          <thead><tr><th>RACE</th><th>TIME</th><th className="is-left">RACE NAME</th><th>DIST</th><th>CLASS</th><th>FIELD</th><th>SCR</th><th>STATUS</th></tr></thead>
          <tbody>
            {model.races.map((row) => (
              <tr key={row.raceKey} className={selectedRaceKey === row.raceKey ? "is-selected" : ""} role="button" tabIndex={0} aria-label={`Open ${row.raceLabel} ${row.raceName}`}
                onClick={() => { onSelectRace(row.raceKey); onOpenRace(row.race, row.raceIndex); }}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelectRace(row.raceKey); onOpenRace(row.race, row.raceIndex); } }}>
                <td>{loadingRaceKey === row.raceKey ? "…" : row.raceLabel.replace(/^R/i, "")}</td>
                <td>{row.time}</td>
                <td className="is-left"><strong>{row.raceName}</strong></td>
                <td>{row.distance}</td><td>{row.raceClass}</td><td>{row.fieldSize}</td><td>{row.scratchings}</td>
                <td className={row.statusTone ? `is-${row.statusTone}` : ""}>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SelectedRacePanel({ selected }: { selected: MeetingDetailSelectedRace | null }) {
  if (!selected) return <section className="eiq-meeting-v1-panel eiq-meeting-v1-selected-race"><header><div><span>SELECTED RACE</span><strong>No race selected</strong></div></header></section>;
  return (
    <section className="eiq-meeting-v1-panel eiq-meeting-v1-selected-race">
      <header><div><span>SELECTED RACE</span><strong>{selected.row.raceLabel} - {selected.row.raceName}</strong></div><p>{selected.row.secondary || "Race details not supplied"}</p></header>
      <DetailGrid details={selected.details} />
    </section>
  );
}

function RacesTab({ model, selected, selectedRaceKey, setSelectedRaceKey, onOpenRace, loadingRaceKey }: {
  model: ReturnType<typeof buildMeetingDetailViewModel>;
  selected: MeetingDetailSelectedRace | null;
  selectedRaceKey: string;
  setSelectedRaceKey: (raceKey: string) => void;
  onOpenRace: (race: ThreeDayRace, index: number) => void;
  loadingRaceKey: string;
}) {
  return (
    <div className="eiq-meeting-v1-main-stack">
      <RacesTable model={model} selectedRaceKey={selectedRaceKey} onSelectRace={setSelectedRaceKey} onOpenRace={onOpenRace} loadingRaceKey={loadingRaceKey} />
      <SelectedRacePanel selected={selected} />
    </div>
  );
}

export function MeetingWorkspace({ raceBook, meeting, clean, onBackToMeetings, onOpenRace }: MeetingWorkspaceProps) {
  void raceBook;
  void clean;

  const model = useMemo(() => buildMeetingDetailViewModel(meeting), [meeting]);
  const [tab, setTab] = useState<MeetingDetailTab>("RACES");
  const [selectedRaceKey, setSelectedRaceKey] = useState(model.races[0]?.raceKey ?? "");
  const [loadingRaceKey, setLoadingRaceKey] = useState("");
  const [raceLoadError, setRaceLoadError] = useState("");

  const selected = useMemo(() => buildMeetingDetailSelectedRace(model, meeting, selectedRaceKey), [model, meeting, selectedRaceKey]);

  useEffect(() => {
    if (!model.races.some((race) => race.raceKey === selectedRaceKey)) setSelectedRaceKey(model.races[0]?.raceKey ?? "");
  }, [model, selectedRaceKey]);

  async function openRaceOnDemand(race: ThreeDayRace, index: number) {
    setLoadingRaceKey(race.raceKey);
    setRaceLoadError("");
    try {
      const fullRace = await loadRaceDetail(meeting.date, meeting.meetingKey, race.raceKey);
      onOpenRace(fullRace, index);
    } catch (error) {
      setRaceLoadError(error instanceof Error ? error.message : "Race detail unavailable");
    } finally {
      setLoadingRaceKey("");
    }
  }

  const activePending = MEETING_DETAIL_TAB_ORDER.find((item) => item.key === tab && item.key !== "RACES");

  return (
    <section className="eiq-meeting-workspace eiq-meeting-v1" data-edgeiq-workspace-key={tab} data-edgeiq-mounted-component={meetingMountedComponentByTab[tab]}>
      <header className="eiq-meeting-v1-hero">
        <div><span>MEETING DETAIL</span><h2>{model.meetingName}</h2><p>{model.venueLine}</p>{raceLoadError ? <p role="alert">{raceLoadError}</p> : null}</div>
        <button type="button" onClick={onBackToMeetings}>Back to Meetings</button>
      </header>

      <SummaryStrip items={model.summary} />
      <MeetingConditionStrip meeting={meeting} selected={selected} />

      <nav className="eiq-context-tabs eiq-meeting-v1-tabs" aria-label="Meeting workspace navigation" role="tablist">
        {MEETING_DETAIL_TAB_ORDER.map((item) => (
          <button key={item.key} type="button" role="tab" aria-selected={tab === item.key} className={tab === item.key ? "is-active" : ""} onClick={() => setTab(item.key)}>{item.label}</button>
        ))}
      </nav>

      <div className="eiq-meeting-v1-layout">
        <main>
          {tab === "RACES" ? (
            <RacesTab model={model} selected={selected} selectedRaceKey={selectedRaceKey} setSelectedRaceKey={setSelectedRaceKey} onOpenRace={(race, index) => void openRaceOnDemand(race, index)} loadingRaceKey={loadingRaceKey} />
          ) : tab === "SCRATCHINGS" ? (
            <MeetingScratchingsWorkspace meeting={meeting} />
          ) : tab === "GEAR_CHANGES" ? (
            <MeetingGearChangesWorkspace meeting={meeting} />
          ) : tab === "TRACK" ? (
            <MeetingTrackWorkspace meeting={meeting} />
          ) : tab === "WEATHER" ? (
            <MeetingWeatherWorkspace meeting={meeting} />
          ) : tab === "RESULTS" ? (
            <MeetingResultsWorkspace meeting={meeting} />
          ) : activePending ? (
            <PendingTab label={activePending.label} message={activePending.pendingMessage ?? model.pendingTabs[tab]} />
          ) : null}
        </main>
      </div>
    </section>
  );
}
