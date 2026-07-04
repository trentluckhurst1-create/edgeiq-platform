from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_CUSTOMER_INTELLIGENCE_WIRE_V1_20260623.tsx")
checkpoint.parent.mkdir(exist_ok=True)
checkpoint.write_text(s, encoding="utf-8")

def must_replace(old, new):
    global s
    if old not in s:
        raise SystemExit(f"[PATCH FAILED] anchor not found:\n{old[:500]}")
    s = s.replace(old, new, 1)

must_replace(
'''  intelligenceScore: "/data/edgeiq_live_intelligence_score_v1.csv",
};''',
'''  intelligenceScore: "/data/edgeiq_live_intelligence_score_v1.csv",
  customerIntelligence: "/data/edgeiq_customer_intelligence_terminal_feed_v1.csv",
};'''
)

must_replace(
'''  limited?: Row;''',
'''  limited?: Row;
  customerIntel?: Row;'''
)

must_replace(
'''  const [limitedDataRows, setLimitedDataRows] = useState<Row[]>([]);''',
'''  const [limitedDataRows, setLimitedDataRows] = useState<Row[]>([]);
  const [customerIntelligenceRows, setCustomerIntelligenceRows] = useState<Row[]>([]);'''
)

must_replace(
'''      const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limitedData, intelligenceScore] = await Promise.all([''',
'''      const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limitedData, intelligenceScore, customerIntelligence] = await Promise.all(['''
)

must_replace(
'''        loadCsv(FILES.intelligenceScore),
      ]);''',
'''        loadCsv(FILES.intelligenceScore),
        loadCsv(FILES.customerIntelligence),
      ]);'''
)

must_replace(
'''      setLimitedDataRows(limitedData);''',
'''      setLimitedDataRows(limitedData);
      setCustomerIntelligenceRows(customerIntelligence);'''
)

must_replace(
'''      const limited = findSidecar(limitedDataRows, row);''',
'''      const limited = findSidecar(limitedDataRows, row);
      const customerIntel = findSidecar(customerIntelligenceRows, row);'''
)

must_replace(
'''      return { row, runnerIntel, v8, bet, rel, drawer, dna, explainability, connection, limited, intel, factorRows };''',
'''      return { row, runnerIntel, v8, bet, rel, drawer, dna, explainability, connection, limited, intel, customerIntel, factorRows };'''
)

must_replace(
'''  }, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows]);''',
'''  }, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows, customerIntelligenceRows]);'''
)

must_replace(
'''  const selectedExplainability = selected?.explainability;''',
'''  const selectedExplainability = selected?.explainability;
  const selectedCustomerIntel = selected?.customerIntel;
  const selectedEdgeiqScore = selected ? firstText(selectedCustomerIntel, ["edgeiq_score"], "--") : "--";
  const selectedEdgeiqBand = selected ? firstText(selectedCustomerIntel, ["edgeiq_band"], "--") : "--";
  const selectedEdgeiqVerdict = selected ? firstText(selectedCustomerIntel, ["edgeiq_verdict"], "") : "";
  const selectedEdgeiqReasons = selected ? firstText(selectedCustomerIntel, ["primary_reasons"], "") : "";
  const selectedEdgeiqRisks = selected ? firstText(selectedCustomerIntel, ["primary_risks"], "") : "";
  const selectedStableIntentBand = selected ? firstText(selectedCustomerIntel, ["stable_intent_band"], "--") : "--";
  const selectedContextSignalCount = selected ? firstText(selectedCustomerIntel, ["context_signal_count"], "--") : "--";
  const selectedDnaBand = selected ? firstText(selectedCustomerIntel, ["dna_band"], "--") : "--";'''
)

anchor = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0 }}>
            <strong style={{ display: "block", marginBottom: 8, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ View</strong>
            <p style={{ margin: 0, color: "#dbe7fb", fontSize: 12, lineHeight: 1.55 }}>{selectedExplainabilityWhy || selectedReason}</p>
          </div>'''

insert = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0, borderColor: "rgba(125,211,252,.32)", background: "rgba(14,22,35,.86)" }}>
            <strong style={{ display: "block", marginBottom: 8, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ Intelligence Score</strong>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginBottom: 10 }}>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Score</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqScore}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Band</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>DNA</span><strong style={{ ...miniValueStyle, color: cellTone(selectedDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedDnaBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Stable Intent</span><strong style={{ ...miniValueStyle, color: cellTone(selectedStableIntentBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedStableIntentBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Context</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{selectedIsScratched ? "SCRATCHED" : selectedContextSignalCount}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Verdict</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqVerdict || "--"}</strong></div>
            </div>
            <p style={{ margin: "0 0 8px", color: "#dbe7fb", fontSize: 12, lineHeight: 1.55 }}>{selectedEdgeiqReasons || "No customer intelligence reasons loaded."}</p>
            <p style={{ margin: 0, color: "#94a3b8", fontSize: 11, lineHeight: 1.5 }}>{selectedEdgeiqRisks || "No customer intelligence risks loaded."}</p>
          </div>
''' + anchor

must_replace(anchor, insert)

p.write_text(s, encoding="utf-8")
print("[CUSTOMER_INTELLIGENCE_UI_PATCH] COMPLETE")
print(f"checkpoint={checkpoint}")
print(f"patched={p}")
