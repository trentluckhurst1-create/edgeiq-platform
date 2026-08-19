from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
APP = ROOT / "src" / "App.tsx"
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CHECK_RACE = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRODUCT_SHELL_HOME_V2_20260629.tsx"
CHECK_APP = ROOT / "src" / "App_CHECKPOINT_PRODUCT_SHELL_HOME_V2_20260629.tsx"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v2_upgrade_report.txt"

app = APP.read_text(encoding="utf-8")
race = TSX.read_text(encoding="utf-8")
CHECK_APP.write_text(app, encoding="utf-8")
CHECK_RACE.write_text(race, encoding="utf-8")

def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Missing insertion point: {label}")
    return src.replace(old, new, 1)

# App: bridge shell view into outer chrome visibility.
app = replace_once(
    app,
    'const [selectedRaceKey, setSelectedRaceKey] = useState(() => storedValue("edgeiq_selected_race"));\n  const [selectedHorseKey, setSelectedHorseKey] = useState(() => storedValue("edgeiq_selected_runner"));\n',
    'const [selectedRaceKey, setSelectedRaceKey] = useState(() => storedValue("edgeiq_selected_race"));\n  const [selectedHorseKey, setSelectedHorseKey] = useState(() => storedValue("edgeiq_selected_runner"));\n  const [intelligenceProductView, setIntelligenceProductView] = useState<"HOME" | "MEETING" | "RACE">("HOME");\n',
    "App product shell state",
)
app = replace_once(
    app,
    '  return (\n    <>      <EdgeRaceTicker meetings={tickerMeetings} currentRaceKey={currentRace?.key ?? ""} onSelectRace={(raceKey) => { setSelectedRaceKey(raceKey); setSelectedHorseKey(""); }} />      <div className="edgeiq-racing-app ert-shell min-h-screen bg-[#07101b] text-[#dbe7f3]">\n',
    '  const showOuterTerminalChrome = tab !== "INTELLIGENCE" || intelligenceProductView === "RACE";\n\n  return (\n    <>\n      {showOuterTerminalChrome ? (\n        <EdgeRaceTicker\n          meetings={tickerMeetings}\n          currentRaceKey={currentRace?.key ?? ""}\n          onSelectRace={(raceKey) => {\n            setSelectedRaceKey(raceKey);\n            setSelectedHorseKey("");\n            setIntelligenceProductView("RACE");\n          }}\n        />\n      ) : null}\n      <div className="edgeiq-racing-app ert-shell min-h-screen bg-[#07101b] text-[#dbe7f3]">\n',
    "App ticker chrome gate",
)
app = replace_once(
    app,
    '        <header className="rounded-2xl border border-slate-700/60 bg-gradient-to-r from-[#0b1220] to-[#070d18] text-white shadow-xl">\n',
    '        {showOuterTerminalChrome ? (\n        <header className="rounded-2xl border border-slate-700/60 bg-gradient-to-r from-[#0b1220] to-[#070d18] text-white shadow-xl">\n',
    "App header open gate",
)
app = replace_once(
    app,
    '          </header>\n\n        {currentMeeting ? (\n',
    '          </header>\n        ) : null}\n\n        {showOuterTerminalChrome && currentMeeting ? (\n',
    "App header close gate",
)
app = replace_once(
    app,
    '        {activeSelectorMismatch && activeSelectorFocus ? (\n',
    '        {showOuterTerminalChrome && activeSelectorMismatch && activeSelectorFocus ? (\n',
    "App mismatch gate",
)
app = replace_once(
    app,
    '        <div className="mt-3">\n          <TerminalNav\n            activeTab={tab as any}\n            onChange={(next) => setTab(next as TabKey)}\n          />\n        </div>\n\n      <main className="mt-3">\n',
    '        {showOuterTerminalChrome ? (\n          <div className="mt-3">\n            <TerminalNav\n              activeTab={tab as any}\n              onChange={(next) => setTab(next as TabKey)}\n            />\n          </div>\n        ) : null}\n\n      <main className={showOuterTerminalChrome ? "mt-3" : "mt-0"}>\n',
    "App terminal nav gate",
)
app = replace_once(
    app,
    '              compactKey={compactKey}\n            />          ) : tab === "MARKET" ? (\n',
    '              compactKey={compactKey}\n              onProductViewChange={(next: "HOME" | "MEETING" | "RACE") => setIntelligenceProductView(next)}\n            />          ) : tab === "MARKET" ? (\n',
    "App pass product callback",
)
app = replace_once(
    app,
    '        <div className="mt-2 text-[10px] text-[#6d7680]">Data: {displayDate(currentRace?.raceDate ?? currentMeeting?.raceDate ?? "")} | local CSV files</div>\n',
    '        {showOuterTerminalChrome ? (\n          <div className="mt-2 text-[10px] text-[#6d7680]">Data: {displayDate(currentRace?.raceDate ?? currentMeeting?.raceDate ?? "")} | local CSV files</div>\n        ) : null}\n',
    "App data footer gate",
)

