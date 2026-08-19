from pathlib import Path

path = Path(r".\src\terminal\tabs\ResultsTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''  const matchedBet = enriched.filter((row) => row.betScore !== null).length;
'''

new = '''  const matchedBet = enriched.filter((row) => row.betScore !== null).length;

  const debugBetQuality = {
    betRows: betRows.length,
    saleR8BetRows: betRows.filter((row) => cleanTrack(track(row)) === "SALE" && raceNo(row) === "8").length,
    currentRows: currentRows.length,
    firstResultHorse: currentRows[0] ? horse(currentRows[0]) : "",
    firstBetHorse: betRows.find((row) => cleanTrack(track(row)) === "SALE" && raceNo(row) === "8") ? horse(betRows.find((row) => cleanTrack(track(row)) === "SALE" && raceNo(row) === "8")!) : "",
    firstResultClean: currentRows[0] ? cleanHorseLoose(horse(currentRows[0])) : "",
    firstBetClean: betRows.find((row) => cleanTrack(track(row)) === "SALE" && raceNo(row) === "8") ? cleanHorseLoose(horse(betRows.find((row) => cleanTrack(track(row)) === "SALE" && raceNo(row) === "8")!)) : "",
  };
'''

if old not in text:
    raise SystemExit("MATCHED_BET_LINE_NOT_FOUND")

text = text.replace(old, new)

old2 = '''          <div style={statCardStyle}><span>Bet Quality</span><strong style={{ display: "block", fontSize: 22 }}>{matchedBet}</strong></div>
'''

new2 = '''          <div style={statCardStyle}>
            <span>Bet Quality</span>
            <strong style={{ display: "block", fontSize: 22 }}>{matchedBet}</strong>
            <em style={{ display: "block", fontSize: 10, color: "#94a3b8", marginTop: 4 }}>
              rows {debugBetQuality.betRows} | saleR8 {debugBetQuality.saleR8BetRows}
            </em>
            <em style={{ display: "block", fontSize: 10, color: "#94a3b8" }}>
              R {debugBetQuality.firstResultClean} / B {debugBetQuality.firstBetClean}
            </em>
          </div>
'''

if old2 not in text:
    raise SystemExit("BET_CARD_BLOCK_NOT_FOUND")

text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")
print("BET_QUALITY_VISIBLE_DIAGNOSTIC_ADDED")
