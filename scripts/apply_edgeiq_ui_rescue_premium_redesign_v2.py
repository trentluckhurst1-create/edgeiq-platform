from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
RACE = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
SUMMARY = ROOT / "public" / "data" / "edgeiq_ui_rescue_premium_redesign_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_ui_rescue_premium_redesign_v1_report.txt"
text = RACE.read_text(encoding="utf-8")

def rng(start, end):
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"bad range {start} {end}")
    return start, end

home_start, meeting_start = rng(text.find('if (productView === "HOME") {'), text.find('if (productView === "MEETING") {'))
race_start = text.find('{intelMode === "COMMND" ? (() => {')
map_start = text.find('{intelMode === "MP" ? (() => {', race_start)
rng(race_start, map_start)
form_idx = text.find('intelMode === "FORM"')
form_start = text.rfind('{', 0, form_idx)
run_idx = text.find('intelMode === "RUNNERS"', form_idx)
run_start = text.rfind('{', 0, run_idx)
rng(form_start, run_start)
heat_start = text.find('<section className="edgeiq-product-heatmap edgeiq-product-card" aria-label="Ratings Intelligence Heat Map">')
heat_end = text.find('\n        {selected ? (', heat_start) if heat_start >= 0 else -1

new_home = '''if (productView === "HOME") {
 const primaryMeeting = todayShellMeetings[0] || productShellMeetings[0];
 const upcomingMeetings = upcomingShellMeetings.slice(0, 3);
 const meetingCard = (meeting: typeof productShellMeetings[number]) => (
 <article key={`premium-home-meeting-${meeting.meetingKey}`} className="edgeiq-premium-meeting-card"><div><strong>{meeting.trackName}</strong><span>{cleanMeetingDateLabel(meeting)} / {cleanTrackCondition(meeting.trackConditionLatest)} / {meeting.raceCount} races</span></div><button type="button" onClick={() => openShellMeeting(meeting.meetingKey)}>Open Meeting</button></article>
 );
 return <div className="edgeiq-premium-home edgeiq-product-home"><div className="edgeiq-premium-home-inner"><header className="edgeiq-premium-home-top"><strong>EDGEiQ</strong><span>Racing Intelligence Platform</span></header><main className="edgeiq-premium-home-hero"><section><span>EDGEiQ</span><h1>Adaptive Racing Intelligence.</h1><h2>Not tips. Not noise.</h2><p>EDGEiQ reads race shape, ratings, runner profiles and market context so the race can be assessed clearly before the field jumps.</p><button type="button" onClick={() => primaryMeeting ? openShellMeeting(primaryMeeting.meetingKey) : updateProductView("MEETING")}>Enter Terminal</button></section></main><section className="edgeiq-premium-meeting-section"><div className="edgeiq-premium-section-title">Today's Meetings</div>{primaryMeeting ? meetingCard(primaryMeeting) : <div className="edgeiq-product-empty">No meeting loaded.</div>}</section><section className="edgeiq-premium-meeting-section"><div className="edgeiq-premium-section-title">Upcoming Meetings</div><div className="edgeiq-premium-meeting-list">{upcomingMeetings.length ? upcomingMeetings.map((meeting) => meetingCard(meeting)) : <div className="edgeiq-product-empty">No upcoming meetings loaded.</div>}</div></section></div></div>;
 }

 '''
