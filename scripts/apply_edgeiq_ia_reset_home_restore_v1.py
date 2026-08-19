from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
RACE = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CSS = ROOT / "src" / "styles" / "edgeiqProductTerminalV1.css"
SUMMARY = ROOT / "public" / "data" / "edgeiq_ia_reset_home_restore_v1_summary.csv"
REPORT = ROOT / "public" / "data" / "edgeiq_ia_reset_home_restore_v1_report.txt"
text = RACE.read_text(encoding="utf-8")

def replace_range(s, start, end, repl):
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"bad range {start} {end}")
    return s[:start] + repl + s[end:]

# Type and visible nav order.
text = text.replace('type IntelMode = "COMMND" | "MP" | "FORM" | "RUNNERS" | "FCTORS" | "DVNCED" | "RESULTS";',
                    'type IntelMode = "COMMND" | "RUNNERS" | "RATINGS" | "FORM" | "MP" | "CONNECTIONS" | "DVNCED" | "RESULTS";')
nav_start = text.find('const intelModeTabs: Array<{ mode: IntelMode; label: string; hint: string }> = [')
nav_end = text.find(' ];', nav_start)
if nav_start < 0 or nav_end < 0:
    raise SystemExit('nav block not found')
new_nav = '''const intelModeTabs: Array<{ mode: IntelMode; label: string; hint: string }> = [
 { mode: "COMMND", label: "RACE", hint: "Race overview" },
 { mode: "RUNNERS", label: "FIELD", hint: "Race field" },
 { mode: "RATINGS", label: "RATINGS", hint: "Ratings heat map" },
 { mode: "FORM", label: "FORM", hint: "Form study" },
 { mode: "MP", label: "MAP", hint: "Speed map" },
 { mode: "CONNECTIONS", label: "CONNECTIONS", hint: "Trainer and jockey" },
 { mode: "DVNCED", label: "MARKET", hint: "Price comparison" },
 { mode: "RESULTS", label: "RESULTS", hint: "Post-race" },
'''
text = replace_range(text, nav_start, nav_end, new_nav)

# Home block restore with fuller clean layout.
home_start = text.find('if (productView === "HOME") {')
meeting_start = text.find('if (productView === "MEETING") {', home_start)
new_home = '''if (productView === "HOME") {
 const primaryMeeting = todayShellMeetings[0] || productShellMeetings[0];
 const upcomingMeetings = upcomingShellMeetings.slice(0, 3);
 const homeStatements = [
 { title: "Race shape", text: "Understand tempo, pressure and how the field is likely to organise." },
 { title: "Ratings intelligence", text: "Compare each runner against today's expected race standard." },
 { title: "Market and runner context", text: "Read price, profile and field context without turning the screen into noise." },
 ];
 const meetingCard = (meeting: typeof productShellMeetings[number]) => (
 <article key={`premium-home-meeting-${meeting.meetingKey}`} className="edgeiq-premium-meeting-card">
 <div><strong>{meeting.trackName}</strong><span>{meeting.dayLabel} / {meeting.trackConditionLatest} / {meeting.raceCount} races</span></div>
 <button type="button" onClick={() => openShellMeeting(meeting.meetingKey)}>Open Meeting</button>
 </article>
 );
 return (
 <div className="edgeiq-premium-home edgeiq-product-home edgeiq-home-restored">
 <div className="edgeiq-premium-home-inner">
 <header className="edgeiq-premium-home-top"><strong>EDGEiQ</strong><span>Racing Intelligence Platform</span></header>
 <main className="edgeiq-home-restored-grid">
 <section className="edgeiq-premium-home-hero edgeiq-home-restored-hero">
 <span>EDGEiQ</span>
 <h1>Adaptive Racing Intelligence.</h1>
 <h2>Not tips. Not noise.</h2>
 <p>EDGEiQ organises race shape, ratings, form, map, connections and market context into a single race-reading workspace.</p>
 <button type="button" onClick={() => primaryMeeting ? openShellMeeting(primaryMeeting.meetingKey) : updateProductView("MEETING")}>Enter Terminal</button>
 </section>
 <aside className="edgeiq-home-statement-panel">
 {homeStatements.map((item) => <article key={`home-statement-${item.title}`}><strong>{item.title}</strong><p>{item.text}</p></article>)}
 </aside>
 </main>
 <section className="edgeiq-home-meetings-grid">
 <div><div className="edgeiq-premium-section-title">Today's Meetings</div>{primaryMeeting ? meetingCard(primaryMeeting) : <div className="edgeiq-product-empty">No meeting loaded.</div>}</div>
 <div><div className="edgeiq-premium-section-title">Upcoming Meetings</div><div className="edgeiq-premium-meeting-list">{upcomingMeetings.length ? upcomingMeetings.map((meeting) => meetingCard(meeting)) : <div className="edgeiq-product-empty">No upcoming meetings loaded.</div>}</div></div>
 </section>
 </div>
 </div>
 );
 }

 '''
