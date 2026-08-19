from pathlib import Path

path = Path(r".\src\edgeiq-speedmap-v2.css")

path.write_text(r'''
.edgeiq-speed-benchmark {
  background: #050b12;
  border: 1px solid rgba(51, 65, 85, 0.95);
  border-radius: 16px;
  overflow: hidden;
}

.edgeiq-speed-benchmark-head {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(420px, 1.2fr);
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.7);
  background: linear-gradient(90deg, rgba(2, 6, 12, 0.98), rgba(15, 23, 42, 0.78));
}

.edgeiq-speed-kicker {
  color: #34d399;
  font-size: 10px;
  font-weight: 950;
  letter-spacing: 0.18em;
}

.edgeiq-speed-benchmark-head h2 {
  margin: 4px 0 2px;
  color: #f8fafc;
  font-size: 24px;
  font-weight: 950;
  line-height: 1;
}

.edgeiq-speed-benchmark-head p {
  margin: 0;
  color: #94a3b8;
  font-size: 11px;
}

.edgeiq-speed-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.edgeiq-speed-summary div {
  border: 1px solid rgba(71, 85, 105, 0.8);
  border-radius: 10px;
  background: #0f172a;
  padding: 8px 10px;
  min-height: 50px;
}

.edgeiq-speed-summary span {
  display: block;
  color: #64748b;
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.edgeiq-speed-summary strong {
  display: block;
  margin-top: 4px;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 950;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edgeiq-speed-table {
  display: block;
  padding: 0 12px 12px;
  overflow: auto;
}

.edgeiq-speed-row {
  position: relative;
  display: grid;
  grid-template-columns: 38px 220px 120px 70px 54px repeat(10, minmax(42px, 1fr));
  align-items: center;
  min-height: 40px;
  width: 100%;
  border: 0;
  border-bottom: 1px solid rgba(51, 65, 85, 0.55);
  background: transparent;
  color: #cbd5e1;
  text-align: left;
  font: inherit;
}

.edgeiq-speed-row:not(.edgeiq-speed-header):hover {
  background: rgba(15, 23, 42, 0.82);
}

.edgeiq-speed-row.selected {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.18), rgba(15, 23, 42, 0.92));
}

.edgeiq-speed-header {
  min-height: 38px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: #08111d;
  position: sticky;
  top: 0;
  z-index: 2;
}

.edgeiq-speed-row > span {
  padding: 0 8px;
  font-size: 10px;
  font-weight: 800;
  min-width: 0;
}

.edgeiq-speed-row .horse {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edgeiq-speed-row .horse img {
  width: 19px;
  height: 19px;
  border-radius: 3px;
  flex: 0 0 19px;
}

.edgeiq-speed-row .horse strong {
  color: #f8fafc;
  font-size: 10px;
  font-weight: 950;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edgeiq-speed-row .spd {
  color: #7dd3fc;
  font-size: 11px;
  font-weight: 950;
}

.edgeiq-speed-row .scale {
  color: #94a3b8;
  text-align: center;
  font-size: 10px;
}

.edgeiq-speed-row .bar-cell {
  position: absolute;
  left: calc(38px + 220px + 120px + 70px + 54px);
  right: 8px;
  top: 9px;
  bottom: 9px;
  padding: 0;
  border-left: 1px dashed rgba(148, 163, 184, 0.24);
  background:
    repeating-linear-gradient(
      90deg,
      transparent 0,
      transparent calc(10% - 1px),
      rgba(148, 163, 184, 0.14) calc(10% - 1px),
      rgba(148, 163, 184, 0.14) 10%
    );
  pointer-events: none;
}

.edgeiq-speed-row .bar-cell i {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(34, 197, 94, 0.68), rgba(74, 222, 128, 0.92));
  box-shadow: inset 0 0 0 1px rgba(187, 247, 208, 0.08);
}

@media (max-width: 1400px) {
  .edgeiq-speed-benchmark-head {
    grid-template-columns: 1fr;
  }

  .edgeiq-speed-row {
    grid-template-columns: 32px 170px 90px 56px 44px repeat(10, minmax(34px, 1fr));
  }

  .edgeiq-speed-row .bar-cell {
    left: calc(32px + 170px + 90px + 56px + 44px);
  }
}
''', encoding="utf-8")

print("WROTE EDGEIQ STYLE 1 SPEEDMAP CSS")
