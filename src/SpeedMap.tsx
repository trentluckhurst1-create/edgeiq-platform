import { useMemo } from "react";
import type { CSSProperties } from "react";

type SpeedMapRow = {
  race_date?: string;
  track?: string;
  race_no?: number;
  horse: string;
  barrier?: number;
  speed_map_group?: string;
  speed_map_rank?: number;
  map_comment?: string;
  source?: string;
};

type CanonicalLane = "Leader" | "On Pace" | "Midfield" | "Back";

type Props = {
  rows: SpeedMapRow[];
};

type ProcessedRunner = {
  id: string;
  horse: string;
  barrier?: number;
  lane: CanonicalLane;
  rank: number;
  comment?: string;
  source?: string;
};

const LANE_ORDER: CanonicalLane[] = ["Leader", "On Pace", "Midfield", "Back"];

const laneDescriptions: Record<CanonicalLane, string> = {
  Leader: "Natural leaders and early pressure",
  "On Pace": "Forward runners just off the lead",
  Midfield: "Expected to settle midfield",
  Back: "Likely to drift back early"
};

export default function SpeedMap({ rows }: Props) {
  const processed = useMemo(() => buildProcessedRows(rows), [rows]);

  if (!rows.length) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>Speed Map</div>
            <div style={styles.subtitle}>No speed map data available for this race</div>
          </div>
        </div>
      </div>
    );
  }

  const maxBarrier = processed.maxBarrier;

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div>
          <div style={styles.title}>Elite Speed Map</div>
          <div style={styles.subtitle}>
            Premium visual settling positions by lane and barrier
          </div>
        </div>

        <div style={styles.metaGroup}>
          <div style={styles.metaPill}>{processed.runners.length} runners</div>
          <div style={styles.metaPill}>Barriers 1-{maxBarrier}</div>
        </div>
      </div>

      <div style={styles.barrierHeaderRow}>
        <div style={styles.barrierHeaderLabel}>Settle</div>
        <div style={styles.barrierHeaderTrack}>
          {Array.from({ length: maxBarrier }, (_, i) => i + 1).map((barrier) => (
            <div
              key={barrier}
              style={{
                ...styles.barrierMarker,
                left: `${barrierLeftPercent(barrier, maxBarrier)}%`
              }}
            >
              <span style={styles.barrierMarkerText}>{barrier}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.lanesWrap}>
        {LANE_ORDER.map((lane) => {
          const laneRunners = processed.byLane[lane];
          return (
            <LaneRow
              key={lane}
              lane={lane}
              runners={laneRunners}
              maxBarrier={maxBarrier}
            />
          );
        })}
      </div>
    </div>
  );
}

