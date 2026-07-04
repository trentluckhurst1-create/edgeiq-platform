from pathlib import Path

css_path = Path(r".\src\index.css")
css = css_path.read_text(encoding="utf-8")

css += """

/* SELECTED RUNNER INTELLIGENCE PANEL */
.edgeiq-runner-intel {
  padding: 12px !important;
  height: 100%;
  overflow-y: auto;
}

.runner-intel-head {
  display: grid;
  grid-template-columns: 46px minmax(0,1fr);
  gap: 10px;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(71,85,105,.55);
}

.runner-intel-head img {
  width: 42px;
  height: 42px;
  object-fit: contain;
}

.runner-intel-head h2 {
  margin: 2px 0;
  font-size: 16px;
  line-height: 1.05;
  color: #f8fafc;
}

.runner-intel-head p {
  margin: 0;
  font-size: 10px;
  color: #94a3b8;
}

.runner-intel-price-grid,
.runner-intel-grid,
.runner-intel-records {
  display: grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 7px;
  margin-top: 10px;
}

.runner-intel-price-grid div,
.runner-intel-grid div,
.runner-intel-records div {
  border: 1px solid rgba(51,65,85,.75);
  background: rgba(15,23,42,.72);
  border-radius: 10px;
  padding: 8px;
}

.runner-intel-price-grid span,
.runner-intel-grid span,
.runner-intel-records span {
  display: block;
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: .14em;
  color: #64748b;
  font-weight: 900;
}

.runner-intel-price-grid strong,
.runner-intel-grid strong,
.runner-intel-records strong {
  display: block;
  margin-top: 3px;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 950;
}

.runner-intel-section {
  margin-top: 12px;
}

.runner-intel-runs {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.runner-intel-runs div {
  display: grid;
  grid-template-columns: 58px minmax(0,1fr) 48px 36px 42px;
  gap: 6px;
  align-items: center;
  border: 1px solid rgba(51,65,85,.6);
  background: rgba(2,8,16,.52);
  border-radius: 8px;
  padding: 7px;
  font-size: 10px;
}

.runner-intel-runs strong {
  color: #f8fafc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.runner-intel-runs span {
  color: #94a3b8;
}

.runner-intel-runs em {
  color: #7dd3fc;
  font-style: normal;
  font-weight: 900;
  text-align: right;
}

"""

css_path.write_text(css, encoding="utf-8")

print("=" * 80)
print("RUNNER INTELLIGENCE CSS ADDED")
print("=" * 80)
