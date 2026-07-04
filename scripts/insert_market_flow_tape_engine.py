from pathlib import Path

path = Path(r".\src\terminal\tabs\MarketTab.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''type MarketTabProps = {
  selectedMeetingKey: string;
  selectedRaceKey: string;
};
''',
'''type MarketTabProps = {
  selectedMeetingKey: string;
  selectedRaceKey: string;
};

type MarketFlow = {
  firmingMoves: number;
  driftingMoves: number;
  stableMoves: number;
  netFlow: number;
  largestFirm: string;
  largestFirmDelta: number | null;
  largestDrift: string;
  largestDriftDelta: number | null;
  state: string;
};
'''
)

marker = "function bookPercent"
insert = r'''
function emptyMarketFlow(): MarketFlow {
  return {
    firmingMoves: 0,
    driftingMoves: 0,
    stableMoves: 0,
    netFlow: 0,
    largestFirm: "-",
    largestFirmDelta: null,
    largestDrift: "-",
    largestDriftDelta: null,
    state: "QUIET",
  };
}

function buildMarketFlow(tapeRows: Row[], selectedTrack: string, selectedRaceNo: string): MarketFlow {
  const matched = tapeRows
    .filter((row) => compact(first(row, ["track"])) === compact(selectedTrack))
    .filter((row) => raceNoKey(first(row, ["race_no", "race_number", "race"])) === raceNoKey(selectedRaceNo))
    .filter((row) => !["TRUE", "YES", "1", "SCRATCHED"].includes(first(row, ["is_scratched", "runner_status"]).toUpperCase()));

  if (!matched.length) return emptyMarketFlow();

  const latestSnapshot = matched
    .map((row) => first(row, ["snapshot_time", "timestamp", "built_at", "updated_at"]))
    .filter(Boolean)
    .sort()
    .pop();

  const latestRows = latestSnapshot
    ? matched.filter((row) => first(row, ["snapshot_time", "timestamp", "built_at", "updated_at"]) === latestSnapshot)
    : matched;

  let firmingMoves = 0;
  let driftingMoves = 0;
  let stableMoves = 0;

  let largestFirm = "-";
  let largestFirmDelta: number | null = null;
  let largestDrift = "-";
  let largestDriftDelta: number | null = null;

  latestRows.forEach((row) => {
    const direction = first(row, ["move_direction"]).toUpperCase();
    const delta = firstNum(row, ["move_delta"]) ?? 0;
    const horse = first(row, ["horse"]) || "-";

    if (direction === "FIRMING" || delta < 0) {
      firmingMoves += 1;
      if (largestFirmDelta === null || delta < largestFirmDelta) {
        largestFirmDelta = delta;
        largestFirm = horse;
      }
      return;
    }

    if (direction === "DRIFTING" || delta > 0) {
      driftingMoves += 1;
      if (largestDriftDelta === null || delta > largestDriftDelta) {
        largestDriftDelta = delta;
        largestDrift = horse;
      }
      return;
    }

    stableMoves += 1;
  });

  const netFlow = firmingMoves - driftingMoves;

  const state =
    netFlow >= 4
      ? "AGGRESSIVE SUPPORT"
      : netFlow >= 2
        ? "SUPPORT"
        : netFlow <= -4
          ? "AGGRESSIVE DRIFT"
          : netFlow <= -2
            ? "DRIFTING"
            : "BALANCED";

  return {
    firmingMoves,
    driftingMoves,
    stableMoves,
    netFlow,
    largestFirm,
    largestFirmDelta,
    largestDrift,
    largestDriftDelta,
    state,
  };
}

'''

if insert.strip() not in text:
    text = text.replace(marker, insert + marker)

text = text.replace(
'''  const [rows, setRows] = useState<MarketRunner[]>([]);
  const [updatedAt, setUpdatedAt] = useState("");
''',
'''  const [rows, setRows] = useState<MarketRunner[]>([]);
  const [marketFlow, setMarketFlow] = useState<MarketFlow>(emptyMarketFlow());
  const [updatedAt, setUpdatedAt] = useState("");
