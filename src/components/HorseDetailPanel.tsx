import React, { useMemo } from "react";
import type { HistoricalFormRow, RaceMarketRow } from "../types/racing";

type Props = {
  selectedRunner: RaceMarketRow | null;
  formRows: HistoricalFormRow[];
};

function formatNumber(value: number | null, decimals = 1): string {
  if (value === null || value === undefined) return "";
  return value.toFixed(decimals);
}

function formatPrice(value: number | null): string {
  if (value === null || value === undefined || value <= 0) return "";
  return `$${value.toFixed(2)}`;
}

function average(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function performancePath(values: number[], width: number, height: number): string {
  if (!values.length) return "";

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const lastIndex = Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      const x = (index / lastIndex) * width;
      const y = height - ((value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

export default function HorseDetailPanel({ selectedRunner, formRows }: Props) {
  const orderedForm = useMemo(() => {
    return [...formRows].sort((a, b) => {
      if (a.race_date !== b.race_date) return b.race_date.localeCompare(a.race_date);
      return (b.race_no ?? 0) - (a.race_no ?? 0);
    });
  }, [formRows]);

  const runRatings = orderedForm
    .map((row) => row.run_rating)
    .filter((v): v is number => v !== null && Number.isFinite(v));

  const latestRunRating = runRatings.length ? runRatings[0] : null;
  const last3 = average(runRatings.slice(0, 3));
  const last5 = average(runRatings.slice(0, 5));
  const peak = runRatings.length ? Math.max(...runRatings) : null;
  const chartValues = [...runRatings].reverse();
  const polyline = performancePath(chartValues, 420, 90);

  if (!selectedRunner) {
    return (
      <div style={styles.emptyWrap}>
        <div style={styles.emptyTitle}>Horse Detail Panel</div>
        <div style={styles.emptyText}>
          Click a runner in the worksheet to open full form and ratings.
        </div>
      </div>
    );
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.topHeader}>
        <div>
          <div style={styles.titleRow}>
            <div style={styles.numberBadge}>{selectedRunner.horse_no ?? ""}</div>
            <div>
              <div style={styles.horseName}>{selectedRunner.horse}</div>
              <div style={styles.metaLine}>
                Bar {selectedRunner.barrier ?? ""}  {selectedRunner.jockey || ""} {" "}
                {selectedRunner.trainer || ""}
              </div>
            </div>
          </div>
        </div>
        <div style={styles.todayCard}>
          <div style={styles.todayCardLabel}>Today</div>
          <div style={styles.todayCardValue}>{formatNumber(selectedRunner.today_rating, 2)}</div>
          <div style={styles.todayCardSub}>
            Win Fig {formatNumber(selectedRunner.winning_rating, 2)}  Gap{" "}
            {selectedRunner.today_rating !== null && selectedRunner.winning_rating !== null
              ? formatNumber(selectedRunner.winning_rating - selectedRunner.today_rating, 2)
              : ""}
          </div>
          <div style={styles.todayCardSub}>Rated Price {formatPrice(selectedRunner.rated_price)}</div>
        </div>
      </div>

      <div style={styles.summaryGrid}>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Latest Run</div>
          <div style={styles.summaryValue}>{formatNumber(latestRunRating)}</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Last 3 Avg</div>
          <div style={styles.summaryValue}>{formatNumber(last3)}</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Last 5 Avg</div>
          <div style={styles.summaryValue}>{formatNumber(last5)}</div>
        </div>
        <div style={styles.summaryCard}>
          <div style={styles.summaryLabel}>Career Peak</div>
          <div style={styles.summaryValue}>{formatNumber(peak)}</div>
        </div>
      </div>

      <div style={styles.chartCard}>
        <div style={styles.sectionTitle}>Ratings History</div>
        {chartValues.length ? (
          <svg viewBox="0 0 420 90" preserveAspectRatio="none" style={styles.svg}>
            <polyline fill="none" stroke="currentColor" strokeWidth="2.5" points={polyline} />
          </svg>
        ) : (
          <div style={styles.noChart}>No ratings history available</div>
        )}
      </div>

      <div style={styles.formCard}>
        <div style={styles.sectionTitle}>Previous Runs</div>
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Date</th>
                <th style={styles.thLeft}>Track</th>
                <th style={styles.th}>R</th>
                <th style={styles.th}>Dist</th>
                <th style={styles.thLeft}>Cond</th>
                <th style={styles.th}>Bar</th>
                <th style={styles.thLeft}>Jockey</th>
                <th style={styles.thLeft}>Trainer</th>
                <th style={styles.th}>Fin</th>
                <th style={styles.th}>Margin</th>
                <th style={styles.th}>SP</th>
                <th style={styles.th}>Run</th>
                <th style={styles.th}>Race</th>
              </tr>
            </thead>
            <tbody>
              {orderedForm.map((row, index) => (
                <tr key={`${row.horse}-${row.race_date}-${row.track}-${row.race_no}-${index}`} style={styles.tr}>
                  <td style={styles.tdCenter}>{row.race_date || ""}</td>
                  <td style={styles.tdLeft}>{row.track || ""}</td>
                  <td style={styles.tdCenter}>{row.race_no ?? ""}</td>
                  <td style={styles.tdCenter}>{row.distance ?? ""}</td>
                  <td style={styles.tdLeft}>{row.track_condition || ""}</td>
                  <td style={styles.tdCenter}>{row.barrier ?? ""}</td>
                  <td style={styles.tdLeft}>{row.jockey || ""}</td>
                  <td style={styles.tdLeft}>{row.trainer || ""}</td>
                  <td style={styles.tdCenter}>{row.finish_pos || ""}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.margin)}</td>
                  <td style={styles.tdCenter}>{formatPrice(row.sp)}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.run_rating)}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.race_rating)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
    background: "#0b0e12",
    border: "1px solid #1a2129",
    borderRadius: 18,
    padding: 16,
  },
  emptyWrap: {
    background: "#0b0e12",
    border: "1px solid #1a2129",
    borderRadius: 18,
    padding: 24,
    minHeight: 280,
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    gap: 8,
  },
  emptyTitle: {
    color: "#ffffff",
    fontWeight: 800,
    fontSize: 20,
  },
  emptyText: {
    color: "#98a5b4",
    fontSize: 14,
  },
  topHeader: {
    display: "grid",
    gridTemplateColumns: "1fr 220px",
    gap: 16,
    alignItems: "stretch",
  },
  titleRow: {
    display: "flex",
    alignItems: "center",
    gap: 14,
  },
  numberBadge: {
    width: 48,
    height: 48,
    borderRadius: 12,
    background: "#131a22",
    border: "1px solid #293140",
    color: "#ffffff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 18,
    fontWeight: 800,
    flexShrink: 0,
  },
  horseName: {
    color: "#ffffff",
    fontSize: 24,
    fontWeight: 800,
    lineHeight: 1.1,
  },
  metaLine: {
    color: "#9aa8b8",
    fontSize: 13,
    marginTop: 4,
  },
  todayCard: {
    background: "#111821",
    border: "1px solid #1d2733",
    borderRadius: 14,
    padding: 14,
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    gap: 6,
  },
  todayCardLabel: {
    color: "#98a4b3",
    fontSize: 12,
    textTransform: "uppercase",
    letterSpacing: 0.6,
  },
  todayCardValue: {
    color: "#ffffff",
    fontSize: 24,
    fontWeight: 800,
  },
  todayCardSub: {
    color: "#c7d1dd",
    fontSize: 12,
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: 12,
  },
  summaryCard: {
    background: "#10151b",
    border: "1px solid #1b232d",
    borderRadius: 14,
    padding: 14,
  },
  summaryLabel: {
    color: "#95a4b5",
    fontSize: 12,
    marginBottom: 6,
  },
  summaryValue: {
    color: "#ffffff",
    fontSize: 22,
    fontWeight: 800,
  },
  chartCard: {
    background: "#10151b",
    border: "1px solid #1b232d",
    borderRadius: 14,
    padding: 14,
    color: "#f3f7fb",
  },
  sectionTitle: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: 800,
    marginBottom: 12,
  },
  svg: {
    width: "100%",
    height: 90,
    display: "block",
    opacity: 0.96,
  },
  noChart: {
    border: "1px dashed #2b3340",
    borderRadius: 12,
    height: 90,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#8d9bab",
    fontSize: 13,
  },
  formCard: {
    background: "#10151b",
    border: "1px solid #1b232d",
    borderRadius: 14,
    padding: 14,
  },
  tableWrap: {
    overflowX: "auto",
    border: "1px solid #182029",
    borderRadius: 12,
  },
  table: {
    width: "100%",
    minWidth: 1320,
    borderCollapse: "collapse",
    background: "#0f1318",
  },
  th: {
    padding: "11px 10px",
    textAlign: "center",
    color: "#c7d1dd",
    fontSize: 12,
    fontWeight: 700,
    background: "#111821",
    borderBottom: "1px solid #1c2430",
    whiteSpace: "nowrap",
  },
  thLeft: {
    padding: "11px 10px",
    textAlign: "left",
    color: "#c7d1dd",
    fontSize: 12,
    fontWeight: 700,
    background: "#111821",
    borderBottom: "1px solid #1c2430",
    whiteSpace: "nowrap",
  },
  tr: {
    borderBottom: "1px solid #171e27",
  },
  tdCenter: {
    padding: "11px 10px",
    textAlign: "center",
    color: "#edf2f7",
    fontSize: 13,
    whiteSpace: "nowrap",
  },
  tdLeft: {
    padding: "11px 10px",
    textAlign: "left",
    color: "#edf2f7",
    fontSize: 13,
    whiteSpace: "nowrap",
  },
};


