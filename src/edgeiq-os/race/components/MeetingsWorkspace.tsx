import { useEffect, useMemo, useState } from "react";
import type { ThreeDayMeeting, ThreeDayRace } from "../services/threeDayCatalog";
import {
  canonicalRailDisplay,
  canonicalTrackDisplayName,
  canonicalTrackRatingDisplay,
  canonicalWeatherDisplay,
  cleanProductText,
} from "../../design-system/presentation";
import {
  loadMeetingsWorkspaceViewModel,
  type MeetingSummaryViewModel,
  type MeetingsDayKey,
  type MeetingsWorkspaceViewModel,
} from "../services/meetingsFeed";
import {
  buildMeetingScratchingsViewModel,
  type ScratchingRecordViewModel,
} from "../services/scratchingsFeed";
import { MeetingGearChangesWorkspace } from "./MeetingGearChangesWorkspace";
import { MeetingResultsWorkspace } from "./MeetingResultsWorkspace";
import { MeetingTrackWorkspace } from "./MeetingTrackWorkspace";
import { MeetingWeatherWorkspace } from "./MeetingWeatherWorkspace";
import {
  EiqButton,
  EiqDataTable,
  EiqEmptyState,
  EiqLoadingState,
  EiqPanel,
  EiqSectionHeader,
  EiqTabs,
  PageFrame,
  PageHeader,
} from "../../design-system/v1";

type MeetingsWorkspaceProps = {
  selectedDayKey: MeetingsDayKey;
  selectedMeetingKey: string | null;
  clean: (value: any) => string;
  onDayChange: (day: MeetingsDayKey) => void;
  onSelectMeeting: (meeting: ThreeDayMeeting | null) => void;
  onOpenMeeting: (meeting: ThreeDayMeeting) => void;
  onOpenRace: (meeting: ThreeDayMeeting, race: ThreeDayRace, index: number) => void;
};

type MeetingStatusFilter = "Current" | "Completed" | "Abandoned" | "Postponed";
type MeetingDetailTab = "Scratchings" | "Gear Changes" | "Track" | "Weather" | "Results";

const STATUS_FILTERS: MeetingStatusFilter[] = ["Current", "Completed", "Abandoned", "Postponed"];
const MEETING_DETAIL_TABS: MeetingDetailTab[] = ["Scratchings", "Gear Changes", "Track", "Weather", "Results"];

function display(value: unknown, fallback = "Not Supplied"): string {
  return cleanProductText(value, fallback);
}

function displayTrack(value: unknown, fallback = "Not Supplied"): string {
  return canonicalTrackDisplayName(value) || fallback;
}

function shortDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", month: "short" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

function meetingStatusFilter(value: unknown): MeetingStatusFilter {
  const text = String(value ?? "").toLowerCase();
  if (text.includes("abandon")) return "Abandoned";
  if (text.includes("postpon")) return "Postponed";
  if (text.includes("result") || text.includes("complete") || text.includes("finalised")) return "Completed";
  return "Current";
}

function formatScratchDateTime(record: ScratchingRecordViewModel): string {
  return record.scratchedAtDisplay || "Not supplied";
}

