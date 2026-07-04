from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRODUCT_SHELL_V1_20260629.tsx"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_ui_fix_v1_report.txt"
text = TSX.read_text(encoding="utf-8")
CHECKPOINT.write_text(text, encoding="utf-8")

replacements = []

def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Missing insertion point: {label}")
    return src.replace(old, new, 1)

text = replace_once(
    text,
    'type IntelMode = "COMMAND" | "MAP" | "FORM" | "RUNNERS" | "FACTORS" | "ADVANCED";\n',
    'type IntelMode = "COMMAND" | "MAP" | "FORM" | "RUNNERS" | "FACTORS" | "ADVANCED";\ntype ProductView = "HOME" | "MEETING" | "RACE";\n',
    "ProductView type",
)

text = replace_once(
    text,
    '  const [selectedKey, setSelectedKey] = useState("");\n',
    '  const [selectedKey, setSelectedKey] = useState("");\n  const [productView, setProductView] = useState<ProductView>("HOME");\n  const [shellMeetingKey, setShellMeetingKey] = useState("");\n  const [shellTrack, setShellTrack] = useState("");\n  const [shellRaceNo, setShellRaceNo] = useState("");\n',
    "shell state",
)

text = replace_once(
    text,
    '  const selectedTrack = cleanTrack(props.selectedTrack || props.currentRace?.track);\n  const selectedRaceNo = text(props.selectedRaceNo || props.currentRace?.raceNo || props.currentRace?.race_no);\n',
    '  const selectedTrack = cleanTrack(shellTrack || props.selectedTrack || props.currentRace?.track);\n  const selectedRaceNo = text(shellRaceNo || props.selectedRaceNo || props.currentRace?.raceNo || props.currentRace?.race_no);\n',
    "selected shell override",
)

