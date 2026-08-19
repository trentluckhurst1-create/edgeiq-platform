import { useEffect, useMemo, useState } from "react";
import {
  findRunnerProfileStats,
  formatPct,
  formatRaceRecord,
  formatSp,
  hasPositiveNumber,
  loadRunnerProfileStats,
  toNumber,
  type RunnerProfileStats,
} from "../services/runnerProfileStats";

type RunnerProfileSummaryProps = {
  runner: any;
  currentRace?: any;
  bestRun: any;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  dna: (value: any) => string;
  importance: (run: any) => string;
};

function hasValue(value: any) {
  return value !== null && value !== undefined && value !== "" && value !== "-" && value !== "Not available" && value !== "Not recorded";
}

function firstValue(...values: any[]) {
  return values.find(hasValue);
}

function hasMeaningfulValue(value: any) {
  if (!hasValue(value)) return false;
  const text = String(value).trim().toUpperCase();
  return ![
    "AWAITING DNA",
    "DEVELOPING",
    "PENDING",
    "MARKET PENDING",
    "NOT LISTED",
    "NOT NOTIFIED",
    "IGNORE",
  ].includes(text);
}

function evidenceLabel(value: string) {
  if (value === "PRIMARY") return "Key Chance";
  if (value === "SUPPORTING") return "Genuine Chance";
  if (value === "REFERENCE") return "Useful Run";
  if (value === "BACKGROUND") return "Watch";
  return value ? "Forgive / Ignore" : "";
}

function displayPunterSummary(value: any) {
  const raw = String(value ?? "");
  if (!raw.trim()) return "";
  return raw
    .replace(/Strong in defeat\. The performance rated better than the finishing position suggests\./gi, "Better than the finishing position suggests. Previous run has more merit than it reads on paper.")
    .replace(/Primary\s+\w+\s+runner\..*$/gi, "Key chance profile with useful form to test against today's race.")
    .replace(/Secondary\s+\w+\s+runner\..*$/gi, "Capable profile, but needs the right race shape.")
        .replace(/historical\s+evidence/gi, "past form")
    .replace(/assignment/gi, "race setup")
    .replace(/evidence/gi, "form")
    .trim();
}

function ratingValue(run: any) {
  return run?.professionalForm?.evidence?.runRating?.overall ?? run?.edgeiqRunRating;
}

function raceValue(run: any) {
  return run?.professionalForm?.evidence?.raceStrength?.overall ?? run?.edgeiqRaceStrength;
}

function racingRecord(starts: any, wins: any, seconds: any, thirds: any) {
  return formatRaceRecord(starts, wins, seconds, thirds);
}

type ProfileStatRow = {
  key: string;
  label: string;
  value: string;
  isToday?: boolean;
};

type ProfileStatSection = {
  title: string;
  rows: ProfileStatRow[];
};

function hasNumber(value: any) {
  return toNumber(value) !== undefined;
}

function numberValue(value: any) {
  return toNumber(value) ?? 0;
}

