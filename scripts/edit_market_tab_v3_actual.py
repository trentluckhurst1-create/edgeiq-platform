from pathlib import Path
import re

path = Path("src/terminal/tabs/MarketTab.tsx")
s = path.read_text(encoding="utf-8")

# Remove Market State top metric, leaving 3 cards
s = re.sub(
    r'\s*<div className="terminal-metric warning"><span>Market State</span><strong>\{marketState\}</strong></div>',
    '',
    s
)

s = s.replace('terminal-grid four bookmaker-summary', 'terminal-grid three bookmaker-summary')

# Upgrade story text block
s = re.sub(
    r'const story = `\$\{personalityCopy\(personality, favourite\?\.horse \|\| "The market leader"\)\} \$\{pricedRows\.length\} active runners are priced by TAB\. \$\{firmers\.length\} firming, \$\{drifters\.length\} drifting, \$\{stable\.length\} stable\.`;',
    '''const story =
    personality === "QUIET MARKET"
      ? `The TAB market remains stable with little meaningful movement. ${favourite?.horse || "The market leader"} continues to hold favouritism at ${money(favourite?.live ?? null)}. No significant support or drift has emerged and market conviction remains ${marketConfidence.toLowerCase()}.`
      : personality === "ACTIVE MARKET"
        ? `TAB prices are becoming more active approaching jump time. ${firmers.length} runner${firmers.length === 1 ? "" : "s"} firming and ${drifters.length} drifting as market sentiment begins to take shape.`
        : personality === "OPEN RACE"
          ? `TAB betting remains spread across the field with no runner fully controlling the market. The race currently presents a competitive market profile.`
          : `${personalityCopy(personality, favourite?.horse || "The market leader")} ${pricedRows.length} active runners are priced by TAB.`;''',
    s
)

# Rename TAB Coverage to Market Coverage
s = s.replace('<div className="market-intel-title">TAB Coverage</div>', '<div className="market-intel-title">Market Coverage</div>')

# Replace firmer/drifter cards with conditional single empty movers card
old = '''                <div className="market-intel-card">
                  <div className="market-intel-title terminal-positive">Biggest Firmer</div>
                  {strongestFirm ? (
                    <div className="market-intel-row">
                      <span>{strongestFirm.horse}</span>
                      <strong>{money(moveBase(strongestFirm))} → {money(strongestFirm.live)}</strong>
                    </div>
                  ) : <div className="market-intel-empty">No meaningful firmer detected</div>}
                </div>

                <div className="market-intel-card">
                  <div className="market-intel-title terminal-negative">Biggest Drifter</div>
                  {strongestDrift ? (
                    <div className="market-intel-row">
                      <span>{strongestDrift.horse}</span>
                      <strong>{money(moveBase(strongestDrift))} → {money(strongestDrift.live)}</strong>
                    </div>
                  ) : <div className="market-intel-empty">No meaningful drift detected</div>}
                </div>'''

new = '''                {!strongestFirm && !strongestDrift ? (
                  <div className="market-intel-card market-intel-card-wide">
                    <div className="market-intel-title">No Significant Market Movers</div>
                    <div className="market-intel-empty">No runners are currently showing meaningful TAB support or drift.</div>
                  </div>
                ) : (
                  <>
                    <div className="market-intel-card">
                      <div className="market-intel-title terminal-positive">Biggest Firmer</div>
                      {strongestFirm ? (
                        <div className="market-intel-row">
                          <span>{strongestFirm.horse}</span>
                          <strong>{money(moveBase(strongestFirm))} → {money(strongestFirm.live)}</strong>
                        </div>
                      ) : <div className="market-intel-empty">No meaningful firmer detected</div>}
                    </div>

                    <div className="market-intel-card">
                      <div className="market-intel-title terminal-negative">Biggest Drifter</div>
                      {strongestDrift ? (
                        <div className="market-intel-row">
                          <span>{strongestDrift.horse}</span>
                          <strong>{money(moveBase(strongestDrift))} → {money(strongestDrift.live)}</strong>
                        </div>
                      ) : <div className="market-intel-empty">No meaningful drift detected</div>}
                    </div>
                  </>
                )}'''

if old not in s:
    raise SystemExit("Could not find mover cards block. File differs from expected current MarketTab.")
s = s.replace(old, new)

# Remove Market Status column header
s = re.sub(r'\s*<th className="terminal-th terminal-cell-center">Market Status</th>', '', s)

# Remove Market Status cell
s = re.sub(
    r'\s*<td className="terminal-td terminal-cell-center">\s*<span className=\{`terminal-chip \$\{moveChipClass\(move\)\}`\}>\{status\}</span>\s*</td>',
    '',
    s
)

# Remove unused status const in row render
s = s.replace('                    const status = marketStatusFromMove(move);\n', '')

path.write_text(s, encoding="utf-8")
print("MARKET V3 actual edit complete")