new_race = '''{intelMode === "COMMND" ? (() => {
 const raceRowsForTab = activeRaceRows.filter((item) => !isScratched(item));
 const raceFieldSize = raceRowsForTab.length || activeRaceRows.length;
 const raceStandardValue = activeRaceRows.map((item) => firstNum(item.ratingsHeatmap, ["expected_rating"])).find((value) => value !== null) ?? null;
 const runnerRatings = activeRaceRows.map((item) => firstNum(item.ratingsHeatmap, ["runner_rating"])).filter((value): value is number => value !== null);
 const ratingSpread = runnerRatings.length ? Math.max(...runnerRatings) - Math.min(...runnerRatings) : null;
 const raceShapeText = displayExpectedTempo !== "-" ? displayExpectedTempo : fallbackTempoLabel !== "-" ? fallbackTempoLabel : "Balanced";
 const raceStrengthText = ratingSpread === null ? "Unclear" : ratingSpread >= 12 ? "Deep" : ratingSpread >= 7 ? "Competitive" : "Even";
 const confidenceText = bettingConfidence !== "-" ? bettingConfidence : raceFieldSize >= 8 ? "Medium" : "Low";
 const narrativeText = (raceStory || customerBriefingNarrative || briefingNarrative || "This race is best read through the expected standard, likely shape and strength of the field.").split(/(?<=[.!?])\\s+/).slice(0, 1).join(" ");
 const raceCards = [{ label: "Race Standard", value: raceStandardValue === null ? "-" : renderMetricValue(raceStandardValue, 1), detail: "Expected figure" }, { label: "Race Shape", value: raceShapeText, detail: `${raceFieldSize} runners` }, { label: "Race Strength", value: raceStrengthText, detail: ratingSpread === null ? "Rating spread unavailable" : `${renderMetricValue(ratingSpread, 1)} point spread` }, { label: "Confidence", value: confidenceText, detail: "Pre-race read" }];
 return <section className="edgeiq-race-premium-workspace edgeiq-product-section edgeiq-race-simple"><div className="edgeiq-race-simple-hero"><span>{header ? `${track(header)} R${raceNo(header)}` : futureMeetingSelectedRace}</span><strong>{header ? `${distance(header)} ${raceClass(header)}` : futureMeetingSelectedMeta || "Race"}</strong><em>{header ? `${trackCondition(header)} / ${raceFieldSize} Runners` : `${futureMeetingFieldCount} Runners`}</em></div><div className="edgeiq-race-simple-grid">{raceCards.map((card) => <article key={`race-simple-${card.label}`} className="edgeiq-race-simple-card"><span>{card.label}</span><strong>{card.value}</strong><em>{card.detail}</em></article>)}</div><section className="edgeiq-race-simple-narrative"><span>Intelligence Narrative</span><p>{narrativeText}</p></section></section>;
 })() : null}
 '''
