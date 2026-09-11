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
import { normaliseFormGuideRace } from "../services/formGuideNormaliser";
import { findEnrichedFormGuideRace, loadFormGuideEnrichedFeed, type EnrichedFormGuideRace } from "../services/formGuideEnrichedFeed";

type RaceWorkspaceProps = { raceBook:any; field:any[]; selectedRunnerIndex:number; clean:(value:any)=>string; weight:(value:any)=>string; market:(value:any)=>string; meetingRaces?:ThreeDayRace[]; selectedRaceKey?:string; onBackToMeeting:()=>void; onOpenRunner:(index:number)=>void; onOpenRace?:(race:ThreeDayRace)=>void; initialTab?:RaceTab };

const tabs = ["RACE","FIELD","FORM GUIDE","PERFORMANCE","MAP","MARKET","OVERVIEW","INSIGHTS","EPI","RESULTS","REVIEW"] as const;
export type RaceTab = typeof tabs[number];

const tabDesign: Record<RaceTab,{title:string; mission:string; outputs:string[]}> = {
  RACE:{title:"Race Command",mission:"The decision screen: race conditions, shape, pressure, leading ratings and the complete runner board.",outputs:["Race Shape","What Matters","Top Ratings","Runner Board"]},
  FIELD:{title:"Declared Field",mission:"Official runner administration with barriers, weights, riders, trainers, status and rapid recent-form expansion.",outputs:["Declarations","Barrier / Weight","Connections","Last 5"]},
  "FORM GUIDE":{title:"Professional Form",mission:"Deep runner-by-runner form analysis. Compare historical performance with today's race and expose suitability and trajectory.",outputs:["Last 5","EPI / ERI","Suitability","Fair Price"]},
  PERFORMANCE:{title:"Performance Matrix",mission:"Compare repeatable performance across recent starts and inspect the context behind every historical rating.",outputs:["Run Ratings","History Matrix","Benchmark","Run Detail"]},
  MAP:{title:"Speed Map",mission:"Visualise where the field is expected to settle, the pressure profile and which runners gain or lose from race shape.",outputs:["Early Position","Pressure","Barriers","Map Advantage"]},
  MARKET:{title:"Pricing & Market",mission:"Put EDGEiQ fair prices beside the observed market and surface actionable mispricing without hiding feed freshness.",outputs:["Fair Price","Market","Edge","Movement"]},
  OVERVIEW:{title:"Analyst Overview",mission:"One-screen synthesis of the race environment, field intelligence, map, ratings and the questions that need answering.",outputs:["Environment","Field Read","Map Read","Key Questions"]},
  INSIGHTS:{title:"Hidden Angles",mission:"Surface governed signals that are easy to miss in conventional form: preparation, intent, conditions and campaign context.",outputs:["Stable Intent","Prep Stage","Conditions","Evidence"]},
  EPI:{title:"EPI Ratings",mission:"Rank the field on EDGEiQ Performance Index and interrogate the historical evidence and benchmark behind each figure.",outputs:["Current EPI","Field Rank","Trend","Evidence"]},
  RESULTS:{title:"Race Results",mission:"Official finishing order and result context for closing the race-day workflow.",outputs:["Finish","Margins","SP","Result Status"]},
  REVIEW:{title:"Post-Race Review",mission:"Audit what happened against the pre-race view and preserve the evidence needed to improve future analysis.",outputs:["Expected vs Actual","Map Review","Price Review","Lessons"]},
};

const mountedComponentByRaceTab:Record<RaceTab,string>={RACE:"RaceIntelligenceWorkspace",FIELD:"FieldWorkspace","FORM GUIDE":"RaceFormGuideWorkspace",PERFORMANCE:"PerformanceWorkspace",MAP:"MapWorkspace",MARKET:"MarketWorkspace",OVERVIEW:"OverviewWorkspace",INSIGHTS:"InsightsWorkspace",EPI:"EpiWorkspaceWorkspace",RESULTS:"RaceResultsWorkspace",REVIEW:"ReviewWorkspace"};

