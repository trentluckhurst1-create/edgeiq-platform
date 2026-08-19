import type { ThreeDayMeeting } from "../services/threeDayCatalog";
import { MeetingResultsWorkspace } from "./MeetingResultsWorkspace";

type GlobalResultsWorkspaceProps = {
  meeting?: ThreeDayMeeting | null;
};

export function GlobalResultsWorkspace({ meeting = null }: GlobalResultsWorkspaceProps) {
  if (!meeting) {
    return (
      <section className="eiq-global-results-workspace" data-edgeiq-workspace-key="RESULTS" data-edgeiq-mounted-component="GlobalResultsWorkspace">
        <section className="eiq-workspace-panel">
          <span>RESULTS</span>
          <strong>Select a meeting to review results.</strong>
          <p>Meeting and race results are shown once a governed meeting context is available.</p>
        </section>
      </section>
    );
  }

  return (
    <section className="eiq-global-results-workspace" data-edgeiq-workspace-key="RESULTS" data-edgeiq-mounted-component="GlobalResultsWorkspace">
      <MeetingResultsWorkspace meeting={meeting} />
    </section>
  );
}