text = replace_range(text, home_start, meeting_start, new_home)

# Field block: race field only.
field_start = text.find('{intelMode === "RUNNERS" ? (')
ratings_old_start = text.find('{intelMode === "FCTORS" ? (', field_start)
if field_start < 0 or ratings_old_start < 0:
    raise SystemExit('field or old insights block not found')
new_field = '''{intelMode === "RUNNERS" ? (() => {
 const fieldRows = activeRaceRows;
 const cleanMarket = (item: EnrichedRunner) => {
 const value = money(livePrice(item.row, item.bet));
 return value && value !== "-" ? value : "Awaiting Feed";
 };
 return (
 <section className="edgeiq-field-tab edgeiq-product-section">
 <div className="edgeiq-tab-heading"><span>FIELD</span><strong>Race field</strong></div>
 <div className="edgeiq-field-table edgeiq-product-table" role="table" aria-label="Race field table">
 <div className="edgeiq-field-table-row head" role="row">{['No','Horse','Barrier','Weight','Jockey','Trainer','Market','Status'].map((label) => <span key={`field-head-${label}`}>{label}</span>)}</div>
 {fieldRows.map((item) => {
 const row = item.row;
 const scratched = isScratched(item);
 const status = scratched ? "SCRATCHED" : firstText(row, ["runner_status", "scratch_status", "ui_status"], "ACTIVE").replace(/_/g, " ");
 return <button key={`field-row-${runnerRowKey(row)}`} type="button" className={`edgeiq-field-table-row ${runnerRowKey(row) === selectedKey ? "is-selected" : ""}`} onClick={() => setSelectedKey(runnerRowKey(row))} role="row"><span>{saddle(row) === 999 ? "-" : saddle(row)}</span><strong>{horse(row)}</strong><span>{barrier(row)}</span><span>{firstText(row, ["weight", "weight_carried", "allocated_weight"], "-")}</span><span>{firstText(row, ["jockey", "jockey_name", "rider"], "-")}</span><span>{firstText(row, ["trainer", "trainer_name"], "-")}</span><span>{cleanMarket(item)}</span><span>{status}</span></button>;
 })}
 </div>
 </section>
 );
 })() : null}

 '''
text = replace_range(text, field_start, ratings_old_start, new_field)

# Ratings block replaces old FCTORS block before selected runner drawer.
ratings_start = text.find('{intelMode === "FCTORS" ? (')
selected_drawer_start = text.find('{selected && intelMode === "RUNNERS" ? (', ratings_start)
if ratings_start < 0 or selected_drawer_start < 0:
    raise SystemExit('ratings block range not found')