new_form = '''{intelMode === "FORM" ? (() => {
 if (!selected) return <p style={narrativeInsetStyle}>Select a runner to inspect form.</p>;
 const formRows = lastFiveRuns.slice(0, 5);
 const projected = selectedTodayProjectionFigure;
 const expected = selected.ratingsHeatmap ? firstNum(selected.ratingsHeatmap, ["expected_rating"]) : null;
 const gap = selected.ratingsHeatmap ? firstNum(selected.ratingsHeatmap, ["rating_gap"]) : null;
 const price = selectedIsScratched ? "-" : money(limitedAdjustedPrice(selected) ?? fairPrice(selected.row, selected.bet));
 const sparkValues = [selectedLastStartRatingValue, selectedAVGRatingLast5Value, selectedBestRatingLast5Value, projected].filter((value): value is number => value !== null);
 const sparkMax = Math.max(70, ...sparkValues, expected ?? 0);
 const trendText = selectedTrendRead && selectedTrendRead !== "-" ? selectedTrendRead : ratingTrendText || "Steady";
 const formNarrative = selectedIsContextOnly ? "Context only; detailed rated-history lines are not available for this runner." : selectedFormVerdict.split(/(?<=[.!?])\\s+/).slice(0, 1).join(" ");
 const summaryRows = [["Current", projected === null ? "-" : renderMetricValue(projected, 1)], ["Peak", selectedBestRatingLast5], ["AVG5", selectedAVGRatingLast5], ["Trend", trendText], ["Expected", expected === null ? "-" : renderMetricValue(expected, 1)], ["Price", price]];
 return <section className="edgeiq-form-showcase edgeiq-product-section"><div className="edgeiq-form-showcase-hero"><div><span>FORM</span><strong>{horse(selected.row)}</strong><em>No {saddle(selected.row) === 999 ? "-" : saddle(selected.row)} / Barrier {firstText(selected.row, ["barrier", "draw"], "-")}</em></div><div className="edgeiq-form-hero-metrics"><article><span>Projected Rating</span><strong>{projected === null ? "-" : renderMetricValue(projected, 1)}</strong></article><article><span>Expected / Gap</span><strong>{expected === null ? "-" : `${renderMetricValue(expected, 1)} / ${gap === null ? "-" : signed(gap, 1)}`}</strong></article><article><span>Race Rank</span><strong>{selected.modelRank ? `#${selected.modelRank}` : "-"}</strong></article><article><span>Price</span><strong>{price}</strong></article></div></div><div className="edgeiq-form-rating-strip">{[["Last", selectedLastStartRatingValue], ["Current", projected], ["AVG5", selectedAVGRatingLast5Value], ["Peak", selectedBestRatingLast5Value]].map(([label, value]) => { const ratingValue = typeof value === "number" ? value : null; const width = ratingValue === null ? 0 : Math.max(4, Math.min(100, (ratingValue / sparkMax) * 100)); return <article key={`form-rating-strip-${label}`}><span>{label}</span><div><i style={{ width: `${width}%`, background: ratingValue !== null && expected !== null && ratingValue >= expected ? "#34d399" : ratingValue !== null && expected !== null && ratingValue <= expected - 5 ? "#f87171" : "#e5e7eb" }} /></div><strong>{ratingValue === null ? "-" : renderMetricValue(ratingValue, 1)}</strong></article>; })}</div><div className="edgeiq-form-showcase-main"><section className="edgeiq-form-last-five"><div className="edgeiq-form-table-title">Last Five Runs</div><div className="edgeiq-form-table"><div className="edgeiq-form-table-row head">{['Date','Track','Distance','Class','Pos','SP','Rating','Settled'].map((label) => <span key={`form-main-head-${label}`}>{label}</span>)}</div>{selectedIsContextOnly ? <div className="edgeiq-form-table-empty">No detailed rated-history lines available.</div> : formRows.map((run) => <div key={`form-main-row-${run.n}`} className="edgeiq-form-table-row"><span>{run.date || "-"}</span><span>{run.trk || "-"}</span><span>{run.dist ? `${String(run.dist).replace(".0", "")}m` : "-"}</span><span>{run.cls || "-"}</span><span className={String(run.pos || "").startsWith("1") ? "pos-good" : Number(run.pos) >= 7 ? "pos-bad" : ""}>{run.pos || "-"}</span><span>{run.sp || "-"}</span><span>{run.rating !== null ? renderMetricValue(run.rating, 1) : "-"}</span><span>{firstText(run.raw, ["settled_position", "settling_position", "settled", "in_run"], "-")}</span></div>)}</div></section><aside className="edgeiq-form-summary-panel">{summaryRows.map(([label, value]) => <article key={`form-summary-${label}`}><span>{label}</span><strong>{value}</strong></article>)}<p>{formNarrative}</p></aside></div></section>;
 })() : null}

 '''
new_heat = '''<section className="edgeiq-product-heatmap edgeiq-product-card" aria-label="Ratings Intelligence Heat Map"><div className="edgeiq-product-heatmap-head"><div><span>RATINGS INTELLIGENCE HEAT MAP</span><strong>How well each runner sits against today's expected race standard.</strong></div></div>{activeRaceRows.some((item) => item.ratingsHeatmap) ? (() => { const heatRows = activeRaceRows.flatMap((item) => item.ratingsHeatmap ? [{ item, heat: item.ratingsHeatmap }] : []); const expectedRaceRating = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).find((value) => value !== null) ?? null; return <><div className="edgeiq-heatmap-standard-card"><span>Expected Race Standard</span><strong>{expectedRaceRating === null ? "-" : renderMetricValue(expectedRaceRating, 1)}</strong></div><div className="edgeiq-product-table edgeiq-product-heatmap-table simple" role="table" aria-label="Ratings intelligence heat map table"><div className="edgeiq-product-table-row edgeiq-product-table-head" role="row">{['Horse','Rating','Gap'].map((label) => <span key={`heat-simple-head-${label}`} role="columnheader">{label}</span>)}</div>{heatRows.map(({ item, heat }) => { const rating = firstNum(heat, ["runner_rating"]); const gap = firstNum(heat, ["rating_gap"]); const gapClass = gap === null ? "neutral" : gap >= 5 ? "positive" : gap <= -5 ? "negative" : "neutral"; return <div className="edgeiq-product-table-row" role="row" key={`ratings-heat-${runnerRowKey(item.row)}`}><strong role="cell">{horse(item.row)}</strong><span role="cell">{rating === null ? "-" : renderMetricValue(rating, 1)}</span><span role="cell" className={gapClass}>{gap === null ? "-" : signed(gap, 1)}</span></div>; })}</div></>; })() : <div className="edgeiq-product-empty">Ratings heatmap unavailable for this race.</div>}</section>
'''

