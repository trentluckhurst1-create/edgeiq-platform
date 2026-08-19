from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_RUN_DETAIL_REBUILD_V17.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_RUN_DETAIL_REBUILD_V17.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

start = text.find("function RunInvestigationReport({ run }: { run: any }) {")
end = text.find("function ProfessionalFormTable", start)

new_func = r'''function RunInvestigationReport({ run }: { run: any }) {
  const [showCompare, setShowCompare] = useState(false);
  const official = run.professionalForm?.official ?? {};
  const evidence = run.professionalForm?.evidence ?? {};

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={22}>
        <section className="eiq-run-detail-v17">
          <header className="eiq-run-detail-v17__header">
            <div>
              <span>Historical Run Detail</span>
              <strong>{clean(official.track)} · {clean(official.distance)} · {clean(official.raceClass)}</strong>
              <p>{clean(official.date)} · {clean(official.condition)}</p>
            </div>

            <div className="eiq-run-detail-v17__result">
              <b>{clean(official.finish)}</b>
              <em>{clean(official.margin)} margin · SP {market(official.sp)}</em>
            </div>
          </header>

          <div className="eiq-run-detail-v17__grid">
            <article>
              <span>Race Context</span>
              <dl>
                <div><dt>Track</dt><dd>{clean(official.track)}</dd></div>
                <div><dt>Distance</dt><dd>{clean(official.distance)}</dd></div>
                <div><dt>Class</dt><dd>{clean(official.raceClass)}</dd></div>
                <div><dt>Condition</dt><dd>{clean(official.condition)}</dd></div>
                <div><dt>Barrier</dt><dd>{clean(official.barrier)}</dd></div>
                <div><dt>Weight</dt><dd>{weight(official.weight)}</dd></div>
                <div><dt>Jockey</dt><dd>{clean(official.jockey)}</dd></div>
                <div><dt>Field</dt><dd>{clean(official.fieldSize)}</dd></div>
              </dl>
            </article>

            <article>
              <span>Performance</span>
              <div className="eiq-run-detail-v17__metrics">
                <div><small>Run Rating™</small><strong>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</strong><em>{ratingBand(evidence.runRating?.overall ?? run.edgeiqRunRating)}</em></div>
                <div><small>Race Strength™</small><strong>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</strong><em>{ratingBand(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</em></div>
                <div><small>Pressure</small><strong>{clean(evidence.pressure)}</strong><em>Race profile</em></div>
                <div><small>Tempo</small><strong>{clean(evidence.tempo)}</strong><em>Race speed</em></div>
              </div>
            </article>

            <article>
              <span>EDGEIQ Run Notes</span>
              <strong>{verdict(run)}</strong>
              <p>{narrative(run)}</p>
              <ul>
                {reasons(run).slice(0, 3).map((x) => <li key={x}>✓ {x}</li>)}
              </ul>
            </article>
          </div>

          <footer className="eiq-run-detail-v17__actions">
            <button type="button" onClick={() => setShowCompare(!showCompare)}>
              {showCompare ? "Hide Compare" : "Compare to Today"}
            </button>
            <button type="button">Open Historical Race Book</button>
            <button type="button">Evidence Trace</button>
          </footer>

          {showCompare ? (
            <section className="eiq-run-detail-v17__compare">
              <SimilarityEnginePanel run={run} />
              <ComparisonTable run={run} />
              <FactorScorePanel run={run} />
              <EvidenceStoryPanel run={run} />
              <VerdictPanel run={run} />
            </section>
          ) : null}
        </section>
      </td>
    </tr>
  );
}

'''

if start == -1 or end == -1:
    raise SystemExit("Could not locate RunInvestigationReport block")

text = text[:start] + new_func + text[end:]
tsx.write_text(text, encoding="utf-8")

