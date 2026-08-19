import React from "react";
import type { TabKey } from "../types/racing";

type Props = {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
};

const tabs: Array<{ key: TabKey; label: string; sub: string }> = [
  { key: "execution", label: "Execution", sub: "Calibrated board" },
  { key: "market_tape", label: "Market Tape", sub: "Steam / drift" },
  { key: "ratings", label: "Ratings", sub: "Model price" },
  { key: "form", label: "Form", sub: "Runner history" },
  { key: "speed_map", label: "Speed Map", sub: "Race shape" },
  { key: "intelligence", label: "Intelligence", sub: "Gear / stewards" },
  { key: "performance", label: "Performance", sub: "Model audit" },
  { key: "bets", label: "Bets", sub: "Execution log" },
];

export default function Tabs({ activeTab, onChange }: Props) {
  return (
    <div style={styles.wrap}>
      {tabs.map((tab) => {
        const isActive = tab.key === activeTab;

        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            style={{
              ...styles.tab,
              ...(isActive ? styles.tabActive : {}),
            }}
          >
            <span style={styles.label}>{tab.label}</span>
            <span style={styles.sub}>{tab.sub}</span>
          </button>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
    alignItems: "stretch",
    padding: "8px 0",
  },
  tab: {
    border: "1px solid rgba(42, 58, 77, 0.95)",
    background: "linear-gradient(180deg, #101821 0%, #0b1118 100%)",
    color: "#aab7c6",
    borderRadius: 12,
    padding: "9px 13px",
    minWidth: 118,
    minHeight: 54,
    fontSize: 12,
    fontWeight: 800,
    cursor: "pointer",
    textAlign: "left",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tabActive: {
    background: "linear-gradient(180deg, rgba(16,185,129,0.22) 0%, rgba(10,18,25,1) 100%)",
    color: "#ffffff",
    borderColor: "rgba(16, 185, 129, 0.85)",
    boxShadow: "0 0 0 1px rgba(16,185,129,0.18), 0 0 18px rgba(16,185,129,0.10)",
  },
  label: {
    display: "block",
    fontSize: 12,
    lineHeight: "15px",
  },
  sub: {
    display: "block",
    marginTop: 4,
    fontSize: 9,
    lineHeight: "11px",
    color: "#7f8da0",
    fontWeight: 700,
    letterSpacing: "0.05em",
  },
};
