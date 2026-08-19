import React from "react";
import { getTrackMapSlug } from "../utils/trackMaps";

type MeetingsScreenProps = {
  productShellMeetings: any[];
  productShellRaces: any[];
  selectedShellMeeting: any;
  selectedShellMeetingRaces: any[];
  runnerRows: any[];
  shellTrack: any;
  shellRaceNo: any;
  pageStyle: React.CSSProperties;
  intelModeTabs: any[];
  updateProductView: (view: any) => void;
  openShellMeeting: (meetingKey: any) => void;
  openShellRace: (race: any) => void;
  setShellMeetingKey: (meetingKey: any) => void;
  setIntelMode: (mode: any) => void;
};

export function MeetingsScreen({
  productShellMeetings,
  productShellRaces,
  selectedShellMeeting,
  selectedShellMeetingRaces,
  runnerRows,
  shellTrack,
  shellRaceNo,
  pageStyle,
  intelModeTabs,
  updateProductView,
  openShellMeeting,
  openShellRace,
  setShellMeetingKey,
  setIntelMode,
}: MeetingsScreenProps) {

 const dayOrder = ["TODAY", "TOMORROW", "DAY+2"];
 const displayMeetingValue = (value: unknown) => { const raw = String(value ?? "").trim(); return raw && raw !== "-" ? raw : "-"; };
 const meetingRaceCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count} races` : "Race list pending"; };
 const raceFieldCountLabel = (value: unknown) => { const count = Number(value); return Number.isFinite(count) && count > 0 ? `${count}` : "Fields pending"; };
 const meetingRowsToday = productShellMeetings.filter((meeting) => meeting.dayLabel === "TODAY");
 const meetingRowsTomorrow = productShellMeetings.filter((meeting) => meeting.dayLabel === "TOMORROW");
 const allMeetingRows = productShellMeetings.length ? productShellMeetings : meetingRowsToday;
 const selectedMeetingTrack = selectedShellMeeting?.trackName || "Meeting";
 const meetingRaceRows = (meetingKey: string) => productShellRaces.filter((race) => String(race.meetingKey || "") === String(meetingKey || ""));
 const meetingRunnerCount = (meetingKey: string) => meetingRaceRows(meetingKey).reduce((sum, race) => sum + (Number(race.fieldSize) || 0), 0);
 const stateFromMeeting = (meeting: any) => String(meeting.state || meeting.region || meeting.stateCode || "VIC").toUpperCase().trim() || "VIC";
 const currentState = "VIC";
 const stateSummary = ["VIC", "NSW", "QLD", "WA", "SA", "TAS", "NT"].map((state) => ({ state, count: allMeetingRows.filter((meeting) => stateFromMeeting(meeting) === state).length }));
 const firstRaceOfDay = productShellRaces.map((race) => String(race.raceTime || "").trim()).filter(Boolean).sort()[0] || allMeetingRows[0]?.firstRaceTime || "Pending";
 const lastRaceOfDay = productShellRaces.map((race) => String(race.raceTime || "").trim()).filter(Boolean).sort().slice(-1)[0] || allMeetingRows[0]?.lastRaceTime || "Pending";
 const formatMeetingDateLong = (value: string) => {
  const parsed = value ? new Date(`${value}T12:00:00`) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return displayMeetingValue(value);
  return parsed.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
 };
 const getMeetingSlug = (trackName: string) => {
  const clean = String(trackName || "").toUpperCase().trim();
  const aliases: Record<string, string> = {
   "BALLARAT SYNTHETIC": "ballarat_synthetic",
   "PAKENHAM SYNTHETIC": "pakenham_synthetic",
   "PAKENHAM / TYNONG": "pakenham_tynong",
   "PAKENHAM TYNONG": "pakenham_tynong",
   "GEELONG SYNTHETIC": "geelong_synthetic",
   "GEELONG TURF": "geelong_turf",
   "MOONEE VALLEY": "moonee_valley",
   "YARRA VALLEY": "yarra_valley",
   "STONY CREEK": "stony_creek",
   "SWAN HILL": "swan_hill",
   "GREAT WESTERN": "great_western",
   "MT WYCHEPROOF": "mt_wycheproof",
   "ST ARNAUD": "st_arnaud",
  };
  return aliases[clean] || clean.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
 };
 const renderMeetingMap = (meeting: typeof productShellMeetings[number] | null) => {
  const slug = getTrackMapSlug(meeting?.trackName || "");
  const source = meeting?.mapAvailable && meeting.mapFile ? meeting.mapFile : `/assets/tracks/thumbs/${slug}.png`;
  return <div className="edgeiq-meetings-pro-map-thumb"><img src={source} alt={`${meeting?.trackName || "Track"} track map`} loading="lazy" onError={(event) => { event.currentTarget.style.display = "none"; }} /></div>;
 };
 const meetingsTopbar = (
  <div className="edgeiq-home-final-top edgeiq-meetings-pro-top">
   <button type="button" className="edgeiq-home-final-brand" onClick={() => updateProductView("HOME")}>
    <span className="edgeiq-home-final-mark"></span>
    <span><strong>EDGE<span>iQ</span></strong><em>ADAPTIVE RACING INTELLIGENCE</em></span>
   </button>
   <nav className="edgeiq-home-final-nav" aria-label="Meetings navigation">
    {["HOME", "MEETINGS", "RACE", "FIELD", "PERFORMANCE", "FORM", "MAP", "LAB", "STATS", "MARKET", "RESULTS", "CONDITIONS"].map((item) => (
     <button key={`meetings-pro-nav-${item}`} type="button" className={item === "MEETINGS" ? "is-active" : ""} disabled={item !== "HOME" && item !== "MEETINGS" && (!shellTrack || !shellRaceNo)} onClick={() => { if (item === "HOME") updateProductView("HOME"); else if (item === "MEETINGS") updateProductView("MEETINGS"); else { const tab = intelModeTabs.find((entry) => entry.label === item); if (tab) setIntelMode(tab.mode); updateProductView("RCE"); } }}>{item}</button>
    ))}
   </nav>
   <div className="edgeiq-home-final-terminal"><span>TERMINAL</span><i /><strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong></div>
  </div>
 );
 const meetingsDateLabel = formatMeetingDateLong(allMeetingRows[0]?.meetingDate || new Date().toISOString().slice(0, 10));
 const todayStats = [
  ["Meetings", String(allMeetingRows.length || 0)],
  ["Races", String(productShellRaces.length || 0)],
  ["Runners", String(runnerRows.length || 0)],
  ["First Race", firstRaceOfDay],
  ["Last Race", lastRaceOfDay],
 ];
 if (selectedShellMeeting) {
  const meetingFacts = [
   ["Track", displayMeetingValue(selectedShellMeeting.trackConditionLatest)],
   ["Rail", displayMeetingValue(selectedShellMeeting.railPositionLatest)],
   ["Weather", displayMeetingValue(selectedShellMeeting.weather)],
   ["Wind", [displayMeetingValue(selectedShellMeeting.windDirection), displayMeetingValue(selectedShellMeeting.windSpeed)].filter((v) => v !== "-").join(" ") || "-"],
   ["Rainfall", `24h ${displayMeetingValue(selectedShellMeeting.rainfall24h)} / 7d ${displayMeetingValue(selectedShellMeeting.rainfall7d)}`],
   ["Irrigation", `24h ${displayMeetingValue(selectedShellMeeting.irrigation24h)} / 7d ${displayMeetingValue(selectedShellMeeting.irrigation7d)}`],
  ];
  const selectedRows = selectedShellMeetingRaces;
  return (
   <div className="edgeiq-meetings-pro edgeiq-product-surface" style={pageStyle}>
    {meetingsTopbar}
    <div className="edgeiq-meetings-pro-shell">
     <aside className="edgeiq-meetings-pro-sidebar">
      <strong>{selectedMeetingTrack}</strong>
      <span>{formatMeetingDateLong(selectedShellMeeting.meetingDate || "")}</span>
      <em>{meetingRaceCountLabel(selectedRows.length || selectedShellMeeting.raceCount)}</em>
      <button type="button" className="is-active" onClick={() => setShellMeetingKey("")}><- All Meetings</button>
      <div className="edgeiq-meetings-pro-info">
       {meetingFacts.slice(0, 4).map(([label, value]) => <div key={`selected-meeting-side-${label}`}><span>{label}</span><b>{value}</b></div>)}
      </div>
      <button type="button" className="edgeiq-meetings-pro-pin">Pin Meeting</button>
     </aside>
     <main className="edgeiq-meetings-pro-main">
      <section className="edgeiq-meetings-pro-hero selected">
       <div>
        <span>MEETING CONTROL</span>
        <h1>{selectedMeetingTrack}</h1>
        <p>{meetingRaceCountLabel(selectedRows.length || selectedShellMeeting.raceCount)}  /  First {displayMeetingValue(selectedShellMeeting.firstRaceTime)}  /  Last {displayMeetingValue(selectedShellMeeting.lastRaceTime)}</p>
       </div>
       <div className="edgeiq-meetings-pro-hero-map">{renderMeetingMap(selectedShellMeeting)}</div>
      </section>
      <section className="edgeiq-meetings-pro-selected-grid">
       <div className="edgeiq-meetings-pro-card large">
        <div className="edgeiq-meetings-pro-section-head"><span>Race List</span><strong>{meetingRaceCountLabel(selectedRows.length || selectedShellMeeting.raceCount)}</strong></div>
        <div className="edgeiq-meetings-pro-race-table">
         <div className="head"><span>Race</span><span>Time</span><span>Distance</span><span>Class</span><span>Field</span><span>Condition</span><span>Status</span><span /></div>
         {selectedRows.length ? selectedRows.map((race) => <div key={`meeting-selected-race-${race.raceKey}`}><strong>R{race.raceNoValue}</strong><span>{displayMeetingValue(race.raceTime)}</span><span>{displayMeetingValue(race.distanceValue)}</span><span>{displayMeetingValue(race.raceClassValue)}</span><span>{raceFieldCountLabel(race.fieldSize)}</span><span>{displayMeetingValue(race.trackConditionValue)}</span><span>{race.fieldSize > 0 ? "Fields Ready" : "Fields Pending"}</span><button type="button" disabled={race.fieldSize <= 0} onClick={() => openShellRace(race)}>{race.fieldSize > 0 ? "Open Race" : "Pending"}</button></div>) : <p>No race rows loaded for this meeting yet.</p>}
        </div>
       </div>
       <div className="edgeiq-meetings-pro-card">
        <div className="edgeiq-meetings-pro-section-head"><span>Meeting Intelligence</span></div>
        <div className="edgeiq-meetings-pro-facts">{meetingFacts.map(([label, value]) => <article key={`selected-meeting-fact-${label}`}><span>{label}</span><strong>{value}</strong></article>)}</div>
       </div>
      </section>
     </main>
    </div>
    <footer className="edgeiq-home-final-footer">EDGEiQ - ADAPTIVE RACING INTELLIGENCE / NOT TIPS. NOT NOISE. JUST CONTEXT.</footer>
   </div>
  );
 }
 return (
  <div className="edgeiq-meetings-pro edgeiq-product-surface" style={pageStyle}>
   {meetingsTopbar}
   <div className="edgeiq-meetings-pro-shell">
    <aside className="edgeiq-meetings-pro-sidebar">
     <strong>MEETINGS</strong>
     <span>Racing Calendar</span>
     <p>Select a meeting to explore races, fields, performance and intelligence.</p>
     {["Today", "Tomorrow", "Day +2", "All Calendar", "Custom Filter"].map((label, index) => <button type="button" className={index === 0 ? "is-active" : ""} key={`meetings-pro-filter-${label}`}>{label}</button>)}
     <b>Filter by State</b>
     {stateSummary.map(({ state, count }) => <em key={`meetings-pro-state-${state}`}><span>{state === "VIC" ? "Victoria" : state}</span><i>{count || "-"}</i></em>)}
     <button type="button" className="edgeiq-meetings-pro-data">Data Info</button>
    </aside>
    <main className="edgeiq-meetings-pro-main">
     <section className="edgeiq-meetings-pro-titlebar">
      <div><span>MEETINGS</span><h1>Today's Meetings</h1><p>{meetingsDateLabel}</p></div>
      <div className="edgeiq-meetings-pro-actions"><button type="button">View Full Calendar</button><button type="button"><</button><button type="button">></button></div>
     </section>
     <section className="edgeiq-meetings-pro-stats">{todayStats.map(([label, value]) => <article key={`meetings-pro-stat-${label}`}><span>{label}</span><strong>{value}</strong></article>)}</section>
     <section className="edgeiq-meetings-pro-cards">
      {meetingRowsToday.slice(0, 6).map((meeting) => {
       const rows = meetingRaceRows(meeting.meetingKey);
       const runners = meetingRunnerCount(meeting.meetingKey);
       return <article key={`meetings-pro-card-${meeting.meetingKey}`} className={meeting.trackName.toUpperCase().includes("FLEMINGTON") ? "is-active" : ""}>
        <div className="edgeiq-meetings-pro-card-head"><span>{stateFromMeeting(meeting)}</span><em>{meetingRaceCountLabel(meeting.raceCount)}</em></div>
        <div className="edgeiq-meetings-pro-card-body"><div><strong>{meeting.trackName}</strong><p>{formatMeetingDateLong(meeting.meetingDate || "")}</p><small>{displayMeetingValue(meeting.trackConditionLatest)} <i /> Rail {displayMeetingValue(meeting.railPositionLatest)}</small></div>{renderMeetingMap(meeting)}</div>
        <section><span>First Race <b>{displayMeetingValue(meeting.firstRaceTime)}</b></span><span>Last Race <b>{displayMeetingValue(meeting.lastRaceTime)}</b></span></section>
        <section><span>Races <b>{rows.length || meeting.raceCount || "-"}</b></span><span>Runners <b>{runners || "-"}</b></span></section>
        <div className="edgeiq-meetings-pro-track-rating"><span>EDGEiQ Track Rating</span><strong>{displayMeetingValue(meeting.trackConditionLatest)}</strong></div>
        <button type="button" onClick={() => openShellMeeting(meeting.meetingKey)}>View Meeting -></button>
       </article>;
      })}
     </section>
     <section className="edgeiq-meetings-pro-lower">
      <div className="edgeiq-meetings-pro-card large">
       <div className="edgeiq-meetings-pro-section-head"><span>Race Calendar</span><strong>{currentState}</strong><div><button type="button" className="is-active">By Time</button><button type="button">By Track</button></div></div>
       <div className="edgeiq-meetings-pro-calendar-table">
        <div className="head"><span>Time</span><span>Track</span><span>Race</span><span>Distance</span><span>Class</span><span>Condition</span><span>Rail</span></div>
        {productShellRaces.slice(0, 12).map((race) => <button type="button" key={`meetings-pro-race-${race.raceKey}`} onClick={() => openShellRace(race)}><span>{displayMeetingValue(race.raceTime)}</span><strong>{race.trackName}</strong><em>R{race.raceNoValue}</em><em>{displayMeetingValue(race.distanceValue)}</em><em>{displayMeetingValue(race.raceClassValue)}</em><b>{displayMeetingValue(race.trackConditionValue)}</b><em>{displayMeetingValue(race.railValue)}</em></button>)}
       </div>
      </div>
      <div className="edgeiq-meetings-pro-card track-card">
       <div className="edgeiq-meetings-pro-section-head"><span>Track Map</span><strong>{meetingRowsToday[0]?.trackName || "Selected Meeting"}</strong></div>
       {renderMeetingMap(meetingRowsToday[0] || null)}
       <p>Track information, rail context and race shape intelligence populate from the meeting feed.</p>
       <button type="button">Track Information -></button>
      </div>
     </section>
    </main>
    <aside className="edgeiq-meetings-pro-right">
     <section><strong>Meeting Summary</strong>{todayStats.map(([label, value]) => <div key={`meetings-pro-summary-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
     <section><strong>Data Coverage</strong>{[["Racing Data", "25 Years"], ["Results Accuracy", "99.8%"], ["Speed Coverage", "99.7%"], ["Updated", "Daily"]].map(([label, value]) => <div key={`meetings-pro-data-${label}`}><span>{label}</span><em>{value}</em></div>)}</section>
    </aside>
   </div>
   <footer className="edgeiq-home-final-footer">EDGEiQ - ADAPTIVE RACING INTELLIGENCE / NOT TIPS. NOT NOISE. JUST CONTEXT.</footer>
  </div>
 );

}
