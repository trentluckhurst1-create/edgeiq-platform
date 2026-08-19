import React from "react";
import { Runner } from "../types/racing";
import { formatPct, formatPrice } from "../utils/format";

interface Props {
  runners: Runner[];
}

export default function RatedPrices({ runners }: Props) {
  const sorted = [...runners].sort((a, b) => a.rated_price - b.rated_price);

  return (
    <div style={styles.wrap}>
      <div style={styles.title}>Rated Prices</div>

      <div style={styles.header}>
        <div>Horse</div>
        <div>Rating</div>
        <div>Rated</div>
        <div>Market</div>
        <div>Overlay</div>
      </div>

      {sorted.map((r, i) => (
        <div key={`${r.horse}-${i}`} style={styles.row}>
          <div>{r.horse}</div>
          <div>{r.rating.toFixed(1)}</div>
          <div style={{ color: "#4ade80", fontWeight: 700 }}>
            {formatPrice(r.rated_price)}
          </div>
          <div>{formatPrice(r.market_price)}</div>
          <div style={{ color: (r.overlay_pct ?? 0) > 0 ? "#4ade80" : "#f87171" }}>
            {formatPct(r.overlay_pct ?? 0)}
          </div>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    padding: 16
  },
  title: {
    fontSize: 18,
    fontWeight: 800,
    marginBottom: 14
  },
  header: {
    display: "grid",
    gridTemplateColumns: "1.4fr 80px 80px 80px 90px",
    gap: 8,
    padding: "8px 10px",
    borderBottom: "1px solid #253041",
    color: "#94a3b8",
    fontSize: 12,
    textTransform: "uppercase"
  },
  row: {
    display: "grid",
    gridTemplateColumns: "1.4fr 80px 80px 80px 90px",
    gap: 8,
    padding: "10px",
    borderBottom: "1px solid #18212e",
    alignItems: "center"
  }
};


