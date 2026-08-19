from pathlib import Path

root = Path.cwd()
router = root / "src/components/workspaces/EdgeiqWorkspaceRouter.tsx"
text = router.read_text(encoding="utf-8")

if "function CommandWorkspaceFrame" not in text:
    text = text.replace(
'''function WorkspaceShell({ spec }: { spec: WorkspaceSpec }) {''',
'''function CommandWorkspaceFrame({ children }: { children: ReactNode }) {
  return (
    <div className="edgeiq-command-frame">
      <div className="edgeiq-command-frame__header">
        <div>
          <div className="edgeiq-command-frame__eyebrow">RACE COMMAND</div>
          <h1>Executive Race Briefing</h1>
          <p>What is this race telling me?</p>
        </div>
        <div className="edgeiq-command-frame__status">Live Intelligence</div>
      </div>

      <div className="edgeiq-command-frame__notice">
        Existing COMMAND intelligence is preserved here while the EDGEiQ OS executive briefing is rebuilt.
      </div>

      <div className="edgeiq-command-frame__legacy">
        {children}
      </div>
    </div>
  );
}

function WorkspaceShell({ spec }: { spec: WorkspaceSpec }) {'''
    )

text = text.replace(
'''  if (activeWorkspace === "COMMAND") {
    return <>{commandWorkspace}</>;
  }''',
'''  if (activeWorkspace === "COMMAND") {
    return <CommandWorkspaceFrame>{commandWorkspace}</CommandWorkspaceFrame>;
  }'''
)

router.write_text(text, encoding="utf-8")

css = root / "src/components/shell/edgeiqOsShell.css"
css_text = css.read_text(encoding="utf-8")

if ".edgeiq-command-frame" not in css_text:
    css_text += r'''

.edgeiq-command-frame {
  min-height: 100%;
  padding: 30px;
  background:
    linear-gradient(180deg, rgba(216, 184, 106, 0.055), transparent 260px),
    var(--edgeiq-bg);
}

.edgeiq-command-frame__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
  padding: 26px 28px;
  border: 1px solid var(--edgeiq-border);
  background: var(--edgeiq-panel);
  margin-bottom: 14px;
}

.edgeiq-command-frame__eyebrow {
  color: var(--edgeiq-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.edgeiq-command-frame h1 {
  margin: 0;
  color: var(--edgeiq-text);
  font-size: clamp(30px, 3vw, 48px);
  line-height: 0.95;
  letter-spacing: -0.055em;
}

.edgeiq-command-frame p {
  margin: 12px 0 0;
  color: var(--edgeiq-text-secondary);
  font-size: 18px;
}

.edgeiq-command-frame__status {
  border: 1px solid var(--edgeiq-border);
  color: var(--edgeiq-success);
  background: var(--edgeiq-bg-secondary);
  padding: 9px 12px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  white-space: nowrap;
}

.edgeiq-command-frame__notice {
  border: 1px solid var(--edgeiq-border-muted);
  background: var(--edgeiq-bg-secondary);
  color: var(--edgeiq-text-muted);
  padding: 12px 16px;
  font-size: 12px;
  letter-spacing: 0.04em;
  margin-bottom: 18px;
}

.edgeiq-command-frame__legacy {
  min-width: 0;
}
'''
    css.write_text(css_text, encoding="utf-8")

print("[EDGEIQ_OS_COMMAND_FRAME] COMMAND wrapped in OS executive frame")
