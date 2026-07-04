import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type RunRow = Record<string, unknown>;

function cleanText(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  return text.toLowerCase() === "nan" ? "" : text;
}

function cleanUpper(value: unknown): string {
  return cleanText(value).toUpperCase();
}

function cleanHorseKey(value: unknown): string {
  return cleanUpper(value).replace(/[^A-Z0-9]/g, "");
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text || text === "-" || text === "" || text.toUpperCase() === "NAN") return null;
  const cleaned = text.replace(/[$,%]/g, "").replace(/,/g, "");
  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}

function format1(value: number | null): string {
  return value === null ? "" : value.toFixed(1);
}

function parseFinishPos(value: unknown): number | null {
  const text = cleanText(value);
  const match = text.match(/^(\d+)/);
  return match ? Number(match[1]) : null;
}

function simplifyGoing(value: string): string {
  const v = cleanUpper(value);
  if (v.startsWith("FIRM")) return "Firm";
  if (v.startsWith("GOOD")) return "Good";
  if (v.startsWith("SOFT")) return "Soft";
  if (v.startsWith("HEAVY")) return "Heavy";
  if (v.includes("SYN")) return "Synthetic";
  return "Other";
}

type Props = {
  horse: string;
  horseKey: string;
  raceClass: string;
  trackCondition: string;
};

