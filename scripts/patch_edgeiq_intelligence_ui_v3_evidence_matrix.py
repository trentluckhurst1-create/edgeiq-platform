from pathlib import Path

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

backup = Path(r".\src\components\RaceIntelligenceScreen_CHECKPOINT_INTELLIGENCE_UI_V3_EVIDENCE_MATRIX_20260620.tsx")
backup.write_text(text, encoding="utf-8")

if "EDGEIQ RUNNER EVIDENCE MATRIX" in text:
    print("[UI_V3_EVIDENCE_MATRIX] already installed")
    raise SystemExit(0)

marker = "DECISION BOARD"
idx = text.find(marker)
if idx < 0:
    raise RuntimeError("Could not find DECISION BOARD marker")

section_start = text.rfind("<section", 0, idx)
if section_start < 0:
    raise RuntimeError("Could not find section before DECISION BOARD")

evidence_block = r'''
        <section style={{ ...panelStyle, display: "grid", gap: 10 }}>
          <div style={titleStyle}>
            <span>EDGEiQ RUNNER EVIDENCE MATRIX</span>
            <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>
              RANK | WIN | FAIR | TAB | EDGE | DNA | PROJECTION | SECTIONALS | LATE | CONFIDENCE | CALL
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "52px minmax(180px,1.7fr) 72px 78px 78px 82px 76px 92px 92px 76px 96px 100px",
              gap: 6,
              padding: "0 10px 8px",
              color: "#9fb3d9",
              fontSize: 10,
              fontWeight: 900,
              textTransform: "uppercase",
              letterSpacing: ".08em",
            }}
          >
            <span>Rank</span>
            <span>Runner</span>
            <span>Win %</span>
            <span>Fair</span>
            <span>TAB</span>
            <span>Edge</span>
            <span>DNA</span>
            <span>Proj Gap</span>
            <span>Sectionals</span>
            <span>Late</span>
            <span>Confidence</span>
            <span>Call</span>
          </div>

          <div style={{ display: "grid", gap: 6 }}>
            {enriched.map((item, evidenceIndex) => {
              const r = item.row;
              const d = item.dna;
              const win = winPct(r, item.bet);
              const fair = fairPrice(r, item.bet);
              const live = livePrice(r, item.bet);
              const edge = edgePct(r, item.bet);
              const dnaScore =
                firstNum(d, ["dna_v6_2_score", "dna_score", "runner_dna_score"]) ??
                firstNum(r, ["dna_v6_2_score", "runner_dna_score"]);
              const projGap = firstNum(r, ["projection_gap_V6_1_RESEARCH", "projection_gap_v5_2", "projection_gap"]);
              const sectionals =
                firstNum(r, ["sectional_weapon_score", "sectional_score"]) ??
                firstNum(d, ["sectional_score"]);
              const late =
                firstNum(r, ["late_power_score", "late_power_index"]) ??
                firstNum(d, ["late_power_score", "late_power_index"]);
              const confidence =
                firstNum(r, ["confidence_score", "confidence_score_v1"]) ??
                firstNum(item.bet, ["confidence_score"]);
              const modelRank =
                firstText(r, ["V6_1_RESEARCH_price_rank", "price_rank", "final_probability_rank_used"], "") ||
                firstText(d, ["runner_dna_v6_2_rank_in_race", "runner_dna_rank_in_race"], "") ||
                String(evidenceIndex + 1);
              const finalCall = limitedDecisionValue(item);
              const selectedRowKey = `${track(r)}|${raceNo(r)}|${cleanHorse(horse(r))}`;
              const isActive = selectedRowKey === selectedKey;

              const bar = (value: number | null, max = 100) => (
                <span style={{ display: "grid", gap: 3 }}>
                  <span>{value === null ? "—" : value.toFixed(value >= 10 ? 1 : 2)}</span>
                  <span style={barTrackStyle}>
                    <span style={barFill(value === null ? 0 : (value / max) * 100, value === null ? "#475569" : cellTone(String(value)))} />
                  </span>
                </span>
              );

              return (
                <button
                  key={`evidence-${selectedRowKey}`}
                  type="button"
                  onClick={() => setSelectedKey(selectedRowKey)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "52px minmax(180px,1.7fr) 72px 78px 78px 82px 76px 92px 92px 76px 96px 100px",
                    gap: 6,
                    alignItems: "center",
                    width: "100%",
                    border: `1px solid ${isActive ? "rgba(91,229,169,.38)" : "rgba(80,120,180,.20)"}`,
                    borderRadius: 10,
                    padding: "9px 10px",
                    background: isActive ? "rgba(36,92,74,.36)" : "rgba(5,12,22,.66)",
                    color: "#dbeafe",
                    fontSize: 11,
                    fontWeight: 850,
                    textAlign: "left",
                    cursor: "pointer",
                  }}
                >
                  <span style={{ color: "#7dd3fc" }}>#{modelRank}</span>
                  <span>
                    <strong style={{ display: "block", color: "#eaf2ff" }}>{horse(r)}</strong>
                    <em style={{ color: "#8ea6c9", fontSize: 10, fontStyle: "italic" }}>{firstText(r, ["trainer"], "")}</em>
                  </span>
                  <span>{pct(win)}</span>
                  <span>{money(fair)}</span>
                  <span>{money(live)}</span>
                  <span style={{ color: edge === null ? "#94a3b8" : edge > 0 ? "#3ee68f" : "#f87171" }}>
                    {pct(edge)}
                  </span>
                  <span>{bar(dnaScore)}</span>
                  <span style={{ color: projGap === null ? "#94a3b8" : projGap > 0 ? "#3ee68f" : "#f87171" }}>
                    {projGap === null ? "—" : signed(projGap)}
                  </span>
                  <span>{bar(sectionals)}</span>
                  <span>{bar(late)}</span>
                  <span>{bar(confidence)}</span>
                  <span style={{ color: cellTone(finalCall), fontWeight: 950 }}>{finalCall}</span>
                </button>
              );
            })}
          </div>
        </section>

'''

text = text[:section_start] + evidence_block + text[section_start:]
text = text.replace("DECISION BOARD", "ADVANCED RUNNER TABLE", 1)

path.write_text(text, encoding="utf-8")
print("[UI_V3_EVIDENCE_MATRIX] COMPLETE")
print(f"backup={backup}")
print(f"updated={path}")
