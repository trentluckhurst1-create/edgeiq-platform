from pathlib import Path

tsx = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/edgeiq-os/styles/edgeiqOsV2.css")

tsx_backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_SIMILARITY_ENGINE_V11_20260709.tsx")
css_backup = Path("src/edgeiq-os/styles/edgeiqOsV2_CHECKPOINT_BEFORE_SIMILARITY_ENGINE_V11_20260709.css")

tsx_backup.write_text(tsx.read_text(encoding="utf-8"), encoding="utf-8")
css_backup.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

text = tsx.read_text(encoding="utf-8")

anchor = '''function ComparisonTable({ run }: { run: any }) {'''

addition = r'''
function similarityScore(value: any, max = 100): number {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return 50;
  return Math.max(0, Math.min(max, n));
}

function SimilarityEnginePanel({ run }: { run: any }) {
  const evidence = run.professionalForm?.evidence ?? {};
  const official = run.professionalForm?.official ?? {};
  const match = score(run);

  const factors = [
    ["Distance", clean(official.distance), clean(file.raceBook.official.distance), clean(official.distance) === clean(file.raceBook.official.distance) ? 100 : 58],
    ["Track", clean(official.condition), clean(file.raceBook.official.trackCondition), clean(official.condition) === clean(file.raceBook.official.trackCondition) ? 92 : 48],
    ["Class", clean(official.raceClass), clean(file.raceBook.official.raceClass), clean(official.raceClass) === clean(file.raceBook.official.raceClass) ? 92 : 62],
    ["Pressure", clean(evidence.pressure), clean(file.raceBook.intelligence.pressure), 86],
    ["Tempo", clean(evidence.tempo), clean(file.raceBook.intelligence.tempo), 82],
    ["Race Strength", clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength), "Today benchmark", similarityScore(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)],
    ["Run Rating", clean(evidence.runRating?.overall ?? run.edgeiqRunRating), "Performance benchmark", similarityScore(evidence.runRating?.overall ?? run.edgeiqRunRating)],
    ["Barrier", clean(official.barrier), clean(primary?.official?.barrier), clean(official.barrier) === clean(primary?.official?.barrier) ? 90 : 55],
  ];

  return (
    <section className="eiq-similarity-engine">
      <header>
        <div>
          <span>Similarity Engine</span>
          <strong>Why this historical run was opened</strong>
          <p>EDGEIQ compares the historical performance against today’s assignment so the analyst can see what transfers and what needs challenging.</p>
        </div>
        <aside>
          <span>Overall Match</span>
          <MatchBar value={match} />
        </aside>
      </header>

      <div className="eiq-similarity-grid">
        {factors.map(([factor, historical, today, value]) => (
          <article key={factor}>
            <div>
              <span>{factor}</span>
              <strong>{value}%</strong>
            </div>
            <i><b style={{ width: `${value}%` }} /></i>
            <footer>
              <em>{historical}</em>
              <em>{today}</em>
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidenceStoryPanel({ run }: { run: any }) {
  const match = score(run);
  const role = importance(run);
  const evidence = run.professionalForm?.evidence ?? {};
  const official = run.professionalForm?.official ?? {};

  return (
    <section className="eiq-evidence-story">
      <span>EDGEIQ Evidence Story</span>
      <strong>
        {role === "PRIMARY"
          ? "This run is suitable as a primary benchmark."
          : role === "SUPPORTING"
            ? "This run supports the case but needs confirmation."
            : "This run explains context, not today’s full assignment."}
      </strong>
      <p>
        The selected {clean(official.track)} run returned a {clean(evidence.runRating?.overall ?? run.edgeiqRunRating)} Run Rating™ and {clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)} Race Strength™. 
        The assignment match is {match}%, so EDGEIQ treats it as {role.toLowerCase()} evidence. The analyst should use it to understand the runner, then challenge it against today’s track, class, pressure, tempo and barrier.
      </p>
    </section>
  );
}

'''

if "function SimilarityEnginePanel" not in text:
    text = text.replace(anchor, addition + "\n" + anchor)

text = text.replace(
'''          <ComparisonTable run={run} />

          <FactorScorePanel run={run} />''',
'''          <SimilarityEnginePanel run={run} />

          <ComparisonTable run={run} />

          <FactorScorePanel run={run} />

          <EvidenceStoryPanel run={run} />'''
)

tsx.write_text(text, encoding="utf-8")

css_add = r'''

/* EDGEIQ SIMILARITY ENGINE — V11 */
.eiq-similarity-engine,
.eiq-evidence-story {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(95,134,184,.14);
  background: rgba(255,255,255,.018);
}

.eiq-similarity-engine header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 18px;
  align-items: start;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(95,134,184,.12);
}

.eiq-similarity-engine header strong,
.eiq-evidence-story strong {
  display: block;
  margin-top: 7px;
  color: #f4f8f8;
  font-size: 17px;
  line-height: 1.28;
}

.eiq-similarity-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0,1fr));
  gap: 10px;
  margin-top: 12px;
}

.eiq-similarity-grid article {
  min-height: 92px;
  padding: 11px;
  border: 1px solid rgba(95,134,184,.12);
  background: rgba(0,0,0,.14);
}

.eiq-similarity-grid article > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.eiq-similarity-grid article strong {
  color: #f4f8f8;
  font-size: 14px;
}

.eiq-similarity-grid i {
  display: block;
  height: 6px;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(255,255,255,.07);
  overflow: hidden;
}

.eiq-similarity-grid i b {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #5f86b8;
}

.eiq-similarity-grid footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}

.eiq-similarity-grid em {
  color: rgba(244,248,248,.54);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eiq-evidence-story {
  border-left: 3px solid rgba(95,134,184,.72);
}

.eiq-evidence-story p {
  max-width: 980px;
}

@media (max-width: 1350px) {
  .eiq-similarity-engine header,
  .eiq-similarity-grid {
    grid-template-columns: 1fr;
  }
}
'''

if "EDGEIQ SIMILARITY ENGINE — V11" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + css_add, encoding="utf-8")

print("[EDGEIQ] Similarity Engine V11 built")
print(f"[EDGEIQ] TSX checkpoint: {tsx_backup}")
print(f"[EDGEIQ] CSS checkpoint: {css_backup}")
