import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type GearRow = Record<string, string>;

type Props = {
  raceDate?: string;
  track?: string;
  raceNo?: number | string;
};

const SOURCES = [
  "/data/gear_changes.csv",
  "/data/gear_changes_today.csv",
  "/data/race_gear_changes.csv",
  "/data/gear_changes_report.csv",
];

function clean(v: unknown): string {
  return String(v ?? "").trim();
}

function norm(v: unknown): string {
  return clean(v).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export default function GearTab({ raceDate, track, raceNo }: Props): React.ReactElement {
  const [rows, setRows] = useState<GearRow[]>([]);

  useEffect(() => {
    let alive = true;

    async function load() {
      for (const src of SOURCES) {
        try {
          const res = await fetch(src, { cache: "no-store" });
          if (!res.ok) continue;
          const txt = await res.text();
          const parsed = Papa.parse<GearRow>(txt, { header: true, skipEmptyLines: true });
          if (alive && parsed.data.length) {
            setRows(parsed.data);
            return;
          }
        } catch {
          // try next source
        }
      }
      if (alive) setRows([]);
    }

    void load();
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const rd = clean(raceDate);
    const tr = norm(track);
    const rn = clean(raceNo);

    return rows.filter((r) => {
      const rowDate = clean(r.race_date || r.date);
      const rowTrack = norm(r.track || r.meeting);
      const rowRace = clean(r.race_no || r.race_number || r.race);

      if (rd && rowDate && rowDate !== rd) return false;
      if (tr && rowTrack && rowTrack !== tr) return false;
      if (rn && rowRace && rowRace !== rn) return false;
      return true;
    });
  }, [rows, raceDate, track, raceNo]);

  return (
    <section className="edgeiq-gear-tab">
      <div className="edgeiq-ws-card">
        <div className="edgeiq-ws-head">
          <div>
            <div className="edgeiq-ws-kicker">EDGEiQ RACING</div>
            <div className="edgeiq-ws-title">Gear Changes</div>
          </div>
          <div className="edgeiq-ws-head-right">
            {clean(track)} R{clean(raceNo)}
          </div>
        </div>

        <div className="edgeiq-ws-table-wrap">
          <table className="edgeiq-ws-table">
            <thead>
              <tr>
                <th>Horse</th>
                <th>Gear Change</th>
                <th>Race</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={i}>
                  <td>{clean(r.horse || r.runner || r.horse_name) || "-"}</td>
                  <td>{clean(r.gear_change || r.gear_changes || r.gear || r.change) || "-"}</td>
                  <td>{clean(r.track || track)} R{clean(r.race_no || r.race_number || raceNo)}</td>
                  <td>{clean(r.source || r.source_url || r.scraped_from) || "-"}</td>
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty">
                    NO GEAR CHANGES LISTED FOR THIS RACE
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