# Race screen: callback helper and shell copy/layout.
race = replace_once(
    race,
    '  const [productView, setProductView] = useState<ProductView>("HOME");\n',
    '  const [productView, setProductView] = useState<ProductView>("HOME");\n  const updateProductView = (next: ProductView) => {\n    setProductView(next);\n    if (typeof props.onProductViewChange === "function") props.onProductViewChange(next);\n  };\n',
    "Race updateProductView helper",
)
race = race.replace('setProductView("MEETING")', 'updateProductView("MEETING")')
race = race.replace('setProductView("RACE")', 'updateProductView("RACE")')
race = race.replace('setProductView("HOME")', 'updateProductView("HOME")')
# Avoid replacing the helper's own setProductView? We replaced helper body now has updateProductView recursion? Fix if so.
race = race.replace('  const updateProductView = (next: ProductView) => {\n    updateProductView(next);', '  const updateProductView = (next: ProductView) => {\n    setProductView(next);')

home_start = race.find('  if (productView === "HOME") {')
meeting_start = race.find('  if (productView === "MEETING") {', home_start)
if home_start == -1 or meeting_start == -1:
    raise SystemExit("Could not locate HOME block")
new_home = r'''  if (productView === "HOME") {
    const productShellStats = [
      `${productShellMeetings.length} meetings`,
      `${productShellRaces.length} races`,
      `${runnerRows.length} runners`,
      "Victoria focus",
      "Fields ready",
    ];
    const productCapabilityCards = [
      { title: "RACE SHAPE", text: "Speed maps, pressure, settling positions and pace advantage." },
      { title: "FORM INTELLIGENCE", text: "Recovered historical ratings, last-five evidence, form figures and profile trends." },
      { title: "RUNNER PROFILES", text: "Distance, condition, class, campaign and trajectory context." },
      { title: "MARKET COMMAND", text: "Fair price, edge context and market movement intelligence." },
      { title: "FACTOR LAB", text: "Evidence breakdowns for users who want to inspect the why." },
    ];
    const renderMeetingCards = (meetings: typeof productShellMeetings, emptyLabel: string, compact = false) => (
      meetings.length ? meetings.map((meeting) => (
        <article key={`shell-meeting-${meeting.meetingKey}`} style={{ ...shellMeetingCardStyle, minHeight: compact ? 126 : 148 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start" }}>
            <div style={{ display: "grid", gap: 4 }}>
              <span style={{ color: "#7dd3fc", fontSize: 10, fontWeight: 1000, letterSpacing: ".12em", textTransform: "uppercase" }}>{meeting.dayLabel}</span>
              <strong style={{ color: "#f8fafc", fontSize: compact ? 17 : 20, lineHeight: 1 }}>{meeting.trackName}</strong>
              <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>{meeting.meetingDate || "Date TBC"}</span>
            </div>
            <span style={fitBadge(meeting.meetingStatus, "#34d399", "rgba(22,101,52,.18)", "1px solid rgba(52,211,153,.28)")}>{meeting.meetingStatus}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 8 }}>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Races</span><strong style={miniValueStyle}>{meeting.raceCount}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Condition</span><strong style={miniValueStyle}>{meeting.trackConditionLatest}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Rail</span><strong style={miniValueStyle}>{meeting.railPositionLatest}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Status</span><strong style={miniValueStyle}>{meeting.dataQualityStatus}</strong></div>
          </div>
          <button type="button" style={shellButtonStyle} onClick={() => openShellMeeting(meeting.meetingKey)}>View Meeting</button>
        </article>
      )) : <div style={{ color: "#94a3b8", fontSize: 13 }}>{emptyLabel}</div>
    );

    return (
      <div style={{ ...pageStyle, paddingTop: 18 }}>
        <section style={{ ...panelStyle, display: "grid", gap: 22, alignContent: "start", background: "radial-gradient(circle at 78% 8%, rgba(52,211,153,.13), transparent 26%), radial-gradient(circle at 12% 18%, rgba(125,211,252,.14), transparent 30%), linear-gradient(135deg, rgba(8,15,28,.98), rgba(3,8,16,.94))" }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.05fr) minmax(320px,.95fr)", gap: 20, alignItems: "stretch" }}>
            <div style={{ display: "grid", gap: 18, alignContent: "center", padding: "18px 4px" }}>
              <div style={{ display: "inline-grid", justifyItems: "start", gap: 7 }}>
                <span style={{ color: "#34d399", fontSize: 11, fontWeight: 1000, letterSpacing: ".24em", textTransform: "uppercase" }}>Racing Intelligence Platform</span>
                <strong style={{ color: "#f8fafc", fontSize: 62, lineHeight: .9, letterSpacing: ".01em" }}>EDGEiQ</strong>
                <span style={{ color: "#dbeafe", fontSize: 22, fontWeight: 950 }}>Racing Intelligence Platform</span>
              </div>
              <p style={{ margin: 0, maxWidth: 720, color: "#dbe7f3", fontSize: 16, lineHeight: 1.65, fontWeight: 800 }}>
                Race-shape, form, market, runner and factor intelligence in one terminal.
              </p>
              <p style={{ margin: 0, maxWidth: 760, color: "#94a3b8", fontSize: 14, lineHeight: 1.72 }}>
                EDGEiQ is not a tipping service. It is a decision-support platform built to show how a race is likely to be run, where the evidence is strongest, and which runners deserve deeper attention.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  style={{ ...shellButtonStyle, padding: "12px 16px", background: "linear-gradient(135deg, rgba(14,165,233,.24), rgba(52,211,153,.18))" }}
                  onClick={() => selectedShellMeeting ? openShellMeeting(selectedShellMeeting.meetingKey) : updateProductView("MEETING")}
                >
                  Enter Terminal
                </button>
                <button
                  type="button"
                  style={{ ...shellButtonStyle, padding: "12px 16px", background: "rgba(15,23,42,.9)" }}
                  onClick={() => selectedShellMeeting ? openShellMeeting(selectedShellMeeting.meetingKey) : updateProductView("MEETING")}
                >
                  View Today's Meetings
                </button>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {productShellStats.map((item, index) => (
                  <span key={`product-shell-stat-${item}`} style={fitBadge(item, index < 3 ? "#7dd3fc" : "#34d399", "rgba(15,23,42,.88)", "1px solid rgba(80,120,180,.32)")}>{item}</span>
                ))}
              </div>
            </div>
            <div style={{ border: "1px solid rgba(80,120,180,.32)", borderRadius: 8, padding: 18, background: "linear-gradient(135deg, rgba(8,15,28,.96), rgba(5,12,22,.86))", display: "grid", gap: 15, alignContent: "center", minHeight: 300 }}>
              <div style={{ display: "grid", gap: 9 }}>
                <div style={{ height: 2, background: "linear-gradient(90deg, #34d399, #7dd3fc, transparent)", width: "82%" }} />
                <div style={{ height: 2, background: "linear-gradient(90deg, transparent, #f5c451, #7dd3fc)", width: "94%", justifySelf: "end" }} />
                <div style={{ height: 2, background: "linear-gradient(90deg, #7dd3fc, transparent)", width: "66%" }} />
                <div style={{ height: 28, borderBottom: "1px solid rgba(125,211,252,.34)", borderLeft: "1px solid rgba(52,211,153,.28)", transform: "skewX(-18deg)", opacity: .72 }} />
              </div>
              <div style={{ border: "1px solid rgba(125,211,252,.28)", borderRadius: 8, padding: 15, background: "rgba(2,6,23,.55)", display: "grid", gap: 8 }}>
                <span style={{ color: "#7dd3fc", fontSize: 10, fontWeight: 1000, letterSpacing: ".16em", textTransform: "uppercase" }}>EDGEiQ Terminal</span>
                <strong style={{ color: "#f8fafc", fontSize: 23 }}>Evidence before opinion</strong>
                <span style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.55 }}>Meetings flow into race workspaces for COMMAND, MAP, FORM, RUNNERS, FACTOR LAB and RESEARCH.</span>
              </div>
            </div>
          </div>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={titleStyle}><span>What EDGEiQ Does</span><em>decision support, not tipping copy</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
              {productCapabilityCards.map((card) => (
                <article key={`product-capability-${card.title}`} style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 8, padding: 13, background: "rgba(5,12,22,.72)", display: "grid", gap: 8 }}>
                  <strong style={{ color: "#dbeafe", fontSize: 12, fontWeight: 1000, letterSpacing: ".1em" }}>{card.title}</strong>
                  <span style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.55 }}>{card.text}</span>
                </article>
              ))}
            </div>
          </section>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={titleStyle}><span>Today Meetings</span><em>clean path into the terminal</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
              {renderMeetingCards(todayShellMeetings.length ? todayShellMeetings : productShellMeetings.slice(0, 4), "No meetings loaded for today.")}
            </div>
          </section>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={titleStyle}><span>Upcoming Meetings</span><em>future cards in the governed universe</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
              {renderMeetingCards(upcomingShellMeetings, "No additional upcoming meetings loaded.", true)}
            </div>
          </section>
        </section>
      </div>
    );
  }

'''
race = race[:home_start] + new_home + race[meeting_start:]

