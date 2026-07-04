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
  return value >= 100 ? value.toFixed(0) : value.toFixed(2);
}

function tileTone(value: number | null, benchmark: number | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "bg-[#232323] text-[#7f7f7f] border-[#343434]";
  }

  if (benchmark === null || benchmark === undefined || !Number.isFinite(benchmark)) {
    return "bg-[#2d2d2d] text-[#e7e7e7] border-[#444444]";
  }

  const diff = value - benchmark;

  if (diff >= 1.5) return "bg-[#166534] text-white border-[#1f8f4d]";
  if (diff >= -1.0) return "bg-[#a16207] text-white border-[#d3a11b]";
  return "bg-[#991b1b] text-white border-[#b93838]";
}

function ratingTile(value: number | null, benchmark: number | null, label: string): React.ReactElement {
  const tone = tileTone(value, benchmark);

  return (
    <div className={`relative flex h-[40px] w-[54px] items-center justify-center rounded-sm border text-[12px] font-semibold ${tone}`}>
      <span className="absolute left-1 top-0.5 text-[8px] uppercase tracking-[0.14em] text-white/70">
        {label}
      </span>
      <span className="mt-[8px] leading-none">{fmt(value, 1)}</span>
    </div>
  );
}

export default function RatingsTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
}: Props) {
  const sorted = [...runners].sort((a, b) => {
    const aScr = Number((a as any).is_scratched ?? 0) === 1 || (a as any).is_scratched === true;
    const bScr = Number((b as any).is_scratched ?? 0) === 1 || (b as any).is_scratched === true;

    if (aScr !== bScr) return aScr ? 1 : -1;
    if (a.modelRank !== null && b.modelRank !== null) return a.modelRank - b.modelRank;
    if (a.horseNo !== null && b.horseNo !== null) return a.horseNo - b.horseNo;
    return a.horse.localeCompare(b.horse);
  });

  const winningFigure =
    sorted.find((r) => r.winningFigure !== null)?.winningFigure ?? null;

  return (
    <div className="rounded-md border border-[#2b2b2b] bg-[#161616]">
      <div className="border-b border-[#2a2a2a] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#8d8d8d]">
              Ratings Grid
            </div>
            <div className="mt-1 text-[22px] font-semibold tracking-tight text-[#f2f2f2]">
              Race Ratings
            </div>
          </div>

          <div className="rounded-sm border border-[#303030] bg-[#202020] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[#8a8a8a]">
              Winning Figure
            </div>
            <div className="mt-1 text-[24px] font-semibold leading-none text-[#f4f4f4]">
              {fmt(winningFigure, 2)}
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1380px] w-full text-white text-[13px]">
          <thead>
            <tr className="border-b border-[#272727] bg-[#1b1b1b] text-left text-[11px] uppercase tracking-[0.12em] text-[#9e9e9e]">
              <th className="px-3 py-3">Horse</th>
              <th className="px-3 py-3">Jockey</th>
              <th className="px-3 py-3">Trainer</th>
              <th className="px-3 py-3">Bar</th>
              <th className="px-2 py-3">EXP</th>
              <th className="px-2 py-3">TODAY</th>
              <th className="px-2 py-3">LS1</th>
              <th className="px-2 py-3">LS2</th>
              <th className="px-2 py-3">LS3</th>
              <th className="px-2 py-3">LS4</th>
              <th className="px-2 py-3">LS5</th>
              <th className="px-3 py-3">Rated</th>
              <th className="px-3 py-3">Market</th>
              <th className="px-3 py-3">Rank</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((runner) => {
              const isScratched =
                Number((runner as any).is_scratched ?? 0) === 1 ||
                (runner as any).is_scratched === true;

              const isSelected = selectedHorseKey === runner.horseKey;

              return (
                <tr
                  key={runner.id}
                  onClick={() => !isScratched && onSelectHorse(runner.horseKey)}
                  className={[
                    "border-b border-[#202020] transition",
                    isScratched ? "bg-[#201616]" : "bg-[#161616] hover:bg-[#1d1d1d]",
                    isSelected ? "outline outline-1 outline-[#7c6320]" : "",
                    isScratched ? "" : "cursor-pointer",
                  ].join(" ")}
                >
                  <td className="px-3 py-3">
                    <div className="flex items-start gap-2">
                      <div className={`min-w-[24px] text-[13px] font-semibold ${isScratched ? "text-[#c96a6a]" : "text-[#f3f3f3]"}`}>
                        {runner.horseNo ?? "-"}
                      </div>
                      <div>
                        <div className={`text-[14px] font-medium leading-tight ${isScratched ? "text-[#d27b7b]" : "text-[#f3f3f3]"}`}>
                          {runner.horse}
                        </div>
                        <div className={`mt-1 text-[11px] ${isScratched ? "text-[#b46b6b]" : "text-[#8e8e8e]"}`}>
                          {isScratched ? "SCRATCHED" : runner.raceClass || ""}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className={`px-3 py-3 text-[12px] ${isScratched ? "text-[#b46b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.jockey || "-"}
                  </td>

                  <td className={`px-3 py-3 text-[12px] ${isScratched ? "text-[#b46b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.trainer || "-"}
                  </td>

                  <td className={`px-3 py-3 text-center ${isScratched ? "text-[#b46b6b]" : "text-[#f0f0f0]"}`}>
                    {runner.barrier ?? "-"}
                  </td>

                  <td className="px-2 py-2">{ratingTile(runner.last5?.peak ?? null, winningFigure, "EXP")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.todayRating ?? null, winningFigure, "TODAY")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.last5?.ls1 ?? null, winningFigure, "LS1")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.last5?.ls2 ?? null, winningFigure, "LS2")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.last5?.ls3 ?? null, winningFigure, "LS3")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.last5?.ls4 ?? null, winningFigure, "LS4")}</td>
                  <td className="px-2 py-2">{ratingTile(runner.last5?.ls5 ?? null, winningFigure, "LS5")}</td>

                  <td className={`px-3 py-3 text-center font-semibold ${isScratched ? "text-[#b46b6b]" : "text-[#f2f2f2]"}`}>
                    {isScratched ? "-" : fmtPrice(runner.ratedPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center ${isScratched ? "text-[#b46b6b]" : "text-[#c6c6c6]"}`}>
                    {isScratched ? "-" : fmtPrice(runner.marketPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center ${isScratched ? "text-[#b46b6b]" : "text-[#9e9e9e]"}`}>
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

