type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";

type RunnerSummaryProps = {
  sectionalStandard: SectionalStandard;
  setSectionalStandard: (standard: SectionalStandard) => void;
};

export function RunnerSummary({
  sectionalStandard,
  setSectionalStandard,
}: RunnerSummaryProps) {
  return (
    <section className="eiq-runner-summary eiq-runner-summary--standards">
      <article>
        <span>ESI Standard</span>
        <div className="eiq-sectional-standard-toggle">
          <button type="button" className={sectionalStandard === "sameClass" ? "is-active" : ""} onClick={() => setSectionalStandard("sameClass")}>Same Class</button>
          <button type="button" className={sectionalStandard === "open" ? "is-active" : ""} onClick={() => setSectionalStandard("open")}>Open</button>
          <button type="button" className={sectionalStandard === "trackDistance" ? "is-active" : ""} onClick={() => setSectionalStandard("trackDistance")}>Track/Distance</button>
          <button type="button" className={sectionalStandard === "todayProjection" ? "is-active" : ""} onClick={() => setSectionalStandard("todayProjection")}>Today</button>
        </div>
        <p>Negative ESI figures are inside EDGEiQ Standard. Positive ESI figures are outside standard. Raw sectional times are not displayed.</p>
      </article>
    </section>
  );
}
