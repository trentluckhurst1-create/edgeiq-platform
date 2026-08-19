from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT_DIR = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"FORM_GUIDE_FINAL_SPEC_V1_{STAMP}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def checkpoint(path: Path) -> None:
    if not path.exists():
        return
    dest = CHECKPOINT_DIR / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


TRACE = """# EDGEIQ FORM GUIDE Trace V1

Generated: {generated}

## Canonical Source Flow

| Product field | Canonical source | Service path | Component path | Availability / gap |
| --- | --- | --- | --- | --- |
| NO | Three-day race catalog / race book runner identity | formGuideNormaliser.runnerNo | RaceFormGuideWorkspace main table | Available from official runner number with source fallback. |
| SILKS | Three-day race catalog / race book runner identity | formGuideNormaliser.silkUrl | RaceFormGuideWorkspace main table and dossier | Available where official silk URL is present; neutral fallback square otherwise. |
| LAST 5 | Enriched form guide / official form string | formGuideNormaliser.lastFive | RaceFormGuideWorkspace main table | Available starts only; no padded dashes. |
| HORSE | Race book + enriched runner join | formGuideNormaliser.runnerName | RaceFormGuideWorkspace main table and dossier | Available through runner catalog or enriched feed. |
| TRAINER | Race book runner fields | formGuideNormaliser.trainer | RaceFormGuideWorkspace main table and dossier | Available where official trainer is supplied. |
| JOCKEY | Race book runner fields | formGuideNormaliser.formatJockey | RaceFormGuideWorkspace main table and recent form | Current jockey available; historical jockey available through enriched fullForm where supplied. |
| WT | Race book runner fields | formGuideNormaliser.weight | RaceFormGuideWorkspace main table and dossier | Available where official carried weight exists. |
| BAR | Race book runner fields | formGuideNormaliser.barrier | RaceFormGuideWorkspace main table and recent form | Current and historical barrier available where supplied. |
| DAYS | Enriched form guide current runner row | daysSinceLastRun | RaceFormGuideWorkspace main table and dossier | Available where last official run date is joined. |
| EPI | edgeiq_epi_current_rating_v1 via enriched feed | formGuideNormaliser.epi | RaceFormGuideWorkspace main table and recent form | React displays only. |
| EARLY SPEED | edgeiq_current_early_speed_v1 via enriched feed | formGuideNormaliser.earlySpeed | RaceFormGuideWorkspace main table | React displays only. |
| LATE SPEED | edgeiq_current_late_speed_v1 via enriched feed | formGuideNormaliser.late | RaceFormGuideWorkspace main table | React displays only. |
| SUITABILITY | edgeiq_current_suitability_v1 via enriched feed | formGuideNormaliser.suitabilityScore | RaceFormGuideWorkspace main table | React displays only. |
| FORM MOMENTUM | edgeiq_current_form_momentum_v1 via enriched feed | formGuideNormaliser.formMomentum | RaceFormGuideWorkspace main table | React displays only. |
| MARKET | current market price carried by enriched feed | formGuideNormaliser.marketPrice | RaceFormGuideWorkspace main table | Current market path only; no component calculation. |
| EDGEiQ PRICE | approved pricing feed carried by enriched feed | formGuideNormaliser.edgeiqPrice | RaceFormGuideWorkspace main table | Displayed as EDGEiQ price; React does not calculate. |
| Career profile | edgeiq_runner_profile_stats_v1 / enriched profile records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Horse Profile | Career/track/distance/track-dist/class/jockey/prep rows are generic labels with governed records. |
| Conditions profile | edgeiq_runner_profile_stats_v1 / enriched condition records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Horse Profile | Firm/Good/Soft/Heavy shown when supplied; unavailable otherwise. |
| Today condition match | Current race context + existing matchesToday flag | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Today Match | Generic categories only; no invented match score. |
| Recent form | enriched fullForm | formGuideNormaliser.recentRunsFromEnriched | Runner dossier Recent Form | Up to eight historical starts. |
| Recent form EPI | standardised sectionals epi_post or performanceRating fallback | formGuideNormaliser.recentRunsFromEnriched | Recent Form table | Numeric display where supplied. |
| Recent form ERI | run_ratings_v1 raceRating source value | formGuideNormaliser.recentRunsFromEnriched | Recent Form table | Numeric display where supplied. |
| Recent form ESI segments | edgeiq_form_sectional_profile_feed_v1 split_lengths | formGuideNormaliser.recentRunsFromEnriched | Recent Form table 8-6 / 6-4 / 4-2 / 2-F | Standardised lengths only. No raw times. |
| Position In Running | Not present in current enriched feed contract | formGuideNormaliser.positionInRunning | Recent Form table | Column exists; values stay unavailable until a governed source is added. |
| Key Insights | formGuideNormaliser governed insight groups from available records | formGuideWorkspaceViewModel.buildRunnerProfileDossier | Runner dossier Key Insights | Uses supportable record/market/price notes only. |

## Mock / Demo Risk Trace

- No mock, demo, sample, or synthetic runner metrics are introduced by this tranche.
- No product-facing Confidence column or field is rendered by the FORM GUIDE component.
- No Race Shape or Avg Finish columns are rendered in the FORM GUIDE main table.
- React displays service-shaped fields and does not calculate EPI, ERI, ESI, market, price, suitability, speed, or form momentum.
"""


