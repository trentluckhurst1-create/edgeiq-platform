import React from "react";
import { getTrackMapSlug } from "../utils/trackMaps";

type HomeScreenProps = {
  productShellMeetings: any[];
  updateProductView: (view: any) => void;
  shellTrack: any;
  shellRaceNo: any;
  setIntelMode: (mode: any) => void;
  openShellMeeting: (meetingKey: any) => void;
};

export function HomeScreen({
  productShellMeetings,
  updateProductView,
  shellTrack,
  shellRaceNo,
  setIntelMode,
  openShellMeeting,
}: HomeScreenProps) {

const homeMeetingsByState = (() => {
 const groups: Record<string, typeof productShellMeetings> = {};
 productShellMeetings.slice(0, 18).forEach((meeting) => {
  const rawState = String((meeting as any).state || (meeting as any).region || (meeting as any).stateCode || "VIC").toUpperCase().trim() || "VIC";
  if (!groups[rawState]) groups[rawState] = [];
  groups[rawState].push(meeting);
 });
 return Object.entries(groups).slice(0, 5);
})();
const todayMeetings = productShellMeetings.filter((meeting) => meeting.dayLabel === "TODAY").slice(0, 8);
const homeDataStats = [
 { label: "MEETINGS", value: "9,393", note: "historical meetings indexed" },
 { label: "RACES", value: "77,732", note: "race records available" },
 { label: "RUNS", value: "931,245", note: "runner results in warehouse" },
 { label: "SPEED", value: "99.7%", note: "speed coverage recovered" },
];
const homeModules = [
 { title: "RACE", copy: "Race intelligence, shape, standard and key context." },
 { title: "FIELD", copy: "Runner list, weights, riders, barriers and status." },
 { title: "PERFORMANCE", copy: "EPI, current figures, peaks, trends and heatmaps." },
 { title: "FORM", copy: "Gear, previous runs, benchmark sectionals and profile." },
 { title: "MAP", copy: "Barrier lanes, start matrix and race shape." },
 { title: "LAB", copy: "Scenario modelling, price engine and research." },
 { title: "MARKET", copy: "Firming, drifting, overlays and market interpretation." },
 { title: "RESULTS", copy: "Results, EDGEiQ Standard and race analysis." },
 { title: "CONDITIONS", copy: "Official rating, EDGEiQ rating, rail, weather and bias." },
];
const openHomeModule = (title: string) => {
 if (title === "RACE") { updateProductView("MEETINGS"); return; }
 if (title === "FIELD") { setIntelMode("RUNNERS"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "PERFORMANCE") { setIntelMode("PERFORMANCE"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "FORM") { setIntelMode("FORM"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "MAP") { setIntelMode("MP"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "LAB") { setIntelMode("NEXUS"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "MARKET") { setIntelMode("DVNCED"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "RESULTS") { setIntelMode("RESULTS"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 if (title === "CONDITIONS") { setIntelMode("WEATHER"); updateProductView(shellTrack && shellRaceNo ? "RCE" : "MEETINGS"); return; }
 updateProductView("MEETINGS");
};
return (
<div className="edgeiq-home-final edgeiq-product-v5">
<header className="edgeiq-home-final-top">
<button type="button" className="edgeiq-home-final-brand" onClick={() => updateProductView("HOME")}>
<span className="edgeiq-home-final-mark"></span>
<span><strong>EDGE<span>iQ</span></strong><em>ADAPTIVE RACING INTELLIGENCE</em></span>
</button>
<nav className="edgeiq-home-final-nav" aria-label="EDGEiQ product navigation">
{["HOME", "MEETINGS", "RACE", "FIELD", "PERFORMANCE", "FORM", "MAP", "LAB", "STATS", "MARKET", "RESULTS", "CONDITIONS"].map((item) => (
<button type="button" key={`home-final-nav-${item}`} className={item === "HOME" ? "is-active" : ""} onClick={() => { if (item === "HOME") updateProductView("HOME"); else if (item === "MEETINGS") updateProductView("MEETINGS"); else openHomeModule(item); }}>{item}</button>
))}
</nav>
<div className="edgeiq-home-final-terminal"><span>TERMINAL</span><i /><strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong></div>
</header>
<main className="edgeiq-home-final-shell">
<section className="edgeiq-home-final-hero">
<div className="edgeiq-home-final-copy">
<span className="edgeiq-home-final-kicker">ADAPTIVE RACING INTELLIGENCE</span>
<h1>Intelligence isn't more data.<br />It's better interpretation.</h1>
<p>EDGEiQ exists to bridge the gap between information and intelligence. Every rating, benchmark, profile and model is built to answer one question: <strong>what does the evidence actually mean?</strong></p>
<div className="edgeiq-home-final-cta"><button type="button" onClick={() => updateProductView("MEETINGS")}>OPEN MEETINGS</button><span>We don't tip. We interpret.</span></div>
</div>
<aside className="edgeiq-home-final-mission">
<strong>MODERN RACING HAS NO SHORTAGE OF INFORMATION.</strong>
<p>What it lacks is interpretation. EDGEiQ transforms racing data into clear, explainable intelligence for people who think for themselves.</p>
<ul>
<li>Evidence-based intelligence.</li><li>No tips. No bias. No agendas.</li><li>Every race. Every runner. Every detail.</li>
</ul>
</aside>
</section>
<section className="edgeiq-home-final-dataflow">
{[["DATA", "Results, markets, sectionals, weather, gear, ratings and profiles."], ["INTERPRETATION", "Standard times, true track rating, race shape, market behaviour and context."], ["INTELLIGENCE", "Confidence, risk, probability, pricing research and decision support."]].map(([label, copy], index) => <article key={`home-dataflow-${label}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{label}</strong><p>{copy}</p></article>)}
</section>
<section className="edgeiq-home-final-grid">
<div className="edgeiq-home-final-panel edgeiq-home-final-meetings">
<div className="edgeiq-home-final-head edgeiq-home-final-meetings-head"><div><span>MEETINGS</span><em>VICTORIA</em></div><button type="button" onClick={() => updateProductView("MEETINGS")}>VIEW ALL -></button></div>
{homeMeetingsByState.length ? homeMeetingsByState.map(([state, meetings]) => <div className="edgeiq-home-final-state" key={`home-state-${state}`}><h3>{state}</h3><div>{meetings.slice(0, 4).map((meeting) => <button type="button" key={`home-final-meeting-${meeting.meetingKey}`} onClick={() => openShellMeeting(meeting.meetingKey)}><div className="edgeiq-home-final-track-thumb"><img src={`/assets/tracks/thumbs/${getTrackMapSlug(meeting.trackName)}.png`} alt={`${meeting.trackName} track map`} onError={(event) => { event.currentTarget.style.display = "none"; }} /></div><div className="edgeiq-home-final-meeting-copy"><strong>{meeting.trackName}</strong><span>{meeting.raceCount ? `${meeting.raceCount} races` : "Race list pending"}</span><em>First {meeting.firstRaceTime || "-"}  /  Last {meeting.lastRaceTime || "-"}</em></div></button>)}</div></div>) : <div className="edgeiq-home-final-empty">No meetings loaded for today.</div>}
</div>
<div className="edgeiq-home-final-panel edgeiq-home-final-modules">
<div className="edgeiq-home-final-head"><span>WHAT EDGEiQ DOES</span></div>
<div className="edgeiq-home-final-module-grid">{homeModules.map((module) => <button type="button" key={`home-module-${module.title}`} onClick={() => openHomeModule(module.title)}><strong>{module.title}</strong><span>{module.copy}</span></button>)}</div>
</div>
</section>
<section className="edgeiq-home-final-stats">
{homeDataStats.map((stat) => <article key={`home-stat-${stat.label}`}><span>{stat.label}</span><strong>{stat.value}</strong><em>{stat.note}</em></article>)}
</section>
<section className="edgeiq-home-final-bottom"><strong>Information tells you what happened.</strong><span>Intelligence explains why it matters.</span></section>
</main>
<footer className="edgeiq-home-final-footer">EDGEiQ - ADAPTIVE RACING INTELLIGENCE / NOT TIPS. NOT NOISE. JUST CONTEXT.</footer>
</div>
);

}
