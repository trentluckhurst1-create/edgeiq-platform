import React, { useEffect, useMemo, useState } from "react";

const fmt = (v) => {
  if (v === null || v === undefined || v === "") return "-";
  return Number(v).toLocaleString();
};

const pct = (v) => {
  const n = Number(v || 0);
  return `${n.toFixed(2)}%`;
};

const loadCsv = async (path) => {
  const text = await fetch(path + `?t=${Date.now()}`).then(r => r.text());

  const lines = text.trim().split(/\r?\n/);

  if (lines.length <= 1) return [];

  const headers = lines[0].split(",");

  return lines.slice(1).map(line => {
    const vals = line.split(",");
    const row = {};
    headers.forEach((h, i) => row[h] = vals[i] ?? "");
    return row;
  });
};

const MetricCard = ({ title, value, sub }) => (
  <div className="rounded-2xl border border-emerald-500/20 bg-[#081018] p-4 shadow-lg shadow-black/30">
    <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
      {title}
    </div>

    <div className="mt-2 text-3xl font-black text-white">
      {value}
    </div>

    <div className="mt-1 text-xs text-zinc-400">
      {sub}
    </div>
  </div>
);

export default function AccountabilityCentreTab() {

  const [summary, setSummary] = useState([]);
  const [matchTypes, setMatchTypes] = useState([]);
  const [pending, setPending] = useState([]);

  useEffect(() => {

    loadCsv("/data/edgeiq_accountability_summary.csv").then(setSummary);
    loadCsv("/data/edgeiq_accountability_match_types.csv").then(setMatchTypes);
    loadCsv("/data/edgeiq_accountability_pending_breakdown.csv").then(setPending);

  }, []);

  const s = summary[0] || {};

  const topPending = useMemo(() => {
    return [...pending]
      .sort((a, b) => Number(b.rows || 0) - Number(a.rows || 0))
      .slice(0, 20);
  }, [pending]);

  return (
    <div className="edgeiq-aux-terminal text-white">

      <div className="mb-6 flex items-center justify-between border-b border-emerald-500/20 pb-4">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-emerald-400">
            EDGEIQ RACING
          </div>

          <h1 className="mt-1 text-3xl font-black tracking-tight">
            Accountability Centre
          </h1>
        </div>

        <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300">
          Settlement Rate {pct(s.settlement_rate_pct)}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

        <MetricCard
          title="Settled Rows"
          value={fmt(s.settled_rows)}
          sub="Officially reconciled"
        />

        <MetricCard
          title="Pending Rows"
          value={fmt(s.pending_rows)}
          sub="Awaiting resolution"
        />

        <MetricCard
          title="Exact Matches"
          value={fmt(s.exact_matches)}
          sub="High confidence reconciliation"
        />

        <MetricCard
          title="Unresolved Review"
          value={fmt(s.unresolved_requires_review)}
          sub="Manual review queue"
        />

      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">

        <div className="rounded-2xl border border-emerald-500/20 bg-[#081018] p-4">

          <div className="mb-4 text-sm font-bold uppercase tracking-[0.18em] text-emerald-300">
            Match Quality
          </div>

          <div className="space-y-3">

            {matchTypes.map((r, idx) => (

              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-white/5 bg-black/20 px-4 py-3"
              >

                <div className="text-sm text-zinc-300">
                  {r.result_match_type}
                </div>

                <div className="text-lg font-black text-white">
                  {fmt(r.rows)}
                </div>

              </div>

            ))}

          </div>

        </div>

        <div className="rounded-2xl border border-emerald-500/20 bg-[#081018] p-4">

          <div className="mb-4 text-sm font-bold uppercase tracking-[0.18em] text-emerald-300">
            Top Pending Meetings
          </div>

          <div className="space-y-2 max-h-[600px] overflow-auto pr-2">

            {topPending.map((r, idx) => (

              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-white/5 bg-black/20 px-4 py-3"
              >

                <div>
                  <div className="text-sm font-semibold text-white">
                    {r.track}
                  </div>

                  <div className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">
                    {r.pending_classification}
                  </div>
                </div>

                <div className="text-lg font-black text-amber-300">
                  {fmt(r.rows)}
                </div>

              </div>

            ))}

          </div>

        </div>

      </div>

    </div>
  );
}
