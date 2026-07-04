from pathlib import Path

path = Path(r".\src\terminal\tabs\MarketTab.tsx")
text = path.read_text(encoding="utf-8")

old = '''  const velocityLeader = [...firmers, ...drifters].sort((a, b) => Math.abs(b.move) - Math.abs(a.move))[0];
'''

new = '''  const strongestSupport = firmers[0] ?? null;
  const strongestOpposition = drifters[0] ?? null;
  const marketConfidence =
    pricedCount >= Math.max(1, activeRows.length - 1) && firmers.length + drifters.length >= 3
      ? "HIGH"
      : pricedCount >= Math.max(1, Math.floor(activeRows.length * 0.7))
        ? "MEDIUM"
        : "LOW";
'''

if old not in text:
    raise SystemExit("Could not find velocityLeader block. No changes made.")

text = text.replace(old, new)

old_card = '''              <div className="market-intel-card market-intel-card-wide">
                <div className="market-intel-title">Velocity Leader</div>
                {velocityLeader ? (
                  <div className="market-intel-velocity">
                    <span>{velocityLeader.row.horse}</span>
                    <strong>{money(velocityLeader.row.open)} → {money(velocityLeader.row.live)}</strong>
                    <em className={velocityLeader.move < 0 ? "terminal-positive" : "terminal-negative"}>{pct(velocityLeader.move)}</em>
                  </div>
                ) : (
                  <div className="market-intel-empty">No meaningful velocity detected</div>
                )}
              </div>
'''

new_card = '''              <div className="market-intel-card market-intel-card-wide">
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

if old_card not in text:
    raise SystemExit("Could not find velocity leader card. No changes made.")

text = text.replace(old_card, new_card)
path.write_text(text, encoding="utf-8")
print("MARKET SUMMARY CARD INSERTED")
