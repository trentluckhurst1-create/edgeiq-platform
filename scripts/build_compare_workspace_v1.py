from pathlib import Path

compare_dir = Path("src/edgeiq-os/compare")
compare_dir.mkdir(parents=True, exist_ok=True)

service = Path("src/edgeiq-os/services/CompareService.ts")
race = Path("src/edgeiq-os/race/RaceFileV3.tsx")
css = Path("src/styles/edgeiqProductTerminalV1.css")

service.write_text(r'''
import { RaceFileService } from "./RaceFileService";

export function buildCompareModel() {
  const file = RaceFileService.buildRaceBook();
  const runner = file.field[0];
  const historical = runner?.historicalRuns?.[0];

  return {
    today: {
      race: `${file.raceBook.official.meeting} R${file.raceBook.official.raceNumber}`,
      distance: file.raceBook.official.distance,
      className: file.raceBook.official.raceClass,
      condition: file.raceBook.official.trackCondition,
      rail: file.raceBook.official.rail,
      pressure: file.raceBook.intelligence.pressure,
      tempo: file.raceBook.intelligence.tempo,
      trackSignature: file.raceBook.intelligence.trackSignature,
      speedProfile: file.raceBook.intelligence.speedProfile,
    },
    historical: historical
      ? {
          race: `${historical.track} · ${historical.distance} · ${historical.raceClass}`,
          condition: historical.condition,
          barrier: historical.barrier,
          weight: historical.weight,
          jockey: historical.jockey,
          officialTime: historical.officialRaceTime,
          raceStrength: historical.edgeiqRaceStrength,
          runRating: historical.edgeiqRunRating,
          pressure: historical.pressureRating,
          tempo: historical.tempoRating,
          trackSignature: historical.trackSignatureMatch,
          raceFlow: historical.raceFlowMatch,
          speedProfile: historical.speedProfile,
          positionInRunning: historical.positionInRunning,
        }
      : null,
    similarity: {
      score: 92,
      verdict: "HIGH MATCH",
      reasons: ["Distance", "Class", "Track condition", "Pressure", "Tempo"],
      watch: ["Barrier", "Market movement"],
    },
  };
}

export const CompareService = {
  build: buildCompareModel,
};
'''.lstrip(), encoding="utf-8")

(compare_dir / "CompareWorkspace.tsx").write_text(r'''
import { CompareService } from "../services/CompareService";

const compare = CompareService.build();

export function CompareWorkspace() {
  return (
    <section className="eiq-compare-workspace">
      <header>
        <span>EDGEiQ Compare</span>
        <strong>Has this horse already done today’s job?</strong>
        <p>
          Compare today’s race against the closest historical run using official racing facts,
          EDGEiQ ratings, SpeedProfile™, position in running and race-shape intelligence.
        </p>
      </header>

      <div className="eiq-compare-workspace__grid">
        <article>
          <span>Today</span>
          <strong>{compare.today.race}</strong>
          <p>{compare.today.distance} · {compare.today.className} · {compare.today.condition} · {compare.today.rail}</p>

          <dl>
            <div><dt>Pressure</dt><dd>{compare.today.pressure}</dd></div>
            <div><dt>Tempo</dt><dd>{compare.today.tempo}</dd></div>
            <div><dt>TrackSignature™</dt><dd>{compare.today.trackSignature}</dd></div>
            <div><dt>SpeedProfile™</dt><dd>{compare.today.speedProfile}</dd></div>
          </dl>
        </article>

        <article>
          <span>Closest Historical Run</span>
          <strong>{compare.historical?.race ?? "No historical match"}</strong>
          <p>{compare.historical?.condition ?? "Pending"} · {compare.historical?.weight ?? ""} · {compare.historical?.jockey ?? ""}</p>

          <dl>
            <div><dt>Race Strength™</dt><dd>{compare.historical?.raceStrength ?? "—"}</dd></div>
            <div><dt>Run Rating™</dt><dd>{compare.historical?.runRating ?? "—"}</dd></div>
            <div><dt>Official Time</dt><dd>{compare.historical?.officialTime ?? "—"}</dd></div>
            <div><dt>RaceFlow™</dt><dd>{compare.historical?.raceFlow ?? "—"}</dd></div>
          </dl>
        </article>

        <aside>
          <span>Similarity</span>
          <strong>{compare.similarity.score}%</strong>
          <b>{compare.similarity.verdict}</b>

          <div>
            {compare.similarity.reasons.map((reason) => (
              <em key={reason}>✓ {reason}</em>
            ))}
            {compare.similarity.watch.map((watch) => (
              <em key={watch}>Watch: {watch}</em>
            ))}
          </div>
        </aside>
      </div>

      {compare.historical ? (
        <div className="eiq-compare-workspace__speed">
          <header>
            <span>SpeedProfile™</span>
            <strong>Historical lengths vs EDGEiQ standard</strong>
          </header>

          <div>
            {compare.historical.speedProfile.map((split) => (
              <article key={split.marker}>
                <span>{split.marker}</span>
                <strong>{split.lengthsVsStandard}</strong>
                <small>{split.position}</small>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
'''.lstrip(), encoding="utf-8")

