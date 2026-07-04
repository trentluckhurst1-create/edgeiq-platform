import { cleanTrack, text } from "../utils/edgeiqFormat";
import type { CsvRow } from "../utils/edgeiqCsv";
import { firstText } from "../utils/raceRowHelpers";
import type { ProductShellRace } from "./productShellRaceService";

export type ProductShellMeeting = {
  meetingDate: string;
  dayLabel: string;
  trackName: string;
  meetingKey: string;
  meetingStatus: string;
  raceCount: number;
  firstRaceTime: string;
  lastRaceTime: string;
  trackConditionLatest: string;
  railPositionLatest: string;
  weather: string;
  temperature: string;
  windDirection: string;
  windSpeed: string;
  rainfall24h: string;
  rainfall7d: string;
  irrigation24h: string;
  irrigation7d: string;
  updated: string;
  marketStatusSummary: string;
  stateRegion: string;
  dataQualityStatus: string;
  mapFile: string;
  mapAvailable: boolean;
};

export function buildProductShellMeetings(params: {
  productShellRaces: ProductShellRace[];
  productMeetingRows: CsvRow[];
  meetingCalendarRows: CsvRow[];
  liveTrackIntelligenceRows: CsvRow[];
  trackMapManifestRows: CsvRow[];
}): ProductShellMeeting[] {
  const {
    productShellRaces,
    productMeetingRows,
    meetingCalendarRows,
    liveTrackIntelligenceRows,
    trackMapManifestRows,
  } = params;

  const meetingMap = new Map<string, ProductShellMeeting>();

  const cleanMeetingValue = (value: unknown, fallback = "-") => {
    const raw = text(value).replace(/ÃƒÂ¢Ã¢â€šÂ¬.|Ã¢â‚¬â€/g, "-").trim();
    if (!raw || /^(-|TBC|TIME TBC|N\/A|NA|null|undefined)$/i.test(raw)) return fallback;
    return raw.replace(/_/g, " ");
  };

  const dayKeyFor = (value: unknown) => {
    const raw = text(value).toUpperCase().replace(/\s+/g, "").replace("DY+2", "DAY+2");
    if (raw.includes("TODAY")) return "TODAY";
    if (raw.includes("TOMORROW")) return "TOMORROW";
    if (raw.includes("DAY+2")) return "DAY+2";
    return raw || "DAY+2";
  };

  const normaliseMapTrack = (value: unknown) => {
    const raw = cleanTrack(text(value));
    if (raw.includes("SANDOWN")) return "SANDOWN";
    if (raw.includes("BALLARAT")) return "BALLARAT";
    if (raw.includes("CAULFIELD")) return "CAULFIELD";
    return raw;
  };

  const availableMapFiles = new Set(["/assets/tracks/caulfield_edgeiq.svg", "/assets/tracks/flemington_edgeiq.svg"]);
  const manifestByTrack = new Map<string, CsvRow>();

  trackMapManifestRows.forEach((row) => {
    const key = normaliseMapTrack(firstText(row, ["track"], ""));
    if (key) manifestByTrack.set(key, row);
  });

  const applyMap = (meeting: { trackName: string; mapFile: string; mapAvailable: boolean }) => {
    const manifest = manifestByTrack.get(normaliseMapTrack(meeting.trackName));
    const mapFile = firstText(manifest || {}, ["map_file"], "");
    meeting.mapFile = mapFile;
    meeting.mapAvailable = Boolean(mapFile && availableMapFiles.has(mapFile));
  };

  const ensureMeeting = (seed: any) => {
    const trackName = cleanMeetingValue(seed.trackName, "Meeting");
    const meetingDate = cleanMeetingValue(seed.meetingDate, "-");
    const meetingKey = text(seed.meetingKey) || `${meetingDate}_${cleanTrack(trackName)}`;
    const existing = meetingMap.get(meetingKey);
    if (existing) return existing;

    const created: ProductShellMeeting = {
      meetingDate,
      dayLabel: dayKeyFor(seed.dayLabel),
      trackName,
      meetingKey,
      meetingStatus: cleanMeetingValue(seed.meetingStatus, "Fields pending"),
      raceCount: Number(seed.raceCount) || 0,
      firstRaceTime: cleanMeetingValue(seed.firstRaceTime),
      lastRaceTime: cleanMeetingValue(seed.lastRaceTime),
      trackConditionLatest: cleanMeetingValue(seed.trackConditionLatest),
      railPositionLatest: cleanMeetingValue(seed.railPositionLatest),
      weather: cleanMeetingValue(seed.weather),
      temperature: cleanMeetingValue(seed.temperature),
      windDirection: cleanMeetingValue(seed.windDirection),
      windSpeed: cleanMeetingValue(seed.windSpeed),
      rainfall24h: cleanMeetingValue(seed.rainfall24h),
      rainfall7d: cleanMeetingValue(seed.rainfall7d),
      irrigation24h: cleanMeetingValue(seed.irrigation24h),
      irrigation7d: cleanMeetingValue(seed.irrigation7d),
      updated: cleanMeetingValue(seed.updated),
      marketStatusSummary: cleanMeetingValue(seed.marketStatusSummary, "Awaiting Feed"),
      stateRegion: cleanMeetingValue(seed.stateRegion, "VIC"),
      dataQualityStatus: cleanMeetingValue(seed.dataQualityStatus, "Ready"),
      mapFile: "",
      mapAvailable: false,
    };

    applyMap(created);
    meetingMap.set(meetingKey, created);
    return created;
  };

  productMeetingRows.forEach((row) => {
    const meetingDate = firstText(row, ["meeting_date", "race_date"], "");
    const trackName = firstText(row, ["track"], "");
    if (!meetingDate || !trackName) return;

    ensureMeeting({
      meetingDate,
      dayLabel: firstText(row, ["day_label", "day_bucket"], ""),
      trackName,
      meetingKey: firstText(row, ["meeting_key"], `${meetingDate}_${cleanTrack(trackName)}`),
      meetingStatus: firstText(row, ["meeting_status"], "Fields ready"),
      raceCount: firstText(row, ["race_count"], "0"),
      firstRaceTime: firstText(row, ["first_race_time"], ""),
      lastRaceTime: firstText(row, ["last_race_time"], ""),
      trackConditionLatest: firstText(row, ["track_condition_latest"], ""),
      railPositionLatest: firstText(row, ["rail_position_latest"], ""),
      marketStatusSummary: firstText(row, ["market_status_summary"], ""),
      stateRegion: firstText(row, ["state", "region"], "VIC"),
      dataQualityStatus: firstText(row, ["data_quality_status"], "Ready"),
    });
  });

  meetingCalendarRows.forEach((row) => {
    const meetingDate = firstText(row, ["race_date", "meeting_date"], "");
    const trackName = firstText(row, ["track"], "");
    if (!meetingDate || !trackName) return;

    ensureMeeting({
      meetingDate,
      dayLabel: firstText(row, ["day_bucket", "day_label"], ""),
      trackName,
      meetingKey: `${meetingDate}_${cleanTrack(trackName)}`,
      meetingStatus: firstText(row, ["meeting_type"], "Fields pending"),
      stateRegion: "VIC",
      dataQualityStatus: "Calendar",
    });
  });

  const raceCountByMeeting = new Map<string, number>();
  productShellRaces.forEach((race) => {
    if (!meetingMap.has(race.meetingKey)) return;
    raceCountByMeeting.set(race.meetingKey, (raceCountByMeeting.get(race.meetingKey) || 0) + 1);
  });

  liveTrackIntelligenceRows.forEach((row) => {
    const meetingDate = firstText(row, ["race_date", "meeting_date"], "");
    const trackName = firstText(row, ["track"], "");
    const meetingKey = `${meetingDate}_${cleanTrack(trackName)}`;
    const existing = meetingMap.get(meetingKey);
    if (!existing) return;

    if (existing.trackConditionLatest === "-") existing.trackConditionLatest = cleanMeetingValue(firstText(row, ["track_condition", "condition_group"], ""));
    if (existing.railPositionLatest === "-") existing.railPositionLatest = cleanMeetingValue(firstText(row, ["rail_position", "rail"], ""));
    applyMap(existing);
  });

  productShellRaces.forEach((race) => {
    const existing = meetingMap.get(race.meetingKey) || (race.fieldSize > 0
      ? ensureMeeting({
        meetingDate: race.meetingDate,
        dayLabel: race.dayLabel,
        trackName: race.trackName,
        meetingKey: race.meetingKey,
        meetingStatus: "Fields Ready",
        raceCount: 0,
        firstRaceTime: race.raceTime,
        lastRaceTime: race.raceTime,
        trackConditionLatest: race.trackConditionValue,
        railPositionLatest: race.railValue,
        marketStatusSummary: race.marketStateValue,
        dataQualityStatus: race.dataQualityStatus,
      })
      : null);

    if (!existing) return;

    existing.meetingStatus = "Fields Ready";
    existing.raceCount = Math.max(existing.raceCount, raceCountByMeeting.get(race.meetingKey) || 0);

    if (race.raceTime !== "Time TBC" && race.raceTime !== "-") {
      existing.firstRaceTime = existing.firstRaceTime === "-" ? race.raceTime : [existing.firstRaceTime, race.raceTime].sort()[0];
      existing.lastRaceTime = existing.lastRaceTime === "-" ? race.raceTime : [existing.lastRaceTime, race.raceTime].sort().slice(-1)[0];
    }

    if (existing.trackConditionLatest === "-") existing.trackConditionLatest = race.trackConditionValue || "-";
    if (existing.railPositionLatest === "-") existing.railPositionLatest = race.railValue || "-";
    if (existing.marketStatusSummary === "Awaiting Feed") existing.marketStatusSummary = race.marketStateValue || "Awaiting Feed";

    applyMap(existing);
  });

  return Array.from(meetingMap.values()).sort((a, b) => {
    const dayOrder = { TODAY: 0, TOMORROW: 1, "DAY+2": 2 } as Record<string, number>;
    return (dayOrder[a.dayLabel] ?? 9) - (dayOrder[b.dayLabel] ?? 9) || a.meetingDate.localeCompare(b.meetingDate) || cleanTrack(a.trackName).localeCompare(cleanTrack(b.trackName));
  });
}
