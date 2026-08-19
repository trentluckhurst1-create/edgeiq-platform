from pathlib import Path

path = Path("src/state/edgeiqOsStore.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'import { createContext, ReactNode, useContext, useMemo, useState } from "react";',
'import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";'
)

text = text.replace(
'''export function EdgeiqOsProvider({ children }: { children: ReactNode }) {
  const [activeSection, setActiveSection] = useState<EdgeiqSection>("RACES");
  const [activeWorkspace, setActiveWorkspace] = useState<EdgeiqWorkspace>("COMMAND");''',
'''const validSections: EdgeiqSection[] = ["HOME", "TODAY", "RACES", "RESULTS", "LAB", "SETTINGS"];
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

  useEffect(() => {
    window.localStorage.setItem("edgeiq-os-section", activeSection);
  }, [activeSection]);

  useEffect(() => {
    window.localStorage.setItem("edgeiq-os-workspace", activeWorkspace);
  }, [activeWorkspace]);'''
)

path.write_text(text, encoding="utf-8")
print("[EDGEIQ_OS_NAV_PERSISTENCE] section/workspace restore added")
