import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

export type EdgeiqSection = "HOME" | "TODAY" | "RACES" | "RESULTS" | "LAB" | "SETTINGS";

export type EdgeiqWorkspace =
  | "COMMAND"
  | "FIELD"
  | "MAP"
  | "MARKET"
  | "PERFORMANCE"
  | "CONDITIONS";

type EdgeiqRaceContext = {
  meeting: string;
  race: string;
  distance: string;
  track: string;
  rail: string;
  jump: string;
};

type EdgeiqOsState = {
  activeSection: EdgeiqSection;
  activeWorkspace: EdgeiqWorkspace;
  raceContext: EdgeiqRaceContext;
  setActiveSection: (section: EdgeiqSection) => void;
  setActiveWorkspace: (workspace: EdgeiqWorkspace) => void;
};

const EdgeiqOsContext = createContext<EdgeiqOsState | null>(null);

const validSections: EdgeiqSection[] = ["HOME", "TODAY", "RACES", "RESULTS", "LAB", "SETTINGS"];
const validWorkspaces: EdgeiqWorkspace[] = ["COMMAND", "FIELD", "MAP", "MARKET", "PERFORMANCE", "CONDITIONS"];

function readStoredSection(): EdgeiqSection {
  const stored = window.localStorage.getItem("edgeiq-os-section");
  return validSections.includes(stored as EdgeiqSection) ? (stored as EdgeiqSection) : "RACES";
}

function readStoredWorkspace(): EdgeiqWorkspace {
  const stored = window.localStorage.getItem("edgeiq-os-workspace");
  return validWorkspaces.includes(stored as EdgeiqWorkspace) ? (stored as EdgeiqWorkspace) : "COMMAND";
}

export function EdgeiqOsProvider({ children }: { children: ReactNode }) {
  const [activeSection, setActiveSection] = useState<EdgeiqSection>(readStoredSection);
  const [activeWorkspace, setActiveWorkspace] = useState<EdgeiqWorkspace>(readStoredWorkspace);

  const raceContext: EdgeiqRaceContext = {
    meeting: "Current Meeting",
    race: "Selected Race",
    distance: "Race Distance",
    track: "Track Condition",
    rail: "Rail Position",
    jump: "Jump Countdown",
  };

  useEffect(() => {
    window.localStorage.setItem("edgeiq-os-section", activeSection);
  }, [activeSection]);

  useEffect(() => {
    window.localStorage.setItem("edgeiq-os-workspace", activeWorkspace);
  }, [activeWorkspace]);

  const value = useMemo(
    () => ({
      activeSection,
      activeWorkspace,
      raceContext,
      setActiveSection,
      setActiveWorkspace,
    }),
    [activeSection, activeWorkspace]
  );

  return <EdgeiqOsContext.Provider value={value}>{children}</EdgeiqOsContext.Provider>;
}

export function useEdgeiqOs() {
  const context = useContext(EdgeiqOsContext);

  if (!context) {
    throw new Error("useEdgeiqOs must be used inside EdgeiqOsProvider");
  }

  return context;
}

export type { EdgeiqRaceContext };
