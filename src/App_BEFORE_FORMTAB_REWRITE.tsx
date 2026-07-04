import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import RatingsTab from "./components/RatingsTab";
import Worksheet from "./components/Worksheet";

type TabKey =
  | "Worksheet"
  | "Ratings"
  | "Form"
  | "Speed Map"
  | "Performance"
  | "Results"
  | "Bets";

type MarketRow = Record<string, string>;
type HistoryCsvRow = Record<string, string>;

export type FormHistoryRow = {
  id: string;
  horse: string;
  horseKey: string;
  runDate: string;
  track: string;
  distance: number | null;
  raceClass: string;
  trackCondition: string;
  finishPos: string;
  margin: string;
  runRating: number | null;
  runType: string;
};

export type RatingDisplayRow = {
  id: string;
  raceKey: string;
  raceDate: string;
  track: string;
  raceNo: number;
  horse: string;
  horseKey: string;
  horseNo: number | null;
  jockey: string;
  trainer: string;
  barrier: number | null;
  raceClass: string;
  distance: number | null;
  todayRating: number | null;
  winningFigure: number | null;
  ratedPrice: number | null;
  marketPrice: number | null;
  modelRank: number | null;
  isScratched: boolean;
  exp: number | null;
  ls1: number | null;
  ls2: number | null;
  ls3: number | null;
  ls4: number | null;
  ls5: number | null;
  peak: number | null;
};

type RaceGroup = {
  key: string;
  raceDate: string;
  track: string;
  raceNo: number;
  raceClass: string;
  distance: number | null;
  winningFigure: number | null;
  rows: RatingDisplayRow[];
};

function parseString(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function parseNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim().replace("$", "");
  if (!text || text === "-" || text.toLowerCase() === "nan") return null;
  const num = Number(text);
  return Number.isFinite(num) ? num : null;
}

function parseScratched(value: unknown): boolean {
  const text = String(value ?? "").trim().toLowerCase();
  return text === "1" || text === "true" || text === "yes";
}