shell_logic = r'''
  const productShellRaces = useMemo(() => {
    const raceMap = new Map<string, {
      meetingDate: string;
      dayLabel: string;
      trackName: string;
      meetingKey: string;
      raceKey: string;
      raceNoValue: string;
      raceTime: string;
      raceTitle: string;
      distanceValue: string;
      raceClassValue: string;
      trackConditionValue: string;
      railValue: string;
      fieldSize: number;
      marketStateValue: string;
      ratingReference: string;
      priceReference: string;
      dataQualityStatus: string;
    }>();

    runnerRows.forEach((row) => {
      const dateValue = raceDate(row) || firstText(row, ["meeting_date", "_date"], "");
      const trackName = track(row);
      const raceNoValue = raceNo(row);
      if (!trackName || !raceNoValue) return;
      const meetingKey = firstText(row, ["meeting_key"], `${dateValue}_${cleanTrack(trackName)}`);
      const raceKeyValue = firstText(row, ["race_key"], `${meetingKey}_R${raceNoValue}`);
      const existing = raceMap.get(raceKeyValue);
      if (existing) {
        existing.fieldSize += 1;
        if (existing.raceTime === "Time TBC") existing.raceTime = firstText(row, ["race_time", "jump_time", "start_time"], existing.raceTime) || existing.raceTime;
        if (existing.trackConditionValue === "—") existing.trackConditionValue = trackCondition(row);
        if (existing.railValue === "—") existing.railValue = firstText(row, ["rail_position", "rail", "rail_clean"], "—");
        return;
      }
      const priceReady = firstNum(row, ["edgeiq_active_display_fair_price", "edgeiq_v7_2g2_guarded_display_fair_price", "fair_price"]) !== null;
      const ratingReady = firstNum(row, ["projected_rating_V6_1_RESEARCH", "projected_rating_v5_2", "total_rating_points"]) !== null;
      raceMap.set(raceKeyValue, {
        meetingDate: dateValue,
        dayLabel: firstText(row, ["day_bucket"], "UPCOMING").replace("DAY+2", "DAY +2"),
        trackName,
        meetingKey,
        raceKey: raceKeyValue,
        raceNoValue,
        raceTime: firstText(row, ["race_time", "jump_time", "start_time"], "Time TBC") || "Time TBC",
        raceTitle: firstText(row, ["race_title", "race_name"], `${trackName} R${raceNoValue}`),
        distanceValue: distance(row),
        raceClassValue: raceClass(row),
        trackConditionValue: trackCondition(row),
        railValue: firstText(row, ["rail_position", "rail", "rail_clean"], "—"),
        fieldSize: 1,
        marketStateValue: firstText(row, ["market_state", "tab_fixed_betting_status", "market_source_status"], "PENDING").replace(/_/g, " ").toUpperCase(),
        ratingReference: ratingReady ? "V6.1 reference" : "Rating pending",
        priceReference: priceReady ? "V7.2G2 display" : "Price pending",
        dataQualityStatus: "READY",
      });
    });

    return Array.from(raceMap.values()).sort((a, b) =>
      a.meetingDate.localeCompare(b.meetingDate) ||
      cleanTrack(a.trackName).localeCompare(cleanTrack(b.trackName)) ||
      (Number(a.raceNoValue) || 999) - (Number(b.raceNoValue) || 999)
    );
  }, [runnerRows]);

  const productShellMeetings = useMemo(() => {
    const meetingMap = new Map<string, {
      meetingDate: string;
      dayLabel: string;
      trackName: string;
      meetingKey: string;
      meetingStatus: string;
      raceCount: number;
      firstRaceTime: string;
      lastRaceTime: string;
      trackConditionLatest: string;
      railPositionLatest: string;
      marketStatusSummary: string;
      stateRegion: string;
      dataQualityStatus: string;
    }>();

    productShellRaces.forEach((race) => {
      const existing = meetingMap.get(race.meetingKey);
      if (existing) {
        existing.raceCount += 1;
        if (race.raceTime !== "Time TBC") {
          existing.firstRaceTime = existing.firstRaceTime === "Time TBC" ? race.raceTime : [existing.firstRaceTime, race.raceTime].sort()[0];
          existing.lastRaceTime = existing.lastRaceTime === "Time TBC" ? race.raceTime : [existing.lastRaceTime, race.raceTime].sort().slice(-1)[0];
        }
        if (existing.trackConditionLatest === "—") existing.trackConditionLatest = race.trackConditionValue;
        if (existing.railPositionLatest === "—") existing.railPositionLatest = race.railValue;
        return;
      }
      meetingMap.set(race.meetingKey, {
        meetingDate: race.meetingDate,
        dayLabel: race.dayLabel || "UPCOMING",
        trackName: race.trackName,
        meetingKey: race.meetingKey,
        meetingStatus: "FIELDS READY",
        raceCount: 1,
        firstRaceTime: race.raceTime,
        lastRaceTime: race.raceTime,
        trackConditionLatest: race.trackConditionValue,
        railPositionLatest: race.railValue,
        marketStatusSummary: race.marketStateValue || "PENDING",
        stateRegion: "VIC",
        dataQualityStatus: race.dataQualityStatus,
      });
    });

    return Array.from(meetingMap.values()).sort((a, b) =>
      a.meetingDate.localeCompare(b.meetingDate) || cleanTrack(a.trackName).localeCompare(cleanTrack(b.trackName))
    );
  }, [productShellRaces]);

  const selectedShellMeeting = productShellMeetings.find((meeting) => meeting.meetingKey === shellMeetingKey) || productShellMeetings[0];
  const selectedShellMeetingRaces = selectedShellMeeting
    ? productShellRaces.filter((race) => race.meetingKey === selectedShellMeeting.meetingKey)
    : [];
  const todayShellMeetings = productShellMeetings.filter((meeting) => meeting.dayLabel.toUpperCase().includes("TODAY"));
  const upcomingShellMeetings = productShellMeetings.filter((meeting) => !meeting.dayLabel.toUpperCase().includes("TODAY"));
  const shellMeetingCardStyle: React.CSSProperties = {
    border: "1px solid rgba(80,120,180,.28)",
    borderRadius: 8,
    padding: 13,
    background: "linear-gradient(135deg, rgba(8,15,28,.96), rgba(15,23,42,.82))",
    display: "grid",
    gap: 10,
    minHeight: 148,
  };
  const shellButtonStyle: React.CSSProperties = {
    appearance: "none",
    border: "1px solid rgba(125,211,252,.38)",
    borderRadius: 6,
    padding: "8px 10px",
    background: "rgba(14,165,233,.12)",
    color: "#dbeafe",
    fontSize: 11,
    fontWeight: 1000,
    letterSpacing: ".08em",
    textTransform: "uppercase",
    cursor: "pointer",
  };
  const openShellMeeting = (meetingKey: string) => {
    setShellMeetingKey(meetingKey);
    setProductView("MEETING");
  };
  const openShellRace = (race: typeof productShellRaces[number]) => {
    setShellMeetingKey(race.meetingKey);
    setShellTrack(race.trackName);
    setShellRaceNo(race.raceNoValue);
    setProductView("RACE");
    setSelectedKey("");
    setIntelMode("COMMAND");
  };
'''