export default function FormGuide({ horse, horseKey, raceClass, trackCondition }: Props) {
  const [rows, setRows] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    Papa.parse("/data/form_card_runs.csv", {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        if (cancelled) return;
        setRows((result.data as RunRow[]) || []);
        setLoading(false);
      },
      error: () => {
        if (cancelled) return;
        setRows([]);
        setLoading(false);
      },
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const horseRuns = useMemo(() => {
    const target = cleanHorseKey(horseKey || horse);

    return rows
      .filter((r) => cleanHorseKey(r.horse_key || r.horse) === target)
      .map((r) => ({
        horse: cleanText(r.horse),
        runDate: cleanText(r.run_date).slice(0, 10),
        track: cleanText(r.track),
        distance: toNumber(r.distance),
        className: cleanText(r.race_class),
        condition: cleanText(r.track_condition),
        finishPosText: cleanText(r.finish_pos),
        finishPosNum: parseFinishPos(r.finish_pos),
        margin: cleanText(r.margin),
        spText: cleanText(r.sp_text || r.sp),
        runRating: toNumber(r.run_rating),
        runType: cleanText(r.run_type),
      }))
      .sort((a, b) => b.runDate.localeCompare(a.runDate));
  }, [rows, horse, horseKey]);

  const officialRuns = useMemo(
    () => horseRuns.filter((r) => cleanUpper(r.runType) === "RACE"),
    [horseRuns]
  );

  const stats = useMemo(() => {
    const starts = officialRuns.length;
    const wins = officialRuns.filter((r) => r.finishPosNum === 1).length;
    const seconds = officialRuns.filter((r) => r.finishPosNum === 2).length;
    const thirds = officialRuns.filter((r) => r.finishPosNum === 3).length;

    const firstUpRuns = officialRuns.slice(0, 1);
    const secondUpRuns = officialRuns.slice(1, 2);

    const firstUpStats = {
      starts: firstUpRuns.length,
      wins: firstUpRuns.filter((r) => r.finishPosNum === 1).length,
      seconds: firstUpRuns.filter((r) => r.finishPosNum === 2).length,
      thirds: firstUpRuns.filter((r) => r.finishPosNum === 3).length,
    };

    const secondUpStats = {
      starts: secondUpRuns.length,
      wins: secondUpRuns.filter((r) => r.finishPosNum === 1).length,
      seconds: secondUpRuns.filter((r) => r.finishPosNum === 2).length,
      thirds: secondUpRuns.filter((r) => r.finishPosNum === 3).length,
    };

    function blockText(runs: typeof officialRuns) {
      const s = runs.length;
      const w = runs.filter((r) => r.finishPosNum === 1).length;
      const p2 = runs.filter((r) => r.finishPosNum === 2).length;
      const p3 = runs.filter((r) => r.finishPosNum === 3).length;
      return `${s}:${w}-${p2}-${p3}`;
    }

    const currentTrackName = cleanUpper(officialRuns[0]?.track || "");
    const currentDistanceValue = officialRuns[0]?.distance ?? null;

    const currentTrack = officialRuns.filter((r) => cleanUpper(r.track) === currentTrackName);
    const currentDistance = officialRuns.filter((r) => r.distance === currentDistanceValue);
    const currentTrackDistance = officialRuns.filter(
      (r) => cleanUpper(r.track) === currentTrackName && r.distance === currentDistanceValue
    );

    const goingBuckets = {
      Firm: officialRuns.filter((r) => simplifyGoing(r.condition) === "Firm"),
      Good: officialRuns.filter((r) => simplifyGoing(r.condition) === "Good"),
      Soft: officialRuns.filter((r) => simplifyGoing(r.condition) === "Soft"),
      Heavy: officialRuns.filter((r) => simplifyGoing(r.condition) === "Heavy"),
      Synthetic: officialRuns.filter((r) => simplifyGoing(r.condition) === "Synthetic"),
    };

    const winsByDistance = officialRuns
      .filter((r) => r.finishPosNum === 1 && r.distance !== null)
      .reduce<Record<string, number>>((acc, run) => {
        const key = String(Math.round(run.distance || 0));
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {});

    const distanceWinsText = Object.entries(winsByDistance)
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .map(([dist, count]) => `${dist} (${count})`)
      .join(", ");

    return {
      recordText: `${starts}:${wins}-${seconds}-${thirds}`,
      firstUpText: `${firstUpStats.starts}:${firstUpStats.wins}-${firstUpStats.seconds}-${firstUpStats.thirds}`,
      secondUpText: `${secondUpStats.starts}:${secondUpStats.wins}-${secondUpStats.seconds}-${secondUpStats.thirds}`,
      trackText: blockText(currentTrack),
      distanceText: blockText(currentDistance),
      trackDistanceText: blockText(currentTrackDistance),
      distanceWinsText: distanceWinsText || "",
      going: {
        Firm: blockText(goingBuckets.Firm),
        Good: blockText(goingBuckets.Good),
        Soft: blockText(goingBuckets.Soft),
        Heavy: blockText(goingBuckets.Heavy),
        Synthetic: blockText(goingBuckets.Synthetic),
      },
    };
  }, [officialRuns]);

  if (loading) {
    return (
      <div className="rounded-[26px] border border-[#1d2a4c] bg-[linear-gradient(120deg,rgba(14,22,48,0.96),rgba(4,8,20,0.98))] p-5 text-slate-300">
        Loading form guide...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[26px] border border-[#1d2a4c] bg-[linear-gradient(120deg,rgba(15,23,52,0.9),rgba(2,6,17,0.95))] p-5">
        <div className="text-[12px] font-semibold uppercase tracking-[0.2em] text-sky-300/80">
          Form Guide
        </div>
        <div className="mt-3 text-3xl font-black">{horse}</div>
        <div className="mt-4 flex flex-wrap gap-3">
          <div className="rounded-full border border-white/10 bg-[#07101d]/[0.05] px-4 py-2 text-sm font-semibold">
            Class: {raceClass || "Unknown"}
          </div>
          <div className="rounded-full border border-white/10 bg-[#07101d]/[0.05] px-4 py-2 text-sm font-semibold">
            Condition: {trackCondition || "Unknown"}
          </div>
          <div className="rounded-full border border-white/10 bg-[#07101d]/[0.05] px-4 py-2 text-sm font-semibold">
            Career Runs: {officialRuns.length}
          </div>
        </div>
      </section>

      <section className="rounded-[26px] border border-[#1d2a4c] bg-[linear-gradient(120deg,rgba(14,22,48,0.96),rgba(4,8,20,0.98))] p-5">
        <div className="text-[12px] font-semibold uppercase tracking-[0.2em] text-sky-300/80">
          Horse Stats
        </div>

        <div className="mt-4 space-y-3 text-sm text-slate-200">
          <div>
            <span className="font-bold">Record:</span> {stats.recordText}
            <span className="ml-6 font-bold">1st Up:</span> {stats.firstUpText}
            <span className="ml-6 font-bold">2nd Up:</span> {stats.secondUpText}
          </div>

          <div>
            <span className="font-bold">Track:</span> {stats.trackText}
            <span className="ml-6 font-bold">Dist:</span> {stats.distanceText}
            <span className="ml-6 font-bold">Track/Dist:</span> {stats.trackDistanceText}
            <span className="ml-6 font-bold">Distance(s) Won:</span> {stats.distanceWinsText}
          </div>

          <div>
            <span className="font-bold">Firm:</span> {stats.going.Firm}
            <span className="ml-6 font-bold">Good:</span> {stats.going.Good}
            <span className="ml-6 font-bold">Soft:</span> {stats.going.Soft}
            <span className="ml-6 font-bold">Heavy:</span> {stats.going.Heavy}
            <span className="ml-6 font-bold">Synthetic:</span> {stats.going.Synthetic}
          </div>
        </div>
      </section>

      <section className="rounded-[26px] border border-[#1d2a4c] bg-[linear-gradient(120deg,rgba(14,22,48,0.96),rgba(4,8,20,0.98))] p-5">
        <div className="mb-3 text-[12px] font-semibold uppercase tracking-[0.2em] text-sky-300/80">
          Full Career Form
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-[0.18em] text-slate-400">
                <th className="px-2 py-2">Date</th>
                <th className="px-2 py-2">Track</th>
                <th className="px-2 py-2">Dist</th>
                <th className="px-2 py-2">Class</th>
                <th className="px-2 py-2">Cond</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Fin</th>
                <th className="px-2 py-2">Margin</th>
                <th className="px-2 py-2">SP</th>
                <th className="px-2 py-2">Rating</th>
              </tr>
            </thead>
            <tbody>
              {horseRuns.map((run, index) => (
                <tr key={`${run.runDate}__${index}`} className="border-t border-white/5">
                  <td className="px-2 py-2">{run.runDate || ""}</td>
                  <td className="px-2 py-2">{run.track || ""}</td>
                  <td className="px-2 py-2">{run.distance ?? ""}</td>
                  <td className="px-2 py-2">{run.className || ""}</td>
                  <td className="px-2 py-2">{run.condition || ""}</td>
                  <td className="px-2 py-2">{run.runType || ""}</td>
                  <td className="px-2 py-2">{run.finishPosText || ""}</td>
                  <td className="px-2 py-2">{run.margin || ""}</td>
                  <td className="px-2 py-2">{run.spText || ""}</td>
                  <td className="px-2 py-2">{format1(run.runRating)}</td>
                </tr>
              ))}

              {!horseRuns.length && (
                <tr>
                  <td colSpan={10} className="px-2 py-6 text-slate-400">
                    No form found for this horse.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}