css_add = r'''

/* EDGEIQ RUN DETAIL REBUILD — V17 */
.eiq-form-guide-table .eiq-form-report-row > td {
  padding: 0 !important;
  height: auto !important;
  white-space: normal !important;
  overflow: visible !important;
}

.eiq-run-detail-v17 {
  display: block !important;
  padding: 18px !important;
  border-left: 3px solid rgba(85,122,168,.78) !important;
  background: linear-gradient(180deg, rgba(6,11,15,.96), rgba(2,6,8,.96)) !important;
}

.eiq-run-detail-v17__header {
  display: grid !important;
  grid-template-columns: minmax(0,1fr) 240px !important;
  gap: 18px !important;
  align-items: center !important;
  padding-bottom: 16px !important;
  border-bottom: 1px solid rgba(95,134,184,.16) !important;
}

.eiq-run-detail-v17 span {
  display: block !important;
  color: #6fa3d8 !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  letter-spacing: .16em !important;
  text-transform: uppercase !important;
}

.eiq-run-detail-v17__header strong {
  display: block !important;
  margin-top: 7px !important;
  color: #f4f8f8 !important;
  font-size: 22px !important;
  line-height: 1.2 !important;
}

.eiq-run-detail-v17 p {
  margin: 8px 0 0 !important;
  color: rgba(244,248,248,.66) !important;
  font-size: 12px !important;
  line-height: 1.45 !important;
}

.eiq-run-detail-v17__result {
  display: grid !important;
  justify-items: end !important;
  gap: 6px !important;
}

.eiq-run-detail-v17__result b {
  color: #f4f8f8 !important;
  font-size: 28px !important;
}

.eiq-run-detail-v17__result em {
  color: rgba(244,248,248,.62) !important;
  font-size: 12px !important;
  font-style: normal !important;
  font-weight: 800 !important;
}

.eiq-run-detail-v17__grid {
  display: grid !important;
  grid-template-columns: 1fr 1.2fr 1fr !important;
  gap: 12px !important;
  margin-top: 14px !important;
}

.eiq-run-detail-v17__grid article {
  min-height: 210px !important;
  padding: 15px !important;
  border: 1px solid rgba(95,134,184,.14) !important;
  background: rgba(255,255,255,.014) !important;
}

.eiq-run-detail-v17 dl {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0,1fr)) !important;
  gap: 12px 16px !important;
  margin: 14px 0 0 !important;
}

.eiq-run-detail-v17 dt {
  color: rgba(111,163,216,.9) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  letter-spacing: .12em !important;
  text-transform: uppercase !important;
}

.eiq-run-detail-v17 dd {
  margin: 4px 0 0 !important;
  color: #f4f8f8 !important;
  font-size: 12px !important;
  font-weight: 800 !important;
}

.eiq-run-detail-v17__metrics {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0,1fr)) !important;
  gap: 10px !important;
  margin-top: 14px !important;
}

.eiq-run-detail-v17__metrics div {
  min-height: 78px !important;
  padding: 12px !important;
  border: 1px solid rgba(95,134,184,.13) !important;
  background: rgba(85,122,168,.08) !important;
}

.eiq-run-detail-v17__metrics small {
  display: block !important;
  color: #6fa3d8 !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  letter-spacing: .12em !important;
  text-transform: uppercase !important;
}

.eiq-run-detail-v17__metrics strong {
  display: block !important;
  margin-top: 8px !important;
  color: #f4f8f8 !important;
  font-size: 20px !important;
}

.eiq-run-detail-v17__metrics em {
  display: block !important;
  margin-top: 2px !important;
  color: rgba(244,248,248,.55) !important;
  font-size: 10px !important;
  font-style: normal !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.eiq-run-detail-v17__grid article > strong {
  display: block !important;
  margin-top: 12px !important;
  color: #f4f8f8 !important;
  font-size: 16px !important;
}

.eiq-run-detail-v17 ul {
  display: grid !important;
  gap: 7px !important;
  margin: 12px 0 0 !important;
  padding: 0 !important;
  list-style: none !important;
  color: rgba(244,248,248,.72) !important;
  font-size: 12px !important;
}

.eiq-run-detail-v17__actions {
  display: flex !important;
  gap: 10px !important;
  margin-top: 14px !important;
  padding-top: 14px !important;
  border-top: 1px solid rgba(95,134,184,.16) !important;
}

.eiq-run-detail-v17__actions button {
  height: 34px !important;
  padding: 0 14px !important;
  border: 1px solid rgba(85,122,168,.34) !important;
  border-radius: 999px !important;
  background: rgba(85,122,168,.09) !important;
  color: #cfe2ff !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  cursor: pointer !important;
}

.eiq-run-detail-v17__actions button:first-child {
  background: rgba(85,122,168,.18) !important;
  color: #ffffff !important;
}

.eiq-run-detail-v17__compare {
  margin-top: 14px !important;
  padding-top: 14px !important;
  border-top: 1px solid rgba(95,134,184,.18) !important;
}

@media (max-width: 1350px) {
  .eiq-run-detail-v17__header,
  .eiq-run-detail-v17__grid {
    grid-template-columns: 1fr !important;
  }

  .eiq-run-detail-v17__result {
    justify-items: start !important;
  }
}
'''

if "EDGEIQ RUN DETAIL REBUILD — V17" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")

print("[EDGEIQ] Run Detail Rebuild V17 applied")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