replacements = []
if heat_start >= 0 and heat_end > heat_start:
    replacements.append((heat_start, heat_end, new_heat))
replacements += [(form_start, run_start, new_form), (race_start, map_start, new_race), (home_start, meeting_start, new_home)]
for start, end, repl in sorted(replacements, reverse=True):
    text = text[:start] + repl + text[end:]

for old, new in {
    'label: "RCE"': 'label: "RACE"', 'label: "MP"': 'label: "MAP"', 'label: "MRKET"': 'label: "MARKET"',
    'LEDERS': 'LEADERS', 'ON PCE': 'ON PACE', 'BCKMRKERS': 'BACKMARKERS', 'NEGTIVE': 'NEGATIVE',
    'RTINGS': 'RATINGS', 'HET MP': 'HEAT MAP', 'TODY': 'TODAY', 'RCING INTELLIGENCE PLTFORM': 'RACING INTELLIGENCE PLATFORM',
    'daptive racing intelligence': 'Adaptive racing intelligence', 'NOT LODED': 'NOT LOADED', 'SOURCE GP': 'SOURCE GAP',
    'vg L5': 'AVG5', 'selectedvgRatingLast5': 'selectedAVGRatingLast5', 'selectedvgRatingLast5Value': 'selectedAVGRatingLast5Value',
    'const aAVG5': 'const avg5', 'aAVG5,': 'avg5,', 'aAVG5Rating': 'avg5Rating', 'aAVG5HoverCard': 'avg5HoverCard',
    'buildverageHoverCard': 'buildAverageHoverCard', 'verage last 5': 'Average last 5', 'MRGIN': 'MARGIN', 'CLSS': 'CLASS',
    'TRCK': 'TRACK', 'DTE': 'DATE', 'RTING': 'RATING', 'DT QULITY': 'DATA QUALITY', 'FORM STTUS': 'FORM STATUS',
    'ge/Sex': 'Age/Sex', 'Setup dvantage': 'Setup Advantage', 'FIR PRICE': 'FAIR PRICE', 'TB PRICE': 'TAB PRICE',
    'SETUP GP': 'SETUP GAP', 'MRKET RED': 'MARKET READ', 'CHNCE': 'CHANCE', 'RNK': 'RANK', 'WTCH': 'WATCH',
    'NO SIGNL': 'NO SIGNAL', 'PRTIL': 'PARTIAL', 'HISTORICL': 'HISTORICAL', 'TCTICL': 'TACTICAL', 'MODERTE': 'MODERATE',
    'NEUTRL': 'NEUTRAL', 'Leder': 'Leader', 'LEDER': 'LEADER', 'limiteddjustedPrice': 'limitedAdjustedPrice', 'racessessmentNarrative': 'raceAssessmentNarrative'
}.items():
    text = text.replace(old, new)
