export type ReviewWorkspaceItem = {
  id: string;
  label: string;
  state: string;
  detail: string;
  actionTab?: "FORM GUIDE" | "MAP" | "MARKET" | "OVERVIEW" | "INSIGHTS" | "EPI" | "REVIEW";
};

export type ReviewWorkspaceViewModel = {
  raceLabel: string;
  raceName: string;
  status: string;
  statusTone: "ready" | "pending" | "unavailable";
  meta: Array<{ label: string; value: string }>;
  reviewableItems: ReviewWorkspaceItem[];
  savedState: {
    title: string;
    detail: string;
  };
  sourceBoundary: string[];
};

const UNAVAILABLE = "Unavailable";

function clean(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text || text === "-" || text.toLowerCase() === "none" || text.toLowerCase() === "null") return "";
  return text;
}

function value(...values: unknown[]): string {
  for (const item of values) {
    const text = clean(item);
    if (text) return text;
  }
  return UNAVAILABLE;
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function hasObject(value: unknown): boolean {
  return Boolean(value && typeof value === "object" && Object.keys(value as Record<string, unknown>).length > 0);
}

function hasMarket(field: any[]): boolean {
  return field.some((runner) => clean(runner?.official?.market) || clean(runner?.source?.market) || clean(runner?.source?.live_price));
}

function resultState(raceBook: any): { label: string; tone: ReviewWorkspaceViewModel["statusTone"] } {
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const raw = upper(official.status || source.result_status || source.race_status || source.status);
  if (raw.includes("OFFICIAL") || raw.includes("UNOFFICIAL") || clean(source.winner) || clean(official.winner)) {
    return { label: raw.includes("UNOFFICIAL") ? "Result supplied" : "Official result supplied", tone: "ready" };
  }
  if (raw.includes("ABANDON")) return { label: "Race abandoned", tone: "unavailable" };
  return { label: "Awaiting result", tone: "pending" };
}

export function buildReviewWorkspaceViewModel(
  raceBook: any,
  field: any[],
  selectedRaceKey?: string | null,
): ReviewWorkspaceViewModel {
  const official = raceBook?.official ?? {};
  const source = raceBook?.source ?? {};
  const result = resultState(raceBook);
  const meeting = value(official.meeting, source.meeting, source.track);
  const raceNumber = value(official.raceNumber, source.race_no, source.raceNumber);
  const raceLabel = `${meeting} R${raceNumber.replace(/^R/i, "")}`;
  const raceName = value(official.raceName, source.race_name, source.name, raceLabel);
  const runnerCount = field.length || Number(clean(official.fieldSize || source.field_size || source.runners)) || 0;

  const items: ReviewWorkspaceItem[] = [];
  if (runnerCount > 0) {
    items.push({
      id: "field",
      label: "Form guide",
      state: "Available",
      detail: `${runnerCount} runners loaded for this race.`,
      actionTab: "FORM GUIDE",
    });
  }
  if (hasObject(raceBook?.intelligence)) {
    items.push({
      id: "overview",
      label: "Race intelligence",
      state: "Available",
      detail: "Race overview and current intelligence are available for review.",
      actionTab: "OVERVIEW",
    });
  }
  if (hasObject(raceBook?.map) || hasObject(raceBook?.raceMap) || hasObject(raceBook?.intelligence?.map)) {
    items.push({
      id: "map",
      label: "Speed map",
      state: "Available",
      detail: "Race shape and settling-position work is available.",
      actionTab: "MAP",
    });
  }
  if (hasMarket(field)) {
    items.push({
      id: "market",
      label: "Market worksheet",
      state: "Available",
      detail: "Market values exist in the current field feed.",
      actionTab: "MARKET",
    });
  }
  if (result.tone === "ready") {
    items.push({
      id: "result",
      label: "Result review",
      state: "Ready",
      detail: "Result data has been supplied for this race.",
      actionTab: "REVIEW",
    });
  }

  if (!items.length) {
    items.push({
      id: "none",
      label: "Review record",
      state: "Unavailable",
      detail: "No reviewable race work has been created for this context.",
    });
  }

  return {
    raceLabel,
    raceName,
    status: result.label,
    statusTone: result.tone,
    meta: [
      { label: "Race Key", value: value(selectedRaceKey, official.raceKey, source.race_key) },
      { label: "Distance", value: value(official.distance, source.distance) },
      { label: "Class", value: value(official.raceClass, source.class, source.race_class) },
      { label: "Track", value: value(official.trackCondition, source.track_condition) },
      { label: "Rail", value: value(official.rail, source.rail) },
      { label: "Field", value: runnerCount ? String(runnerCount) : UNAVAILABLE },
    ],
    reviewableItems: items,
    savedState: {
      title: "No saved review record",
      detail: "Review persistence is not connected for this race, so EDGEiQ is not showing saved notes or completed analysis that the product has not created.",
    },
    sourceBoundary: [
      "Review only displays race work already available in the current product state.",
      "Official result analysis remains held until a result is supplied.",
      "No saved item is shown without a real saved record.",
    ],
  };
}
