from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

tsx_path = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
css_path = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

tsx_backup = tsx_path.with_name(
    f"{tsx_path.stem}_CHECKPOINT_BEFORE_ALL_RUNNER_DEFAULT_{timestamp}{tsx_path.suffix}"
)
css_backup = css_path.with_name(
    f"{css_path.stem}_CHECKPOINT_BEFORE_FORM_GUIDE_UI_RECOVERY_{timestamp}{css_path.suffix}"
)

shutil.copy2(tsx_path, tsx_backup)
shutil.copy2(css_path, css_backup)

tsx = tsx_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------
# 1. Remove Fragment import because profiles will no longer be embedded
#    as conditional table rows.
# ---------------------------------------------------------------------

old_import = 'import { Fragment, useEffect, useMemo, useState } from "react";'
new_import = 'import { useEffect, useMemo, useState } from "react";'

if old_import not in tsx:
    raise SystemExit(
        "PATCH_ABORTED: expected React import was not found. "
        "No active files were changed."
    )

tsx = tsx.replace(old_import, new_import, 1)

# ---------------------------------------------------------------------
# 2. Replace single expanded-runner state with highlighted navigator state.
# ---------------------------------------------------------------------

old_state = '''  const [expandedRunnerId, setExpandedRunnerId] = useState<string | null>(null);
  const guide = useMemo(() => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace), [raceBook, field, meetingRaces, enrichedRace]);
  const runnerIds = useMemo(() => guide.runners.map((runner) => runner.id).join("|"), [guide.runners]);

  useEffect(() => {
    if (!guide.runners.length) {
      if (expandedRunnerId !== null) setExpandedRunnerId(null);
      return;
    }
    const withHistory = guide.runners.find((runner) => runner.recentRuns.length >= 3 && !runner.scratched);
    const fallback = guide.runners.find((runner) => !runner.scratched) ?? guide.runners[0];
    const preferred = withHistory ?? fallback;
    if (!expandedRunnerId || !guide.runners.some((runner) => runner.id === expandedRunnerId)) {
      setExpandedRunnerId(preferred.id);
    }
  }, [expandedRunnerId, guide.runners, runnerIds]);
'''

new_state = '''  const [highlightedRunnerId, setHighlightedRunnerId] = useState<string | null>(null);
  const guide = useMemo(() => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace), [raceBook, field, meetingRaces, enrichedRace]);

  const orderedRunners = useMemo(
    () =>
      [...guide.runners].sort((left, right) => {
        const leftNumber = Number.parseInt(String(left.no ?? "").replace(/[^0-9]/g, ""), 10);
        const rightNumber = Number.parseInt(String(right.no ?? "").replace(/[^0-9]/g, ""), 10);

        const leftValid = Number.isFinite(leftNumber);
        const rightValid = Number.isFinite(rightNumber);

        if (leftValid && rightValid && leftNumber !== rightNumber) {
          return leftNumber - rightNumber;
        }

        if (leftValid !== rightValid) {
          return leftValid ? -1 : 1;
        }

        return String(left.horse ?? "").localeCompare(String(right.horse ?? ""));
      }),
    [guide.runners],
  );

  const navigateToRunner = (runner: FormGuideRunnerDisplay) => {
    setHighlightedRunnerId(runner.id);

    window.requestAnimationFrame(() => {
      scrollToRunner(runner);
    });

    window.setTimeout(() => {
      setHighlightedRunnerId((current) => current === runner.id ? null : current);
    }, 1800);
  };

  useEffect(() => {
    setHighlightedRunnerId(null);
  }, [selectedRaceKey]);
'''

if old_state not in tsx:
    raise SystemExit(
        "PATCH_ABORTED: expected expanded-runner state block was not found. "
        "No active files were changed."
    )

tsx = tsx.replace(old_state, new_state, 1)

# ---------------------------------------------------------------------
# 3. Replace accordion table body with compact navigation rows only.
# ---------------------------------------------------------------------

