from pathlib import Path
from datetime import datetime

root = Path.cwd()

files = {
"src/state/edgeiqOsStore.tsx": r'''import { createContext, ReactNode, useContext, useMemo, useState } from "react";

export type EdgeiqSection = "HOME" | "TODAY" | "RACES" | "RESULTS" | "LAB" | "SETTINGS";

export type EdgeiqWorkspace =
  | "COMMAND"
  | "FIELD"
  | "MAP"
  | "MARKET"
  | "PERFORMANCE"
  | "CONDITIONS";

type EdgeiqOsState = {
  activeSection: EdgeiqSection;
  activeWorkspace: EdgeiqWorkspace;
  setActiveSection: (section: EdgeiqSection) => void;
  setActiveWorkspace: (workspace: EdgeiqWorkspace) => void;
};

const EdgeiqOsContext = createContext<EdgeiqOsState | null>(null);

export function EdgeiqOsProvider({ children }: { children: ReactNode }) {
  const [activeSection, setActiveSection] = useState<EdgeiqSection>("RACES");
  const [activeWorkspace, setActiveWorkspace] = useState<EdgeiqWorkspace>("COMMAND");

  const value = useMemo(
    () => ({
      activeSection,
      activeWorkspace,
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
''',

"src/components/workspaces/EdgeiqWorkspaceRouter.tsx": r'''import { ReactNode } from "react";
import { useEdgeiqOs } from "../../state/edgeiqOsStore";

type EdgeiqWorkspaceRouterProps = {
  commandWorkspace: ReactNode;
};

function PlaceholderWorkspace({ title, question }: { title: string; question: string }) {
  return (
    <div className="edgeiq-os-placeholder">
      <div className="edgeiq-os-placeholder__eyebrow">EDGEiQ OS WORKSPACE</div>
      <h1>{title}</h1>
      <p>{question}</p>
      <div className="edgeiq-os-placeholder__note">
        This workspace is reserved for the upcoming rebuild. Existing intelligence engines remain untouched.
      </div>
    </div>
  );
}

export function EdgeiqWorkspaceRouter({ commandWorkspace }: EdgeiqWorkspaceRouterProps) {
  const { activeSection, activeWorkspace } = useEdgeiqOs();

  if (activeSection === "HOME") {
    return <PlaceholderWorkspace title="HOME" question="What is happening today?" />;
  }

  if (activeSection === "TODAY") {
    return <PlaceholderWorkspace title="TODAY" question="Which races matter right now?" />;
  }

  if (activeSection === "RESULTS") {
    return <PlaceholderWorkspace title="RESULTS" question="Did reality match the projection?" />;
  }

  if (activeSection === "LAB") {
    return <PlaceholderWorkspace title="LAB" question="What happens if assumptions change?" />;
  }

  if (activeSection === "SETTINGS") {
    return <PlaceholderWorkspace title="SETTINGS" question="How should EDGEiQ OS behave for this user?" />;
  }

  if (activeWorkspace === "COMMAND") {
    return <>{commandWorkspace}</>;
  }

  const questions: Record<string, string> = {
    FIELD: "What do I know about every runner?",
    MAP: "How will this race unfold?",
    MARKET: "Where is the market wrong?",
    PERFORMANCE: "Why is this horse rated here?",
    CONDITIONS: "What external factors matter?",
  };

  return <PlaceholderWorkspace title={activeWorkspace} question={questions[activeWorkspace]} />;
}
'''
}

for file, content in files.items():
    path = root / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

shell = root / "src/components/shell/EdgeiqOsShell.tsx"
text = shell.read_text(encoding="utf-8")

if 'useEdgeiqOs' not in text:
    text = text.replace(
        'import { ReactNode, useEffect, useMemo, useState } from "react";',
        'import { ReactNode, useEffect, useMemo, useState } from "react";\nimport { useEdgeiqOs } from "../../state/edgeiqOsStore";'
    )

text = text.replace(
'''  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);''',
'''  const nextTheme = useMemo(() => (theme === "dark" ? "light" : "dark"), [theme]);
  const os = useEdgeiqOs();'''
)

