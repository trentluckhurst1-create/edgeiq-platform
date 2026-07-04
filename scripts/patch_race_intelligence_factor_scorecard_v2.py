from pathlib import Path

path = Path("src/components/RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

backup = Path("src/components/RaceIntelligenceScreen_BEFORE_FACTOR_SCORECARD_V2_PY_PATCH.tsx")
backup.write_text(text, encoding="utf-8")

def must_replace(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise RuntimeError(f"Missing target block: {label}")
    text = text.replace(old, new)

def replace_once_if_missing(target_marker: str, old: str, new: str, label: str) -> None:
    global text
    if target_marker in text:
        return
    must_replace(old, new, label)

replace_once_if_missing(
    'factorScorecard: "/data/edgeiq_live_runner_factor_scorecard_v2.csv"',
    '  runnerDnaDrawer: "/data/edgeiq_runner_dna_drawer_feed_v1.csv",\n  limitedData: "/data/edgeiq_limited_data_market_adjusted_v1.csv",',
    '  runnerDnaDrawer: "/data/edgeiq_runner_dna_drawer_feed_v1.csv",\n  factorScorecard: "/data/edgeiq_live_runner_factor_scorecard_v2.csv",\n  limitedData: "/data/edgeiq_limited_data_market_adjusted_v1.csv",',
    "FILES.factorScorecard",
)

replace_once_if_missing(
    "factorRows?: Row[];",
    "  limited?: Row;\n  intel?: Row;",
    "  limited?: Row;\n  intel?: Row;\n  factorRows?: Row[];",
    "EnrichedRunner.factorRows",
)

replace_once_if_missing(
    "const [factorScorecardRows, setFactorScorecardRows] = useState<Row[]>([]);",
    "  const [intelligenceScoreRows, setIntelligenceScoreRows] = useState<Row[]>([]);\n  const [selectedKey, setSelectedKey] = useState(\"\");",
    "  const [intelligenceScoreRows, setIntelligenceScoreRows] = useState<Row[]>([]);\n  const [factorScorecardRows, setFactorScorecardRows] = useState<Row[]>([]);\n  const [selectedKey, setSelectedKey] = useState(\"\");",
    "factorScorecardRows state",
)

must_replace(
    "const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, limitedData, intelligenceScore] = await Promise.all([",
    "const [runner, runnerIntel, v8, bet, rel, cards, briefing, marketIntel, verdict, trackIntel, horseDrawer, runnerDnaDrawer, factorScorecard, limitedData, intelligenceScore] = await Promise.all([",
    "Promise.all destructure",
)

replace_once_if_missing(
    "loadCsv(FILES.factorScorecard)",
    "        loadCsv(FILES.runnerDnaDrawer),\n        loadCsv(FILES.limitedData),",
    "        loadCsv(FILES.runnerDnaDrawer),\n        loadCsv(FILES.factorScorecard),\n        loadCsv(FILES.limitedData),",
    "Promise.all factorScorecard load",
)

replace_once_if_missing(
    "setFactorScorecardRows(factorScorecard);",
    "      setRunnerDnaDrawerRows(runnerDnaDrawer);\n      setLimitedDataRows(limitedData);",
    "      setRunnerDnaDrawerRows(runnerDnaDrawer);\n      setFactorScorecardRows(factorScorecard);\n      setLimitedDataRows(limitedData);",
    "setFactorScorecardRows",
)

replace_once_if_missing(
    "const factorRows = factorScorecardRows",
    "      const intel = findSidecar(intelligenceScoreRows, row);\n\n      return { row, runnerIntel, v8, bet, rel, drawer, dna, limited, intel };",
    "      const intel = findSidecar(intelligenceScoreRows, row);\n      const factorRows = factorScorecardRows\n        .filter((factorRow) => cleanTrack(track(factorRow)) === cleanTrack(track(row)) && raceNo(factorRow) === raceNo(row) && cleanHorse(horse(factorRow)) === cleanHorse(horse(row)))\n        .sort((a, b) => (num(a.factor_order) ?? 999) - (num(b.factor_order) ?? 999));\n\n      return { row, runnerIntel, v8, bet, rel, drawer, dna, limited, intel, factorRows };",
    "attach factorRows",
)

must_replace(
    "}, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, limitedDataRows, intelligenceScoreRows]);",
    "}, [raceRows, runnerIntelRows, v8Rows, betRows, reliabilityRows, horseDrawerRows, runnerDnaDrawerRows, factorScorecardRows, limitedDataRows, intelligenceScoreRows]);",
    "useMemo deps",
)

replace_once_if_missing(
    "const selectedFactorRows = selected?.factorRows || [];",
    '  const selectedDnaNarrative = selected ? firstText(selected.dna, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";\n  const selectedCurrentDecision = selected ? decision(selected.row, selected.bet) : "—";',
    '  const selectedDnaNarrative = selected ? firstText(selected.dna, ["runner_dna_v6_2_narrative", "runner_dna_v6_1_narrative"], "") : "";\n  const selectedFactorRows = selected?.factorRows || [];\n  const selectedCurrentDecision = selected ? decision(selected.row, selected.bet) : "—";',
    "selectedFactorRows",
)

dna_read_block = '''              <div style={{ ...narrativeInsetStyle, margin: 0, fontSize: 11, lineHeight: 1.4 }}>
                <strong style={{ color: "#7dd3fc", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em" }}>
                  EDGEiQ DNA Read
                </strong>
                <div style={{ marginTop: 4 }}>
                  {selectedIsScratched ? "Runner scratched." : selectedDnaNarrative || "No DNA narrative available."}
                </div>
              </div>'''

factor_block = '''              <div style={{ ...narrativeInsetStyle, margin: 0, display: "grid", gap: 6 }}>
                <strong style={{ color: "#7dd3fc", fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em" }}>
                  DNA Factor Breakdown
                </strong>
                {selectedIsScratched ? (
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>Runner scratched.</div>
                ) : selectedFactorRows.length ? (
                  <div style={{ display: "grid", gap: 6 }}>
                    {selectedFactorRows.map((factorRow) => {
                      const factorName = firstText(factorRow, ["factor"], "—");
                      const factorScore = firstNum(factorRow, ["factor_score"]);
                      const factorBand = firstText(factorRow, ["factor_band"], "—").replace(/_/g, " ").toUpperCase();
                      const isStrong = firstText(factorRow, ["is_strongest_factor"], "") === "YES";
                      const isWeak = firstText(factorRow, ["is_weakest_factor"], "") === "YES";
                      const tone = isWeak ? "#f5c451" : isStrong ? "#7dd3fc" : cellTone(factorBand);
                      return (
                        <div key={`${horse(selected.row)}-${factorName}`} style={{ display: "grid", gap: 3 }}>
                          <div style={{ display: "grid", gridTemplateColumns: "92px 42px 1fr", gap: 6, alignItems: "center" }}>
                            <span style={{ color: tone, fontSize: 10.5, fontWeight: 900, letterSpacing: ".04em" }}>{factorName}</span>
                            <strong style={{ color: "#f8fafc", fontSize: 11, textAlign: "right" }}>{factorScore === null ? "—" : factorScore.toFixed(0)}</strong>
                            <span style={{ color: "#94a3b8", fontSize: 9.5, fontWeight: 800, textTransform: "uppercase" }}>{factorBand}</span>
                          </div>
                          <div style={barTrackStyle}>
                            <div style={barFill(factorScore ?? 0, tone)} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ color: "#94a3b8", fontSize: 11 }}>No factor breakdown available.</div>
                )}
              </div>'''

if "DNA Factor Breakdown" not in text:
    must_replace(dna_read_block, dna_read_block + "\n\n" + factor_block, "DNA factor breakdown insert")

path.write_text(text, encoding="utf-8")
print("[FACTOR_SCORECARD_V2_PY_PATCH] COMPLETE")