function LaneRow({
  lane,
  runners,
  maxBarrier
}: {
  lane: CanonicalLane;
  runners: ProcessedRunner[];
  maxBarrier: number;
}) {
  const accent = laneAccent(lane);

  return (
    <div style={styles.laneRow}>
      <div style={styles.laneLabelCell}>
        <div style={styles.laneLabel}>{lane}</div>
        <div style={styles.laneDescription}>{laneDescriptions[lane]}</div>
      </div>

      <div style={styles.trackCell}>
        <div style={styles.trackSurface} />
        <div style={styles.trackCenterLine} />

        {Array.from({ length: maxBarrier }, (_, i) => i + 1).map((barrier) => (
          <div
            key={barrier}
            style={{
              ...styles.trackGuide,
              left: `${barrierLeftPercent(barrier, maxBarrier)}%`
            }}
          />
        ))}

        {runners.map((runner, index) => {
          const left =
            typeof runner.barrier === "number" && runner.barrier > 0
              ? barrierLeftPercent(runner.barrier, maxBarrier)
              : fallbackLeftPercent(index, runners.length);

          return (
            <div
              key={runner.id}
              style={{
                ...styles.runnerWrap,
                left: `${left}%`
              }}
              title={buildRunnerTitle(runner, lane)}
            >
              <div
                style={{
                  ...styles.runnerPill,
                  border: `1px solid ${accent.border}`,
                  boxShadow: accent.shadow
                }}
              >
                <div
                  style={{
                    ...styles.barrierBadge,
                    background: accent.badgeBg,
                    color: accent.badgeText
                  }}
                >
                  {typeof runner.barrier === "number" ? runner.barrier : ""}
                </div>

                <div style={styles.runnerTextWrap}>
                  <div style={styles.runnerName}>{cleanHorseName(runner.horse)}</div>
                  {typeof runner.rank === "number" && runner.rank !== 999 ? (
                    <div style={styles.runnerComment}>Rank {runner.rank}</div>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function buildProcessedRows(rows: SpeedMapRow[]) {
  const runners: ProcessedRunner[] = rows.map((row, index) => ({
    id: `${row.horse}-${row.barrier ?? "x"}-${row.speed_map_rank ?? index}-${index}`,
    horse: row.horse,
    barrier: normalizePositiveNumber(row.barrier),
    lane: normalizeLane(row.speed_map_group),
    rank: normalizeRank(row.speed_map_rank),
    comment: cleanText(row.map_comment),
    source: cleanText(row.source)
  }));

  runners.sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;

    const barrierA = typeof a.barrier === "number" ? a.barrier : 999;
    const barrierB = typeof b.barrier === "number" ? b.barrier : 999;
    if (barrierA !== barrierB) return barrierA - barrierB;

    return a.horse.localeCompare(b.horse);
  });

  const byLane: Record<CanonicalLane, ProcessedRunner[]> = {
    Leader: [],
    "On Pace": [],
    Midfield: [],
    Back: []
  };

  runners.forEach((runner) => {
    byLane[runner.lane].push(runner);
  });

  LANE_ORDER.forEach((lane) => {
    byLane[lane].sort((a, b) => {
      if (a.rank !== b.rank) return a.rank - b.rank;

      const barrierA = typeof a.barrier === "number" ? a.barrier : 999;
      const barrierB = typeof b.barrier === "number" ? b.barrier : 999;
      if (barrierA !== barrierB) return barrierA - barrierB;

      return a.horse.localeCompare(b.horse);
    });
  });

  const discoveredMaxBarrier = Math.max(
    1,
    ...runners.map((runner, idx) =>
      typeof runner.barrier === "number" ? runner.barrier : idx + 1
    )
  );

  return {
    runners,
    byLane,
    maxBarrier: discoveredMaxBarrier
  };
}

function normalizeLane(value?: string): CanonicalLane {
  const text = String(value ?? "")
    .toLowerCase()
    .trim();

  if (
    text.includes("leader") ||
    text.includes("lead") ||
    text.includes("front") ||
    text.includes("forward")
  ) {
    return "Leader";
  }

  if (
    text.includes("on pace") ||
    text.includes("on-pace") ||
    text.includes("pace") ||
    text.includes("stalk") ||
    text.includes("box seat") ||
    text.includes("handy")
  ) {
    return "On Pace";
  }

  if (
    text.includes("midfield") ||
    text.includes("mid") ||
    text.includes("middle")
  ) {
    return "Midfield";
  }

  if (
    text.includes("back") ||
    text.includes("rear") ||
    text.includes("get back") ||
    text.includes("last")
  ) {
    return "Back";
  }

  return "Midfield";
}

function normalizePositiveNumber(value: unknown): number | undefined {
  const num = Number(value);
  if (Number.isFinite(num) && num > 0) {
    return num;
  }
  return undefined;
}

function normalizeRank(value: unknown): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : 999;
}

function barrierLeftPercent(barrier: number, maxBarrier: number): number {
  if (maxBarrier <= 1) return 50;
  return ((barrier - 1) / (maxBarrier - 1)) * 100;
}

function fallbackLeftPercent(index: number, total: number): number {
  if (total <= 1) return 50;
  return (index / (total - 1)) * 100;
}

function cleanHorseName(value: string): string {
  return String(value ?? "")
    .replace(/^\d+\.\s*/, "")
    .trim();
}

function cleanText(value?: string): string | undefined {
  const text = String(value ?? "").trim();
  return text ? text : undefined;
}

function buildRunnerTitle(runner: ProcessedRunner, lane: CanonicalLane): string {
  const bits = [
    cleanHorseName(runner.horse),
    typeof runner.barrier === "number" ? `Barrier ${runner.barrier}` : undefined,
    lane,
    runner.comment,
    runner.source
  ].filter(Boolean);

  return bits.join(" | ");
}

function laneAccent(lane: CanonicalLane) {
  switch (lane) {
    case "Leader":
      return {
        border: "rgba(102, 170, 255, 0.42)",
        badgeBg: "rgba(102, 170, 255, 0.18)",
        badgeText: "#dcecff",
        shadow: "0 10px 24px rgba(70, 120, 255, 0.16)"
      };
    case "On Pace":
      return {
        border: "rgba(86, 240, 190, 0.36)",
        badgeBg: "rgba(86, 240, 190, 0.16)",
        badgeText: "#dcfff3",
        shadow: "0 10px 24px rgba(55, 210, 160, 0.12)"
      };
    case "Midfield":
      return {
        border: "rgba(255, 211, 107, 0.36)",
        badgeBg: "rgba(255, 211, 107, 0.16)",
        badgeText: "#fff4cd",
        shadow: "0 10px 24px rgba(255, 190, 70, 0.12)"
      };
    case "Back":
      return {
        border: "rgba(255, 122, 122, 0.36)",
        badgeBg: "rgba(255, 122, 122, 0.16)",
        badgeText: "#ffe3e3",
        shadow: "0 10px 24px rgba(255, 100, 100, 0.12)"
      };
  }
}

const styles: Record<string, CSSProperties> = {
  card: {
    background: "linear-gradient(180deg, #0b1017 0%, #0a0f15 100%)",
    border: "1px solid #1f2937",
    borderRadius: 18,
    padding: 16,
    boxShadow: "0 18px 40px rgba(0, 0, 0, 0.22)"
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "flex-start",
    flexWrap: "wrap",
    marginBottom: 16
  },
  title: {
    fontSize: 20,
    fontWeight: 800,
    color: "#f8fafc",
    letterSpacing: "-0.02em"
  },
  subtitle: {
    marginTop: 4,
    fontSize: 12,
    color: "#94a3b8"
  },
  metaGroup: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap"
  },
  metaPill: {
    background: "rgba(255,255,255,0.04)",
    color: "#cbd5e1",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 999,
    padding: "7px 11px",
    fontSize: 12,
    fontWeight: 700
  },
  barrierHeaderRow: {
    display: "grid",
    gridTemplateColumns: "170px 1fr",
    gap: 12,
    marginBottom: 10
  },
  barrierHeaderLabel: {
    color: "#64748b",
    fontSize: 11,
    fontWeight: 800,
    textTransform: "uppercase",
    letterSpacing: "0.12em",
    alignSelf: "end"
  },
  barrierHeaderTrack: {
    position: "relative",
    height: 26,
    borderRadius: 12,
    background: "rgba(255,255,255,0.025)",
    border: "1px solid rgba(255,255,255,0.06)",
    overflow: "hidden"
  },
  barrierMarker: {
    position: "absolute",
    top: 0,
    transform: "translateX(-50%)",
    height: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center"
  },
  barrierMarkerText: {
    fontSize: 10,
    fontWeight: 800,
    color: "#94a3b8",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 999,
    padding: "2px 6px"
  },
  lanesWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 12
  },
  laneRow: {
    display: "grid",
    gridTemplateColumns: "170px 1fr",
    gap: 12,
    alignItems: "stretch"
  },
  laneLabelCell: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    padding: "10px 4px 10px 0"
  },
  laneLabel: {
    fontSize: 15,
    fontWeight: 800,
    color: "#f8fafc"
  },
  laneDescription: {
    marginTop: 4,
    fontSize: 12,
    color: "#94a3b8",
    lineHeight: 1.35
  },
  trackCell: {
    position: "relative",
    minHeight: 82,
    borderRadius: 16,
    overflow: "hidden",
    background: "linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02))",
    border: "1px solid rgba(255,255,255,0.06)"
  },
  trackSurface: {
    position: "absolute",
    inset: 0,
    background:
      "linear-gradient(90deg, rgba(255,255,255,0.015) 0%, rgba(255,255,255,0.04) 50%, rgba(255,255,255,0.015) 100%)"
  },
  trackCenterLine: {
    position: "absolute",
    left: 0,
    right: 0,
    top: "50%",
    height: 1,
    background: "rgba(255,255,255,0.06)",
    transform: "translateY(-50%)"
  },
  trackGuide: {
    position: "absolute",
    top: 8,
    bottom: 8,
    width: 1,
    background: "rgba(255,255,255,0.05)",
    transform: "translateX(-50%)"
  },
  runnerWrap: {
    position: "absolute",
    top: "50%",
    transform: "translate(-50%, -50%)",
    zIndex: 2
  },
  runnerPill: {
    minWidth: 110,
    maxWidth: 168,
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 10px",
    borderRadius: 14,
    background: "linear-gradient(180deg, #131a23 0%, #10161f 100%)",
    backdropFilter: "blur(8px)"
  },
  barrierBadge: {
    minWidth: 26,
    height: 26,
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 900,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0
  },
  runnerTextWrap: {
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    gap: 2
  },
  runnerName: {
    fontSize: 12,
    fontWeight: 800,
    color: "#f8fafc",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis"
  },
  runnerComment: {
    fontSize: 10,
    color: "#94a3b8",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    maxWidth: 120
  }
};