function ScratchingsDetail({
  activeDay,
  selectedMeeting,
}: {
  activeDay: MeetingsWorkspaceViewModel["days"][number];
  selectedMeeting: MeetingSummaryViewModel | null;
}) {
  const selectedModel = useMemo(
    () => (selectedMeeting ? buildMeetingScratchingsViewModel(selectedMeeting.rawMeeting) : null),
    [selectedMeeting],
  );
  const selectedRecords = useMemo(
    () => selectedModel?.raceGroups.flatMap((group) => group.records.map((record) => ({ group, record }))) ?? [],
    [selectedModel],
  );
  const totalScratchings = activeDay.meetings.reduce((total, meeting) => total + meeting.scratchings, 0);
  const selectedMeetingName = selectedMeeting ? displayTrack(selectedMeeting.meeting) : "Selected Meeting";
  const selectedCount = selectedModel?.summary.totalScratchings ?? selectedMeeting?.scratchings ?? 0;

  return (
    <div className="eiq-meetings-v3-scratchings" aria-label="Meeting scratchings">
      <EiqPanel density="compact" className="eiq-meetings-v3-scratchings-card">
        <EiqSectionHeader title="Today's Scratchings" />
        <EiqDataTable
          density="compact"
          className="eiq-meetings-v3-scratchings-table"
          wrapperProps={{ className: "eiq-meetings-v3-table-scroll" }}
        >
          <thead>
            <tr>
              <th className="is-left">MEETING</th>
              <th>RACES</th>
              <th>SCRATCHINGS</th>
            </tr>
          </thead>
          <tbody>
            {activeDay.meetings.map((meeting) => (
              <tr key={meeting.meetingKey}>
                <td className="is-left">
                  <strong>{displayTrack(meeting.meeting)}</strong>
                </td>
                <td>{meeting.races}</td>
                <td>{meeting.scratchings}</td>
              </tr>
            ))}
          </tbody>
        </EiqDataTable>
        <div className="eiq-meetings-v3-total">
          <span>Total Scratchings</span>
          <strong>{totalScratchings}</strong>
        </div>
      </EiqPanel>

      <EiqPanel density="compact" className="eiq-meetings-v3-scratchings-card">
        <EiqSectionHeader title={`${selectedMeetingName} Scratchings (${selectedCount})`} />
        {selectedRecords.length ? (
          <EiqDataTable
            density="compact"
            className="eiq-meetings-v3-scratchings-table"
            wrapperProps={{ className: "eiq-meetings-v3-table-scroll" }}
          >
            <thead>
              <tr>
                <th>RACE</th>
                <th className="is-left">HORSE</th>
                <th>DATE / TIME</th>
              </tr>
            </thead>
            <tbody>
              {selectedRecords.map(({ group, record }) => (
                <tr key={record.eventKey}>
                  <td>R{group.raceNumber}</td>
                  <td className="is-left">
                    <strong>{record.horse}</strong>
                  </td>
                  <td>{formatScratchDateTime(record)}</td>
                </tr>
              ))}
            </tbody>
          </EiqDataTable>
        ) : (
          <EiqEmptyState title="No official scratchings have been received for this meeting." />
        )}
      </EiqPanel>
    </div>
  );
}