RACE.write_text(text, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
if 'EDGEiQ UI Rescue + Premium Redesign V1' not in css:
    css += '''

/* EDGEiQ UI Rescue + Premium Redesign V1 */
.edgeiq-premium-home { min-height: 100vh; background: radial-gradient(circle at 22% 0%, rgba(255,255,255,.08), transparent 28rem), #050b14; color: #f8fafc; padding: 24px; }
.edgeiq-premium-home-inner { max-width: 1320px; margin: 0 auto; display: grid; gap: 22px; }
.edgeiq-premium-home-top { display: flex; justify-content: space-between; align-items: center; padding: 18px 0; border-bottom: 1px solid rgba(148,163,184,.18); }
.edgeiq-premium-home-top strong { font-size: 30px; letter-spacing: .02em; }
.edgeiq-premium-home-top span { color: #9ca3af; font-size: 11px; font-weight: 900; letter-spacing: .22em; text-transform: uppercase; }
.edgeiq-premium-home-hero { min-height: 410px; display: grid; align-items: center; border: 1px solid rgba(148,163,184,.18); border-radius: 24px; padding: clamp(28px, 6vw, 78px); background: linear-gradient(145deg, rgba(15,23,42,.84), rgba(5,11,20,.96)); box-shadow: 0 24px 70px rgba(0,0,0,.32); }
.edgeiq-premium-home-hero section { max-width: 760px; display: grid; gap: 14px; }
.edgeiq-premium-home-hero span { color: #d1d5db; font-size: 12px; font-weight: 1000; letter-spacing: .24em; text-transform: uppercase; }
.edgeiq-premium-home-hero h1 { margin: 0; color: #fff; font-size: clamp(44px, 8vw, 88px); line-height: .92; letter-spacing: -.05em; }
.edgeiq-premium-home-hero h2 { margin: 0; color: #e5e7eb; font-size: clamp(22px, 3vw, 34px); line-height: 1.12; }
.edgeiq-premium-home-hero p { margin: 0; max-width: 620px; color: #aeb8c5; font-size: 16px; line-height: 1.55; }
.edgeiq-premium-home-hero button, .edgeiq-premium-meeting-card button { width: fit-content; min-height: 46px; border-radius: 999px; border: 1px solid rgba(229,231,235,.35); background: rgba(255,255,255,.05); color: #fff; padding: 0 22px; font-size: 12px; font-weight: 1000; letter-spacing: .12em; text-transform: uppercase; cursor: pointer; }
.edgeiq-premium-section-title { color: #f8fafc; font-size: 13px; font-weight: 1000; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 12px; }
.edgeiq-premium-meeting-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.edgeiq-premium-meeting-card { display: flex; justify-content: space-between; gap: 16px; align-items: center; border: 1px solid rgba(148,163,184,.18); border-radius: 18px; padding: 18px; background: rgba(15,23,42,.68); }
.edgeiq-premium-meeting-card div { display: grid; gap: 5px; }
.edgeiq-premium-meeting-card strong { color: #fff; font-size: 22px; }
.edgeiq-premium-meeting-card span { color: #aeb8c5; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; }
.edgeiq-race-simple { display: grid; gap: 16px; }
.edgeiq-race-simple-hero { border: 1px solid rgba(148,163,184,.20); border-radius: 22px; padding: 24px; background: linear-gradient(145deg, rgba(15,23,42,.86), rgba(3,7,18,.92)); display: grid; gap: 7px; }
.edgeiq-race-simple-hero span { color: #f8fafc; font-size: 34px; font-weight: 1000; letter-spacing: -.02em; }
.edgeiq-race-simple-hero strong { color: #e5e7eb; font-size: 16px; font-weight: 900; text-transform: uppercase; letter-spacing: .08em; }
.edgeiq-race-simple-hero em { color: #9ca3af; font-style: normal; font-size: 13px; font-weight: 850; text-transform: uppercase; }
.edgeiq-race-simple-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.edgeiq-race-simple-card, .edgeiq-race-simple-narrative { border: 1px solid rgba(148,163,184,.18); border-radius: 18px; padding: 18px; background: rgba(15,23,42,.66); }
.edgeiq-race-simple-card span, .edgeiq-race-simple-narrative span { color: #9ca3af; font-size: 10px; font-weight: 1000; letter-spacing: .16em; text-transform: uppercase; }
.edgeiq-race-simple-card strong { display: block; color: #fff; font-size: 24px; margin: 8px 0 4px; }
.edgeiq-race-simple-card em { color: #aeb8c5; font-size: 12px; font-style: normal; }
.edgeiq-race-simple-narrative p { margin: 10px 0 0; color: #d1d5db; font-size: 15px; line-height: 1.55; max-width: 980px; }
.edgeiq-form-showcase { display: grid; gap: 14px; }
.edgeiq-form-showcase-hero { display: grid; grid-template-columns: minmax(0,1fr) minmax(520px,1.15fr); gap: 16px; border: 1px solid rgba(148,163,184,.20); border-radius: 22px; padding: 20px; background: linear-gradient(145deg, rgba(15,23,42,.90), rgba(3,7,18,.88)); }
.edgeiq-form-showcase-hero > div:first-child { display: grid; gap: 6px; }
.edgeiq-form-showcase-hero span { color: #9ca3af; font-size: 10px; font-weight: 1000; letter-spacing: .18em; text-transform: uppercase; }
.edgeiq-form-showcase-hero strong { color: #fff; font-size: 32px; line-height: 1; }
.edgeiq-form-showcase-hero em { color: #aeb8c5; font-size: 12px; font-style: normal; }
.edgeiq-form-hero-metrics { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }
.edgeiq-form-hero-metrics article, .edgeiq-form-summary-panel article { border: 1px solid rgba(148,163,184,.16); border-radius: 14px; padding: 12px; background: rgba(255,255,255,.035); }
.edgeiq-form-hero-metrics strong, .edgeiq-form-summary-panel strong { color: #fff; font-size: 18px; }
.edgeiq-form-rating-strip { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }
.edgeiq-form-rating-strip article { border: 1px solid rgba(148,163,184,.16); border-radius: 16px; padding: 12px; background: rgba(15,23,42,.58); display: grid; gap: 8px; }
.edgeiq-form-rating-strip div { height: 8px; border-radius: 999px; background: rgba(148,163,184,.18); overflow: hidden; }
.edgeiq-form-rating-strip i { display: block; height: 100%; border-radius: inherit; }
.edgeiq-form-rating-strip strong { color: #fff; font-size: 16px; }
.edgeiq-form-showcase-main { display: grid; grid-template-columns: minmax(0,1fr) 260px; gap: 14px; }
.edgeiq-form-last-five, .edgeiq-form-summary-panel { border: 1px solid rgba(148,163,184,.18); border-radius: 18px; background: rgba(15,23,42,.62); overflow: hidden; }
.edgeiq-form-table-title { padding: 14px; color: #fff; font-size: 13px; font-weight: 1000; letter-spacing: .16em; text-transform: uppercase; border-bottom: 1px solid rgba(148,163,184,.16); }
.edgeiq-form-table { overflow-x: auto; }
.edgeiq-form-table-row { min-width: 920px; display: grid; grid-template-columns: 100px 120px 90px 160px 64px 90px 90px 120px; border-bottom: 1px solid rgba(148,163,184,.12); }
.edgeiq-form-table-row span { padding: 10px 12px; color: #d1d5db; font-size: 12px; border-right: 1px solid rgba(148,163,184,.08); }
.edgeiq-form-table-row.head span { color: #9ca3af; font-size: 10px; font-weight: 1000; text-transform: uppercase; letter-spacing: .12em; background: rgba(3,7,18,.52); }
.edgeiq-form-table-row .pos-good, .edgeiq-product-heatmap-table .positive { color: #34d399; font-weight: 1000; }
.edgeiq-form-table-row .pos-bad, .edgeiq-product-heatmap-table .negative { color: #f87171; font-weight: 1000; }
.edgeiq-form-table-empty { padding: 18px; color: #9ca3af; }
.edgeiq-form-summary-panel { padding: 14px; display: grid; gap: 10px; align-content: start; }
.edgeiq-form-summary-panel p { margin: 4px 0 0; color: #d1d5db; font-size: 12px; line-height: 1.5; }
.edgeiq-heatmap-standard-card { border: 1px solid rgba(148,163,184,.16); border-radius: 16px; padding: 14px; background: rgba(15,23,42,.62); width: fit-content; min-width: 220px; }
.edgeiq-heatmap-standard-card span { display: block; color: #9ca3af; font-size: 10px; font-weight: 1000; letter-spacing: .14em; text-transform: uppercase; }
.edgeiq-heatmap-standard-card strong { display: block; color: #fff; font-size: 28px; margin-top: 4px; }
.edgeiq-product-heatmap-table.simple .edgeiq-product-table-row { grid-template-columns: minmax(180px, 1fr) 120px 120px; min-width: 520px; }
.edgeiq-product-heatmap-table .neutral { color: #e5e7eb; }
@media (max-width: 980px) { .edgeiq-premium-meeting-list, .edgeiq-race-simple-grid, .edgeiq-form-rating-strip { grid-template-columns: 1fr; } .edgeiq-form-showcase-hero, .edgeiq-form-showcase-main { grid-template-columns: 1fr; } }
'''
    CSS.write_text(css, encoding="utf-8")
SUMMARY.write_text("metric,value\nstatus,APPLIED\nfiles_changed,src/components/RaceIntelligenceScreen.tsx;src/styles/edgeiqProductTerminalV1.css\n", encoding="utf-8")
REPORT.write_text("EDGEIQ_UI_RESCUE_PREMIUM_REDESIGN_V1 applied. Home, RACE, FORM and INSIGHTS heatmap content simplified/productised.\n", encoding="utf-8")
print('premium_redesign_applied')