text = replace_once(
    text,
    '  const historyMasterByHorse = useMemo(() => {\n',
    shell_logic + '\n  const historyMasterByHorse = useMemo(() => {\n',
    "product shell logic",
)

home_jsx = r'''
  if (productView === "HOME") {
    const renderMeetingCards = (meetings: typeof productShellMeetings, emptyLabel: string) => (
      meetings.length ? meetings.map((meeting) => (
        <article key={`shell-meeting-${meeting.meetingKey}`} style={shellMeetingCardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start" }}>
            <div style={{ display: "grid", gap: 4 }}>
              <span style={{ color: "#7dd3fc", fontSize: 10, fontWeight: 1000, letterSpacing: ".12em", textTransform: "uppercase" }}>{meeting.dayLabel}</span>
              <strong style={{ color: "#f8fafc", fontSize: 20, lineHeight: 1 }}>{meeting.trackName}</strong>
              <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 800 }}>{meeting.meetingDate || "Date TBC"}</span>
            </div>
            <span style={fitBadge(meeting.meetingStatus, "#34d399", "rgba(22,101,52,.18)", "1px solid rgba(52,211,153,.28)")}>{meeting.meetingStatus}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 8 }}>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Races</span><strong style={miniValueStyle}>{meeting.raceCount}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>First Race</span><strong style={miniValueStyle}>{meeting.firstRaceTime}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Condition</span><strong style={miniValueStyle}>{meeting.trackConditionLatest}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Rail</span><strong style={miniValueStyle}>{meeting.railPositionLatest}</strong></div>
          </div>
          <button type="button" style={shellButtonStyle} onClick={() => openShellMeeting(meeting.meetingKey)}>View Meeting</button>
        </article>
      )) : <div style={{ color: "#94a3b8", fontSize: 13 }}>{emptyLabel}</div>
    );

    return (
      <div style={pageStyle}>
        <section style={{ ...panelStyle, minHeight: "72vh", display: "grid", gap: 18, alignContent: "start" }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.1fr) minmax(280px,.9fr)", gap: 18, alignItems: "stretch" }}>
            <div style={{ display: "grid", gap: 16, alignContent: "center", padding: "18px 4px" }}>
              <div style={{ display: "inline-grid", justifyItems: "start", gap: 6 }}>
                <span style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 1000, letterSpacing: ".24em", textTransform: "uppercase" }}>Racing Intelligence</span>
                <strong style={{ color: "#f8fafc", fontSize: 54, lineHeight: .92, letterSpacing: ".02em" }}>EDGEiQ</strong>
                <span style={{ color: "#cbd5e1", fontSize: 18, fontWeight: 900 }}>Racing Intelligence Terminal</span>
              </div>
              <p style={{ margin: 0, maxWidth: 620, color: "#dbe7f3", fontSize: 15, lineHeight: 1.65 }}>
                Race-shape, form, market and runner intelligence in one terminal.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  type="button"
                  style={{ ...shellButtonStyle, padding: "11px 15px", background: "linear-gradient(135deg, rgba(14,165,233,.22), rgba(52,211,153,.16))" }}
                  onClick={() => selectedShellMeeting ? openShellMeeting(selectedShellMeeting.meetingKey) : setProductView("MEETING")}
                >
                  Enter Terminal
                </button>
                <span style={fitBadge(`${productShellMeetings.length} meetings`, "#7dd3fc", "rgba(15,23,42,.88)", "1px solid rgba(80,120,180,.32)")}>{productShellMeetings.length} meetings</span>
                <span style={fitBadge(`${productShellRaces.length} races`, "#34d399", "rgba(15,23,42,.88)", "1px solid rgba(80,120,180,.32)")}>{productShellRaces.length} races</span>
              </div>
            </div>
            <div style={{ border: "1px solid rgba(80,120,180,.32)", borderRadius: 8, padding: 16, background: "radial-gradient(circle at 25% 20%, rgba(125,211,252,.18), transparent 28%), linear-gradient(135deg, rgba(8,15,28,.96), rgba(5,12,22,.86))", display: "grid", gap: 14, alignContent: "center", minHeight: 260 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <div style={{ height: 2, background: "linear-gradient(90deg, #34d399, #7dd3fc, transparent)", width: "78%" }} />
                <div style={{ height: 2, background: "linear-gradient(90deg, transparent, #f5c451, #7dd3fc)", width: "92%", justifySelf: "end" }} />
                <div style={{ height: 2, background: "linear-gradient(90deg, #7dd3fc, transparent)", width: "64%" }} />
              </div>
              <div style={{ border: "1px solid rgba(125,211,252,.28)", borderRadius: 8, padding: 14, background: "rgba(2,6,23,.55)", display: "grid", gap: 7 }}>
                <span style={{ color: "#7dd3fc", fontSize: 10, fontWeight: 1000, letterSpacing: ".16em", textTransform: "uppercase" }}>Terminal Motif</span>
                <strong style={{ color: "#f8fafc", fontSize: 22 }}>Race Control Layer</strong>
                <span style={{ color: "#94a3b8", fontSize: 12, lineHeight: 1.5 }}>Meetings feed into race workspaces: COMMAND, MAP, FORM, RUNNERS, FACTOR LAB and RESEARCH.</span>
              </div>
            </div>
          </div>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={titleStyle}><span>Today Meetings</span><em>select a meeting to inspect its race card</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
              {renderMeetingCards(todayShellMeetings.length ? todayShellMeetings : productShellMeetings.slice(0, 4), "No meetings loaded for today.")}
            </div>
          </section>

          <section style={{ display: "grid", gap: 12 }}>
            <div style={titleStyle}><span>Upcoming Meetings</span><em>future cards already in the governed universe</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
              {renderMeetingCards(upcomingShellMeetings, "No additional upcoming meetings loaded.")}
            </div>
          </section>
        </section>
      </div>
    );
  }

  if (productView === "MEETING") {
    return (
      <div style={pageStyle}>
        <section style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start", flexWrap: "wrap" }}>
            <div style={{ display: "grid", gap: 6 }}>
              <button type="button" style={{ ...shellButtonStyle, width: "fit-content", background: "rgba(15,23,42,.9)" }} onClick={() => setProductView("HOME")}>Back to Home</button>
              <div style={titleStyle}><span>{selectedShellMeeting?.trackName || "Meeting"}</span><em>{selectedShellMeeting?.meetingDate || "Date TBC"}</em></div>
              <div className="edgeiq-intel-race-meta">
                <span>{selectedShellMeeting?.raceCount || 0} races</span>
                <span>TRACK {selectedShellMeeting?.trackConditionLatest || "—"}</span>
                <span>RAIL {selectedShellMeeting?.railPositionLatest || "—"}</span>
                <span>{selectedShellMeeting?.meetingStatus || "FIELDS READY"}</span>
              </div>
            </div>
            <span style={fitBadge(selectedShellMeeting?.dataQualityStatus || "READY", "#34d399", "rgba(22,101,52,.18)", "1px solid rgba(52,211,153,.28)")}>{selectedShellMeeting?.dataQualityStatus || "READY"}</span>
          </div>

          <div style={{ marginTop: 14, overflowX: "auto" }}>
            <div style={{ minWidth: 880, display: "grid", gap: 7 }}>
              <div style={{ display: "grid", gridTemplateColumns: "70px 90px minmax(180px,1.2fr) 90px 130px 90px 130px 130px 120px", gap: 8, padding: "9px 10px", color: "#94a3b8", fontSize: 10, fontWeight: 1000, letterSpacing: ".08em", textTransform: "uppercase", borderBottom: "1px solid rgba(80,120,180,.35)" }}>
                <span>Race</span><span>Time</span><span>Title</span><span>Dist</span><span>Class</span><span>Field</span><span>Market</span><span>Rating</span><span>Open</span>
              </div>
              {selectedShellMeetingRaces.map((race) => (
                <div key={`shell-race-${race.raceKey}`} style={{ display: "grid", gridTemplateColumns: "70px 90px minmax(180px,1.2fr) 90px 130px 90px 130px 130px 120px", gap: 8, alignItems: "center", padding: "10px", border: "1px solid rgba(80,120,180,.22)", borderRadius: 8, background: "rgba(5,12,22,.82)" }}>
                  <strong style={{ color: "#f8fafc" }}>R{race.raceNoValue}</strong>
                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.raceTime}</span>
                  <span style={{ color: "#dbeafe", fontSize: 12, fontWeight: 850 }}>{race.raceTitle}</span>
                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.distanceValue}</span>
                  <span style={{ color: "#cbd5e1", fontSize: 12 }}>{race.raceClassValue}</span>
                  <span style={{ color: "#f8fafc", fontSize: 12, fontWeight: 900 }}>{race.fieldSize}</span>
                  <span style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 900 }}>{race.marketStateValue}</span>
                  <span style={{ color: "#34d399", fontSize: 11, fontWeight: 900 }}>{race.ratingReference}</span>
                  <button type="button" style={shellButtonStyle} onClick={() => openShellRace(race)}>Open Race</button>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    );
  }

'''

