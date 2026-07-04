import React from "react";
import type { WorksheetRunner } from "../App";

type Props = {
  runners: WorksheetRunner[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
};

function fmt(value: number | null, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return value.toFixed(digits);
}

function fmtPrice(value: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  if (value >= 100) return value.toFixed(0);
  return value.toFixed(2).replace(/\.00$/, "");
}

function tileTone(value: number | null, benchmark: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "bg-[#242424] text-[#7f7f7f] border-[#343434]";
  }

  if (benchmark === null || benchmark === undefined || !Number.isFinite(benchmark)) {
    return "bg-[#2a2a2a] text-[#ececec] border-[#3c3c3c]";
  }

  const diff = value - benchmark;

  if (diff >= 1.5) return "bg-[#37924f] text-white border-[#4ebd6c]";
  if (diff >= -1.0) return "bg-[#b7841b] text-white border-[#dca632]";
  return "bg-[#a42b2b] text-white border-[#ca4a4a]";
}

function metricTile(
  value: number | null,
  benchmark: number | null,
  label: string,
  emphasis: "today" | "exp" | "ls" = "ls"
): React.ReactElement {
  const tone = tileTone(value, benchmark);
  const sizeClass =
    emphasis === "today"
      ? "h-[42px] w-[56px] text-[12px]"
      : emphasis === "exp"
      ? "h-[40px] w-[54px] text-[11px]"
      : "h-[38px] w-[50px] text-[11px]";

  return (
    <div
      className={[
        "relative flex items-center justify-center rounded-sm border font-semibold",
        "shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]",
        sizeClass,
        tone,
      ].join(" ")}
    >
      <span className="absolute left-1 top-[2px] text-[7px] uppercase tracking-[0.14em] text-white/70">
        {label}
      </span>
      <span className="mt-[9px] leading-none">{fmt(value, 1)}</span>
    </div>
  );
}

