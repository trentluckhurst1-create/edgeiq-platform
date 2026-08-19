import {
  buildCommandExecutiveSummary,
  type CommandExecutiveSummary,
} from "../../services/buildCommandExecutiveSummary";

type RaceCommandExecutiveWorkspaceProps = {
  summary?: CommandExecutiveSummary;
};

export function RaceCommandExecutiveWorkspace({
  summary = buildCommandExecutiveSummary(),
}: RaceCommandExecutiveWorkspaceProps) {
  return (
    <div className="edgeiq-command-executive">
      <header className="edgeiq-command-executive__hero">
        <div>
          <div className="edgeiq-command-executive__eyebrow">COMMAND</div>
          <h1>Executive Race Briefing</h1>
          <p>What is this race telling me?</p>
        </div>
        <div className="edgeiq-command-executive__state">Live Intelligence</div>
      </header>

      <section className="edgeiq-command-executive__context-strip">
        {summary.raceContextStrip?.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="edgeiq-command-executive__assessment edgeiq-command-executive__assessment--premium">
        <div className="edgeiq-command-executive__label">Executive Assessment</div>
        <div className="edgeiq-command-executive__assessment-text">{summary.assessment}</div>
      </section>

      <section className="edgeiq-command-executive__command-flow">
        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--findings">
          <div className="edgeiq-command-executive__label">Key Findings</div>
          <div className="edgeiq-command-executive__stack">
            {summary.findings.map((finding) => (
              <div className={`edgeiq-command-executive__finding is-${finding.tone}`} key={finding.label}>
                <span>{finding.label}</span>
                <strong>{finding.text}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--tactical">
          <div className="edgeiq-command-executive__label">Tactical Projection</div>
          <div className="edgeiq-command-executive__tactical-board">
            <div className="edgeiq-command-executive__tactical-row">
              <span>01</span>
              <strong>{summary.tactical.speed}</strong>
              <em>Who crosses, who holds, who gets buried.</em>
            </div>
            <div className="edgeiq-command-executive__tactical-row">
              <span>02</span>
              <strong>{summary.tactical.settle}</strong>
              <em>Where the field is expected to organise.</em>
            </div>
            <div className="edgeiq-command-executive__tactical-row">
              <span>03</span>
              <strong>{summary.tactical.close}</strong>
              <em>Who is advantaged when the race turns for home.</em>
            </div>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--market">
          <div className="edgeiq-command-executive__label">Market Assessment</div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Overlay</span>
            <strong>{summary.market.overlay}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Confidence</span>
            <strong>{summary.market.confidence}</strong>
          </div>
          <div className="edgeiq-command-executive__metric-row">
            <span>Movement</span>
            <strong>{summary.market.movement}</strong>
          </div>
        </article>

        <article className="edgeiq-command-executive__panel edgeiq-command-executive__panel--contenders">
          <div className="edgeiq-command-executive__label">Primary Contenders</div>
          <div className="edgeiq-command-executive__contender-grid">
            {summary.contenders.map((contender) => (
              <div className="edgeiq-command-executive__contender" key={contender.role}>
                <span>{contender.role}</span>
                <h3>{contender.title}</h3>
                <strong>{contender.detail}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

    </div>
  );
}
