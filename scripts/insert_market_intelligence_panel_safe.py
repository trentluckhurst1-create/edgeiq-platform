from pathlib import Path

path = Path(r".\src\terminal\tabs\MarketTab.tsx")
text = path.read_text(encoding="utf-8")

helper_marker = "function renderFlucLadder"
helper_insert = r'''
function marketMovePct(row: MarketRunner): number | null {
  if (row.live === null || row.open === null || row.open <= 0) return null;
  return ((row.live - row.open) / row.open) * 100;
}

function bookPercent(rows: MarketRunner[], priceKey: "live" | "open"): number | null {
  const priced = rows.filter((row) => !row.isScratched && row[priceKey] !== null && Number(row[priceKey]) > 0);
  if (!priced.length) return null;
  return priced.reduce((sum, row) => sum + (1 / Number(row[priceKey])), 0) * 100;
}

'''

if "function marketMovePct" not in text:
    text = text.replace(helper_marker, helper_insert + helper_marker)

old_block = '''  const favourite = rows.find((row) => row.live !== null) ?? null;
  const activeRows = rows.filter((row) => !row.isScratched);
  const pricedCount = activeRows.filter((row) => row.live !== null).length;
  const overround = activeRows.reduce((sum, row) => sum + (row.live ? 1 / row.live : 0), 0) * 100;
'''

new_block = '''  const activeRows = rows.filter((row) => !row.isScratched);
  const favourite = activeRows.find((row) => row.live !== null) ?? null;
  const pricedCount = activeRows.filter((row) => row.live !== null).length;
  const overround = bookPercent(rows, "live");
  const openOverround = bookPercent(rows, "open");

  const firmers = activeRows
    .map((row) => ({ row, move: marketMovePct(row) }))
    .filter((item): item is { row: MarketRunner; move: number } => item.move !== null && item.move < 0)
    .sort((a, b) => a.move - b.move)
    .slice(0, 4);

  const drifters = activeRows
    .map((row) => ({ row, move: marketMovePct(row) }))
    .filter((item): item is { row: MarketRunner; move: number } => item.move !== null && item.move > 0)
    .sort((a, b) => b.move - a.move)
    .slice(0, 4);

  const stableCount = activeRows.filter((row) => {
    const move = marketMovePct(row);
    return move === null || Math.abs(move) < 1;
  }).length;

  const pressure =
    firmers.length > drifters.length + 1
      ? "BULLISH"
      : drifters.length > firmers.length + 1
        ? "BEARISH"
        : "BALANCED";

  const bookShape =
    overround !== null && openOverround !== null
      ? overround < openOverround
        ? "COMPRESSING"
        : overround > openOverround
          ? "EXPANDING"
          : "UNCHANGED"
      : "-";

  const velocityLeader = [...firmers, ...drifters].sort((a, b) => Math.abs(b.move) - Math.abs(a.move))[0];
'''

if old_block not in text:
    raise SystemExit("Could not find summary calculation block. No changes made.")
text = text.replace(old_block, new_block)

text = text.replace(
    '<div className="terminal-metric warning"><span>Book %</span><strong>{overround ? `${overround.toFixed(1)}%` : "-"}</strong></div>',
    '<div className="terminal-metric warning"><span>Book %</span><strong>{overround !== null ? `${overround.toFixed(1)}%` : "-"}</strong></div>'
)

table_start = '''        {!!rows.length ? (
          <div className="terminal-table-wrap bookmaker-table-wrap">
'''

table_start_new = '''        {!!rows.length ? (
          <>
            <div className="terminal-table-wrap bookmaker-table-wrap">
'''

if table_start not in text:
    raise SystemExit("Could not find table start block. No changes made.")
text = text.replace(table_start, table_start_new)

table_end = '''            </table>
          </div>
        ) : null}
'''

panel = r'''            </table>
          </div>

          <div className="market-intel-panel">
            <div className="market-intel-head">
              <div>
                <div className="terminal-kicker">Market Intelligence</div>
                <div className="terminal-muted">Open-to-live pressure, firmers, drifters and book shape</div>
              </div>
              <div className={`terminal-chip ${pressure === "BULLISH" ? "positive" : pressure === "BEARISH" ? "negative" : "neutral"}`}>
                {pressure}
              </div>
            </div>

            <div className="market-intel-grid">
              <div className="market-intel-card">
                <div className="market-intel-title terminal-positive">Strongest Firmers</div>
                {firmers.length ? firmers.map(({ row, move }) => (
                  <div className="market-intel-row" key={`firm-${row.id}`}>
                    <span>{row.horse}</span>
                    <strong>{money(row.open)} → {money(row.live)}</strong>
                    <em className="terminal-positive">{pct(move)}</em>
                  </div>
                )) : <div className="market-intel-empty">No firmers detected</div>}
              </div>

              <div className="market-intel-card">
                <div className="market-intel-title terminal-negative">Strongest Drifters</div>
                {drifters.length ? drifters.map(({ row, move }) => (
                  <div className="market-intel-row" key={`drift-${row.id}`}>
                    <span>{row.horse}</span>
                    <strong>{money(row.open)} → {money(row.live)}</strong>
                    <em className="terminal-negative">{pct(move)}</em>
                  </div>
                )) : <div className="market-intel-empty">No drifters detected</div>}
              </div>

              <div className="market-intel-card">
                <div className="market-intel-title">Race Pressure</div>
                <div className="market-pressure-grid">
                  <div><span>Firmers</span><strong className="terminal-positive">{firmers.length}</strong></div>
                  <div><span>Drifters</span><strong className="terminal-negative">{drifters.length}</strong></div>
                  <div><span>Stable</span><strong>{stableCount}</strong></div>
                </div>
                <div className="market-intel-note">Signal: {pressure}</div>
              </div>

              <div className="market-intel-card">
                <div className="market-intel-title">Book Shape</div>
                <div className="market-intel-row">
                  <span>Open Book</span>
                  <strong>{openOverround !== null ? `${openOverround.toFixed(1)}%` : "-"}</strong>
                </div>
                <div className="market-intel-row">
                  <span>Live Book</span>
                  <strong>{overround !== null ? `${overround.toFixed(1)}%` : "-"}</strong>
                </div>
                <div className="market-intel-note">Status: {bookShape}</div>
              </div>

              <div className="market-intel-card market-intel-card-wide">
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
            </div>
          </div>
          </>
        ) : null}
'''

if table_end not in text:
    raise SystemExit("Could not find table end block. No changes made.")
text = text.replace(table_end, panel)

path.write_text(text, encoding="utf-8")
print("MARKET INTELLIGENCE PANEL SAFELY INSERTED")
