from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if old not in text:
        raise RuntimeError(f"Expected block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_app_navigation() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "AppNavigation.tsx"
    old = '''export type GlobalSection = "meetings" | "results" | "lab" | "settings";

type AppNavigationProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
};

const navItems: Array<{ key: GlobalSection; label: string }> = [
  { key: "meetings", label: "MEETINGS" },
  { key: "results", label: "RESULTS" },
  { key: "lab", label: "LAB" },
  { key: "settings", label: "SETTINGS" },
];'''
    new = '''export type GlobalSection =
  | "home"
  | "meetings"
  | "race"
  | "field"
  | "formGuide"
  | "performance"
  | "epi"
  | "map"
  | "market"
  | "overview"
  | "insights"
  | "results"
  | "lab"
  | "compare"
  | "review"
  | "settings";

type AppNavigationProps = {
  activeSection: GlobalSection;
  onSectionChange: (section: GlobalSection) => void;
};

const navItems: Array<{ key: GlobalSection; label: string }> = [
  { key: "home", label: "HOME" },
  { key: "meetings", label: "MEETINGS" },
  { key: "race", label: "RACE" },
  { key: "field", label: "FIELD" },
  { key: "formGuide", label: "FORM GUIDE" },
  { key: "performance", label: "PERFORMANCE" },
  { key: "epi", label: "EPI" },
  { key: "map", label: "MAP" },
  { key: "market", label: "MARKET" },
  { key: "overview", label: "OVERVIEW" },
  { key: "insights", label: "INSIGHTS" },
  { key: "results", label: "RESULTS" },
  { key: "lab", label: "LAB" },
  { key: "compare", label: "COMPARE" },
  { key: "review", label: "REVIEW" },
  { key: "settings", label: "SETTINGS" },
];'''
    replace_once(path, old, new)


def patch_race_workspace() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
    replace_once(
        path,
        'type RaceTab = typeof tabs[number];',
        'export type RaceTab = typeof tabs[number];',
    )
    replace_once(
        path,
        '''  onBackToMeeting: () => void;
  onOpenRunner: (index: number) => void;
  onOpenRace?: (race: ThreeDayRace) => void;
};''',
        '''  onBackToMeeting: () => void;
  onOpenRunner: (index: number) => void;
  onOpenRace?: (race: ThreeDayRace) => void;
  initialTab?: RaceTab;
};''',
    )
    replace_once(
        path,
        '''  selectedRaceKey,
  onBackToMeeting,
  onOpenRunner,
  onOpenRace,
}: RaceWorkspaceProps) {
  const [tab, setTab] = useState<RaceTab>("FORM GUIDE");''',
        '''  selectedRaceKey,
  onBackToMeeting,
  onOpenRunner,
  onOpenRace,
  initialTab = "FORM GUIDE",
}: RaceWorkspaceProps) {
  const [tab, setTab] = useState<RaceTab>(initialTab);''',
    )
    replace_once(
        path,
        '''  const official = raceBook?.official ?? {};

  useEffect(() => {''',
        '''  const official = raceBook?.official ?? {};

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  useEffect(() => {''',
    )


def patch_race_file() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "RaceFileV3.tsx"
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace(
        'import { RaceWorkspace } from "./components/RaceWorkspace";',
        'import { RaceWorkspace, type RaceTab } from "./components/RaceWorkspace";',
        1,
    )
    old = '''type WorkbenchMode = RunnerWorkspaceMode;
type ViewLevel = "meetings" | "meeting" | "race" | "runner";
type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";'''
    new = '''type WorkbenchMode = RunnerWorkspaceMode;
type ViewLevel = "meetings" | "meeting" | "race" | "runner";
type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";

const raceTabBySection: Partial<Record<GlobalSection, RaceTab>> = {
  race: "OVERVIEW",
  field: "FORM GUIDE",
  formGuide: "FORM GUIDE",
  performance: "EPI",
  epi: "EPI",
  map: "MAP",
  market: "MARKET",
  overview: "OVERVIEW",
  insights: "INSIGHTS",
  review: "REVIEW",
};

const runnerModeBySection: Partial<Record<GlobalSection, RunnerWorkspaceMode>> = {
  compare: "compare",
};'''
    text = text.replace(old, new, 1)

    old = '''  function openSection(section: GlobalSection) {
    setActiveSection(section);
    if (section === "meetings") setViewLevel("meetings");
  }'''
    new = '''  function openSection(section: GlobalSection) {
    setActiveSection(section);
    if (section === "home" || section === "meetings") {
      setViewLevel("meetings");
      return;
    }
    if (section === "results" || section === "lab" || section === "settings") return;
    const runnerMode = runnerModeBySection[section];
    if (runnerMode) {
      setMode(runnerMode);
      setViewLevel("runner");
      return;
    }
    if (raceTabBySection[section]) {
      if (!selectedRace && selectedMeeting?.races?.[0]) {
        setSelectedRace(selectedMeeting.races[0]);
      }
      setViewLevel("race");
    }
  }'''
    text = text.replace(old, new, 1)

    old = '''  const shellTitle =
    activeSection === "results"
      ? "Global Results"
      : activeSection === "lab"
        ? "EDGEIQ LAB"
        : activeSection === "settings"
          ? "Settings"
          : viewLevel === "runner"'''
    new = '''  const shellTitle =
    activeSection === "home"
      ? "EDGEiQ"
      : activeSection === "results"
        ? "Global Results"
        : activeSection === "lab"
          ? "EDGEIQ LAB"
          : activeSection === "settings"
            ? "Settings"
            : viewLevel === "runner"'''
    text = text.replace(old, new, 1)

    old = '''  const shellMeta =
    activeSection === "meetings"
      ? viewLevel === "meetings"
        ? "Three-day governed meeting window"'''
    new = '''  const shellMeta =
    activeSection === "home"
      ? "Professional Racing Intelligence Operating System"
      : activeSection === "meetings"
        ? viewLevel === "meetings"
          ? "Three-day governed meeting window"'''
    text = text.replace(old, new, 1)

    old = '''        <RaceWorkspace
          raceBook={activeFile.raceBook}
          field={activeFile.field}
          selectedRunnerIndex={selectedRunnerIndex}
          clean={clean}
          weight={weight}
          market={market}
          meetingRaces={selectedMeeting?.races ?? []}
          selectedRaceKey={selectedRace?.raceKey ?? activeFile.raceBook.official.raceKey}
          onBackToMeeting={() => setViewLevel("meeting")}'''
    new = '''        <RaceWorkspace
          raceBook={activeFile.raceBook}
          field={activeFile.field}
          selectedRunnerIndex={selectedRunnerIndex}
          clean={clean}
          weight={weight}
          market={market}
          meetingRaces={selectedMeeting?.races ?? []}
          selectedRaceKey={selectedRace?.raceKey ?? activeFile.raceBook.official.raceKey}
          initialTab={raceTabBySection[activeSection] ?? "FORM GUIDE"}
          onBackToMeeting={() => setViewLevel("meeting")}'''
    text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_app_navigation()
    patch_race_workspace()
    patch_race_file()
    print("Applied EDGEiQ full product navigation foundation v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
