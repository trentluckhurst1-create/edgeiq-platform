import React, { useMemo, useState } from "react";
import type { CareerStats, FormHistoryRow, FormSummary, FullCareerFormRow, RatingDisplayRow } from "../App";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  selectedHorseHistory?: FormHistoryRow[];
  selectedFullCareer?: FullCareerFormRow[];
  selectedSummary?: FormSummary | null;
  selectedCareerStats?: CareerStats | null;
};

type CareerFilter = "All" | "Races" | "Trials" | "Jumpouts";

function rating(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return value.toFixed(1);
}

function price(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value) || value <= 0) return "-";
  return value.toFixed(2);
}


function money(v: unknown): string {
  const raw = safe(v);
  if (raw === "-") return "-";

  const cleaned = raw.replace("$", "").trim();
  const n = Number(cleaned);

  if (!Number.isFinite(n)) return raw.startsWith("$") ? raw : `$${raw}`;
  if (Number.isInteger(n)) return `$${n}`;

  return `$${n.toFixed(2).replace(/0$/, "")}`;
}

function posOnly(v: unknown): string {
  const raw = safe(v);
  if (raw === "-") return "-";

  const n = Number(String(raw).replace(/[^0-9.]/g, ""));
  if (!Number.isFinite(n)) return raw;

  return String(Math.trunc(n));
}

function field(obj: unknown, key: string): unknown {
  return (obj as Record<string, unknown>)[key];
}

function weight(v: unknown): string {
  const raw = safe(v);
  if (raw === "-") return "-";

  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return "-";
  if (Number.isInteger(n)) return String(n);

  return String(n);
}

function record(starts?: number, wins?: number, seconds?: number, thirds?: number): string {
  return `${starts ?? 0}-${wins ?? 0}-${seconds ?? 0}-${thirds ?? 0}`;
}

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  return s || "-";
}

function dateShort(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value || "-";
  return parsed.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "2-digit" });
}

function silk(url?: string): string {
  return url || "/silks/default.svg";
}

