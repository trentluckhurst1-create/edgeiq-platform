from pathlib import Path

app = Path(r".\src\App.tsx")

text = app.read_text(encoding="utf-8")

text = text.replace(
    "RUNNER DECISION LIST",
    "RUNNER DECISION LADDER"
)

text = text.replace(
    "className=\"edgeiq-race-left\"",
    "className=\"edgeiq-race-left edgeiq-runner-ladder\""
)

text = text.replace(
    """<div className="edgeiq-runner-row-name">""",
    """<div className="edgeiq-runner-row-name">
                      <span className="edgeiq-runner-rank">#{idx + 1}</span>"""
)

text = text.replace(
    """<div className="edgeiq-runner-row-meta">""",
    """<div className="edgeiq-runner-row-meta">
                      <span className="edgeiq-live-price">
                        {row.sportsbet_price || row.best_price || "-"}
                      </span>
                      <span className="edgeiq-rated-price">
                        {row.rated_price || row.fair_price || "-"}
                      </span>"""
)

css = Path(r".\src\terminal\layout\terminal-shell.css")

css_text = css.read_text(encoding="utf-8")

css_text += """

/* RUNNER LADDER REBUILD */

.edgeiq-runner-ladder {
  min-width: 260px;
  max-width: 260px;
}

.edgeiq-runner-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-right: 8px;
  border-radius: 4px;
  background: rgba(59,130,246,0.18);
  border: 1px solid rgba(59,130,246,0.35);
  color: #93c5fd;
  font-size: 10px;
  font-weight: 800;
}

.edgeiq-live-price {
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
}

.edgeiq-rated-price {
  color: #6ee7b7;
  font-size: 11px;
  font-weight: 700;
}

.edgeiq-runner-row {
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.edgeiq-runner-row:hover {
  background: rgba(59,130,246,0.08);
}

.edgeiq-runner-row-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
"""

css.write_text(css_text, encoding="utf-8")

app.write_text(text, encoding="utf-8")

print("RUNNER LADDER V1 APPLIED")
