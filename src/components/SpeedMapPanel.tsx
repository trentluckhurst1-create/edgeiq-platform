import { normaliseHorse } from "../lib/normalise";
import React, { useMemo } from "react";

type Runner = {
  horse: string;
  horse_no?: number | string | null;
  barrier?: number | string | null;
  speed_map_group?: string | null;
  speed_map_rank?: number | string | null;
  silk_url?: string | null;
  market_price?: number | string | null;
  rated_price?: number | string | null;
  edge_pct?: number | string | null;
  jockey?: string | null;
  trainer?: string | null;
};

type Props = {
  runners: Runner[];
  selectedHorse?: string | null;
  onSelectHorse?: (horse: string) => void;
  title?: string;
};

const GROUP_ORDER = ["Leader", "On Pace", "Midfield", "Back"] as const;

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeGroup(group?: string | null): string {
  const g = String(group || "").trim().toLowerCase();

  if (g === "leader" || g === "leaders") return "Leader";
  if (g === "on pace" || g === "on-pace" || g === "onpace" || g === "forward") return "On Pace";
  if (g === "midfield" || g === "mid") return "Midfield";
  if (g === "back" || g === "rear") return "Back";

  return "";
}

function formatOdds(value: unknown): string {
  const n = toNumber(value);
  if (n === null || n <= 0) return "";
  return `$${n.toFixed(n >= 10 ? 1 : 2).replace(/\.00$/, "")}`;
}

