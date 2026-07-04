import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type Row = Record<string, string>;

function clean(v: any, fallback = "-") {
  const s = String(v ?? "").trim();
  if (!s || s === "nan" || s === "NaN" || s === "UNKNOWN") return fallback;
  return s;
}

function raceNoKey(v: any) {
  const n = Number(String(v ?? "").replace(/[^\d.]/g, ""));
  if (Number.isFinite(n) && n > 0) return String(Math.trunc(n));
  return String(v ?? "").trim();
}

function trackKey(v: any) {
  return String(v ?? "")
    .toUpperCase()
    .replace(/BET365|LADBROKES|TAB|RACINGCOM/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function raceKey(row: Row) {
  return `${clean(row.race_date, "")}|${trackKey(row.track)}|${raceNoKey(row.race_no)}`;
}

function posClass(v: string) {
  const p = Number(String(v || "").replace(/[^\d.]/g, ""));
  if (p === 1) return "rrPosWin";
  if (p === 2 || p === 3) return "rrPosPlace";
  return "";
}

function gradeClass(grade: any) {
  const g = clean(grade, "").toUpperCase();
  if (g === "ELITE") return "rrGradeElite";
  if (g === "HIGH") return "rrGradeHigh";
  if (g === "STRONG") return "rrGradeStrong";
  if (g === "AVERAGE") return "rrGradeAverage";
  if (g === "WEAK") return "rrGradeWeak";
  return "rrGradeUnknown";
}

function fmtNum(v: any, fallback = "-") {
  const n = Number(v);
  if (!Number.isFinite(n)) return clean(v, fallback);
  return n.toFixed(Math.abs(n) >= 100 ? 0 : 1).replace(/\.0$/, "");
}

async function loadCsvOptional(path: string): Promise<Row[]> {
  try {
    const res = await fetch(`${path}?t=${Date.now()}`);
    if (!res.ok) return [];
    const txt = await res.text();
    return Papa.parse<Row>(txt, { header: true, skipEmptyLines: true }).data || [];
  } catch {
    return [];
  }
}

export default function ResultsTab() {
  const [races, setRaces] = useState<Row[]>([]);
  const [details, setDetails] = useState<Row[]>([]);
  const [raceRatings, setRaceRatings] = useState<Row[]>([]);
  const [track, setTrack] = useState("ALL");
  const [raceDate, setRaceDate] = useState("LATEST");
  const [selectedRaceKey, setSelectedRaceKey] = useState("");

  useEffect(() => {
    let mounted = true;

    async function load() {
      const [reviewRows, detailRows, strengthRows] = await Promise.all([
        loadCsvOptional("/data/results_review.csv"),
        loadCsvOptional("/data/results_race_detail.csv"),
        loadCsvOptional("/data/historical_race_ratings.csv"),
      ]);

      if (!mounted) return;
      setRaces(reviewRows);
      setDetails(detailRows);
      setRaceRatings(strengthRows);
    }

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const ratingByRace = useMemo(() => {
    const map = new Map<string, Row>();
    for (const row of raceRatings) {
      const key = raceKey(row);
      if (key.replace(/\|/g, "")) map.set(key, row);
    }
    return map;
  }, [raceRatings]);

  const dates = useMemo(() => {
    const vals = Array.from(new Set(races.map((r) => clean(r.race_date, "")).filter(Boolean))).sort().reverse();
    return ["LATEST", "ALL", ...vals];
  }, [races]);

  const filteredByDate = useMemo(() => {
    if (raceDate === "LATEST" && dates[2]) {
      return races.filter((r) => clean(r.race_date, "") === dates[2]);
    }
    if (raceDate !== "ALL" && raceDate !== "LATEST") {
      return races.filter((r) => clean(r.race_date, "") === raceDate);
    }
    return races;
  }, [races, raceDate, dates]);

  const tracks = useMemo(() => {
    const vals = Array.from(new Set(filteredByDate.map((r) => clean(r.track, "")).filter(Boolean))).sort();
    return ["ALL", ...vals];
  }, [filteredByDate]);

  const filtered = useMemo(() => {
    let x = [...filteredByDate];

    if (track !== "ALL") {
      x = x.filter((r) => clean(r.track, "") === track);
    }

    return x.slice(0, 250);
  }, [filteredByDate, track]);

  const activeRace = useMemo(() => {
    if (selectedRaceKey) {
      const found = filtered.find((r) => raceKey(r) === selectedRaceKey);
      if (found) return found;
    }
    return filtered[0];
  }, [filtered, selectedRaceKey]);

  const activeKey = activeRace ? raceKey(activeRace) : "";
  const activeRating = activeRace ? ratingByRace.get(activeKey) ?? null : null;

  const raceDetails = useMemo(() => {
    if (!activeRace) return [];

    return details.filter(
      (r) =>
        clean(r.race_date, "") === clean(activeRace.race_date, "") &&
        trackKey(r.track) === trackKey(activeRace.track) &&
        raceNoKey(r.race_no) === raceNoKey(activeRace.race_no)
    );
  }, [details, activeRace]);

  const summary = useMemo(() => {
    return {
      races: filtered.length,
      tracks: new Set(filtered.map((r) => clean(r.track, "")).filter(Boolean)).size,
      runners: raceDetails.length,
      winners: filtered.filter((r) => clean(r.winner, "")).length,
      ratedRaces: filtered.filter((r) => ratingByRace.has(raceKey(r))).length,
    };
  }, [filtered, raceDetails, ratingByRace]);

  return (
    <div className="rrPage">
      <div className="rrHeader">
        <div>
          <div className="rrKicker">EDGEiQ RESULTS REVIEW</div>
          <h2>{activeRace ? `${clean(activeRace.track)} R${clean(activeRace.race_no)} Full Result` : "Results Review"}</h2>
          <p>
            Full finishing order with race-strength ratings, race shape, SP, margins and historical runner context.
          </p>
        </div>

        <div className="rrFilters">
          <label>
            Date
            <select value={raceDate} onChange={(e) => { setRaceDate(e.target.value); setTrack("ALL"); setSelectedRaceKey(""); }}>
              {dates.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>

          <label>
            Track
            <select value={track} onChange={(e) => { setTrack(e.target.value); setSelectedRaceKey(""); }}>
              {tracks.map((t) => <option key={t}>{t}</option>)}
            </select>
          </label>
        </div>
      </div>

      <div className="rrSummaryGrid">
        <div className="rrCard"><span>Races</span><strong>{summary.races}</strong></div>
        <div className="rrCard"><span>Tracks</span><strong>{summary.tracks}</strong></div>
        <div className="rrCard"><span>Runners In Race</span><strong>{summary.runners}</strong></div>
        <div className="rrCard"><span>Winners Loaded</span><strong>{summary.winners}</strong></div>
        <div className="rrCard"><span>Race Ratings</span><strong>{summary.ratedRaces}</strong></div>
      </div>

      <div className="rrRaceStrip">
        {filtered.map((r) => {
          const key = raceKey(r);
          const rating = ratingByRace.get(key);
          const grade = clean(rating?.race_strength_grade, "");
          return (
            <button
              key={key}
              className={`rrRaceButton ${key === activeKey ? "active" : ""}`}
              onClick={() => setSelectedRaceKey(key)}
            >
              <span>{clean(r.track)} R{clean(r.race_no)}</span>
              <strong>{clean(r.winner)}</strong>
              {grade ? <em className={`rrGradeChip ${gradeClass(grade)}`}>{grade}</em> : null}
            </button>
          );
        })}
      </div>

      <div className="rrPanel">
        <div className="rrPanelHead">
          <div>
            <div className="rrKicker">FULL RACE RESULT</div>
            <strong>
              {activeRace
                ? `${clean(activeRace.track)} R${clean(activeRace.race_no)} · ${clean(activeRace.distance)}m · ${clean(activeRace.condition)}`
                : "No race selected"}
            </strong>
            {activeRating ? (
              <div className="rrStrengthGrid">
                <span><b>Strength</b>{fmtNum(activeRating.race_strength_rating)}</span>
                <span><b>Grade</b><em className={`rrGradeChip ${gradeClass(activeRating.race_strength_grade)}`}>{clean(activeRating.race_strength_grade)}</em></span>
                <span><b>Tempo</b>{clean(activeRating.tempo_proxy)}</span>
                <span><b>Shape</b>{clean(activeRating.race_shape)}</span>
                <span><b>Base</b>{fmtNum(activeRating.base_class_rating)}</span>
                <span><b>Field</b>{fmtNum(activeRating.field_depth_adj)}</span>
                <span><b>Market</b>{fmtNum(activeRating.market_depth_adj)}</span>
                <span><b>Condition</b>{fmtNum(activeRating.condition_adj)}</span>
              </div>
            ) : (
              <div className="rrStrengthEmpty">Race strength rating not loaded for this race.</div>
            )}
          </div>
          <span>{raceDetails.length} runners</span>
        </div>

        {!raceDetails.length ? (
          <div className="rrEmpty">No full result data loaded for this race.</div>
        ) : (
          <div className="rrTableWrap">
            <table className="rrTable rrDetailTable">
              <thead>
                <tr>
                  <th>Pl</th>
                  <th>Runner</th>
                  <th>Margin</th>
                  <th>SP</th>
                  <th>Jockey</th>
                  <th>Trainer</th>
                  <th>Run Rating</th>
                  <th>EDGEiQ Rank</th>
                  <th>Rated</th>
                  <th>Market</th>
                  <th>Edge</th>
                  <th>Pace</th>
                  <th>Snapshot</th>
                </tr>
              </thead>

              <tbody>
                {raceDetails.map((r, i) => (
                  <tr key={`${r.runner}-${i}`} className={Number(clean(r.finish_pos, "0")) === 1 ? "rrWinnerRow" : ""}>
                    <td>
                      <span className={`rrPos ${posClass(r.finish_pos)}`}>
                        {clean(r.finish_pos)}
                      </span>
                    </td>
                    <td>
                      <div className="rrWinner">{clean(r.runner)}</div>
                      <div className="rrTiny">{clean(r.race_class)} · {clean(r.condition)}</div>
                    </td>
                    <td>{clean(r.margin)}</td>
                    <td>{clean(r.sp)}</td>
                    <td>{clean(r.jockey)}</td>
                    <td>{clean(r.trainer)}</td>
                    <td><strong>{clean(r.run_rating)}</strong></td>
                    <td>{clean(r.edgeiq_rank)}</td>
                    <td>{clean(r.edgeiq_rated_price)}</td>
                    <td>{clean(r.edgeiq_market)}</td>
                    <td>{clean(r.edgeiq_edge)}</td>
                    <td>{clean(r.pace_setup)}</td>
                    <td>
                      <span className="rrSnapshotChip">{clean(r.model_snapshot_status)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
