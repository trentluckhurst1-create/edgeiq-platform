import { type ReactNode, useEffect, useMemo, useState } from "react";
import { CompareWorkspace } from "../../compare/CompareWorkspace";
import { FormGuideWorkspace, type SectionalProfile } from "./FormGuideWorkspace";
import { MapWorkspace } from "./MapWorkspace";
import { ResultsWorkspace } from "./ResultsWorkspace";
import { RunnerProfileSummary } from "./RunnerProfileSummary";
import { RunnerSummary } from "./RunnerSummary";
import { RunnerTabs, type RunnerWorkspaceMode } from "./RunnerTabs";
import { loadRunnerDetail } from "../services/runnerDetailFeed";

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
  const [hydratedRunner, setHydratedRunner] = useState<any>(runner);
  const [runnerLoading, setRunnerLoading] = useState(false);
  const [runnerLoadError, setRunnerLoadError] = useState("");
  const detailPath = String(runner?.source?.runnerDetailPath ?? "").trim();

  useEffect(() => {
    let active = true;
    setHydratedRunner(runner);
    setRunnerLoadError("");
    if (!detailPath) return () => { active = false; };
    setRunnerLoading(true);
    loadRunnerDetail(detailPath)
      .then((fullRunner) => {
        if (active) setHydratedRunner(fullRunner);
      })
      .catch((error) => {
        if (active) setRunnerLoadError(error instanceof Error ? error.message : "Runner detail unavailable");
      })
      .finally(() => {
        if (active) setRunnerLoading(false);
      });
    return () => { active = false; };
  }, [detailPath, runner]);

  const activeRunner = hydratedRunner ?? runner;
  const activeRuns = useMemo(() => {
    if (!activeRunner) return displayedRuns;
    if (mode === "results") return activeRunner.evidenceRuns ?? activeRunner.historicalRuns ?? displayedRuns;
    return activeRunner.historicalRuns ?? displayedRuns;
  }, [activeRunner, displayedRuns, mode]);
  const activeBestRun = activeRuns?.[0] ?? bestRun;
  const activeField = useMemo(() => field.map((item) => item === runner ? activeRunner : item), [activeRunner, field, runner]);

  return (
    <section className="eiq-form-workbench eiq-runner-workspace-v13">
      <div className="eiq-workspace-breadcrumb">
        <button type="button" onClick={onBackToRace}>FORM GUIDE</button>
        <span>/</span>
        <strong>PROFILE</strong>
        {runnerLoading ? <span>LOADING FORM…</span> : null}
        {runnerLoadError ? <span role="alert">{runnerLoadError}</span> : null}
      </div>

      <RunnerProfileSummary
        runner={activeRunner}
        currentRace={raceBook?.official}
        bestRun={activeBestRun}
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
          runs={activeRuns}
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
          run={activeBestRun}
          runner={activeRunner}
          raceKey={raceBook?.official?.raceKey}
          raceBook={raceBook}
          clean={clean}
          weight={weight}
          market={market}
          esiOverall={activeBestRun ? renderSectionalDelta(sectionalProfile(activeBestRun, sectionalStandard).edgeiq) : undefined}
          onBackToForm={() => setMode("profile")}
          onCompareSelectedRun={() => setMode("compare")}
          onEvidence={() => setMode("results")}
        />
      ) : mode === "compare" ? (
        <CompareWorkspace raceKey={raceBook?.official?.raceKey} runner={activeRunner} />
      ) : mode === "dna" ? (
        <RunnerPendingWorkspace title="DNA" body="What type of horse is this?" />
      ) : mode === "map" ? (
        <MapWorkspace
          raceBook={raceBook}
          field={activeField}
          selectedRunner={activeRunner}
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
