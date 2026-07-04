import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type LiveRace = {
  race_date?: string;
  track?: string;
  race_no?: string | number;
  race_time?: string;
  jump_time?: string;
  race_datetime?: string;
  race_status?: string;
  active_runners?: string | number;
  scratchings?: string | number;
  top_rated?: string;
  top_rated_price?: string | number;
};

function text(v: unknown): string {
  return String(v ?? "").trim();
}

function raceNo(v: unknown): string {
  const raw = text(v).replace(".0", "");
  return raw ? `R${raw}` : "R?";
}

function parseJump(row: LiveRace): Date | null {
  const dt = text(row.race_datetime);
  if (dt) {
    const parsed = new Date(dt.replace(" ", "T"));
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }

  const d = text(row.race_date);
  const t = text(row.race_time || row.jump_time);
  if (!d || !t) return null;

  const cleaned = t.toUpperCase().replace(/\s+/g, "");
  const parsed = new Date(`${d} ${cleaned}`);
  if (!Number.isNaN(parsed.getTime())) return parsed;

  const parsed2 = new Date(`${d}T${cleaned}`);
  if (!Number.isNaN(parsed2.getTime())) return parsed2;

  return null;
}

function minsToJump(row: LiveRace, now: Date): number | null {
  const jump = parseJump(row);
  if (!jump) return null;
  return Math.round((jump.getTime() - now.getTime()) / 60000);
}

function timeLabel(row: LiveRace): string {
  const raw = text(row.jump_time || row.race_time);
  if (raw) return raw.toUpperCase();
  const jump = parseJump(row);
  if (!jump) return "TIME TBC";
  return jump.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit" }).toUpperCase();
}

function statusClass(mins: number | null): string {
  if (mins === null) return "unknown";
  if (mins < -5) return "done";
  if (mins <= 0) return "jump";
  if (mins <= 10) return "hot";
  if (mins <= 30) return "soon";
  return "normal";
}

function minsLabel(mins: number | null): string {
  if (mins === null) return "TBC";
  if (mins < -5) return "DONE";
  if (mins <= 0) return "JUMP";

  if (mins >= 60) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }

  return `${mins}m`;
}

function selectRace(row: LiveRace): void {
  window.dispatchEvent(
    new CustomEvent("edgeiq-select-race", {
      detail: {
        raceDate: text(row.race_date),
        track: text(row.track),
        raceNo: text(row.race_no).replace(".0", ""),
      },
    })
  );
}

export default function LiveRaceControl() {
  const [rows, setRows] = useState<LiveRace[]>([]);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    let active = true;

    function load() {
      fetch("/data/live_race_control.csv", { cache: "no-store" })
        .then((r) => r.text())
        .then((csv) => {
          const parsed = Papa.parse<LiveRace>(csv, {
            header: true,
            skipEmptyLines: true,
          });

          if (active) setRows(parsed.data || []);
        })
        .catch(() => {
          if (active) setRows([]);
        });
    }

    load();
    const refresh = window.setInterval(load, 60000);
    const clock = window.setInterval(() => setNow(new Date()), 15000);

    return () => {
      active = false;
      window.clearInterval(refresh);
      window.clearInterval(clock);
    };
  }, []);

  const races = useMemo(() => {
    return rows
      .map((row) => {
        const mins = minsToJump(row, now);
        return { row, mins };
      })
      .filter((item) => item.mins === null || item.mins >= -5)
      .sort((a, b) => {
        const av = a.mins ?? 999999;
        const bv = b.mins ?? 999999;
        return av - bv;
      })
      .slice(0, 10);
  }, [rows, now]);

  return (
    <div className="edgeiq-countdown-banner">
      <div className="edgeiq-countdown-brand">EDGEiQ RACING</div>

      <div className="edgeiq-countdown-track">
        {races.length ? (
          races.map(({ row, mins }, i) => (
            <div
              key={`${text(row.race_date)}-${text(row.track)}-${text(row.race_no)}-${i}`}
              className={`edgeiq-countdown-item ${statusClass(mins)} ${i === 0 ? "next" : ""}`}
              title={`${text(row.race_date)} ${timeLabel(row)} ${text(row.track)} ${raceNo(row.race_no)}`}
              role="button"
              tabIndex={0}
              onClick={() => selectRace(row)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") selectRace(row);
              }}
            >
              <span className="meeting">{text(row.track)}</span>
              <span className="race">{raceNo(row.race_no)}</span>
              <span className="jump-time">{timeLabel(row)}</span>
              <strong>{minsLabel(mins)}</strong>
            </div>
          ))
        ) : (
          <div className="edgeiq-countdown-item unknown">
            <span className="meeting">NO RACES LOADED</span>
            <strong>TBC</strong>
          </div>
        )}
      </div>
    </div>
  );
}

