import { useEffect, useMemo, useState } from "react";
import { cleanText, formatUserLocalRaceTime, raceDateTimeMs } from "../utils/raceTime";

type AnyRow = Record<string, any>;

type Props = {
  meetings?: AnyRow[];
  currentRaceKey?: string;
  onSelectRace?: (raceKey: string) => void;
};

const CLOSED_GRACE_MINUTES = 3;

function clean(v: any): string {
  return cleanText(v);
}

function raceKey(r: AnyRow): string {
  return clean(r.key) || `${clean(r.raceDate || r.race_date)}|${clean(r.track)}|${clean(r.raceNo || r.race_no)}`;
}

function parseRaceDateTime(r: AnyRow): number {
  return raceDateTimeMs(r) ?? 0;
}

function flattenMeetings(meetings: AnyRow[] = []): AnyRow[] {
  const rows: AnyRow[] = [];
  meetings.forEach((m) => {
    const races = Array.isArray(m.races) ? m.races : Array.isArray(m.rows) ? m.rows : [];
    if (races.length) {
      races.forEach((r: AnyRow) => {
        const firstRunner = Array.isArray(r.rows) ? r.rows[0] : null;
        rows.push({
          ...r,
          meetingKey: m.key || m.meetingKey,
          raceDate: r.raceDate ?? r.race_date ?? m.raceDate ?? m.race_date,
          raceTime: r.raceTime ?? r.race_time ?? firstRunner?.raceTime ?? firstRunner?.race_time,
          race_time_utc: r.race_time_utc ?? r.raceTimeUtc ?? m.race_time_utc ?? m.raceTimeUtc ?? firstRunner?.race_time_utc,
          race_time_local: r.race_time_local ?? m.race_time_local ?? firstRunner?.race_time_local,
          track: r.track ?? m.track,
          state: r.state ?? m.state ?? firstRunner?.state,
          track_timezone: r.track_timezone ?? r.timezone ?? m.track_timezone ?? m.timezone ?? firstRunner?.track_timezone ?? firstRunner?.timezone,
          trackCondition: r.trackCondition ?? r.track_condition ?? m.trackCondition ?? m.track_condition ?? firstRunner?.todayTrackCondition,
          distance: r.distance ?? firstRunner?.distance,
          status: r.status ?? r.raceStatus ?? r.race_status,
        });
      });
    } else {
      rows.push(m);
    }
  });
  return rows;
}

function statusFor(r: AnyRow, now: number): { label: string; closed: boolean; minutes: number } {
  const rawStatus = clean(r.status || r.raceStatus || r.race_status).toUpperCase();
  const t = parseRaceDateTime(r);

  if (/CLOSED|FINAL|RESULT|ABANDON|JUMPED|CLOSE/.test(rawStatus)) {
    return { label: "CLOSED", closed: true, minutes: -999 };
  }

  if (!t) return { label: "OPEN", closed: false, minutes: 9999 };

  const minutes = Math.round((t - now) / 60000);
  if (minutes < -CLOSED_GRACE_MINUTES) return { label: "CLOSED", closed: true, minutes };
  if (minutes <= 0) return { label: "LIVE", closed: false, minutes };
  if (minutes < 60) return { label: `${minutes}m`, closed: false, minutes };

  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return { label: `${h}h ${m}m`, closed: false, minutes };
}

function condClass(cond: string): string {
  const c = cond.toUpperCase();
  if (c.includes("HEAVY")) return "edge-ticker-cond-heavy";
  if (c.includes("SOFT")) return "edge-ticker-cond-soft";
  if (c.includes("GOOD")) return "edge-ticker-cond-good";
  if (c.includes("FAST")) return "edge-ticker-cond-fast";
  return "";
}

export default function EdgeRaceTicker({ meetings = [], currentRaceKey = "", onSelectRace }: Props) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15000);
    return () => window.clearInterval(timer);
  }, []);

  const tickerRows = useMemo(() => {
    return flattenMeetings(meetings)
      .map((r: AnyRow) => ({ ...r, _status: statusFor(r, now), _time: parseRaceDateTime(r), _key: raceKey(r) }))
      .filter((r) => !r._status.closed)
      .sort((a: AnyRow, b: AnyRow) => {
        const at = a._time || Number.MAX_SAFE_INTEGER;
        const bt = b._time || Number.MAX_SAFE_INTEGER;
        return at - bt || clean(a.track).localeCompare(clean(b.track)) || Number(a.raceNo ?? a.race_no ?? 0) - Number(b.raceNo ?? b.race_no ?? 0);
      })
      .slice(0, 14);
  }, [meetings, now]);

  if (!tickerRows.length) {
    return <div className="edge-race-ticker"><div className="edge-race-ticker-brand">EDGEiQ RACING</div><div className="edge-race-ticker-empty">No upcoming races</div></div>;
  }

  return (
    <div className="edge-race-ticker">
      <div className="edge-race-ticker-brand">EDGEiQ RACING</div>
      <div className="edge-race-ticker-strip">
        {tickerRows.map((r: AnyRow) => {
          const k = r._key;
          const active = k === currentRaceKey;
          const track = clean(r.track).toUpperCase();
          const rn = clean(r.raceNo || r.race_no || r.no);
          const dist = clean(r.distance || r.dist);
          const cond = clean(r.trackCondition || r.track_condition);
          const time = formatUserLocalRaceTime(r, undefined, "");
          const label = r._status.label;
          return (
            <button key={k} type="button" className={["edge-race-ticker-pill", active ? "edge-race-ticker-pill-active" : "", label === "LIVE" ? "edge-race-ticker-pill-live" : ""].join(" ")} onClick={() => onSelectRace?.(k)} title={`${track} R${rn}`}>
              <span className="edge-race-ticker-main">{track} R{rn}</span>
              {time ? <span className="edge-race-ticker-meta">{time}</span> : null}
              {dist ? <span className="edge-race-ticker-meta">{dist}m</span> : null}
              {cond ? <span className={`edge-race-ticker-cond ${condClass(cond)}`}>{cond}</span> : null}
              <span className="edge-race-ticker-countdown">{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