'''
)

text = text.replace(
'''      const [terminalRows, bookmakerRows, flucRows] = await Promise.all([
        loadCsv("/data/edgeiq_vic_live_terminal_feed_v1.csv"),
        loadCsv("/data/edgeiq_bookmaker_board_v1.csv"),
        loadCsv("/data/edgeiq_market_fluctuations_v1.csv"),
      ]);
''',
'''      const [terminalRows, bookmakerRows, flucRows, tapeRows] = await Promise.all([
        loadCsv("/data/edgeiq_vic_live_terminal_feed_v1.csv"),
        loadCsv("/data/edgeiq_bookmaker_board_v1.csv"),
        loadCsv("/data/edgeiq_market_fluctuations_v1.csv"),
        loadCsv("/data/edgeiq_market_tape.csv"),
      ]);
'''
)

text = text.replace(
'''      setRows(nextRows);
      setUpdatedAt(new Date().toLocaleTimeString());
''',
'''      setRows(nextRows);
      setMarketFlow(buildMarketFlow(tapeRows, selectedTrack, selectedRaceNo));
      setUpdatedAt(new Date().toLocaleTimeString());
'''
)

old_card = '''              <div className="market-intel-card market-intel-card-wide">
                <div className="market-intel-title">Market Summary</div>
                <div className="market-summary-grid">
                  <div>
                    <span>Strongest Support</span>
                    <strong>{strongestSupport ? strongestSupport.row.horse : "-"}</strong>
                    <em className="terminal-positive">{strongestSupport ? pct(strongestSupport.move) : "-"}</em>
                  </div>
                  <div>
                    <span>Strongest Opposition</span>
                    <strong>{strongestOpposition ? strongestOpposition.row.horse : "-"}</strong>
                    <em className="terminal-negative">{strongestOpposition ? pct(strongestOpposition.move) : "-"}</em>
                  </div>
                  <div>
                    <span>Pressure</span>
                    <strong>{pressure}</strong>
                    <em>{firmers.length} in / {drifters.length} out</em>
                  </div>
                  <div>
                    <span>Book</span>
                    <strong>{bookShape}</strong>
                    <em>{overround !== null ? `${overround.toFixed(1)}%` : "-"}</em>
                  </div>
                  <div>
                    <span>Confidence</span>
                    <strong>{marketConfidence}</strong>
                    <em>{pricedCount}/{activeRows.length} priced</em>
                  </div>
                </div>
              </div>
'''

new_card = '''              <div className="market-intel-card market-intel-card-wide">
                <div className="market-intel-title">Market Flow</div>
                <div className="market-summary-grid">
                  <div>
                    <span>Firming Moves</span>
                    <strong className="terminal-positive">{marketFlow.firmingMoves}</strong>
                    <em>latest tape</em>
                  </div>
                  <div>
                    <span>Drifting Moves</span>
                    <strong className="terminal-negative">{marketFlow.driftingMoves}</strong>
                    <em>latest tape</em>
                  </div>
                  <div>
                    <span>Net Flow</span>
                    <strong>{marketFlow.netFlow > 0 ? `+${marketFlow.netFlow}` : marketFlow.netFlow}</strong>
                    <em>{marketFlow.state}</em>
                  </div>
                  <div>
                    <span>Largest Firm</span>
                    <strong>{marketFlow.largestFirm}</strong>
                    <em className="terminal-positive">{marketFlow.largestFirmDelta !== null ? marketFlow.largestFirmDelta.toFixed(2) : "-"}</em>
                  </div>
                  <div>
                    <span>Largest Drift</span>
                    <strong>{marketFlow.largestDrift}</strong>
                    <em className="terminal-negative">{marketFlow.largestDriftDelta !== null ? `+${marketFlow.largestDriftDelta.toFixed(2)}` : "-"}</em>
                  </div>
                </div>
              </div>
'''

if old_card not in text:
    raise SystemExit("Could not find Market Summary card. No changes made.")

text = text.replace(old_card, new_card)

path.write_text(text, encoding="utf-8")
print("MARKET FLOW TAPE ENGINE INSERTED")
