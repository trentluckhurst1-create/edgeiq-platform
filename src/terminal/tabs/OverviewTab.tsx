import React from "react";

type OverviewRunner = {
  id: string;
  raceKey: string;
  raceDate: string;
  track: string;
  raceNo: number;
  horse: string;
  horseKey: string;
  jockey: string;
  trainer: string;
  raceClass: string;
  distance: number | null;
  raceTime: string;
  todayTrackCondition: string;
  railPosition?: string;
  ratedPrice: number | null;
  marketPrice: number | null;
  isScratched: boolean;
  modelConfidenceScore?: number | null;
  priceConfidenceBand?: string;
  projected_tempo_shape?: string;
  tempo_role?: string;
};

type OverviewRaceGroup = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceTime: string;
  raceClass: string;
  distance: number | null;
  todayTrackCondition: string;
  rows: OverviewRunner[];
};

type OverviewMeeting = {
  meetingKey: string;
  raceDate: string;
  track: string;
  dayBucket: string;
  meetingType: string;
  meetingStatus: string;
  dashboardReady: string;
  fieldRows: number;
  fieldRaces: number;
  pricedRows: number;
  races?: OverviewRaceGroup[];
};

type UpcomingMeeting = OverviewMeeting & {
  raceCount: number;
};

type TrackBiasRow = Record<string, string>;

type OverviewTabProps = {
  staleSnapshot: boolean;
  currentMeeting: OverviewMeeting | null;
  currentRace: OverviewRaceGroup | null;
  currentMeetingRaces: OverviewRaceGroup[];
  upcomingMeetings: UpcomingMeeting[];
  marketStateLabel: string;
  settlementAuditSummary: string;
  scratchFeedSummary: string;
  selectorFeedSummary: string;
  trackBiasRows: TrackBiasRow[];
  displayDate: (dateValue: string) => string;
  setSelectedMeetingKey: (value: string) => void;
  setSelectedRaceKey: (value: string) => void;
  setSelectedHorseKey: (value: string) => void;
  setTab: (value: "OVERVIEW" | "INTELLIGENCE" | "MARKET" | "TRACKING" | "RESULTS") => void;
};

type RaceProgramSummary = {
  race: OverviewRaceGroup;
  activeCount: number;
  scratchedCount: number;
  liveCount: number;
  projectedCount: number;
  clarity: string;
  tempo: string;
  confidence: string;
  trackRead: string;
  scratchImpact: string;
};