export function MeetingsWorkspace({
  selectedDayKey,
  selectedMeetingKey,
  onDayChange,
  onSelectMeeting,
  onOpenMeeting,
}: MeetingsWorkspaceProps) {
  const [viewModel, setViewModel] = useState<MeetingsWorkspaceViewModel | null>(null);
  const [status, setStatus] = useState<"LOADING" | "READY" | "ERROR">("LOADING");
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<MeetingStatusFilter>("Current");
  const [activeDetailTab, setActiveDetailTab] = useState<MeetingDetailTab>("Scratchings");

  useEffect(() => {
    let active = true;
    setStatus("LOADING");
    loadMeetingsWorkspaceViewModel()
      .then((nextViewModel) => {
        if (!active) return;
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch(() => {
        if (!active) return;
        setStatus("ERROR");
      });

    return () => {
      active = false;
    };
  }, []);

  const activeDay = useMemo(() => {
    return viewModel?.days.find((day) => day.key === selectedDayKey) ?? viewModel?.days[0] ?? null;
  }, [selectedDayKey, viewModel]);

  const selectedMeeting = useMemo(() => {
    if (!activeDay) return null;
    return activeDay.meetings.find((meeting) => meeting.meetingKey === selectedMeetingKey) ?? activeDay.meetings[0] ?? null;
  }, [activeDay, selectedMeetingKey]);

  useEffect(() => {
    if (status !== "READY" || !activeDay) return;
    if (selectedMeeting) {
      if (selectedMeeting.meetingKey !== selectedMeetingKey) {
        onSelectMeeting(selectedMeeting.rawMeeting);
      }
      return;
    }
    if (selectedMeetingKey) onSelectMeeting(null);
  }, [activeDay, onSelectMeeting, selectedMeeting, selectedMeetingKey, status]);

  const availableStatusFilters = useMemo(() => {
    if (!activeDay) return [];
    return STATUS_FILTERS.filter((filter) => activeDay.meetings.some((meeting) => meetingStatusFilter(meeting.status) === filter));
  }, [activeDay]);

  const effectiveStatusFilter = availableStatusFilters.includes(statusFilter) ? statusFilter : availableStatusFilters[0] ?? statusFilter;

  const filteredMeetings = useMemo(() => {
    if (!activeDay) return [];
    const search = searchText.trim().toLowerCase();
    return activeDay.meetings.filter((meeting) => {
      const matchesSearch = !search || displayTrack(meeting.meeting).toLowerCase().includes(search);
      const matchesStatus = meetingStatusFilter(meeting.status) === effectiveStatusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [activeDay, effectiveStatusFilter, searchText]);

  if (status === "LOADING") {
    return (
      <PageFrame className="eiq-meetings-v3 eiq-meetings-v2">
        <EiqLoadingState title="Loading the three-day race programme." />
      </PageFrame>
    );
  }

  if (status === "ERROR" || !viewModel || !activeDay) {
    return (
      <PageFrame className="eiq-meetings-v3 eiq-meetings-v2">
        <EiqEmptyState title="No meetings published for this date." />
      </PageFrame>
    );
  }

  const cycleStatusFilter = () => {
    if (!availableStatusFilters.length) return;
    const currentIndex = availableStatusFilters.indexOf(effectiveStatusFilter);
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % availableStatusFilters.length : 0;
    setStatusFilter(availableStatusFilters[nextIndex]);
  };

  return (
    <PageFrame className="eiq-meetings-v3 eiq-meetings-v2" aria-label="Meetings" data-edgeiq-workspace-key="MEETINGS" data-edgeiq-mounted-component="MeetingsWorkspace">
      <PageHeader
        eyebrow="MEETINGS"
        title="Meetings"
        description="Three-day racing outlook. Select a meeting to view races and details."
        actions={
          <EiqTabs
            density="compact"
            label="Date range"
            items={viewModel.days.map((day) => ({ value: day.key, label: <><strong>{day.label}</strong><small>{shortDate(day.date)}</small></> }))}
            activeValue={activeDay.key}
            onValueChange={onDayChange}
            className="eiq-meetings-v2-date-tabs"
          />
        }
      />

      <EiqPanel className="eiq-meetings-v3-panel eiq-meetings-v2-card" aria-label={`Meetings for ${activeDay.displayDate}`}>
        <div className="eiq-meetings-v1-actions">
          <label>
            <span>Search meetings</span>
            <input
              aria-label="Search meetings"
              placeholder="Search meetings..."
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </label>
          <EiqButton
            size="compact"
            type="button"
            aria-label={`Filters. Current filter: ${effectiveStatusFilter}`}
            title={`Current filter: ${effectiveStatusFilter}`}
            onClick={cycleStatusFilter}
          >
            Filters
          </EiqButton>
          <EiqButton
            variant="primary"
            size="compact"
            disabled={!selectedMeeting}
            onClick={() => selectedMeeting && onOpenMeeting(selectedMeeting.rawMeeting)}
          >
            Open Meeting
          </EiqButton>
        </div>

        <EiqSectionHeader title={`Meetings (${activeDay.displayDate})`} />

        {filteredMeetings.length ? (
          <EiqDataTable
            density="compact"
            className="eiq-meetings-v2-table"
            wrapperProps={{ className: "eiq-v1-standard-table-scroll eiq-meetings-v3-table-scroll" }}
          >
              <colgroup>
                <col style={{ width: "68px" }} />
                <col style={{ width: "150px" }} />
                <col style={{ width: "64px" }} />
                <col style={{ width: "130px" }} />
                <col style={{ width: "130px" }} />
                <col style={{ width: "150px" }} />
                <col style={{ width: "72px" }} />
                <col style={{ width: "104px" }} />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">SELECT</th>
                  <th scope="col" className="is-left">MEETING</th>
                  <th scope="col">STATE</th>
                  <th scope="col">RAIL</th>
                  <th scope="col">TRACK</th>
                  <th scope="col">WEATHER</th>
                  <th scope="col">RACES</th>
                  <th scope="col">SCRATCHINGS</th>
                </tr>
              </thead>
              <tbody>
                {filteredMeetings.map((meeting) => {
                  const isSelected = meeting.meetingKey === selectedMeeting?.meetingKey;
                  const trackRating = canonicalTrackRatingDisplay(meeting.track);
                  return (
                    <tr
                      key={meeting.meetingKey}
                      className={isSelected ? "is-selected" : ""}
                      aria-selected={isSelected}
                      tabIndex={0}
                      onClick={() => onSelectMeeting(meeting.rawMeeting)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelectMeeting(meeting.rawMeeting);
                        }
                      }}
                    >
                      <td>
                        <button
                          className="eiq-meetings-v3-select"
                          type="button"
                          aria-pressed={isSelected}
                          aria-label={`${isSelected ? "Selected" : "Select"} ${displayTrack(meeting.meeting)}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelectMeeting(meeting.rawMeeting);
                          }}
                        >
                          <span />
                        </button>
                      </td>
                      <td className="is-left">
                        <button
                          className="eiq-meetings-v1-meeting-name"
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            onSelectMeeting(meeting.rawMeeting);
                          }}
                        >
                          {displayTrack(meeting.meeting)}
                        </button>
                      </td>
                      <td>{display(meeting.state, "VIC")}</td>
                      <td>{canonicalRailDisplay(meeting.rail)}</td>
                      <td>{trackRating}</td>
                      <td>{canonicalWeatherDisplay(meeting.weather)}</td>
                      <td>{meeting.races}</td>
                      <td>{meeting.scratchings}</td>
                    </tr>
                  );
                })}
              </tbody>
          </EiqDataTable>
        ) : (
          <EiqEmptyState title="No meetings published for this date." />
        )}
      </EiqPanel>

      <section className="eiq-meetings-v3-detail" aria-label="Meeting detail">
        <EiqTabs
          density="compact"
          label="Meeting detail"
          items={MEETING_DETAIL_TABS.map((tab) => ({ value: tab, label: tab }))}
          activeValue={activeDetailTab}
          onValueChange={(value) => setActiveDetailTab(value as MeetingDetailTab)}
          className="eiq-meetings-v3-detail-tabs"
        />
        <div className="eiq-meetings-v3-detail-panel">
          {activeDetailTab === "Scratchings" ? (
            <ScratchingsDetail activeDay={activeDay} selectedMeeting={selectedMeeting} />
          ) : selectedMeeting && activeDetailTab === "Gear Changes" ? (
            <MeetingGearChangesWorkspace meeting={selectedMeeting.rawMeeting} />
          ) : selectedMeeting && activeDetailTab === "Track" ? (
            <MeetingTrackWorkspace meeting={selectedMeeting.rawMeeting} />
          ) : selectedMeeting && activeDetailTab === "Weather" ? (
            <MeetingWeatherWorkspace meeting={selectedMeeting.rawMeeting} />
          ) : selectedMeeting && activeDetailTab === "Results" ? (
            <MeetingResultsWorkspace meeting={selectedMeeting.rawMeeting} />
          ) : (
            <EiqEmptyState title="Select a meeting to view details." />
          )}
        </div>
      </section>
    </PageFrame>
  );
}
