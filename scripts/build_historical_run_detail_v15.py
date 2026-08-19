from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_HISTORICAL_RUN_DETAIL_V15_20260709.tsx")
backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

start = text.find("function RunInvestigationReport({ run }: { run: any }) {")
end = text.find("function ProfessionalFormTable", start)

new_func = r'''function RunInvestigationReport({ run }: { run: any }) {
  const [showCompare, setShowCompare] = useState(false);
  const official = run.professionalForm?.official ?? {};
  const evidence = run.professionalForm?.evidence ?? {};
  const match = score(run);

  return (
    <tr className="eiq-form-report-row">
      <td colSpan={22}>
        <section className="eiq-historical-run-detail-v15">
          <header>
            <div>
              <span>Historical Run Detail</span>
              <strong>{clean(official.date)} · {clean(official.track)} · {clean(official.distance)} · {clean(official.raceClass)}</strong>
              <p>{narrative(run)}</p>
            </div>
            <aside>
              <EvidenceBadge run={run} />
              <strong>{clean(official.finish)}</strong>
              <p>{clean(official.margin)} margin · SP {market(official.sp)}</p>
            </aside>
          </header>

          <div className="eiq-historical-detail-grid">
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
              <div className="eiq-historical-metrics">
                <RatingTile label="Run Rating™" value={evidence.runRating?.overall ?? run.edgeiqRunRating} />
                <RatingTile label="Race Strength™" value={evidence.raceStrength?.overall ?? run.edgeiqRaceStrength} />
                <RatingTile label="Pressure" value={evidence.pressure} sub="Race profile" />
                <RatingTile label="Tempo" value={evidence.tempo} sub="Race speed" />
              </div>
            </article>

            <article>
              <span>Run Notes</span>
              <strong>{verdict(run)}</strong>
              <p>{narrative(run)}</p>
              <ul>
                {reasons(run).slice(0, 3).map((x) => <li key={x}>✓ {x}</li>)}
              </ul>
            </article>
          </div>

          <section className="eiq-historical-actions-v15">
            <button type="button" onClick={() => setShowCompare(!showCompare)}>
              {showCompare ? "Hide Today Comparison" : "Compare to Today"}
            </button>
            <button type="button">Open Historical Race Book</button>
            <button type="button">Evidence Trace</button>
          </section>

          {showCompare ? (
            <section className="eiq-compare-to-today-v15">
              <header>
                <div>
                  <span>Compare to Today</span>
                  <strong>Does this historical run transfer to today’s assignment?</strong>
                  <p>This section compares the selected historical run against today’s race. Use it after reviewing what happened in the original race.</p>
                </div>
                <aside>
                  <span>Assignment Match</span>
                  <MatchBar value={match} />
                </aside>
              </header>

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

if start != -1 and end != -1:
    text = text[:start] + new_func + text[end:]
else:
    raise SystemExit("Could not find RunInvestigationReport block")

tsx.write_text(text, encoding="utf-8")
print("[EDGEIQ] Historical Run Detail V15 applied")
print(f"[EDGEIQ] checkpoint: {backup}")
