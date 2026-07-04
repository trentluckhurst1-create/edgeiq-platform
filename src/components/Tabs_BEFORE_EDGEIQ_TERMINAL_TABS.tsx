import React from "react";
import type { TabKey } from "../types/racing";

type Props = {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
};

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: "worksheet", label: "Worksheet" },
  { key: "performance", label: "Performance" },
  { key: "ratings", label: "Ratings" },
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
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  tab: {
    border: "1px solid #243040",
    background: "#0f141b",
    color: "#c7d1dd",
    borderRadius: 12,
    padding: "10px 16px",
    fontSize: 13,
    fontWeight: 700,
    cursor: "pointer",
  },
  tabActive: {
    background: "#182331",
    color: "#ffffff",
    borderColor: "#39506b",
  },
};


