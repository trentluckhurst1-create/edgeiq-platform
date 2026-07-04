import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import Worksheet from "./components/Worksheet";
import RatingsTab from "./components/RatingsTab";
import FormTab from "./components/FormTab";

type TabKey =
  | "worksheet"
  | "ratings"
  | "form"
  | "speedmap"
  | "performance"
  | "results"
  | "bets";

type CsvRow = Record<string, unknown>;

type FormRun = {
  horse: string;
  horseKey: string;
  runType: string;
  runDate: string;
  track: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
  finishPos: string;
  margin: string;
  jockey: string;
  trainer: string;
  barrier: number | null;
  sp: string;
  runRating: number | null;
  pos800: number | null;
  pos400: number | null;
  inRunPositions: string;
  isOfficialRace: boolean;
};

export type WorksheetRunner = {
  id: string;
  raceDate: string;
  track: string;
  raceNo: number;
  horse: string;
  horseKey: string;
  horseNo: number | null;
  barrier: number | null;
  jockey: string;
  trainer: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
  ratedPrice: number | null;
  marketPrice: number | null;
  todayRating: number | null;
  winningFigure: number | null;
  ratingGap: number | null;
  modelRank: number | null;
  officialRunCount: number | null;
  last5: {
    ls1: number | null;
    ls2: number | null;
    ls3: number | null;
    ls4: number | null;
    ls5: number | null;
    ls3a: number | null;
    ls5a: number | null;
    peak: number | null;
    gap: number | null;
  };
  matchedRuns: FormRun[];
};

type RaceFieldRow = {
  raceDate: string;
  track: string;
  raceNo: number | null;
  horse: string;
  horseKey: string;
  horseNo: number | null;
  barrier: number | null;
  jockey: string;
  trainer: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
};

type RaceOption = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  label: string;
};

type SpeedMapRow = {
  horse: string;
  horseKey: string;
  horseNo: number | null;
  barrier: number | null;
  avg800: number | null;
  avg400: number | null;
};

function parseString(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value).trim();
  if (!text || text.toUpperCase() === "NAN" || text === "undefined" || text === "null") return "";
  return text;
}

function parseNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(String(value).replace(/[^0-9.\-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function parseBool(value: unknown): boolean {
  const s = String(value ?? "").trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "y";
}

function parseScratched(value: unknown): number {
  if (value === true || value === 1) return 1;
  if (value === false || value === 0 || value === null || value === undefined) return 0;

  const s = String(value).trim().toLowerCase();
  if (!s) return 0;

  return ["1","true","yes","y","scr","scratched"].includes(s) ? 1 : 0;
}

function normaliseHorseName(value: string): string {
  return parseString(value)
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .toUpperCase()
    .replace(/\([^)]*\)/g, "")
    .replace(/['''"]/g, "")
    .replace(/[^A-Z0-9]/g, "")
    .trim();
}

function horseKeyFromRow(row: CsvRow, horseField = "horse"): string {
  return normaliseHorseName(parseString(row[horseField]));
}

function raceKeyOf(raceDate: string, track: string, raceNo: number | null): string {
  return `${raceDate}|${track.toUpperCase()}|${raceNo ?? ""}`;
}

function raceHorseKeyOf(
  raceDate: string,
  track: string,
  raceNo: number | null,
  horseKey: string
): string {
  return `${raceKeyOf(raceDate, track, raceNo)}|${horseKey}`;
}

function byHorseNo<T extends { horseNo: number | null }>(a: T, b: T): number {
  return (a.horseNo ?? 999) - (b.horseNo ?? 999);
}

function sortRunsDesc(a: FormRun, b: FormRun): number {
  return b.runDate.localeCompare(a.runDate);
}

function average(values: Array<number | null>): number | null {
  const clean = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!clean.length) return null;
  return clean.reduce((a, b) => a + b, 0) / clean.length;
}

function priceText(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  return value >= 100 ? value.toFixed(0) : value.toFixed(2);
}

function buildRaceLabel(
  raceDate: string,
  track: string,
  raceNo: number,
  raceClass: string,
  distance: number | null
): string {
  const bits = [
    raceDate,
    track,
    `R${raceNo}`,
    distance ? `${Math.round(distance)}m` : "",
    raceClass,
  ].filter(Boolean);

  return bits.join(" - ");
}

function pickFirstNonBlank(...values: Array<string | null | undefined>): string {
  for (const value of values) {
    const clean = parseString(value);
    if (clean) return clean;
  }
  return "";
}

function cleanJockey(value: string): string {
  let text = parseString(value);
  if (!text) return "";

  text = text.replace(/\(\$.*?\)/g, "").trim();

  const upper = text.toUpperCase();

  if (
    [
      "CL1",
      "CL2",
      "CL3",
      "CL4",
      "CL5",
      "BM64",
      "BM66",
      "BM70",
      "BM74",
      "BM78",
      "BM84",
      "MDN",
      "TRL",
      "TRIAL",
      "TRIALS",
      "HCP",
      "G1",
      "G2",
      "G3",
      "G4",
      "G5",
      "S5",
      "S6",
      "VG",
      "F&M",
      "JUMP",
      "JUMPOUT",
      "JUMP OUT",
      "UNKNOWN",
    ].includes(upper)
  ) {
    return "";
  }

  if (
    upper.includes("GOOD") ||
    upper.includes("SOFT") ||
    upper.includes("HEAVY") ||
    upper.includes("FAST") ||
    upper.includes("HANDICAP") ||
    upper.includes("MAIDEN") ||
    upper.includes("PLATE") ||
    upper.includes("BENCHMARK") ||
    upper.includes("GROUP")
  ) {
    return "";
  }

  return text;
}

function cleanTrainer(value: string): string {
  let text = parseString(value);
  if (!text) return "";

  text = text.replace(/and Owner Reforms/gi, "").trim();
  text = text.replace(/\(\$.*?\)/g, "").trim();

  const upper = text.toUpperCase();

  if (
    !text ||
    upper.includes("GOOD") ||
    upper.includes("SOFT") ||
    upper.includes("HEAVY") ||
    upper.includes("FAST") ||
    upper.includes("HANDICAP") ||
    upper.includes("MAIDEN") ||
    upper.includes("PLATE") ||
    upper.includes("BENCHMARK") ||
    upper.includes("GROUP") ||
    upper === "UNKNOWN"
  ) {
    return "";
  }

  return text;
}

function normaliseRaceClass(value: string): string {
  const text = parseString(value);
  if (!text) return "";

  const upper = text.toUpperCase();
  const conditionMatch = upper.match(/\b(FAST|GOOD|SOFT|HEAVY)\s*\d*\b/);
  if (!conditionMatch) return text;

  const cleaned = upper.replace(conditionMatch[0], "").trim();
  return cleaned || "";
}

function normaliseTrackCondition(value: string): string {
  const text = parseString(value);
  if (!text) return "";

  const upper = text.toUpperCase();
  const conditionMatch = upper.match(/\b(FAST|GOOD|SOFT|HEAVY)\s*\d*\b/);
  if (conditionMatch) return conditionMatch[0].trim();

  return text;
}

function hasAnyFormData(run: FormRun): boolean {
  return Boolean(
    run.runDate ||
      run.track ||
      run.raceClass ||
      run.trackCondition ||
      run.finishPos ||
      run.margin ||
      run.jockey ||
      run.trainer ||
      run.sp ||
      run.runRating !== null ||
      run.pos800 !== null ||
      run.pos400 !== null
  );
}

async function loadCsv<T extends CsvRow>(url: string): Promise<T[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<T>(url, {
      download: true,
      header: true,
      skipEmptyLines: true,
      complete: (results) => resolve((results.data ?? []) as T[]),
      error: (error) => reject(error),
    });
  });
}

function buildRaceFieldRow(row: CsvRow): RaceFieldRow {
  return {
    raceDate: parseString(row.race_date),
    track: parseString(row.track).toUpperCase(),
    raceNo: parseNumber(row.race_no),
    horse: parseString(row.horse),
    horseKey: horseKeyFromRow(row),
    horseNo: parseNumber(row.horse_no),
    barrier: parseNumber(row.barrier),
    jockey: cleanJockey(parseString(row.jockey)),
    trainer: cleanTrainer(parseString(row.trainer)),
    distance: parseNumber(row.distance),
    raceClass: normaliseRaceClass(parseString(row.race_class)),
    trackCondition: normaliseTrackCondition(parseString(row.track_condition)),
  };
}

function buildFormRun(row: CsvRow): FormRun {
  const rawRaceClass = parseString(row.race_class);
  const rawTrackCondition = parseString(row.track_condition);

  return {
    horse: parseString(row.horse),
    horseKey: horseKeyFromRow(row),
    runType: parseString(row.run_type).toUpperCase(),
    runDate: parseString(row.run_date_iso || row.run_date),
    track: parseString(row.track).toUpperCase(),
    distance: parseNumber(row.distance),
    raceClass: normaliseRaceClass(rawRaceClass),
    trackCondition: normaliseTrackCondition(
      rawTrackCondition || rawRaceClass
    ),
    finishPos: parseString(row.finish_pos),
    margin: parseString(row.margin),
    jockey: cleanJockey(parseString(row.jockey)),
    trainer: cleanTrainer(parseString(row.trainer)),
    barrier: parseNumber(row.barrier),
    sp: parseString(row.sp),
    runRating: parseNumber(row.run_rating),
    pos800: parseNumber(row.pos_800),
    pos400: parseNumber(row.pos_400),
    inRunPositions: parseString(row.in_run_positions),
    isOfficialRace: parseBool(row.is_official_race),
  };
}

function App() {
  const [tab, setTab] = useState<TabKey>("worksheet");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedRaceKey, setSelectedRaceKey] = useState("");
  const [selectedHorseKey, setSelectedHorseKey] = useState("");
  const [ratedRows, setRatedRows] = useState<CsvRow[]>([]);
  const [raceFieldRows, setRaceFieldRows] = useState<RaceFieldRow[]>([]);
  const [formRunRows, setFormRunRows] = useState<FormRun[]>([]);
  const [resultsRows, setResultsRows] = useState<CsvRow[]>([]);
  const [betsRows, setBetsRows] = useState<CsvRow[]>([]);

  useEffect(() => {
    let alive = true;

    async function run(): Promise<void> {
      setLoading(true);
      setError("");

      try {
        const [rated, fields, formRuns, results, bets] = await Promise.all([
          loadCsv<CsvRow>("/data/rated_market_v2.csv"),
          loadCsv<CsvRow>("/data/race_fields.csv"),
          loadCsv<CsvRow>("/data/form_card_runs.csv"),
          loadCsv<CsvRow>("/data/results_tab_feed.csv").catch(() => []),
          loadCsv<CsvRow>("/data/horse_bets_v4.csv").catch(() => []),
        ]);

        if (!alive) return;

        setRatedRows(rated);
        setRaceFieldRows(fields.map(buildRaceFieldRow));
        setFormRunRows(formRuns.map(buildFormRun));
        setResultsRows(results);
        setBetsRows(bets);
      } catch (err) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load data files.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    void run();

    return () => {
      alive = false;
    };
  }, []);

  const formRunsByHorseKey = useMemo(() => {
    const map = new Map<string, FormRun[]>();

    for (const run of formRunRows) {
      const key = run.horseKey;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(run);
    }

    for (const [key, runs] of map.entries()) {
      const cleanedRuns = [...runs]
        .filter(hasAnyFormData)
        .sort(sortRunsDesc);
      map.set(key, cleanedRuns);
    }

    return map;
  }, [formRunRows]);

  const raceFieldByRaceAndHorse = useMemo(() => {
    const map = new Map<string, RaceFieldRow>();
    for (const row of raceFieldRows) {
      map.set(raceHorseKeyOf(row.raceDate, row.track, row.raceNo, row.horseKey), row);
    }
    return map;
  }, [raceFieldRows]);

  const worksheetRunners = useMemo<WorksheetRunner[]>(() => {
    return ratedRows
      .map((row) => {
        const raceDate = parseString(row.race_date);
        const track = parseString(row.track).toUpperCase();
        const raceNo = parseNumber(row.race_no) ?? 0;
        const horse = parseString(row.horse);
        const horseKey = horseKeyFromRow(row);

        const raceField = raceFieldByRaceAndHorse.get(
          raceHorseKeyOf(raceDate, track, raceNo, horseKey)
        );

        const allRuns = formRunsByHorseKey.get(horseKey) ?? [];
        const officialRuns = allRuns.filter((r) => r.isOfficialRace);
        const usableRuns = officialRuns.length ? officialRuns : allRuns;

        const firstRunWithTrainer = usableRuns.find((r) => !!cleanTrainer(r.trainer));
        const firstRunWithJockey = usableRuns.find((r) => !!cleanJockey(r.jockey));

        return {
          id: `${raceDate}-${track}-${raceNo}-${horseKey}`,
          raceDate,
          track,
          raceNo,
          horse,
          horseKey,
          horseNo: parseNumber(row.horse_no) ?? raceField?.horseNo ?? null,
          barrier: raceField?.barrier ?? parseNumber(row.barrier) ?? null,
          jockey: pickFirstNonBlank(raceField?.jockey, firstRunWithJockey?.jockey, ""),
          trainer: pickFirstNonBlank(raceField?.trainer, firstRunWithTrainer?.trainer, ""),
          distance: parseNumber(row.distance) ?? raceField?.distance ?? null,
          raceClass: pickFirstNonBlank(
            normaliseRaceClass(parseString(row.race_class)),
            raceField?.raceClass,
            ""
          ),
          trackCondition: pickFirstNonBlank(
            normaliseTrackCondition(parseString(row.track_condition)),
            raceField?.trackCondition,
            ""
          ),
          ratedPrice: parseNumber(row.rated_price),
          marketPrice: parseNumber(row.market_price),
          is_scratched: parseScratched(row.is_scratched),
          todayRating: parseNumber(row.today_rating),
          winningFigure: parseNumber(row.winning_figure),
          ratingGap: parseNumber(row.rating_gap),
          modelRank: parseNumber(row.model_rank),
          officialRunCount: parseNumber(row.official_run_count),
          last5: {
            ls1: parseNumber(row["1LS"]),
            ls2: parseNumber(row["2LS"]),
            ls3: parseNumber(row["3LS"]),
            ls4: parseNumber(row["4LS"]),
            ls5: parseNumber(row["5LS"]),
            ls3a: parseNumber(row["3LSA"]),
            ls5a: parseNumber(row["5LSA"]),
            peak: parseNumber(row.PEAK),
            gap: parseNumber(row.gap),
          },
          matchedRuns: usableRuns,
        };
      })
      .sort((a, b) => {
        if (a.raceDate !== b.raceDate) return a.raceDate.localeCompare(b.raceDate);
        if (a.track !== b.track) return a.track.localeCompare(b.track);
        if (a.raceNo !== b.raceNo) return a.raceNo - b.raceNo;
        return byHorseNo(a, b);
      });
  }, [ratedRows, raceFieldByRaceAndHorse, formRunsByHorseKey]);

  const raceOptions = useMemo<RaceOption[]>(() => {
    const seen = new Map<string, RaceOption>();

    for (const runner of worksheetRunners) {
      const key = raceKeyOf(runner.raceDate, runner.track, runner.raceNo);
      if (!seen.has(key)) {
        seen.set(key, {
          key,
          raceDate: runner.raceDate,
          track: runner.track,
          raceNo: runner.raceNo,
          label: buildRaceLabel(
            runner.raceDate,
            runner.track,
            runner.raceNo,
            runner.raceClass,
            runner.distance
          ),
        });
      }
    }

    return [...seen.values()].sort((a, b) => {
      if (a.raceDate !== b.raceDate) return a.raceDate.localeCompare(b.raceDate);
      if (a.track !== b.track) return a.track.localeCompare(b.track);
      return a.raceNo - b.raceNo;
    });
  }, [worksheetRunners]);

  useEffect(() => {
    if (!selectedRaceKey && raceOptions.length) {
      setSelectedRaceKey(raceOptions[0].key);
    }
  }, [raceOptions, selectedRaceKey]);

  const currentRaceRunners = useMemo(() => {
    if (!selectedRaceKey) return [];
    return worksheetRunners
      .filter(
        (runner) => raceKeyOf(runner.raceDate, runner.track, runner.raceNo) === selectedRaceKey
      )
      .sort(byHorseNo);
  }, [worksheetRunners, selectedRaceKey]);

  useEffect(() => {
    if (!currentRaceRunners.length) {
      setSelectedHorseKey("");
      return;
    }

    if (!selectedHorseKey || !currentRaceRunners.some((r) => r.horseKey === selectedHorseKey)) {
      setSelectedHorseKey(currentRaceRunners[0].horseKey);
    }
  }, [currentRaceRunners, selectedHorseKey]);

  const selectedHorseRunner = useMemo(() => {
    return currentRaceRunners.find((runner) => runner.horseKey === selectedHorseKey) ?? null;
  }, [currentRaceRunners, selectedHorseKey]);

  const fullCareerRunsForSelectedHorse = useMemo(() => {
    if (!selectedHorseRunner) return [];
    return [...(formRunsByHorseKey.get(selectedHorseRunner.horseKey) ?? [])].sort(sortRunsDesc);
  }, [formRunsByHorseKey, selectedHorseRunner]);

  const speedMapRows = useMemo<SpeedMapRow[]>(() => {
    return [...currentRaceRunners].sort(byHorseNo).map((runner) => {
      const usableRuns = runner.matchedRuns.slice(0, 5);
      return {
        horse: runner.horse,
        horseKey: runner.horseKey,
        horseNo: runner.horseNo,
        barrier: runner.barrier,
        avg800: average(usableRuns.map((r) => r.pos800)),
        avg400: average(usableRuns.map((r) => r.pos400)),
      };
    });
  }, [currentRaceRunners]);

  const currentRaceResults = useMemo(() => {
    if (!selectedRaceKey) return [];
    const [raceDate, track, raceNoText] = selectedRaceKey.split("|");
    return resultsRows.filter((row) => {
      return (
        parseString(row.race_date) === raceDate &&
        parseString(row.track).toUpperCase() === track &&
        String(parseNumber(row.race_no) ?? "") === String(parseNumber(raceNoText) ?? "")
      );
    });
  }, [resultsRows, selectedRaceKey]);

  const currentRaceBets = useMemo(() => {
    if (!selectedRaceKey) return [];
    const [raceDate, track, raceNoText] = selectedRaceKey.split("|");

    return betsRows.filter((row) => {
      const rowDate = parseString(row.race_date || row.date || row.Date);
      const rowTrack = parseString(row.track || row.Track).toUpperCase();
      const rowRaceNo = parseNumber(row.race_no || row.RaceNo || row.race);
      return (
        rowDate === raceDate &&
        rowTrack === track &&
        String(rowRaceNo ?? "") === String(parseNumber(raceNoText) ?? "")
      );
    });
  }, [betsRows, selectedRaceKey]);

  const currentRaceMeta = currentRaceRunners[0] ?? null;

  const topRatedRunner = useMemo(() => {
    if (!currentRaceRunners.length) return null;
    return [...currentRaceRunners].sort((a, b) => {
      const aRank = a.modelRank ?? 999;
      const bRank = b.modelRank ?? 999;
      if (aRank !== bRank) return aRank - bRank;

      const aRated = a.ratedPrice ?? 9999;
      const bRated = b.ratedPrice ?? 9999;
      if (aRated !== bRated) return aRated - bRated;

      return byHorseNo(a, b);
    })[0];
  }, [currentRaceRunners]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-7xl mx-auto rounded-2xl border border-slate-800 bg-slate-900 p-6">
          Loading EDGEiQ RACING"
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 text-white p-6">
        <div className="max-w-7xl mx-auto rounded-2xl border border-red-800 bg-slate-900 p-6">
          <div className="text-lg font-semibold text-red-300">Data load failed</div>
          <div className="mt-2 text-sm text-slate-300">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-7xl mx-auto p-4 md:p-6 space-y-4">
        <header className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-slate-400">
                EDGEiQ RACING
              </div>
              <h1 className="mt-1 text-2xl md:text-3xl font-bold text-white">
                Live Race Analysis
              </h1>
              {currentRaceMeta ? (
                <div className="mt-2 text-sm text-slate-300">
                  {currentRaceMeta.raceDate} {currentRaceMeta.track} Race {currentRaceMeta.raceNo}
                  {" "}
                  {currentRaceMeta.distance ? `${Math.round(currentRaceMeta.distance)}m` : ""}
                  {" "}
                  {currentRaceMeta.raceClass || ""}
                  {" "}
                  {currentRaceMeta.trackCondition || ""}
                </div>
              ) : (
                <div className="mt-2 text-sm text-slate-400">No race selected</div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full lg:w-auto">
              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 min-w-[180px]">
                <div className="text-[11px] uppercase tracking-widest text-slate-500">
                  Race selector
                </div>
                <select
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none"
                  value={selectedRaceKey}
                  onChange={(e) => setSelectedRaceKey(e.target.value)}
                >
                  {raceOptions.map((race) => (
                    <option key={race.key} value={race.key}>
                      {race.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 min-w-[160px]">
                <div className="text-[11px] uppercase tracking-widest text-slate-500">
                  Winning Figure
                </div>
                <div className="mt-2 text-2xl font-bold">
                  {currentRaceMeta?.winningFigure?.toFixed(2) ?? ""}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 min-w-[160px]">
                <div className="text-[11px] uppercase tracking-widest text-slate-500">
                  Top Rated
                </div>
                <div className="mt-2 text-sm font-semibold text-white">
                  {topRatedRunner?.horse ?? ""}
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  Rated {priceText(topRatedRunner?.ratedPrice ?? null)}
                </div>
              </div>
            </div>
          </div>
        </header>

        <nav className="flex flex-wrap gap-2">
          {[
            ["worksheet", "Worksheet"],
            ["ratings", "Ratings"],
            ["form", "Form"],
            ["speedmap", "Speed Map"],
            ["performance", "Performance"],
            ["results", "Results"],
            ["bets", "Bets"],
          ].map(([key, label]) => {
            const active = tab === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key as TabKey)}
                className={`rounded-2xl px-4 py-2 text-sm font-semibold transition ${
                  active
                    ? "bg-[#07101d] text-slate-950"
                    : "border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800"
                }`}
              >
                {label}
              </button>
            );
          })}
        </nav>

        {tab === "worksheet" && (
          <Worksheet
            runners={currentRaceRunners}
            selectedHorseKey={selectedHorseKey}
            onSelectHorse={setSelectedHorseKey}
          />
        )}

        {tab === "ratings" && (
          <RatingsTab
            runners={currentRaceRunners}
            selectedHorseKey={selectedHorseKey}
            onSelectHorse={setSelectedHorseKey}
          />
        )}

        {tab === "form" && (
          <FormTab
            runners={currentRaceRunners}
            selectedHorseKey={selectedHorseKey}
            onSelectHorse={setSelectedHorseKey}
            selectedHorseRunner={selectedHorseRunner}
            fullCareerRuns={fullCareerRunsForSelectedHorse}
          />
        )}

        {tab === "speedmap" && (
          <SimplePanel title="Speed Map">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-950/80 text-slate-400">
                  <tr>
                    <th className="px-3 py-2 text-left">Horse</th>
                    <th className="px-3 py-2 text-left">Bar</th>
                    <th className="px-3 py-2 text-left">@800 Avg</th>
                    <th className="px-3 py-2 text-left">@400 Avg</th>
                  </tr>
                </thead>
                <tbody>
                  {speedMapRows.map((row) => (
                    <tr key={row.horseKey} className="border-t border-slate-800">
                      <td className="px-3 py-2">{row.horse}</td>
                      <td className="px-3 py-2">{row.barrier ?? ""}</td>
                      <td className="px-3 py-2">{row.avg800 !== null ? row.avg800.toFixed(1) : ""}</td>
                      <td className="px-3 py-2">{row.avg400 !== null ? row.avg400.toFixed(1) : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SimplePanel>
        )}

        {tab === "performance" && (
          <SimplePanel title="Performance">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {[...currentRaceRunners].sort(byHorseNo).map((runner) => (
                <div
                  key={runner.horseKey}
                  className="rounded-2xl border border-slate-800 bg-slate-950 p-4"
                >
                  <div className="font-semibold">{runner.horse}</div>
                  <div className="mt-2 text-sm text-slate-400">5LS  1LS</div>
                  <div className="mt-2 flex flex-wrap gap-2 text-sm">
                    {[runner.last5.ls5, runner.last5.ls4, runner.last5.ls3, runner.last5.ls2, runner.last5.ls1].map(
                      (v, i) => (
                        <span
                          key={i}
                          className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1"
                        >
                          {v !== null ? v.toFixed(1) : ""}
                        </span>
                      )
                    )}
                  </div>
                </div>
              ))}
            </div>
          </SimplePanel>
        )}

        {tab === "results" && (
          <SimplePanel title="Results">
            <div className="text-sm text-slate-400 mb-3">
              Matching rows: {currentRaceResults.length}
            </div>
            <PreviewTable rows={currentRaceResults} />
          </SimplePanel>
        )}

        {tab === "bets" && (
          <SimplePanel title="Bets">
            <div className="text-sm text-slate-400 mb-3">
              Matching rows: {currentRaceBets.length}
            </div>
            <PreviewTable rows={currentRaceBets} />
          </SimplePanel>
        )}
      </div>
    </div>
  );
}

function SimplePanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-300">
        {title}
      </div>
      {children}
    </div>
  );
}

function PreviewTable({ rows }: { rows: any[] }) {
  if (!rows || rows.length === 0) {
    return <div className="text-slate-400 text-sm">No data</div>;
  }

  const columns = Object.keys(rows[0] || {});

  return (
    <div className="overflow-auto max-h-[500px] border border-slate-800 rounded-xl">
      <table className="min-w-full text-xs text-left">
        <thead className="bg-slate-900 sticky top-0">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-3 py-2 text-slate-400">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 50).map((row, idx) => (
            <tr key={idx} className="border-t border-slate-800">
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 whitespace-nowrap">
                  {row[col] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;




