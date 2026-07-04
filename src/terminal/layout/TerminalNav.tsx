import { EdgeTabKey, EDGEIQ_TABS } from "./terminalTabs";

type Props = {
  activeTab: EdgeTabKey;
  onChange: (tab: EdgeTabKey) => void;
};

export default function TerminalNav({
  activeTab,
  onChange,
}: Props) {
  return (
    <div className="edgeiq-terminal-nav">
      {EDGEIQ_TABS.map((tab) => (
        <button
          key={tab}
          className={
            activeTab === tab
              ? "edgeiq-terminal-tab active"
              : "edgeiq-terminal-tab"
          }
          onClick={() => onChange(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
