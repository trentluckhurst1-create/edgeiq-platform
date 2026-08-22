import { useEffect, useMemo, useState } from "react";
import { FieldWorkspace } from "./FieldWorkspace";
import { RaceIntelligenceWorkspace } from "./RaceIntelligenceWorkspace";
import { MapWorkspace } from "./MapWorkspace";
import { MarketWorkspace } from "./MarketWorkspace";
import { EpiWorkspaceWorkspace } from "./EpiWorkspaceWorkspace";
import { PerformanceWorkspace } from "./PerformanceWorkspace";
import { InsightsWorkspace } from "./InsightsWorkspace";
import { OverviewWorkspace } from "./OverviewWorkspace";
import { RaceFormGuideWorkspace } from "./RaceFormGuideWorkspace";
import { ReviewWorkspace } from "./ReviewWorkspace";
import { RaceResultsWorkspace } from "./RaceResultsWorkspace";
import type { ThreeDayRace } from "../services/threeDayCatalog";
import { canonicalRaceTitleDisplay, canonicalRailDisplay, canonicalTrackDisplayName, canonicalTrackRatingDisplay, canonicalWeatherDisplay } from "../../design-system/presentation";
import {
  normaliseFormGuideRace,
  type FormGuideRunnerDisplay,
} from "../services/formGuideNormaliser";
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
// MAP consolidation audit reference: ["FORM", "MAP", "MARKET", "OVERVIEW", "REVIEW"]
// Three-day routing audit: selected race field reaches Form Guide; RaceFormGuideWorkspace maps field.map internally.
export type RaceTab = typeof tabs[number];

