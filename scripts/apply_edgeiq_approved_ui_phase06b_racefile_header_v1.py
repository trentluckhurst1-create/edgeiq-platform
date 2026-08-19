from pathlib import Path
import shutil
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
RACE = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceWorkspace.tsx"
CHECKPOINT_ROOT = ROOT / "docs" / "full-product-implementation" / "checkpoints"
MARKER = "/* EDGEIQ APPROVED UI PHASE 06B RACEFILE HEADER */"


def checkpoint() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CHECKPOINT_ROOT / f"CHECKPOINT_APPROVED_UI_PHASE06B_RACEFILE_HEADER_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in (CSS, RACE):
        shutil.copy2(path, out / path.name)
    return out


def patch_race_workspace() -> None:
    text = RACE.read_text(encoding="utf-8")
    old = '''  const formGuide = useMemo(
    () => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace),
    [raceBook, field, meetingRaces, enrichedRace],
  );

  return (
    <section className="eiq-race-workspace">
      <div className="eiq-workspace-breadcrumb">
        <button type="button" onClick={onBackToMeeting}>{clean(official.meeting)}</button>
        <span>/</span>
        <strong>R{clean(official.raceNumber)}</strong>
      </div>

      <nav className="eiq-context-tabs" aria-label="Race workspace navigation">
        {tabs.map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>
'''
    new = '''  const formGuide = useMemo(
    () => normaliseFormGuideRace(raceBook, field, meetingRaces, enrichedRace),
    [raceBook, field, meetingRaces, enrichedRace],
  );
  const activeTabClass = tab.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const raceNumber = clean(official.raceNumber);
  const meetingName = clean(official.meeting);
  const raceClass = clean(official.class) || clean(official.raceClass);
  const distance = clean(official.distance);
  const trackCondition = clean(official.trackCondition) || clean(official.condition);
  const raceDate = clean(official.date) || clean(official.raceDate);
  const raceTime = clean(official.time) || clean(official.localTime);
  const surface = clean(official.surface) || clean(official.trackType);
  const prizeMoney = clean(official.prizeMoney) || clean(official.totalPrizeMoney);
  const raceTitle = clean(official.raceName) || clean(official.name);
  const showRaceFileHeader = tab !== "RACE";
  const raceHeaderMeta = [
    ["LOCATION", meetingName],
    ["DATE", raceDate],
    ["TIME", raceTime],
    ["DISTANCE", distance],
    ["SURFACE", surface],
    ["PRIZE MONEY", prizeMoney],
  ].filter((item) => item[1]);

  return (
    <section className={`eiq-race-workspace eiq-race-workspace--${activeTabClass}`}>
      {showRaceFileHeader ? (
        <header className="eiq-approved-racefile-header">
          <div className="eiq-approved-racefile-header__crumb">
            <button type="button" onClick={onBackToMeeting}>MEETINGS</button>
            <span>{meetingName}</span>
            <span>RACE {raceNumber}</span>
            <strong>{tab}</strong>
          </div>
          <div className="eiq-approved-racefile-header__title">
            <div>
              <h1>
                <span>Race {raceNumber}</span>
                {raceTitle ? <strong>{raceTitle}</strong> : null}
                {raceClass ? <em>{raceClass}</em> : null}
              </h1>
            </div>
            <button type="button" className="eiq-approved-button" onClick={onBackToMeeting}>Back to Races</button>
          </div>
          <dl className="eiq-approved-racefile-header__meta">
            {raceHeaderMeta.map(([label, value]) => (
              <div key={`${label}-${value}`}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
            {trackCondition ? (
              <div>
                <dt>TRACK</dt>
                <dd>{trackCondition}</dd>
              </div>
            ) : null}
          </dl>
        </header>
      ) : null}

      <nav className="eiq-context-tabs" aria-label="Race workspace navigation">
        {tabs.map((item) => (
          <button key={item} type="button" className={tab === item ? "is-active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>
'''
    if old not in text:
        raise SystemExit("Expected RaceWorkspace render block not found; source changed unexpectedly.")
    RACE.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def patch_css() -> None:
    text = CSS.read_text(encoding="utf-8")
    block = f'''

{MARKER}
.eiq-race-workspace > .eiq-context-tabs {{
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  min-height: 41px;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 5px;
  overflow: hidden;
  background: #ffffff;
}}

.eiq-race-workspace > .eiq-context-tabs button {{
  border: 0;
  border-right: 1px solid var(--eiq-approved-line);
  background: transparent;
  color: var(--eiq-approved-navy);
  font: inherit;
  font-size: 11px;
  font-weight: 900;
  cursor: pointer;
}}

.eiq-race-workspace > .eiq-context-tabs button:last-child {{
  border-right: 0;
}}

.eiq-race-workspace > .eiq-context-tabs button.is-active {{
  color: var(--eiq-approved-blue);
  background: #f8fbff;
  box-shadow: inset 0 -3px 0 var(--eiq-approved-blue);
}}

.eiq-race-workspace--race > .eiq-context-tabs {{
  display: none;
}}

.eiq-approved-racefile-header {{
  display: grid;
  gap: 8px;
  padding: 0 2px 10px;
  border-bottom: 1px solid var(--eiq-approved-line);
}}

.eiq-approved-racefile-header__crumb {{
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 18px;
  color: var(--eiq-approved-blue);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}}

.eiq-approved-racefile-header__crumb button {{
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0;
  font: inherit;
  cursor: pointer;
}}

.eiq-approved-racefile-header__crumb span::before,
.eiq-approved-racefile-header__crumb strong::before {{
  content: ">";
  margin-right: 8px;
  color: var(--eiq-approved-muted);
}}

.eiq-approved-racefile-header__title {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}}

.eiq-approved-racefile-header__title h1 {{
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: 22px;
  color: var(--eiq-approved-blue);
  font-size: 25px;
  line-height: 1.1;
  font-weight: 900;
}}

.eiq-approved-racefile-header__title h1 strong {{
  color: var(--eiq-approved-navy);
  font-size: 22px;
  font-weight: 900;
}}

.eiq-approved-racefile-header__title h1 em {{
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  border-radius: 5px;
  background: var(--eiq-approved-blue-mid);
  color: var(--eiq-approved-blue);
  padding: 0 9px;
  font-size: 13px;
  font-style: normal;
  font-weight: 900;
}}

.eiq-approved-racefile-header__meta {{
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 5px;
  background: #ffffff;
  overflow: hidden;
}}

.eiq-approved-racefile-header__meta div {{
  min-width: 118px;
  min-height: 40px;
  display: grid;
  align-content: center;
  gap: 2px;
  padding: 5px 12px;
  border-right: 1px solid var(--eiq-approved-line);
}}

.eiq-approved-racefile-header__meta div:last-child {{
  border-right: 0;
}}

.eiq-approved-racefile-header__meta dt {{
  color: var(--eiq-approved-muted);
  font-size: 9px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: 0.04em;
}}

.eiq-approved-racefile-header__meta dd {{
  margin: 0;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  line-height: 1.1;
  font-weight: 900;
}}

.eiq-race-workspace:not(.eiq-race-workspace--race) .eiq-race-form-guide--v4 .eiq-form-race-header {{
  display: none;
}}

.eiq-race-workspace:not(.eiq-race-workspace--race) .eiq-race-form-guide--v4 {{
  gap: 6px;
}}

.eiq-race-workspace:not(.eiq-race-workspace--race) .eiq-race-form-guide--v4 .eiq-form-race-selector {{
  justify-content: flex-start;
}}
'''
    if MARKER in text:
        before = text[: text.index(MARKER)].rstrip()
        CSS.write_text(before + block, encoding="utf-8", newline="\n")
    else:
        CSS.write_text(text.rstrip() + block, encoding="utf-8", newline="\n")


def main() -> None:
    cp = checkpoint()
    patch_race_workspace()
    patch_css()
    print(f"checkpoint={cp}")
    print("files_changed:")
    print(f"- {RACE}")
    print(f"- {CSS}")
    print("EDGEIQ_APPROVED_UI_PHASE06B_RACEFILE_HEADER_PASS")


if __name__ == "__main__":
    main()
