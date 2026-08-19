import React from "react";

type Runner = {
  horse: string;
  barrier: number | null;
  speedMapBucket?: string;
};

type Props = {
  runners: Runner[];
};

function bucketName(bucket?: string): string {
  return String(bucket || "").toUpperCase().trim();
}

function laneFillCount(bucket?: string): number {
  const b = bucketName(bucket);

  if (b.includes("LEADER")) return 4;
  if (b.includes("ON PACE")) return 3;
  if (b.includes("MIDFIELD")) return 2;
  if (b.includes("BACK")) return 1;
  if (b.includes("FIRST START")) return 0;

  return 0;
}

function laneFillClass(bucket?: string): string {
  const b = bucketName(bucket);

  if (b.includes("LEADER")) return "bg-blue-500";
  if (b.includes("ON PACE")) return "bg-sky-400";
  if (b.includes("MIDFIELD")) return "bg-amber-400";
  if (b.includes("BACK")) return "bg-rose-500";
  if (b.includes("FIRST START")) return "bg-slate-700";

  return "bg-slate-800";
}

function bucketLabel(bucket?: string): string {
  const b = bucketName(bucket);

  if (b.includes("LEADER")) return "LEADER";
  if (b.includes("ON PACE")) return "ON PACE";
  if (b.includes("MIDFIELD")) return "MIDFIELD";
  if (b.includes("BACK")) return "BACKMARKER";
  if (b.includes("FIRST START")) return "FIRST START";

  return "-";
}

export default function SpeedMap({ runners }: Props) {
  const sorted = [...runners].sort((a, b) => (b.barrier ?? 0) - (a.barrier ?? 0));

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
      <div className="mb-4">
        <div className="text-lg font-bold text-white">Speed Map</div>
        <div className="mt-1 text-sm text-slate-400">
          Barrier 1 at the bottom. Higher barriers rise to the top.
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <div className="grid grid-cols-[56px_minmax(0,1fr)_180px_110px] gap-3 mb-3 text-[11px] uppercase tracking-[0.22em] text-slate-500">
          <div>Bar</div>
          <div className="grid grid-cols-4 gap-2">
            <div>Back</div>
            <div>Mid</div>
            <div>On Pace</div>
            <div>Lead</div>
          </div>
          <div>Horse</div>
          <div>Map</div>
        </div>

        <div className="space-y-2">
          {sorted.map((runner) => {
            const fillCount = laneFillCount(runner.speedMapBucket);
            const fillClass = laneFillClass(runner.speedMapBucket);
            const label = bucketLabel(runner.speedMapBucket);

            return (
              <div
                key={`${runner.horse}-${runner.barrier ?? "x"}`}
                className="grid grid-cols-[56px_minmax(0,1fr)_180px_110px] gap-3 items-center"
              >
                <div className="text-sm font-semibold text-slate-300">
                  {runner.barrier ?? "-"}
                </div>

                <div className="grid grid-cols-4 gap-2">
                  {[1, 2, 3, 4].map((col) => (
                    <div
                      key={col}
                      className={`h-7 rounded-xl border border-slate-800 ${
                        col <= fillCount ? fillClass : "bg-slate-900"
                      }`}
                    />
                  ))}
                </div>

                <div className="text-sm font-semibold text-white truncate">
                  {runner.horse}
                </div>

                <div className="text-xs font-semibold text-slate-300">
                  {label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

