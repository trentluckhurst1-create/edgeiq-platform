from pathlib import Path

race = Path("src/edgeiq-os/race/RaceFileV3.tsx")
components_dir = Path("src/edgeiq-os/race/components")
components_dir.mkdir(parents=True, exist_ok=True)

backup = Path("src/edgeiq-os/race/RaceFileV3_CHECKPOINT_BEFORE_RUNNER_HEADER_EXTRACTION_V21.tsx")
backup.write_text(race.read_text(encoding="utf-8"), encoding="utf-8")

runner_header = components_dir / "RunnerHeader.tsx"
runner_header.write_text(r'''import type { ReactNode } from "react";

type RunnerHeaderProps = {
  runner: ReactNode;
  meetingLine: ReactNode;
  trainer: ReactNode;
  jockey: ReactNode;
  barrier: ReactNode;
  weight: ReactNode;
  market: ReactNode;
  dna: ReactNode;
  evidence: ReactNode;
};

export function RunnerHeader({
  runner,
  meetingLine,
  trainer,
  jockey,
  barrier,
  weight,
  market,
  dna,
  evidence,
}: RunnerHeaderProps) {
  return (
    <section className="eiq-runner-hero">
      <div>
        <span>Runner Workspace</span>
        <strong>{runner}</strong>
        <p>{meetingLine}</p>
      </div>
      <dl>
        <div><dt>Trainer</dt><dd>{trainer}</dd></div>
        <div><dt>Jockey</dt><dd>{jockey}</dd></div>
        <div><dt>Barrier</dt><dd>{barrier}</dd></div>
        <div><dt>Weight</dt><dd>{weight}</dd></div>
        <div><dt>Market</dt><dd>{market}</dd></div>
        <div><dt>DNA</dt><dd>{dna}</dd></div>
        <div><dt>Evidence</dt><dd>{evidence}</dd></div>
      </dl>
    </section>
  );
}
''', encoding="utf-8")

text = race.read_text(encoding="utf-8")

if 'import { RunnerHeader } from "./components/RunnerHeader";' not in text:
    text = text.replace(
        'import {',
        'import { RunnerHeader } from "./components/RunnerHeader";\nimport {',
        1
    )

old = r'''      <section className="eiq-runner-hero">
        <div>
          <span>Runner Workspace</span>
          <strong>{clean(primary?.official?.runner)}</strong>
          <p>{clean(file.raceBook.official.meeting)} R{clean(file.raceBook.official.raceNumber)} Â· {clean(file.raceBook.official.distance)} Â· {clean(file.raceBook.official.trackCondition)} Â· {clean(file.raceBook.intelligence.pressure)} pressure</p>
        </div>
        <dl>
          <div><dt>Trainer</dt><dd>{clean(primary?.official?.trainer)}</dd></div>
          <div><dt>Jockey</dt><dd>{clean(primary?.official?.jockey)}</dd></div>
          <div><dt>Barrier</dt><dd>{clean(primary?.official?.barrier)}</dd></div>
          <div><dt>Weight</dt><dd>{weight(primary?.official?.weight)}</dd></div>
          <div><dt>Market</dt><dd>{market(primary?.official?.market)}</dd></div>
          <div><dt>DNA</dt><dd>{dna(primary?.runnerDNA)}</dd></div>
          <div><dt>Evidence</dt><dd>{bestRun ? importance(bestRun) : "Not available"}</dd></div>
        </dl>
      </section>'''

new = r'''      <RunnerHeader
        runner={clean(primary?.official?.runner)}
        meetingLine={`${clean(file.raceBook.official.meeting)} | R${clean(file.raceBook.official.raceNumber)} | ${clean(file.raceBook.official.distance)} | ${clean(file.raceBook.official.trackCondition)} | ${clean(file.raceBook.intelligence.pressure)} Pressure`}
        trainer={clean(primary?.official?.trainer)}
        jockey={clean(primary?.official?.jockey)}
        barrier={clean(primary?.official?.barrier)}
        weight={weight(primary?.official?.weight)}
        market={market(primary?.official?.market)}
        dna={dna(primary?.runnerDNA)}
        evidence={bestRun ? importance(bestRun) : "Not available"}
      />'''

if old not in text:
    raise SystemExit("Runner header block not found. Extraction stopped safely.")

text = text.replace(old, new)

race.write_text(text, encoding="utf-8")

print("[EDGEIQ] RunnerHeader component extracted V21")
print(f"[EDGEIQ] checkpoint: {backup}")
print(f"[EDGEIQ] created: {runner_header}")
