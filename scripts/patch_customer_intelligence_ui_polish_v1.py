from pathlib import Path

p = Path(".\\src\\components\\RaceIntelligenceScreen.tsx")
s = p.read_text(encoding="utf-8")

checkpoint = Path(".\\checkpoints\\RaceIntelligenceScreen_CHECKPOINT_BEFORE_CUSTOMER_INTELLIGENCE_UI_POLISH_20260623.tsx")
checkpoint.write_text(s, encoding="utf-8")

old = '''  const selectedEdgeiqScore = selected ? firstText(selectedCustomerIntel, ["edgeiq_score"], "--") : "--";
  const selectedEdgeiqBand = selected ? firstText(selectedCustomerIntel, ["edgeiq_band"], "--") : "--";
  const selectedEdgeiqVerdict = selected ? firstText(selectedCustomerIntel, ["edgeiq_verdict"], "") : "";
  const selectedEdgeiqReasons = selected ? firstText(selectedCustomerIntel, ["primary_reasons"], "") : "";
  const selectedEdgeiqRisks = selected ? firstText(selectedCustomerIntel, ["primary_risks"], "") : "";
  const selectedStableIntentBand = selected ? firstText(selectedCustomerIntel, ["stable_intent_band"], "--") : "--";
  const selectedContextSignalCount = selected ? firstText(selectedCustomerIntel, ["context_signal_count"], "--") : "--";
  const selectedCustomerDnaBand = selected ? firstText(selectedCustomerIntel, ["dna_band"], "--") : "--";'''

new = '''  const selectedEdgeiqScore = selected ? firstText(selectedCustomerIntel, ["edgeiq_score"], "--") : "--";
  const selectedEdgeiqBandRaw = selected ? firstText(selectedCustomerIntel, ["edgeiq_band"], "--") : "--";
  const selectedEdgeiqBand = selectedEdgeiqBandRaw.replace(/_/g, " ").toUpperCase();
  const selectedEdgeiqVerdict = selected ? firstText(selectedCustomerIntel, ["edgeiq_verdict"], "") : "";
  const selectedEdgeiqReasonsRaw = selected ? firstText(selectedCustomerIntel, ["primary_reasons"], "") : "";
  const selectedEdgeiqRisksRaw = selected ? firstText(selectedCustomerIntel, ["primary_risks"], "") : "";
  const selectedEdgeiqReasons = selectedEdgeiqReasonsRaw.split("|").map((x) => x.trim()).filter(Boolean).slice(0, 4);
  const selectedEdgeiqRisks = selectedEdgeiqRisksRaw.split("|").map((x) => x.trim()).filter(Boolean).slice(0, 4);
  const selectedStableIntentBandRaw = selected ? firstText(selectedCustomerIntel, ["stable_intent_band"], "--") : "--";
  const selectedStableIntentBand = selectedStableIntentBandRaw.replace(/_/g, " ").toUpperCase();
  const selectedContextSignalCount = selected ? firstText(selectedCustomerIntel, ["context_signal_count"], "--") : "--";
  const selectedCustomerDnaBandRaw = selected ? firstText(selectedCustomerIntel, ["dna_band"], "--") : "--";
  const selectedCustomerDnaBand = selectedCustomerDnaBandRaw.replace(/_/g, " ").toUpperCase();'''

if old not in s:
    raise SystemExit("[PATCH FAILED] derived value block not found")

s = s.replace(old, new, 1)