old_body = '''          <tbody>
            {guide.runners.map((runner) => {
              const isExpanded = expandedRunnerId === runner.id;
              return (
                <Fragment key={runner.id}>
                  <tr className={`${runner.scratched ? "is-scratched" : ""} ${isExpanded ? "is-expanded" : ""}`.trim()}>
                    <td className="eiq-cell-no">{cleanDisplay(runner.no)}</td>
                    <td>{runner.silkUrl ? <img className="eiq-form-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-silk eiq-form-silk--fallback" aria-hidden="true" />}</td>
                    <td className="eiq-cell-last-five">{runner.lastFive.length ? <LastFiveStrip values={runner.lastFive} /> : DASH}</td>
                    <td><button type="button" className="eiq-form-runner-anchor eiq-form-runner-expand" aria-expanded={isExpanded} aria-controls={runnerProfileId(runner)} onClick={() => { const next = isExpanded ? null : runner.id; setExpandedRunnerId(next); if (!isExpanded) window.requestAnimationFrame(() => scrollToRunner(runner)); }}><strong>{cleanDisplay(runner.horse)}</strong>{runner.scratched ? <small>SCRATCHED</small> : null}</button></td>
                    <td>{cleanDisplay(runner.trainer)}</td>
                    <td>{cleanDisplay(runner.jockey)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.weight)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.barrier)}</td>
                    <td className="eiq-cell-days">{cleanDisplay(runner.daysSinceLastRun)}</td>
                    <td className="eiq-cell-epi">{cleanDisplay(runner.epi)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.earlySpeed)}</td>
                    <td className="eiq-cell-compact">{cleanDisplay(runner.late)}</td>
                    <td className="eiq-cell-suitability"><strong>{cleanDisplay(runner.suitabilityScore)}</strong><small>{cleanDisplay(runner.suitabilityLabel)}</small></td>
                    <td className="eiq-cell-momentum" data-direction={runner.formMomentumDirection}>{cleanDisplay(runner.formMomentum)}</td>
                    <td className="eiq-cell-price eiq-cell-market">{cleanDisplay(runner.marketPrice)}</td>
                    <td className="eiq-cell-price eiq-cell-edgeiq-price">{cleanDisplay(runner.edgeiqPrice)}</td>
                  </tr>
                  {isExpanded ? <tr className="eiq-form-expanded-row"><td colSpan={summaryColumns.length}><RunnerProfile runner={runner} /></td></tr> : null}
                </Fragment>
              );
            })}
          </tbody>'''

new_body = '''          <tbody>
            {orderedRunners.map((runner) => (
              <tr
                key={runner.id}
                className={`${runner.scratched ? "is-scratched" : ""} ${highlightedRunnerId === runner.id ? "is-targeted" : ""}`.trim()}
              >
                <td className="eiq-cell-no">{cleanDisplay(runner.no)}</td>
                <td>{runner.silkUrl ? <img className="eiq-form-silk" src={runner.silkUrl} alt={`${runner.horse} silks`} loading="lazy" /> : <span className="eiq-form-silk eiq-form-silk--fallback" aria-hidden="true" />}</td>
                <td className="eiq-cell-last-five">{runner.lastFive.length ? <LastFiveStrip values={runner.lastFive} /> : DASH}</td>
                <td>
                  <button
                    type="button"
                    className="eiq-form-runner-anchor eiq-form-runner-navigator"
                    aria-controls={runnerProfileId(runner)}
                    onClick={() => navigateToRunner(runner)}
                  >
                    <strong>{cleanDisplay(runner.horse)}</strong>
                    {runner.scratched ? <small>SCRATCHED</small> : null}
                  </button>
                </td>
                <td>{cleanDisplay(runner.trainer)}</td>
                <td>{cleanDisplay(runner.jockey)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.weight)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.barrier)}</td>
                <td className="eiq-cell-days">{cleanDisplay(runner.daysSinceLastRun)}</td>
                <td className="eiq-cell-epi">{cleanDisplay(runner.epi)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.earlySpeed)}</td>
                <td className="eiq-cell-compact">{cleanDisplay(runner.late)}</td>
                <td className="eiq-cell-suitability"><strong>{cleanDisplay(runner.suitabilityScore)}</strong><small>{cleanDisplay(runner.suitabilityLabel)}</small></td>
                <td className="eiq-cell-momentum" data-direction={runner.formMomentumDirection}>{cleanDisplay(runner.formMomentum)}</td>
                <td className="eiq-cell-price eiq-cell-market">{cleanDisplay(runner.marketPrice)}</td>
                <td className="eiq-cell-price eiq-cell-edgeiq-price">{cleanDisplay(runner.edgeiqPrice)}</td>
              </tr>
            ))}
          </tbody>'''

if old_body not in tsx:
    raise SystemExit(
        "PATCH_ABORTED: expected accordion table body was not found. "
        "No active files were changed."
    )

tsx = tsx.replace(old_body, new_body, 1)

