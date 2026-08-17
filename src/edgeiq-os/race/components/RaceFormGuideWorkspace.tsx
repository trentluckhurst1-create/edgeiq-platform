import { useEffect, useMemo, useState } from "react";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import {
  normaliseFormGuideRace,
  type FormGuideRunnerDisplay,
  type FormGuideProfileLine,
} from "../services/formGuideNormaliser";
import {
  findEnrichedFormGuideRace,
  loadFormGuideEnrichedFeed,
  type EnrichedFormGuideRace,
} from "../services/formGuideEnrichedFeed";
import { canonicalTrackDisplayName } from "../../design-system/presentation";
import {
  EiqButton,
  EiqDataTable,
  EiqMetric,
  EiqPanel,
  EiqSectionHeader,
  EiqStatusBadge,
} from "../../design-system/v1";

type RaceFormGuideWorkspaceProps = {
  raceBook: any;
  field: ThreeDayRunner[];
  meetingRaces: ThreeDayRace[];
  selectedRaceKey?: string;
  onOpenRace?: (race: ThreeDayRace) => void;
};

const DASH = "-";

const formGuideTrackAbbreviations: Record<string, string> = {
  ARARAT: "ARAR",
  BENDIGO: "BEND",
  CASTERTON: "CAST",
  CAULFIELD: "CAUL",
  "CAUL-HEATH": "C-HEATH",
  FLEMINGTON: "FLEM",
  GEELONG: "GEEL",
  HAMILTON: "HAM",
  "GREAT WESTERN": "G WST",
  HEALESVILLE: "HEALS",
  BALNARRING: "BALN",
  "MOONEE VALLEY": "MV",
  "SANDOWN HILLSIDE": "SAN-H",
  "SANDOWN LAKESIDE": "SAN-L",
  AVOCA: "AVO",
  ALEXANDRA: "ALEX",
  BAIRNSDALE: "BAIRN",
  "BALLARAT SYNTHETIC": "B-SYN",
  BALLARAT: "BALL",
  BENALLA: "BENA",
  BUCHAN: "BUCH",
  BURRUMBEET: "BURR",
  CAMPERDOWN: "CAMP",
  COLAC: "COL",
  COLERAINE: "COLE",
  CRANBOURNE: "CRAN",
  "CRANBOURNE TRAINING TRACK": "CRAN TR",
  DEDERANG: "DEDE",
  DONALD: "DONA",
  DROUIN: "DRO",
  DUNKELD: "DUNK",
  ECHUCA: "ECH",
  EDENHOPE: "EDEN",
  GUNBOWER: "GUNB",
  "HANGING ROCK": "H RK",
  HORSHAM: "HORS",
  HINNOMUNJIE: "HINN",
  KERANG: "KERA",
  KILMORE: "KILM",
  KYNETON: "KYNE",
  MANANGATANG: "MANA",
  MANSFIELD: "MANS",
  MERTON: "MERT",
  MILDURA: "MILD",
  MOE: "MOE",
};

const summaryColumns = [
  "NO",
  "SILKS",
  "LAST 5",
  "HORSE",
  "TRAINER",
  "JOCKEY",
  "WGT",
  "BAR",
  "DAYS",
  "EPR",
  "EARLY SPEED",
  "LATE SPEED",
  "SUITABILITY",
  "FORM MOMENTUM",
  "MARKET",
  "EDGEiQ PRICE",
] as const;

const summaryColumnWidths = [
  "38px",
  "46px",
  "86px",
  "170px",
  "138px",
  "132px",
  "48px",
  "42px",
  "48px",
  "58px",
  "78px",
  "76px",
  "90px",
  "104px",
  "72px",
  "88px",
];

const recentBaseColumns = [
  "DATE",
  "TRACK",
  "DIST",
  "CLASS",
  "POS",
  "MARGIN (L)",
  "EPI",
  "ERI",
  "SP",
  "BAR",
  "WGT",
  "JOCKEY",
] as const;

