import React from "react";
import type { RatingDisplayRow } from "../App";

type Props = {
  runners: RatingDisplayRow[];
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

function todayTone(value: number | null, fieldTop: number | null): string {
  if (value === null || !Number.isFinite(value)) return "text-[#7f7f7f]";
  if (fieldTop === null || !Number.isFinite(fieldTop)) return "text-[#f0f0f0]";

  const diff = fieldTop - value;
  if (diff <= 0.35) return "text-[#63d57f]";
  if (diff <= 1.25) return "text-[#f0c15b]";
  return "text-[#e66b6b]";
}

export default function Worksheet({
  runners,
  selectedHorseKey,
  onSelectHorse,
}: Props): React.ReactElement {
  const sorted = [...runners].sort((a, b) => {
    if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
    if (a.horseNo !== null && b.horseNo !== null) return a.horseNo - b.horseNo;
    return a.horse.localeCompare(b.horse);
  });

  const fieldTop = Math.max(
    ...sorted
      .filter((r) => !r.isScratched && r.todayRating !== null)
      .map((r) => r.todayRating as number),
    0
  );

  return (
    <div className="rounded-md border border-[#2c2c2c] bg-[#171717] shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
      <div className="border-b border-[#2a2a2a] bg-[linear-gradient(180deg,#1d1d1d_0%,#181818_100%)] px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.20em] text-[#8d8d8d]">
              Worksheet
            </div>
            <div className="mt-1 text-[22px] font-semibold tracking-tight text-[#f3f3f3]">
              Race Worksheet
            </div>
          </div>

          <div className="rounded-sm border border-[#313131] bg-[#202020] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[#8a8a8a]">
              Rows
            </div>
            <div className="mt-1 text-[24px] font-semibold leading-none text-[#f5f5f5]">
              {sorted.length}
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1280px] w-full text-[12px] text-white">
          <thead>
            <tr className="border-b border-[#262626] bg-[#1a1a1a] text-left text-[10px] uppercase tracking-[0.14em] text-[#9d9d9d]">
              <th className="px-3 py-3">No</th>
              <th className="px-3 py-3">Horse</th>
              <th className="px-3 py-3">Bar</th>
              <th className="px-3 py-3">Jockey</th>
              <th className="px-3 py-3">Trainer</th>
              <th className="px-3 py-3 text-center">Today</th>
              <th className="px-3 py-3 text-center">EXP</th>
              <th className="px-3 py-3 text-center">Rated</th>
              <th className="px-3 py-3 text-center">Market</th>
              <th className="px-3 py-3 text-center">Rank</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((runner) => {
              const isSelected = selectedHorseKey === runner.horseKey;

              return (
                <tr
                  key={runner.id}
                  onClick={() => {
                    if (!runner.isScratched) onSelectHorse(runner.horseKey);
                  }}
                  className={[
                    "border-b border-[#1f1f1f] transition",
                    runner.isScratched ? "bg-[#231717]" : "bg-[#151515] hover:bg-[#1b1b1b]",
                    isSelected ? "outline outline-1 outline-[#7a6324]" : "",
                    runner.isScratched ? "" : "cursor-pointer",
                  ].join(" ")}
                >
                  <td className={`px-3 py-3 text-[12px] font-semibold ${runner.isScratched ? "text-[#cd7777]" : "text-[#f5f5f5]"}`}>
                    {runner.horseNo ?? "-"}
                  </td>

                  <td className="px-3 py-3">
                    <div className={`text-[13px] font-semibold leading-tight ${runner.isScratched ? "text-[#d78383]" : "text-[#f3f3f3]"}`}>
                      {runner.horse}
                    </div>
                    <div className={`mt-1 text-[10px] uppercase tracking-[0.12em] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#868686]"}`}>
                      {runner.isScratched ? "Scratched" : runner.raceClass || "Race"}
                    </div>
                  </td>

                  <td className={`px-3 py-3 text-[12px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#f0f0f0]"}`}>
                    {runner.barrier ?? "-"}
                  </td>

                  <td className={`px-3 py-3 text-[11px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.jockey || "-"}
                  </td>

                  <td className={`px-3 py-3 text-[11px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#d0d0d0]"}`}>
                    {runner.trainer || "-"}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] font-semibold ${runner.isScratched ? "text-[#b86b6b]" : todayTone(runner.todayRating, fieldTop)}`}>
                    {runner.isScratched ? "-" : fmt(runner.todayRating, 1)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#d7d7d7]"}`}>
                    {runner.isScratched ? "-" : fmt(runner.exp, 1)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] font-semibold ${runner.isScratched ? "text-[#b86b6b]" : "text-[#f5f5f5]"}`}>
                    {runner.isScratched ? "-" : fmtPrice(runner.ratedPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#c8c8c8]"}`}>
                    {runner.isScratched ? "-" : fmtPrice(runner.marketPrice)}
                  </td>

                  <td className={`px-3 py-3 text-center text-[12px] ${runner.isScratched ? "text-[#b86b6b]" : "text-[#9a9a9a]"}`}>
                    {runner.isScratched ? "-" : (runner.modelRank ?? "-")}
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

