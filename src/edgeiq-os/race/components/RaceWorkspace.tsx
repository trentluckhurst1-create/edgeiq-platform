import { useEffect, useMemo, useState } from "react";
import { FieldWorkspace } from "./FieldWorkspace";
import { RaceIntelligenceWorkspace } from "./RaceIntelligenceWorkspace";
import { MapWorkspace } from "./MapWorkspace";
import { MarketWorkspace } from "./MarketWorkspace";
import { EpiWorkspaceWorkspace } from "./EpiWorkspaceWorkspace";
import { PerformanceWorkspace } from "./PerformanceWorkspace";
import { InsightsWorkspace } from "./InsightsWorkspace";
import { OverviewWorkspace } from "./OverviewWorkspace";
import { FormCommandWorkspace } from "./FormCommandWorkspace";
import { ReviewWorkspace } from "./ReviewWorkspace";
import { RaceResultsWorkspace } from "./RaceResultsWorkspace";
import type { ThreeDayRace } from "../services/threeDayCatalog";
import {
  canonicalRaceTitleDisplay,
  canonicalRailDisplay,
  canonicalTrackDisplayName,
  canonicalTrackRatingDisplay,
  canonicalWeatherDisplay,
} from "../../design-system/presentation";
import { normaliseFormGuideRace } from "../services/formGuideNormaliser";
import {
  findEnrichedFormGuideRace,
  loadFormGuideEnrichedFeed,
  type EnrichedFormGuideRace,
} from "../services/formGuideEnrichedFeed";

type RaceWorkspaceProps = {
  raceBook: any;
  field: any[];
  selectedRunnerIndex: number;
  clean: (value: any) => string;
  weight: (value: any) => string;
  market: (value: any) => string;
  meetingRaces?: ThreeDayRace[];
  selectedRaceKey?: string;
  onBackToMeeting: () => void;
  onOpenRunner: (index: number) => void;
  onOpenRace?: (race: ThreeDayRace) => void;
  initialTab?: RaceTab;
};

