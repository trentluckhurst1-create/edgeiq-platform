import type {
  FormGuideInsightGroup,
  FormGuideProfileLine,
  FormGuideRunnerDisplay,
} from "./formGuideNormaliser";

export type FormGuideProfileTile = {
  label: string;
  record: string;
  winPct: string;
  placePct: string;
  matchesToday: boolean;
  source: string;
};

export type FormGuideProfileGroup = {
  title: string;
  tiles: FormGuideProfileTile[];
};

export type FormGuideTodayMatchItem = {
  label: string;
  record: string;
  detail: string;
  source: string;
};

export type FormGuideDossierViewModel = {
  currentRaceDetails: Array<{ label: string; value: string }>;
  profileGroups: FormGuideProfileGroup[];
  todayMatch: FormGuideTodayMatchItem[];
  keyInsights: FormGuideInsightGroup[];
};

function clean(value: string | undefined | null): string {
  return String(value ?? "").trim();
}

function emptyLine(label: string): FormGuideProfileLine {
  return {
    label,
    record: "",
    starts: "",
    wins: "",
    seconds: "",
    thirds: "",
    winPct: "",
    placePct: "",
    matchesToday: false,
    source: "",
  };
}

function token(value: string): string {
  return clean(value)
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "");
}

function lineByLabel(rows: FormGuideProfileLine[], labels: string[]): FormGuideProfileLine {
  const wanted = labels.map(token).filter(Boolean);
  return rows.find((row) => wanted.includes(token(row.label))) ?? emptyLine(labels[0] ?? "Profile");
}

function bestLine(rows: FormGuideProfileLine[], fallbackLabel: string): FormGuideProfileLine {
  return rows.find((row) => row.matchesToday && row.record) ?? rows.find((row) => row.record) ?? emptyLine(fallbackLabel);
}

function tile(label: string, row: FormGuideProfileLine): FormGuideProfileTile {
  return {
    label,
    record: clean(row.record),
    winPct: clean(row.winPct),
    placePct: clean(row.placePct),
    matchesToday: Boolean(row.matchesToday),
    source: clean(row.source),
  };
}

function metric(label: string, value: string): { label: string; value: string } {
  return { label, value: clean(value) };
}

export function buildRunnerProfileDossier(runner: FormGuideRunnerDisplay): FormGuideDossierViewModel {
  const careerRows = runner.careerProfile;
  const conditionRows = runner.conditionProfile;
  const prepRows = runner.raceDayPattern;

  const profileGroups: FormGuideProfileGroup[] = [
    {
      title: "Career & Conditions",
      tiles: [
        tile("Career", lineByLabel(careerRows, ["Career"])),
        tile("Track", lineByLabel(careerRows, ["Track"])),
        tile("Distance", lineByLabel(careerRows, ["Distance"])),
        tile("Track/Dist", lineByLabel(careerRows, ["Track/Dist", "Track Distance"])),
        tile("Firm", lineByLabel(conditionRows, ["Firm"])),
        tile("Good", lineByLabel(conditionRows, ["Good"])),
        tile("Soft", lineByLabel(conditionRows, ["Soft"])),
        tile("Heavy", lineByLabel(conditionRows, ["Heavy"])),
      ],
    },
    {
      title: "Connections & Class",
      tiles: [
        tile("Jockey", lineByLabel(runner.jockeyProfile, ["Jockey", "Current Jockey"])),
        tile("Class", bestLine(runner.classProfile, "Class")),
      ],
    },
    {
      title: "Preparation",
      tiles: [
        tile("1st Up", lineByLabel(prepRows, ["1st Up", "First Up"])),
        tile("2nd Up", lineByLabel(prepRows, ["2nd Up", "Second Up"])),
        tile("3rd Up", lineByLabel(prepRows, ["3rd Up", "Third Up"])),
      ],
    },
  ];

  const todayMatch = profileGroups
    .flatMap((group) => group.tiles)
    .filter((item) => item.matchesToday && item.record)
    .map((item) => ({
      label: item.label,
      record: item.record,
      detail: [item.winPct ? `${item.winPct} win` : "", item.placePct ? `${item.placePct} place` : ""].filter(Boolean).join(" | "),
      source: item.source,
    }));

  return {
    currentRaceDetails: [
      metric("Trainer", runner.trainer),
      metric("Jockey", runner.jockey),
      metric("Wt", runner.weight),
      metric("Bar", runner.effectiveBarrier || runner.barrier),
      metric("Market", runner.marketPrice),
      metric("EDGEiQ Price", runner.edgeiqPrice),
      metric("Days", runner.daysSinceLastRun),
      metric("Gear", runner.gear),
    ],
    profileGroups,
    todayMatch,
    keyInsights: runner.scratched ? [] : runner.insights.filter((group) => group.items.length),
  };
}
