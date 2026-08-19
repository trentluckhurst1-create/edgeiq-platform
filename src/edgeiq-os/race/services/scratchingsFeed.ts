import type { ThreeDayMeeting, ThreeDayRace, ThreeDayRunner } from "./threeDayCatalog";

export type ScratchingStatus =
  | "SCRATCHED"
  | "LATE_SCRATCHING"
  | "EMERGENCY_PROMOTED"
  | "EMERGENCY_NOT_REQUIRED"
  | "WITHDRAWN"
  | "UNAVAILABLE";

export type DownstreamStatus = "NOT_REQUIRED" | "PENDING" | "PASS" | "FAIL" | "UNAVAILABLE";

export type ScratchingsDataStatusViewModel = {
  source: string | null;
  sourceUpdatedAt: string | null;
  builderVersion: string | null;
  generatedAt: string | null;
  stale: boolean;
  coverageStatus: string | null;
};

export type ScratchingRecordViewModel = {
  eventKey: string;
  meetingKey: string;
  raceKey: string;
  raceNumber: number;
  runnerKey: string;
  runnerNumber: number | null;
  silk: string | null;
  horse: string;
  trainer: string | null;
  jockey: string | null;
  scratchedAt: string | null;
  scratchedAtDisplay: string;
  reason: string | null;
  source: string | null;
  status: ScratchingStatus;
  originalBarrier: number | null;
  effectiveBarrierBefore: number | null;
  effectiveBarrierAfter: number | null;
  fieldSizeBefore: number | null;
  fieldSizeAfter: number | null;
  emergencyPromotion: {
    promoted: boolean;
    promotedAt: string | null;
    replacedRunnerKey: string | null;
  } | null;
  downstream: {
    activeFieldUpdated: boolean | null;
    effectiveBarriersUpdated: boolean | null;
    mapStatus: DownstreamStatus;
    raceShapeStatus: DownstreamStatus;
  };
};

export type ScratchingsRaceGroupViewModel = {
  raceKey: string;
  raceNumber: number;
  raceName: string | null;
  scheduledTime: string | null;
  fieldSizeBefore: number | null;
  fieldSizeAfter: number | null;
  scratchingsCount: number;
  records: ScratchingRecordViewModel[];
};

export type ScratchingEventViewModel = {
  eventKey: string;
  occurredAt: string | null;
  occurredAtDisplay: string;
  raceNumber: number | null;
  horse: string | null;
  event: string;
  reason: string | null;
  source: string | null;
  processedAt: string | null;
};

export type MeetingScratchingsViewModel = {
  meetingKey: string;
  date: string;
  generatedAt: string | null;
  officialUpdatedAt: string | null;
  summary: {
    totalScratchings: number;
    racesAffected: number;
    newSinceCount: number | null;
    newSinceLabel: string | null;
    materiallyChangedFields: number | null;
    emergenciesPromoted: number;
  };
  raceGroups: ScratchingsRaceGroupViewModel[];
  events: ScratchingEventViewModel[];
  dataStatus: ScratchingsDataStatusViewModel;
  sourceUnavailable: boolean;
};

export type EffectiveBarrierInput = {
  runnerKey: string;
  originalBarrier: number | null;
  scratched?: boolean;
  emergencyPromoted?: boolean;
};

export type EffectiveBarrierResult = {
  runnerKey: string;
  originalBarrier: number | null;
  effectiveBarrier: number | null;
  unresolved: boolean;
};

function officialValue(runner: ThreeDayRunner, key: string): unknown {
  return (runner.official as Record<string, unknown>)[key];
}

function usable(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text === "-" || text === "\u2014") return "";
  if (["null", "undefined", "none", "n/a", "na"].includes(text.toLowerCase())) return "";
  return text;
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const text = usable(value);
    if (text) return text;
  }
  return "";
}

function sourceValue(source: Record<string, unknown> | undefined, keys: string[]): string {
  for (const key of keys) {
    const text = firstText(source?.[key]);
    if (text) return text;
  }
  return "";
}

function boolish(value: unknown): boolean {
  const text = firstText(value).toLowerCase();
  return ["1", "true", "yes", "y", "scratched", "withdrawn"].includes(text);
}

function intValue(value: unknown): number | null {
  const text = firstText(value);
  if (!text) return null;
  const num = Number(String(text).replace(/[^\d.-]/g, ""));
  return Number.isFinite(num) ? Math.trunc(num) : null;
}

function runnerName(runner: ThreeDayRunner): string {
  return firstText(runner.official.runner, runner.source?.horse, runner.source?.horseName, "Runner");
}

function runnerKey(meeting: ThreeDayMeeting, race: ThreeDayRace, runner: ThreeDayRunner, index: number): string {
  return firstText(
    runner.source?.runner_key,
    runner.source?.runnerKey,
    `${meeting.meetingKey}_${race.raceKey}_${runnerName(runner).replace(/\W+/g, "").toUpperCase()}_${index + 1}`,
  );
}

