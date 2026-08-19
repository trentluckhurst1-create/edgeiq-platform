from pathlib import Path

file = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

text = file.read_text(encoding="utf-8")

text = text.replace(
'''        <aside>
          <article><span>RaceFlow™</span><strong>{file.raceRead.raceFlow}</strong></article>
          <article><span>Pressure</span><strong>{file.raceRead.pressure}</strong></article>
          <article><span>Tempo</span><strong>{file.raceRead.tempo}</strong></article>
          <article><span>Confidence</span><strong>{file.raceRead.confidence}</strong></article>
        </aside>''',
'''        <aside>
          <article><span>RaceFlow™</span><strong>{file.raceRead.raceFlow}</strong></article>
          <article><span>Pressure</span><strong>{file.raceRead.pressure}</strong></article>
          <article><span>Tempo</span><strong>{file.raceRead.tempo}</strong></article>
          <article><span>TrackSignature™</span><strong>{file.raceRead.trackSignature}</strong></article>
          <article><span>SpeedProfile™</span><strong>{file.raceRead.speedProfile}</strong></article>
          <article><span>Confidence</span><strong>{file.raceRead.confidence}</strong></article>
        </aside>'''
)

insert = r'''
      <section className="eiq-race-file-v3__book-strip">
        <article>
          <span>Official Race</span>
          <strong>{file.officialRace.distance}</strong>
          <p>{file.officialRace.raceClass} · {file.officialRace.trackCondition}</p>
        </article>

        <article>
          <span>Race Conditions</span>
          <strong>{file.officialRace.rail}</strong>
          <p>Rail and surface are carried into TrackSignature™.</p>
        </article>

        <article>
          <span>Field</span>
          <strong>{file.field.length}</strong>
          <p>Active runners in today’s race file.</p>
        </article>

        <article>
          <span>Race Book Status</span>
          <strong>Live File</strong>
          <p>Official facts first. EDGEiQ intelligence second.</p>
        </article>
      </section>
'''

if 'eiq-race-file-v3__book-strip' not in text:
    text = text.replace('      <section className="eiq-race-file-v3__assessment">', insert + '\n      <section className="eiq-race-file-v3__assessment">')

file.write_text(text, encoding="utf-8")

marker = "EDGEiQ Race File V3A Professional Strip"
existing = css.read_text(encoding="utf-8")

if marker not in existing:
    css.write_text(existing + r'''

/* ==========================================================================
   EDGEiQ Race File V3A Professional Strip
   ========================================================================== */

.eiq-race-file-v3__hero aside {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.eiq-race-file-v3__book-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
  padding: 24px;
  border: 1px solid rgba(246,243,234,.085);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.026), rgba(255,255,255,.012));
}

.eiq-race-file-v3__book-strip article {
  padding-top: 14px;
  border-top: 1px solid rgba(246,243,234,.10);
}

.eiq-race-file-v3__book-strip strong {
  display: block;
  margin-top: 8px;
  color: #f6f3ea;
  font-size: 22px;
  line-height: 1;
  letter-spacing: -.055em;
}

.eiq-race-file-v3__book-strip p {
  margin: 9px 0 0;
  color: rgba(246,243,234,.54);
  font-size: 12px;
  line-height: 1.45;
}

@media(max-width:1200px){
  .eiq-race-file-v3__hero aside,
  .eiq-race-file-v3__book-strip {
    grid-template-columns: 1fr;
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Race File V3A professional strip built")