new_ratings = '''{intelMode === "RATINGS" ? (() => {
 const heatRows = activeRaceRows.flatMap((item) => item.ratingsHeatmap ? [{ item, heat: item.ratingsHeatmap }] : []);
 const expectedRaceRating = heatRows.map((entry) => firstNum(entry.heat, ["expected_rating"])).find((value) => value !== null) ?? null;
 const runnerRatings = heatRows.map((entry) => firstNum(entry.heat, ["runner_rating"])).filter((value): value is number => value !== null).sort((a, b) => a - b);
 const fieldMedian = runnerRatings.length ? runnerRatings[Math.floor(runnerRatings.length / 2)] : null;
 const ratingSpread = runnerRatings.length ? Math.max(...runnerRatings) - Math.min(...runnerRatings) : null;
 const strength = ratingSpread === null ? "-" : ratingSpread >= 12 ? "Deep" : ratingSpread >= 7 ? "Competitive" : "Even";
 return (
 <section className="edgeiq-ratings-tab edgeiq-product-section">
 <div className="edgeiq-ratings-hero"><span>Expected Race Standard</span><strong>{expectedRaceRating === null ? "-" : renderMetricValue(expectedRaceRating, 1)}</strong></div>
 <div className="edgeiq-ratings-summary-grid"><article><span>Field Median</span><strong>{fieldMedian === null ? "-" : renderMetricValue(fieldMedian, 1)}</strong></article><article><span>Race Strength</span><strong>{strength}</strong></article><article><span>Rating Spread</span><strong>{ratingSpread === null ? "-" : renderMetricValue(ratingSpread, 1)}</strong></article></div>
 <div className="edgeiq-ratings-heat-table edgeiq-product-table" role="table" aria-label="Ratings heat map"><div className="edgeiq-ratings-heat-row head" role="row">{['Horse','Rating','Gap'].map((label) => <span key={`ratings-head-${label}`}>{label}</span>)}</div>{heatRows.map(({ item, heat }) => { const rating = firstNum(heat, ["runner_rating"]); const gap = firstNum(heat, ["rating_gap"]); const gapClass = gap === null ? "neutral" : gap >= 5 ? "positive" : gap <= -5 ? "negative" : "neutral"; return <div className="edgeiq-ratings-heat-row" role="row" key={`ratings-tab-${runnerRowKey(item.row)}`}><strong>{horse(item.row)}</strong><span>{rating === null ? "-" : renderMetricValue(rating, 1)}</span><span className={gapClass}>{gap === null ? "-" : signed(gap, 1)}</span></div>; })}</div>
 </section>
 );
 })() : null}

 '''
text = replace_range(text, ratings_start, selected_drawer_start, new_ratings)

# Hide supporting drawer on FIELD to keep main field clean.
text = text.replace('{selected && intelMode === "RUNNERS" ? (', '{false && selected && intelMode === "RUNNERS" ? (', 1)

# Connections block inserted before Market.
market_start = text.find('{intelMode === "DVNCED" ? (() => {')
if market_start < 0:
    raise SystemExit('market block not found')
new_connections = '''{intelMode === "CONNECTIONS" ? (() => {
 const source = selectedConnectionSource || {};
 const trainerName = selected ? firstText(selected.row, ["trainer", "trainer_name"], "-") : "-";
 const jockeyName = selected ? firstText(selected.row, ["jockey", "jockey_name", "rider"], "-") : "-";
 const partnership = firstText(source, ["combo_read", "connection_angle_3", "connection_narrative"], "-");
 const statRows = [["Track", firstText(source, ["trainer_track_read", "jockey_track_read"], "-")], ["Distance", firstText(source, ["trainer_distance_read", "jockey_distance_read"], "-")], ["Class / Prep", firstText(source, ["trainer_prep_read", "connection_angle_2"], "-")], ["Market / SP", firstText(source, ["trainer_market_read", "market_expectation_label"], "-")]];
 return <section className="edgeiq-connections-tab edgeiq-product-section"><div className="edgeiq-tab-heading"><span>CONNECTIONS</span><strong>{selected ? horse(selected.row) : "Select a runner"}</strong></div><div className="edgeiq-connections-grid"><article><span>Trainer</span><strong>{trainerName}</strong></article><article><span>Jockey</span><strong>{jockeyName}</strong></article><article><span>Partnership</span><strong>{partnership}</strong></article></div><div className="edgeiq-connections-stats">{statRows.map(([label, value]) => <article key={`connection-stat-${label}`}><span>{label}</span><strong>{value || "-"}</strong></article>)}</div>{selectedConnectionNarrative ? <p className="edgeiq-connections-read">{selectedConnectionNarrative}</p> : null}</section>;
 })() : null}

 '''
text = text[:market_start] + new_connections + text[market_start:]

