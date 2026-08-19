import { Fragment, type ReactNode, useState } from "react";
import { EdgeiqMetricTooltip, edgeiqMetricDefinitions } from "./EdgeiqMetricTooltip";

export type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";

export type SectionalProfile = {
  early: number;
  mid: number;
  late: number;
  edgeiq: number;
};

type FormGuideWorkspaceProps = {
  runs: any[];
  sectionalStandard: SectionalStandard;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  sectionalProfile: (run: any, standard: SectionalStandard) => SectionalProfile;
  renderSectionalDelta: (value: number) => ReactNode;
  renderHistoricalRunCard: (run: any, sectionalProfile: SectionalProfile) => ReactNode;
};

export function FormGuideWorkspace({
  runs,
  sectionalStandard,
  clean,
  weight,
  market,
  sectionalProfile,
  renderSectionalDelta,
  renderHistoricalRunCard,
}: FormGuideWorkspaceProps) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div className="eiq-form-guide-shell">
      <div className="eiq-form-guide-toolbar">
        <div>
          <span>EDGEiQ Form Guide</span>
          <strong>Past runs in order | ESI in lengths vs EDGEiQ Standard</strong>
        </div>
        <div className="eiq-standard-note">
          <span>Current Standard</span>
          <strong>
            {sectionalStandard === "sameClass" ? "Same Class" : sectionalStandard === "open" ? "Open" : sectionalStandard === "trackDistance" ? "Track/Distance" : "Today's Projection"}
          </strong>
        </div>
      </div>

      <div className="eiq-form-guide-table">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Date</th>
              <th>Track</th>
              <th>Dist</th>
              <th>Class</th>
              <th>Cond</th>
              <th>Bar</th>
              <th>Wt</th>
              <th>Jockey</th>
              <th>SP</th>
              <th>Fin</th>
              <th>Margin</th>
              <th><EdgeiqMetricTooltip label="EPI" {...edgeiqMetricDefinitions.EPI} /></th>
              <th><EdgeiqMetricTooltip label="ERI" {...edgeiqMetricDefinitions.ERI} /></th>
              <th><EdgeiqMetricTooltip label="ESI" {...edgeiqMetricDefinitions.ESI} /></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run: any, index: number) => {
              const key = `${run.date}-${run.track}-${run.race}-${index}`;
              const official = run.professionalForm?.official ?? {};
              const evidence = run.professionalForm?.evidence ?? {};
              const sec = sectionalProfile(run, sectionalStandard);
              const isOpen = openKey === key;

              return (
                <Fragment key={key}>
                  <tr className={isOpen ? "is-open" : ""} onClick={() => setOpenKey(isOpen ? null : key)}>
                    <td>{isOpen ? "-" : "+"}</td>
                    <td>{clean(official.date)}</td>
                    <td><strong>{clean(official.track)}</strong></td>
                    <td>{clean(official.distance)}</td>
                    <td>{clean(official.raceClass)}</td>
                    <td>{clean(official.condition)}</td>
                    <td>{clean(official.barrier)}</td>
                    <td>{weight(official.weight)}</td>
                    <td>{clean(official.jockey)}</td>
                    <td>{market(official.sp)}</td>
                    <td>{clean(official.finish)}</td>
                    <td>{clean(official.margin)}</td>
                    <td><b>{clean(evidence.runRating?.overall ?? run.edgeiqRunRating)}</b></td>
                    <td><b>{clean(evidence.raceStrength?.overall ?? run.edgeiqRaceStrength)}</b></td>
                    <td>{renderSectionalDelta(sec.edgeiq)}</td>
                  </tr>
                  {isOpen ? renderHistoricalRunCard(run, sec) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
