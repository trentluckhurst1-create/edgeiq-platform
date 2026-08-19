from pathlib import Path

services = Path("src/edgeiq-os/services")
services.mkdir(parents=True, exist_ok=True)

(service := services / "mission-control.ts").write_text(r'''
import { getOperationalRaceState } from "./intelligence-orchestrator";

export type MissionControlModel = {
  meetingCount: number;
  raceCount: number;
  runnerCount: number;

  highestConfidence: {
    label: string;
    value: string;
  };

  largestOverlay: {
    label: string;
    value: string;
  };

  weatherWatch: {
    label: string;
    value: string;
  };

  operationalFocus: {
    label: string;
    value: string;
  };
};

export function buildMissionControlModel(): MissionControlModel {

  const raceState = getOperationalRaceState();

  const meetingName = raceState.meetingName ?? "Victoria";

  const raceName =
    raceState.raceName ??
    `${meetingName} R${raceState.raceNumber}`;

  return {

    meetingCount: 1,

    raceCount: 1,

    runnerCount: raceState.evidence.length,

    highestConfidence: {
      label: raceName,
      value: raceState.confidence >= 80
        ? "Very High"
        : raceState.confidence >= 65
          ? "High"
          : "Developing",
    },

    largestOverlay: {
      label: raceState.referenceRunner,
      value: raceState.decision.state,
    },

    weatherWatch: {
      label: raceState.trackCondition,
      value: raceState.rail,
    },

    operationalFocus: {
      label: raceState.decision.headline,
      value: raceState.decision.state,
    },

  };

}
'''.lstrip(), encoding="utf-8")

home = Path("src/edgeiq-os/home/EdgeiqOsHome.tsx")

text = home.read_text(encoding="utf-8")

if 'buildMissionControlModel' not in text:

    text = text.replace(
        'import { WorkspaceHeader, BriefSection, SectionHeader } from "../design-system";',
        '''import { WorkspaceHeader, BriefSection, SectionHeader } from "../design-system";
import { buildMissionControlModel } from "../services/mission-control";'''
    )

    text = text.replace(
        "const todayStats = [",
        "const mission = buildMissionControlModel();\n\nconst todayStats = ["
    )

    text = text.replace(
        '''{ label: "Meetings", value: "Victoria", note: "Active racing universe" },''',
        '''{ label: "Meetings", value: String(mission.meetingCount), note: "Operational meetings" },'''
    )

    text = text.replace(
        '''{ label: "Races", value: "Pending Feed", note: "Race universe connecting" },''',
        '''{ label: "Races", value: String(mission.raceCount), note: "Operational races" },'''
    )

    text = text.replace(
        '''{ label: "Highest Confidence", value: "Pending", note: "Requires race selection" },''',
        '''{ label: "Highest Confidence", value: mission.highestConfidence.label, note: mission.highestConfidence.value },'''
    )

    text = text.replace(
        '''{ label: "Largest Overlay", value: "Pending", note: "Market validation pending" },''',
        '''{ label: "Operational Focus", value: mission.operationalFocus.label, note: mission.operationalFocus.value },'''
    )

    text = text.replace(
        '''{ label: "Weather", value: "Stable", note: "Environment intelligence reserved" },''',
        '''{ label: "Weather", value: mission.weatherWatch.label, note: mission.weatherWatch.value },'''
    )

    home.write_text(text, encoding="utf-8")

print("[EDGEIQ] Mission Control model connected")