# ---------------------------------------------------------------------
# 4. Add every runner dossier underneath the completed field table.
# ---------------------------------------------------------------------

old_after_table = '''      </div>

      <footer className="eiq-form-v3-footer">'''

new_after_table = '''      </div>

      <section
        className="eiq-form-all-runner-dossiers"
        data-region="all_runner_dossiers"
        aria-label="Complete runner form dossiers"
      >
        <header className="eiq-form-all-runner-dossiers__header">
          <div>
            <span>COMPLETE FIELD FORM</span>
            <h3>Every Runner</h3>
          </div>
          <p>Full governed profile and recent-form evidence in saddlecloth order.</p>
        </header>

        <div className="eiq-form-all-runner-dossiers__list">
          {orderedRunners.map((runner) => (
            <div
              key={`dossier-${runner.id}`}
              className={highlightedRunnerId === runner.id ? "is-targeted" : ""}
            >
              <RunnerProfile runner={runner} />
            </div>
          ))}
        </div>
      </section>

      <footer className="eiq-form-v3-footer">'''

if old_after_table not in tsx:
    raise SystemExit(
        "PATCH_ABORTED: expected insertion point after field table was not found. "
        "No active files were changed."
    )

tsx = tsx.replace(old_after_table, new_after_table, 1)

# ---------------------------------------------------------------------
# 5. Add final governed UI overrides.
# ---------------------------------------------------------------------

css_marker = "/* EDGEIQ_FORM_GUIDE_ALL_RUNNER_DEFAULT_V1 */"