VIEW_MODEL = r'''import type {
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
'''


COMPONENT = r'''import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { ThreeDayRace, ThreeDayRunner } from "../services/threeDayCatalog";
import {
  displayOrDash,
  normaliseFormGuideRace,
  type FormGuideProfileGroup,
  type FormGuideRunnerDisplay,
} from "../services/formGuideNormaliser";
import {
  findEnrichedFormGuideRace,
  loadFormGuideEnrichedFeed,
  type EnrichedFormGuideRace,
} from "../services/formGuideEnrichedFeed";
import { buildRunnerProfileDossier } from "../services/formGuideWorkspaceViewModel";

type RaceFormGuideWorkspaceProps = {
  raceBook: any;
  field: ThreeDayRunner[];
  meetingRaces: ThreeDayRace[];
  selectedRaceKey?: string;
  onOpenRace?: (race: ThreeDayRace) => void;
};

const metricDefinitions = {
  "LAST 5": "Finishing positions from the runner's five most recent official starts. The most recent start appears first.",
  DAYS: "Calendar days since the runner's most recent official race start, measured against the selected race date.",
  EPI: "EDGEiQ Performance Index: the runner's approved performance figure for today's race.",
  "EARLY SPEED": "Expected early-position strength from the approved current early-speed feed.",
  "LATE SPEED": "Late-sectional strength from the approved current late-speed feed.",
  SUITABILITY: "Distance, conditions, class, preparation and setup suitability from the governed current feed.",
  "FORM MOMENTUM": "Current-form trend from approved performance and sectional evidence.",
  MARKET: "The runner's current available market price.",
  "EDGEiQ PRICE": "EDGEiQ assessed price from the approved pricing model.",
} as const;

const summaryColumns = [
  "NO",
  "SILKS",
  "LAST 5",
  "HORSE",
  "TRAINER",
  "JOCKEY",
  "WT",
  "BAR",
  "DAYS",
  "EPI",
  "EARLY SPEED",
  "LATE SPEED",
  "SUITABILITY",
  "FORM MOMENTUM",
  "MARKET",
  "EDGEiQ PRICE",
] as const;

const summaryColumnWidths = [
  "44px",
  "56px",
  "108px",
  "210px",
  "172px",
  "154px",
  "56px",
  "48px",
  "58px",
  "64px",
  "84px",
  "82px",
  "92px",
  "106px",
  "82px",
  "96px",
];

const recentFormColumns = [
  "DATE",
  "TRACK",
  "DIST",
  "CLASS",
  "COND",
  "JOCKEY",
  "BAR",
  "WT",
  "POS",
  "FIELD",
  "SP",
  "MARGIN",
  "EPI",
  "ERI",
  "PIR",
  "8-6",
  "6-4",
  "4-2",
  "2-F",
] as const;

function valueOrBlank(value: string): string {
  return value || "";
}

function safeAnchorPart(value: string): string {
  return String(value || "")
    .trim()
    .replace(/[^a-z0-9_-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
}

function runnerProfileId(runner: FormGuideRunnerDisplay): string {
  return `runner-profile-${safeAnchorPart(runner.id)}`;
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function scrollToRunner(runner: FormGuideRunnerDisplay) {
  const element = document.getElementById(runnerProfileId(runner));
  if (!element) return;
  const top = element.getBoundingClientRect().top + window.scrollY - 16;
  window.scrollTo({ top, behavior: "smooth" });
  window.history.replaceState(null, "", `#${runnerProfileId(runner)}`);
}

type TooltipState = {
  column: string;
  definition: string;
  left: number;
  top: number;
} | null;

function MetricHeader({
  column,
  setActiveTooltip,
}: {
  column: (typeof summaryColumns)[number];
  setActiveTooltip: (state: TooltipState) => void;
}) {
  const definition = metricDefinitions[column as keyof typeof metricDefinitions];
  const showTooltip = (target: HTMLElement) => {
    if (!definition) return;
    const rect = target.getBoundingClientRect();
    const width = 292;
    const left = clamp(rect.left + rect.width / 2, width / 2 + 12, window.innerWidth - width / 2 - 12);
    const top = rect.top - 16 < 12 ? 12 : rect.top - 16;
    setActiveTooltip({ column, definition, left, top });
  };

  return (
    <span className="eiq-form-metric-header">
      {definition ? (
        <button
          type="button"
          className="eiq-form-tooltip-trigger"
          aria-label={`${column}: ${definition}`}
          onMouseEnter={(event) => showTooltip(event.currentTarget)}
          onClick={(event) => showTooltip(event.currentTarget)}
          onMouseLeave={() => setActiveTooltip(null)}
          onFocus={(event) => showTooltip(event.currentTarget)}
          onBlur={() => setActiveTooltip(null)}
        >
          {column}
        </button>
      ) : (
        <span>{column}</span>
      )}
    </span>
  );
}

function MetricGuide() {
  const [open, setOpen] = useState(false);
  const guideRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (guideRef.current?.contains(event.target as Node)) return;
      setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="eiq-form-v33-tools" ref={guideRef}>
      <button
        type="button"
        className="eiq-form-metric-guide-button"
        aria-expanded={open}
        aria-controls="eiq-form-metric-guide-popover"
        onClick={() => setOpen((value) => !value)}
      >
        Metric Guide
      </button>
      {open ? (
        <div id="eiq-form-metric-guide-popover" className="eiq-form-metric-guide-popover" role="dialog" aria-label="Metric Guide">
          <dl>
            {Object.entries(metricDefinitions).map(([label, definition]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{definition}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </div>
  );
}

function LastFiveStrip({ values }: { values: string[] }) {
  return (
    <span className="eiq-form-last5-strip" aria-label="Last five starts">
      {values.map((value, index) => (
        <span key={`${value}-${index}`}>{value}</span>
      ))}
    </span>
  );
}

function CurrentMetricStrip({ runner }: { runner: FormGuideRunnerDisplay }) {
  const metrics = [
    ["EPI", runner.epi],
    ["Early Speed", runner.earlySpeed],
    ["Late Speed", runner.late],
    ["Suitability", runner.suitabilityScore],
    ["Form Momentum", runner.formMomentum],
    ["Market", runner.marketPrice],
    ["EDGEiQ Price", runner.edgeiqPrice],
  ];

  return (
    <dl className="eiq-form-v4-current-strip">
      {metrics.map(([label, value]) => (
        <div key={label} className={value ? "" : "is-empty"}>
          <dt>{label}</dt>
          <dd>{valueOrBlank(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function ProfileGroup({ group }: { group: FormGuideProfileGroup }) {
  return (
    <section className="eiq-form-v4-profile-group">
      <h3>{group.title}</h3>
      <div className="eiq-form-v4-profile-tiles">
        {group.tiles.map((tile) => (
          <article key={`${group.title}-${tile.label}`} className={tile.matchesToday ? "is-current-match" : ""}>
            <span>{tile.label}</span>
            <strong>{displayOrDash(tile.record)}</strong>
            <small>
              {[tile.winPct ? `${tile.winPct} win` : "", tile.placePct ? `${tile.placePct} place` : ""]
                .filter(Boolean)
                .join(" | ")}
            </small>
          </article>
        ))}
      </div>
    </section>
  );
}

function TodayMatch({ runner }: { runner: FormGuideRunnerDisplay }) {
  const dossier = buildRunnerProfileDossier(runner);
  return (
    <aside className="eiq-form-v4-today-match">
      <h3>Today's Match</h3>
      {dossier.todayMatch.length ? (
        <ul>
          {dossier.todayMatch.map((item) => (
            <li key={`${item.label}-${item.record}`}>
              <strong>{item.label}</strong>
              <span>{item.record}</span>
              {item.detail ? <small>{item.detail}</small> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p>Governed match evidence is not available for this runner.</p>
      )}
    </aside>
  );
}

function KeyInsights({ runner }: { runner: FormGuideRunnerDisplay }) {
  const dossier = buildRunnerProfileDossier(runner);
  const groups = dossier.keyInsights;

  return (
    <section className="eiq-form-v31-insights eiq-form-v4-key-insights">
      <h3>Key Insights</h3>
      {groups.length ? (
        <div className="eiq-form-v31-insight-grid">
          {groups.map((group) => (
            <article key={group.key}>
              <strong>{group.title}</strong>
              <ul>
                {group.items.map((item) => (
                  <li key={`${group.key}-${item.text}`} data-tone={item.tone}>
                    {item.text}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : (
        <p>{runner.scratched ? "Runner is scratched. Historical evidence remains below." : "Approved insight inputs are not available for this runner."}</p>
      )}
    </section>
  );
}

function sectionalClassName(value: string): string {
  const parsed = Number(String(value || "").replace("+", ""));
  if (!Number.isFinite(parsed)) return "is-empty";
  if (parsed < 0) return "is-negative";
  if (parsed > 0) return "is-positive";
  return "is-neutral";
}

function RecentForm({ runner }: { runner: FormGuideRunnerDisplay }) {
  return (
    <section className="eiq-form-v31-recent-form eiq-form-v4-recent-form">
      <header>
        <div>
          <span>RECENT FORM</span>
          <strong>Last 8 Starts</strong>
        </div>
        <p>ESI is EDGEiQ standardised lengths. Negative is inside standard; positive is outside standard.</p>
      </header>
      {runner.recentRuns.length ? (
        <div className="eiq-form-run-table eiq-form-run-table--v3 eiq-form-run-table--v4">
          <table data-columns={recentFormColumns.join("|")}>
            <thead>
              <tr>
                {recentFormColumns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runner.recentRuns.map((run, index) => (
                <tr key={`${runner.id}-run-${index}`}>
                  <td>{displayOrDash(run.date)}</td>
                  <td>{displayOrDash(run.track)}</td>
                  <td>{displayOrDash(run.distance)}</td>
                  <td>{displayOrDash(run.raceClass)}</td>
                  <td>{displayOrDash(run.condition)}</td>
                  <td>{displayOrDash(run.jockey)}</td>
                  <td>{displayOrDash(run.barrier)}</td>
                  <td>{displayOrDash(run.weight)}</td>
                  <td>{displayOrDash(run.position)}</td>
                  <td>{displayOrDash(run.fieldSize)}</td>
                  <td>{displayOrDash(run.sp)}</td>
                  <td>{displayOrDash(run.margin)}</td>
                  <td>{displayOrDash(run.epi)}</td>
                  <td>{displayOrDash(run.eri)}</td>
                  <td>{displayOrDash(run.positionInRunning)}</td>
                  <td className={sectionalClassName(run.esi800600)}>{displayOrDash(run.esi800600)}</td>
                  <td className={sectionalClassName(run.esi600400)}>{displayOrDash(run.esi600400)}</td>
                  <td className={sectionalClassName(run.esi400200)}>{displayOrDash(run.esi400200)}</td>
                  <td className={sectionalClassName(run.esi200F)}>{displayOrDash(run.esi200F)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="eiq-form-empty">Official recent-run detail is not available in the current source for this runner.</p>
      )}
    </section>
  );
}

function RunnerProfile({ runner }: { runner: FormGuideRunnerDisplay }) {
  const dossier = buildRunnerProfileDossier(runner);
  const identity = [
    runner.age ? `${runner.age}yo` : "",
    runner.sex,
    runner.breeding,
    runner.trainer ? `Trainer: ${runner.trainer}` : "",
    runner.jockey ? `Jockey: ${runner.jockey}` : "",
    runner.effectiveBarrier ? `Eff Bar ${runner.effectiveBarrier}` : runner.barrier ? `Bar ${runner.barrier}` : "",
    runner.weight,
  ].filter(Boolean);

  return (
    <article
      id={runnerProfileId(runner)}
      className={`eiq-form-v31-runner-sheet eiq-form-v4-runner-sheet ${runner.scratched ? "is-scratched" : ""}`.trim()}
      data-runner-profile="true"
      data-runner-no={runner.no}
    >
      <section className="eiq-form-v3-runner-header eiq-form-v31-runner-header eiq-form-v4-runner-header">
        {runner.silkUrl ? (
          <img className="eiq-form-detail-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" />
        ) : (
          <span className="eiq-form-detail-silk eiq-form-silk--fallback" aria-hidden="true" />
        )}
        <div className="eiq-form-v3-runner-identity">
          <span>{runner.scratched ? "SCRATCHED RUNNER" : "HORSE PROFILE"}</span>
          <strong><em>{runner.no}</em>{runner.horse}</strong>
          <p>{identity.join(" | ")}</p>
        </div>
        <CurrentMetricStrip runner={runner} />
      </section>

      <section className="eiq-form-v4-dossier-grid">
        <div className="eiq-form-v4-dossier-main">
          <section className="eiq-form-v4-current-details">
            {dossier.currentRaceDetails.map((item) => (
              <div key={item.label} className={item.value ? "" : "is-empty"}>
                <span>{item.label}</span>
                <strong>{displayOrDash(item.value)}</strong>
              </div>
            ))}
          </section>
          <section className="eiq-form-v4-profile-block">
            <header>
              <span>HORSE PROFILE</span>
              <strong>Career evidence for today's race</strong>
            </header>
            {dossier.profileGroups.map((group) => (
              <ProfileGroup key={group.title} group={group} />
            ))}
          </section>
        </div>
        <TodayMatch runner={runner} />
      </section>

      <RecentForm runner={runner} />
      <KeyInsights runner={runner} />
    </article>
  );
}

export function RaceFormGuideWorkspace({
  raceBook,
  field,
  meetingRaces,
  selectedRaceKey,
  onOpenRace,
}: RaceFormGuideWorkspaceProps) {
  const [enrichedRace, setEnrichedRace] = useState<EnrichedFormGuideRace | null>(null);
  const [activeTooltip, setActiveTooltip] = useState<TooltipState>(null);
  const [expandedRunnerId, setExpandedRunnerId] = useState<string | null>(null);
  const guide = useMemo(
    () => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace),
    [raceBook, field, meetingRaces, enrichedRace],
  );

  const runnerIds = useMemo(() => guide.runners.map((runner) => runner.id).join("|"), [guide.runners]);

  useEffect(() => {
    if (!guide.runners.length) {
      if (expandedRunnerId !== null) setExpandedRunnerId(null);
      return;
    }
    if (!expandedRunnerId || !guide.runners.some((runner) => runner.id === expandedRunnerId)) {
      setExpandedRunnerId(guide.runners[0].id);
    }
  }, [expandedRunnerId, guide.runners, runnerIds]);

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

    return () => {
      cancelled = true;
    };
  }, [raceBook, meetingRaces, selectedRaceKey]);

  return (
    <section className="eiq-race-form-guide eiq-race-form-guide--v3 eiq-race-form-guide--v4 eiq-race-form-guide--all-runner" aria-label="Race form guide">
      <header className="eiq-form-race-header eiq-form-race-header--v3">
        <div className="eiq-form-v3-race-title">
          <span>FORM GUIDE</span>
          <strong>{guide.primaryLine}</strong>
          <h2>{guide.raceName}</h2>
        </div>
        {guide.metadata.length ? (
          <dl>
            {guide.metadata.map((item) => (
              <div key={`${item.label}-${item.value}`}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </header>

      {meetingRaces.length > 1 ? (
        <nav className="eiq-form-race-selector" aria-label="Race selector">
          {meetingRaces.map((race) => {
            const active = String(race.raceKey) === String(selectedRaceKey ?? raceBook?.official?.raceKey);

            return (
              <button
                key={race.raceKey}
                type="button"
                className={active ? "is-active" : ""}
                onClick={() => onOpenRace?.(race)}
              >
                R{race.raceNumber}
              </button>
            );
          })}
        </nav>
      ) : null}

      <MetricGuide />

      <div className="eiq-form-summary-table eiq-form-summary-table--v3 eiq-form-summary-table--all-runner" data-columns={summaryColumns.join("|")}>
        <table>
          <colgroup>
            {summaryColumnWidths.map((width, index) => (
              <col key={`${summaryColumns[index]}-${width}`} style={{ width }} />
            ))}
          </colgroup>
          <thead>
            <tr>
              {summaryColumns.map((column) => (
                <th key={column}>
                  <MetricHeader column={column} setActiveTooltip={setActiveTooltip} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {guide.runners.map((runner) => {
              const isExpanded = expandedRunnerId === runner.id;
              return (
                <Fragment key={runner.id}>
                  <tr className={`${runner.scratched ? "is-scratched" : ""} ${isExpanded ? "is-expanded" : ""}`.trim()}>
                    <td className="eiq-cell-no">{runner.no}</td>
                    <td>{runner.silkUrl ? <img className="eiq-form-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-silk eiq-form-silk--fallback" aria-hidden="true" />}</td>
                    <td className="eiq-cell-last-five">{runner.lastFive.length ? <LastFiveStrip values={runner.lastFive} /> : ""}</td>
                    <td><button type="button" className="eiq-form-runner-anchor eiq-form-runner-expand" aria-expanded={isExpanded} aria-controls={runnerProfileId(runner)} onClick={() => { const next = isExpanded ? null : runner.id; setExpandedRunnerId(next); if (!isExpanded) window.requestAnimationFrame(() => scrollToRunner(runner)); }}><strong>{runner.horse}</strong>{runner.scratched ? <small>SCRATCHED</small> : null}</button></td>
                    <td>{displayOrDash(runner.trainer)}</td>
                    <td>{displayOrDash(runner.jockey)}</td>
                    <td className="eiq-cell-compact">{displayOrDash(runner.weight)}</td>
                    <td className="eiq-cell-compact">{displayOrDash(runner.barrier)}</td>
                    <td className="eiq-cell-days">{runner.daysSinceLastRun}</td>
                    <td className="eiq-cell-epi">{runner.epi}</td>
                    <td className="eiq-cell-compact">{runner.earlySpeed}</td>
                    <td className="eiq-cell-compact">{runner.late}</td>
                    <td className="eiq-cell-suitability"><strong>{runner.suitabilityScore}</strong><small>{runner.suitabilityLabel}</small></td>
                    <td className="eiq-cell-momentum" data-direction={runner.formMomentumDirection}>{runner.formMomentum}</td>
                    <td className="eiq-cell-price eiq-cell-market">{runner.marketPrice}</td>
                    <td className="eiq-cell-price eiq-cell-edgeiq-price">{runner.edgeiqPrice}</td>
                  </tr>
                  {isExpanded ? <tr className="eiq-form-expanded-row"><td colSpan={summaryColumns.length}><RunnerProfile runner={runner} /></td></tr> : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="eiq-form-v3-footer">
        <span>{guide.fieldSummary}</span>
        <span>Data is modelled and subject to change.</span>
      </footer>
      {activeTooltip
        ? createPortal(
            <div
              className="eiq-form-header-tooltip"
              role="tooltip"
              style={{ left: activeTooltip.left, top: activeTooltip.top }}
              data-column={activeTooltip.column}
            >
              <strong>{activeTooltip.column}</strong>
              <span>{activeTooltip.definition}</span>
            </div>,
            document.body,
          )
        : null}
    </section>
  );
}
'''


