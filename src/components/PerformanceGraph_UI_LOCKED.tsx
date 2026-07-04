import React, { useMemo, useState } from "react";
import { getLineColour } from "../utils/chartColours";

type FormRun = {
  runDate: string;
  runRating: number | null;
  isOfficialRace: boolean;
};

type Runner = {
  horse: string;
  horseKey: string;
  horseNo: number | null;
  todayRating: number | null;
  winningFigure: number | null;
  matchedRuns: FormRun[];
};

type Props = {
  runners: Runner[];
};

type SeriesRow = {
  horse: string;
  horseKey: string;
  horseNo: number | null;
  todayRating: number | null;
  winningFigure: number | null;
  values: number[];
};

function officialRatedRuns(runs: FormRun[]): number[] {
  return [...runs]
    .filter((r) => r.isOfficialRace && r.runRating !== null)
    .sort((a, b) => a.runDate.localeCompare(b.runDate))
    .map((r) => r.runRating as number)
    .slice(-10);
}

function linePath(values: number[], minY: number, maxY: number, width: number, height: number): string {
  if (!values.length) return "";
  const range = Math.max(1, maxY - minY);

  return values
    .map((v, i) => {
      const x = values.length === 1 ? width / 2 : (i / (values.length - 1)) * width;
      const y = height - ((v - minY) / range) * height;
      return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function pointX(index: number, count: number, width: number): number {
  return count <= 1 ? width / 2 : (index / (count - 1)) * width;
}

function pointY(value: number, minY: number, maxY: number, height: number): number {
  const range = Math.max(1, maxY - minY);
  return height - ((value - minY) / range) * height;
}

export default function PerformanceGraph({ runners }: Props) {
  const [activeHorseKey, setActiveHorseKey] = useState<string | null>(null);

  const series = useMemo<SeriesRow[]>(() => {
    return [...runners]
      .sort((a, b) => (a.horseNo ?? 999) - (b.horseNo ?? 999))
      .map((runner) => ({
        horse: runner.horse,
        horseKey: runner.horseKey,
        horseNo: runner.horseNo,
        todayRating: runner.todayRating,
        winningFigure: runner.winningFigure,
        values: officialRatedRuns(runner.matchedRuns),
      }));
  }, [runners]);

  const rankedHorseKeys = useMemo(() => {
    return [...series]
      .filter((s) => s.todayRating !== null)
      .sort((a, b) => (b.todayRating ?? 0) - (a.todayRating ?? 0))
      .map((s) => s.horseKey);
  }, [series]);

  function getRank(horseKey: string): number {
    const idx = rankedHorseKeys.indexOf(horseKey);
    return idx === -1 ? 999 : idx + 1;
  }

  const allValues = series.flatMap((s) => s.values);
  const allWinning = series
    .map((s) => s.winningFigure)
    .filter((v): v is number => v !== null && Number.isFinite(v));

  const minY =
    allValues.length || allWinning.length
      ? Math.min(...allValues, ...allWinning) - 2
      : 0;

  const maxY =
    allValues.length || allWinning.length
      ? Math.max(...allValues, ...allWinning) + 2
      : 100;

  const width = 1100;
  const height = 360;
  const winningFigure = series[0]?.winningFigure ?? null;
  const winY =
    winningFigure !== null ? pointY(winningFigure, minY, maxY, height) : null;

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <div className="text-lg font-bold text-white">Performance</div>
          <div className="mt-1 text-sm text-slate-400">
            Cleaner race chart. Hover a runner tile below to isolate its line.
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
          Win Fig {winningFigure !== null ? winningFigure.toFixed(2) : "-"}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <div className="overflow-x-auto">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[1100px] h-[390px]">
            <rect x="0" y="0" width={width} height={height} rx="16" fill="#020617" />

            {[0, 0.25, 0.5, 0.75, 1].map((p) => {
              const y = (height * p).toFixed(1);
              return (
                <line
                  key={p}
                  x1="40"
                  x2={width - 40}
                  y1={y}
                  y2={y}
                  stroke="#1e293b"
                  strokeWidth="1"
                />
              );
            })}

            {winY !== null && Number.isFinite(winY) && (
              <line
                x1="40"
                x2={width - 40}
                y1={winY.toFixed(1)}
                y2={winY.toFixed(1)}
                stroke="#f59e0b"
                strokeWidth="2"
                strokeDasharray="8 6"
              />
            )}

            {series.map((runner, idx) => {
              const rank = getRank(runner.horseKey);
              const isTop = rank <= 4;
              const isMid = rank <= 8;
              const isActive = activeHorseKey === runner.horseKey;
              const anyActive = activeHorseKey !== null;

              let opacity = 0.08;
              if (isTop) opacity = 0.95;
              else if (isMid) opacity = 0.45;
              else opacity = 0.14;

              if (anyActive) {
                opacity = isActive ? 1 : 0.06;
              }

              const path = linePath(runner.values, minY, maxY, width - 80, height - 20);

              return (
                <g key={runner.horseKey} opacity={opacity} transform="translate(40,10)">
                  {path && (
                    <path
                      d={path}
                      fill="none"
                      stroke={getLineColour(idx)}
                      strokeWidth={isActive ? 5 : isTop ? 3.6 : isMid ? 2.2 : 1.2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}

                  {runner.values.map((value, pointIdx) => {
                    const x = pointX(pointIdx, runner.values.length, width - 80);
                    const y = pointY(value, minY, maxY, height - 20);
                    return (
                      <circle
                        key={`${runner.horseKey}-${pointIdx}`}
                        cx={x.toFixed(1)}
                        cy={y.toFixed(1)}
                        r={isActive ? "4.8" : isTop ? "3.6" : "2.6"}
                        fill="#ffffff"
                      />
                    );
                  })}
                </g>
              );
            })}
          </svg>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4">
          {series.map((runner, idx) => {
            const active = activeHorseKey === runner.horseKey;
            const rank = getRank(runner.horseKey);
            const borderColour = getLineColour(idx);

            return (
              <button
                key={runner.horseKey}
                type="button"
                onMouseEnter={() => setActiveHorseKey(runner.horseKey)}
                onMouseLeave={() => setActiveHorseKey(null)}
                onClick={() => setActiveHorseKey(active ? null : runner.horseKey)}
                className={`rounded-2xl border bg-slate-900 px-3 py-3 text-left transition ${
                  active
                    ? "bg-slate-800"
                    : "border-slate-800 hover:bg-slate-800"
                }`}
                style={{ borderColor: active ? borderColour : undefined }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold text-white">{runner.horse}</div>
                  <div
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: getLineColour(idx) }}
                  />
                </div>

                <div className="mt-1 text-xs text-slate-400">
                  Today {runner.todayRating !== null ? runner.todayRating.toFixed(2) : "-"}  Win Fig{" "}
                  {runner.winningFigure !== null ? runner.winningFigure.toFixed(2) : "-"}
                </div>

                <div className="mt-1 text-xs text-slate-500">
                  Rank {rank}  {runner.values.length} official run(s)
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

