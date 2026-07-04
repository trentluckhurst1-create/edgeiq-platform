import type { CareerStats, FormHistoryRow, RatingDisplayRow } from "../App";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  historyByHorse: Map<string, FormHistoryRow[]>;
  careerStats?: CareerStats | null;
};

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  if (!s || s.toLowerCase() === "nan" || s.toLowerCase() === "null") return "—";
  return s;
}

function num(v: unknown): number | null {
  const n = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function money(v: unknown): string {
  const n = num(v);
  return n === null ? "—" : n.toFixed(2);
}

function pct(v: unknown): string {
  const n = num(v);
  return n === null ? "—" : `${n.toFixed(1)}%`;
}

function tone(v: unknown): string {
  const n = num(v);
  if (n === null) return "edgeiq-muted";
  return n >= 0 ? "edgeiq-green" : "edgeiq-red";
}

function rating(v: unknown): string {
  const n = num(v);
  return n === null ? "—" : n.toFixed(1);
}

function silk(src: string): string {
  return src && src.trim() ? src : "/silks/default.svg";
}

function historyFor(row: RatingDisplayRow, historyByHorse: Map<string, FormHistoryRow[]>): FormHistoryRow[] {
  return historyByHorse.get(row.horseKey) ?? historyByHorse.get(row.matchKey) ?? [];
}

function sortedOfficialRuns(rows: FormHistoryRow[]): FormHistoryRow[] {
  return rows
    .filter((r) => r.isOfficialRace)
    .sort((a, b) => {
      const da = new Date(a.runDate || 0).getTime();
      const db = new Date(b.runDate || 0).getTime();
      return db - da;
    });
}

function avgRating(rows: FormHistoryRow[], take: number): number | null {
  const vals = sortedOfficialRuns(rows)
    .slice(0, take)
    .map((r) => r.runRating)
    .filter((x): x is number => typeof x === "number" && Number.isFinite(x));

  if (!vals.length) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

export default function RatingsTab({
  runners,
  selectedHorseKey,
  onSelectHorse,
  historyByHorse,
  careerStats,
}: Props) {
  const live = runners.filter((r) => !r.isScratched);
  const scratched = runners.filter((r) => r.isScratched);

  const ranked = [...live].sort((a, b) => {
    const ar = a.modelRank ?? 999;
    const br = b.modelRank ?? 999;
    return ar - br;
  });

  const selected =
    runners.find((r) => r.horseKey === selectedHorseKey) ??
    ranked[0] ??
    runners[0] ??
    null;

  const selectedHistory = selected ? historyFor(selected, historyByHorse) : [];
  const selectedAvg3 = avgRating(selectedHistory, 3);
  const selectedAvg5 = avgRating(selectedHistory, 5);

  const fieldAvg =
    live.length > 0
      ? live.reduce((sum, r) => sum + (r.todayRating ?? 0), 0) / live.length
      : null;

  const topRated = ranked[0] ?? null;
  const bestEdge = [...live].sort((a, b) => (b.edgePct ?? -999) - (a.edgePct ?? -999))[0] ?? null;

  return (
    <div className="edgeiq-ratings">
      <section className="edgeiq-ratings-hero">
        <div>
          <div className="edgeiq-ws-kicker">EDGEiQ RATINGS</div>
          <h2>Rated market breakdown</h2>
          <p>Model rank · rated price · market price · value edge</p>
        </div>

        <div className="edgeiq-rating-metrics">
          <div>
            <span>Top Rated</span>
            <strong>{topRated ? topRated.horse : "—"}</strong>
            <em>{topRated ? rating(topRated.todayRating) : "—"}</em>
          </div>

          <div>
            <span>Best Edge</span>
            <strong>{bestEdge ? bestEdge.horse : "—"}</strong>
            <em className={bestEdge ? tone(bestEdge.edgePct) : ""}>{bestEdge ? pct(bestEdge.edgePct) : "—"}</em>
          </div>

          <div>
            <span>Field Avg</span>
            <strong>{rating(fieldAvg)}</strong>
            <em>{live.length} runners</em>
          </div>
        </div>
      </section>

      <div className="edgeiq-ratings-grid">
        <section className="edgeiq-ws-card">
          <div className="edgeiq-ws-head">
            <div className="edgeiq-ws-kicker">RATED MARKET</div>
          </div>

          <div className="edgeiq-ws-table-wrap">
            <table className="edgeiq-ws-table edgeiq-ratings-table">
              <thead>
                <tr>
                  <th className="col-rank">Rank</th>
                  <th className="col-runner">Runner</th>
                  <th className="num">Today</th>
                  <th className="num">Win Fig</th>
                  <th className="num">Rated</th>
                  <th className="num">Market</th>
                  <th className="num">Edge</th>
                  <th className="num">Peak</th>
                  <th className="num">Avg 3</th>
                  <th className="num">Avg 5</th>
                </tr>
              </thead>

              <tbody>
                {[...ranked, ...scratched].map((row, idx) => {
                  const isSelected = selected?.horseKey === row.horseKey;
                  const history = historyFor(row, historyByHorse);
                  const avg3 = avgRating(history, 3);
                  const avg5 = avgRating(history, 5);

                  return (
                    <tr
                      key={row.id || `${row.horseKey}-${idx}`}
                      className={`${isSelected ? "is-selected" : ""} ${row.isScratched ? "is-scratched" : ""}`}
                      onClick={() => onSelectHorse(row.horseKey)}
                    >
                      <td className="num strong">{row.isScratched ? "SCR" : row.modelRank ?? idx + 1}</td>

                      <td>
                        <div className="edgeiq-runner">
                          <img src={silk(row.silkUrl)} alt="" />
                          <div className="edgeiq-runner-meta">
                            <strong>{safe(row.horse)}</strong>
                            <span>No {safe(row.horseNo)} · Bar {safe(row.barrier)}</span>
                          </div>
                        </div>
                      </td>

                      <td className="num strong">{rating(row.todayRating)}</td>
                      <td className="num">{rating(row.winningFigure)}</td>
                      <td className="num">{money(row.ratedPrice)}</td>
                      <td className="num">{row.isScratched ? "SCR" : money(row.marketPrice)}</td>
                      <td className={`num strong ${tone(row.edgePct)}`}>{row.isScratched ? "—" : pct(row.edgePct)}</td>
                      <td className="num">{rating(row.peak)}</td>
                      <td className="num">{rating(avg3)}</td>
                      <td className="num">{rating(avg5)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="edgeiq-rating-panel">
          {selected ? (
            <>
              <div className="edgeiq-rating-profile">
                <img src={silk(selected.silkUrl)} alt="" />
                <div>
                  <div className="edgeiq-ws-kicker">SELECTED RUNNER</div>
                  <h3>{safe(selected.horse)}</h3>
                  <p>No {safe(selected.horseNo)} · Bar {safe(selected.barrier)} · {safe(selected.jockey)}</p>
                </div>
              </div>

              <div className="edgeiq-rating-price-grid">
                <div><span>Today</span><strong>{rating(selected.todayRating)}</strong></div>
                <div><span>Rated</span><strong>{money(selected.ratedPrice)}</strong></div>
                <div><span>Market</span><strong>{selected.isScratched ? "SCR" : money(selected.marketPrice)}</strong></div>
                <div><span>Edge</span><strong className={tone(selected.edgePct)}>{selected.isScratched ? "—" : pct(selected.edgePct)}</strong></div>
                <div><span>Peak</span><strong>{rating(selected.peak)}</strong></div>
                <div><span>Gap</span><strong>{rating(selected.exp)}</strong></div>
              </div>

              <div className="edgeiq-rating-section">
                <div className="edgeiq-ws-kicker">LAST START SHAPE</div>
                <div className="edgeiq-ls-strip">
                  <div><span>1LS</span><strong>{rating(selected.ls1)}</strong></div>
                  <div><span>2LS</span><strong>{rating(selected.ls2)}</strong></div>
                  <div><span>3LS</span><strong>{rating(selected.ls3)}</strong></div>
                  <div><span>4LS</span><strong>{rating(selected.ls4)}</strong></div>
                  <div><span>5LS</span><strong>{rating(selected.ls5)}</strong></div>
                </div>
              </div>

              <div className="edgeiq-rating-section">
                <div className="edgeiq-ws-kicker">CAREER FILTERS</div>
                <div className="edgeiq-career-grid">
                  <div><span>Career</span><strong>{careerStats ? `${careerStats.careerStarts}: ${careerStats.careerWins}-${careerStats.careerSeconds}-${careerStats.careerThirds}` : "—"}</strong></div>
                  <div><span>Track</span><strong>{careerStats ? `${careerStats.trackStarts}: ${careerStats.trackWins}-${careerStats.trackSeconds}-${careerStats.trackThirds}` : "—"}</strong></div>
                  <div><span>Distance</span><strong>{careerStats ? `${careerStats.distanceStarts}: ${careerStats.distanceWins}-${careerStats.distanceSeconds}-${careerStats.distanceThirds}` : "—"}</strong></div>
                  <div><span>Avg 3</span><strong>{rating(selectedAvg3)}</strong></div>
                  <div><span>Avg 5</span><strong>{rating(selectedAvg5)}</strong></div>
                </div>
              </div>
            </>
          ) : (
            <div className="edgeiq-muted">No runner selected.</div>
          )}
        </aside>
      </div>
    </div>
  );
}
