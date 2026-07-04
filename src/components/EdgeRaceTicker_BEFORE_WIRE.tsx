import { useEffect, useMemo, useState } from "react";

type Row = Record<string, string>;

type RaceItem = {
  raceDate: string;
  track: string;
  raceNo: number;
  raceTime: string;
  label: string;
  sortTime: number;
};

function clean(v: unknown): string {
  return String(v ?? "").trim();
}

function num(v: unknown): number {
  const n = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function parseCsv(text: string): Row[] {
  const lines = text.replace(/\r/g, "").split("\n").filter(Boolean);
  if (!lines.length) return [];

  const headers = lines[0].split(",").map((h) => h.trim());

  return lines.slice(1).map((line) => {
    const cells: string[] = [];
    let cur = "";
    let quote = false;

    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') quote = !quote;
      else if (ch === "," && !quote) {
        cells.push(cur);
        cur = "";
      } else cur += ch;
    }

    cells.push(cur);

    const row: Row = {};
    headers.forEach((h, i) => {
      row[h] = cells[i] ?? "";
    });
    return row;
  });
}

function parseDateTime(raceDate: string, raceTime: string): number {
  const d = clean(raceDate);
  const t = clean(raceTime);

  if (!d || !t) return 0;

  const raw = `${d} ${t}`;
  const parsed = Date.parse(raw);

  if (Number.isFinite(parsed)) return parsed;

  const m = t.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
  if (!m) return 0;

  let hh = Number(m[1]);
  const mm = Number(m[2]);
  const ap = (m[3] || "").toUpperCase();

  if (ap === "PM" && hh < 12) hh += 12;
  if (ap === "AM" && hh === 12) hh = 0;

  const dt = new Date(`${d}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return 0;

  dt.setHours(hh, mm, 0, 0);
  return dt.getTime();
}

function timeLeft(ts: number, now: number): string {
  if (!ts) return "--";
  const diff = ts - now;

  if (diff <= 0) return "LIVE";

  const mins = Math.floor(diff / 60000);
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;

  if (hrs > 0) return `${hrs}h ${rem}m`;
  return `${mins}m`;
}

export default function EdgeRaceTicker() {
  const [rows, setRows] = useState<Row[]>([]);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    let alive = true;

    fetch("/data/race_fields.csv", { cache: "no-store" })
      .then((r) => r.text())
      .then((t) => {
        if (alive) setRows(parseCsv(t));
      })
      .catch(() => {});

    const timer = window.setInterval(() => setNow(Date.now()), 30000);

    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const races = useMemo<RaceItem[]>(() => {
    const map = new Map<string, RaceItem>();

    rows.forEach((r) => {
      const raceDate = clean(r.race_date || r.raceDate || r.date);
      const track = clean(r.track || r.meeting || r.venue).toUpperCase();
      const raceNo = num(r.race_no || r.raceNo || r.race);
      const raceTime = clean(r.race_time || r.raceTime || r.time);

      if (!raceDate || !track || !raceNo) return;

      const key = `${raceDate}|${track}|${raceNo}`;

      if (!map.has(key)) {
        const sortTime = parseDateTime(raceDate, raceTime);
        map.set(key, {
          raceDate,
          track,
          raceNo,
          raceTime,
          sortTime,
          label: `${track} R${raceNo}`,
        });
      }
    });

    return Array.from(map.values())
      .sort((a, b) => (a.sortTime || 9999999999999) - (b.sortTime || 9999999999999))
      .slice(0, 18);
  }, [rows]);

  function selectRace(r: RaceItem) {
    window.dispatchEvent(
      new CustomEvent("edgeiq-select-race", {
        detail: {
          raceDate: r.raceDate,
          track: r.track,
          raceNo: String(r.raceNo),
        },
      })
    );
  }

  if (!races.length) return null;

  return (
    <div className="edgeiq-ticker-shell">
      <div className="edgeiq-ticker-brand">EDGEiQ RACING</div>

      <div className="edgeiq-ticker-track">
        {races.map((r) => {
          const left = timeLeft(r.sortTime, now);
          const live = left === "LIVE";

          return (
            <button
              key={`${r.raceDate}-${r.track}-${r.raceNo}`}
              className={`edgeiq-ticker-chip ${live ? "is-live" : ""}`}
              onClick={() => selectRace(r)}
              type="button"
            >
              <span className="ticker-main">{r.label}</span>
              <span className="ticker-date">{r.raceDate}</span>
              <span className="ticker-time">{r.raceTime || "TBC"}</span>
              <strong>{left}</strong>
            </button>
          );
        })}
      </div>
    </div>
  );
}