function formatEdge(value: unknown): string {
  const n = toNumber(value);
  if (n === null) return "";
  return `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
}

function buildRows(runners: Runner[]) {
  const grouped: Record<string, Runner[]> = {
    Leader: [],
    "On Pace": [],
    Midfield: [],
    Back: [],
  };

  for (const r of runners) {
    const group = normalizeGroup(r.speed_map_group);
    if (group && grouped[group]) grouped[group].push(r);
  }

  for (const key of GROUP_ORDER) {
    grouped[key].sort((a, b) => {
      const ra = toNumber(a.speed_map_rank);
      const rb = toNumber(b.speed_map_rank);
      if (ra === null && rb === null) return String(a.horse).localeCompare(String(b.horse));
      if (ra === null) return 1;
      if (rb === null) return -1;
      return ra - rb;
    });
  }

  return grouped;
}

function RunnerPill({
  runner,
  selected,
  onClick,
}: {
  runner: Runner;
  selected: boolean;
  onClick?: () => void;
}) {
  const edge = toNumber(runner.edge_pct);
  const positiveEdge = edge !== null && edge > 0;

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        background: selected ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)",
        border: selected ? "1px solid rgba(255,255,255,0.35)" : "1px solid rgba(255,255,255,0.10)",
        borderRadius: 16,
        padding: 10,
        minWidth: 165,
        textAlign: "left",
        cursor: "pointer",
        color: "#fff",
        boxShadow: selected ? "0 0 0 1px rgba(255,255,255,0.08) inset" : "none",
        transition: "all 0.15s ease",
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <div
          style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: "rgba(255,255,255,0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          {runner.silk_url ? (
            <img
              src={runner.silk_url}
              alt={runner.horse}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          ) : (
            <span style={{ fontSize: 11, opacity: 0.7 }}>Silk</span>
          )}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              display: "flex",
              gap: 6,
              alignItems: "center",
              marginBottom: 3,
              flexWrap: "wrap",
            }}
          >
            {runner.horse_no !== null && runner.horse_no !== undefined && runner.horse_no !== "" && (
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 999,
                  background: "rgba(255,255,255,0.10)",
                  color: "rgba(255,255,255,0.82)",
                }}
              >
                #{runner.horse_no}
              </span>
            )}

            {runner.barrier !== null && runner.barrier !== undefined && runner.barrier !== "" && (
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 999,
                  background: "rgba(255,255,255,0.10)",
                  color: "rgba(255,255,255,0.82)",
                }}
              >
                B {runner.barrier}
              </span>
            )}

            {runner.speed_map_rank !== null &&
              runner.speed_map_rank !== undefined &&
              runner.speed_map_rank !== "" && (
                <span
                  style={{
                    fontSize: 10,
                    padding: "2px 6px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.10)",
                    color: "rgba(255,255,255,0.82)",
                  }}
                >
                  Map {runner.speed_map_rank}
                </span>
              )}
          </div>

          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              lineHeight: 1.2,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              marginBottom: 5,
            }}
          >
            {runner.horse}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 6,
              fontSize: 10,
              color: "rgba(255,255,255,0.72)",
            }}
          >
            <div>
              <div style={{ opacity: 0.7 }}>Rated</div>
              <div style={{ color: "#fff", fontWeight: 600 }}>{formatOdds(runner.rated_price)}</div>
            </div>
            <div>
              <div style={{ opacity: 0.7 }}>Market</div>
              <div style={{ color: "#fff", fontWeight: 600 }}>{formatOdds(runner.market_price)}</div>
            </div>
            <div>
              <div style={{ opacity: 0.7 }}>Edge</div>
              <div style={{ color: positiveEdge ? "#7CFFB2" : "#fff", fontWeight: 700 }}>
                {formatEdge(runner.edge_pct)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </button>
  );
}

function DetailCard({ runner }: { runner: Runner | null }) {
  if (!runner) {
    return (
      <div
        style={{
          borderRadius: 18,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
          color: "rgba(255,255,255,0.72)",
          minHeight: 140,
        }}
      >
        Click a runner on the map to inspect speed-map position and price profile.
      </div>
    );
  }

  return (
    <div
      style={{
        borderRadius: 18,
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        color: "#fff",
        minHeight: 140,
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12 }}>
        <div
          style={{
            width: 52,
            height: 52,
            borderRadius: 12,
            background: "rgba(255,255,255,0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          {runner.silk_url ? (
            <img
              src={runner.silk_url}
              alt={runner.horse}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          ) : null}
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 18, fontWeight: 800, lineHeight: 1.15 }}>{runner.horse}</div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.68)", marginTop: 4 }}>
            {normalizeGroup(runner.speed_map_group) || ""}  Map rank {runner.speed_map_rank ?? ""}  Barrier{" "}
            {runner.barrier ?? ""}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: 10,
          marginBottom: 12,
        }}
      >
        {[
          ["Rated", formatOdds(runner.rated_price)],
          ["Market", formatOdds(runner.market_price)],
          ["Edge", formatEdge(runner.edge_pct)],
          ["Jockey", runner.jockey || ""],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{
              borderRadius: 14,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              padding: 10,
            }}
          >
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.62)", marginBottom: 4 }}>{label}</div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: label === "Edge" && String(value).startsWith("+") ? "#7CFFB2" : "#fff",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)" }}>
        Trainer: <span style={{ color: "#fff" }}>{runner.trainer || ""}</span>
      </div>
    </div>
  );
}

export default function SpeedMapPanel({
  runners,
  selectedHorse,
  onSelectHorse,
  title = "Visual Speed Map",
}: Props) {
  const grouped = useMemo(() => buildRows(runners), [runners]);

  const selectedRunner =
    runners.find((r) => normaliseHorse(r.horse) === normaliseHorse(selectedHorse || "")) || null;

  const totalMapped = runners.filter((r) => normalizeGroup(r.speed_map_group)).length;

  return (
    <section
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1.6fr) minmax(320px, 0.9fr)",
        gap: 16,
      }}
    >
      <div
        style={{
          borderRadius: 24,
          background: "linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.03))",
          border: "1px solid rgba(255,255,255,0.08)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "16px 18px 12px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#fff" }}>{title}</div>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.65)", marginTop: 3 }}>
              Settling-position view using mapped runners only
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <div
              style={{
                padding: "7px 10px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.07)",
                color: "rgba(255,255,255,0.78)",
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              Mapped {totalMapped}
            </div>
            <div
              style={{
                padding: "7px 10px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.07)",
                color: "rgba(255,255,255,0.78)",
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              Field {runners.length}
            </div>
          </div>
        </div>

        <div style={{ padding: 16 }}>
          {GROUP_ORDER.map((group, idx) => {
            const row = grouped[group];
            return (
              <div
                key={group}
                style={{
                  marginBottom: idx === GROUP_ORDER.length - 1 ? 0 : 12,
                  borderRadius: 20,
                  border: "1px solid rgba(255,255,255,0.06)",
                  background: "rgba(255,255,255,0.03)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    padding: "10px 14px",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 800, color: "#fff" }}>{group}</div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.62)" }}>{row.length} runners</div>
                </div>

                <div
                  style={{
                    padding: 12,
                    display: "flex",
                    gap: 10,
                    overflowX: "auto",
                  }}
                >
                  {row.length ? (
                    row.map((runner) => (
                      <RunnerPill
                        key={runner.horse}
                        runner={runner}
                        selected={normaliseHorse(selectedHorse || "") === normaliseHorse(runner.horse)}
                        onClick={() => onSelectHorse?.(runner.horse)}
                      />
                    ))
                  ) : (
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.52)", padding: 8 }}>
                      No mapped runners in this lane.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <DetailCard runner={selectedRunner} />
    </section>
  );
}