text = text.replace(
'''          <button className={`edgeiq-os__nav-item ${activeSection === "HOME" ? "is-active" : ""}`}>HOME</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "TODAY" ? "is-active" : ""}`}>TODAY</button>''',
'''          <button className={`edgeiq-os__nav-item ${os.activeSection === "HOME" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("HOME")}>HOME</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "TODAY" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("TODAY")}>TODAY</button>'''
)

text = text.replace(
'''                className={`edgeiq-os__nav-sub ${activeWorkspace === workspace ? "is-active" : ""}`}
                type="button"
              >
                {workspace}''',
'''                className={`edgeiq-os__nav-sub ${os.activeSection === "RACES" && os.activeWorkspace === workspace ? "is-active" : ""}`}
                type="button"
                onClick={() => {
                  os.setActiveSection("RACES");
                  os.setActiveWorkspace(workspace);
                }}
              >
                {workspace}'''
)

text = text.replace(
'''          <button className={`edgeiq-os__nav-item ${activeSection === "RESULTS" ? "is-active" : ""}`}>RESULTS</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "LAB" ? "is-active" : ""}`}>LAB</button>
          <button className={`edgeiq-os__nav-item ${activeSection === "SETTINGS" ? "is-active" : ""}`}>SETTINGS</button>''',
'''          <button className={`edgeiq-os__nav-item ${os.activeSection === "RESULTS" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("RESULTS")}>RESULTS</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "LAB" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("LAB")}>LAB</button>
          <button className={`edgeiq-os__nav-item ${os.activeSection === "SETTINGS" ? "is-active" : ""}`} type="button" onClick={() => os.setActiveSection("SETTINGS")}>SETTINGS</button>'''
)

shell.write_text(text, encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
css_text = css.read_text(encoding="utf-8")
if ".edgeiq-os-placeholder" not in css_text:
    css_text += r'''

.edgeiq-os-placeholder {
  max-width: 920px;
  margin: 64px auto;
  padding: 48px;
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
}

.edgeiq-os-placeholder__eyebrow {
  color: var(--edgeiq-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.18em;
  margin-bottom: 18px;
}

.edgeiq-os-placeholder h1 {
  margin: 0 0 12px;
  color: var(--edgeiq-text);
  font-size: 42px;
  letter-spacing: -0.04em;
}

.edgeiq-os-placeholder p {
  margin: 0;
  color: var(--edgeiq-text-secondary);
  font-size: 19px;
}

.edgeiq-os-placeholder__note {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid var(--edgeiq-border-muted);
  color: var(--edgeiq-text-muted);
  font-size: 13px;
}
'''
    css.write_text(css_text, encoding="utf-8")

app = root / "src/App.tsx"
app_text = app.read_text(encoding="utf-8")
checkpoint = app.with_name(f"App_CHECKPOINT_BEFORE_EDGEIQ_OS_STORE_ROUTER_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsx")
checkpoint.write_text(app_text, encoding="utf-8")

if 'EdgeiqOsProvider' not in app_text:
    app_text = 'import { EdgeiqOsProvider } from "./state/edgeiqOsStore";\nimport { EdgeiqWorkspaceRouter } from "./components/workspaces/EdgeiqWorkspaceRouter";\n' + app_text

app_text = app_text.replace(
    '<EdgeiqOsShell><RaceIntelligenceScreen /></EdgeiqOsShell>',
    '<EdgeiqOsProvider><EdgeiqOsShell><EdgeiqWorkspaceRouter commandWorkspace={<RaceIntelligenceScreen />} /></EdgeiqOsShell></EdgeiqOsProvider>'
)

app.write_text(app_text, encoding="utf-8")

print("[EDGEIQ_OS_STORE_ROUTER] created app store")
print("[EDGEIQ_OS_STORE_ROUTER] created workspace router")
print("[EDGEIQ_OS_STORE_ROUTER] wired shell navigation")
print("[EDGEIQ_OS_STORE_ROUTER] wrapped app provider/router")
