import type { ReactNode } from "react";
import { CompareWorkspace } from "../../compare/CompareWorkspace";
import { FormGuideWorkspace, type SectionalProfile } from "./FormGuideWorkspace";
import { MapWorkspace } from "./MapWorkspace";
import { ResultsWorkspace } from "./ResultsWorkspace";
import { RunnerProfileSummary } from "./RunnerProfileSummary";
import { RunnerSummary } from "./RunnerSummary";
import { RunnerTabs, type RunnerWorkspaceMode } from "./RunnerTabs";

type SectionalStandard = "sameClass" | "open" | "trackDistance" | "todayProjection";

type RunnerProfileWorkspaceProps = {
  runner: any;
  raceBook: any;
  field: any[];
  mode: RunnerWorkspaceMode;
  setMode: (mode: RunnerWorkspaceMode) => void;
  displayedRuns: any[];
  bestRun: any;
  sectionalStandard: SectionalStandard;
  setSectionalStandard: (standard: SectionalStandard) => void;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  dna: (value: any) => string;
  importance: (run: any) => string;
  sectionalProfile: (run: any, standard: SectionalStandard) => SectionalProfile;
  renderSectionalDelta: (value: number) => ReactNode;
  renderHistoricalRunCard: (run: any, sectionalProfile: SectionalProfile) => ReactNode;
  onBackToRace: () => void;
};

function RunnerPendingWorkspace({ title, body }: { title: string; body: string }) {
  return (
    <section className="eiq-runner-pending">
      <span>{title}</span>
      <strong>{body}</strong>
      <p>Official racing data explains what happened. EDGEIQ context explains what it means.</p>
    </section>
  );
}

export function RunnerProfileWorkspace({
  runner,
  raceBook,
  field,
  mode,
  setMode,
  displayedRuns,
  bestRun,
  sectionalStandard,
  setSectionalStandard,
  clean,
  weight,
  market,
  dna,
  importance,
  sectionalProfile,
  renderSectionalDelta,
  renderHistoricalRunCard,
  onBackToRace,
}: RunnerProfileWorkspaceProps) {
  return (
    <section className="eiq-form-workbench eiq-runner-workspace-v13">
      <div className="eiq-workspace-breadcrumb">
        <button type="button" onClick={onBackToRace}>FORM GUIDE</button>
        <span>/</span>
        <strong>PROFILE</strong>
      </div>

      <RunnerProfileSummary
        runner={runner}
        currentRace={raceBook?.official}
        bestRun={bestRun}
        clean={clean}
        weight={weight}
        market={market}
        dna={dna}
        importance={importance}
      />

      <RunnerSummary
        sectionalStandard={sectionalStandard}
        setSectionalStandard={setSectionalStandard}
      />

      <RunnerTabs mode={mode} setMode={setMode} />

      {mode === "profile" ? (
        <FormGuideWorkspace
          runs={displayedRuns}
          sectionalStandard={sectionalStandard}
          clean={clean}
          weight={weight}
          market={market}
          sectionalProfile={sectionalProfile}
          renderSectionalDelta={renderSectionalDelta}
          renderHistoricalRunCard={renderHistoricalRunCard}
        />
      ) : mode === "results" ? (
        <ResultsWorkspace
          run={bestRun}
          runner={runner}
          raceKey={raceBook?.official?.raceKey}
          raceBook={raceBook}
          clean={clean}
          weight={weight}
          market={market}
          esiOverall={bestRun ? renderSectionalDelta(sectionalProfile(bestRun, sectionalStandard).edgeiq) : undefined}
          onBackToForm={() => setMode("profile")}
          onCompareSelectedRun={() => setMode("compare")}
          onEvidence={() => setMode("results")}
        />
      ) : mode === "compare" ? (
        <CompareWorkspace raceKey={raceBook?.official?.raceKey} runner={runner} />
      ) : mode === "dna" ? (
        <RunnerPendingWorkspace title="DNA" body="What type of horse is this?" />
      ) : mode === "map" ? (
        <MapWorkspace
          raceBook={raceBook}
          field={field}
          selectedRunner={runner}
          clean={clean}
          market={market}
          mode="runner"
        />
      ) : (
        <RunnerPendingWorkspace title="Market" body="Today's runner price, fair price, overlay and movement workspace." />
      )}
    </section>
  );
}