export function RaceWorkspace({raceBook,field,clean,weight,market,meetingRaces=[],selectedRaceKey,onBackToMeeting,onOpenRunner,onOpenRace,initialTab="RACE"}:RaceWorkspaceProps){
 const [tab,setTab]=useState<RaceTab>(initialTab); const [enrichedRace,setEnrichedRace]=useState<EnrichedFormGuideRace|null>(null); const official=raceBook?.official??{};
 useEffect(()=>setTab(initialTab),[initialTab]);
 useEffect(()=>{let cancelled=false;loadFormGuideEnrichedFeed().then(feed=>{if(!cancelled)setEnrichedRace(findEnrichedFormGuideRace(feed,raceBook,meetingRaces,selectedRaceKey));}).catch(()=>{if(!cancelled)setEnrichedRace(null);});return()=>{cancelled=true};},[raceBook,meetingRaces,selectedRaceKey]);
 const formGuide=useMemo(()=>normaliseFormGuideRace(raceBook,field,meetingRaces,enrichedRace),[raceBook,field,meetingRaces,enrichedRace]);
 const activeTabClass=tab.toLowerCase().replace(/[^a-z0-9]+/g,"-");
 const headerValue=(value:any)=>{const t=clean(value);if(!t||t==="-"||/^not supplied$/i.test(t)||/^unavailable$/i.test(t)||/^race file$/i.test(t))return "";return t};
 const useful=(value:any)=>{const t=headerValue(value);if(!t||t.length>80||/Set Weights|Apprentices|VOBIS|field limit|Track name:|Track type:|No sex restriction|No age restriction|Bonus/i.test(t))return "";return t};
 const first=(...values:any[])=>values.map(useful).find(Boolean)||"";
 const raceNumber=headerValue(official.raceNumber), meetingName=canonicalTrackDisplayName(headerValue(official.meeting));
 const raceClass=first(official.class,official.raceClass,official.benchmark,official.restrictions?.class),distance=first(official.distance),trackCondition=canonicalTrackRatingDisplay(first(official.trackCondition,official.condition),""),rail=canonicalRailDisplay(first(official.rail,official.railPosition),""),weather=canonicalWeatherDisplay(first(official.weather,official.weatherCondition),""),raceDate=first(official.date,official.raceDate),raceTime=first(official.time,official.localTime),prizeMoney=first(official.prizeMoney,official.totalPrizeMoney),raceTitle=canonicalRaceTitleDisplay(headerValue(official.raceName)||headerValue(official.name));
 const meta=[["MEETING",meetingName],["DATE",raceDate],["TIME",raceTime],["DISTANCE",distance],["CLASS",raceClass],["TRACK",trackCondition],["RAIL",rail],["WEATHER",weather],["PRIZEMONEY",prizeMoney]].filter(x=>x[1]); const design=tabDesign[tab];
 return <section className={`eiq-race-workspace eiq-race-workspace--${activeTabClass}`} data-edgeiq-workspace-key={tab} data-edgeiq-mounted-component={mountedComponentByRaceTab[tab]}>
  <header className="eiq-race-command-header">
   <div className="eiq-race-command-header__top"><div><button type="button" onClick={onBackToMeeting}>MEETINGS</button><span>/</span><b>{meetingName||"MEETING"}</b><span>/</span><b>R{raceNumber||"-"}</b></div><div><strong>{raceTitle||`Race ${raceNumber}`}</strong>{raceClass?<span>{raceClass}</span>:null}</div></div>
   <dl>{meta.map(([label,value])=><div key={`${label}-${value}`}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
  </header>
  <nav className="eiq-context-tabs" aria-label="Race workspace navigation">{tabs.map(item=><button key={item} type="button" className={tab===item?"is-active":""} onClick={()=>setTab(item)}>{item==="FORM GUIDE"?"FORM":item}</button>)}</nav>
  <section className="eiq-tab-mission"><div><span>{tab}</span><h2>{design.title}</h2><p>{design.mission}</p></div><dl>{design.outputs.map((output,index)=><div key={output}><dt>{String(index+1).padStart(2,"0")}</dt><dd>{output}</dd></div>)}</dl></section>
  <div className="eiq-tab-workarea">
  {tab==="RACE"?<RaceIntelligenceWorkspace raceBook={raceBook} field={field} formGuide={formGuide} raceKey={clean(official.raceKey)||selectedRaceKey} meetingRaces={meetingRaces} clean={clean} onBackToMeeting={onBackToMeeting} onOpenRace={onOpenRace}/>
  :tab==="FIELD"?<FieldWorkspace field={field} formGuide={formGuide} clean={clean} weight={weight} market={market} onOpenRunner={onOpenRunner}/>
  :tab==="FORM GUIDE"?<RaceFormGuideWorkspace raceBook={raceBook} field={field} meetingRaces={meetingRaces} selectedRaceKey={selectedRaceKey} onOpenRace={onOpenRace}/>
  :tab==="PERFORMANCE"?<PerformanceWorkspace raceKey={clean(official.raceKey)||selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field}/>
  :tab==="MARKET"?<MarketWorkspace raceBook={raceBook} field={field} meetingKey={raceBook?.official?.meetingKey??null}/>
  :tab==="MAP"?<MapWorkspace raceBook={raceBook} field={field} clean={clean} market={market} onOpenRunner={(runner)=>{const i=(Array.isArray(field)?field:[]).findIndex((candidate:any)=>candidate===runner||String(candidate?.official?.runner??candidate?.runner??candidate?.name??"").trim().toUpperCase()===String((runner as any)?.official?.runner??(runner as any)?.runner??(runner as any)?.name??"").trim().toUpperCase());if(i>=0)onOpenRunner(i)}}/>
  :tab==="OVERVIEW"?<OverviewWorkspace raceKey={clean(official.raceKey)||selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field} onOpenTab={setTab}/>
  :tab==="INSIGHTS"?<InsightsWorkspace raceKey={clean(official.raceKey)||selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field}/>
  :tab==="EPI"?<EpiWorkspaceWorkspace raceKey={clean(official.raceKey)||selectedRaceKey} meetingKey={clean(official.meetingKey)} raceLabel={`${clean(official.meeting)} R${clean(official.raceNumber)}`} field={field}/>
  :tab==="RESULTS"?<RaceResultsWorkspace raceBook={raceBook} field={field}/>
  :<ReviewWorkspace raceBook={raceBook} field={field}/>} </div>
 </section>;
}
