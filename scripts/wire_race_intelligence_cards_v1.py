from pathlib import Path

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''  reliability: "/data/edgeiq_live_race_reliability_v1_feed.csv",
};''',
'''  reliability: "/data/edgeiq_live_race_reliability_v1_feed.csv",
  intelligenceCards: "/data/edgeiq_race_intelligence_cards_v1.csv",
};'''
)

text = text.replace(
'''  const [reliabilityRows, setReliabilityRows] = useState<Row[]>([]);''',
'''  const [reliabilityRows, setReliabilityRows] = useState<Row[]>([]);
  const [intelligenceCardRows, setIntelligenceCardRows] = useState<Row[]>([]);'''
)

text = text.replace(
'''      const [runner, v8, bet, rel] = await Promise.all([
        loadCsv(FILES.runnerBoard),
        loadCsv(FILES.v8),
        loadCsv(FILES.betQuality),
        loadCsv(FILES.reliability),
      ]);''',
'''      const [runner, v8, bet, rel, cards] = await Promise.all([
        loadCsv(FILES.runnerBoard),
        loadCsv(FILES.v8),
        loadCsv(FILES.betQuality),
        loadCsv(FILES.reliability),
        loadCsv(FILES.intelligenceCards),
      ]);'''
)

text = text.replace(
'''      setReliabilityRows(rel);
      setLoading(false);''',
'''      setReliabilityRows(rel);
      setIntelligenceCardRows(cards);
      setLoading(false);'''
)

needle = '''  const header = raceRows[0];
  const positiveEdges = enriched.filter((item) => (edgePct(item.row, item.bet) ?? 0) > 0).length;
  const matchedBet = enriched.filter((item) => item.bet).length;
  const matchedV8 = enriched.filter((item) => item.v8 || item.bet).length;
  const avgFairValues = enriched.map((item) => fairPrice(item.row, item.bet)).filter((x): x is number => x !== null && x > 0);
  const avgFair = avgFairValues.length ? avgFairValues.reduce((a, b) => a + b, 0) / avgFairValues.length : null;
'''

replacement = '''  const header = raceRows[0];

  const intelligenceCard = useMemo(() => {
    if (!header) return undefined;
    return intelligenceCardRows.find((row) =>
      cleanTrack(track(row)) === cleanTrack(track(header)) &&
      raceNo(row) === raceNo(header)
    );
  }, [intelligenceCardRows, header]);

  const positiveEdges = enriched.filter((item) => (edgePct(item.row, item.bet) ?? 0) > 0).length;
  const matchedBet = enriched.filter((item) => item.bet).length;
  const matchedV8 = enriched.filter((item) => item.v8 || item.bet).length;
  const avgFairValues = enriched.map((item) => fairPrice(item.row, item.bet)).filter((x): x is number => x !== null && x > 0);
  const avgFair = avgFairValues.length ? avgFairValues.reduce((a, b) => a + b, 0) / avgFairValues.length : null;

  const raceClarity = firstText(intelligenceCard, ["race_clarity_band_v1"], "—").replace(/_/g, " ");
  const expectedTempo = firstText(intelligenceCard, ["expected_tempo_band_v1"], "—").replace(/_/g, " ");
  const bettingConfidence = firstText(intelligenceCard, ["betting_confidence_band_v1"], "—").replace(/_/g, " ");
  const raceStory = firstText(intelligenceCard, ["race_story_v1"], "");
  const trackProfile = `${trackCondition(header).toUpperCase()} / ${distance(header)} / ${raceClass(header)}`;
'''

if needle not in text:
    raise SystemExit("HEADER_METRICS_BLOCK_NOT_FOUND")

text = text.replace(needle, replacement)

old = '''        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,120px)", gap: 10 }}>
          <div style={statStyle}><span>Runners</span><strong style={{ display: "block", fontSize: 22 }}>{raceRows.length}</strong></div>
          <div style={statStyle}><span>Positive Edge</span><strong style={{ display: "block", fontSize: 22 }}>{positiveEdges}</strong></div>
          <div style={statStyle}><span>Avg Fair</span><strong style={{ display: "block", fontSize: 22 }}>{money(avgFair)}</strong></div>
          <div style={statStyle}><span>Sidecars</span><strong style={{ display: "block", fontSize: 22 }}>B{matchedBet}/V{matchedV8}</strong></div>
        </div>'''

new = '''        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,150px)", gap: 10 }}>
          <div style={statStyle}><span>Race Clarity</span><strong style={{ display: "block", fontSize: 18 }}>{raceClarity}</strong></div>
          <div style={statStyle}><span>Expected Tempo</span><strong style={{ display: "block", fontSize: 18 }}>{expectedTempo}</strong></div>
          <div style={statStyle}><span>Track Profile</span><strong style={{ display: "block", fontSize: 13 }}>{trackProfile}</strong></div>
          <div style={statStyle}><span>Betting Confidence</span><strong style={{ display: "block", fontSize: 18 }}>{bettingConfidence}</strong></div>
        </div>'''

if old not in text:
    raise SystemExit("OLD_HEADER_CARD_BLOCK_NOT_FOUND")

text = text.replace(old, new)

old2 = '''          <p style={{ margin: 0, color: "#bfd0ea" }}>
            Live Runner Board is the primary source. V8 and Bet Quality are sidecars only.
          </p>'''

new2 = '''          <p style={{ margin: 0, color: "#bfd0ea" }}>
            {raceStory || "Live Runner Board is the primary source. V8 and Bet Quality are sidecars only."}
          </p>'''

text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")
print("RACE_INTELLIGENCE_CARDS_V1_WIRED")