const tabs = ["RACE", "FIELD", "FORM GUIDE", "PERFORMANCE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "EPI", "RESULTS", "REVIEW"] as const;
export type RaceTab = (typeof tabs)[number];

const mounted: Record<RaceTab, string> = {
  RACE: "RaceIntelligenceWorkspace",
  FIELD: "FieldWorkspace",
  "FORM GUIDE": "FormCommandWorkspace",
  PERFORMANCE: "PerformanceWorkspace",
  MAP: "MapWorkspace",
  MARKET: "MarketWorkspace",
  OVERVIEW: "OverviewWorkspace",
  INSIGHTS: "InsightsWorkspace",
  EPI: "EpiWorkspaceWorkspace",
  RESULTS: "RaceResultsWorkspace",
  REVIEW: "ReviewWorkspace",
};

export function RaceWorkspace({
  raceBook,
  field,
  clean,
  weight,
  market,
  meetingRaces = [],
  selectedRaceKey,
  onBackToMeeting,
  onOpenRunner,
  onOpenRace,
  initialTab = "RACE",
}: RaceWorkspaceProps) {
  const [tab, setTab] = useState<RaceTab>(initialTab);
  const [enrichedRace, setEnrichedRace] = useState<EnrichedFormGuideRace | null>(null);
  const official = raceBook?.official ?? {};

  useEffect(() => setTab(initialTab), [initialTab]);
  useEffect(() => {
    let cancelled = false;
    loadFormGuideEnrichedFeed()
      .then((feed) => {
        if (!cancelled) setEnrichedRace(findEnrichedFormGuideRace(feed, raceBook, meetingRaces, selectedRaceKey));
      })
      .catch(() => {
        if (!cancelled) setEnrichedRace(null);
      });
    return () => { cancelled = true; };
  }, [raceBook, meetingRaces, selectedRaceKey]);

  const formGuide = useMemo(
    () => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace),
    [raceBook, field, meetingRaces, enrichedRace],
  );

  const className = tab.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const healthy = (value: any) => {
    const text = clean(value);
    return !text || text === "-" || /^not supplied$|^unavailable$|^race file$/i.test(text) ? "" : text;
  };
  const useful = (value: any) => {
    const text = healthy(value);
    return !text || text.length > 80 || /Set Weights|Apprentices|VOBIS|field limit|Track name:|Track type:|No sex restriction|No age restriction|Bonus/i.test(text) ? "" : text;
  };
  const first = (...values: any[]) => values.map(useful).find(Boolean) || "";

  const raceNumber = healthy(official.raceNumber);
  const meetingName = canonicalTrackDisplayName(healthy(official.meeting));
  const raceClass = first(official.class, official.raceClass, official.benchmark, official.restrictions?.class);
  const distance = first(official.distance);
  const track = canonicalTrackRatingDisplay(first(official.trackCondition, official.condition), "");
  const rail = canonicalRailDisplay(first(official.rail, official.railPosition), "");
  const weather = canonicalWeatherDisplay(first(official.weather, official.weatherCondition), "");
  const date = first(official.date, official.raceDate);
  const time = first(official.time, official.localTime);
  const prize = first(official.prizeMoney, official.totalPrizeMoney);
  const title = canonicalRaceTitleDisplay(healthy(official.raceName) || healthy(official.name));
  const raceIdentity = [meetingName, raceNumber ? `Race ${raceNumber}` : "", title].filter(Boolean).join(" · ");
  const meta = [
    ["DATE", date], ["TIME", time], ["DISTANCE", distance], ["CLASS", raceClass],
    ["TRACK", track], ["RAIL", rail], ["WEATHER", weather], ["PRIZEMONEY", prize],
  ].filter((entry) => entry[1]);

  return (
    <section
      className={`eiq-race-workspace eiq-race-workspace--${className}`}
      data-edgeiq-workspace-key={tab}
      data-edgeiq-mounted-component={mounted[tab]}
    >
      <header className="eiq-race-locked__header">
        <div>
          <h1>Race</h1>
          <p>{raceIdentity || "Race analysis workspace"}</p>
        </div>
        <button type="button" className="eiq-race-locked__back" onClick={onBackToMeeting}>← Back to Meeting</button>
      </header>

      <section className="eiq-race-command-header" aria-label="Race context">
        <header>
          <div>
            <strong>{raceNumber ? `R${raceNumber}` : "R-"} {title || "Race"}</strong>
            <span>{meetingName || "Meeting"}</span>
          </div>
          {raceClass ? <b>{raceClass}</b> : null}
        </header>
        <dl>
          {meta.map(([label, value]) => (
            <div key={`${label}-${value}`}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>
      </section>

      <nav className="eiq-context-tabs" aria-label="Race analysis tabs">
        {tabs.map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item === "FORM GUIDE" ? "FORM" : item}
          </button>
        ))}
      </nav>

      <div className="eiq-tab-workarea">
        {tab === "RACE" ? (
          <RaceIntelligenceWorkspace raceBook={raceBook} field={field} formGuide={formGuide} raceKey={clean(official.raceKey) || selectedRaceKey} meetingRaces={meetingRaces} clean={clean} onBackToMeeting={onBackToMeeting} onOpenRace={onOpenRace} onOpenRunner={onOpenRunner} />
        ) : tab === "FIELD" ? (
          <FieldWorkspace field={field} formGuide={formGuide} clean={clean} weight={weight} market={market} onOpenRunner={onOpenRunner} />
        ) : tab === "FORM GUIDE" ? (
          <FormCommandWorkspace formGuide={formGuide} onOpenRunner={onOpenRunner} />
        ) : tab === "PERFORMANCE" ? (
          <PerformanceWorkspace raceKey={clean(official.raceKey) || selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field} />
        ) : tab === "MARKET" ? (
          <MarketWorkspace raceBook={raceBook} field={field} meetingKey={raceBook?.official?.meetingKey ?? null} />
        ) : tab === "MAP" ? (
          <MapWorkspace raceBook={raceBook} field={field} clean={clean} market={market} onOpenRunner={(runner) => {
            const index = field.findIndex((item: any) => item === runner || String(item?.official?.runner ?? item?.runner ?? item?.name ?? "").trim().toUpperCase() === String((runner as any)?.official?.runner ?? (runner as any)?.runner ?? (runner as any)?.name ?? "").trim().toUpperCase());
            if (index >= 0) onOpenRunner(index);
          }} />
        ) : tab === "OVERVIEW" ? (
          <OverviewWorkspace raceKey={clean(official.raceKey) || selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field} onOpenTab={setTab} />
        ) : tab === "INSIGHTS" ? (
          <InsightsWorkspace raceKey={clean(official.raceKey) || selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field} />
        ) : tab === "EPI" ? (
          <EpiWorkspaceWorkspace raceKey={clean(official.raceKey) || selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field} />
        ) : tab === "RESULTS" ? (
          <RaceResultsWorkspace raceBook={raceBook} field={field} clean={clean} market={market} />
        ) : (
          <ReviewWorkspace raceBook={raceBook} field={field} clean={clean} onOpenTab={setTab} />
        )}
      </div>
    </section>
  );
}