export default function RatingsTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
}: Props): React.ReactElement {
  const sorted = [...runners].sort((a, b) => {
    const aScr =
      Number((a as unknown as { is_scratched?: number | boolean }).is_scratched ?? 0) === 1 ||
      (a as unknown as { is_scratched?: number | boolean }).is_scratched === true;
    const bScr =
      Number((b as unknown as { is_scratched?: number | boolean }).is_scratched ?? 0) === 1 ||
      (b as unknown as { is_scratched?: number | boolean }).is_scratched === true;

    if (aScr !== bScr) return aScr ? 1 : -1;
    if (a.modelRank !== null && b.modelRank !== null) return a.modelRank - b.modelRank;
    if (a.horseNo !== null && b.horseNo !== null) return a.horseNo - b.horseNo;
    return a.horse.localeCompare(b.horse);
  });

  const winningFigure =
    sorted.find((r) => r.winningFigure !== null)?.winningFigure ?? null;

  const topRated =
    sorted.find((r) => !(Number((r as unknown as { is_scratched?: number | boolean }).is_scratched ?? 0) === 1 || (r as unknown as { is_scratched?: number | boolean }).is_scratched === true) && r.modelRank === 1) ??
    sorted.find((r) => !(Number((r as unknown as { is_scratched?: number | boolean }).is_scratched ?? 0) === 1 || (r as unknown as { is_scratched?: number | boolean }).is_scratched === true)) ??
    null;

  return (
    <div className="rounded-md border border-[#2c2c2c] bg-[#171717] shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
      <div className="border-b border-[#2a2a2a] bg-[linear-gradient(180deg,#1d1d1d_0%,#181818_100%)] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.20em] text-[#8d8d8d]">
              Ratings Grid
            </div>
            <div className="mt-1 text-[22px] font-semibold tracking-tight text-[#f3f3f3]">
              Race Ratings
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-[120px] rounded-sm border border-[#313131] bg-[#202020] px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.14em] text-[#8a8a8a]">
                Winning Figure
              </div>
              <div className="mt-1 text-[24px] font-semibold leading-none text-[#f5f5f5]">
                {fmt(winningFigure, 2)}
              </div>
            </div>

            <div className="min-w-[170px] rounded-sm border border-[#313131] bg-[#202020] px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.14em] text-[#8a8a8a]">
                Top Rated
              </div>
              <div className="mt-1 text-[16px] font-semibold leading-none text-[#f5f5f5]">
                {topRated?.horse ?? "-"}
              </div>
              <div className="mt-1 text-[11px] text-[#b9b9b9]">
                Rated {fmtPrice(topRated?.ratedPrice ?? null)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="border-b border-[#252525] bg-[#141414] px-4 py-2">
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#b5b5b5]">
          <span>
            <span className="uppercase tracking-[0.12em] text-[#7f7f7f]">Lead Speed</span>
            <span className="ml-1 text-[#f0f0f0]">Live</span>
          </span>
          <span>
            <span className="uppercase tracking-[0.12em] text-[#7f7f7f]">Class Rank</span>
            <span className="ml-1 text-[#f0f0f0]">Today</span>
          </span>
          <span>
            <span className="uppercase tracking-[0.12em] text-[#7f7f7f]">Time Rank</span>
            <span className="ml-1 text-[#f0f0f0]">Live Grid</span>
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1480px] w-full text-[12px] text-white">
          <thead>
            <tr className="border-b border-[#262626] bg-[#1a1a1a] text-left text-[10px] uppercase tracking-[0.14em] text-[#9d9d9d]">
              <th className="px-3 py-3">Horse</th>
              <th className="px-3 py-3">Jockey</th>
              <th className="px-3 py-3">Trainer</th>
              <th className="px-3 py-3 text-center">Bar</th>
              <th className="px-1 py-3">EXP</th>
              <th className="px-1 py-3">TODAY</th>
              <th className="px-1 py-3">LS1</th>
              <th className="px-1 py-3">LS2</th>
              <th className="px-1 py-3">LS3</th>
              <th className="px-1 py-3">LS4</th>
              <th className="px-1 py-3">LS5</th>
              <th className="px-3 py-3 text-center">Rated</th>
              <th className="px-3 py-3 text-center">Market</th>
              <th className="px-3 py-3 text-center">Rank</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((runner) => {
              const isScratched =
                Number((runner as unknown as { is_scratched?: number | boolean }).is_scratched ?? 0) === 1 ||
                (runner as unknown as { is_scratched?: number | boolean }).is_scratched === true;

              const isSelected = selectedHorseKey === runner.horseKey;

              return (
                <tr
                  key={runner.id}
                  onClick={() => {
                    if (!isScratched) onSelectHorse(runner.horseKey);
                  }}
                  className={[
                    "border-b border-[#1f1f1f] transition",
                    isScratched ? "bg-[#231717]" : "bg-[#151515] hover:bg-[#1b1b1b]",
                    isSelected ? "outline outline-1 outline-[#7a6324]" : "",
                    isScratched ? "" : "cursor-pointer",
                  ].join(" ")}
                >
                  <td className="px-3 py-3">
                    <div className="flex items-start gap-3">
                      <div className={`min-w-[14px] text-[12px] font-semibold ${isScratched ? "text-[#cd7777]" : "text-[#f5f5f5]"}`}>
                        {runner.horseNo ?? "-"}
                      </div>
                      <div>
                        <div className={`text-[13px] font-semibold leading-tight ${isScratched ? "text-[#d78383]" : "text-[#f3f3f3]"}`}>
                          {runner.horse}
                        </div>
                        <div className={`mt-1 text-[10px] uppercase tracking-[0.12em] ${isScratched ? "text-[#b86b6b]" : "text-[#868686]"}`}>
                          {isScratched ? "Scratched" : runner.raceClass || "Race"}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className={`px-3 py-3 text-[11px] ${isScratched ? "text-[#b86b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.jockey || "-"}
                  </td>

                  <td className={`px-3 py-3 text-[11px] ${isScratched ? "text-[#b86b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.trainer || "-"}
                  </td>

                  <td className={`px-3 py-3 text-center text-[11px] ${isScratched ? "text-[#b86b6b]" : "text-[#f0f0f0]"}`}>
                    {runner.barrier ?? "-"}
                  </td>

                  <td className="px-1 py-2">{metricTile(runner.last5?.peak ?? null, winningFigure, "EXP", "exp")}</td>
                  <td className="px-1 py-2">{metricTile(runner.todayRating ?? null, winningFigure, "TODAY", "today")}</td>
                  <td className="px-1 py-2">{metricTile(runner.last5?.ls1 ?? null, winningFigure, "LS1", "ls")}</td>
                  <td className="px-1 py-2">{metricTile(runner.last5?.ls2 ?? null, winningFigure, "LS2", "ls")}</td>
                  <td className="px-1 py-2">{metricTile(runner.last5?.ls3 ?? null, winningFigure, "LS3", "ls")}</td>
                  <td className="px-1 py-2">{metricTile(runner.last5?.ls4 ?? null, winningFigure, "LS4", "ls")}</td>
                  <td className="px-1 py-2">{metricTile(runner.last5?.ls5 ?? null, winningFigure, "LS5", "ls")}</td>

                  <td className={`px-3 py-3 text-center text-[12px] font-semibold ${isScratched ? "text-[#b86b6b]" : "text-[#f5f5f5]"}`}>
                    {isScratched ? "-" : fmtPrice(runner.ratedPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] ${isScratched ? "text-[#b86b6b]" : "text-[#c8c8c8]"}`}>
                    {isScratched ? "-" : fmtPrice(runner.marketPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] ${isScratched ? "text-[#b86b6b]" : "text-[#9a9a9a]"}`}>
                    {isScratched ? "-" : (runner.modelRank ?? "-")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}


