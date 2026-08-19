import type { ReactNode } from "react";

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
