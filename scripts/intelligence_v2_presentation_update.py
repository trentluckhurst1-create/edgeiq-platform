from pathlib import Path

path = Path(r".\src\components\RaceIntelligenceScreen.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
'''<PanelTitle kicker="RACE FIELD" title="Execution discipline board" meta="saddlecloth order | truth, suppression and trust are live engine outputs" />''',
'''<PanelTitle kicker="RUNNER BOARD" title="Decision board" meta="saddlecloth order | live, fair, edge and decision signals" />'''
)

text = text.replace(
'''<PanelTitle kicker="RACE INTELLIGENCE" title="Market truth and tactical read" meta="only populated discipline signals shown" />''',
'''<PanelTitle kicker="RACE READ" title="Tactical and market read" meta="only populated decision signals shown" />'''
)

text = text.replace(
'''<PanelTitle kicker="SPEED MAP" title="Settling-position map" meta={[projectedShape, pressure].filter(has).join(" | ")} />''',
'''<PanelTitle kicker="RACE SHAPE" title="Speed map" meta={[projectedShape, pressure].filter(has).join(" | ")} />'''
)

text = text.replace(
'''<ProfileSection title="Execution Summary" items={executionSummary} narrative />
            <ProfileSection title="Form Snapshot" items={formItems} />
            <ProfileSection title="Tactical Read" items={tacticalRead} />''',
'''<ProfileSection title="Decision" items={executionSummary} narrative />
            <ProfileSection title="Profile" items={formItems} />
            <ProfileSection title="Race Fit" items={tacticalRead} />'''
)

text = text.replace(
'''<summary><span>Deep Form / Ratings / Profile</span><strong>{clean(selectedRunner?.horse)}</strong></summary>''',
'''<summary><span>Form + Ratings</span><strong>{clean(selectedRunner?.horse)}</strong></summary>'''
)

text = text.replace(
'''<summary><span>Execution Reasoning</span><strong>{executionFeedRows?.length ? `${executionFeedRows.length} rows` : "collapsed"}</strong></summary>''',
'''<summary><span>Why</span><strong>{executionFeedRows?.length ? `${executionFeedRows.length} signals` : "collapsed"}</strong></summary>'''
)

form_block = '''          {guideRows.length ? (
            <section className="race-panel race-form-guide-panel" aria-label="Selected runner form guide">
              <PanelTitle kicker="FORM GUIDE" title={clean(selectedRunner?.horse) || "Selected runner"} meta="last five official starts" />
              <FormGuide rows={guideRows} />
            </section>
          ) : null}

          {raceRead.length ? (
            <section className="race-panel race-read-panel" aria-label="Race execution read">
              <PanelTitle kicker="RACE READ" title="Tactical and market read" meta="only populated decision signals shown" />
              <InfoGrid items={raceRead} variant="read" />
            </section>
          ) : null}

          <section className="race-panel race-map-panel" aria-label="Speed map and race shape">
            <PanelTitle kicker="RACE SHAPE" title="Speed map" meta={[projectedShape, pressure].filter(has).join(" | ")} />
            <SpeedMapTab
              data={currentSpeedRows}
              runners={activeField}
              paceRows={currentPacePressureRows}
              raceShape={currentRaceShapeRow}
              selectedMeeting={currentMeeting?.track}
              selectedHorse={selectedRunner?.horse ?? ""}
              biasProfile={trackBiasRows}
              raceDistance={currentRace?.distance ?? null}
              trackCondition={currentRace?.todayTrackCondition ?? ""}
              onSelectHorse={(horse: string) => {
                const found = field.find((row) => sameHorse(row, horse, compactKey));
                if (found) selectRunner(found);
              }}
            />
          </section>'''

new_block = '''          <section className="race-panel race-map-panel" aria-label="Speed map and race shape">
            <PanelTitle kicker="RACE SHAPE" title="Speed map" meta={[projectedShape, pressure].filter(has).join(" | ")} />
            <SpeedMapTab
              data={currentSpeedRows}
              runners={activeField}
              paceRows={currentPacePressureRows}
              raceShape={currentRaceShapeRow}
              selectedMeeting={currentMeeting?.track}
              selectedHorse={selectedRunner?.horse ?? ""}
              biasProfile={trackBiasRows}
              raceDistance={currentRace?.distance ?? null}
              trackCondition={currentRace?.todayTrackCondition ?? ""}
              onSelectHorse={(horse: string) => {
                const found = field.find((row) => sameHorse(row, horse, compactKey));
                if (found) selectRunner(found);
              }}
            />
          </section>

          {guideRows.length ? (
            <section className="race-panel race-form-guide-panel" aria-label="Selected runner form guide">
              <PanelTitle kicker="FORM GUIDE" title={clean(selectedRunner?.horse) || "Selected runner"} meta="last five official starts" />
              <FormGuide rows={guideRows} />
            </section>
          ) : null}

          {raceRead.length ? (
            <section className="race-panel race-read-panel" aria-label="Race execution read">
              <PanelTitle kicker="RACE READ" title="Tactical and market read" meta="only populated decision signals shown" />
              <InfoGrid items={raceRead} variant="read" />
            </section>
          ) : null}'''

if form_block not in text:
    raise SystemExit("Could not find layout block. No changes made.")

text = text.replace(form_block, new_block)

path.write_text(text, encoding="utf-8")
print("INTELLIGENCE V2 PRESENTATION UPDATE COMPLETE")
