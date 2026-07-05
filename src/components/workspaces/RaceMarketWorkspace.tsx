type Row = Record<string, any>;

type EnrichedRunnerLike = {
  row: Row;
  bet?: Row;
  [key: string]: any;
};

type RaceMarketWorkspaceProps = {
  activeRaceRows: EnrichedRunnerLike[];
  bettingConfidence: string;
  firstNum: (row: Row | undefined, keys: string[]) => number | null;
  limitedAdjustedPrice: (item: EnrichedRunnerLike) => number | null;
  fairPrice: (row: Row, bet?: Row) => number | null;
  livePrice: (row: Row, bet?: Row) => number | null;
  edgePct: (row: Row, bet?: Row) => number | null;
  horse: (row: Row) => string;
  saddle: (row: Row) => number;
  runnerRowKey: (row: Row) => string;
  money: (value: number | null) => string;
  marketMoney: (value: number | null) => string;
  pct: (value: number | null) => string;
};

export function RaceMarketWorkspace(props: RaceMarketWorkspaceProps) {
  const {
    activeRaceRows,
    bettingConfidence,
    firstNum,
    limitedAdjustedPrice,
    fairPrice,
    livePrice,
    edgePct,
    horse,
    saddle,
    runnerRowKey,
    money,
    marketMoney,
    pct,
  } = props;

  const priceFrom = (item: EnrichedRunnerLike, keys: string[]) => firstNum({ ...(item.row || {}), ...(item.bet || {}) }, keys);

  const enrichedMarketRows = activeRaceRows.map((item) => {
    const fair = limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet);
    const open = priceFrom(item, ["open_price", "opening_price", "market_open", "tab_open_price", "fixed_open_price"]);
    const current = livePrice(item.row, item.bet);
    const fluc = open !== null && current !== null && open > 0 ? ((current - open) / open) * 100 : null;
    const diff = edgePct(item.row, item.bet);
    return { item, fair, open, current, fluc, diff };
  });

  const firmers = enrichedMarketRows.filter((row) => row.fluc !== null && row.fluc < 0);
  const drifters = enrichedMarketRows.filter((row) => row.fluc !== null && row.fluc > 0);
  const unchanged = enrichedMarketRows.filter((row) => row.fluc === null || row.fluc === 0);
  const strongestEdge = [...enrichedMarketRows].filter((row) => row.diff !== null).sort((a, b) => (b.diff ?? -999) - (a.diff ?? -999))[0];
  const biggestFirm = [...firmers].sort((a, b) => (a.fluc ?? 0) - (b.fluc ?? 0))[0];
  const biggestDrift = [...drifters].sort((a, b) => (b.fluc ?? 0) - (a.fluc ?? 0))[0];

  return (
    <section className="edgeiq-market-tab edgeiq-product-section edgeiq-product-v4-panel edgeiq-market-v1-lock edgeiq-market-final-lock">
      <div className="edgeiq-tab-heading edgeiq-product-v4-section-title">
        <span>MARKET</span>
        <strong>EDGEiQ Trading Floor</strong>
        <em>Market intelligence, fluctuations, value and context.</em>
      </div>

      <div className="edgeiq-market-final-cards">
        {[
          ["Largest Overlay", strongestEdge ? horse(strongestEdge.item.row) : "Pending", strongestEdge?.diff === null || !strongestEdge ? "-" : pct(strongestEdge.diff)],
          ["Biggest Firm", biggestFirm ? horse(biggestFirm.item.row) : "Pending", biggestFirm?.fluc === null || !biggestFirm ? "Pending Market" : `Firm ${Math.abs(biggestFirm.fluc).toFixed(1)}%`],
          ["Biggest Drift", biggestDrift ? horse(biggestDrift.item.row) : "Pending", biggestDrift?.fluc === null || !biggestDrift ? "Pending Market" : `Drift ${Math.abs(biggestDrift.fluc).toFixed(1)}%`],
          ["Market Confidence", bettingConfidence !== "-" ? bettingConfidence : "Pending", ""],
        ].map(([label, value, detail]) => (
          <article key={`market-card-${label}`}>
            <span>{label}</span>
            <strong>{value}</strong>
            <em>{detail}</em>
          </article>
        ))}
      </div>

      <div className="edgeiq-market-content-grid">
        <div className="edgeiq-market-table edgeiq-product-table edgeiq-product-v4-table" role="table" aria-label="Market comparison table">
          <div className="edgeiq-market-row head" role="row">
            {["NO", "RUNNER", "EDGEIQ", "OPEN", "CURRENT", "FLUC", "EDGE %"].map((label) => <span key={`market-head-${label}`}>{label}</span>)}
          </div>

          {enrichedMarketRows.map(({ item, fair, open, current, fluc, diff }) => {
            const flucClass = fluc === null ? "neutral" : fluc > 0 ? "drift" : fluc < 0 ? "firm" : "neutral";
            const flucDisplay = fluc === null ? "Pending Market" : fluc > 0 ? `Drift ${Math.abs(fluc).toFixed(1)}%` : fluc < 0 ? `Firm ${Math.abs(fluc).toFixed(1)}%` : "0.0%";

            return (
              <div className="edgeiq-market-row" role="row" key={`market-row-${runnerRowKey(item.row)}`}>
                <span>{saddle(item.row) === 999 ? "-" : saddle(item.row)}</span>
                <strong>{horse(item.row)}</strong>
                <span>{money(fair)}</span>
                <span>{marketMoney(open)}</span>
                <span>{marketMoney(current)}</span>
                <span className={flucClass}>{flucDisplay}</span>
                <span className={diff === null ? "neutral" : diff > 0 ? "positive" : "negative"}>{diff === null ? "-" : pct(diff)}</span>
              </div>
            );
          })}
        </div>

        <aside className="edgeiq-market-fluc-panel edgeiq-market-final-side">
          <section>
            <span>Market Pulse</span>
            {[["Firmers", firmers.length], ["Drifters", drifters.length], ["Unchanged", unchanged.length]].map(([label, value]) => (
              <div key={`market-pulse-${label}`}><em>{label}</em><strong>{value}</strong></div>
            ))}
          </section>

          <section>
            <span>Money Flow</span>
            {[...firmers].sort((a, b) => (a.fluc ?? 0) - (b.fluc ?? 0)).slice(0, 3).map((row, index) => (
              <div key={`market-flow-${runnerRowKey(row.item.row)}`}>
                <em>{index + 1}. {horse(row.item.row)}</em>
                <strong className="firm">Firm {Math.abs(row.fluc ?? 0).toFixed(1)}%</strong>
              </div>
            ))}
          </section>

          <section>
            <span>Market Narrative</span>
            <p>Market board shows live price movement and EDGEiQ fair-price context only. No recommendation language is shown.</p>
          </section>
        </aside>
      </div>
    </section>
  );
}