# Market block simplification.
market_start = text.find('{intelMode === "DVNCED" ? (() => {')
results_start = text.find('{intelMode === "RESULTS" ? (', market_start)
new_market = '''{intelMode === "DVNCED" ? (() => {
 const marketRows = activeRaceRows;
 const marketStatusFor = (item: EnrichedRunner) => {
 const state = firstText(item.row, ["market_state", "tab_fixed_betting_status", "tab_tote_betting_status"], "").toUpperCase();
 const price = livePrice(item.row, item.bet);
 if (state.includes("CLOSED")) return "Market Closed";
 return price !== null ? "Market Available" : "Awaiting Feed";
 };
 return <section className="edgeiq-market-tab edgeiq-product-section"><div className="edgeiq-tab-heading"><span>MARKET</span><strong>EDGEiQ and market price comparison</strong></div><div className="edgeiq-market-table edgeiq-product-table" role="table" aria-label="Market comparison table"><div className="edgeiq-market-row head" role="row">{['Horse','EDGEiQ','Market','Difference','Status'].map((label) => <span key={`market-head-${label}`}>{label}</span>)}</div>{marketRows.map((item) => { const fair = limitedAdjustedPrice(item) ?? fairPrice(item.row, item.bet); const market = livePrice(item.row, item.bet); const diff = edgePct(item.row, item.bet); return <div className="edgeiq-market-row" role="row" key={`market-row-${runnerRowKey(item.row)}`}><strong>{horse(item.row)}</strong><span>{money(fair)}</span><span>{money(market)}</span><span className={diff === null ? "neutral" : diff >= 0 ? "positive" : "negative"}>{diff === null ? "-" : pct(diff)}</span><span>{marketStatusFor(item)}</span></div>; })}</div></section>;
 })() : null}

 '''
text = replace_range(text, market_start, results_start, new_market)

# Results placeholder.
results_start = text.find('{intelMode === "RESULTS" ? (')
results_end = text.find('\n </div>\n );\n}', results_start)
if results_start >= 0 and results_end > results_start:
    new_results = '''{intelMode === "RESULTS" ? (
 <section className="edgeiq-results-tab edgeiq-product-section"><div className="edgeiq-tab-heading"><span>RESULTS</span><strong>Post-race workspace</strong></div><div className="edgeiq-results-future-grid">{['Official Result','Winner Rating','Race Rating','Forgive Run','Sectional Star','Future Follow'].map((label) => <article key={`results-future-${label}`}><span>{label}</span><strong>Pending</strong></article>)}</div></section>
 ) : null}
'''
    text = replace_range(text, results_start, results_end, new_results)

