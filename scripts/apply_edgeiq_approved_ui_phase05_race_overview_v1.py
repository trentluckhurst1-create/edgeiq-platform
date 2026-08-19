from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHECKPOINT = ROOT / "docs" / "full-product-implementation" / "checkpoints" / f"CHECKPOINT_APPROVED_UI_PHASE05_RACE_OVERVIEW_{STAMP}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def checkpoint(paths: list[Path]) -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            target = CHECKPOINT / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


TSX = """import { useEffect, useMemo, useState } from "react";
import { buildRaceIntelligenceViewModel } from "../services/raceWorkspaceViewModel";
import {
  findCurrentRaceIntelligenceRace,
  loadCurrentRaceIntelligenceFeed,
  type CurrentRaceIntelligenceRace,
} from "../services/currentRaceIntelligenceFeed";
import type { FormGuideRaceDisplay } from "../services/formGuideNormaliser";

type RaceIntelligenceWorkspaceProps = {
  raceBook: any;
  field: any[];
  formGuide?: FormGuideRaceDisplay | null;
  raceKey?: string | null;
  meetingRaces?: any[];
  clean: (value: any) => string;
};

function text(value: unknown, fallback = "Unavailable"): string {
  const valueText = String(value ?? "").replace(/\\s+/g, " ").trim();
  if (!valueText || valueText === "-" || ["null", "undefined", "none", "n/a", "na"].includes(valueText.toLowerCase())) return fallback;
  return valueText;
}

function firstValue(source: unknown, keys: string[]): unknown {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) {
    const value = key.split(".").reduce((acc: any, part) => acc?.[part], source as any);
    if (value !== undefined && value !== null && String(value).trim() !== "") return value;
  }
  return undefined;
}

function money(value: unknown): string {
  const raw = text(value, "").replace(/[$,]/g, "");
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) return "";
  return `$${parsed.toLocaleString("en-AU", { maximumFractionDigits: 0 })}`;
}

function Silk({ src, runner }: { src: string; runner: string }) {
  return src ? <img className="eiq-approved-race__silk" src={src} alt={`${runner} silks`} loading="lazy" /> : <span className="eiq-approved-race__silk is-empty" aria-hidden="true" />;
}

export function RaceIntelligenceWorkspace({ raceBook, field, formGuide, raceKey, meetingRaces = [], clean }: RaceIntelligenceWorkspaceProps) {
  const [intelligenceRace, setIntelligenceRace] = useState<CurrentRaceIntelligenceRace | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "loaded" | "unavailable">("loading");

  useEffect(() => {
    let cancelled = false;
    setLoadState("loading");
    loadCurrentRaceIntelligenceFeed()
      .then((payload) => {
        if (cancelled) return;
        setIntelligenceRace(findCurrentRaceIntelligenceRace(payload, raceKey));
        setLoadState("loaded");
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Current race intelligence feed unavailable", error);
          setIntelligenceRace(null);
          setLoadState("unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [raceKey]);

  const model = useMemo(
    () => buildRaceIntelligenceViewModel({ raceBook, field, formGuide, intelligenceRace }),
    [raceBook, field, formGuide, intelligenceRace],
  );

  const official = raceBook?.official ?? {};
  const raceSource = raceBook?.source ?? {};
  const meeting = clean(official.meeting);
  const raceNo = clean(official.raceNumber);
  const raceName = clean(official.raceName) || `Race ${raceNo}`;
  const raceClass = clean(official.raceClass) || clean(firstValue(raceSource, ["raceClass", "class"]));
  const distance = clean(official.distance) || clean(firstValue(raceSource, ["distance"]));
  const surface = clean(firstValue(official, ["surface"])) || clean(firstValue(raceSource, ["surface", "trackSurface"])) || "Turf";
  const trackCondition = clean(official.trackCondition) || clean(firstValue(raceSource, ["trackCondition", "condition", "conditions"]));
  const rail = clean(official.rail) || clean(firstValue(raceSource, ["rail", "railPosition"]));
  const raceTime = clean(official.raceTime) || clean(official.officialRaceTime) || clean(firstValue(raceSource, ["raceTime", "time"]));
  const date = clean(official.date) || clean(official.meetingDate) || clean(firstValue(raceSource, ["date", "raceDate"]));
  const prizeMoney = money(firstValue(raceSource, ["prizeMoney", "prizemoney", "totalPrizeMoney"]) ?? official.prizeMoney);
  const weather = clean(firstValue(raceSource, ["weather", "weatherCondition", "forecast"]));
  const wind = clean(firstValue(raceSource, ["wind", "windSpeed", "windSpeedKmh"]));
  const temperature = clean(firstValue(raceSource, ["temperature", "temperatureC", "temp"]));
  const humidity = clean(firstValue(raceSource, ["humidity", "humidityPct"]));
  const rain24 = clean(firstValue(raceSource, ["rain24h", "rain24hMm", "rainfall24h"]));
  const rain7 = clean(firstValue(raceSource, ["rain7d", "rain7dMm", "rainfall7d"]));
  const penetrometer = clean(firstValue(raceSource, ["penetrometer"]));
  const status = clean(firstValue(official, ["status"]) ?? firstValue(raceSource, ["status"]));

  const raceSummaryRows = [
    ["Race", raceNo],
    ["Name", raceName],
    ["Class", raceClass],
    ["Distance", distance],
    ["Prize Money", prizeMoney],
    ["Surface", surface],
    ["Rail", rail],
    ["Track Rating", trackCondition],
    ["First Race", raceTime],
    ["Last Race", clean(firstValue(raceSource, ["lastRaceTime"]))],
  ];

  const conditionRows = [
    ["Track Rating", trackCondition],
    ["Rail Position", rail],
    ["Track Bias", clean(firstValue(raceSource, ["trackBias", "bias"]))],
    ["Wind", wind],
    ["Temperature", temperature],
    ["Humidity", humidity],
    ["Rain (24h)", rain24],
    ["Rain (7d)", rain7],
    ["Penetrometer", penetrometer],
  ];

  const meetingRows = [
    ["Track Type", surface],
    ["Track Circumference", clean(firstValue(raceSource, ["trackCircumference", "circumference"]))],
    ["Straight", clean(firstValue(raceSource, ["straightLength", "straight"]))],
    ["Direction", clean(firstValue(raceSource, ["direction"]))],
    ["Rail Position", rail],
    ["Penetrometer", penetrometer],
    ["Irrigation (24h)", clean(firstValue(raceSource, ["irrigation24h", "irrigation24hMm"]))],
    ["Rain (7 days)", rain7],
    ["Wind", wind],
    ["Temperature", temperature],
    ["Humidity", humidity],
    ["Pressure", clean(intelligenceRace?.pressure ?? firstValue(raceSource, ["pressure"]))],
  ];

  return (
    <section className="eiq-approved-race" aria-label="Race overview">
      <header className="eiq-approved-race__context">
        <div>
          <p>MEETINGS <span>›</span> {text(meeting, "Meeting").toUpperCase()} <span>›</span> RACE {text(raceNo, "")}</p>
          <h1>Race {text(raceNo, "")} <strong>{text(raceName, "Race")}</strong> {raceClass ? <em>{raceClass}</em> : null}</h1>
          <div className="eiq-approved-race__meta">
            <span>{text(meeting, "Meeting")}</span>
            <span>{text(date, "Date unavailable")}</span>
            <span>{text(raceTime, "Time unavailable")}</span>
            <span>{text(distance, "Distance unavailable")}</span>
            <span>{text(surface, "Surface unavailable")}</span>
            <span>Prizemoney: {text(prizeMoney, "Unavailable")}</span>
            <span>{text(weather || trackCondition, "Weather unavailable")}</span>
          </div>
        </div>
        <button className="eiq-approved-button" type="button">BACK TO RACES</button>
      </header>

      <div className="eiq-approved-race__tabs" aria-label="Race overview navigation">
        {["RACE OVERVIEW", "FIELD & RUNNERS", "FORM GUIDE", "MAP", "MARKET", "OVERVIEW", "INSIGHTS", "RESULTS"].map((item, index) => (
          <span key={item} className={index === 0 ? "is-active" : ""}>{item}</span>
        ))}
      </div>

      <section className="eiq-approved-race__grid">
        <article className="eiq-approved-race__panel eiq-approved-race__summary">
          <h2>RACE SUMMARY</h2>
          <dl>
            {raceSummaryRows.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{text(value)}</dd></div>
            ))}
          </dl>
        </article>

        <article className="eiq-approved-race__panel eiq-approved-race__conditions">
          <h2>RACE CONDITIONS</h2>
          <dl>
            {conditionRows.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{text(value)}</dd></div>
            ))}
          </dl>
        </article>

        <aside className="eiq-approved-race__panel eiq-approved-race__meeting">
          <h2>MEETING INFORMATION</h2>
          <dl>
            {meetingRows.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{text(value)}</dd></div>
            ))}
          </dl>
        </aside>

        <article className="eiq-approved-race__panel eiq-approved-race__races">
          <h2>RACES AT THIS MEETING</h2>
          <div className="eiq-approved-race__table-wrap">
            <table className="eiq-approved-table">
              <thead>
                <tr>
                  <th>RACE</th>
                  <th>TIME</th>
                  <th>NAME</th>
                  <th>DISTANCE</th>
                  <th>CLASS</th>
                  <th>PRIZEMONEY</th>
                  <th>CONDITIONS</th>
                  <th>STATUS</th>
                  <th>VIEW</th>
                </tr>
              </thead>
              <tbody>
                {meetingRaces.length ? (
                  meetingRaces.map((race: any, index: number) => (
                    <tr key={race?.raceKey ?? index}>
                      <td>{text(race?.raceNumber ?? index + 1)}</td>
                      <td>{text(race?.raceTime)}</td>
                      <td><strong>{text(race?.raceName, `Race ${index + 1}`)}</strong></td>
                      <td>{text(race?.distance)}</td>
                      <td>{text(race?.raceClass)}</td>
                      <td>{text(money(firstValue(race?.source, ["prizeMoney", "prizemoney", "totalPrizeMoney"])), "Unavailable")}</td>
                      <td>{text(race?.trackCondition ?? trackCondition)}</td>
                      <td><span className="eiq-approved-pill">{text(race?.status ?? status, "Unavailable")}</span></td>
                      <td>View</td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={9}>Race list is unavailable for this meeting.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <footer>
            <strong>{meetingRaces.length ? `${meetingRaces.length} races` : "Race list unavailable"}</strong>
            <span>Current</span>
            <span>Completed</span>
            <span>Abandoned</span>
            <span>Postponed</span>
          </footer>
        </article>

        <aside className="eiq-approved-race__panel eiq-approved-race__actions">
          <h2>QUICK ACTIONS</h2>
          {["Download Race Card", "Print Race Card", "Add Race Notes", "Compare Races"].map((item) => (
            <button key={item} type="button">{item}</button>
          ))}
        </aside>
      </section>

    </section>
  );
}
"""


