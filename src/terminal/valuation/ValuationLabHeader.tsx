type RunnerRow = Record<string, any>;

type Props = {
  runners: RunnerRow[];
};

function text(value: unknown): string {
  return String(value ?? "").trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace("%", "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function ratedPrice(row: RunnerRow): number | null {
  return (
    num(row.ratedPrice) ??
    num(row.rated_price) ??
    num(row.model_price) ??
    num(row.fair_price)
  );
}

function marketPrice(row: RunnerRow): number | null {
  return (
    num(row.marketPrice) ??
    num(row.market_price) ??
    num(row.best_odds) ??
    num(row.price) ??
    num(row.odds)
  );
}

function overlay(row: RunnerRow): number {
  const explicit =
    num(row.edgePct) ??
    num(row.edge_pct) ??
    num(row.overlay_pct) ??
    num(row.overlay_score);

  if (explicit !== null) {
    return explicit;
  }

  const rated = ratedPrice(row);
  const market = marketPrice(row);

  if (!rated || !market || rated <= 0 || market <= 0) {
    return 0;
  }

  return ((market - rated) / rated) * 100;
}

function confidence(row: RunnerRow): number {
  return (
    num(row.confidence_score) ??
    num(row.model_confidence) ??
    num(row.rating_confidence) ??
    0
  );
}

function valuationTier(row: RunnerRow): string {
  const edge = overlay(row);
  const conf = confidence(row);

  if (edge >= 15 && conf >= 75) return "ELITE";
  if (edge >= 10 && conf >= 60) return "STRONG";
  if (edge >= 5) return "WATCH";

  return "NEUTRAL";
}

export default function ValuationLabHeader({
  runners,
}: Props) {
  const active = runners.filter((row) => !row.isScratched);

  const ranked: RunnerRow[] = [...active]
    .map((row) => ({
      ...row,
      computed_overlay: overlay(row),
      computed_confidence: confidence(row),
      valuation_tier: valuationTier(row),
    }))
    .sort((a, b) => b.computed_overlay - a.computed_overlay);

  const topRows = ranked.slice(0, 8);

  return (
    <div className="edgeiq-valuation-lab">
      <div className="edgeiq-valuation-hero">
        <div>
          <div className="edgeiq-kicker">VALUATION LAB</div>

          <h1>Rated Price Intelligence</h1>

          <p>
            This is the EDGEiQ ability layer:
            fair price,
            market price,
            overlay quality,
            uncertainty,
            confidence
            and valuation integrity.
          </p>
        </div>

        <div className="edgeiq-valuation-warning">
          Weak pricing creates fake overlays.
          Strong pricing creates executable market intelligence.
        </div>
      </div>

      <div className="edgeiq-command-grid">
        <div className="edgeiq-stat-card">
          <div className="label">ACTIVE RUNNERS</div>
          <div className="value emerald">{active.length}</div>
          <div className="sub">excluding scratchings</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">VALUATION SIGNALS</div>
          <div className="value blue">
            {ranked.filter((r) => r.computed_overlay >= 5).length}
          </div>
          <div className="sub">overlay threshold met</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">ELITE OVERLAYS</div>
          <div className="value purple">
            {ranked.filter((r) => r.valuation_tier === "ELITE").length}
          </div>
          <div className="sub">high confidence value</div>
        </div>

        <div className="edgeiq-stat-card">
          <div className="label">TOP OVERLAY</div>
          <div className="value gold">
            {topRows[0]?.horse || "-"}
          </div>
          <div className="sub">
            {(topRows[0]?.computed_overlay ?? 0).toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="edgeiq-panel">
        <div className="edgeiq-panel-title">
          VALUATION EDGE TABLE
        </div>

        <div className="edgeiq-valuation-table">

          <div className="edgeiq-valuation-header">
            <div>#</div>
            <div>RUNNER</div>
            <div>MARKET</div>
            <div>RATED</div>
            <div>OVERLAY</div>
            <div>CONF</div>
            <div>TIER</div>
          </div>

          {topRows.map((row, idx) => (
            <div
              key={`${row.horse}-${idx}`}
              className={`edgeiq-valuation-row ${row.valuation_tier.toLowerCase()}`}
            >

              <div className="rank">
                {idx + 1}
              </div>

              <div className="runner">
                <div className="horse">
                  {text(row.horse)}
                </div>

                <div className="meta">
                  {text(row.jockey) || "JOCKEY"}
                </div>
              </div>

              <div className="market">
                {(marketPrice(row) ?? 0).toFixed(2)}
              </div>

              <div className="rated">
                {(ratedPrice(row) ?? 0).toFixed(2)}
              </div>

              <div className="overlay">
                {row.computed_overlay.toFixed(1)}%
              </div>

              <div className="confidence">
                {row.computed_confidence.toFixed(0)}
              </div>

              <div className={`tier ${row.valuation_tier.toLowerCase()}`}>
                {row.valuation_tier}
              </div>

            </div>
          ))}

        </div>
      </div>
    </div>
  );
}