css_addition = r'''

/* EDGEIQ_FORM_GUIDE_ALL_RUNNER_DEFAULT_V1 */

.eiq-race-form-guide--final-locked {
  width: 100%;
  max-width: none;
  background: #f5f8fc;
  padding: 18px 18px 36px;
}

.eiq-race-form-guide--final-locked .eiq-form-race-header--v3 {
  background: #ffffff;
  border: 1px solid #cbd9ea;
  border-top: 4px solid #0f5ea8;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(18, 55, 91, 0.07);
}

.eiq-race-form-guide--final-locked .eiq-form-summary-table--final-locked {
  background: #ffffff;
  border: 1px solid #c5d5e8;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(18, 55, 91, 0.06);
  overflow-x: auto;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked th {
  min-height: 42px;
  padding: 11px 8px;
  background: #eaf2fb;
  color: #183b62;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked td {
  padding: 11px 8px;
  color: #26394d;
  font-size: 12px;
  vertical-align: middle;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr {
  transition: background 140ms ease, box-shadow 140ms ease;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr:hover > td {
  background: #f0f6fd;
}

.eiq-race-form-guide--final-locked
.eiq-form-summary-table--final-locked tbody tr.is-targeted > td {
  background: #dcecff;
  box-shadow: inset 0 1px 0 #8db9e7, inset 0 -1px 0 #8db9e7;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator {
  width: 100%;
  min-width: 130px;
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: #123f70;
  text-align: left;
  cursor: pointer;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator strong {
  font-size: 13px;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-navigator:hover strong {
  color: #0874ca;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.eiq-form-all-runner-dossiers {
  margin-top: 24px;
}

.eiq-form-all-runner-dossiers__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 12px;
  padding: 14px 18px;
  background: #ffffff;
  border: 1px solid #c5d5e8;
  border-left: 5px solid #0f5ea8;
  border-radius: 6px;
}

.eiq-form-all-runner-dossiers__header span {
  display: block;
  margin-bottom: 3px;
  color: #0f5ea8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.eiq-form-all-runner-dossiers__header h3 {
  margin: 0;
  color: #122d49;
  font-size: 21px;
  line-height: 1.1;
}

.eiq-form-all-runner-dossiers__header p {
  margin: 0;
  color: #617389;
  font-size: 12px;
}

.eiq-form-all-runner-dossiers__list {
  display: grid;
  gap: 18px;
}

.eiq-form-all-runner-dossiers__list > div {
  scroll-margin-top: 120px;
  transition: transform 160ms ease, filter 160ms ease;
}

.eiq-form-all-runner-dossiers__list > div.is-targeted {
  transform: translateY(-2px);
  filter: drop-shadow(0 0 7px rgba(15, 94, 168, 0.28));
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-sheet {
  margin: 0;
  background: #ffffff;
  border: 1px solid #b9cde3;
  border-top: 4px solid #1264ad;
  border-radius: 7px;
  box-shadow: 0 3px 11px rgba(18, 55, 91, 0.08);
  overflow: hidden;
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-sheet.is-scratched {
  opacity: 0.58;
  filter: grayscale(0.45);
}

.eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
  min-height: 94px;
  padding: 15px 18px;
  background: linear-gradient(90deg, #f5f9fe 0%, #ffffff 48%);
  border-bottom: 1px solid #cbd9e8;
}

.eiq-race-form-guide--final-locked .eiq-form-detail-silk {
  width: 54px;
  height: 62px;
  object-fit: contain;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity strong {
  gap: 10px;
  color: #112f4f;
  font-size: 22px;
  line-height: 1.15;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity strong em {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  flex: 0 0 34px;
  border-radius: 4px;
  background: #0f5ea8;
  color: #ffffff;
  font-size: 17px;
  font-style: normal;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-v3-runner-identity p {
  margin-top: 6px;
  color: #53677c;
  font-size: 12px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
  gap: 0;
  background: #ffffff;
  border: 1px solid #c8d6e5;
  border-radius: 5px;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip > div {
  min-width: 82px;
  padding: 10px 11px;
  border-right: 1px solid #d9e3ed;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip > div:last-child {
  border-right: 0;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip dt {
  color: #61758b;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.eiq-race-form-guide--final-locked .eiq-form-final-current-strip dd {
  margin-top: 3px;
  color: #153c64;
  font-size: 16px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
  grid-template-columns: minmax(190px, 0.85fr) minmax(680px, 3fr) minmax(220px, 1fr);
  gap: 12px;
  padding: 14px;
  background: #f7f9fc;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match,
.eiq-race-form-guide--final-locked .eiq-form-final-dossier-main,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read {
  min-height: 100%;
  background: #ffffff;
  border: 1px solid #c9d7e6;
  border-radius: 5px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-today-match h3,
.eiq-race-form-guide--final-locked .eiq-form-final-profile-matrix header,
.eiq-race-form-guide--final-locked .eiq-form-final-match-read h3,
.eiq-race-form-guide--final-locked .eiq-form-final-recent-form header {
  min-height: 35px;
  padding: 10px 12px;
  background: #eaf2fb;
  border-bottom: 1px solid #c5d5e8;
  color: #173f69;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.05em;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell {
  min-height: 35px;
  padding: 8px 7px;
  font-size: 11px;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell--head {
  color: #1c456e;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked .eiq-form-final-profile-cell.is-today {
  background: #e1effe;
  color: #0a4e8b;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked .eiq-form-final-recent-form {
  margin: 0 14px 14px;
  background: #ffffff;
  border: 1px solid #c9d7e6;
  border-radius: 5px;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 {
  overflow-x: auto;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 table {
  min-width: 1450px;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 th {
  padding: 9px 8px;
  background: #f1f5fa;
  color: #294d72;
  font-size: 10px;
  font-weight: 900;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked .eiq-form-run-table--v4 td {
  padding: 9px 8px;
  color: #30455a;
  font-size: 11px;
  white-space: nowrap;
}

.eiq-race-form-guide--final-locked .eiq-form-final-sectional-legend {
  margin: -3px 14px 14px;
  padding: 9px 12px;
  background: #f5f8fc;
  border: 1px solid #d4dfeb;
  border-radius: 4px;
  color: #5b6f84;
}

@media (max-width: 1450px) {
  .eiq-race-form-guide--final-locked .eiq-form-final-runner-header {
    grid-template-columns: auto minmax(260px, 1fr);
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-current-strip {
    grid-column: 1 / -1;
    width: 100%;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns: minmax(180px, 0.8fr) minmax(620px, 3fr);
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-match-read {
    grid-column: 1 / -1;
  }
}

@media (max-width: 980px) {
  .eiq-race-form-guide--final-locked {
    padding-inline: 8px;
  }

  .eiq-form-all-runner-dossiers__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns: 1fr;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-match-read {
    grid-column: auto;
  }
}
'''

if css_marker not in css:
    css = css.rstrip() + css_addition + "\n"

tsx_path.write_text(tsx, encoding="utf-8", newline="\n")
css_path.write_text(css, encoding="utf-8", newline="\n")

print(f"UPDATED_TSX={tsx_path}")
print(f"UPDATED_CSS={css_path}")
print(f"CHECKPOINT_TSX={tsx_backup}")
print(f"CHECKPOINT_CSS={css_backup}")
print("FORM_GUIDE_ALL_RUNNER_DEFAULT_AND_UI_RECOVERY_PASS")
