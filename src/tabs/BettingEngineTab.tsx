import React, { useEffect, useMemo, useState } from "react";

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(value, decimals = 2) {
  const n = toNumber(value);
  if (n === null) return "";
  return n.toFixed(decimals);
}

function formatPrice(value) {
  const n = toNumber(value);
  if (n === null) return "";
  return `$${n.toFixed(2)}`;
}

function formatPercent(value) {
  const n = toNumber(value);
  if (n === null) return "";
  return `${n.toFixed(1)}%`;
}

function badgeClass(action) {
  if (action === "BET") {
    return "bg-green-600/20 text-green-300 border border-green-500/40";
  }
  if (action === "WATCH") {
    return "bg-yellow-500/20 text-yellow-200 border border-yellow-400/40";
  }
  return "bg-[#07101d]/5 text-zinc-300 border border-white/10";
}

function tierClass(tier) {
  if (tier === "A+") return "text-yellow-300";
  if (tier === "A") return "text-green-300";
  if (tier === "B") return "text-sky-300";
  if (tier === "C") return "text-orange-300";
  return "text-zinc-400";
}

function rowGlow(action, tier) {
  if (action === "BET" && tier === "A+") {
    return "ring-1 ring-yellow-400/30 bg-yellow-500/[0.04]";
  }
  if (action === "BET") {
    return "ring-1 ring-green-400/20 bg-green-500/[0.03]";
  }
  if (action === "WATCH") {
    return "ring-1 ring-yellow-400/15 bg-yellow-500/[0.03]";
  }
  return "bg-[#07101d]/[0.02]";
}