old_card = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0, borderColor: "rgba(125,211,252,.32)", background: "rgba(14,22,35,.86)" }}>
            <strong style={{ display: "block", marginBottom: 8, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".06em" }}>EDGEiQ Intelligence Score</strong>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginBottom: 10 }}>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Score</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqScore}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Band</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>DNA</span><strong style={{ ...miniValueStyle, color: cellTone(selectedCustomerDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedCustomerDnaBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Stable Intent</span><strong style={{ ...miniValueStyle, color: cellTone(selectedStableIntentBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedStableIntentBand}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Context</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{selectedIsScratched ? "SCRATCHED" : selectedContextSignalCount}</strong></div>
              <div style={valueTileStyle}><span style={miniLabelStyle}>Verdict</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqVerdict || "--"}</strong></div>
            </div>
            <p style={{ margin: "0 0 8px", color: "#dbe7fb", fontSize: 12, lineHeight: 1.55 }}>{selectedEdgeiqReasons || "No customer intelligence reasons loaded."}</p>
            <p style={{ margin: 0, color: "#94a3b8", fontSize: 11, lineHeight: 1.5 }}>{selectedEdgeiqRisks || "No customer intelligence risks loaded."}</p>
          </div>'''

new_card = '''          <div style={{ ...narrativeInsetStyle, marginTop: 0, borderColor: "rgba(125,211,252,.32)", background: "linear-gradient(135deg, rgba(14,22,35,.96), rgba(3,7,18,.92))" }}>
            <strong style={{ display: "block", marginBottom: 10, color: "#7dd3fc", fontSize: 11, textTransform: "uppercase", letterSpacing: ".08em" }}>EDGEiQ Intelligence Score</strong>

            <div style={{ display: "grid", gridTemplateColumns: "170px 1fr", gap: 12, alignItems: "stretch", marginBottom: 10 }}>
              <div style={{ ...valueTileStyle, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: 104 }}>
                <span style={{ ...miniLabelStyle, marginBottom: 5 }}>EDGEIQ SCORE</span>
                <strong style={{ fontSize: 38, lineHeight: 1, color: cellTone(selectedEdgeiqBand), letterSpacing: "-.04em" }}>
                  {selectedIsScratched ? "SCR" : selectedEdgeiqScore}
                </strong>
                <span style={{ marginTop: 8, color: cellTone(selectedEdgeiqBand), fontWeight: 1000, fontSize: 12 }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqBand}</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Stable Intent</span><strong style={{ ...miniValueStyle, color: cellTone(selectedStableIntentBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedStableIntentBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Context Signals</span><strong style={{ ...miniValueStyle, color: "#7dd3fc" }}>{selectedIsScratched ? "SCRATCHED" : selectedContextSignalCount}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>DNA</span><strong style={{ ...miniValueStyle, color: cellTone(selectedCustomerDnaBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedCustomerDnaBand}</strong></div>
                <div style={valueTileStyle}><span style={miniLabelStyle}>Verdict</span><strong style={{ ...miniValueStyle, color: cellTone(selectedEdgeiqBand) }}>{selectedIsScratched ? "SCRATCHED" : selectedEdgeiqVerdict || "--"}</strong></div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ ...valueTileStyle, padding: 10 }}>
                <span style={{ ...miniLabelStyle, color: "#86efac" }}>Why inspect</span>
                <div style={{ display: "grid", gap: 5, marginTop: 7 }}>
                  {selectedEdgeiqReasons.length ? selectedEdgeiqReasons.map((item, index) => (
                    <span key={`edgeiq-reason-${index}`} style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>• {item}</span>
                  )) : <span style={{ color: "#94a3b8", fontSize: 11 }}>No customer intelligence reasons loaded.</span>}
                </div>
              </div>

              <div style={{ ...valueTileStyle, padding: 10 }}>
                <span style={{ ...miniLabelStyle, color: "#fca5a5" }}>Risks</span>
                <div style={{ display: "grid", gap: 5, marginTop: 7 }}>
                  {selectedEdgeiqRisks.length ? selectedEdgeiqRisks.map((item, index) => (
                    <span key={`edgeiq-risk-${index}`} style={{ color: "#dbe7fb", fontSize: 11, lineHeight: 1.35 }}>• {item}</span>
                  )) : <span style={{ color: "#94a3b8", fontSize: 11 }}>No customer intelligence risks loaded.</span>}
                </div>
              </div>
            </div>
          </div>'''

if old_card not in s:
    raise SystemExit("[PATCH FAILED] existing customer intelligence card not found")

s = s.replace(old_card, new_card, 1)

p.write_text(s, encoding="utf-8")
print("[CUSTOMER_INTELLIGENCE_UI_POLISH_V1] COMPLETE")
print(f"checkpoint={checkpoint}")