function runnerNumber(runner: ThreeDayRunner): number | null {
  return intValue(runner.official.no ?? runner.official.number ?? runner.source?.horse_no ?? runner.source?.saddlecloth);
}

function originalBarrier(runner: ThreeDayRunner): number | null {
  return intValue(runner.official.barrier ?? runner.source?.barrier ?? runner.source?.original_barrier);
}

function silkUrl(runner: ThreeDayRunner): string | null {
  return firstText(runner.source?.silkUrl, runner.source?.silk_url, runner.source?.mobile_silk_image) || null;
}

function raceTime(race: ThreeDayRace): string | null {
  return firstText(race.raceTime, race.source?.race_time, race.source?.raceTime) || null;
}

function normaliseStatus(runner: ThreeDayRunner): ScratchingStatus {
  const raw = firstText(
    runner.source?.scratching_status,
    runner.source?.scratch_status,
    runner.source?.runner_status,
    runner.source?.status,
  ).toUpperCase();
  if (raw.includes("LATE")) return "LATE_SCRATCHING";
  if (raw.includes("PROMOT")) return "EMERGENCY_PROMOTED";
  if (raw.includes("NOT REQUIRED")) return "EMERGENCY_NOT_REQUIRED";
  if (raw.includes("WITHDRAW")) return "WITHDRAWN";
  if (raw.includes("SCRATCH")) return "SCRATCHED";
  if (boolish(officialValue(runner, "scratched")) || boolish(runner.source?.is_scratched) || boolish(runner.source?.scratched)) {
    return "SCRATCHED";
  }
  return "UNAVAILABLE";
}

function isScratchingRecord(runner: ThreeDayRunner): boolean {
  const status = normaliseStatus(runner);
  return status !== "UNAVAILABLE";
}

function formatLocalTime(value: unknown): string {
  const text = firstText(value);
  if (!text) return "";
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return text;
  return new Intl.DateTimeFormat("en-AU", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Australia/Sydney",
  })
    .format(parsed)
    .replace(/\s/g, "")
    .toLowerCase();
}

export function calculateEffectiveBarriers(inputs: EffectiveBarrierInput[]): EffectiveBarrierResult[] {
  const seen = new Set<number>();
  const duplicates = inputs
    .map((item) => item.originalBarrier)
    .filter((barrier): barrier is number => barrier !== null)
    .filter((barrier) => {
      if (seen.has(barrier)) return true;
      seen.add(barrier);
      return false;
    });
  if (duplicates.length) {
    return inputs.map((item) => ({
      runnerKey: item.runnerKey,
      originalBarrier: item.originalBarrier,
      effectiveBarrier: null,
      unresolved: true,
    }));
  }

  const active = inputs
    .filter((item) => !item.scratched && item.originalBarrier !== null)
    .sort((a, b) => (a.originalBarrier ?? 999) - (b.originalBarrier ?? 999));
  const effective = new Map<string, number>();
  active.forEach((item, index) => effective.set(item.runnerKey, index + 1));

  return inputs.map((item) => ({
    runnerKey: item.runnerKey,
    originalBarrier: item.originalBarrier,
    effectiveBarrier: item.originalBarrier === null ? null : effective.get(item.runnerKey) ?? null,
    unresolved: item.originalBarrier === null,
  }));
}