function normalizeText(value: any) {
  return String(value ?? "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function distanceNumber(value: any) {
  const match = String(value ?? "").match(/\d+/);
  return match ? Number(match[0]) : undefined;
}

function conditionKey(value: any) {
  const normalized = normalizeText(value);
  if (normalized.includes("FIRM")) return "condition_firm";
  if (normalized.includes("GOOD")) return "condition_good";
  if (normalized.includes("SOFT")) return "condition_soft";
  if (normalized.includes("HEAVY")) return "condition_heavy";
  if (normalized.includes("SYNTH")) return "condition_synthetic";
  return "";
}

function buildTodayContext(currentRace?: any) {
  const context = currentRace ?? {};
  return {
    track: normalizeText(firstValue(context.meeting, context.track, context.trackName)),
    distance: distanceNumber(firstValue(context.distance, context.raceDistance)),
    raceClass: normalizeText(firstValue(context.raceClass, context.class, context.grade)),
    condition: conditionKey(firstValue(context.trackCondition, context.condition, context.going)),
    jockey: normalizeText(firstValue(context.jockey, context.rider)),
  };
}

function isTodayRelevantStat(statKey: string, stats: RunnerProfileStats, currentRace?: any) {
  const context = buildTodayContext(currentRace);
  if (statKey === "track") {
    const profileTrack = normalizeText(firstValue(stats.latest_track, stats.best_track_by_starts));
    return Boolean(context.track && profileTrack && context.track === profileTrack);
  }
  if (statKey === "distance") {
    const profileDistance = distanceNumber(firstValue(stats.latest_distance, stats.best_distance_by_starts));
    return Boolean(context.distance && profileDistance && context.distance === profileDistance);
  }
  if (statKey === "track_distance") {
    const profileTrack = normalizeText(firstValue(stats.latest_track, stats.best_track_by_starts));
    const profileDistance = distanceNumber(firstValue(stats.latest_distance, stats.best_distance_by_starts));
    return Boolean(context.track && context.distance && profileTrack === context.track && profileDistance === context.distance);
  }
  if (statKey === "class") {
    const profileClass = normalizeText(stats.latest_class);
    return Boolean(context.raceClass && profileClass && context.raceClass === profileClass);
  }
  if (statKey === "jockey") {
    const profileJockey = normalizeText(stats.latest_jockey);
    return Boolean(context.jockey && profileJockey && context.jockey === profileJockey);
  }
  if (statKey.startsWith("condition_")) return Boolean(context.condition && context.condition === statKey);
  return false;
}

function recordRow(key: string, label: string, starts: any, wins: any, seconds: any, thirds: any, stats: RunnerProfileStats, currentRace?: any): ProfileStatRow | undefined {
  if (!hasNumber(starts)) return undefined;
  return {
    key,
    label,
    value: racingRecord(starts, wins, seconds, thirds),
    isToday: isTodayRelevantStat(key, stats, currentRace),
  };
}

function metricRow(key: string, label: string, value: any): ProfileStatRow | undefined {
  return hasValue(value) ? { key, label, value: String(value) } : undefined;
}

function spRow(key: string, label: string, value: any): ProfileStatRow | undefined {
  const formatted = formatSp(value);
  return formatted ? { key, label, value: formatted } : undefined;
}

function conditionCoverageIsKnown(stats: RunnerProfileStats) {
  if (!hasNumber(stats.career_starts)) return false;
  const trackedStarts =
    numberValue(stats.good_starts) +
    numberValue(stats.soft_starts) +
    numberValue(stats.heavy_starts) +
    numberValue(stats.firm_starts) +
    numberValue(stats.synthetic_starts);
  return trackedStarts === numberValue(stats.career_starts);
}

function buildProfileSections(stats?: RunnerProfileStats, currentRace?: any): ProfileStatSection[] {
  if (!stats) return [];
  const conditionCoverageKnown = conditionCoverageIsKnown(stats);

  const firmRow = hasNumber(stats.firm_starts)
    ? recordRow("condition_firm", "Firm", stats.firm_starts, stats.firm_wins, stats.firm_seconds, stats.firm_thirds, stats, currentRace)
    : conditionCoverageKnown
      ? recordRow("condition_firm", "Firm", 0, 0, 0, 0, stats, currentRace)
      : undefined;

  const syntheticRow = hasNumber(stats.synthetic_starts)
    ? recordRow("condition_synthetic", "Synthetic", stats.synthetic_starts, stats.synthetic_wins, stats.synthetic_seconds, stats.synthetic_thirds, stats, currentRace)
    : conditionCoverageKnown
      ? recordRow("condition_synthetic", "Synthetic", 0, 0, 0, 0, stats, currentRace)
      : undefined;

  const sections = [
    {
      title: "Career",
      rows: [
        recordRow("career", "Career", stats.career_starts, stats.career_wins, stats.career_seconds, stats.career_thirds, stats, currentRace),
        metricRow("career_win_pct", "Win %", formatPct(stats.career_win_pct)),
        metricRow("career_place_pct", "Place %", formatPct(stats.career_place_pct)),
      ],
    },
    {
      title: "Recent",
      rows: [
        recordRow("last_5", "Last 5", stats.last_5_starts, stats.last_5_wins, stats.last_5_seconds, stats.last_5_thirds, stats, currentRace),
        recordRow("last_10", "Last 10", stats.last_10_starts, stats.last_10_wins, stats.last_10_seconds, stats.last_10_thirds, stats, currentRace),
        metricRow("avg_finish", "Avg Finish", hasValue(stats.last_5_avg_finish) ? `Avg Fin ${stats.last_5_avg_finish}` : ""),
      ],
    },
    {
      title: "Conditions",
      rows: [
        firmRow,
        recordRow("condition_good", "Good", stats.good_starts, stats.good_wins, stats.good_seconds, stats.good_thirds, stats, currentRace),
        recordRow("condition_soft", "Soft", stats.soft_starts, stats.soft_wins, stats.soft_seconds, stats.soft_thirds, stats, currentRace),
        recordRow("condition_heavy", "Heavy", stats.heavy_starts, stats.heavy_wins, stats.heavy_seconds, stats.heavy_thirds, stats, currentRace),
        syntheticRow,
      ],
    },
    {
      title: "Suitability",
      rows: [
        recordRow("track", "Track", stats.latest_track_starts, stats.latest_track_wins, stats.latest_track_seconds, stats.latest_track_thirds, stats, currentRace),
        recordRow("distance", "Distance", stats.latest_distance_starts, stats.latest_distance_wins, stats.latest_distance_seconds, stats.latest_distance_thirds, stats, currentRace),
        recordRow("track_distance", "Track/Dist", stats.latest_track_distance_starts, stats.latest_track_distance_wins, stats.latest_track_distance_seconds, stats.latest_track_distance_thirds, stats, currentRace),
        recordRow("class", "Class", stats.latest_class_starts, stats.latest_class_wins, stats.latest_class_seconds, stats.latest_class_thirds, stats, currentRace),
        recordRow("jockey", "Jockey", stats.latest_jockey_starts, stats.latest_jockey_wins, stats.latest_jockey_seconds, stats.latest_jockey_thirds, stats, currentRace),
      ],
    },
    {
      title: "Preparation",
      rows: [
        recordRow("first_up", "1st Up", stats.first_up_starts, stats.first_up_wins, stats.first_up_seconds, stats.first_up_thirds, stats, currentRace),
        recordRow("second_up", "2nd Up", stats.second_up_starts, stats.second_up_wins, stats.second_up_seconds, stats.second_up_thirds, stats, currentRace),
        recordRow("third_up", "3rd Up", stats.third_up_starts, stats.third_up_wins, stats.third_up_seconds, stats.third_up_thirds, stats, currentRace),
      ],
    },
    {
      title: "Market",
      rows: [
        spRow("avg_sp", "Avg SP", stats.avg_sp),
        spRow("best_sp", "Best SP", stats.best_sp),
        spRow("last_sp", "Last SP", stats.last_start_sp),
      ],
    },
  ];

  return sections
    .map((section) => ({
      ...section,
      rows: section.rows.filter((row): row is ProfileStatRow => Boolean(row) && hasValue(row.value)),
    }))
    .filter((section) => section.rows.length > 0);
}

export function RunnerProfileSummary({
  runner,
  currentRace,
  bestRun,
  clean,
  weight,
  market,
  dna,
  importance,
}: RunnerProfileSummaryProps) {
  const official = runner?.official ?? {};
  const runnerName = firstValue(official.runner, runner?.runner, runner?.name, runner?.latest_runner_name);
  const [profileRows, setProfileRows] = useState<RunnerProfileStats[] | null>(null);

  useEffect(() => {
    let active = true;
    loadRunnerProfileStats().then((rows) => {
      if (active) setProfileRows(rows);
    });
    return () => {
      active = false;
    };
  }, []);

  const profileStats = useMemo(
    () => findRunnerProfileStats(profileRows ?? [], runnerName),
    [profileRows, runnerName],
  );
  const currentProfileContext = useMemo(
    () => ({ ...(currentRace ?? {}), jockey: official.jockey }),
    [currentRace, official.jockey],
  );
  const profileSections = useMemo(() => buildProfileSections(profileStats, currentProfileContext), [profileStats, currentProfileContext]);
  const evidenceRole = bestRun ? evidenceLabel(importance(bestRun)) : "";
  const analystSummary = displayPunterSummary(firstValue(
    runner?.assessment,
    bestRun?.professionalForm?.evidence?.narrative,
    bestRun?.assessment,
  ));
  const esiStandard = firstValue(
    bestRun?.relativePerformance,
    bestRun?.professionalForm?.assignment?.edge,
  );

  const snapshotMetrics = [
    ["Trainer", official.trainer, clean],
    ["Jockey", official.jockey, clean],
    ["Bar", official.barrier, clean],
    ["Wt", official.weight, weight],
    ["Market", official.market, market],
    ["Run Style", firstValue(runner?.runStyle, runner?.runnerStyle, runner?.speedProfile), clean],
    ["Chance Type", evidenceRole, clean],
    ["DNA Status", hasMeaningfulValue(runner?.runnerDNA) ? runner?.runnerDNA : "", dna],
  ].filter(([, value]) => hasMeaningfulValue(value));

  const intelligenceMetrics = [
    ["EPI", ratingValue(bestRun), clean],
    ["ERI", raceValue(bestRun), clean],
    ["Chance Type", evidenceRole, clean],
    ["ESI Standard", esiStandard, clean],
    ["DNA", hasMeaningfulValue(runner?.runnerDNA) ? runner?.runnerDNA : "", dna],
  ].filter(([, value]) => hasMeaningfulValue(value));

  return (
    <section className="eiq-runner-profile-summary eiq-runner-profile-summary--v2">
      <article className="eiq-runner-profile-summary__panel eiq-runner-profile-summary__snapshot">
        <div className="eiq-runner-profile-summary__title">
          <span>HORSE</span>
          <strong>{clean(runnerName)}</strong>
        </div>
        <div className="eiq-runner-profile-summary__metrics">
          {snapshotMetrics.map(([label, value, formatter]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{formatter(value)}</dd>
            </div>
          ))}
        </div>
      </article>

      <article className="eiq-runner-profile-summary__panel eiq-runner-profile-summary__stats">
        <span>CAREER PROFILE</span>
        {profileRows === null ? (
          <p>Connecting career profile.</p>
        ) : !profileStats ? (
          <p>Career profile not yet connected for this runner.</p>
        ) : profileSections.length ? (
          <div className="eiq-runner-profile-summary__section-grid">
            {profileSections.map((section) => (
              <section key={section.title} className="eiq-runner-profile-summary__section">
                <h4>{section.title}</h4>
                <div className="eiq-stat-tile-row">
                  {section.rows.map((row) => (
                    <div
                      key={`${section.title}-${row.key}-${row.label}`}
                      className={`eiq-stat-row${row.isToday ? " eiq-stat-row--today" : ""}`}
                    >
                      <span className="eiq-stat-label">{clean(row.label)}</span>
                      <strong className="eiq-stat-value">{clean(row.value)}</strong>
                    </div>
                  ))}
                </div>
              </section>
            ))}
            <small>Profile stats derived from historical results.</small>
          </div>
        ) : (
          <p>Historical profile is connected; displayable career totals are not available for this runner.</p>
        )}
      </article>

      <article className="eiq-runner-profile-summary__panel eiq-runner-profile-summary__intelligence">
        <span>TODAY'S ASSESSMENT</span>
        {intelligenceMetrics.length ? (
          <div className="eiq-runner-profile-summary__metrics eiq-runner-profile-summary__metrics--intelligence">
            {intelligenceMetrics.map(([label, value, formatter]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{formatter(value)}</dd>
              </div>
            ))}
          </div>
        ) : null}
        {hasMeaningfulValue(analystSummary) ? (
          <p className="eiq-runner-profile-summary__narrative">{clean(analystSummary)}</p>
        ) : intelligenceMetrics.length ? null : (
          <p>Today's assessment is not yet connected for this runner.</p>
        )}
      </article>
    </section>
  );
}