CSS_APPEND = r"""
/* EDGEIQ APPROVED UI PHASE 05 RACE OVERVIEW */
.eiq-race-workspace {
  display: grid;
  gap: 12px;
}

.eiq-race-workspace > .eiq-workspace-breadcrumb {
  display: none;
}

.eiq-race-workspace > .eiq-context-tabs {
  display: none;
}

.eiq-approved-race {
  display: grid;
  gap: 14px;
  color: var(--eiq-approved-text);
}

.eiq-approved-race__context {
  min-height: 118px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
  padding: 0 6px 12px;
  border-bottom: 1px solid var(--eiq-approved-line);
}

.eiq-approved-race__context p {
  margin: 0 0 16px;
  color: var(--eiq-approved-navy);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.eiq-approved-race__context p span {
  color: var(--eiq-approved-blue);
  margin: 0 8px;
}

.eiq-approved-race__context h1 {
  margin: 0;
  color: var(--eiq-approved-blue);
  font-size: 28px;
  line-height: 1.1;
  font-weight: 900;
}

.eiq-approved-race__context h1 strong {
  margin-left: 18px;
  color: var(--eiq-approved-navy);
  font-weight: 900;
}

.eiq-approved-race__context h1 em {
  display: inline-flex;
  height: 25px;
  align-items: center;
  margin-left: 12px;
  border-radius: 5px;
  background: var(--eiq-approved-blue-mid);
  color: var(--eiq-approved-blue);
  padding: 0 10px;
  font-size: 14px;
  font-style: normal;
  font-weight: 900;
  vertical-align: middle;
}

.eiq-approved-race__meta {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0;
  color: var(--eiq-approved-navy);
  font-size: 13px;
  font-weight: 700;
}

.eiq-approved-race__meta span {
  padding: 0 18px;
  border-left: 1px solid var(--eiq-approved-line);
}

.eiq-approved-race__meta span:first-child {
  padding-left: 0;
  border-left: 0;
}

.eiq-approved-race__context > button {
  margin-top: 8px;
}

.eiq-approved-race__tabs {
  min-height: 56px;
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  align-items: stretch;
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.eiq-approved-race__tabs span {
  display: grid;
  place-items: center;
  border-right: 1px solid var(--eiq-approved-line);
  color: var(--eiq-approved-navy);
  font-size: 12px;
  font-weight: 900;
  text-align: center;
}

.eiq-approved-race__tabs span:last-child {
  border-right: 0;
}

.eiq-approved-race__tabs span.is-active {
  color: var(--eiq-approved-blue);
  box-shadow: inset 0 -3px 0 var(--eiq-approved-blue);
  background: #f8fbff;
}

.eiq-approved-race__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr) 352px;
  gap: 14px;
  align-items: start;
}

.eiq-approved-race__panel,
.eiq-approved-race__runner-board {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 6px;
  background: #ffffff;
}

.eiq-approved-race__panel {
  padding: 16px 18px;
}

.eiq-approved-race__panel h2,
.eiq-approved-race__runner-board h2 {
  margin: 0 0 16px;
  color: var(--eiq-approved-navy);
  font-size: 14px;
  line-height: 1;
  font-weight: 900;
  letter-spacing: 0.03em;
}

.eiq-approved-race__summary,
.eiq-approved-race__conditions {
  min-height: 230px;
}

.eiq-approved-race__summary dl,
.eiq-approved-race__conditions dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 36px;
  row-gap: 15px;
}

.eiq-approved-race__meeting dl,
.eiq-approved-race__actions {
  display: grid;
  gap: 11px;
}

.eiq-approved-race__panel dl {
  margin: 0;
}

.eiq-approved-race__panel div {
  min-width: 0;
}

.eiq-approved-race__panel dt {
  color: var(--eiq-approved-navy);
  font-size: 11px;
  font-weight: 900;
}

.eiq-approved-race__panel dd {
  margin: 4px 0 0;
  color: var(--eiq-approved-text);
  font-size: 13px;
  font-weight: 700;
}

.eiq-approved-race__races {
  grid-column: 1 / span 2;
  min-height: 374px;
}

.eiq-approved-race__table-wrap {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 4px;
  overflow: auto;
}

.eiq-approved-race__races .eiq-approved-table th,
.eiq-approved-race__races .eiq-approved-table td {
  height: 30px;
  text-align: center;
  font-size: 12px;
}

.eiq-approved-race__races .eiq-approved-table th:nth-child(3),
.eiq-approved-race__races .eiq-approved-table td:nth-child(3) {
  text-align: left;
}

.eiq-approved-race__races footer {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 38px;
  color: var(--eiq-approved-muted);
  font-size: 12px;
}

.eiq-approved-race__races footer strong {
  margin-right: auto;
  color: var(--eiq-approved-navy);
}

.eiq-approved-race__actions {
  min-height: 254px;
  align-content: start;
}

.eiq-approved-race__actions button {
  height: 34px;
  border: 0;
  background: transparent;
  color: var(--eiq-approved-blue);
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  text-align: left;
  cursor: pointer;
}

.eiq-approved-race__runner-board {
  padding: 14px;
}

.eiq-approved-race__runner-board .eiq-approved-table th,
.eiq-approved-race__runner-board .eiq-approved-table td {
  height: 34px;
  text-align: center;
  font-size: 12px;
}

.eiq-approved-race__runner-board .eiq-approved-table th:nth-child(3),
.eiq-approved-race__runner-board .eiq-approved-table td:nth-child(3) {
  text-align: left;
}

.eiq-approved-race__silk {
  width: 28px;
  height: 28px;
  display: inline-block;
  object-fit: contain;
  vertical-align: middle;
}

.eiq-approved-race__silk.is-empty {
  border: 1px solid var(--eiq-approved-line);
  border-radius: 3px;
  background: #f8fafc;
}

.eiq-approved-race__feed-state {
  color: var(--eiq-approved-muted);
  font-size: 12px;
  text-align: right;
}

@media (max-width: 1180px) {
  .eiq-approved-race__grid {
    grid-template-columns: 1fr;
  }
  .eiq-approved-race__races {
    grid-column: auto;
  }
}
"""


def main() -> None:
    tsx = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceIntelligenceWorkspace.tsx"
    css = ROOT / "src" / "edgeiq-os" / "approved-ui" / "edgeiqApprovedUiRebuildV1.css"
    checkpoint([tsx, css])
    write(tsx, TSX)
    css_text = read(css)
    if "EDGEIQ APPROVED UI PHASE 05 RACE OVERVIEW" not in css_text:
        write(css, css_text.rstrip() + "\n\n" + CSS_APPEND.strip() + "\n")
    print(f"checkpoint={CHECKPOINT}")
    print("EDGEIQ_APPROVED_UI_PHASE05_RACE_OVERVIEW_PASS")


if __name__ == "__main__":
    main()
