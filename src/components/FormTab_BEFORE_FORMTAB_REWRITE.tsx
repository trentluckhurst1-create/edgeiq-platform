import React, { useMemo } from "react";

type FormRun = {
  runDate: string;
  runType: string;
  track: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
  finishPos: string;
  margin: string;
  jockey: string;
  trainer: string;
  barrier: number | null;
  sp: string;
  runRating: number | null;
  pos800: number | null;
  pos400: number | null;
  isOfficialRace: boolean;
};

type Runner = {
  horse: string;
  horseKey: string;
  horseNo: number | null;
  barrier: number | null;
  jockey: string;
  trainer: string;
};

type Props = {
  runners: Runner[];
  selectedHorseKey?: string;
  onSelectHorse?: (horseKey: string) => void;
  selectedHorseRunner: Runner | null;
  fullCareerRuns: FormRun[];
};

function runTypeBadge(runType: string, sp: string): string {
  const t = String(runType || "").toUpperCase();
  if (t.includes("TRIAL") || sp === "$000") return "TRIAL";
  if (t.includes("JUMPOUT") || t.includes("JUMP OUT") || t.includes("JUMPOUT")) return "J/OUT";
  if (t.includes("JUMPOUT") || sp === "$000") return "J/OUT";
  return "RACE";
}

export default function FormTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
  selectedHorseRunner,
  fullCareerRuns,
}: Props) {
  const sortedRunners = useMemo(() => {
    return [...runners].sort((a, b) => (a.horseNo ?? 999) - (b.horseNo ?? 999));
  }, [runners]);

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-4 md:p-5 shadow-xl">
      <div className="grid grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)] gap-4">
        <aside className="rounded-2xl border border-slate-800 bg-slate-950 p-3">
          <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Horses</div>

          <div className="mt-3 max-h-[560px] overflow-y-auto space-y-2 pr-1">
            {sortedRunners.map((runner) => {
              const isSelected = runner.horseKey === selectedHorseKey;
              return (
                <button
                  key={runner.horseKey}
                  type="button"
                  onClick={() => onSelectHorse?.(runner.horseKey)}
                  className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                    isSelected
                      ? "border-slate-700/60 bg-[#07101d] text-slate-950"
                      : "border-slate-800 bg-slate-900 text-white hover:bg-slate-800"
                  }`}
                >
                  <div className="font-semibold">{runner.horse}</div>
                  <div className={`mt-1 text-xs ${isSelected ? "text-slate-600" : "text-slate-400"}`}>
                    No {runner.horseNo ?? "-"}  Bar {runner.barrier ?? "-"}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="rounded-2xl border border-slate-800 bg-slate-950">
          {selectedHorseRunner ? (
            <>
              <div className="border-b border-slate-800 p-4">
                <div className="text-2xl font-bold text-white">{selectedHorseRunner.horse}</div>
                <div className="mt-2 text-sm text-slate-300">
                  Trainer: {selectedHorseRunner.trainer || "-"}{" "}
                  | Jockey: {selectedHorseRunner.jockey || "-"}{" "}
                  | Barrier: {selectedHorseRunner.barrier ?? "-"}
                </div>
                <div className="mt-2 text-sm text-slate-400">
                  Record view: full career available  scroll for all runs
                </div>
              </div>

              <div className="max-h-[560px] overflow-auto">
                <table className="min-w-full text-sm">
                  <thead className="sticky top-0 bg-slate-950 text-slate-400 z-10">
                    <tr>
                      <th className="px-3 py-3 text-left">Date</th>
                      <th className="px-3 py-3 text-left">Type</th>
                      <th className="px-3 py-3 text-left">Track</th>
                      <th className="px-3 py-3 text-left">Dist</th>
                      <th className="px-3 py-3 text-left">Class</th>
                      <th className="px-3 py-3 text-left">Cond</th>
                      <th className="px-3 py-3 text-left">Fin</th>
                      <th className="px-3 py-3 text-left">Margin</th>
                      <th className="px-3 py-3 text-left">@800</th>
                      <th className="px-3 py-3 text-left">@400</th>
                      <th className="px-3 py-3 text-left">Barrier</th>
                      <th className="px-3 py-3 text-left">SP</th>
                      <th className="px-3 py-3 text-left">Rating</th>
                    </tr>
                  </thead>

                  <tbody>
                    {fullCareerRuns.map((run, idx) => {
                      const badge = runTypeBadge(run.runType, run.sp);
                      const isOfficial = run.isOfficialRace && badge === "RACE";

                      return (
                        <tr key={`${run.runDate}-${idx}`} className="border-t border-slate-800 hover:bg-slate-900/60">
                          <td className="px-3 py-3 whitespace-nowrap text-white">{run.runDate || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap">
                            <span
                              className={`inline-flex rounded-xl px-2.5 py-1 text-xs font-semibold ${
                                badge === "RACE"
                                  ? "bg-slate-800 text-slate-200"
                                  : badge === "TRIAL"
                                  ? "bg-amber-950/70 text-amber-300 border border-amber-800"
                                  : "bg-sky-950/70 text-sky-300 border border-sky-800"
                              }`}
                            >
                              {badge}
                            </span>
                          </td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.track || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">
                            {run.distance !== null ? Math.round(run.distance) : "-"}
                          </td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.raceClass || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.trackCondition || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.finishPos || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.margin || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">
                            {run.pos800 !== null ? Math.round(run.pos800) : "-"}
                          </td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">
                            {run.pos400 !== null ? Math.round(run.pos400) : "-"}
                          </td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">
                            {run.barrier !== null ? Math.round(run.barrier) : "-"}
                          </td>
                          <td className="px-3 py-3 whitespace-nowrap text-slate-200">{run.sp || "-"}</td>
                          <td className="px-3 py-3 whitespace-nowrap">
                            <span
                              className={`font-semibold ${
                                isOfficial && run.runRating !== null ? "text-white" : "text-slate-500"
                              }`}
                            >
                              {isOfficial && run.runRating !== null ? run.runRating.toFixed(2) : "-"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}

                    {!fullCareerRuns.length && (
                      <tr>
                        <td className="px-3 py-8 text-center text-slate-400" colSpan={13}>
                          No runs available.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="p-6 text-slate-400">No horse selected.</div>
          )}
        </div>
      </div>
    </section>
  );
}

