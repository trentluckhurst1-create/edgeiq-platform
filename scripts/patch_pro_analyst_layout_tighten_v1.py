from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_PRO_ANALYST_LAYOUT_TIGHTEN_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

# Ensure professional dot helper exists
if "const intelligenceDotStyle =" not in s:
    anchor = '''  const miniValueStyle: React.CSSProperties = {'''
    pos = s.find(anchor)
    if pos == -1:
        raise SystemExit("[PATCH FAILED] miniValueStyle anchor not found")

    helper = '''  const intelligenceDotStyle = (color: string): React.CSSProperties => ({
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: color,
    boxShadow: `0 0 8px ${color}`,
    flexShrink: 0,
  });

'''
    s = s[:pos] + helper + s[pos:]

# Tighten hero grid proportions
s = s.replace('gridTemplateColumns: "220px 1fr 1fr"', 'gridTemplateColumns: "190px 1fr 1fr"', 1)
s = s.replace('minHeight: 146', 'minHeight: 118', 1)
s = s.replace('fontSize: 48', 'fontSize: 42', 1)

# Tighten positive/risk signal cards only in the score block
s = s.replace('              <div style={{ ...valueTileStyle, padding: 12 }}>\n                <span style={{ ...miniLabelStyle, color: "#86efac" }}>Positive Signals</span>', '              <div style={{ ...valueTileStyle, padding: 10 }}>\n                <span style={{ ...miniLabelStyle, color: "#86efac" }}>Positive Signals</span>', 1)
s = s.replace('              <div style={{ ...valueTileStyle, padding: 12 }}>\n                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>Risk Signals</span>', '              <div style={{ ...valueTileStyle, padding: 10 }}>\n                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>Risk Signals</span>', 1)
s = s.replace('display: "grid", gap: 7, marginTop: 10', 'display: "grid", gap: 5, marginTop: 7', 2)

# Add runner selector ribbon above selected runner decision engine, if not already present
if "COMMAND RUNNER SELECTOR" not in s:
    anchor = '''        <section style={breakdownCardStyle}>
          <div style={subsectionTitleStyle}>
            <span>Selected Runner EDGEiQ Decision Engine</span>'''
    insert = '''        <section style={breakdownCardStyle}>
          <div style={{ display: "grid", gap: 7, marginBottom: 13 }}>
            <div style={{ color: "#94a3b8", fontSize: 10.5, fontWeight: 900, letterSpacing: ".08em", textTransform: "uppercase" }}>
              COMMAND RUNNER SELECTOR
            </div>
            <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 6 }}>
              {activeRaceRows.map((runner, idx) => {
                const key = String(runner.row.race_key || "") + "_" + String(runner.row.horse || runner.row.runner || runner.row.runner_name || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
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

          <div style={subsectionTitleStyle}>
            <span>Selected Runner EDGEiQ Decision Engine</span>'''
    if anchor not in s:
        raise SystemExit("[PATCH FAILED] selected runner section anchor not found")
    s = s.replace(anchor, insert, 1)

p.write_text(s, encoding="utf-8")
print("[PRO_ANALYST_LAYOUT_TIGHTEN] COMPLETE")
print(f"checkpoint={checkpoint}")