function sortedRows(rows: RatingDisplayRow[]): RatingDisplayRow[] {
  const seen = new Set<string>();
  const unique = rows.filter((row) => {
    const key = `${row.raceDate}|${row.track}|${row.raceNo}|${row.horseNo}|${row.horseKey}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return unique.sort((a, b) => {
    if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
    return (a.horseNo ?? 999) - (b.horseNo ?? 999);
  });
}

function conditionClass(v?: string | null): string {
  const x = safe(v).toUpperCase();
  if (x.includes("FAST 1") || x.includes("FAST 2")) return "cond-fast";
  if (x.includes("GOOD 3") || x.includes("GOOD 4")) return "cond-good";
  if (x.includes("SOFT 5") || x.includes("SOFT 6") || x.includes("SOFT 7")) return "cond-soft";
  if (x.includes("HEAVY 8") || x.includes("HEAVY 9") || x.includes("HEAVY 10")) return "cond-heavy";
  return "cond-unknown";
}

function runTypeClass(type: string): string {
  if (type === "RACE") return "race";
  if (type === "TRIAL") return "trial";
  if (type === "JUMPOUT") return "jumpout";
  return "";
}

function isCareerVisible(run: FullCareerFormRow, filter: CareerFilter): boolean {
  if (filter === "All") return true;
  if (filter === "Races") return run.runType === "RACE";
  if (filter === "Trials") return run.runType === "TRIAL";
  return run.runType === "JUMPOUT";
}

function displayRating(run: FormHistoryRow | FullCareerFormRow): string {
  if ("ratingDisplay" in run && run.ratingDisplay) return run.ratingDisplay;
  return run.runType === "RACE" ? rating(run.runRating) : "-";
}

export default function FormTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
  selectedHorseHistory = [],
  selectedFullCareer = [],
  selectedSummary = null,
  selectedCareerStats = null,
}: Props): React.ReactElement {
  const [careerOpen, setCareerOpen] = useState(false);
  const [careerFilter, setCareerFilter] = useState<CareerFilter>("All");

  const rows = sortedRows(runners);
  const selected = rows.find((row) => row.horseKey === selectedHorseKey) ?? rows.find((row) => !row.isScratched) ?? rows[0] ?? null;

  const fullCareer = useMemo(
    () => [...selectedFullCareer].sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime()),
    [selectedFullCareer]
  );

  const source = fullCareer.length ? fullCareer : selectedHorseHistory;
  const official = [...source]
    .filter((run) => run.isOfficialRace)
    .sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime())
    .slice(0, 5);

  const extras = source.filter((run) => !run.isOfficialRace).slice(0, 4);
  const visibleCareer = fullCareer.filter((run) => isCareerVisible(run, careerFilter));

  return (
    <section className="edgeiq-form-tab">
      <div className="edgeiq-form-rail">
        {rows.map((row) => {
          const active = row.horseKey === selected?.horseKey;
          return (
            <button
              key={row.id}
              type="button"
              onClick={() => !row.isScratched && onSelectHorse(row.horseKey)}
              className={`${active ? "active" : ""} ${row.isScratched ? "scratched" : ""}`}
            >
              <span className="no">{row.horseNo ?? "-"}</span>
              <img
                src={silk(row.silkUrl)}
                alt=""
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = "/silks/default.svg";
                }}
              />
              <span className="name">{row.horse}</span>
              <span className="price">{row.isScratched ? "SCR" : price(row.ratedPrice)}</span>
            </button>
          );
        })}
      </div>

      <div className="edgeiq-form-layout">
        <aside className="edgeiq-form-summary">
          <div className="summary-runner">
            <img
              src={silk(selected?.silkUrl)}
              alt=""
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = "/silks/default.svg";
              }}
            />
            <div>
              <div className="kicker">Runner Profile</div>
              <h2>{selected?.horse ?? "-"}</h2>
              <p>No {selected?.horseNo ?? "-"} · Bar {selected?.barrier ?? "-"} · {selected?.jockey || "-"} · {selected?.trainer || "-"}</p>
            </div>
          </div>

          <div className="summary-grid">
            {[
              ["1LS", rating(selectedSummary?.ls1 ?? selected?.ls1)],
              ["2LS", rating(selectedSummary?.ls2 ?? selected?.ls2)],
              ["3LS", rating(selectedSummary?.ls3 ?? selected?.ls3)],
              ["Peak", rating(selectedSummary?.peak ?? selected?.peak)],
              ["Avg3", rating(selectedSummary?.avg3)],
              ["Runs", selectedSummary?.officialRunCount !== null && selectedSummary?.officialRunCount !== undefined ? selectedSummary.officialRunCount.toFixed(0) : "-"],
            ].map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          <div className="summary-records">
            {[
              ["Career", record(selectedCareerStats?.careerStarts, selectedCareerStats?.careerWins, selectedCareerStats?.careerSeconds, selectedCareerStats?.careerThirds)],
              ["Track", record(selectedCareerStats?.trackStarts, selectedCareerStats?.trackWins, selectedCareerStats?.trackSeconds, selectedCareerStats?.trackThirds)],
              ["Distance", record(selectedCareerStats?.distanceStarts, selectedCareerStats?.distanceWins, selectedCareerStats?.distanceSeconds, selectedCareerStats?.distanceThirds)],
              ["Track/Dist", record(selectedCareerStats?.trackDistanceStarts, selectedCareerStats?.trackDistanceWins, selectedCareerStats?.trackDistanceSeconds, selectedCareerStats?.trackDistanceThirds)],
              ["First Up", record(selectedCareerStats?.firstUpStarts, selectedCareerStats?.firstUpWins, selectedCareerStats?.firstUpSeconds, selectedCareerStats?.firstUpThirds)],
              ["Second Up", record(selectedCareerStats?.secondUpStarts, selectedCareerStats?.secondUpWins, selectedCareerStats?.secondUpSeconds, selectedCareerStats?.secondUpThirds)],
              ["Good", record(selectedCareerStats?.goodStarts, selectedCareerStats?.goodWins, selectedCareerStats?.goodSeconds, selectedCareerStats?.goodThirds)],
              ["Soft/Heavy", `${record(selectedCareerStats?.softStarts, selectedCareerStats?.softWins, selectedCareerStats?.softSeconds, selectedCareerStats?.softThirds)} / ${record(selectedCareerStats?.heavyStarts, selectedCareerStats?.heavyWins, selectedCareerStats?.heavySeconds, selectedCareerStats?.heavyThirds)}`],
            ].map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>

          <div className="summary-note">
            <span>Distances won</span>
            <strong>{selectedCareerStats?.distancesWon || "No wins recorded"}</strong>
          </div>

          <div className="summary-note">
            <span>Weights won with</span>
            <strong>{selectedCareerStats?.weightsWonWith || "No winning weights recorded"}</strong>
          </div>
        </aside>

        <main className="edgeiq-form-main">
          <div className="section-title">Last 5 official starts</div>

          <div className="form-table-box">
            <table className="edgeiq-form-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Track</th>
                  <th>Dist</th>
                  <th>Class</th>
                  <th>Cond</th>
                  <th>Fin</th>
                  <th>Margin</th>
                  <th>Jockey</th>
                  <th>SP</th>
                  <th>Rating</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {official.map((run) => (
                  <tr key={run.id}>
                    <td>{dateShort(run.runDate)}</td>
                    <td>{safe(run.track)}</td>
                    <td>{run.distance ? `${run.distance}m` : "-"}</td>
                    <td>{safe(run.raceClass)}</td>
                    <td><span className={`condition-pill ${conditionClass(run.trackCondition)}`}>{safe(run.trackCondition).toUpperCase()}</span></td>
                    <td>{safe(run.finishPos)}</td>
                    <td>{safe(run.margin)}</td>
                    <td>{safe(run.jockey)}</td>
                    <td>{safe(field(run, "barrier"))}</td>
                    <td>{weight(field(run, "weightCarried"))}</td>
                    <td>{money(run.sp)}</td>
                    <td>{posOnly(field(run, "pos800"))}</td>
                    <td>{posOnly(field(run, "pos400"))}</td>
                    <td>{safe(field(run, "winner"))}</td>
                    <td>{rating(run.runRating)}</td>
                    <td><span className={`form-type ${runTypeClass(run.runType)}`}>{run.runType}</span></td>
                    <td><button type="button" className="form-detail-arrow" title="Race result detail">›</button></td>
                  </tr>
                ))}
                {official.length === 0 ? (
                  <tr><td colSpan={17} className="empty">FIRST START / NO OFFICIAL FORM</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="section-title">Trials / jumpouts</div>

          <div className="mini-run-list">
            {extras.map((run) => (
              <div key={run.id}>
                <span>{dateShort(run.runDate)}</span>
                <span>{safe(run.track)}</span>
                <span>{run.distance ? `${run.distance}m` : "-"}</span>
                <span><span className={`condition-pill ${conditionClass(run.trackCondition)}`}>{safe(run.trackCondition).toUpperCase()}</span></span>
                <span>Fin {safe(run.finishPos)}</span>
                <span className={`form-type ${runTypeClass(run.runType)}`}>{run.runType}</span>
                <span>-</span>
              </div>
            ))}
            {extras.length === 0 ? <div className="empty">No trials or jumpouts listed.</div> : null}
          </div>

          <div className="career-panel">
            <button type="button" onClick={() => setCareerOpen((value) => !value)}>
              <span>Full Career</span>
              <strong>{fullCareer.length} runs / trials / jumpouts</strong>
              <em>{careerOpen ? "Hide" : "Show"}</em>
            </button>

            {careerOpen ? (
              <div className="career-body">
                <div className="filter-row">
                  {(["All", "Races", "Trials", "Jumpouts"] as CareerFilter[]).map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setCareerFilter(filter)}
                      className={careerFilter === filter ? "active" : ""}
                    >
                      {filter}
                    </button>
                  ))}
                </div>

                <div className="form-table-box">
                  <table className="edgeiq-form-table full">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Track</th>
                        <th>Dist</th>
                        <th>Class</th>
                        <th>Cond</th>
                        <th>Fin</th>
                        
                        <th>Margin</th>
                        <th>Jockey</th>
                        <th>Bar</th>
                        <th>Wgt</th>
                        <th>SP</th>
                        <th>800/400</th>
                        <th>Winner</th>
                        <th>Rating</th>
                        <th>Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleCareer.map((run) => (
                        <tr key={run.id}>
                          <td>{dateShort(run.runDate)}</td>
                          <td>{safe(run.track)}</td>
                          <td>{run.distance ? `${run.distance}m` : "-"}</td>
                          <td>{safe(run.raceClass)}</td>
                          <td><span className={`condition-pill ${conditionClass(run.trackCondition)}`}>{safe(run.trackCondition).toUpperCase()}</span></td>
                          <td>{safe(run.finishPos)}</td>
                          
                          <td>{safe(run.margin)}</td>
                          <td>{safe(run.jockey)}</td>
                          <td>{safe(run.barrier)}</td>
                          <td>{weight(run.weightCarried)}</td>
                          <td>{money(run.sp)}</td>
                          <td>{`${posOnly(run.pos800)} / ${posOnly(run.pos400)}`}</td>
                          <td>{safe(run.winner)}</td>
                          <td>{displayRating(run)}</td>
                          <td><span className={`form-type ${runTypeClass(run.runType)}`}>{run.runType}</span></td>
                          <td><button type="button" className="form-detail-arrow" title="Race result detail">›</button></td>
                        </tr>
                      ))}
                      {visibleCareer.length === 0 ? (
                        <tr><td colSpan={16} className="empty">No full career rows for this filter.</td></tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </section>
  );
}