const recentCoreColumnWidths = [
  "96px",
  "92px",
  "72px",
  "92px",
  "54px",
  "78px",
  "58px",
  "58px",
  "58px",
  "54px",
  "64px",
  "150px",
] as const;

type CareerSummaryCell = { label: string; value: string; highlight?: boolean };

function cleanDisplay(value: string | number | null | undefined): string {
  const text = String(value ?? "").trim();
  if (!text || ["UNKNOWN", "NOT LOADED", "SOURCE GAP", "NULL", "UNDEFINED", "NAN"].includes(text.toUpperCase())) return DASH;
  if (text === "0.0%") return DASH;
  return text;
}

function normaliseTrackAbbreviationKey(value: string): string {
  return String(value || "").trim().replace(/\s+/g, " ").toUpperCase();
}

function formGuideHistoricalTrackDisplay(track: string): string {
  const displayName = canonicalTrackDisplayName(track);
  return (
    formGuideTrackAbbreviations[normaliseTrackAbbreviationKey(track)] ??
    formGuideTrackAbbreviations[normaliseTrackAbbreviationKey(displayName)] ??
    displayName
  );
}

function safeAnchorPart(value: string): string {
  return String(value || "").trim().replace(/[^a-z0-9_-]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
}

function runnerProfileId(runner: FormGuideRunnerDisplay): string {
  return `runner-profile-${safeAnchorPart(runner.id)}`;
}

function LastFiveStrip({ values }: { values: string[] }) {
  return (
    <span className="eiq-form-last5-strip" aria-label="Last five starts">
      {values.slice(0, 5).map((value) => cleanDisplay(value)).join(" ")}
    </span>
  );
}


function CurrentMetricStrip({ runner }: { runner: FormGuideRunnerDisplay }) {
  const metrics = [
    {
      key: "epi",
      label: "EPR",
      value: runner.epi,
      supporting: runner.epiDifference,
    },
    { key: "early", label: "EARLY SPEED", value: runner.earlySpeed, supporting: runner.earlySpeedLabel },
    { key: "late", label: "LATE SPEED", value: runner.late, supporting: "" },
    {
      key: "suitability",
      label: "SUITABILITY",
      value: runner.suitabilityScore,
      supporting: runner.suitabilityLabel,
    },
    {
      key: "momentum",
      label: "FORM MOMENTUM",
      value: runner.formMomentum,
      supporting:
        runner.formMomentumDirection === "up"
          ? "Rising"
          : runner.formMomentumDirection === "down"
            ? "Easing"
            : "",
    },
    {
      key: "market",
      label: "MARKET",
      value: runner.marketPrice,
      supporting: "",
    },
    { key: "edgeiq-price", label: "EDGEiQ PRICE", value: runner.edgeiqPrice, supporting: "" },
  ];

  return (
    <div
      className="eiq-form-v5-current-strip eiq-form-v4-current-strip eiq-form-final-current-strip eiq-form-locked-metric-ribbon"
      data-region="hero_metrics"
    >
      {metrics.map((metric) => (
        <EiqMetric
          key={metric.key}
          label={metric.label}
          value={cleanDisplay(metric.value)}
          detail={metric.supporting ? cleanDisplay(metric.supporting) : " "}
        />
      ))}
    </div>
  );
}

function profileLineByLabel(rows: FormGuideProfileLine[], labels: string[]): FormGuideProfileLine | null {
  const keys = labels.map((value) => value.toUpperCase().replace(/[^A-Z0-9]+/g, ""));
  return rows.find((row) => keys.includes(row.label.toUpperCase().replace(/[^A-Z0-9]+/g, ""))) ?? null;
}

function placesFromLine(line: FormGuideProfileLine | null): string {
  if (!line) return "";
  const seconds = Number(line.seconds);
  const thirds = Number(line.thirds);
  if (!Number.isFinite(seconds) && !Number.isFinite(thirds)) return "";
  return String((Number.isFinite(seconds) ? seconds : 0) + (Number.isFinite(thirds) ? thirds : 0));
}

function lineRecord(line: FormGuideProfileLine | null): string {
  return line?.record || "";
}

function careerCells(runner: FormGuideRunnerDisplay): CareerSummaryCell[] {
  const career = profileLineByLabel(runner.careerProfile, ["Career"]);
  const track = profileLineByLabel(runner.careerProfile, ["Track"]);
  const distance = profileLineByLabel(runner.careerProfile, ["Distance"]);
  const firm = profileLineByLabel(runner.conditionProfile, ["Firm"]);
  const good = profileLineByLabel(runner.conditionProfile, ["Good"]);
  const soft = profileLineByLabel(runner.conditionProfile, ["Soft"]);
  const heavy = profileLineByLabel(runner.conditionProfile, ["Heavy"]);
  const firstUp = profileLineByLabel(runner.raceDayPattern, ["1st Up", "First Up"]);
  const secondUp = profileLineByLabel(runner.raceDayPattern, ["2nd Up", "Second Up"]);
  const thirdUp = profileLineByLabel(runner.raceDayPattern, ["3rd Up", "Third Up"]);
  return [
    { label: "STARTS", value: career?.starts || "" },
    { label: "WINS", value: career?.wins || "" },
    { label: "PLACES", value: placesFromLine(career) },
    { label: "WIN %", value: career?.winPct || "" },
    { label: "PLACE %", value: career?.placePct || "" },
    { label: "TRACK", value: lineRecord(track), highlight: track?.matchesToday },
    { label: "DISTANCE", value: lineRecord(distance), highlight: distance?.matchesToday },
    { label: "FIRM", value: lineRecord(firm), highlight: firm?.matchesToday },
    { label: "GOOD", value: lineRecord(good), highlight: good?.matchesToday },
    { label: "SOFT", value: lineRecord(soft), highlight: soft?.matchesToday },
    { label: "HEAVY", value: lineRecord(heavy), highlight: heavy?.matchesToday },
    { label: "1ST UP", value: lineRecord(firstUp), highlight: firstUp?.matchesToday },
    { label: "2ND UP", value: lineRecord(secondUp), highlight: secondUp?.matchesToday },
    { label: "3RD UP", value: lineRecord(thirdUp), highlight: thirdUp?.matchesToday },
    { label: "TRAINER", value: cleanDisplay(runner.trainer) },
  ];
}

function ProfileTable({ title, eyebrow, cells }: { title: string; eyebrow: string; cells: CareerSummaryCell[] }) {
  return (
    <EiqPanel density="compact" className="eiq-form-v6-profile-table-panel eiq-form-v6-profile-table-panel--career">
      <EiqSectionHeader eyebrow={eyebrow} title={title} />
      <EiqDataTable density="dense" className="eiq-form-v6-profile-table eiq-form-v6-profile-table--career" wrapperProps={{ className: "eiq-form-v5-table-scroll" }}>
        <thead><tr>{cells.map((cell) => <th key={cell.label} className={cell.highlight ? "is-today" : ""}>{cell.label}</th>)}</tr></thead>
        <tbody><tr>{cells.map((cell) => <td key={cell.label} className={cell.highlight ? "is-today" : ""}>{cleanDisplay(cell.value)}</td>)}</tr></tbody>
      </EiqDataTable>
    </EiqPanel>
  );
}

function CareerSummary({ runner }: { runner: FormGuideRunnerDisplay }) {
  return <ProfileTable eyebrow="Career Summary" title="Career Summary" cells={careerCells(runner)} />;
}

function sectionalClassName(value: string): string {
  const parsed = Number(String(value || "").replace("+", ""));
  if (!Number.isFinite(parsed)) return "is-empty";
  if (parsed < 0) return "is-negative";
  if (parsed > 0) return "is-positive";
  return "is-neutral";
}

const standardLengthColumns = ["S-8", "8-6", "6-4", "4-2", "2-F"] as const;

function standardTimeValue(run: FormGuideRunnerDisplay["recentRuns"][number], label: string): string {
  if (label === "S-8") return run.esiS8;
  if (label === "8-6") return run.esi800600;
  if (label === "6-4") return run.esi600400;
  if (label === "4-2") return run.esi400200;
  if (label === "2-F") return run.esi200F;
  return "";
}

function RecentForm({ runner }: { runner: FormGuideRunnerDisplay }) {
  const [expanded, setExpanded] = useState(false);
  const visibleRuns = expanded ? runner.recentRuns : runner.recentRuns.slice(0, 8);
  const title = expanded ? "Full Career Form" : "Recent Form (Last 8 Starts)";
  const recentTableMinWidth = 876 + standardLengthColumns.length * 72;

  return (
    <EiqPanel density="compact" className="eiq-form-v5-recent-form eiq-form-v31-recent-form eiq-form-v4-recent-form eiq-form-final-recent-form" data-region="recent_form">
      <EiqSectionHeader eyebrow="Recent Form" title={title} />
      <EiqDataTable
        density="dense"
        className="eiq-form-v5-recent-table"
        wrapperProps={{ className: "eiq-form-v5-table-scroll" }}
        style={{ minWidth: `${recentTableMinWidth}px` }}
        data-columns={[...recentBaseColumns, "EDGEIQ STANDARD TIMES (LENGTHS / FURLONG)", ...standardLengthColumns].join("|")}
      >
          <colgroup>
            {recentCoreColumnWidths.map((width, index) => <col key={`${recentBaseColumns[index]}-${width}`} style={{ width }} />)}
            {standardLengthColumns.map((label) => <col key={`std-col-${label}`} style={{ width: "72px" }} />)}
          </colgroup>
          <thead>
            <tr>
              {recentBaseColumns.map((column) => <th key={column} rowSpan={2}>{column}</th>)}
              <th className="eiq-form-v6-group-head" colSpan={standardLengthColumns.length}>EDGEIQ STANDARD TIMES (LENGTHS / FURLONG)</th>
            </tr>
            <tr>
              {standardLengthColumns.map((label) => <th key={`std-${label}`}>{label}</th>)}
            </tr>
          </thead>
          <tbody>
            {visibleRuns.map((run, index) => (
              <tr key={`${runner.id}-run-${index}`}>
                <td>{cleanDisplay(run.date)}</td>
                <td>{cleanDisplay(formGuideHistoricalTrackDisplay(run.track))}</td>
                <td>{cleanDisplay(run.distance)}</td>
                <td>{cleanDisplay(run.raceClass)}</td>
                <td>{cleanDisplay(run.position)}</td>
                <td>{cleanDisplay(run.margin)}</td>
                <td>{cleanDisplay(run.epi)}</td>
                <td>{cleanDisplay(run.eri)}</td>
                <td>{cleanDisplay(run.sp)}</td>
                <td>{cleanDisplay(run.barrier)}</td>
                <td>{cleanDisplay(run.weight)}</td>
                <td>{cleanDisplay(run.jockey)}</td>
                {standardLengthColumns.map((label) => {
                  const value = standardTimeValue(run, label);
                  return <td key={`std-${label}-${index}`} className={sectionalClassName(value)}>{cleanDisplay(value)}</td>;
                })}
              </tr>
            ))}
          </tbody>
      </EiqDataTable>
      {!runner.recentRuns.length ? <p className="eiq-form-empty">No governed recent-form rows are published for this runner.</p> : null}
      {runner.recentRuns.length ? (
        <div className="eiq-form-v6-career-action">
          <EiqButton size="compact" variant="secondary" onClick={() => setExpanded((current) => !current)}>
            {expanded ? "RECENT FORM (LAST 8 STARTS)" : "FULL CAREER FORM"}
          </EiqButton>
        </div>
      ) : null}
    </EiqPanel>
  );
}


function RunnerHeroHeader({ runner }: { runner: FormGuideRunnerDisplay }) {
  const horseDescription = [
    runner.age ? `${runner.age}yo` : "",
    runner.sex,
    runner.breeding,
  ].filter(Boolean);

  const connections = [
    runner.trainer ? `Trainer: ${runner.trainer}` : "",
    runner.jockey
      ? `Jockey: ${runner.jockey}${runner.weight ? ` (${runner.weight})` : ""}`
      : "",
  ].filter(Boolean);

  const raceDetails = [
    horseDescription.length ? horseDescription.join(" | ") : "",
    runner.effectiveBarrier
      ? `Effective Barrier ${runner.effectiveBarrier}`
      : runner.barrier
        ? `Barrier ${runner.barrier}`
        : "",
  ].filter(Boolean);

  return (
    <header
      className="eiq-form-production-runner-hero"
      data-region="runner_hero_header"
    >
      <div className="eiq-form-production-runner-number">
        {cleanDisplay(runner.no)}
      </div>

      <div className="eiq-form-production-silk">
        {runner.silkUrl ? (
          <img
            src={runner.silkUrl}
            alt={`${runner.horse} silks`}
            loading="lazy"
          />
        ) : (
          <span
            className="eiq-form-production-silk-placeholder"
            aria-label="Silks unavailable"
          />
        )}
      </div>

      <div className="eiq-form-production-identity">
        <h3>{cleanDisplay(runner.horse)}</h3>

        <p className="eiq-form-production-connections">
          {connections.length ? connections.join(" | ") : DASH}
        </p>

        <p className="eiq-form-production-description">
          {raceDetails.length ? raceDetails.join(" | ") : DASH}
        </p>

        {runner.scratched ? (
          <EiqStatusBadge status="Scratched" />
        ) : null}
      </div>

      <CurrentMetricStrip runner={runner} />
    </header>
  );
}

function SelectedRunnerDossier({ runner }: { runner: FormGuideRunnerDisplay }) {
  return (
    <section
      id={runnerProfileId(runner)}
      className={`eiq-form-v6-selected-runner ${runner.scratched ? "is-scratched" : ""}`.trim()}
      data-runner-profile="true"
      data-runner-no={runner.no}
    >
      <RunnerHeroHeader runner={runner} />
      <CareerSummary runner={runner} />
      <RecentForm runner={runner} />
    </section>
  );
}

export function RaceFormGuideWorkspace({ raceBook, field, meetingRaces, selectedRaceKey }: RaceFormGuideWorkspaceProps) {
  const [enrichedRace, setEnrichedRace] = useState<EnrichedFormGuideRace | null>(null);
  const [selectedRunnerId, setSelectedRunnerId] = useState<string | null>(null);
  const [highlightedRunnerId, setHighlightedRunnerId] = useState<string | null>(null);
  const guide = useMemo(() => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace), [raceBook, field, meetingRaces, enrichedRace]);

  const orderedRunners = useMemo(
    () =>
      [...guide.runners].sort((left, right) => {
        const leftNumber = Number.parseInt(String(left.no ?? "").replace(/[^0-9]/g, ""), 10);
        const rightNumber = Number.parseInt(String(right.no ?? "").replace(/[^0-9]/g, ""), 10);

        const leftValid = Number.isFinite(leftNumber);
        const rightValid = Number.isFinite(rightNumber);

        if (leftValid && rightValid && leftNumber !== rightNumber) {
          return leftNumber - rightNumber;
        }

        if (leftValid !== rightValid) {
          return leftValid ? -1 : 1;
        }

        return String(left.horse ?? "").localeCompare(String(right.horse ?? ""));
      }),
    [guide.runners],
  );

  const selectedRunner = orderedRunners.find((runner) => runner.id === selectedRunnerId) ?? orderedRunners[0] ?? null;

  const selectRunner = (runner: FormGuideRunnerDisplay) => {
    setSelectedRunnerId(runner.id);
    setHighlightedRunnerId(runner.id);
    window.setTimeout(() => {
      setHighlightedRunnerId((current) => current === runner.id ? null : current);
    }, 1800);
  };

  useEffect(() => {
    setHighlightedRunnerId(null);
    setSelectedRunnerId(null);
  }, [selectedRaceKey]);

  useEffect(() => {
    let cancelled = false;
    loadFormGuideEnrichedFeed()
      .then((feed) => {
        if (cancelled) return;
        setEnrichedRace(findEnrichedFormGuideRace(feed, raceBook, meetingRaces));
      })
      .catch((error) => {
        console.warn("Form Guide enrichment unavailable", error);
        if (!cancelled) setEnrichedRace(null);
      });
    return () => { cancelled = true; };
  }, [raceBook, meetingRaces, selectedRaceKey]);

  return (
    <section className="eiq-form-v5-workspace eiq-v1-standard-workspace eiq-race-form-guide eiq-race-form-guide--v3 eiq-race-form-guide--v4 eiq-race-form-guide--all-runner eiq-race-form-guide--approved-exact eiq-race-form-guide--final-locked" aria-label="Race form guide" data-edgeiq-workspace="form-guide-final-locked" data-region="form_guide_workspace">
      <EiqPanel density="compact" className="eiq-form-v5-summary-panel">
        <EiqSectionHeader eyebrow="FORM GUIDE" title="Main FORM GUIDE runner table" />
        <EiqDataTable
          density="dense"
          className="eiq-form-v5-summary-table"
          wrapperProps={{ className: "eiq-form-v5-table-scroll eiq-form-summary-table eiq-form-summary-table--v3 eiq-form-summary-table--all-runner eiq-form-summary-table--final-locked" }}
          data-region="summary_table"
          data-columns={summaryColumns.join("|")}
        >
          <colgroup>{summaryColumnWidths.map((width, index) => <col key={`${summaryColumns[index]}-${width}`} style={{ width }} />)}</colgroup>
          <thead><tr>{summaryColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {orderedRunners.map((runner) => (
              <tr
                key={runner.id}
                className={`${runner.scratched ? "is-scratched" : ""} ${selectedRunner?.id === runner.id ? "is-selected" : ""} ${highlightedRunnerId === runner.id ? "is-targeted" : ""}`.trim()}
              >
                <td className="eiq-cell-no">{cleanDisplay(runner.no)}</td>
                <td>{runner.silkUrl ? <img className="eiq-form-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-silk eiq-form-silk--fallback" aria-hidden="true" />}</td>
                <td className="eiq-cell-last-five">{runner.lastFive.length ? <LastFiveStrip values={runner.lastFive} /> : DASH}</td>
                <td>
                  <button
                    type="button"
                    className="eiq-form-runner-anchor eiq-form-runner-navigator"
                    aria-controls={runnerProfileId(runner)}
                    aria-current={selectedRunner?.id === runner.id ? "true" : undefined}
                    onClick={() => selectRunner(runner)}
                  >
                    <strong>{cleanDisplay(runner.horse)}</strong>
                    {runner.scratched ? <small>SCRATCHED</small> : null}
                  </button>
                </td>
                <td>{cleanDisplay(runner.trainer)}</td>
                <td>{cleanDisplay(runner.jockey)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.weight)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.barrier)}</td>
                <td className="eiq-cell-days">{cleanDisplay(runner.daysSinceLastRun)}</td>
                <td className="eiq-cell-epi">{cleanDisplay(runner.epi)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.earlySpeed)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.late)}</td>
                <td className="eiq-cell-suitability">{cleanDisplay(runner.suitabilityScore)}</td>
                <td className="eiq-cell-momentum" data-direction={runner.formMomentumDirection}>{cleanDisplay(runner.formMomentum)}</td>
                <td className="eiq-cell-price eiq-cell-market">{cleanDisplay(runner.marketPrice)}</td>
                <td className="eiq-cell-price eiq-cell-edgeiq-price">{cleanDisplay(runner.edgeiqPrice)}</td>
              </tr>
            ))}
          </tbody>
        </EiqDataTable>
      </EiqPanel>

      {selectedRunner ? <SelectedRunnerDossier runner={selectedRunner} /> : null}

      <footer className="eiq-form-v3-footer"><span>{cleanDisplay(guide.fieldSummary)}</span><span>Data is modelled and subject to change.</span></footer>
    </section>
  );
}
