import React, { useMemo } from "react";

// -----------------------------
// TYPES
// -----------------------------

type BettingRow = Record<string, any>;

type BettingTabProps = {
  betsRows: BettingRow[];
  selectedRaceDate?: string | null;
  selectedTrack?: string | null;
  selectedRaceNo?: number | string | null;
};

// -----------------------------
// HELPERS
// -----------------------------

const clean = (v: any) => (v === null || v === undefined ? "" : String(v).trim());

const toNum = (v: any) => {
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
};

const toInt = (v: any) => {
  const n = parseInt(v, 10);
  return isNaN(n) ? 0 : n;
};

function trackKey(v: any) {
  return clean(v)
    .toUpperCase()
    .replace(/[^A-Z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatPrice(v: any) {
  const n = toNum(v);
  return n ? `$${n.toFixed(2)}` : "";
}

function formatPct(v: any, digits = 1) {
  const n = toNum(v);
  return n ? `${(n * 100).toFixed(digits)}%` : "";
}

function formatProb(v: any) {
  const n = toNum(v);
  return n ? `${(n * 100).toFixed(1)}%` : "";
}

function formatStake(v: any) {
  const n = toNum(v);
  return n ? `${n.toFixed(2)}u` : "";
}

function boolish(v: any) {
  const s = clean(v).toLowerCase();
  return s === "true" || s === "1" || s === "yes" || s === "y";
}

function splitFlags(v: any) {
  const raw = clean(v);
  if (!raw || raw.toLowerCase() === "nan") return [];
  return raw
    .split("|")
    .map((x) => clean(x))
    .filter(Boolean);
}

function tierBg(tier: string) {
  if (tier === "A") {
    return {
      background: "rgba(16, 185, 129, 0.15)",
      border: "1px solid rgba(16, 185, 129, 0.35)",
      color: "#6ee7b7",
    };
  }

  if (tier === "B") {
    return {
      background: "rgba(245, 158, 11, 0.15)",
      border: "1px solid rgba(245, 158, 11, 0.35)",
      color: "#fcd34d",
    };
  }

  return {
    background: "rgba(148, 163, 184, 0.12)",
    border: "1px solid rgba(148, 163, 184, 0.25)",
    color: "#cbd5e1",
  };
}

function edgeColor(v: any) {
  const n = toNum(v);
  if (n >= 0.75) return "#86efac";
  if (n >= 0.30) return "#bef264";
  if (n >= 0.15) return "#fcd34d";
  return "#cbd5e1";
}

// -----------------------------
// COMPONENT
// -----------------------------

export default function BettingTab({
  betsRows,
  selectedRaceDate,
  selectedTrack,
  selectedRaceNo,
}: BettingTabProps) {
  const filteredRows = useMemo(() => {
    const raceDate = clean(selectedRaceDate);
    const track = trackKey(selectedTrack);
    const raceNo = toInt(selectedRaceNo);

    return (betsRows || []).filter((r) => {
      const rowDate = clean(r.race_date);
      const rowTrack = trackKey(r.track);
      const rowRaceNo = toInt(r.race_no);

      return rowDate === raceDate && rowTrack === track && rowRaceNo === raceNo;
    });
  }, [betsRows, selectedRaceDate, selectedTrack, selectedRaceNo]);

  const summary = useMemo(() => {
    const totalBets = filteredRows.length;
    const totalStake = filteredRows.reduce((sum, r) => sum + toNum(r.stake), 0);
    const avgEdge =
      totalBets > 0
        ? filteredRows.reduce((sum, r) => sum + toNum(r.edge_pct), 0) / totalBets
        : 0;

    const aCount = filteredRows.filter((r) => clean(r.confidence_tier).toUpperCase() === "A").length;
    const bCount = filteredRows.filter((r) => clean(r.confidence_tier).toUpperCase() === "B").length;
    const cCount = filteredRows.filter((r) => clean(r.confidence_tier).toUpperCase() === "C").length;

    return {
      totalBets,
      totalStake,
      avgEdge,
      aCount,
      bCount,
      cCount,
    };
  }, [filteredRows]);

  if (!filteredRows.length) {
    return (
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 16,
          padding: 20,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 20 }}>Bets</h2>
        <div style={{ marginTop: 8, color: "#94a3b8", fontSize: 14 }}>
          No qualified bets for this race.
        </div>

        <div
          style={{
            marginTop: 16,
            background: "#0f172a",
            border: "1px solid #1f2937",
            borderRadius: 12,
            padding: 16,
            color: "#cbd5e1",
            fontSize: 14,
          }}
        >
          The Worksheet stays analysis-first.
          <br />
          This tab only shows runners that passed the betting engine filters.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {/* HEADER / SUMMARY */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 16,
          padding: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 16,
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 20 }}>Bets</h2>
            <div style={{ marginTop: 6, color: "#94a3b8", fontSize: 14 }}>
              Filtered execution shortlist for the selected race.
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <SummaryCard label="Bets" value={String(summary.totalBets)} />
            <SummaryCard label="Total Stake" value={`${summary.totalStake.toFixed(2)}u`} />
            <SummaryCard label="Avg Edge" value={formatPct(summary.avgEdge)} accent="#86efac" />
            <SummaryCard
              label="A / B / C"
              value={`${summary.aCount} / ${summary.bCount} / ${summary.cCount}`}
            />
          </div>
        </div>
      </div>

      {/* MAIN TABLE */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 16,
          overflow: "hidden",
        }}
      >
        <div style={{ padding: 16, borderBottom: "1px solid #1f2937" }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Qualified Bets</div>
          <div style={{ marginTop: 4, color: "#94a3b8", fontSize: 14 }}>
            Stakes and tiers only live in this tab.
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#0f172a" }}>
              <tr>
                <th style={thStyle}>No</th>
                <th style={thStyle}>Horse</th>
                <th style={thStyle}>Bar</th>
                <th style={thStyle}>Jockey</th>
                <th style={thStyle}>Trainer</th>
                <th style={thStyle}>Prob</th>
                <th style={thStyle}>Rated</th>
                <th style={thStyle}>Market</th>
                <th style={thStyle}>Edge</th>
                <th style={thStyle}>Tier</th>
                <th style={thStyle}>Stake</th>
                <th style={thStyle}>Flags</th>
              </tr>
            </thead>

            <tbody>
              {filteredRows.map((r, i) => {
                const tier = clean(r.confidence_tier).toUpperCase() || "C";
                const flags = splitFlags(r.profile_flag);
                const isScratched = boolish(r.is_scratched);

                return (
                  <tr
                    key={`${clean(r.race_date)}-${clean(r.track)}-${clean(r.race_no)}-${clean(r.horse)}-${i}`}
                    style={{
                      borderTop: "1px solid #1f2937",
                      opacity: isScratched ? 0.45 : 1,
                      textDecoration: isScratched ? "line-through" : "none",
                    }}
                  >
                    <td style={tdStyle}>{toInt(r.horse_no) || ""}</td>
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 700 }}>{clean(r.horse) || ""}</div>
                      <div style={{ marginTop: 4, color: "#94a3b8", fontSize: 12 }}>
                        Rank {toInt(r.model_rank) || ""}
                        {clean(r.last_start) ? ` " ${clean(r.last_start)}` : ""}
                      </div>
                    </td>
                    <td style={tdStyle}>{toInt(r.barrier) || ""}</td>
                    <td style={tdStyle}>{clean(r.jockey) || ""}</td>
                    <td style={tdStyle}>{clean(r.trainer) || ""}</td>
                    <td style={tdStyle}>{formatProb(r.model_probability)}</td>
                    <td style={tdStyle}>{formatPrice(r.rated_price)}</td>
                    <td style={tdStyle}>{formatPrice(r.market_price)}</td>
                    <td style={{ ...tdStyle, color: edgeColor(r.edge_pct), fontWeight: 700 }}>
                      {formatPct(r.edge_pct)}
                    </td>
                    <td style={tdStyle}>
                      <span
                        style={{
                          ...tierBg(tier),
                          display: "inline-block",
                          minWidth: 30,
                          textAlign: "center",
                          padding: "4px 10px",
                          borderRadius: 999,
                          fontSize: 12,
                          fontWeight: 800,
                        }}
                      >
                        {tier}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, fontWeight: 700 }}>{formatStake(r.stake)}</td>
                    <td style={tdStyle}>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {flags.length ? (
                          flags.map((flag) => (
                            <span
                              key={flag}
                              style={{
                                fontSize: 11,
                                padding: "4px 8px",
                                borderRadius: 999,
                                background: "#0f172a",
                                border: "1px solid #334155",
                                color: "#cbd5e1",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {flag.replace(/_/g, " ")}
                            </span>
                          ))
                        ) : (
                          <span style={{ color: "#64748b", fontSize: 12 }}></span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* BET CARDS */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 16,
          padding: 20,
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 700 }}>Bet Notes</div>
        <div style={{ marginTop: 6, color: "#94a3b8", fontSize: 14 }}>
          Quick execution summary for the shortlisted runners.
        </div>

        <div
          style={{
            marginTop: 16,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: 14,
          }}
        >
          {filteredRows.map((r, i) => {
            const tier = clean(r.confidence_tier).toUpperCase() || "C";
            const flags = splitFlags(r.profile_flag);

            return (
              <div
                key={`card-${clean(r.horse)}-${i}`}
                style={{
                  background: "#0f172a",
                  border: "1px solid #1f2937",
                  borderRadius: 14,
                  padding: 16,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 12,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 800 }}>{clean(r.horse) || ""}</div>
                    <div style={{ marginTop: 4, color: "#94a3b8", fontSize: 12 }}>
                      #{toInt(r.horse_no) || ""} " Barrier {toInt(r.barrier) || ""}
                    </div>
                  </div>

                  <span
                    style={{
                      ...tierBg(tier),
                      display: "inline-block",
                      minWidth: 34,
                      textAlign: "center",
                      padding: "4px 10px",
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 800,
                    }}
                  >
                    {tier}
                  </span>
                </div>

                <div
                  style={{
                    marginTop: 14,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 10,
                  }}
                >
                  <MiniMetric label="Prob" value={formatProb(r.model_probability)} />
                  <MiniMetric label="Edge" value={formatPct(r.edge_pct)} />
                  <MiniMetric label="Rated" value={formatPrice(r.rated_price)} />
                  <MiniMetric label="Market" value={formatPrice(r.market_price)} />
                  <MiniMetric label="Stake" value={formatStake(r.stake)} />
                  <MiniMetric label="Place" value={formatPrice(r.fixed_place)} />
                </div>

                <div style={{ marginTop: 14, color: "#cbd5e1", fontSize: 13 }}>
                  <strong>Jockey:</strong> {clean(r.jockey) || ""}
                </div>
                <div style={{ marginTop: 6, color: "#cbd5e1", fontSize: 13 }}>
                  <strong>Trainer:</strong> {clean(r.trainer) || ""}
                </div>
                <div style={{ marginTop: 6, color: "#94a3b8", fontSize: 12 }}>
                  <strong>Last start:</strong> {clean(r.last_start) || ""}
                </div>

                <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {flags.length ? (
                    flags.map((flag) => (
                      <span
                        key={flag}
                        style={{
                          fontSize: 11,
                          padding: "4px 8px",
                          borderRadius: 999,
                          background: "#111827",
                          border: "1px solid #334155",
                          color: "#cbd5e1",
                        }}
                      >
                        {flag.replace(/_/g, " ")}
                      </span>
                    ))
                  ) : (
                    <span style={{ color: "#64748b", fontSize: 12 }}>No flags</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// -----------------------------
// SMALL COMPONENTS
// -----------------------------

function SummaryCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        minWidth: 130,
        background: "#0f172a",
        border: "1px solid #1f2937",
        borderRadius: 12,
        padding: 12,
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8" }}>{label}</div>
      <div
        style={{
          marginTop: 6,
          fontSize: 22,
          fontWeight: 800,
          color: accent || "#fff",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: "#111827",
        border: "1px solid #1f2937",
        borderRadius: 10,
        padding: "10px 12px",
      }}
    >
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div style={{ marginTop: 4, fontSize: 15, fontWeight: 700, color: "#fff" }}>{value}</div>
    </div>
  );
}

// -----------------------------
// SIMPLE TABLE STYLES
// -----------------------------

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "12px 14px",
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#94a3b8",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 14px",
  fontSize: 14,
  color: "#fff",
};


