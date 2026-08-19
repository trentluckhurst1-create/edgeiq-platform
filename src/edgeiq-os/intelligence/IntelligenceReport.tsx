import { useState } from "react";

export type IntelligenceEvidence = {
  label: string;
  value: string;
  detail?: string;
};

export type SupportingEngine = {
  label: string;
  status: string;
};

export type IntelligenceReportModel = {
  title: string;
  assessment: string;
  operationalMeaning: string;
  evidence: IntelligenceEvidence[];
  supportingEngines?: SupportingEngine[];
  watch: string[];
  confidence: string;
  lastUpdated: string;
};

type IntelligenceReportProps = {
  report: IntelligenceReportModel;
};

export function IntelligenceReport({ report }: IntelligenceReportProps) {
  const [open, setOpen] = useState(false);

  return (
    <section className="eiq-intel-report eiq-intel-report--v2">
      <header>
        <span>EDGEiQ Intelligence Report</span>
        <strong>{report.title}</strong>
      </header>

      <div className="eiq-intel-report__body">
        <article>
          <span>Assessment</span>
          <p>{report.assessment}</p>
        </article>

        <article>
          <span>Operational Meaning</span>
          <p>{report.operationalMeaning}</p>
        </article>

        {report.supportingEngines?.length ? (
          <article>
            <span>Supported By</span>
            <div className="eiq-intel-report__engines">
              {report.supportingEngines.map((engine) => (
                <div key={engine.label}>
                  <i />
                  <strong>{engine.label}</strong>
                  <small>{engine.status}</small>
                </div>
              ))}
            </div>
          </article>
        ) : null}

        <article>
          <button className="eiq-intel-report__evidence-toggle" type="button" onClick={() => setOpen(!open)}>
            Evidence {open ? "▲" : "▼"}
          </button>

          {open ? (
            <div className="eiq-intel-report__evidence">
              {report.evidence.map((item) => (
                <div key={`${item.label}-${item.value}`}>
                  <strong>{item.label}</strong>
                  <b>{item.value}</b>
                  {item.detail ? <small>{item.detail}</small> : null}
                </div>
              ))}
            </div>
          ) : null}
        </article>

        <article>
          <span>Things To Watch</span>
          <ul>
            {report.watch.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <footer>
          <div>
            <span>Confidence</span>
            <strong>{report.confidence}</strong>
          </div>
          <div>
            <span>Updated</span>
            <strong>{report.lastUpdated}</strong>
          </div>
        </footer>
      </div>
    </section>
  );
}
