export type RunnerWorkspaceMode = "profile" | "compare" | "results" | "dna" | "market" | "map";

type RunnerTabsProps = {
  mode: RunnerWorkspaceMode;
  setMode: (mode: RunnerWorkspaceMode) => void;
};

export function RunnerTabs({ mode, setMode }: RunnerTabsProps) {
  const tabs: RunnerWorkspaceMode[] = ["profile", "compare", "results", "dna", "market", "map"];

  return (
    <nav className="eiq-runner-tabs">
      {tabs.map((tab) => (
        <button key={tab} type="button" className={mode === tab ? "is-active" : ""} onClick={() => setMode(tab)}>
          {tab.toUpperCase()}
        </button>
      ))}
    </nav>
  );
}