export default function BettingEngineTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState("BET_WATCH");
  const [selectedTrack, setSelectedTrack] = useState("ALL");
  const [sortBy, setSortBy] = useState("confidence");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        setLoading(true);
        const res = await fetch("/data/final_betting_board.csv", { cache: "no-store" });
        const text = await res.text();

        const parsed = parseCsv(text);
        if (isMounted) {
          setRows(parsed);
        }
      } catch (err) {
        console.error("Failed to load final_betting_board.csv", err);
        if (isMounted) setRows([]);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const tracks = useMemo(() => {
    const vals = Array.from(
      new Set(rows.map((r) => (r.track || "").trim()).filter(Boolean))
    ).sort();
    return ["ALL", ...vals];
  }, [rows]);

  const summary = useMemo(() => {
    const betCount = rows.filter((r) => r.bet_action === "BET").length;
    const watchCount = rows.filter((r) => r.bet_action === "WATCH").length;
    const aPlusCount = rows.filter((r) => r.bet_tier === "A+").length;
    const totalStake = rows.reduce(
      (sum, r) => sum + (toNumber(r.suggested_stake_units) || 0),
      0
    );

    return {
      betCount,
      watchCount,
      aPlusCount,
      totalStake,
    };
  }, [rows]);

  const filteredRows = useMemo(() => {
    let out = [...rows];

    if (filterAction === "BET") {
      out = out.filter((r) => r.bet_action === "BET");
    } else if (filterAction === "WATCH") {
      out = out.filter((r) => r.bet_action === "WATCH");
    } else if (filterAction === "BET_WATCH") {
      out = out.filter((r) => r.bet_action === "BET" || r.bet_action === "WATCH");
    }

    if (selectedTrack !== "ALL") {
      out = out.filter((r) => (r.track || "") === selectedTrack);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      out = out.filter((r) => {
        const horse = (r.horse_display || r.horse || "").toLowerCase();
        const track = (r.track || "").toLowerCase();
        return horse.includes(q) || track.includes(q);
      });
    }

    out.sort((a, b) => {
      if (sortBy === "confidence") {
        return (toNumber(b.betting_confidence_score) || -999) - (toNumber(a.betting_confidence_score) || -999);
      }
      if (sortBy === "edge") {
        return (toNumber(b.edge_pct) || -999) - (toNumber(a.edge_pct) || -999);
      }
      if (sortBy === "stake") {
        return (toNumber(b.suggested_stake_units) || -999) - (toNumber(a.suggested_stake_units) || -999);
      }
      if (sortBy === "price") {
        return (toNumber(a.market_price) || 9999) - (toNumber(b.market_price) || 9999);
      }
      return 0;
    });

    return out;
  }, [rows, filterAction, selectedTrack, sortBy, search]);

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-[1600px] px-6 py-6">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.25em] text-zinc-500">
              Betting Engine
            </div>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">
              Model Betting Board
            </h1>
            <p className="mt-2 text-sm text-zinc-400">
              Separate shortlist view. Your worksheet stays untouched.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="BET" value={summary.betCount} accent="green" />
            <StatCard label="WATCH" value={summary.watchCount} accent="yellow" />
            <StatCard label="A+ Plays" value={summary.aPlusCount} accent="gold" />
            <StatCard label="Stake" value={`${summary.totalStake.toFixed(2)}u`} accent="white" />
          </div>
        </div>

        <div className="mb-5 grid grid-cols-1 gap-3 rounded-2xl border border-white/10 bg-zinc-950 p-4 lg:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-zinc-500">
              Filter
            </label>
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none"
            >
              <option value="BET_WATCH">BET + WATCH</option>
              <option value="BET">BET only</option>
              <option value="WATCH">WATCH only</option>
              <option value="ALL">All</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-zinc-500">
              Track
            </label>
            <select
              value={selectedTrack}
              onChange={(e) => setSelectedTrack(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none"
            >
              {tracks.map((track) => (
                <option key={track} value={track}>
                  {track}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-zinc-500">
              Sort
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none"
            >
              <option value="confidence">Confidence</option>
              <option value="edge">Edge</option>
              <option value="stake">Stake</option>
              <option value="price">Market Price</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-wide text-zinc-500">
              Search
            </label>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Horse or track..."
              className="w-full rounded-xl border border-white/10 bg-black px-3 py-2 text-sm text-white outline-none placeholder:text-zinc-600"
            />
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-950">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-[#07101d]/[0.03] text-zinc-400">
                <tr className="border-b border-white/10">
                  <Th>Race</Th>
                  <Th>Horse</Th>
                  <Th>Action</Th>
                  <Th>Tier</Th>
                  <Th>Rated</Th>
                  <Th>Market</Th>
                  <Th>Edge</Th>
                  <Th>Confidence</Th>
                  <Th>Stake</Th>
                  <Th>Reason</Th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-10 text-center text-zinc-500">
                      Loading betting board...
                    </td>
                  </tr>
                ) : filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="px-4 py-10 text-center text-zinc-500">
                      No rows match current filters.
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((row, idx) => {
                    const raceLabel = `${row.track || ""} R${row.race_no || "?"}`;
                    const horse = row.horse_display || row.horse || "";
                    const action = row.bet_action || "NO BET";
                    const tier = row.bet_tier || "";

                    return (
                      <tr
                        key={`${horse}-${idx}`}
                        className={`border-b border-white/5 transition ${rowGlow(action, tier)}`}
                      >
                        <Td>
                          <div className="font-medium text-white">{raceLabel}</div>
                          <div className="text-xs text-zinc-500">{row.race_date || ""}</div>
                        </Td>

                        <Td>
                          <div className="font-semibold text-white">{horse}</div>
                          <div className="text-xs text-zinc-500">
                            {row.race_class || ""}
                          </div>
                        </Td>

                        <Td>
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass(action)}`}>
                            {action}
                          </span>
                        </Td>

                        <Td>
                          <span className={`font-semibold ${tierClass(tier)}`}>{tier}</span>
                        </Td>

                        <Td>{formatPrice(row.rated_price)}</Td>
                        <Td>{formatPrice(row.market_price)}</Td>
                        <Td>{formatPercent(row.edge_pct)}</Td>
                        <Td>{formatNumber(row.betting_confidence_score, 1)}</Td>
                        <Td>{formatNumber(row.suggested_stake_units, 2)}u</Td>
                        <Td>
                          <div className="max-w-[520px] whitespace-normal text-xs text-zinc-300">
                            {row.bet_reason || ""}
                          </div>
                        </Td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, accent = "white" }) {
  const accentClass =
    accent === "green"
      ? "text-green-300"
      : accent === "yellow"
      ? "text-yellow-200"
      : accent === "gold"
      ? "text-yellow-300"
      : "text-white";

  return (
    <div className="rounded-2xl border border-white/10 bg-black px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.2em] text-zinc-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${accentClass}`}>{value}</div>
    </div>
  );
}

function Th({ children }) {
  return (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide">
      {children}
    </th>
  );
}

function Td({ children }) {
  return <td className="px-4 py-3 align-top">{children}</td>;
}

function parseCsv(text) {
  const lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n").filter(Boolean);
  if (lines.length === 0) return [];

  const headers = parseCsvLine(lines[0]);
  const rows = [];

  for (let i = 1; i < lines.length; i += 1) {
    const values = parseCsvLine(lines[i]);
    const row = {};

    headers.forEach((header, idx) => {
      row[header] = values[idx] ?? "";
    });

    rows.push(row);
  }

  return rows;
}

function parseCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      current += '"';
      i += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      out.push(current);
      current = "";
      continue;
    }

    current += char;
  }

  out.push(current);
  return out;
}


