from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_RUNNER_SELECTOR_AND_SIGNAL_DOTS_EXACT_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

def must_replace(old, new):
    global s
    if old not in s:
        raise SystemExit(f"[PATCH FAILED] anchor not found:\n{old}")
    s = s.replace(old, new, 1)

# 1) Add professional dot helper after commandQuickItemStyle block if not already present
anchor = '''  const commandQuickItemStyle = (tone: string): React.CSSProperties => ({'''
idx = s.find(anchor)
if idx == -1:
    raise SystemExit("[PATCH FAILED] commandQuickItemStyle anchor not found")

helper = '''
  const intelligenceDotStyle = (colour: string): React.CSSProperties => ({
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: colour,
    flexShrink: 0,
    boxShadow: `0 0 0 1px ${colour}55`,
  });

  const runnerSelectorButtonStyle = (active: boolean): React.CSSProperties => ({
    border: active ? "1px solid #38bdf8" : "1px solid rgba(148,163,184,.22)",
    background: active ? "rgba(14,165,233,.16)" : "rgba(2,6,23,.72)",
    color: active ? "#e0f2fe" : "#cbd5e1",
    padding: "8px 11px",
    borderRadius: 8,
    cursor: "pointer",
    whiteSpace: "nowrap",
    fontWeight: 850,
    fontSize: 11,
    letterSpacing: ".01em",
    flexShrink: 0,
  });
'''
if "const intelligenceDotStyle =" not in s:
    # Insert after commandQuickItemStyle function block by finding the next "  const " after it.
    next_const = s.find("\n  const ", idx + len(anchor))
    if next_const == -1:
        raise SystemExit("[PATCH FAILED] cannot find insertion point after commandQuickItemStyle")
    s = s[:next_const] + helper + s[next_const:]

# 2) Insert runner selector immediately after Selected Runner title block
old = '''          <div style={subsectionTitleStyle}>
            <span>Selected Runner EDGEiQ Decision Engine</span>
            <em style={{ color: "#94a3b8", fontStyle: "normal", fontSize: 11, textTransform: "none", letterSpacing: "normal" }}>
              Why the selected runner is rated where it is
            </em>
          </div>
          <div style={compactValueGridStyle(5)}>'''

new = '''          <div style={subsectionTitleStyle}>
            <span>Selected Runner EDGEiQ Decision Engine</span>
            <em style={{ color: "#94a3b8", fontStyle: "normal", fontSize: 11, textTransform: "none", letterSpacing: "normal" }}>
              Why the selected runner is rated where it is
            </em>
          </div>

          <div style={{ display: "grid", gap: 7, marginBottom: 14 }}>
            <div style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900, letterSpacing: ".08em", textTransform: "uppercase" }}>
              Runner Selector
            </div>
            <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8 }}>
              {activeRaceRows.map((runner, idx) => {
                const key = runnerKey(runner.row);
                const active = selectedKey === key;
                return (
                  <button
                    key={`command-runner-selector-${key}-${idx}`}
                    onClick={() => setSelectedKey(key)}
                    style={runnerSelectorButtonStyle(active)}
                    title={`${runner.row.saddlecloth || idx + 1}. ${horse(runner.row)}`}
                  >
                    #{runner.row.saddlecloth || idx + 1} {horse(runner.row)}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={compactValueGridStyle(5)}>'''

must_replace(old, new)

# 3) Replace positive row layout with green dot layout
old = '''                    <div key={`command-support-${index}-${item.factor}`} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                      <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{item.factor}</span>
                      <span style={{ color: "#5eead4", fontWeight: 900, fontSize: 11 }}>{item.value || "N/A"}</span>
                    </div>'''

new = '''                    <div key={`command-support-${index}-${item.factor}`} style={{ display: "grid", gridTemplateColumns: "8px 1fr auto", gap: 10, alignItems: "center" }}>
                      <div style={intelligenceDotStyle("#22c55e")} />
                      <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{item.factor}</span>
                      <span style={{ color: "#5eead4", fontWeight: 900, fontSize: 11 }}>{item.value || "N/A"}</span>
                    </div>'''

must_replace(old, new)

# 4) Replace risk row layout with red dot layout
old = '''                    <div key={`command-risk-${index}-${item.factor}`} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                      <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{item.factor}</span>
                      <span style={{ color: "#f87171", fontWeight: 900, fontSize: 11 }}>{item.value || "N/A"}</span>
                    </div>'''

new = '''                    <div key={`command-risk-${index}-${item.factor}`} style={{ display: "grid", gridTemplateColumns: "8px 1fr auto", gap: 10, alignItems: "center" }}>
                      <div style={intelligenceDotStyle("#ef4444")} />
                      <span style={{ color: "#eaf2ff", fontWeight: 900, fontSize: 11 }}>{item.factor}</span>
                      <span style={{ color: "#f87171", fontWeight: 900, fontSize: 11 }}>{item.value || "N/A"}</span>
                    </div>'''

must_replace(old, new)

p.write_text(s, encoding="utf-8")

print("[RUNNER_SELECTOR_AND_SIGNAL_DOTS_EXACT_PATCH] COMPLETE")
print(f"checkpoint={checkpoint}")
