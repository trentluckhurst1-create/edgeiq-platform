from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_INTELLIGENCE_SUMMARY_V1_1_WIRE_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

def must_replace(old, new):
    global s
    if old not in s:
        raise SystemExit(f"[PATCH FAILED] anchor not found:\n{old[:500]}")
    s = s.replace(old, new, 1)

must_replace(
'''  customerIntelligence: "/data/edgeiq_customer_intelligence_terminal_feed_v1.csv",
};''',
'''  customerIntelligence: "/data/edgeiq_customer_intelligence_terminal_feed_v1.csv",
  intelligenceSummary: "/data/edgeiq_intelligence_summary_engine_v1_1.csv",
};'''
)

must_replace(
'''  customerIntel?: Row;''',
'''  customerIntel?: Row;
  intelligenceSummary?: Row;'''
)

must_replace(
'''  const [customerIntelligenceRows, setCustomerIntelligenceRows] = useState<Row[]>([]);''',
'''  const [customerIntelligenceRows, setCustomerIntelligenceRows] = useState<Row[]>([]);
  const [intelligenceSummaryRows, setIntelligenceSummaryRows] = useState<Row[]>([]);'''
)

must_replace(
'''      const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limitedData, intelligenceScore, customerIntelligence] = await Promise.all([''',
'''      const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, explainability, connection, factorScorecard, limitedData, intelligenceScore, customerIntelligence, intelligenceSummary] = await Promise.all(['''
)

must_replace(
'''        loadCsv(FILES.customerIntelligence),
      ]);''',
'''        loadCsv(FILES.customerIntelligence),
        loadCsv(FILES.intelligenceSummary),
      ]);'''
)

must_replace(
'''      setCustomerIntelligenceRows(customerIntelligence);''',
'''      setCustomerIntelligenceRows(customerIntelligence);
      setIntelligenceSummaryRows(intelligenceSummary);'''
)

must_replace(
'''      const customerIntel = findSidecar(customerIntelligenceRows, row);''',
'''      const customerIntel = findSidecar(customerIntelligenceRows, row);
      const intelligenceSummary = findSidecar(intelligenceSummaryRows, row);'''
)

must_replace(
'''      return { row, runnerIntel, v8, bet, rel, drawer, dna, explainability, connection, limited, intel, customerIntel, factorRows };''',
'''      return { row, runnerIntel, v8, bet, rel, drawer, dna, explainability, connection, limited, intel, customerIntel, intelligenceSummary, factorRows };'''
)

must_replace(
'''  }, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows, customerIntelligenceRows]);''',
'''  }, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, explainabilityRows, connectionRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows, customerIntelligenceRows, intelligenceSummaryRows]);'''
)

must_replace(
'''  const selectedCustomerIntel = selected?.customerIntel;''',
'''  const selectedCustomerIntel = selected?.customerIntel;
  const selectedIntelligenceSummary = selected?.intelligenceSummary;'''
)

must_replace(
'''  const selectedCustomerDnaBand = selectedCustomerDnaBandRaw.replace(/_/g, " ").toUpperCase();''',
'''  const selectedCustomerDnaBand = selectedCustomerDnaBandRaw.replace(/_/g, " ").toUpperCase();
  const selectedIntelligenceSummaryTitle = selected ? firstText(selectedIntelligenceSummary, ["intelligence_summary_title"], "") : "";
  const selectedIntelligenceSummaryText = selected ? firstText(selectedIntelligenceSummary, ["intelligence_summary_text"], "") : "";
  const selectedIntelligenceActionText = selected ? firstText(selectedIntelligenceSummary, ["customer_action_text"], "") : "";'''
)

anchor = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0 }}>
            <strong style={{ display: "block", marginBottom: 8, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ View</strong>'''

insert = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0, borderColor: "rgba(125,211,252,.25)", background: "rgba(2,6,23,.70)" }}>
            <strong style={{ display: "block", marginBottom: 8, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".08em" }}>EDGEiQ Summary</strong>
            <div style={{ color: cellTone(selectedEdgeiqBand), fontSize: 13, fontWeight: 1000, marginBottom: 7 }}>
              {selectedIsScratched ? "SCRATCHED" : selectedIntelligenceSummaryTitle || selectedEdgeiqBand || "--"}
            </div>
            <p style={{ margin: 0, color: "#dbe7fb", fontSize: 12, lineHeight: 1.55 }}>
              {selectedIntelligenceSummaryText || "No EDGEiQ summary loaded for this runner."}
            </p>
            {selectedIntelligenceActionText ? (
              <div style={{ marginTop: 9, paddingTop: 8, borderTop: "1px solid rgba(148,163,184,.16)", color: "#94a3b8", fontSize: 11, lineHeight: 1.45 }}>
                {selectedIntelligenceActionText}
              </div>
            ) : null}
          </div>

''' + anchor

must_replace(anchor, insert)

p.write_text(s, encoding="utf-8")
print("[INTELLIGENCE_SUMMARY_UI_WIRE_V1_1] COMPLETE")
print(f"checkpoint={checkpoint}")