# Meeting table cleanup: replace the header/grid fragments to include Condition and remove Rating.
race = race.replace(
    'gridTemplateColumns: "70px 90px minmax(180px,1.2fr) 90px 130px 90px 130px 130px 120px"',
    'gridTemplateColumns: "70px 90px 90px 130px 90px 120px 130px 120px"'
)
race = race.replace(
    '<span>Race</span><span>Time</span><span>Title</span><span>Dist</span><span>Class</span><span>Field</span><span>Market</span><span>Rating</span><span>Open</span>',
    '<span>Race</span><span>Time</span><span>Distance</span><span>Class</span><span>Field</span><span>Condition</span><span>Market</span><span>Open Race</span>'
)
race = race.replace(
    '                  <span style={{ color: "#dbeafe", fontSize: 12, fontWeight: 850 }}>{race.raceTitle}</span>\n                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.distanceValue}</span>\n                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.raceClassValue}</span>\n                  <span style={{ color: "#f8fafc", fontSize: 12, fontWeight: 900 }}>{race.fieldSize}</span>\n                  <span style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 900 }}>{race.marketStateValue}</span>\n                  <span style={{ color: "#34d399", fontSize: 11, fontWeight: 900 }}>{race.ratingReference}</span>\n                  <button type="button" style={shellButtonStyle} onClick={() => openShellRace(race)}>Open Race</button>',
    '                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.distanceValue}</span>\n                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.raceClassValue}</span>\n                  <span style={{ color: "#f8fafc", fontSize: 12, fontWeight: 900 }}>{race.fieldSize}</span>\n                  <span style={{ color: "#dbeafe", fontSize: 11, fontWeight: 900 }}>{race.trackConditionValue}</span>\n                  <span style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 900 }}>{race.marketStateValue}</span>\n                  <button type="button" style={shellButtonStyle} onClick={() => openShellRace(race)}>Open Race</button>'
)

APP.write_text(app, encoding="utf-8")
TSX.write_text(race, encoding="utf-8")
REPORT.write_text("EDGEiQ PRODUCT SHELL HOME V2 UPGRADE\ncheckpoint_race=" + str(CHECK_RACE) + "\ncheckpoint_app=" + str(CHECK_APP) + "\nstatus=PRODUCT_SHELL_HOME_V2_APPLIED\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n", encoding="utf-8")
print(REPORT)
