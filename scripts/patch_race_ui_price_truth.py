from pathlib import Path
import re

path = Path(r".\src\App.tsx")
text = path.read_text(encoding="utf-8")

# ====================================================================================
# RACE GRID HEADERS
# ====================================================================================

text = text.replace(
'''                    <span>LIVE</span>
                    <span>FAIR</span>
                    <span>EDGE</span>
                    <span>MAP</span>
                    <span>ACTION</span>''',
'''                    <span>LIVE</span>
                    <span>TRUE</span>
                    <span>EDGE</span>
                    <span>CONF</span>
                    <span>ACTION</span>'''
)

# ====================================================================================
# RACE ROW CELLS
# ====================================================================================

pattern = re.compile(
r'''<span className="price">\{row\.marketPrice \? row\.marketPrice\.toFixed\(2\) : "-"\}</span>\s*
\s*<span className="price">\{row\.ratedPrice \? row\.ratedPrice\.toFixed\(2\) : "-"\}</span>\s*
\s*<strong className=\{edge !== null && edge > 0 \? "edge-pos" : "edge-muted"\}>\s*
\s*\{edge === null \? "-" : `\$\{edge\.toFixed\(1\)\}%`\}\s*
\s*</strong>\s*
\s*<span className="map">\{map\}</span>\s*
\s*<span className=\{`action action-\$\{action\.toLowerCase\(\)\}`\}>\{action\}</span>''',
re.MULTILINE
)

replacement = '''<span className="price">
                            {row.live_price ?? (row.marketPrice ? row.marketPrice.toFixed(2) : "-")}
                          </span>

                          <span className="price truth-price">
                            {row.adjusted_fair_price
                              ? Number(row.adjusted_fair_price).toFixed(2)
                              : (row.ratedPrice ? row.ratedPrice.toFixed(2) : "-")}
                          </span>

                          <strong
                            className={
                              row.adjusted_edge_pct != null &&
                              Number(row.adjusted_edge_pct) > 0
                                ? "edge-pos"
                                : "edge-muted"
                            }
                          >
                            {row.adjusted_edge_pct != null
                              ? `${Number(row.adjusted_edge_pct).toFixed(1)}%`
                              : (edge === null ? "-" : `${edge.toFixed(1)}%`)}
                          </strong>

                          <span className="map">
                            {row.confidence_score ?? row.modelConfidenceScore ?? "-"}
                          </span>

                          <span
                            className={`action action-${String(
                              row.execution_action ?? action
                            ).toLowerCase()}`}
                            title={row.price_truth_reason ?? ""}
                          >
                            {row.execution_action ?? action}
                          </span>'''

text = pattern.sub(replacement, text)

path.write_text(text, encoding="utf-8")

print("APP PRICE TRUTH UI PATCHED")
