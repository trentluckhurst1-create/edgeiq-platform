import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import { EDGEIQ_LIVE_FILES, EDGEIQ_REFRESH_MS } from "../../config/edgeiqLiveFeeds";

type TrackingRow = Record<string, string>;
type RunnerBoardRow = Record<string, string>;

type MeetingSelection = {
  raceDate: string;
  track: string;
  dayBucket: string;
  meetingStatus: string;
  dashboardReady: string;
} | null;

type OpportunityRow = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceTime: string;
  horse: string;
  livePrice: number | null;
  fairPrice: number | null;
  edgePct: number | null;
  winChance: number | null;
  runnerProfile: string;
  confidence: string;
  confidenceRank: number;
  priceStatus: string;
  rawAction: string;
  rawStatus: string;
  displayStatus: string;
  statusRank: number;
  runnerStatus: string;
  tracking: TrackingRow;
  board?: RunnerBoardRow;
};

type RaceSummary = {
  key: string;
  raceNo: number;
  raceTime: string;
  candidateCount: number;
  activeRunnerCount: number;
  readyCount: number;
  watchCount: number;
  developingCount: number;
  underReviewCount: number;
  strongest: OpportunityRow | null;
  interestLevel: string;
  interestRank: number;
};

type TrackingTabProps = {
  currentMeeting?: MeetingSelection;
};

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace(/[$,%]/g, "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function cleanTrack(value: unknown): string {
  return text(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function cleanHorse(value: unknown): string {
  return text(value)
    .toUpperCase()
    .replace(/\([^)]*\)/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function firstText(row: Record<string, string> | undefined, keys: string[]): string {
  if (!row) return "";
  for (const key of keys) {
    const value = text(row[key]);
    if (value) return value;
  }
  return "";
}

function firstNum(row: Record<string, string> | undefined, keys: string[]): number | null {
  if (!row) return null;
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

function trackingRaceDate(row: TrackingRow): string {
  return firstText(row, ["race_date", "meeting_date", "date"]);
}

function trackingTrack(row: TrackingRow): string {
  return firstText(row, ["track", "meeting_name", "meeting"]);
}

function trackingRaceNo(row: TrackingRow): number {
  return Math.trunc(firstNum(row, ["race_no", "race_number", "race"]) ?? 0);
}

function trackingHorse(row: TrackingRow): string {
  return firstText(row, ["horse", "runner_name", "runner"]);
}

function boardRaceDate(row: RunnerBoardRow): string {
  return firstText(row, ["race_date", "meeting_date", "date"]);
}

function boardTrack(row: RunnerBoardRow): string {
  return firstText(row, ["track", "meeting_name", "meeting"]);
}

function boardRaceNo(row: RunnerBoardRow): number {
  return Math.trunc(firstNum(row, ["race_no", "race_number", "race"]) ?? 0);
}

function boardHorse(row: RunnerBoardRow): string {
  return firstText(row, ["horse", "runner_name", "runner"]);
}

function boardRaceTime(row: RunnerBoardRow): string {
  return firstText(row, ["race_time", "scheduled_jump", "jump_time"]);
}

function trackingKey(row: TrackingRow): string {
  return [
    trackingRaceDate(row),
    cleanTrack(trackingTrack(row)),
    String(trackingRaceNo(row)),
    cleanHorse(firstText(row, ["horse_key", "horse", "runner_name", "runner"])),
  ].join("|");
}

function boardKey(row: RunnerBoardRow): string {
  return [
    boardRaceDate(row),
    cleanTrack(boardTrack(row)),
    String(boardRaceNo(row)),
    cleanHorse(firstText(row, ["horse_key", "horse", "runner_name", "runner"])),
  ].join("|");
}

function raceGroupKey(dateValue: string, trackValue: string, raceNoValue: number): string {
  return [dateValue, cleanTrack(trackValue), String(raceNoValue)].join("|");
}

function money(value: number | null): string {
  if (value === null || !Number.isFinite(value) || value <= 0) return "-";
  return `$${value.toFixed(2)}`;
}

function pct(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  return `${value.toFixed(1)}%`;
}

function formatTime(value: string): string {
  const raw = text(value);
  if (!raw) return "TBC";

  const parsed = new Date(raw);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleTimeString("en-AU", {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  return raw;
}

function pillColors(label: string): { background: string; border: string; color: string } {
  const value = label.toUpperCase();

  if (value === "READY" || value === "HIGH" || value === "VERY HIGH") {
    return {
      background: "rgba(16,185,129,0.18)",
      border: "rgba(16,185,129,0.4)",
      color: "#bbf7d0",
    };
  }

  if (value === "WATCH" || value === "MEDIUM" || value === "DEVELOPING") {
    return {
      background: "rgba(245,158,11,0.18)",
      border: "rgba(245,158,11,0.4)",
      color: "#fde68a",
    };
  }

  if (value === "UNDER REVIEW" || value === "LOW") {
    return {
      background: "rgba(248,113,113,0.18)",
      border: "rgba(248,113,113,0.4)",
      color: "#fecaca",
    };
  }

  if (value === "CLOSED") {
    return {
      background: "rgba(100,116,139,0.18)",
      border: "rgba(100,116,139,0.42)",
      color: "#cbd5e1",
    };
  }

  return {
    background: "rgba(59,130,246,0.16)",
    border: "rgba(96,165,250,0.4)",
    color: "#dbeafe",
  };
}

function pill(label: string, minWidth = 76): React.ReactElement {
  const colors = pillColors(label);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth,
        border: `1px solid ${colors.border}`,
        borderRadius: 999,
        padding: "4px 9px",
        fontSize: 10,
        fontWeight: 900,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: colors.color,
        background: colors.background,
      }}
    >
      {label || "-"}
    </span>
  );
}

function confidenceLabel(runnerProfile: string, priceStatus: string): string {
  const status = priceStatus.toUpperCase();
  if (status.includes("NO_PROJECTION") || status.includes("FALLBACK")) return "LOW";

  const band = runnerProfile.toUpperCase();
  if (band === "ELITE" || band === "STRONG" || band === "POSITIVE") return "HIGH";
  if (band === "NEUTRAL") return "MEDIUM";
  if (band === "NEGATIVE" || band === "POOR") return "LOW";
  return "MEDIUM";
}

function confidenceRank(label: string): number {
  const value = label.toUpperCase();
  if (value === "HIGH") return 3;
  if (value === "MEDIUM") return 2;
  if (value === "LOW") return 1;
  return 0;
}

function statusRank(label: string): number {
  const value = label.toUpperCase();
  if (value === "READY") return 4;
  if (value === "WATCH") return 3;
  if (value === "DEVELOPING") return 2;
  if (value === "UNDER REVIEW") return 1;
  return 0;
}

function edgeTextColor(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "#cbd5e1";
  if (value < 0) return "#fca5a5";
  if (value >= 100) return "#e2e8f0";
  return "#fde68a";
}

function isClosedTrackingRow(row: TrackingRow, board?: RunnerBoardRow): boolean {
  const finishPosition = firstNum(row, ["result_finish_pos"]);
  const wonFlag = firstText(row, ["won"]).toUpperCase();
  const placedFlag = firstText(row, ["placed"]).toUpperCase();

  if (
    finishPosition !== null ||
    ["YES", "Y", "TRUE", "1"].includes(wonFlag) ||
    ["YES", "Y", "TRUE", "1"].includes(placedFlag)
  ) {
    return true;
  }

  const boardState = [
    firstText(board, ["runner_status"]),
    firstText(board, ["display_decision"]),
    firstText(board, ["scratch_status"]),
    firstText(board, ["tab_fixed_betting_status"]),
  ]
    .join(" ")
    .toUpperCase();

  return boardState.includes("SCRATCH");
}

function openStatus(
  rawAction: string,
  confidence: string,
  livePrice: number | null,
  fairPrice: number | null,
  edgePct: number | null,
): string {
  if (livePrice === null || fairPrice === null || edgePct === null) return "UNDER REVIEW";

  const action = rawAction.toUpperCase();
  if (action === "WATCH" && confidence === "HIGH") return "READY";
  if (action === "WATCH") return "WATCH";
  if (action === "LEAN" && confidence === "HIGH" && edgePct >= 50) return "WATCH";
  if (action === "LEAN") return "DEVELOPING";
  return "UNDER REVIEW";
}

function fairWinChance(fairPrice: number | null): number | null {
  return fairPrice !== null && fairPrice > 0 ? 100 / fairPrice : null;
}

function opportunityScore(row: OpportunityRow): number {
  const chance = Math.min(row.winChance ?? 0, 30);
  const edge = Math.min(Math.max(row.edgePct ?? 0, 0), 120);
  return (row.statusRank * 100) + (row.confidenceRank * 30) + chance + (edge * 0.1);
}

function interestLabel(summary: Omit<RaceSummary, "interestLevel" | "interestRank">): string {
  if (summary.candidateCount === 0) return "LOW";
  if (summary.readyCount >= 2 || (summary.readyCount >= 1 && summary.candidateCount >= 3)) return "VERY HIGH";
  if (summary.readyCount >= 1 || summary.watchCount >= 2 || summary.candidateCount >= 3) return "HIGH";
  if (summary.candidateCount >= 1) return "WATCH";
  return "LOW";
}

function interestRank(label: string): number {
  const value = label.toUpperCase();
  if (value === "VERY HIGH") return 4;
  if (value === "HIGH") return 3;
  if (value === "WATCH") return 2;
  return 1;
}

async function loadCsv<T extends Record<string, string>>(path: string): Promise<T[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const textValue = await response.text();
    const parsed = Papa.parse<T>(textValue, { header: true, skipEmptyLines: true });
    return parsed.data || [];
  } catch {
    return [];
  }
}

export default function TrackingTab({ currentMeeting = null }: TrackingTabProps): React.ReactElement {
  const [trackingRows, setTrackingRows] = useState<TrackingRow[]>([]);
  const [runnerBoardRows, setRunnerBoardRows] = useState<RunnerBoardRow[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [trackingData, runnerBoardData] = await Promise.all([
        loadCsv<TrackingRow>(EDGEIQ_LIVE_FILES.modelTracking),
        loadCsv<RunnerBoardRow>(EDGEIQ_LIVE_FILES.liveRunnerBoard),
      ]);

      if (cancelled) return;
      setTrackingRows(trackingData);
      setRunnerBoardRows(runnerBoardData);
    }

    load();
    const id = window.setInterval(load, EDGEIQ_REFRESH_MS);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const selectedMeetingTrack = text(currentMeeting?.track);
  const selectedMeetingDate = text(currentMeeting?.raceDate);
  const futureMeeting = text(currentMeeting?.dashboardReady).toUpperCase() === "NO";

  const opportunityRows = useMemo(() => {
    const boardMap = new Map<string, RunnerBoardRow>();
    runnerBoardRows.forEach((row) => {
      boardMap.set(boardKey(row), row);
    });

    return trackingRows
      .map((trackingRow): OpportunityRow | null => {
        const key = trackingKey(trackingRow);
        const boardRow = boardMap.get(key);
        const livePrice =
          firstNum(trackingRow, ["live_price"]) ??
          firstNum(boardRow, ["display_live_price", "live_price", "tab_fixed_win"]);
        const fairPrice =
          firstNum(trackingRow, ["fair_price"]) ??
          firstNum(boardRow, ["display_fair_price", "ui_fair_price", "fair_price"]);
        const edgePct =
          firstNum(trackingRow, ["edge_pct"]) ??
          firstNum(boardRow, ["display_edge_pct", "ui_edge_pct", "edge_pct"]);
        const runnerProfile =
          firstText(boardRow, ["projection_band_V6_1_RESEARCH"]) ||
          firstText(trackingRow, ["projection_band"]) ||
          "NEUTRAL";
        const priceStatus = firstText(boardRow, ["V6_1_RESEARCH_price_status"]) || "RESEARCH_RATED";
        const confidence = confidenceLabel(runnerProfile, priceStatus);
        const action = firstText(trackingRow, ["action"]) || "WATCH";
        const displayStatus = isClosedTrackingRow(trackingRow, boardRow)
          ? "CLOSED"
          : openStatus(action, confidence, livePrice, fairPrice, edgePct);

        const raceDate = trackingRaceDate(trackingRow) || boardRaceDate(boardRow ?? {});
        const track = trackingTrack(trackingRow) || boardTrack(boardRow ?? {});
        const raceNo = trackingRaceNo(trackingRow) || boardRaceNo(boardRow ?? {});
        const horse = trackingHorse(trackingRow) || boardHorse(boardRow ?? {});

        if (!track || !raceNo || !horse) return null;

        return {
          key,
          raceDate,
          track,
          raceNo,
          raceTime: boardRaceTime(boardRow ?? {}),
          horse,
          livePrice,
          fairPrice,
          edgePct,
          winChance: fairWinChance(fairPrice),
          runnerProfile,
          confidence,
          confidenceRank: confidenceRank(confidence),
          priceStatus,
          rawAction: action.toUpperCase(),
          rawStatus: firstText(trackingRow, ["status"]).toUpperCase(),
          displayStatus,
          statusRank: statusRank(displayStatus),
          runnerStatus: firstText(boardRow, ["runner_status"]) || "ACTIVE",
          tracking: trackingRow,
          board: boardRow,
        };
      })
      .filter((row): row is OpportunityRow => row !== null)
      .filter((row) => {
        if (!selectedMeetingTrack || !selectedMeetingDate) return true;
        return cleanTrack(row.track) === cleanTrack(selectedMeetingTrack) && row.raceDate === selectedMeetingDate;
      });
  }, [runnerBoardRows, trackingRows, selectedMeetingDate, selectedMeetingTrack]);

  const openRows = useMemo(
    () => opportunityRows.filter((row) => row.displayStatus !== "CLOSED"),
    [opportunityRows],
  );

  const raceSummaries = useMemo(() => {
    const raceMap = new Map<
      string,
      {
        raceNo: number;
        raceTime: string;
        activeRunnerCount: number;
        candidates: OpportunityRow[];
      }
    >();

    runnerBoardRows
      .filter((row) => {
        if (!selectedMeetingTrack || !selectedMeetingDate) return true;
        return cleanTrack(boardTrack(row)) === cleanTrack(selectedMeetingTrack) && boardRaceDate(row) === selectedMeetingDate;
      })
      .forEach((row) => {
      const key = raceGroupKey(boardRaceDate(row), boardTrack(row), boardRaceNo(row));
      if (!raceMap.has(key)) {
        raceMap.set(key, {
          raceNo: boardRaceNo(row),
          raceTime: boardRaceTime(row),
          activeRunnerCount: 0,
          candidates: [],
        });
      }

      const stateBlob = [
        firstText(row, ["runner_status"]),
        firstText(row, ["display_decision"]),
        firstText(row, ["scratch_status"]),
        firstText(row, ["tab_fixed_betting_status"]),
      ]
        .join(" ")
        .toUpperCase();

      if (!stateBlob.includes("SCRATCH")) {
        raceMap.get(key)!.activeRunnerCount += 1;
      }
    });

    opportunityRows.forEach((row) => {
      const key = raceGroupKey(row.raceDate, row.track, row.raceNo);
      if (!raceMap.has(key)) {
        raceMap.set(key, {
          raceNo: row.raceNo,
          raceTime: row.raceTime,
          activeRunnerCount: 0,
          candidates: [],
        });
      }
      raceMap.get(key)!.candidates.push(row);
    });

    return [...raceMap.entries()]
      .map(([key, value]) => {
        const openCandidates = value.candidates.filter((candidate) => candidate.displayStatus !== "CLOSED");
        const readyCount = openCandidates.filter((candidate) => candidate.displayStatus === "READY").length;
        const watchCount = openCandidates.filter((candidate) => candidate.displayStatus === "WATCH").length;
        const developingCount = openCandidates.filter((candidate) => candidate.displayStatus === "DEVELOPING").length;
        const underReviewCount = openCandidates.filter((candidate) => candidate.displayStatus === "UNDER REVIEW").length;
        const strongest =
          openCandidates
            .slice()
            .sort((a, b) => opportunityScore(b) - opportunityScore(a))[0] ?? null;
        const baseSummary = {
          key,
          raceNo: value.raceNo,
          raceTime: value.raceTime,
          candidateCount: openCandidates.length,
          activeRunnerCount: value.activeRunnerCount,
          readyCount,
          watchCount,
          developingCount,
          underReviewCount,
          strongest,
        };
        const label = interestLabel(baseSummary);

        return {
          ...baseSummary,
          interestLevel: label,
          interestRank: interestRank(label),
        };
      })
      .sort((a, b) => a.raceNo - b.raceNo);
  }, [opportunityRows, runnerBoardRows, selectedMeetingDate, selectedMeetingTrack]);

  const raceInterestBoard = useMemo(
    () =>
      raceSummaries
        .slice()
        .sort((a, b) => {
          if (b.interestRank !== a.interestRank) return b.interestRank - a.interestRank;
          if (b.readyCount !== a.readyCount) return b.readyCount - a.readyCount;
          if (b.watchCount !== a.watchCount) return b.watchCount - a.watchCount;
          if (b.candidateCount !== a.candidateCount) return b.candidateCount - a.candidateCount;
          return a.raceNo - b.raceNo;
        }),
    [raceSummaries],
  );

  const watchlistRows = useMemo(
    () =>
      openRows
        .slice()
        .sort((a, b) => opportunityScore(b) - opportunityScore(a))
        .slice(0, 6),
    [openRows],
  );

  const boardRows = useMemo(
    () =>
      openRows
        .slice()
        .sort((a, b) => {
          if (a.raceNo !== b.raceNo) return a.raceNo - b.raceNo;
          const scoreDiff = opportunityScore(b) - opportunityScore(a);
          if (scoreDiff !== 0) return scoreDiff;
          return a.horse.localeCompare(b.horse);
        }),
    [openRows],
  );

  const developingCount = openRows.filter((row) => row.displayStatus === "DEVELOPING").length;
  const readyCount = openRows.filter((row) => row.displayStatus === "READY").length;
  const underReviewCount = openRows.filter((row) => row.displayStatus === "UNDER REVIEW").length;
  const watchCount = openRows.filter((row) => row.displayStatus === "WATCH").length;

  const strongestOpportunity =
    openRows
      .slice()
      .sort((a, b) => opportunityScore(b) - opportunityScore(a))[0] ?? null;

  const meetingTrack = selectedMeetingTrack || firstText(runnerBoardRows[0], ["track"]) || firstText(trackingRows[0], ["track"]) || "Selected Meeting";
  const meetingDate = selectedMeetingDate || firstText(runnerBoardRows[0], ["race_date"]) || firstText(trackingRows[0], ["race_date"]);

  const topRaceCount = Math.max(...raceSummaries.map((race) => race.candidateCount), 0);
  const topRaces = raceInterestBoard
    .filter((race) => race.candidateCount === topRaceCount && topRaceCount > 0)
    .slice(0, 2)
    .map((race) => `R${race.raceNo}`);

  const radarNarrative =
    openRows.length === 0
      ? "EDGEiQ is not actively monitoring any live opportunities on this card right now."
      : [
        `EDGEiQ is currently tracking ${openRows.length} opportunities across ${raceSummaries.filter((race) => race.candidateCount > 0).length} races.`,
        topRaces.length ? `Most activity is concentrated around ${topRaces.join(" and ")}.` : "",
        readyCount > 0 ? `${readyCount} runners are sitting in ready status.` : "No runners are at ready status yet.",
        developingCount > 0 ? `${developingCount} remain in development.` : "",
        underReviewCount > 0
          ? `${underReviewCount} are under review while the live picture settles.`
          : "No major deterioration is currently flagged.",
      ]
        .filter(Boolean)
        .join(" ");

  const trackingOverviewCards = [
    {
      label: "Active Opportunities",
      value: String(openRows.length),
      sub: `${raceSummaries.filter((race) => race.candidateCount > 0).length} races currently in focus`,
      tone: "info",
    },
    {
      label: "Developing",
      value: String(developingCount),
      sub: "still building toward a stronger opportunity signal",
      tone: "warn",
    },
    {
      label: "Ready",
      value: String(readyCount),
      sub: "opportunities with stronger live alignment right now",
      tone: "good",
    },
    {
      label: "Under Review",
      value: String(underReviewCount),
      sub: "opportunities still waiting for a cleaner read",
      tone: underReviewCount > 0 ? "bad" : "neutral",
    },
    {
      label: "Strongest Opportunity",
      value: strongestOpportunity ? strongestOpportunity.horse : "-",
      sub: strongestOpportunity
        ? `R${strongestOpportunity.raceNo} | ${strongestOpportunity.confidence} confidence | ${strongestOpportunity.displayStatus}`
        : "no live opportunity currently stands above the card",
      tone: strongestOpportunity ? "good" : "neutral",
    },
  ] as const;

  if (futureMeeting && currentMeeting) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">
            <span>EDGEiQ OPPORTUNITY CENTRE</span>
            {pill("MONITORING", 104)}
          </div>

          <div style={{ padding: 12, display: "grid", gap: 12 }}>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Selected Meeting</div>
              <div className="edgeiq-mini-note-value">{currentMeeting.track}</div>
              <div className="edgeiq-mini-note-sub">
                {currentMeeting.raceDate} | {text(currentMeeting.dayBucket).replace("DAY+2", "DAY +2")} | {text(currentMeeting.meetingStatus).replace(/_/g, " ")}
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Tracking State</div>
              <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                EDGEiQ is monitoring this meeting. Opportunities will appear here automatically once fields are released and the live runner board is available.
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Active Opportunities</div>
                <div className="edgeiq-terminal-stat-value">0</div>
                <div className="edgeiq-terminal-stat-sub">tracking is waiting for runner fields</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Status</div>
                <div className="edgeiq-terminal-stat-value" style={{ color: "#fde68a" }}>Monitoring</div>
                <div className="edgeiq-terminal-stat-sub">future meeting on watch until data arrives</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="edgeTabSurface">
      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">
          <span>EDGEiQ OPPORTUNITY CENTRE</span>
          <span className="edgeiq-pill good">{meetingDate || "Live card"}</span>
        </div>

        <div style={{ padding: 12, display: "grid", gap: 12 }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div className="edgeiq-mini-note-label">Current Meeting</div>
              <div className="edgeiq-mini-note-value">{meetingTrack}</div>
              <div className="edgeiq-mini-note-sub">
                What EDGEiQ is monitoring right now across the live meeting.
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              {pill(`WATCH ${watchCount}`, 72)}
              {pill(`READY ${readyCount}`, 72)}
              <span style={{ color: "#64748b", fontSize: 11 }}>
                Refreshes every {Math.round(EDGEIQ_REFRESH_MS / 1000)}s
              </span>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 10,
            }}
          >
            {trackingOverviewCards.map((card) => {
              const toneColor =
                card.tone === "good"
                  ? "#bbf7d0"
                  : card.tone === "warn"
                    ? "#fde68a"
                    : card.tone === "bad"
                      ? "#fecaca"
                      : "#e2e8f0";

              return (
                <div
                  key={card.label}
                  className="edgeiq-terminal-stat"
                  style={{ minHeight: 100 }}
                >
                  <div className="edgeiq-terminal-stat-label">{card.label}</div>
                  <div
                    className="edgeiq-terminal-stat-value"
                    style={{
                      color: toneColor,
                      fontSize: card.value.length > 16 ? 18 : 24,
                      lineHeight: 1.15,
                    }}
                  >
                    {card.value}
                  </div>
                  <div className="edgeiq-terminal-stat-sub">{card.sub}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">EDGEiQ OPPORTUNITY RADAR</div>
        <div style={{ padding: 12 }}>
          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">Live Read</div>
            <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
              {radarNarrative}
            </div>
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">OPPORTUNITY WATCHLIST</div>
        <div style={{ padding: 12, display: "grid", gap: 10 }}>
          <div className="edgeiq-data-note">
            Highest-priority live opportunities across the current card.
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 10,
            }}
          >
            {watchlistRows.map((row) => (
              <div
                key={row.key}
                style={{
                  border: "1px solid rgba(41,72,90,0.82)",
                  borderRadius: 12,
                  background: "rgba(5,14,22,0.82)",
                  padding: "10px 12px",
                  display: "grid",
                  gap: 9,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ color: "#f8fafc", fontSize: 15, fontWeight: 900, lineHeight: 1.25 }}>
                      {row.horse}
                    </div>
                    <div style={{ color: "#94a3b8", fontSize: 11 }}>
                      R{row.raceNo} | {row.track}
                    </div>
                  </div>
                  {pill(row.displayStatus, 82)}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: 8,
                  }}
                >
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">TAB Price</div>
                    <div className="edgeiq-mini-note-value">{money(row.livePrice)}</div>
                  </div>
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Fair Price</div>
                    <div className="edgeiq-mini-note-value">{money(row.fairPrice)}</div>
                  </div>
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Value Edge</div>
                    <div
                      className="edgeiq-mini-note-value"
                      style={{ color: edgeTextColor(row.edgePct), fontSize: 16 }}
                    >
                      {pct(row.edgePct)}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ color: "#94a3b8", fontSize: 11 }}>
                    EDGEiQ Confidence: <strong style={{ color: "#e2e8f0" }}>{row.confidence}</strong>
                  </span>
                  <span style={{ color: "#94a3b8", fontSize: 11 }}>
                    Runner Profile: <strong style={{ color: "#e2e8f0" }}>{row.runnerProfile}</strong>
                  </span>
                </div>
              </div>
            ))}

            {watchlistRows.length === 0 && (
              <div className="edgeiq-no-live">No live opportunities are currently on the watchlist.</div>
            )}
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">RACE INTEREST BOARD</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          <div className="edgeiq-data-note">
            Highest-interest races appear first.
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 10,
            }}
          >
            {raceInterestBoard.map((race) => (
              <div
                key={race.key}
                style={{
                  border: "1px solid rgba(41,72,90,0.82)",
                  borderRadius: 12,
                  background: "rgba(5,14,22,0.82)",
                  padding: "10px 12px",
                  display: "grid",
                  gap: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                  <div>
                    <div style={{ color: "#6f8493", fontSize: 9, fontWeight: 900, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                      Race
                    </div>
                    <div style={{ color: "#f8fafc", fontSize: 18, fontWeight: 900 }}>
                      R{race.raceNo}
                    </div>
                    <div style={{ color: "#94a3b8", fontSize: 11 }}>
                      {formatTime(race.raceTime)}
                    </div>
                  </div>
                  {pill(race.interestLevel, 84)}
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 8,
                  }}
                >
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Candidate Count</div>
                    <div className="edgeiq-mini-note-value">{race.candidateCount}</div>
                    <div className="edgeiq-mini-note-sub">
                      {race.activeRunnerCount > 0 ? `${race.activeRunnerCount} active runners in race` : "live field still forming"}
                    </div>
                  </div>

                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Strongest Runner</div>
                    <div className="edgeiq-mini-note-value" style={{ fontSize: 15 }}>
                      {race.strongest?.horse || "-"}
                    </div>
                    <div className="edgeiq-mini-note-sub">
                      {race.strongest ? `${race.strongest.confidence} confidence | ${race.strongest.displayStatus}` : "no live opportunity flagged"}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {race.readyCount > 0 ? pill(`${race.readyCount} READY`, 76) : null}
                  {race.watchCount > 0 ? pill(`${race.watchCount} WATCH`, 76) : null}
                  {race.developingCount > 0 ? pill(`${race.developingCount} DEVELOPING`, 98) : null}
                  {race.underReviewCount > 0 ? pill(`${race.underReviewCount} UNDER REVIEW`, 114) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">TRACKING BOARD</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          <div className="edgeiq-data-note">
            Fast scan of every live opportunity on the card.
          </div>

          <div
            style={{
              overflowX: "auto",
              border: "1px solid rgba(41,72,90,0.7)",
              borderRadius: 12,
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 820,
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ background: "rgba(15,23,42,0.96)" }}>
                  {["RACE", "RUNNER", "TAB", "FAIR", "VALUE EDGE", "EDGEIQ CONFIDENCE", "STATUS"].map((header) => (
                    <th
                      key={header}
                      style={{
                        textAlign: "left",
                        padding: "10px 12px",
                        color: "#93c5fd",
                        fontSize: 10,
                        fontWeight: 900,
                        letterSpacing: "0.12em",
                        borderBottom: "1px solid rgba(148,163,184,0.16)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {boardRows.map((row, index) => (
                  <tr
                    key={row.key}
                    style={{
                      background: index % 2 === 0 ? "rgba(2,6,23,0.55)" : "rgba(15,23,42,0.38)",
                    }}
                  >
                    <td style={tdStrong}>R{row.raceNo}</td>
                    <td style={tdHorse}>
                      <div>{row.horse}</div>
                      <div style={{ color: "#94a3b8", fontSize: 11, fontWeight: 500, marginTop: 2 }}>
                        {row.track}
                      </div>
                    </td>
                    <td style={tdNum}>{money(row.livePrice)}</td>
                    <td style={tdNum}>{money(row.fairPrice)}</td>
                    <td style={{ ...tdNum, color: edgeTextColor(row.edgePct) }}>{pct(row.edgePct)}</td>
                    <td style={td}>{pill(row.confidence, 88)}</td>
                    <td style={td}>{pill(row.displayStatus, 98)}</td>
                  </tr>
                ))}

                {boardRows.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      style={{
                        ...td,
                        textAlign: "center",
                        padding: 24,
                        color: "#64748b",
                      }}
                    >
                      No live opportunities are currently available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

const td: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid rgba(148,163,184,0.08)",
  color: "#dbeafe",
  whiteSpace: "nowrap",
};

const tdStrong: React.CSSProperties = {
  ...td,
  color: "#f8fafc",
  fontWeight: 900,
};

const tdHorse: React.CSSProperties = {
  ...td,
  color: "#ffffff",
  fontWeight: 900,
  whiteSpace: "normal",
  minWidth: 180,
};

const tdNum: React.CSSProperties = {
  ...td,
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
  fontWeight: 800,
};