type ParticipantCount = {
  name: string;
  count: number;
};

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function numberValue(value: unknown): number | null {
  const raw = text(value).replace("%", "").replace("$", "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function compactTrack(value: unknown): string {
  return text(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function uniqueValues(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

function formatTime(value: string): string {
  const raw = text(value);
  if (!raw) return "TBC";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleTimeString("en-AU", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDistanceRange(distances: Array<number | null>): string {
  const valid = distances.filter((value): value is number => value !== null && value > 0);
  if (!valid.length) return "-";
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  return min === max ? `${min}m` : `${min}m - ${max}m`;
}

function mostCommon(values: string[]): string {
  const counts = new Map<string, number>();
  values.forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

function activeRows(race: OverviewRaceGroup): OverviewRunner[] {
  return race.rows.filter((row) => !row.isScratched);
}

function scratchedRows(race: OverviewRaceGroup): OverviewRunner[] {
  return race.rows.filter((row) => row.isScratched);
}

function pricedActiveCount(race: OverviewRaceGroup): number {
  return activeRows(race).filter((row) => row.marketPrice !== null && row.marketPrice > 0).length;
}

function projectedActiveCount(race: OverviewRaceGroup): number {
  return activeRows(race).filter((row) => row.ratedPrice !== null && row.ratedPrice > 0).length;
}

function fairWinChance(row: OverviewRunner | null): number | null {
  const price = row?.ratedPrice ?? null;
  return price !== null && price > 0 ? 100 / price : null;
}

function confidenceLabel(row: OverviewRunner | null): string {
  if (!row) return "LOW";

  const explicitBand = text(row.priceConfidenceBand).toUpperCase();
  if (explicitBand.includes("HIGH")) return "HIGH";
  if (explicitBand.includes("MED")) return "MEDIUM";
  if (explicitBand.includes("LOW")) return "LOW";

  const score = row.modelConfidenceScore ?? null;
  if (score !== null && Number.isFinite(score)) {
    if (score >= 70) return "HIGH";
    if (score >= 45) return "MEDIUM";
    return "LOW";
  }

  const chance = fairWinChance(row) ?? 0;
  if (chance >= 18) return "HIGH";
  if (chance >= 12) return "MEDIUM";
  return "LOW";
}

function raceClarityLabel(race: OverviewRaceGroup): string {
  const chances = activeRows(race)
    .map((row) => fairWinChance(row))
    .filter((value): value is number => value !== null)
    .sort((a, b) => b - a);

  const top = chances[0] ?? 0;
  const second = chances[1] ?? 0;
  const gap = top - second;

  if (top >= 24 || gap >= 5) return "CLEAR";
  if (top >= 18 || gap >= 2.5) return "BALANCED";
  return "OPEN";
}

function expectedTempoLabel(race: OverviewRaceGroup): string {
  const actives = activeRows(race);
  const explicitShape = mostCommon(
    actives
      .map((row) => text(row.projected_tempo_shape).toUpperCase())
      .filter(Boolean),
  );

  if (explicitShape) return explicitShape.replace(/_/g, " ");

  const leaderCount = actives.filter((row) => text(row.tempo_role).toUpperCase().includes("LEADER")).length;
  const onPaceCount = actives.filter((row) => text(row.tempo_role).toUpperCase().includes("PACE")).length;
  const frontCount = leaderCount + onPaceCount;

  if (leaderCount >= 3 || frontCount >= 6) return "FAST";
  if (leaderCount <= 1 && onPaceCount <= 2) return "CONTROLLED";
  return "BALANCED";
}

function distanceBandOf(distance: number | null): string {
  if (distance === null) return "UNKNOWN";
  if (distance < 1200) return "SPRINT_1000_1100";
  if (distance < 1400) return "SPRINT_1200_1300";
  if (distance < 1700) return "MILE_1400_1600";
  if (distance < 2000) return "MIDDLE_1700_2000";
  return "STAYING_2000_PLUS";
}

function conditionBandOf(trackCondition: string, surface: string): string {
  if (surface === "SYNTHETIC") return "UNKNOWN";
  const value = text(trackCondition).toUpperCase();
  if (value.includes("GOOD") || value.includes("FAST")) return "GOOD";
  if (value.includes("SOFT")) return "SOFT";
  if (value.includes("HEAVY")) return "HEAVY";
  return "UNKNOWN";
}

function surfaceLabel(meetingTrack: string, trackCondition: string): string {
  const combined = `${text(meetingTrack)} ${text(trackCondition)}`.toUpperCase();
  return combined.includes("SYNTHETIC") ? "SYNTHETIC" : "TURF";
}

function trackBiasAliases(track: string, surface: string): string[] {
  const compact = compactTrack(track);
  const aliases = new Set<string>([compact, compact.replace(/SYNTHETIC/g, ""), compact.slice(0, 4)]);

  if (compact.includes("PAKENHAM")) {
    aliases.add(surface === "SYNTHETIC" ? "PAKS" : "PAKM");
    aliases.add("PAK");
  }

  if (compact.includes("WARRNAMBOOL")) aliases.add("WBL");
  if (compact.includes("WANGARATTA")) aliases.add("WANG");
  if (compact.includes("BALLARAT")) aliases.add("BALT");
  if (compact.includes("BENDIGO")) aliases.add("BDGO");

  return [...aliases].filter(Boolean);
}

function matchingTrackBiasRows(trackBiasRows: TrackBiasRow[], track: string, surface: string): TrackBiasRow[] {
  const aliases = new Set(trackBiasAliases(track, surface));
  return trackBiasRows.filter((row) => aliases.has(compactTrack(row.track)));
}

function weightedAverage(rows: TrackBiasRow[], column: string): number | null {
  let numerator = 0;
  let denominator = 0;

  rows.forEach((row) => {
    const value = numberValue(row[column]);
    const weight = numberValue(row.sample_size) ?? 1;
    if (value === null) return;
    numerator += value * weight;
    denominator += weight;
  });

  return denominator > 0 ? numerator / denominator : null;
}

function roleLabel(value: string): string {
  const upper = value.toUpperCase();
  if (upper === "LEADERS") return "Leaders";
  if (upper === "ON-PACE") return "On-pace";
  if (upper === "MIDFIELD") return "Midfield";
  if (upper === "BACKMARKERS") return "Backmarkers";
  return value;
}

function bestProfileType(rows: TrackBiasRow[]): string {
  const profileRates = [
    { label: "LEADERS", value: weightedAverage(rows, "leader_win_rate") ?? -1 },
    { label: "ON-PACE", value: weightedAverage(rows, "onpace_win_rate") ?? -1 },
    { label: "MIDFIELD", value: weightedAverage(rows, "midfield_win_rate") ?? -1 },
    { label: "BACKMARKERS", value: weightedAverage(rows, "backmarker_win_rate") ?? -1 },
  ].sort((a, b) => b.value - a.value);

  return profileRates[0]?.value >= 0 ? profileRates[0].label : "UNAVAILABLE";
}

function dominantBiasLabel(rows: TrackBiasRow[]): string {
  return mostCommon(rows.map((row) => text(row.bias_label).toUpperCase()).filter(Boolean)) || "NEUTRAL";
}

function trackFavorLabel(rows: TrackBiasRow[]): string {
  const best = bestProfileType(rows);
  if (best === "UNAVAILABLE") return "Profile unavailable";
  return `${roleLabel(best)} runners`;
}

function runStyleBiasLabel(rows: TrackBiasRow[]): string {
  const best = bestProfileType(rows);
  const bias = dominantBiasLabel(rows);
  if (best === "UNAVAILABLE") return "Profile unavailable";
  if (bias === "NEUTRAL") return `${roleLabel(best)} slightly favoured`;
  return `${roleLabel(best)} best suited`;
}

function barrierBiasLabel(_rows: TrackBiasRow[]): string {
  return "Barrier profile pending";
}

function trackInsight(rows: TrackBiasRow[], trackCondition: string, surface: string): string {
  if (!rows.length) {
    return "Track profile is not available for this meeting yet.";
  }

  const bestProfile = roleLabel(bestProfileType(rows));
  const biasLabel = dominantBiasLabel(rows).toLowerCase();
  const sampleSize = rows.reduce((sum, row) => sum + (numberValue(row.sample_size) ?? 0), 0);
  const conditionBand = conditionBandOf(trackCondition, surface).toLowerCase();
  const sampleNote = sampleSize < 5 ? " Sample depth is light, so treat this as directional only." : "";

  return `Historical track behaviour reads ${biasLabel} for this ${surface.toLowerCase()} setup, with ${bestProfile.toLowerCase()} shaping as the best fit. Condition context currently points to ${conditionBand}.${sampleNote}`;
}

function topParticipants(rows: OverviewRunner[], key: "jockey" | "trainer"): ParticipantCount[] {
  const counts = new Map<string, number>();

  rows.forEach((row) => {
    const cleaned = text(row[key])
      .replace(/\s*\([^)]*\)/g, "")
      .replace(/\s*,.*$/g, "")
      .trim();

    if (!cleaned) return;
    counts.set(cleaned, (counts.get(cleaned) ?? 0) + 1);
  });

  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, 5);
}

function classRange(races: OverviewRaceGroup[]): string {
  const classes = uniqueValues(races.map((race) => text(race.raceClass)));
  if (!classes.length) return "-";
  if (classes.length === 1) return classes[0];
  return `${classes[0]} to ${classes[classes.length - 1]}`;
}

function watchlistTone(value: string): "good" | "warn" | "bad" {
  const upper = value.toUpperCase();
  if (upper.includes("HIGH") || upper.includes("LIVE") || upper.includes("FULL") || upper.includes("CLEAR")) return "good";
  if (upper.includes("OPEN") || upper.includes("PARTIAL") || upper.includes("MEDIUM") || upper.includes("BALANCED") || upper.includes("SNAPSHOT")) return "warn";
  return "bad";
}

function meetingStatusLabel(value: string): string {
  const upper = value.toUpperCase();
  if (upper === "FIELDS_READY") return "FIELDS READY";
  if (upper === "FIELDS_PENDING") return "FIELDS PENDING";
  if (upper === "FIELDS_UNAVAILABLE") return "FIELDS UNAVAILABLE";
  return value || "UNKNOWN";
}

function dayBucketLabel(value: string): string {
  const upper = value.toUpperCase();
  if (upper === "DAY+2") return "DAY +2";
  return upper || "UPCOMING";
}

function meetingStatusTone(value: string): "good" | "warn" | "bad" {
  const upper = value.toUpperCase();
  if (upper === "FIELDS_READY") return "good";
  if (upper === "FIELDS_PENDING") return "warn";
  return "bad";
}

function toneColor(tone: "good" | "warn" | "bad"): string {
  if (tone === "good") return "#a7f3d0";
  if (tone === "warn") return "#fde68a";
  return "#fecaca";
}

function raceProgramTrackRead(
  race: OverviewRaceGroup,
  matchingRows: TrackBiasRow[],
  surface: string,
): string {
  const distanceBand = distanceBandOf(race.distance);
  const conditionBand = conditionBandOf(race.todayTrackCondition, surface);

  const exactRows = matchingRows.filter(
    (row) =>
      text(row.distance_band).toUpperCase() === distanceBand &&
      text(row.track_condition_band).toUpperCase() === conditionBand,
  );

  const fallbackRows = exactRows.length
    ? exactRows
    : matchingRows.filter((row) => text(row.distance_band).toUpperCase() === distanceBand);

  if (!fallbackRows.length) return "-";

  return `${roleLabel(bestProfileType(fallbackRows))} | ${dominantBiasLabel(fallbackRows)}`;
}

function meetingPreviewNarrative(
  meeting: OverviewMeeting,
  raceCount: number,
  surface: string,
  distanceRange: string,
  scratchings: number,
  tabPriceStatus: string,
  trackDna: string,
  bestProfile: string,
): string {
  const profile = bestProfile === "UNAVAILABLE" ? "historical track profile is still unavailable" : `${roleLabel(bestProfile).toLowerCase()} runners currently look best suited`;
  return `${meeting.track} presents a ${raceCount}-race ${surface.toLowerCase()} program spanning ${distanceRange}. TAB coverage is ${tabPriceStatus.toLowerCase()}, ${scratchings} scratchings are already reflected, and the track DNA reads ${trackDna.toLowerCase()} with ${profile}.`;
}

export default function OverviewTab({
  staleSnapshot,
  currentMeeting,
  currentRace,
  currentMeetingRaces,
  upcomingMeetings,
  marketStateLabel,
  trackBiasRows,
  displayDate,
  setSelectedMeetingKey,
  setSelectedRaceKey,
  setSelectedHorseKey,
  setTab,
}: OverviewTabProps): React.ReactElement {
  if (!currentMeeting) {
    return (
      <div className="edgeTabSurface">
        <div className="edgeiq-no-live">No meeting is currently loaded for preview.</div>
      </div>
    );
  }

  const futureMeeting = text(currentMeeting.dashboardReady).toUpperCase() !== "YES";

  if (futureMeeting) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">
            <span>MEETING PREVIEW</span>
            <span className={`edgeiq-pill ${watchlistTone(currentMeeting.meetingStatus)}`}>{dayBucketLabel(currentMeeting.dayBucket)}</span>
          </div>
          <div style={{ padding: 12, display: "grid", gap: 12 }}>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Selected Meeting</div>
              <div className="edgeiq-mini-note-value">{currentMeeting.track}</div>
              <div className="edgeiq-mini-note-sub">
                {displayDate(currentMeeting.raceDate)} | {meetingStatusLabel(currentMeeting.meetingStatus)}
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Meeting Status</div>
                <div className="edgeiq-terminal-stat-value" style={{ color: toneColor(meetingStatusTone(currentMeeting.meetingStatus)) }}>
                  {meetingStatusLabel(currentMeeting.meetingStatus)}
                </div>
                <div className="edgeiq-terminal-stat-sub">current field release state for this meeting</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Meeting Type</div>
                <div className="edgeiq-terminal-stat-value">{currentMeeting.meetingType || "UNKNOWN"}</div>
                <div className="edgeiq-terminal-stat-sub">calendar-driven meeting discovery classification</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Expected Races</div>
                <div className="edgeiq-terminal-stat-value">{currentMeeting.races.length || currentMeeting.fieldRaces || 0}</div>
                <div className="edgeiq-terminal-stat-sub">will populate as soon as fields are released</div>
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Availability</div>
              <div className="edgeiq-mini-note-sub" style={{ marginTop: 6, color: "#dbe7f3" }}>
                Fields not yet available. EDGEiQ is monitoring this meeting and will populate intelligence automatically once fields are released.
              </div>
            </div>
          </div>
        </section>

        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">UPCOMING MEETINGS</div>
          <div style={{ padding: 12, display: "grid", gap: 8 }}>
            {upcomingMeetings.map((meeting) => (
              <div
                key={meeting.meetingKey}
                style={{
                  display: "grid",
                  gridTemplateColumns: "120px minmax(0, 1fr) 160px",
                  gap: 10,
                  alignItems: "center",
                  border: "1px solid rgba(41,72,90,0.82)",
                  borderRadius: 10,
                  background: "rgba(5,14,22,0.82)",
                  padding: "10px 12px",
                }}
              >
                <div>
                  <div style={{ color: "#6f8493", fontSize: 9, fontWeight: 900, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                    {dayBucketLabel(meeting.dayBucket)}
                  </div>
                  <div style={{ color: "#dbe7f3", fontSize: 12, fontWeight: 900 }}>{displayDate(meeting.raceDate)}</div>
                </div>
                <div>
                  <div style={{ color: "#f8fafc", fontSize: 15, fontWeight: 900 }}>{meeting.track}</div>
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>{meeting.meetingType || "Meeting"}</div>
                </div>
                <div style={{ justifySelf: "end" }}>
                    <span className={`edgeiq-pill ${meetingStatusTone(meeting.meetingStatus)}`}>{meetingStatusLabel(meeting.meetingStatus)}</span>
                  </div>
                </div>
              ))}
          </div>
        </section>
      </div>
    );
  }

  const meetingRows = currentMeetingRaces.flatMap((race) => race.rows);
  const activeMeetingRows = meetingRows.filter((row) => !row.isScratched);
  const scratchedMeetingRows = meetingRows.filter((row) => row.isScratched);

  const trackCondition = mostCommon(currentMeetingRaces.map((race) => text(race.todayTrackCondition)).filter(Boolean)) || "-";
  const surface = surfaceLabel(currentMeeting.track, trackCondition);
  const railPosition = mostCommon(meetingRows.map((row) => text(row.railPosition)).filter(Boolean)) || "-";
  const distanceRange = formatDistanceRange(currentMeetingRaces.map((race) => race.distance));

  const pricedRunnerCount = activeMeetingRows.filter((row) => row.marketPrice !== null && row.marketPrice > 0).length;
  const projectedRunnerCount = activeMeetingRows.filter((row) => row.ratedPrice !== null && row.ratedPrice > 0).length;
  const firstRace = currentMeetingRaces[0] ?? null;
  const lastRace = currentMeetingRaces[currentMeetingRaces.length - 1] ?? null;

  const matchingBiasRows = matchingTrackBiasRows(trackBiasRows, currentMeeting.track, surface);
  const meetingBiasRows = matchingBiasRows.filter(
    (row) => text(row.track_condition_band).toUpperCase() === conditionBandOf(trackCondition, surface),
  );
  const resolvedBiasRows = meetingBiasRows.length ? meetingBiasRows : matchingBiasRows;

  const trackDna = resolvedBiasRows.length ? dominantBiasLabel(resolvedBiasRows) : "UNAVAILABLE";
  const bestProfile = resolvedBiasRows.length ? bestProfileType(resolvedBiasRows) : "UNAVAILABLE";
  const runStyleBias = resolvedBiasRows.length ? runStyleBiasLabel(resolvedBiasRows) : "Unavailable";
  const whatTrackFavours = resolvedBiasRows.length ? trackFavorLabel(resolvedBiasRows) : "Unavailable";
  const barrierBias = barrierBiasLabel(resolvedBiasRows);

  const topJockeys = topParticipants(activeMeetingRows, "jockey");
  const topTrainers = topParticipants(activeMeetingRows, "trainer");

  const raceProgram: RaceProgramSummary[] = currentMeetingRaces.map((race) => {
    const actives = activeRows(race);
    const anchorRow =
      actives
        .filter((row) => row.ratedPrice !== null && row.ratedPrice > 0)
        .sort((a, b) => (fairWinChance(b) ?? -1) - (fairWinChance(a) ?? -1))[0] ??
      actives[0] ??
      null;

    const scratchCount = scratchedRows(race).length;
    const total = actives.length + scratchCount;
    const scratchImpact =
      scratchCount === 0
        ? "Clean"
        : scratchCount >= 3 || scratchCount >= Math.ceil(total * 0.25)
          ? "Heavy"
          : "Light";

    return {
      race,
      activeCount: actives.length,
      scratchedCount: scratchCount,
      liveCount: pricedActiveCount(race),
      projectedCount: projectedActiveCount(race),
      clarity: raceClarityLabel(race),
      tempo: expectedTempoLabel(race),
      confidence: confidenceLabel(anchorRow),
      trackRead: raceProgramTrackRead(race, matchingBiasRows, surface),
      scratchImpact,
    };
  });

  const highConfidenceRaces = raceProgram.filter((race) => race.confidence === "HIGH").length;
  const wideOpenRaces = raceProgram.filter((race) => race.clarity === "OPEN").length;
  const heavyScratchImpactRaces = raceProgram.filter((race) => race.scratchImpact === "Heavy").length;
  const missingProjectionRaces = raceProgram.filter((race) => race.projectedCount < race.activeCount).length;
  const liveCoverageRaces = raceProgram.filter((race) => race.liveCount === race.activeCount && race.activeCount > 0).length;

  const tabPriceStatus =
    pricedRunnerCount === 0
      ? "UNAVAILABLE"
      : staleSnapshot
        ? "SNAPSHOT"
        : pricedRunnerCount === activeMeetingRows.length
          ? "FULL LIVE"
          : "PARTIAL";

  const footerHealth = [
    {
      label: "TAB Prices Loaded",
      value: `${pricedRunnerCount}/${activeMeetingRows.length || 0}`,
      sub: `${tabPriceStatus.toLowerCase()} meeting coverage`,
      tone: tabPriceStatus === "FULL LIVE" ? "good" : tabPriceStatus === "PARTIAL" || tabPriceStatus === "SNAPSHOT" ? "warn" : "bad",
    },
    {
      label: "Scratchings Applied",
      value: `${scratchedMeetingRows.length}`,
      sub: "scratched runners removed from the active meeting preview",
      tone: scratchedMeetingRows.length ? "good" : "warn",
    },
    {
      label: "Model Coverage",
      value: `${projectedRunnerCount}/${activeMeetingRows.length || 0}`,
      sub: projectedRunnerCount === activeMeetingRows.length ? "full model coverage across active runners" : "some active runners still missing model coverage",
      tone: projectedRunnerCount === activeMeetingRows.length ? "good" : projectedRunnerCount > 0 ? "warn" : "bad",
    },
  ] as const;

  const previewNarrative = meetingPreviewNarrative(
    currentMeeting,
    currentMeetingRaces.length,
    surface,
    distanceRange,
    scratchedMeetingRows.length,
    tabPriceStatus,
    trackDna,
    bestProfile,
  );

  const baseRowBorderColor = "rgba(41, 72, 90, 0.82)";
  const baseRowBackground = "rgba(5, 14, 22, 0.82)";

  const rowButtonStyle: React.CSSProperties = {
    width: "100%",
    display: "grid",
    alignItems: "center",
    gap: 10,
    border: `1px solid ${baseRowBorderColor}`,
    borderRadius: 10,
    background: baseRowBackground,
    color: "#dbe7f3",
    padding: "10px 12px",
    textAlign: "left",
  };

  const compactLabelStyle: React.CSSProperties = {
    color: "#6f8493",
    fontSize: 9,
    fontWeight: 900,
    letterSpacing: "0.14em",
    textTransform: "uppercase",
  };

  const compactValueStyle: React.CSSProperties = {
    color: "#eef7ff",
    fontSize: 12,
    fontWeight: 900,
    lineHeight: 1.2,
  };

  return (
    <div className="edgeTabSurface">
      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">
          <span>MEETING PREVIEW</span>
          <span className={`edgeiq-pill ${watchlistTone(tabPriceStatus)}`}>{displayDate(currentMeeting.raceDate)}</span>
        </div>
        <div style={{ padding: 12, display: "grid", gap: 12 }}>
          <div
            style={{
              display: "grid",
              gap: 10,
              gridTemplateColumns: "minmax(0, 1.35fr) auto",
              alignItems: "start",
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div className="edgeiq-mini-note-label">Selected Meeting</div>
              <div className="edgeiq-mini-note-value">{currentMeeting.track}</div>
              <div className="edgeiq-mini-note-sub">
                {surface} | first race {formatTime(firstRace?.raceTime ?? "")} | last race {formatTime(lastRace?.raceTime ?? "")}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <span className={`edgeiq-pill ${watchlistTone(trackDna)}`}>{trackDna}</span>
              <span className={`edgeiq-pill ${watchlistTone(tabPriceStatus)}`}>TAB {tabPriceStatus}</span>
            </div>
          </div>

          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">Meeting Read</div>
            <div className="edgeiq-mini-note-sub" style={{ marginTop: 6, color: "#dbe7f3" }}>
              {previewNarrative}
            </div>
          </div>

          <div className="edgeiq-terminal-stat-grid">
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Race Count</div>
              <div className="edgeiq-terminal-stat-value">{currentMeetingRaces.length}</div>
              <div className="edgeiq-terminal-stat-sub">races on the selected meeting</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Active Runners</div>
              <div className="edgeiq-terminal-stat-value">{activeMeetingRows.length}</div>
              <div className="edgeiq-terminal-stat-sub">live runners still in the meeting view</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Scratched Runners</div>
              <div className="edgeiq-terminal-stat-value">{scratchedMeetingRows.length}</div>
              <div className="edgeiq-terminal-stat-sub">meeting scratchings already reflected</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Priced Runners</div>
              <div className="edgeiq-terminal-stat-value">{pricedRunnerCount}</div>
              <div className="edgeiq-terminal-stat-sub">active runners carrying a TAB quote</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">First Race</div>
              <div className="edgeiq-terminal-stat-value">R{firstRace?.raceNo ?? "-"}</div>
              <div className="edgeiq-terminal-stat-sub">{formatTime(firstRace?.raceTime ?? "")}</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Last Race</div>
              <div className="edgeiq-terminal-stat-value">R{lastRace?.raceNo ?? "-"}</div>
              <div className="edgeiq-terminal-stat-sub">{formatTime(lastRace?.raceTime ?? "")}</div>
            </div>
          </div>
        </div>
      </section>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 12,
        }}
      >
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">TRACK CONDITIONS / SETUP</div>
          <div
            style={{
              padding: 12,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Track Condition</div>
              <div className="edgeiq-mini-note-value">{trackCondition}</div>
              <div className="edgeiq-mini-note-sub">{surface} meeting profile</div>
            </div>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Rail Position</div>
              <div className="edgeiq-mini-note-value">{railPosition}</div>
              <div className="edgeiq-mini-note-sub">current rail position for the selected meeting</div>
            </div>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Distance Range</div>
              <div className="edgeiq-mini-note-value">{distanceRange}</div>
              <div className="edgeiq-mini-note-sub">spread from sprint trips to staying races</div>
            </div>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Class Range</div>
              <div className="edgeiq-mini-note-value">{classRange(currentMeetingRaces)}</div>
              <div className="edgeiq-mini-note-sub">mix of classes across the card</div>
            </div>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Scratchings</div>
              <div className="edgeiq-mini-note-value">{scratchedMeetingRows.length}</div>
              <div className="edgeiq-mini-note-sub">total runners currently scratched</div>
            </div>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">TAB Price Status</div>
              <div className="edgeiq-mini-note-value">{tabPriceStatus}</div>
              <div className="edgeiq-mini-note-sub">{pricedRunnerCount}/{activeMeetingRows.length || 0} active runners priced</div>
            </div>
          </div>
        </section>

        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">TRACK INTELLIGENCE</div>
          <div style={{ padding: 12, display: "grid", gap: 10 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Track DNA</div>
                <div className="edgeiq-mini-note-value">{trackDna}</div>
                <div className="edgeiq-mini-note-sub">historical meeting profile</div>
              </div>
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">What The Track Favours</div>
                <div className="edgeiq-mini-note-value">{whatTrackFavours}</div>
                <div className="edgeiq-mini-note-sub">best fit from the current track profile read</div>
              </div>
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Run-Style Bias</div>
                <div className="edgeiq-mini-note-value">{runStyleBias}</div>
                <div className="edgeiq-mini-note-sub">how the card is leaning by run style today</div>
              </div>
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Barrier Effect</div>
                <div className="edgeiq-mini-note-value">{barrierBias}</div>
                <div className="edgeiq-mini-note-sub">dedicated barrier profile not available yet</div>
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">EDGEiQ Insight</div>
              <div className="edgeiq-mini-note-sub" style={{ marginTop: 6, color: "#dbe7f3" }}>
                {trackInsight(resolvedBiasRows, trackCondition, surface)}
              </div>
            </div>
          </div>
        </section>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 12,
        }}
      >
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">MEETING PARTICIPANTS</div>
          <div
            style={{
              padding: 12,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <div className="edgeiq-terminal-mini-table">
              <div className="edgeiq-terminal-mini-title">Most Active Jockeys Today</div>
              <div className="edgeiq-terminal-mini-rows">
                {topJockeys.length ? (
                  topJockeys.map((item) => (
                    <div key={`j-${item.name}`} className="edgeiq-terminal-mini-row">
                      <div className="edgeiq-terminal-mini-head">
                        <span>{item.name}</span>
                        <strong>{item.count} rides</strong>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="edgeiq-no-live">No jockey activity is available on this card.</div>
                )}
              </div>
            </div>

            <div className="edgeiq-terminal-mini-table">
              <div className="edgeiq-terminal-mini-title">Most Active Trainers Today</div>
              <div className="edgeiq-terminal-mini-rows">
                {topTrainers.length ? (
                  topTrainers.map((item) => (
                    <div key={`t-${item.name}`} className="edgeiq-terminal-mini-row">
                      <div className="edgeiq-terminal-mini-head">
                        <span>{item.name}</span>
                        <strong>{item.count} runners</strong>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="edgeiq-no-live">No trainer activity is available on this card.</div>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">WATCHLIST SUMMARY</div>
          <div
            style={{
              padding: 12,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">High Confidence Races</div>
              <div className="edgeiq-terminal-stat-value" style={{ color: toneColor("good") }}>{highConfidenceRaces}</div>
              <div className="edgeiq-terminal-stat-sub">races carrying a stronger top-line confidence read</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Wide Open Races</div>
              <div className="edgeiq-terminal-stat-value" style={{ color: toneColor("warn") }}>{wideOpenRaces}</div>
              <div className="edgeiq-terminal-stat-sub">races where the shape still looks more open</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Heavy Scratch Impact</div>
              <div className="edgeiq-terminal-stat-value" style={{ color: toneColor(heavyScratchImpactRaces ? "warn" : "good") }}>{heavyScratchImpactRaces}</div>
              <div className="edgeiq-terminal-stat-sub">races materially changed by scratchings</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Missing Projections</div>
              <div className="edgeiq-terminal-stat-value" style={{ color: toneColor(missingProjectionRaces ? "warn" : "good") }}>{missingProjectionRaces}</div>
              <div className="edgeiq-terminal-stat-sub">races still missing full model coverage</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Live TAB Coverage</div>
              <div className="edgeiq-terminal-stat-value" style={{ color: toneColor("good") }}>{liveCoverageRaces}</div>
              <div className="edgeiq-terminal-stat-sub">races with full active TAB market coverage</div>
            </div>
          </div>
        </section>
      </div>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">RACE PROGRAM</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          <div className="edgeiq-data-note">Race | Time | Setup | Field | Shape | Tempo | Confidence | Track read</div>

          {raceProgram.map((item) => {
            const selected = currentRace?.key === item.race.key;
            return (
              <button
                key={item.race.key}
                type="button"
                onClick={() => {
                  setSelectedMeetingKey(currentMeeting.meetingKey);
                  setSelectedRaceKey(item.race.key);
                  setSelectedHorseKey("");
                  setTab("INTELLIGENCE");
                }}
                style={{
                  ...rowButtonStyle,
                  gridTemplateColumns: "64px 76px minmax(120px, 1fr) 88px 90px 100px 96px minmax(130px, 1fr)",
                  borderColor: selected ? "rgba(52, 211, 153, 0.55)" : baseRowBorderColor,
                  background: selected ? "rgba(8, 33, 28, 0.88)" : baseRowBackground,
                }}
              >
                <div>
                  <div style={compactLabelStyle}>Race</div>
                  <div style={compactValueStyle}>R{item.race.raceNo}</div>
                </div>
                <div>
                  <div style={compactLabelStyle}>Time</div>
                  <div style={compactValueStyle}>{formatTime(item.race.raceTime)}</div>
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={compactLabelStyle}>Setup</div>
                  <div style={compactValueStyle}>{item.race.distance ? `${item.race.distance}m` : "-"}</div>
                  <div style={{ color: "#94a3b8", fontSize: 10, lineHeight: 1.3 }}>{item.race.raceClass || "-"}</div>
                </div>
                <div>
                  <div style={compactLabelStyle}>Field</div>
                  <div style={compactValueStyle}>{item.activeCount} live</div>
                  <div style={{ color: "#94a3b8", fontSize: 10, lineHeight: 1.3 }}>{item.scratchedCount} scratched</div>
                </div>
                <div>
                  <div style={compactLabelStyle}>Shape</div>
                  <div style={compactValueStyle}>{item.clarity}</div>
                  <div style={{ color: "#94a3b8", fontSize: 10, lineHeight: 1.3 }}>{item.scratchImpact} scratch impact</div>
                </div>
                <div>
                  <div style={compactLabelStyle}>Tempo</div>
                  <div style={compactValueStyle}>{item.tempo}</div>
                </div>
                <div>
                  <div style={compactLabelStyle}>Confidence</div>
                  <div style={compactValueStyle}>{item.confidence}</div>
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={compactLabelStyle}>Track Read</div>
                  <div style={{ ...compactValueStyle, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.trackRead}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">UPCOMING MEETINGS</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          {upcomingMeetings.map((meeting) => (
            <div
              key={meeting.meetingKey}
              style={{
                display: "grid",
                gridTemplateColumns: "120px minmax(0, 1fr) 160px",
                gap: 10,
                alignItems: "center",
                border: "1px solid rgba(41,72,90,0.82)",
                borderRadius: 10,
                background: "rgba(5,14,22,0.82)",
                padding: "10px 12px",
              }}
            >
              <div>
                <div style={{ color: "#6f8493", fontSize: 9, fontWeight: 900, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                  {dayBucketLabel(meeting.dayBucket)}
                </div>
                <div style={{ color: "#dbe7f3", fontSize: 12, fontWeight: 900 }}>{displayDate(meeting.raceDate)}</div>
              </div>
              <div>
                <div style={{ color: "#f8fafc", fontSize: 15, fontWeight: 900 }}>{meeting.track}</div>
                <div style={{ color: "#94a3b8", fontSize: 11 }}>{meeting.meetingType || "Meeting"}</div>
              </div>
              <div style={{ justifySelf: "end" }}>
                <span className={`edgeiq-pill ${meetingStatusTone(meeting.meetingStatus)}`}>{meetingStatusLabel(meeting.meetingStatus)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">CARD HEALTH</div>
        <div
          style={{
            padding: "10px 12px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 10,
          }}
        >
          {footerHealth.map((item) => (
            <div
              key={item.label}
              style={{
                border: "1px solid rgba(41, 72, 90, 0.6)",
                borderRadius: 10,
                background: "rgba(5, 14, 22, 0.68)",
                padding: "8px 10px",
              }}
            >
              <div style={{ color: "#6f8493", fontSize: 9, fontWeight: 900, letterSpacing: "0.14em", textTransform: "uppercase" }}>
                {item.label}
              </div>
              <div style={{ marginTop: 4, color: toneColor(item.tone), fontSize: 13, fontWeight: 900 }}>
                {item.value}
              </div>
              <div style={{ marginTop: 4, color: "#94a3b8", fontSize: 10, lineHeight: 1.35 }}>
                {item.sub}
              </div>
            </div>
          ))}
          <div
            style={{
              border: "1px solid rgba(41, 72, 90, 0.6)",
              borderRadius: 10,
              background: "rgba(5, 14, 22, 0.68)",
              padding: "8px 10px",
            }}
          >
            <div style={{ color: "#6f8493", fontSize: 9, fontWeight: 900, letterSpacing: "0.14em", textTransform: "uppercase" }}>
              Meeting Status
            </div>
              <div style={{ marginTop: 4, color: toneColor(watchlistTone(marketStateLabel)), fontSize: 13, fontWeight: 900 }}>
                {marketStateLabel}
              </div>
              <div style={{ marginTop: 4, color: "#94a3b8", fontSize: 10, lineHeight: 1.35 }}>
                current live state for the selected meeting
              </div>
            </div>
          </div>
      </section>
    </div>
  );
}
