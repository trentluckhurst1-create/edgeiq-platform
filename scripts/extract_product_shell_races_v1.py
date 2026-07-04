from pathlib import Path

root = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
path = root / "src" / "components" / "RaceIntelligenceScreen.tsx"
text = path.read_text(encoding="utf-8")

service = root / "src" / "services" / "productShellRaceService.ts"
service.write_text(r'''import { cleanTrack } from "../utils/edgeiqFormat";
import type { CsvRow } from "../utils/edgeiqCsv";
import { distance, firstNum, firstText, raceClass, raceDate, raceNo, track, trackCondition } from "../utils/raceRowHelpers";

export type ProductShellRace = {
  meetingDate: string;
  dayLabel: string;
  trackName: string;
  meetingKey: string;
  raceKey: string;
  raceNoValue: string;
  raceTime: string;
  raceTitle: string;
  distanceValue: string;
  raceClassValue: string;
  trackConditionValue: string;
  railValue: string;
  fieldSize: number;
  marketStateValue: string;
  ratingReference: string;
  priceReference: string;
  dataQualityStatus: string;
};

export function buildProductShellRaces(params: {
  runnerRows: CsvRow[];
  raceListRows: CsvRow[];
}): ProductShellRace[] {
  const { runnerRows, raceListRows } = params;

  const raceMap = new Map<string, ProductShellRace>();

  runnerRows.forEach((row) => {
    const dateValue = raceDate(row) || firstText(row, ["meeting_date", "_date"], "");
    const trackName = track(row);
    const raceNoValue = raceNo(row);
    if (!trackName || !raceNoValue) return;

    const meetingKey = firstText(row, ["meeting_key"], `${dateValue}_${cleanTrack(trackName)}`);
    const raceKeyValue = firstText(row, ["race_key"], `${meetingKey}_R${raceNoValue}`);
    const existing = raceMap.get(raceKeyValue);

    if (existing) {
      existing.fieldSize += 1;
      if (existing.raceTime === "Time TBC") existing.raceTime = firstText(row, ["race_time", "jump_time", "start_time"], existing.raceTime) || existing.raceTime;
      if (existing.trackConditionValue === "-") existing.trackConditionValue = trackCondition(row);
      if (existing.railValue === "-") existing.railValue = firstText(row, ["rail_position", "rail", "rail_clean"], "-");
      return;
    }

    const priceReady = firstNum(row, ["edgeiq_active_display_fair_price", "edgeiq_v7_2g2_guarded_display_fair_price", "fair_price"]) !== null;
    const ratingReady = firstNum(row, ["projected_rating_V6_1_RESERCH", "projected_rating_v5_2", "total_rating_points"]) !== null;

    raceMap.set(raceKeyValue, {
      meetingDate: dateValue,
      dayLabel: (() => {
        const rawDayLabel = firstText(row, ["day_bucket"], "UPCOMING").replace("DY+2", "DY +2");
        const rawMeetingDate = firstText(row, ["race_date", "meeting_date", "date"], "");
        const parsedMeetingDate = rawMeetingDate ? new Date(rawMeetingDate) : null;
        const isFutureOffset = /^DY\s*\+\s*\d+$/i.test(rawDayLabel);

        if (isFutureOffset && parsedMeetingDate && !Number.isNaN(parsedMeetingDate.getTime())) {
          return parsedMeetingDate
            .toLocaleDateString("en-AU", {
              weekday: "long",
              day: "2-digit",
              month: "short",
              year: "numeric",
            })
            .toUpperCase()
            .replace(",", " ");
        }

        return rawDayLabel;
      })(),
      trackName,
      meetingKey,
      raceKey: raceKeyValue,
      raceNoValue,
      raceTime: firstText(row, ["race_time", "jump_time", "start_time"], "Time TBC") || "Time TBC",
      raceTitle: firstText(row, ["race_title", "race_name"], `${trackName} R${raceNoValue}`),
      distanceValue: distance(row),
      raceClassValue: raceClass(row),
      trackConditionValue: trackCondition(row),
      railValue: firstText(row, ["rail_position", "rail", "rail_clean"], "-"),
      fieldSize: 1,
      marketStateValue: firstText(row, ["market_state", "tab_fixed_betting_status", "market_source_status"], "PENDING").replace(/_/g, " ").toUpperCase(),
      ratingReference: ratingReady ? "Performance reference" : "Performance Index pending",
      priceReference: priceReady ? "EDGEiQ display" : "Price pending",
      dataQualityStatus: "READY",
    });
  });

  if (raceListRows.length > 0) {
    raceListRows.forEach((row) => {
      const meetingDate = firstText(row, ["race_date"], "");
      const trackName = firstText(row, ["normalised_track", "track"], "");
      const raceNoValue = firstText(row, ["race_no"], "");

      if (!meetingDate || !trackName || !raceNoValue) return;

      const meetingKey = `${meetingDate}_${cleanTrack(trackName)}`;
      const raceKeyValue = `${meetingKey}_R${raceNoValue}`;

      if (raceMap.has(raceKeyValue)) return;

      const rawRaceTime = firstText(row, ["race_time_utc"], "");
      const parsedRaceTime = rawRaceTime ? new Date(rawRaceTime) : null;
      const raceTime = parsedRaceTime && !Number.isNaN(parsedRaceTime.getTime())
        ? parsedRaceTime.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit" })
        : "Time TBC";

      raceMap.set(raceKeyValue, {
        meetingDate,
        dayLabel: firstText(row, ["day_bucket"], "UPCOMING"),
        trackName,
        meetingKey,
        raceKey: raceKeyValue,
        raceNoValue,
        raceTime,
        raceTitle: firstText(row, ["race_name"], "") || `${trackName} R${raceNoValue}`,
        distanceValue: firstText(row, ["distance"], "-"),
        raceClassValue: firstText(row, ["race_class"], "-"),
        trackConditionValue: firstText(row, ["track_condition"], "-"),
        railValue: firstText(row, ["rail_position"], "-"),
        fieldSize: 0,
        marketStateValue: firstText(row, ["race_status"], "PENDING").replace(/_/g, " ").toUpperCase(),
        ratingReference: "Fields pending",
        priceReference: "Fields pending",
        dataQualityStatus: firstText(row, ["race_status"], "PENDING"),
      });
    });
  }

  return Array.from(raceMap.values()).sort((a, b) =>
    a.meetingDate.localeCompare(b.meetingDate) ||
    cleanTrack(a.trackName).localeCompare(cleanTrack(b.trackName)) ||
    (Number(a.raceNoValue) || 999) - (Number(b.raceNoValue) || 999)
  );
}
''', encoding="utf-8")

start = text.index(" const productShellRaces = useMemo(() => {")
end = text.index("\n const productShellMeetings = useMemo(() => {", start)

replacement = ''' const productShellRaces = useMemo(() => buildProductShellRaces({
  runnerRows,
  raceListRows,
 }), [runnerRows, raceListRows]);
'''

text = text[:start] + replacement + text[end:]

import_line = 'import { buildProductShellRaces } from "../services/productShellRaceService";'
if import_line not in text:
    lines = text.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].startswith("import "):
        insert_at += 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("[PRODUCT_SHELL_RACE_SERVICE_EXTRACT] complete")