text = replace_once(
    text,
    '  if (!raceRows.length || !header) {\n',
    home_jsx + '  if (!raceRows.length || !header) {\n',
    "home and meeting views",
)

breadcrumb = r'''      <nav style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10, color: "#94a3b8", fontSize: 11, fontWeight: 900, letterSpacing: ".06em", textTransform: "uppercase" }}>
        <button type="button" style={{ ...shellButtonStyle, padding: "6px 8px", background: "rgba(15,23,42,.86)" }} onClick={() => setProductView("HOME")}>Home</button>
        <span>&gt;</span>
        <button type="button" style={{ ...shellButtonStyle, padding: "6px 8px", background: "rgba(15,23,42,.86)" }} onClick={() => setProductView("MEETING")}>{selectedShellMeeting?.trackName || track(header)}</button>
        <span>&gt;</span>
        <span style={{ color: "#dbeafe" }}>R{raceNo(header)}</span>
      </nav>

'''
text = replace_once(
    text,
    '  return (\n    <div style={pageStyle}>\n      <header style={headerStyle}>\n',
    '  return (\n    <div style={pageStyle}>\n' + breadcrumb + '      <header style={headerStyle}>\n',
    "race breadcrumbs",
)

TSX.write_text(text, encoding="utf-8")
REPORT.write_text("EDGEiQ PRODUCT SHELL UI V1\ncheckpoint=" + str(CHECKPOINT) + "\nstatus=PRODUCT_SHELL_UI_APPLIED\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n", encoding="utf-8")
print(REPORT)