function buildRecordsForRace(meeting: ThreeDayMeeting, race: ThreeDayRace): ScratchingRecordViewModel[] {
  const barrierInputs = race.runners.map((runner, index) => ({
    runnerKey: runnerKey(meeting, race, runner, index),
    originalBarrier: originalBarrier(runner),
    scratched: isScratchingRecord(runner) && normaliseStatus(runner) !== "EMERGENCY_PROMOTED",
    emergencyPromoted: normaliseStatus(runner) === "EMERGENCY_PROMOTED",
  }));
  const before = new Map(
    calculateEffectiveBarriers(barrierInputs.map((item) => ({ ...item, scratched: false }))).map((item) => [
      item.runnerKey,
      item.effectiveBarrier,
    ]),
  );
  const after = new Map(calculateEffectiveBarriers(barrierInputs).map((item) => [item.runnerKey, item.effectiveBarrier]));
  const fieldSizeBefore = race.runners.length || null;
  const fieldSizeAfter =
    race.runners.filter((runner) => !(isScratchingRecord(runner) && normaliseStatus(runner) !== "EMERGENCY_PROMOTED")).length || null;

  return race.runners
    .map((runner, index) => ({ runner, index, status: normaliseStatus(runner) }))
    .filter(({ runner }) => isScratchingRecord(runner))
    .map(({ runner, index, status }) => {
      const key = runnerKey(meeting, race, runner, index);
      const scratchedAt = firstText(
        runner.source?.scratched_time,
        runner.source?.scratched_at,
        runner.source?.scratch_time,
        runner.source?.updated_at,
      );
      const reason = firstText(runner.source?.scratch_reason, runner.source?.scratching_reason, runner.source?.reason);
      const source = firstText(runner.source?.scratch_source, runner.source?.source);
      return {
        eventKey: `${key}_${status}`,
        meetingKey: meeting.meetingKey,
        raceKey: race.raceKey,
        raceNumber: race.raceNumber,
        runnerKey: key,
        runnerNumber: runnerNumber(runner),
        silk: silkUrl(runner),
        horse: runnerName(runner),
        trainer: firstText(runner.official.trainer, runner.source?.trainer) || null,
        jockey: firstText(runner.official.jockey, runner.source?.jockey) || null,
        scratchedAt: scratchedAt || null,
        scratchedAtDisplay: formatLocalTime(scratchedAt) || "Not supplied",
        reason: reason || null,
        source: source || null,
        status,
        originalBarrier: originalBarrier(runner),
        effectiveBarrierBefore: before.get(key) ?? null,
        effectiveBarrierAfter: after.get(key) ?? null,
        fieldSizeBefore,
        fieldSizeAfter,
        emergencyPromotion:
          status === "EMERGENCY_PROMOTED"
            ? {
                promoted: true,
                promotedAt: scratchedAt || null,
                replacedRunnerKey: firstText(runner.source?.replaced_runner_key) || null,
              }
            : null,
        downstream: {
          activeFieldUpdated: true,
          effectiveBarriersUpdated: after.get(key) !== null,
          mapStatus: "UNAVAILABLE",
          raceShapeStatus: "UNAVAILABLE",
        },
      } satisfies ScratchingRecordViewModel;
    });
}

function buildRaceGroups(meeting: ThreeDayMeeting): ScratchingsRaceGroupViewModel[] {
  return meeting.races
    .map((race) => {
      const records = buildRecordsForRace(meeting, race);
      const fieldSizeBefore = race.runners.length || null;
      const fieldSizeAfter =
        race.runners.filter((runner) => !(isScratchingRecord(runner) && normaliseStatus(runner) !== "EMERGENCY_PROMOTED")).length || null;
      return {
        raceKey: race.raceKey,
        raceNumber: race.raceNumber,
        raceName: race.raceName || null,
        scheduledTime: raceTime(race),
        fieldSizeBefore,
        fieldSizeAfter,
        scratchingsCount: records.length,
        records,
      };
    })
    .filter((group) => group.records.length > 0);
}

function buildEvents(groups: ScratchingsRaceGroupViewModel[]): ScratchingEventViewModel[] {
  return groups
    .flatMap((group) =>
      group.records.map((record) => ({
        eventKey: `${record.eventKey}_event`,
        occurredAt: record.scratchedAt,
        occurredAtDisplay: record.scratchedAtDisplay,
        raceNumber: group.raceNumber,
        horse: record.horse,
        event: record.status.replace(/_/g, " "),
        reason: record.reason,
        source: record.source,
        processedAt: record.scratchedAt,
      })),
    )
    .sort((a, b) => String(b.occurredAt ?? "").localeCompare(String(a.occurredAt ?? "")));
}

export function buildMeetingScratchingsViewModel(
  meeting: ThreeDayMeeting,
): MeetingScratchingsViewModel {
  const groups = buildRaceGroups(meeting);
  const records = groups.flatMap((group) => group.records);
  const latestScratchings = records
    .map((record) => record.scratchedAt)
    .filter(Boolean)
    .sort();
  const latest = latestScratchings.length ? latestScratchings[latestScratchings.length - 1] : null;
  const sourceHasFlags = meeting.races.some((race) =>
    race.runners.some((runner) => Object.prototype.hasOwnProperty.call(runner.official, "scratched")),
  );

  return {
    meetingKey: meeting.meetingKey,
    date: meeting.date,
    generatedAt: firstText(meeting.source?.built_at) || null,
    officialUpdatedAt: latest,
    summary: {
      totalScratchings: records.length,
      racesAffected: groups.length,
      newSinceCount: null,
      newSinceLabel: null,
      materiallyChangedFields: null,
      emergenciesPromoted: records.filter((record) => record.status === "EMERGENCY_PROMOTED").length,
    },
    raceGroups: groups,
    events: buildEvents(groups),
    dataStatus: {
      source: sourceHasFlags ? "Three-day product catalogue" : null,
      sourceUpdatedAt: latest,
      builderVersion: "scratchingsFeed.v1",
      generatedAt: firstText(meeting.source?.built_at) || null,
      stale: false,
      coverageStatus: sourceHasFlags ? "Official scratching flags loaded" : "Official scratchings data is currently unavailable.",
    },
    sourceUnavailable: !sourceHasFlags,
  };
}