CSS_BLOCK = r'''

/* EDGEIQ FORM GUIDE FINAL SPEC V1 */
.eiq-race-form-guide--v4 {
  display: grid;
  gap: 14px;
}

.eiq-race-form-guide--v4 .eiq-form-summary-table--all-runner {
  overflow-x: auto;
}

.eiq-form-last5-strip {
  display: inline-flex;
  justify-content: center;
  gap: 4px;
  min-width: 86px;
}

.eiq-form-last5-strip span {
  min-width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--edgeiq-border);
  border-radius: 5px;
  background: #f8fafc;
  color: var(--edgeiq-text-primary);
  font-size: 11px;
  font-weight: 700;
}

.eiq-form-v4-runner-sheet {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.eiq-form-v4-runner-header {
  grid-template-columns: 56px minmax(260px, 1.2fr) minmax(520px, 2fr);
  gap: 14px;
  align-items: stretch;
}

.eiq-form-v4-current-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(78px, 1fr));
  gap: 0;
  border: 1px solid var(--edgeiq-border);
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.eiq-form-v4-current-strip div {
  padding: 9px 10px;
  border-right: 1px solid var(--edgeiq-border-soft);
  min-height: 52px;
}

.eiq-form-v4-current-strip div:last-child {
  border-right: 0;
}

.eiq-form-v4-current-strip dt,
.eiq-form-v4-current-details span,
.eiq-form-v4-profile-block header span,
.eiq-form-v4-profile-group h3,
.eiq-form-v4-today-match h3 {
  color: var(--edgeiq-primary);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.eiq-form-v4-current-strip dd,
.eiq-form-v4-current-details strong {
  margin: 4px 0 0;
  color: var(--edgeiq-text-primary);
  font-weight: 750;
  font-size: 15px;
}

.eiq-form-v4-current-strip div.is-empty dd,
.eiq-form-v4-current-details div.is-empty strong,
.eiq-form-v4-profile-tiles article:not(.is-current-match) small:empty {
  color: var(--edgeiq-text-muted);
}

.eiq-form-v4-dossier-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 300px);
  gap: 14px;
  align-items: start;
}

.eiq-form-v4-dossier-main {
  display: grid;
  gap: 12px;
}

.eiq-form-v4-current-details {
  display: grid;
  grid-template-columns: repeat(8, minmax(92px, 1fr));
  border: 1px solid var(--edgeiq-border);
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.eiq-form-v4-current-details div {
  min-height: 48px;
  padding: 8px 10px;
  border-right: 1px solid var(--edgeiq-border-soft);
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-form-v4-profile-block,
.eiq-form-v4-today-match {
  border: 1px solid var(--edgeiq-border);
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
}

.eiq-form-v4-profile-block header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-form-v4-profile-block header strong {
  color: var(--edgeiq-text-primary);
  font-size: 13px;
}

.eiq-form-v4-profile-group {
  display: grid;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-form-v4-profile-group:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.eiq-form-v4-profile-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
}

.eiq-form-v4-profile-tiles article {
  min-height: 60px;
  border: 1px solid var(--edgeiq-border-soft);
  border-radius: 9px;
  background: #f8fafc;
  padding: 8px 9px;
}

.eiq-form-v4-profile-tiles article.is-current-match {
  border-color: #b7cfff;
  background: #eef5ff;
}

.eiq-form-v4-profile-tiles span {
  display: block;
  color: var(--edgeiq-text-secondary);
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.eiq-form-v4-profile-tiles strong {
  display: block;
  margin-top: 4px;
  color: var(--edgeiq-text-primary);
  font-size: 14px;
}

.eiq-form-v4-profile-tiles small {
  display: block;
  min-height: 14px;
  margin-top: 2px;
  color: var(--edgeiq-text-secondary);
  font-size: 11px;
}

.eiq-form-v4-today-match {
  min-height: 100%;
}

.eiq-form-v4-today-match ul,
.eiq-form-v4-key-insights ul {
  list-style: none;
  padding: 0;
  margin: 10px 0 0;
  display: grid;
  gap: 8px;
}

.eiq-form-v4-today-match li {
  display: grid;
  gap: 2px;
  padding: 8px 0;
  border-bottom: 1px solid var(--edgeiq-border-soft);
}

.eiq-form-v4-today-match li:last-child {
  border-bottom: 0;
}

.eiq-form-v4-today-match li strong {
  color: var(--edgeiq-text-primary);
  font-size: 13px;
}

.eiq-form-v4-today-match li span {
  color: var(--edgeiq-primary);
  font-weight: 750;
}

.eiq-form-v4-today-match p {
  margin: 10px 0 0;
  color: var(--edgeiq-text-secondary);
}

.eiq-form-run-table--v4 th,
.eiq-form-run-table--v4 td {
  white-space: nowrap;
  font-size: 11px;
}

.eiq-form-run-table--v4 th:nth-child(2),
.eiq-form-run-table--v4 td:nth-child(2),
.eiq-form-run-table--v4 th:nth-child(6),
.eiq-form-run-table--v4 td:nth-child(6) {
  text-align: left;
}

.eiq-form-run-table--v4 td.is-negative {
  color: #047857 !important;
  background: #e8f8f0 !important;
  font-weight: 750;
}

.eiq-form-run-table--v4 td.is-positive {
  color: #b45309 !important;
  background: #fff7ed !important;
}

.eiq-form-v4-key-insights {
  margin-top: 0;
}

@media (max-width: 1180px) {
  .eiq-form-v4-runner-header,
  .eiq-form-v4-dossier-grid {
    grid-template-columns: 1fr;
  }

  .eiq-form-v4-current-strip,
  .eiq-form-v4-current-details {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Could not find block for {label}")
    return text.replace(old, new, 1)


def patch_normaliser() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts"
    text = read(path)
    text = replace_once(
        text,
        "  position: string;\n  raceClass: string;\n  margin: string;\n",
        "  position: string;\n  fieldSize: string;\n  positionInRunning: string;\n  raceClass: string;\n  margin: string;\n",
        "FormGuideRecentRun fields",
    )
    text = replace_once(
        text,
        """  return Number.isFinite(n) ? `${n}${suffix} of ${field}` : `${pos} of ${field}`;\n}""",
        """  return Number.isFinite(n) ? `${n}/${field}` : `${pos}/${field}`;\n}""",
        "position format",
    )
    text = replace_once(
        text,
        """  return enriched.fullForm.slice(0, 8).map((run) => ({\n    date: safeText(run.date),\n""",
        """  return enriched.fullForm.slice(0, 8).map((run) => {\n    const runRecord = run as EnrichedFormRun & Record<string, unknown>;\n    return {\n    date: safeText(run.date),\n""",
        "recent run map open",
    )
    text = replace_once(
        text,
        """    condition: safeText(run.condition),\n    position: formatPosition(run.position, run.fieldSize),\n    raceClass: safeText(run.class),\n""",
        """    condition: safeText(run.condition),\n    position: formatPosition(run.position, run.fieldSize),\n    fieldSize: safeText(run.fieldSize),\n    positionInRunning: safeText(firstValue(runRecord, [\"positionInRunning\", \"position_in_running\", \"inRunning\", \"in_running\", \"settlingPosition\", \"settling_position\"])),\n    raceClass: safeText(run.class),\n""",
        "recent run position fields",
    )
    text = replace_once(
        text,
        """    source: run.sectionalIndices ? "edgeiq_standardised_sectionals" : "edgeiq_form_guide_enriched_v2",\n  }));\n}""",
        """    source: run.sectionalIndices ? "edgeiq_standardised_sectionals" : "edgeiq_form_guide_enriched_v2",\n  };\n  });\n}""",
        "recent run map close",
    )
    write(path, text)


def patch_enriched_feed_contract() -> None:
    path = ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideEnrichedFeed.ts"
    text = read(path)
    text = replace_once(
        text,
        "  fieldSize: number | null;\n  barrier: number | null;\n",
        "  fieldSize: number | null;\n  positionInRunning?: string | null;\n  barrier: number | null;\n",
        "EnrichedFormRun optional positionInRunning",
    )
    write(path, text)


def patch_css() -> None:
    path = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"
    text = read(path)
    marker = "/* EDGEIQ FORM GUIDE FINAL SPEC V1 */"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n"
    write(path, text.rstrip() + CSS_BLOCK)


def main() -> None:
    files = [
        ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx",
        ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideNormaliser.ts",
        ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideEnrichedFeed.ts",
        ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css",
    ]
    for file in files:
        checkpoint(file)

    write(ROOT / "docs" / "full-product-implementation" / "EDGEIQ_FORM_GUIDE_TRACE_V1.md", TRACE.format(generated=datetime.now().isoformat(timespec="seconds")))
    write(ROOT / "src" / "edgeiq-os" / "race" / "services" / "formGuideWorkspaceViewModel.ts", VIEW_MODEL)
    write(ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx", COMPONENT)
    patch_normaliser()
    patch_enriched_feed_contract()
    patch_css()

    print(f"CHECKPOINT_DIR={CHECKPOINT_DIR}")
    print("EDGEIQ_FORM_GUIDE_FINAL_SPEC_V1_APPLIED")


if __name__ == "__main__":
    main()