function normalizeHorseName(value: unknown): string {
  return parseString(value)
    .toUpperCase()
    .normalize("NFKD")
    .replace(/[^\x00-\x7F]/g, "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function raceKeyOf(raceDate: string, track: string, raceNo: number): string {
  return `${raceDate}|${track}|${raceNo}`;
}

function normalizeRunType(runType: string, raceClass: string): string {
  const rt = parseString(runType).toUpperCase();
  const rc = parseString(raceClass).toUpperCase();

  if (rt.includes("JUMPOUT") || rt.includes("JUMP OUT") || rt === "JUMPOUT") {
    return "J/OUT";
  }

  if (rt.includes("TRIAL")) {
    return "TRIAL";
  }

  if (rc.endsWith("-BT") || rc.includes("OPEN-BT") || rc.includes("MDN-BT") || rc.includes("C1-BT") || rc.includes("C2-BT") || rc.includes("C3-BT")) {
    return "TRIAL";
  }

  return "RACE";
}

async function loadCsv<T extends Record<string, string>>(url: string): Promise<T[]> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}`);
  }
  const text = await response.text();
  const parsed = Papa.parse<T>(text, {
    header: true,
    skipEmptyLines: true,
  });
  return parsed.data;
}

function getLast5RaceRatings(history: FormHistoryRow[]): {
  ls1: number | null;
  ls2: number | null;
  ls3: number | null;
  ls4: number | null;
  ls5: number | null;
  peak: number | null;
} {
  const ratedRuns = history
    .filter((r) => r.runType === "RACE" && r.runRating !== null)
    .sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime())
    .slice(0, 5);

  const ratings = ratedRuns.map((r) => r.runRating as number);

  return {
    ls1: ratedRuns[0]?.runRating ?? null,
    ls2: ratedRuns[1]?.runRating ?? null,
    ls3: ratedRuns[2]?.runRating ?? null,
    ls4: ratedRuns[3]?.runRating ?? null,
    ls5: ratedRuns[4]?.runRating ?? null,
    peak: ratings.length ? Math.max(...ratings) : null,
  };
}

export default function App(): React.ReactElement {
  const [tab, setTab] = useState<TabKey>("Worksheet");
  const [marketRows, setMarketRows] = useState<MarketRow[]>([]);
  const [historyRows, setHistoryRows] = useState<HistoryCsvRow[]>([]);
  const [selectedRaceKey, setSelectedRaceKey] = useState<string>("");
  const [selectedHorseKey, setSelectedHorseKey] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let alive = true;

    async function run(): Promise<void> {
      try {
        setLoading(true);
        setError("");

        const [market, history] = await Promise.all([
          loadCsv<MarketRow>("/data/rated_market_v2.csv"),
          loadCsv<HistoryCsvRow>("/data/runner_form_history.csv"),
        ]);

        if (!alive) return;

        setMarketRows(market);
        setHistoryRows(history);
      } catch (err) {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        if (alive) setLoading(false);
      }
    }

    void run();

    return () => {
      alive = false;
    };
  }, []);

  const historyByHorseKey = useMemo(() => {
    const map = new Map<string, FormHistoryRow[]>();

    for (const row of historyRows) {
      const horse = parseString(row.horse);
      const horseKey = normalizeHorseName(horse);
      if (!horseKey) continue;

      const raceClass = parseString(row.race_class);
      const item: FormHistoryRow = {
        id: `${horseKey}-${parseString(row.run_date)}-${parseString(row.track)}-${parseString(row.distance)}`,
        horse,
        horseKey,
        runDate: parseString(row.run_date),
        track: parseString(row.track),
        distance: parseNumber(row.distance),
        raceClass,
        trackCondition: parseString(row.track_condition),
        finishPos: parseString(row.finish_pos),
        margin: parseString(row.margin),
        runRating: parseNumber(row.run_rating),
        runType: normalizeRunType(parseString(row.run_type), raceClass),
      };

      if (!map.has(horseKey)) map.set(horseKey, []);
      map.get(horseKey)!.push(item);
    }

    for (const [key, rows] of map.entries()) {
      rows.sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime());
      map.set(key, rows);
    }

    return map;
  }, [historyRows]);

  const ratingRows = useMemo<RatingDisplayRow[]>(() => {
    return marketRows
      .filter((row) => parseString(row.horse) !== "")
      .map((row, index) => {
        const raceDate = parseString(row.race_date);
        const track = parseString(row.track);
        const raceNo = parseNumber(row.race_no) ?? 0;
        const horse = parseString(row.horse);
        const horseKey = normalizeHorseName(horse);
        const history = historyByHorseKey.get(horseKey) ?? [];
        const last5 = getLast5RaceRatings(history);

        return {
          id: `${raceDate}-${track}-${raceNo}-${horseKey}-${index}`,
          raceKey: raceKeyOf(raceDate, track, raceNo),
          raceDate,
          track,
          raceNo,
          horse,
          horseKey,
          horseNo: parseNumber(row.horse_no),
          jockey: parseString(row.jockey),
          trainer: parseString(row.trainer),
          barrier: parseNumber(row.barrier),
          raceClass: parseString(row.race_class),
          distance: parseNumber(row.distance),
          todayRating: parseNumber(row.today_rating),
          winningFigure: parseNumber(row.winning_figure),
          ratedPrice: parseNumber(row.rated_price),
          marketPrice: parseNumber(row.market_price),
          modelRank: parseNumber(row.model_rank),
          isScratched: parseScratched(row.is_scratched),
          exp: last5.peak,
          ls1: last5.ls1,
          ls2: last5.ls2,
          ls3: last5.ls3,
          ls4: last5.ls4,
          ls5: last5.ls5,
          peak: last5.peak,
        };
      });
  }, [marketRows, historyByHorseKey]);

  const raceGroups = useMemo<RaceGroup[]>(() => {
    const grouped = new Map<string, RatingDisplayRow[]>();

    for (const row of ratingRows) {
      if (!grouped.has(row.raceKey)) grouped.set(row.raceKey, []);
      grouped.get(row.raceKey)!.push(row);
    }

    return [...grouped.entries()]
      .map(([key, rows]) => {
        const first = rows[0];
        const sortedRows = [...rows].sort((a, b) => {
          if (a.isScratched !== b.isScratched) return a.isScratched ? 1 : -1;
          if (a.horseNo !== null && b.horseNo !== null) return a.horseNo - b.horseNo;
          return a.horse.localeCompare(b.horse);
        });

        return {
          key,
          raceDate: first.raceDate,
          track: first.track,
          raceNo: first.raceNo,
          raceClass: first.raceClass,
          distance: first.distance,
          winningFigure: first.winningFigure,
          rows: sortedRows,
        };
      })
      .sort((a, b) => a.key.localeCompare(b.key));
  }, [ratingRows]);

  useEffect(() => {
    if (!selectedRaceKey && raceGroups.length > 0) {
      setSelectedRaceKey(raceGroups[0].key);
    }
  }, [raceGroups, selectedRaceKey]);

  const currentRace = useMemo(() => {
    return raceGroups.find((race) => race.key === selectedRaceKey) ?? raceGroups[0] ?? null;
  }, [raceGroups, selectedRaceKey]);

  useEffect(() => {
    if (!currentRace) return;
    const firstActive =
      currentRace.rows.find((r) => !r.isScratched)?.horseKey ??
      currentRace.rows[0]?.horseKey ??
      "";
    setSelectedHorseKey(firstActive);
  }, [currentRace?.key]);

  const selectedHorseHistory = useMemo(() => {
    return historyByHorseKey.get(selectedHorseKey) ?? [];
  }, [historyByHorseKey, selectedHorseKey]);

  const topRated =
    currentRace?.rows.find((r) => !r.isScratched && r.modelRank === 1) ??
    currentRace?.rows.find((r) => !r.isScratched) ??
    null;

  const tabs: TabKey[] = ["Worksheet", "Ratings", "Form", "Speed Map", "Performance", "Results", "Bets"];

  return (
    <div className="min-h-screen bg-[#0f0f10] text-white">
      <div className="mx-auto max-w-[1600px] px-4 py-5">
        <div className="rounded-md border border-[#2a2a2a] bg-[#151515] shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
          <div className="border-b border-[#262626] bg-[linear-gradient(180deg,#1d1d1d_0%,#141414_100%)] px-5 py-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-[#8e8e8e]">
                  EDGEiQ RACING
                </div>
                <div className="mt-1 text-[30px] font-semibold tracking-tight text-[#f4f4f4]">
                  Live Race Analysis
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="rounded-sm border border-[#303030] bg-[#202020] px-3 py-2 text-[11px] text-[#d2d2d2]">
                  Today
                </div>
                <div className="rounded-sm border border-[#303030] bg-[#202020] px-3 py-2 text-[11px] text-[#d2d2d2]">
                  Future
                </div>
                <div className="rounded-sm border border-[#6d5722] bg-[#6d5722] px-3 py-2 text-[11px] font-medium text-white">
                  Ratings Engine Live
                </div>
              </div>
            </div>
          </div>

          <div className="border-b border-[#262626] bg-[#121212] px-5 py-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr_1fr_1fr]">
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-[0.16em] text-[#808080]">
                  Meeting / Race
                </div>
                <select
                  className="w-full rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-3 text-[14px] text-[#f2f2f2] outline-none"
                  value={currentRace?.key ?? ""}
                  onChange={(e) => setSelectedRaceKey(e.target.value)}
                >
                  {raceGroups.map((race) => (
                    <option key={race.key} value={race.key}>
                      {race.track}  Race {race.raceNo}  {race.distance ? `${race.distance}m` : "-"}  {race.raceClass || "-"}
                    </option>
                  ))}
                </select>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Winning Figure</div>
                <div className="mt-1 text-[22px] font-semibold text-[#f5f5f5]">
                  {currentRace?.winningFigure !== null && currentRace?.winningFigure !== undefined
                    ? currentRace.winningFigure.toFixed(2)
                    : "-"}
                </div>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Top Rated</div>
                <div className="mt-1 text-[16px] font-semibold text-[#f5f5f5]">
                  {topRated?.horse ?? "-"}
                </div>
                <div className="mt-1 text-[11px] text-[#bbbbbb]">
                  Rated {topRated?.ratedPrice !== null && topRated?.ratedPrice !== undefined ? topRated.ratedPrice.toFixed(2).replace(/\.00$/, "") : "-"}
                </div>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Runners</div>
                <div className="mt-1 text-[22px] font-semibold text-[#f5f5f5]">
                  {currentRace?.rows.length ?? 0}
                </div>
              </div>
            </div>
          </div>

          <div className="border-b border-[#262626] bg-[#171717] px-5 py-2">
            <div className="flex flex-wrap items-center gap-2">
              {tabs.map((tabName) => (
                <button
                  key={tabName}
                  type="button"
                  onClick={() => setTab(tabName)}
                  className={
                    tab === tabName
                      ? "rounded-sm border border-[#725a21] bg-[#725a21] px-3 py-1.5 text-[13px] font-medium text-white"
                      : "rounded-sm border border-[#303030] bg-[#222222] px-3 py-1.5 text-[13px] text-[#d3d3d3]"
                  }
                >
                  {tabName}
                </button>
              ))}
            </div>
          </div>

          <div className="px-5 py-5">
            {loading ? (
              <div className="rounded-md border border-[#2b2b2b] bg-[#111111] px-4 py-10 text-[14px] text-[#bcbcbc]">
                Loading live ratings...
              </div>
            ) : error ? (
              <div className="rounded-md border border-[#4a2323] bg-[#1b1111] px-4 py-10 text-[14px] text-[#f0b8b8]">
                {error}
              </div>
            ) : tab === "Ratings" ? (
              <RatingsTab
                runners={currentRace?.rows ?? []}
                selectedHorseKey={selectedHorseKey}
                onSelectHorse={setSelectedHorseKey}
              />
            ) : tab === "Worksheet" ? (
              <Worksheet
                runners={currentRace?.rows ?? []}
                selectedHorseKey={selectedHorseKey}
                onSelectHorse={setSelectedHorseKey}
                selectedHorseHistory={selectedHorseHistory}
              />
            ) : (
              <div className="rounded-md border border-[#2b2b2b] bg-[#111111] px-4 py-10 text-[14px] text-[#bcbcbc]">
                {tab} tab will be rewritten into this same UI system next.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