text = race.read_text(encoding="utf-8")

if 'import { CompareWorkspace } from "../compare/CompareWorkspace";' not in text:
    text = text.replace(
        'import { RaceFileService } from "../services/RaceFileService";',
        'import { RaceFileService } from "../services/RaceFileService";\nimport { CompareWorkspace } from "../compare/CompareWorkspace";'
    )

if "<CompareWorkspace />" not in text:
    text = text.replace("</section>\n  );\n}", "      <CompareWorkspace />\n    </section>\n  );\n}")

race.write_text(text, encoding="utf-8")

if "EDGEiQ Compare Workspace" not in css.read_text(encoding="utf-8"):
    css.write_text(css.read_text(encoding="utf-8") + r'''

/* ==========================================================================
   EDGEiQ Compare Workspace
   ========================================================================== */

.eiq-compare-workspace {
  margin-top: 42px;
  padding: 32px;
  border: 1px solid rgba(246,243,234,.09);
  border-radius: 32px;
  background:
    radial-gradient(circle at top right, rgba(126,220,155,.07), transparent 35%),
    linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.012));
}

.eiq-compare-workspace > header strong {
  display:block;
  margin-top:8px;
  color:#f6f3ea;
  font-size:34px;
  line-height:1;
  letter-spacing:-.06em;
}

.eiq-compare-workspace__grid {
  display:grid;
  grid-template-columns: 1fr 1fr .55fr;
  gap:18px;
  margin-top:24px;
}

.eiq-compare-workspace__grid > article,
.eiq-compare-workspace__grid > aside {
  padding:22px;
  border:1px solid rgba(246,243,234,.08);
  border-radius:24px;
  background:rgba(255,255,255,.018);
}

.eiq-compare-workspace__grid strong {
  display:block;
  margin-top:8px;
  color:#f6f3ea;
  font-size:22px;
  letter-spacing:-.05em;
}

.eiq-compare-workspace__grid b {
  display:block;
  margin-top:8px;
  color:#7edc9b;
  font-size:13px;
  letter-spacing:.12em;
}

.eiq-compare-workspace dl {
  display:grid;
  gap:10px;
  margin:18px 0 0;
}

.eiq-compare-workspace dl div {
  display:flex;
  justify-content:space-between;
  gap:14px;
  padding-top:10px;
  border-top:1px solid rgba(246,243,234,.075);
}

.eiq-compare-workspace dt {
  color:rgba(246,243,234,.48);
  font-size:11px;
}

.eiq-compare-workspace dd {
  margin:0;
  color:#f6f3ea;
  font-size:12px;
  font-weight:900;
}

.eiq-compare-workspace__grid aside > strong {
  font-size:54px;
}

.eiq-compare-workspace__grid aside em {
  display:block;
  margin-top:10px;
  color:rgba(246,243,234,.72);
  font-size:12px;
  font-style:normal;
}

.eiq-compare-workspace__speed {
  margin-top:22px;
  padding:22px;
  border:1px solid rgba(246,243,234,.08);
  border-radius:24px;
  background:rgba(255,255,255,.016);
}

.eiq-compare-workspace__speed header strong {
  display:block;
  margin-top:6px;
  color:#f6f3ea;
  font-size:18px;
}

.eiq-compare-workspace__speed > div {
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:14px;
  margin-top:18px;
}

.eiq-compare-workspace__speed article {
  padding-top:12px;
  border-top:1px solid rgba(246,243,234,.08);
}

.eiq-compare-workspace__speed article strong {
  display:block;
  margin-top:8px;
  color:#f6f3ea;
  font-size:24px;
  letter-spacing:-.06em;
}

.eiq-compare-workspace__speed small {
  display:block;
  margin-top:6px;
  color:rgba(246,243,234,.54);
  font-size:11px;
}

@media(max-width:1200px){
  .eiq-compare-workspace__grid,
  .eiq-compare-workspace__speed > div {
    grid-template-columns:1fr;
  }
}
''', encoding="utf-8")

print("[EDGEIQ] Compare Workspace built and mounted into Race Book")
