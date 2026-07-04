from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_RUNNER_SELECTOR_V1_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

def must_replace(old, new):
    global s
    if old not in s:
        raise SystemExit(f"[PATCH FAILED]\\n{old[:500]}")
    s = s.replace(old, new, 1)

anchor = '''
          <div style={panelStyle}>
            <h3 style={sectionHeadingStyle}>Selected Runner EDGEiQ Decision Engine</h3>
'''

insert = '''
          <div style={panelStyle}>
            <h3 style={sectionHeadingStyle}>Runners</h3>

            <div
              style={{
                display: "flex",
                gap: 8,
                overflowX: "auto",
                paddingBottom: 6,
                marginBottom: 16,
              }}
            >
              {activeRows.map((runner, idx) => {
                const isSelected =
                  selected?.row?.horse === runner.row.horse &&
                  selected?.row?.race_key === runner.row.race_key;

                return (
                  <button
                    key={`${runner.row.race_key}_${runner.row.horse}_${idx}`}
                    onClick={() => setSelectedRunnerIndex(idx)}
                    style={{
                      border: isSelected
                        ? "1px solid #38bdf8"
                        : "1px solid rgba(148,163,184,.25)",
                      background: isSelected
                        ? "rgba(56,189,248,.15)"
                        : "rgba(15,23,42,.85)",
                      color: isSelected
                        ? "#e0f2fe"
                        : "#cbd5e1",
                      borderRadius: 8,
                      padding: "8px 12px",
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                      fontSize: 11,
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    #{runner.row.saddlecloth || idx + 1}
                    {" "}
                    {runner.row.horse}
                  </button>
                );
              })}
            </div>

            <h3 style={sectionHeadingStyle}>Selected Runner EDGEiQ Decision Engine</h3>
'''

must_replace(anchor, insert)

p.write_text(s, encoding="utf-8")

print("[RUNNER_SELECTOR_UI_V1] COMPLETE")
print(f"checkpoint={checkpoint}")
