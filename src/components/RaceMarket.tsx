import { normaliseHorse } from "../lib/normalise";
import React, { useMemo } from "react";
import type { RaceMarketRow } from "../types/racing";

type Props = {
  rows: RaceMarketRow[];
  selectedHorse: string | null;
  onSelectHorse: (horse: string) => void;
};

function formatNumber(value: number | null, decimals = 2): string {
  if (value === null || value === undefined) return "";
  return value.toFixed(decimals);
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "";
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(2)}%`;
}

function formatPrice(value: number | null): string {
  if (value === null || value === undefined || value <= 0) return "";
  return `$${value.toFixed(2)}`;
}

function getHorseNo(row: RaceMarketRow): number {
  return row.horse_no ?? 9999;
}

export default function RaceMarket({
  rows,
  selectedHorse,
  onSelectHorse,
}: Props) {
  const orderedRows = useMemo(() => {
    return [...rows].sort((a, b) => {
      const noDiff = getHorseNo(a) - getHorseNo(b);
      if (noDiff !== 0) return noDiff;
      return a.horse.localeCompare(b.horse);
    });
  }, [rows]);

  return (
    <div style={styles.wrap}>
      <div style={styles.header}>
        <div style={styles.title}>Race Field</div>
        <div style={styles.subTitle}>
          Click any runner to open full historical form and ratings
        </div>
      </div>

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>No</th>
              <th style={styles.thLeft}>Horse</th>
              <th style={styles.th}>Bar</th>
              <th style={styles.thLeft}>Jockey</th>
              <th style={styles.thLeft}>Trainer</th>
              <th style={styles.th}>Today</th>
              <th style={styles.th}>Win Fig</th>
              <th style={styles.th}>Gap</th>
              <th style={styles.th}>Rated %</th>
              <th style={styles.th}>Rated Price</th>
            </tr>
          </thead>
          <tbody>
            {orderedRows.map((row) => {
              const isSelected =
                normaliseHorse(selectedHorse) === normaliseHorse(row.horse);

              return (
                <tr
                  key={`${row.race_date}-${row.track}-${row.race_no}-${row.horse}`}
                  style={{
                    ...styles.tr,
                    ...(isSelected ? styles.trSelected : {}),
                  }}
                  onClick={() => onSelectHorse(row.horse)}
                >
                  <td style={styles.tdCenter}>
                    {row.horse_no === null ? "" : row.horse_no}
                  </td>
                  <td style={styles.tdHorse}>{row.horse}</td>
                  <td style={styles.tdCenter}>
                    {row.barrier === null ? "" : row.barrier}
                  </td>
                  <td style={styles.tdLeft}>{row.jockey || ""}</td>
                  <td style={styles.tdLeft}>{row.trainer || ""}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.today_rating)}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.winning_rating)}</td>
                  <td style={styles.tdCenter}>{formatNumber(row.rating_gap)}</td>
                  <td style={styles.tdCenter}>
                    {formatPercent(row.rated_probability)}
                  </td>
                  <td style={styles.tdCenter}>{formatPrice(row.rated_price)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    background: "#0b0e12",
    border: "1px solid #1a2129",
    borderRadius: 18,
    padding: 16,
  },
  header: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  title: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: 800,
    letterSpacing: 0.2,
  },
  subTitle: {
    color: "#96a3b3",
    fontSize: 12,
  },
  tableWrap: {
    overflowX: "auto",
    border: "1px solid #182029",
    borderRadius: 14,
  },
  table: {
    width: "100%",
    minWidth: 1040,
    borderCollapse: "collapse",
    background: "#0f1318",
  },
  th: {
    padding: "12px 10px",
    textAlign: "center",
    color: "#c7d1dd",
    fontSize: 12,
    fontWeight: 700,
    background: "#111821",
    borderBottom: "1px solid #1c2430",
    whiteSpace: "nowrap",
  },
  thLeft: {
    padding: "12px 10px",
    textAlign: "left",
    color: "#c7d1dd",
    fontSize: 12,
    fontWeight: 700,
    background: "#111821",
    borderBottom: "1px solid #1c2430",
    whiteSpace: "nowrap",
  },
  tr: {
    cursor: "pointer",
    borderBottom: "1px solid #171e27",
    transition: "background 0.15s ease",
  },
  trSelected: {
    background: "#17212b",
  },
  tdCenter: {
    padding: "12px 10px",
    textAlign: "center",
    color: "#edf2f7",
    fontSize: 13,
    whiteSpace: "nowrap",
  },
  tdLeft: {
    padding: "12px 10px",
    textAlign: "left",
    color: "#edf2f7",
    fontSize: 13,
    whiteSpace: "nowrap",
  },
  tdHorse: {
    padding: "12px 10px",
    textAlign: "left",
    color: "#ffffff",
    fontSize: 13,
    fontWeight: 700,
    whiteSpace: "nowrap",
  },
};



