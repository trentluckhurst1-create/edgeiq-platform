from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\horse_racing_model\dashboard\racing-dashboard")
TSX = ROOT / "src" / "components" / "RaceIntelligenceScreen.tsx"
CHECKPOINT = ROOT / "src" / "components" / "RaceIntelligenceScreen_CHECKPOINT_PRODUCT_SHELL_HOME_V3_POLISH_20260629.tsx"
REPORT = ROOT / "public" / "data" / "edgeiq_product_shell_home_v3_polish_upgrade_report.txt"
text = TSX.read_text(encoding="utf-8")
CHECKPOINT.write_text(text, encoding="utf-8")
start = text.find('  if (productView === "HOME") {')
end = text.find('  if (productView === "MEETING") {', start)
if start == -1 or end == -1:
    raise SystemExit("HOME block not found")
new_home = r'''  if (productView === "HOME") {
    const productCapabilityCards = [
      { title: "Race Shape", text: "Speed maps, pressure, settling positions and pace advantage." },
      { title: "Form Intelligence", text: "Recovered ratings, last-five evidence, form figures and profile trends." },
      { title: "Runner Profiles", text: "Distance, condition, class, campaign and trajectory context." },
      { title: "Market Command", text: "Fair price, edge context and market movement intelligence." },
      { title: "Factor Lab", text: "Evidence breakdowns for users who want to inspect the why." },
    ];
    const terminalPreviewRows = [
      { label: "Evidence Layer", value: "Form, profile and market context", tone: "#7dd3fc" },
      { label: "Race Command", value: "Shape, pressure and runner roles", tone: "#34d399" },
      { label: "Decision Support", value: "Structured read, not tipping copy", tone: "#f5c451" },
    ];
    const renderMeetingCards = (meetings: typeof productShellMeetings, emptyLabel: string) => (
      meetings.length ? meetings.map((meeting) => (
        <article
          key={`shell-meeting-${meeting.meetingKey}`}
          style={{
            border: "1px solid rgba(80,120,180,.22)",
            borderRadius: 8,
            padding: 14,
            background: "linear-gradient(135deg, rgba(8,15,28,.94), rgba(5,12,22,.82))",
            display: "grid",
            gap: 12,
            alignContent: "start",
            minHeight: 0,
          }}
        >
          <div style={{ display: "grid", gap: 4 }}>
            <strong style={{ color: "#f8fafc", fontSize: 20, lineHeight: 1 }}>{meeting.trackName}</strong>
            <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 800 }}>{meeting.dayLabel} · {meeting.meetingDate || "Date TBC"}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 8 }}>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Races</span><strong style={miniValueStyle}>{meeting.raceCount}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Condition</span><strong style={miniValueStyle}>{meeting.trackConditionLatest}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>Rail</span><strong style={miniValueStyle}>{meeting.railPositionLatest}</strong></div>
            <div style={miniTileStyle}><span style={miniLabelStyle}>First Race</span><strong style={miniValueStyle}>{meeting.firstRaceTime}</strong></div>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <span style={{ color: "#94a3b8", fontSize: 11, fontWeight: 850 }}>Status: <strong style={{ color: "#dbeafe" }}>{meeting.meetingStatus}</strong></span>
            <button type="button" style={{ ...shellButtonStyle, minWidth: 118 }} onClick={() => openShellMeeting(meeting.meetingKey)}>View Meeting</button>
          </div>
        </article>
      )) : <div style={{ color: "#94a3b8", fontSize: 13 }}>{emptyLabel}</div>
    );

    return (
      <div style={{ ...pageStyle, paddingTop: 20 }}>
        <section style={{ ...panelStyle, display: "grid", gap: 28, alignContent: "start", padding: 22, background: "radial-gradient(circle at 82% 8%, rgba(52,211,153,.10), transparent 24%), radial-gradient(circle at 10% 16%, rgba(125,211,252,.10), transparent 28%), linear-gradient(135deg, rgba(8,15,28,.98), rgba(3,8,16,.95))" }}>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.05fr) minmax(320px,.78fr)", gap: 24, alignItems: "stretch" }}>
            <div style={{ display: "grid", gap: 16, alignContent: "center", minHeight: 330 }}>
              <div style={{ display: "grid", gap: 8 }}>
                <span style={{ color: "#34d399", fontSize: 11, fontWeight: 1000, letterSpacing: ".24em", textTransform: "uppercase" }}>Racing Intelligence Platform</span>
                <strong style={{ color: "#f8fafc", fontSize: 64, lineHeight: .9, letterSpacing: ".01em" }}>EDGEiQ</strong>
                <span style={{ color: "#dbeafe", fontSize: 22, fontWeight: 950 }}>Racing Intelligence Platform</span>
              </div>
              <p style={{ margin: 0, maxWidth: 700, color: "#dbe7f3", fontSize: 16, lineHeight: 1.65, fontWeight: 800 }}>
                Race-shape, form, market, runner and factor intelligence in one terminal.
              </p>
              <p style={{ margin: 0, maxWidth: 760, color: "#94a3b8", fontSize: 14, lineHeight: 1.72 }}>
                EDGEiQ is a decision-support platform, not a tipping service. It helps users understand how a race is likely to be run, where the evidence is strongest, and which runners deserve deeper analysis.
              </p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 4 }}>
                <button
                  type="button"
                  style={{ ...shellButtonStyle, minWidth: 150, padding: "12px 16px", background: "linear-gradient(135deg, rgba(14,165,233,.24), rgba(52,211,153,.18))" }}
                  onClick={() => selectedShellMeeting ? openShellMeeting(selectedShellMeeting.meetingKey) : updateProductView("MEETING")}
                >
                  Enter Terminal
                </button>
                <button
                  type="button"
                  style={{ ...shellButtonStyle, minWidth: 180, padding: "12px 16px", background: "rgba(15,23,42,.9)" }}
                  onClick={() => selectedShellMeeting ? openShellMeeting(selectedShellMeeting.meetingKey) : updateProductView("MEETING")}
                >
                  View Today's Meetings
                </button>
              </div>
            </div>

            <aside style={{ border: "1px solid rgba(80,120,180,.26)", borderRadius: 8, padding: 16, background: "linear-gradient(135deg, rgba(8,15,28,.96), rgba(5,12,22,.86))", display: "grid", gap: 14, alignContent: "center" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", borderBottom: "1px solid rgba(80,120,180,.24)", paddingBottom: 10 }}>
                <span style={{ color: "#7dd3fc", fontSize: 11, fontWeight: 1000, letterSpacing: ".14em", textTransform: "uppercase" }}>Terminal Preview</span>
                <span style={{ width: 52, height: 2, background: "linear-gradient(90deg, #34d399, #7dd3fc)" }} />
              </div>
              <div style={{ display: "grid", gap: 10 }}>
                {terminalPreviewRows.map((row) => (
                  <div key={`terminal-preview-${row.label}`} style={{ border: "1px solid rgba(80,120,180,.20)", borderRadius: 8, padding: "11px 12px", background: "rgba(2,6,23,.40)", display: "grid", gap: 4 }}>
                    <strong style={{ color: row.tone, fontSize: 12, fontWeight: 1000 }}>{row.label}</strong>
                    <span style={{ color: "#cbd5e1", fontSize: 12, lineHeight: 1.45 }}>{row.value}</span>
                  </div>
                ))}
              </div>
              <div style={{ display: "grid", gap: 7, opacity: .8 }}>
                <div style={{ height: 2, background: "linear-gradient(90deg, #34d399, #7dd3fc, transparent)", width: "82%" }} />
                <div style={{ height: 2, background: "linear-gradient(90deg, transparent, #7dd3fc)", width: "72%", justifySelf: "end" }} />
              </div>
            </aside>
          </div>

          <section style={{ display: "grid", gap: 14 }}>
            <div style={titleStyle}><span>What EDGEiQ Does</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12 }}>
              {productCapabilityCards.map((card) => (
                <article key={`product-capability-${card.title}`} style={{ border: "1px solid rgba(80,120,180,.20)", borderRadius: 8, padding: 15, minHeight: 118, background: "rgba(5,12,22,.68)", display: "grid", gap: 9, alignContent: "start" }}>
                  <strong style={{ color: "#dbeafe", fontSize: 13, fontWeight: 1000 }}>{card.title}</strong>
                  <span style={{ color: "#94a3b8", fontSize: 12.5, lineHeight: 1.55 }}>{card.text}</span>
                </article>
              ))}
            </div>
          </section>

          <section style={{ display: "grid", gap: 14 }}>
            <div style={titleStyle}><span>Today Meetings</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
              {renderMeetingCards(todayShellMeetings.length ? todayShellMeetings : productShellMeetings.slice(0, 4), "No meetings loaded for today.")}
            </div>
          </section>

          <section style={{ display: "grid", gap: 14 }}>
            <div style={titleStyle}><span>Upcoming Meetings</span><em style={{ color: "#64748b" }}>Future cards already loaded into EDGEiQ.</em></div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
              {renderMeetingCards(upcomingShellMeetings, "No additional upcoming meetings loaded.")}
            </div>
          </section>
        </section>
      </div>
    );
  }

'''
text = text[:start] + new_home + text[end:]
TSX.write_text(text, encoding="utf-8")
REPORT.write_text("EDGEiQ PRODUCT SHELL HOME V3 POLISH\ncheckpoint=" + str(CHECKPOINT) + "\nstatus=PRODUCT_SHELL_HOME_V3_POLISH_APPLIED\npricing_maths_changed=NO\nv6_1_changed=NO\nv7_2g2_changed=NO\n", encoding="utf-8")
print(REPORT)