RACE.write_text(text, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
css_add = '''

/* EDGEiQ Information Architecture Reset V1 */
.edgeiq-home-restored-grid { display: grid; grid-template-columns: minmax(0,1.25fr) minmax(320px,.75fr); gap: 18px; align-items: stretch; }
.edgeiq-home-restored-hero { min-height: 340px; }
.edgeiq-home-statement-panel { display: grid; gap: 12px; }
.edgeiq-home-statement-panel article { border: 1px solid rgba(148,163,184,.18); border-radius: 18px; padding: 18px; background: rgba(15,23,42,.62); }
.edgeiq-home-statement-panel strong { color: #fff; font-size: 18px; }
.edgeiq-home-statement-panel p { margin: 7px 0 0; color: #aeb8c5; font-size: 13px; line-height: 1.45; }
.edgeiq-home-meetings-grid { display: grid; grid-template-columns: .82fr 1.18fr; gap: 18px; }
.edgeiq-tab-heading { display: flex; justify-content: space-between; align-items: end; gap: 12px; margin-bottom: 14px; }
.edgeiq-tab-heading span { color: #9ca3af; font-size: 11px; font-weight: 1000; letter-spacing: .20em; text-transform: uppercase; }
.edgeiq-tab-heading strong { color: #fff; font-size: 20px; }
.edgeiq-field-table, .edgeiq-market-table, .edgeiq-ratings-heat-table { border: 1px solid rgba(148,163,184,.18); border-radius: 16px; overflow: auto; background: rgba(15,23,42,.58); }
.edgeiq-field-table-row { min-width: 1080px; display: grid; grid-template-columns: 64px minmax(190px,1fr) 90px 90px minmax(160px,1fr) minmax(170px,1fr) 120px 120px; width: 100%; border: 0; border-bottom: 1px solid rgba(148,163,184,.12); background: transparent; text-align: left; cursor: pointer; }
.edgeiq-field-table-row span, .edgeiq-field-table-row strong, .edgeiq-market-row span, .edgeiq-market-row strong, .edgeiq-ratings-heat-row span, .edgeiq-ratings-heat-row strong { padding: 11px 12px; color: #d1d5db; font-size: 12px; border-right: 1px solid rgba(148,163,184,.08); }
.edgeiq-field-table-row strong, .edgeiq-market-row strong, .edgeiq-ratings-heat-row strong { color: #fff; }
.edgeiq-field-table-row.head, .edgeiq-market-row.head, .edgeiq-ratings-heat-row.head { background: rgba(3,7,18,.48); }
.edgeiq-field-table-row.head span, .edgeiq-market-row.head span, .edgeiq-ratings-heat-row.head span { color: #9ca3af; font-size: 10px; font-weight: 1000; letter-spacing: .12em; text-transform: uppercase; }
.edgeiq-field-table-row.is-selected { box-shadow: inset 3px 0 0 #34d399; background: rgba(52,211,153,.08); }
.edgeiq-ratings-hero { border: 1px solid rgba(148,163,184,.18); border-radius: 22px; padding: 22px; background: rgba(15,23,42,.66); margin-bottom: 12px; }
.edgeiq-ratings-hero span { display: block; color: #9ca3af; font-size: 11px; font-weight: 1000; letter-spacing: .18em; text-transform: uppercase; }
.edgeiq-ratings-hero strong { display: block; color: #fff; font-size: 42px; margin-top: 6px; }
.edgeiq-ratings-summary-grid, .edgeiq-connections-grid, .edgeiq-connections-stats, .edgeiq-results-future-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin-bottom: 12px; }
.edgeiq-ratings-summary-grid article, .edgeiq-connections-grid article, .edgeiq-connections-stats article, .edgeiq-results-future-grid article { border: 1px solid rgba(148,163,184,.18); border-radius: 16px; padding: 14px; background: rgba(15,23,42,.58); }
.edgeiq-ratings-summary-grid span, .edgeiq-connections-grid span, .edgeiq-connections-stats span, .edgeiq-results-future-grid span { color: #9ca3af; font-size: 10px; font-weight: 1000; letter-spacing: .14em; text-transform: uppercase; }
.edgeiq-ratings-summary-grid strong, .edgeiq-connections-grid strong, .edgeiq-connections-stats strong, .edgeiq-results-future-grid strong { display: block; color: #fff; font-size: 18px; margin-top: 5px; }
.edgeiq-ratings-heat-row { min-width: 620px; display: grid; grid-template-columns: minmax(220px,1fr) 120px 120px; border-bottom: 1px solid rgba(148,163,184,.12); }
.edgeiq-market-row { min-width: 780px; display: grid; grid-template-columns: minmax(220px,1fr) 120px 120px 120px 150px; border-bottom: 1px solid rgba(148,163,184,.12); }
.edgeiq-ratings-heat-row .positive, .edgeiq-market-row .positive { color: #34d399; font-weight: 1000; }
.edgeiq-ratings-heat-row .negative, .edgeiq-market-row .negative { color: #f87171; font-weight: 1000; }
.edgeiq-ratings-heat-row .neutral, .edgeiq-market-row .neutral { color: #e5e7eb; }
.edgeiq-connections-read { margin: 0; border: 1px solid rgba(148,163,184,.18); border-radius: 16px; padding: 14px; color: #d1d5db; background: rgba(15,23,42,.58); line-height: 1.5; }
@media (max-width: 980px) { .edgeiq-home-restored-grid, .edgeiq-home-meetings-grid, .edgeiq-ratings-summary-grid, .edgeiq-connections-grid, .edgeiq-connections-stats, .edgeiq-results-future-grid { grid-template-columns: 1fr; } }
'''
if 'EDGEiQ Information Architecture Reset V1' not in css:
    css += css_add
CSS.write_text(css, encoding="utf-8")

SUMMARY.write_text('metric,value\nstatus,APPLIED\nfinal_tab_order,RACE;FIELD;RATINGS;FORM;MAP;CONNECTIONS;MARKET;RESULTS\nui_only,YES\n', encoding='utf-8')
REPORT.write_text('EDGEIQ_INFORMATION_ARCHITECTURE_RESET_HOME_RESTORE_V1 applied. Home restored, FIELD simplified, RATINGS added, CONNECTIONS added, MARKET simplified. Frontend only.\n', encoding='utf-8')
print('ia_reset_applied')
