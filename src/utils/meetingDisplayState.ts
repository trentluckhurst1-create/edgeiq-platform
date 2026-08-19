export type EdgeMeetingDisplayState =
  | "CURRENT_DAY_MEETING"
  | "FUTURE_MEETING_WITH_FIELDS"
  | "FUTURE_MEETING_WITHOUT_FIELDS";

export type EdgeMeetingLike =
  | {
      raceDate?: string | null;
      dayBucket?: string | null;
      meetingStatus?: string | null;
      dashboardReady?: string | null;
    }
  | null
  | undefined;

function clean(value: unknown): string {
  return String(value ?? "").trim();
}

function compareDateToToday(dateValue: unknown): number | null {
  const raw = clean(dateValue);
  if (!raw) return null;

  const parsed = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  parsed.setHours(0, 0, 0, 0);

  return Math.round((parsed.getTime() - today.getTime()) / 86400000);
}

function isFutureBucket(dayBucket: unknown): boolean {
  const value = clean(dayBucket).toUpperCase();
  return value === "TOMORROW" || value === "DAY+2" || value === "DAY +2";
}

export function getMeetingDisplayState(meeting: EdgeMeetingLike): EdgeMeetingDisplayState {
  if (!meeting) return "CURRENT_DAY_MEETING";

  const dayDelta = compareDateToToday(meeting.raceDate);
  const futureMeeting = dayDelta !== null ? dayDelta > 0 : isFutureBucket(meeting.dayBucket);

  if (!futureMeeting) return "CURRENT_DAY_MEETING";

  const meetingStatus = clean(meeting.meetingStatus).toUpperCase();
  const dashboardReady = clean(meeting.dashboardReady).toUpperCase();
  const fieldsReady = meetingStatus === "FIELDS_READY" || dashboardReady === "YES";

  return fieldsReady ? "FUTURE_MEETING_WITH_FIELDS" : "FUTURE_MEETING_WITHOUT_FIELDS";
}

export function isFutureMeetingDisplayState(state: EdgeMeetingDisplayState): boolean {
  return state !== "CURRENT_DAY_MEETING";
}