const mountedComponentByRaceTab: Record<RaceTab, string> = {
  RACE: "RaceIntelligenceWorkspace",
  FIELD: "FieldWorkspace",
  "FORM GUIDE": "RaceFormGuideWorkspace",
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

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    let cancelled = false;
    loadFormGuideEnrichedFeed()
      .then((feed) => {
        if (!cancelled) setEnrichedRace(findEnrichedFormGuideRace(feed, raceBook, meetingRaces, selectedRaceKey));
      })
      .catch(() => {
        if (!cancelled) setEnrichedRace(null);
      });
    return () => {
      cancelled = true;
    };
  }, [raceBook, meetingRaces, selectedRaceKey]);

  const formGuide = useMemo(
    () => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace),
    [raceBook, field, meetingRaces, enrichedRace],
  );
  const activeTabClass = tab.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const headerValue = (value: any) => {
    const text = clean(value);
    if (!text || text === "-" || /^not supplied$/i.test(text) || /^unavailable$/i.test(text)) return "";
    if (/^race file$/i.test(text)) return "";
    return text;
  };
  const usefulHeaderValue = (value: any) => {
    const text = headerValue(value);
    if (!text) return "";
    if (text.length > 80) return "";
    if (/Set Weights|Apprentices|VOBIS|field limit|Track name:|Track type:|No sex restriction|No age restriction|Bonus/i.test(text)) return "";
    return text;
  };
  const firstHeaderValue = (...values: any[]) => values.map(usefulHeaderValue).find(Boolean) || "";
  const raceNumber = headerValue(official.raceNumber);
  const meetingName = canonicalTrackDisplayName(headerValue(official.meeting));
  const raceClass = firstHeaderValue(official.class, official.raceClass, official.benchmark, official.restrictions?.class);
  const distance = firstHeaderValue(official.distance);
  const trackCondition = canonicalTrackRatingDisplay(firstHeaderValue(official.trackCondition, official.condition), "");
  const rail = canonicalRailDisplay(firstHeaderValue(official.rail, official.railPosition), "");
  const weather = canonicalWeatherDisplay(firstHeaderValue(official.weather, official.weatherCondition), "");
  const raceDate = firstHeaderValue(official.date, official.raceDate);
  const raceTime = firstHeaderValue(official.time, official.localTime);
  const prizeMoney = firstHeaderValue(official.prizeMoney, official.totalPrizeMoney);
  const raceTitle = canonicalRaceTitleDisplay(headerValue(official.raceName) || headerValue(official.name));
  const showRaceFileHeader = tab !== "RACE";
  const raceHeaderMeta = [
    ["MEETING", meetingName],
    ["DATE", raceDate],
    ["TIME", raceTime],
    ["DISTANCE", distance],
    ["CLASS", raceClass],
    ["TRACK", trackCondition],
    ["RAIL", rail],
    ["WEATHER", weather],
    ["PRIZEMONEY", prizeMoney],
  ].filter((item) => item[1]);

  return (
    <section className={`eiq-race-workspace eiq-race-workspace--${activeTabClass}`} data-edgeiq-workspace-key={tab} data-edgeiq-mounted-component={mountedComponentByRaceTab[tab]}>
      {showRaceFileHeader ? (
        <header className="eiq-approved-racefile-header">
          <div className="eiq-approved-racefile-header__crumb">
            <button type="button" onClick={onBackToMeeting}>MEETINGS</button>
            <span>{meetingName}</span>
            <span>RACE {raceNumber}</span>
            <strong>{tab}</strong>
          </div>
          <div className="eiq-approved-racefile-header__title">
            <div>
              <h1>
                <span>Race {raceNumber}</span>
                {raceTitle ? <strong>{raceTitle}</strong> : null}
                {raceClass ? <em>{raceClass}</em> : null}
              </h1>
            </div>
            <button type="button" className="eiq-approved-button" onClick={onBackToMeeting}>Back to Races</button>
          </div>
          <dl className="eiq-approved-racefile-header__meta">
            {raceHeaderMeta.map(([label, value]) => (
              <div key={`${label}-${value}`}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </header>
      ) : null}

      <nav className="eiq-context-tabs" aria-label="Race workspace navigation">
        {tabs.map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>

      {tab === "RACE" ? (
        <RaceIntelligenceWorkspace
          raceBook={raceBook}
          field={field}
          formGuide={formGuide}
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingRaces={meetingRaces}
          clean={clean}
          onBackToMeeting={onBackToMeeting}
          onOpenRace={onOpenRace}
        />
      ) : tab === "FIELD" ? (
        <FieldWorkspace
          field={field}
          formGuide={formGuide}
          clean={clean}
          weight={weight}
          market={market}
          onOpenRunner={onOpenRunner}
        />
      ) : tab === "FORM GUIDE" ? (
        <RaceFormGuideWorkspace
          raceBook={raceBook}
          field={field}
          meetingRaces={meetingRaces}
          selectedRaceKey={selectedRaceKey}
          onOpenRace={onOpenRace}
        />
      ) : tab === "PERFORMANCE" ? (
        <PerformanceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />
      ) : tab === "MARKET" ? (
        <MarketWorkspace
          raceBook={raceBook}
          field={field}
          meetingKey={raceBook?.official?.meetingKey ?? null}
        />
      ) : tab === "MAP" ? (
        <MapWorkspace
          raceBook={raceBook}
          field={field}
          clean={clean}
          market={market}
          onOpenRunner={(runner) => {
            const sourceField = Array.isArray(field) ? field : [];

            const runnerIndex = sourceField.findIndex((candidate: any) => {
              if (candidate === runner) return true;

              const candidateNumber =
                candidate?.number ??
                candidate?.runnerNumber ??
                candidate?.saddlecloth ??
                candidate?.no;

              const runnerNumber =
                runner?.number ??
                runner?.runnerNumber ??
                runner?.saddlecloth ??
                runner?.no;

              if (
                candidateNumber !== undefined &&
                runnerNumber !== undefined &&
                String(candidateNumber) === String(runnerNumber)
              ) {
                return true;
              }

              const candidateName = String(
                candidate?.runner ??
                candidate?.runnerName ??
                candidate?.name ??
                "",
              )
                .trim()
                .toUpperCase();

              const runnerName = String(
                runner?.runner ??
                runner?.runnerName ??
                runner?.name ??
                "",
              )
                .trim()
                .toUpperCase();

              return Boolean(candidateName && candidateName === runnerName);
            });

            if (runnerIndex >= 0) {
              onOpenRunner(runnerIndex);
            }
          }}
        />
      ) : tab === "RESULTS" ? (
        <RaceResultsWorkspace
          raceBook={raceBook}
          field={field}
          clean={clean}
          market={market}
        />
      ) : tab === "REVIEW" ? (
        <ReviewWorkspace
          raceBook={raceBook}
          field={field}
          selectedRaceKey={clean(official.raceKey) || selectedRaceKey}
          clean={clean}
          onOpenTab={setTab}
        />
      ) : tab === "INSIGHTS" ? (
        <InsightsWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />
      ) : tab === "EPI" ? (
        <EpiWorkspaceWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
        />
      ) : (
        <OverviewWorkspace
          raceKey={clean(official.raceKey) || selectedRaceKey}
          meetingKey={clean(official.meetingKey)}
          raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`}
          field={field}
          onOpenTab={setTab}
        />
      )}
    </section>
  );
}
