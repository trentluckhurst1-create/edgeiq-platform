import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import RatingsTab from "./components/RatingsTab";

type TabKey =
  | "Worksheet"
  | "Ratings"
  | "Form"
  | "Speed Map"
  | "Performance"
  | "Results"
  | "Bets";

type MarketRow = Record<string, string>;
type FormFeatureRow = Record<string, string>;

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

function parseNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim().replace("$", "");
  if (!text || text === "-" || text.toLowerCase() === "nan") return null;
  const num = Number(text);
  return Number.isFinite(num) ? num : null;
}

function parseString(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function parseScratched(value: unknown): boolean {
  const text = String(value ?? "").trim().toLowerCase();
  return text === "1" || text === "true" || text === "yes";
}

function normalizeHorseKey(row: Record<string, string>): string {
  return (
    parseString(row.horse_key) ||
    parseString(row.field_horse_key) ||
    parseString(row.horse).toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim()
  );
}

function raceKeyOf(raceDate: string, track: string, raceNo: number): string {
  return `${raceDate}|${track}|${raceNo}`;
}

async function loadCsv<T extends Record<string, string>>(url: string): Promise<T[]> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}`);
  }
  const text = await response.text();
  const parsed = Papa.parse<T>(text, { header: true, skipEmptyLines: true });
  return parsed.data;
}

export default function App(): React.ReactElement {
  const [tab, setTab] = useState<TabKey>("Ratings");
  const [marketRows, setMarketRows] = useState<MarketRow[]>([]);
  const [formRows, setFormRows] = useState<FormFeatureRow[]>([]);
  const [selectedRaceKey, setSelectedRaceKey] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let alive = true;

    async function run(): Promise<void> {
      try {
        setLoading(true);
        setError("");

        const [market, form] = await Promise.all([
          loadCsv<MarketRow>("/data/rated_market_v2.csv"),
          loadCsv<FormFeatureRow>("/data/horse_form_features.csv").catch(() => []),
        ]);

        if (!alive) return;

        setMarketRows(market);
        setFormRows(form);
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

  const formByHorseKey = useMemo(() => {
    const map = new Map<string, FormFeatureRow>();

    for (const row of formRows) {
      const key =
        parseString(row.horse_key) ||
        parseString(row.field_horse_key) ||
        parseString(row.horse).toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim();

      if (key) map.set(key, row);
    }

    return map;
  }, [formRows]);

  const ratingRows = useMemo<RatingDisplayRow[]>(() => {
    return marketRows
      .filter((row) => parseString(row.horse) !== "")
      .map((row, index) => {
        const raceDate = parseString(row.race_date);
        const track = parseString(row.track);
        const raceNo = parseNumber(row.race_no) ?? 0;
        const horseKey = normalizeHorseKey(row);
        const form = formByHorseKey.get(horseKey);

        return {
          id: `${raceDate}-${track}-${raceNo}-${horseKey}-${index}`,
          raceKey: raceKeyOf(raceDate, track, raceNo),
          raceDate,
          track,
          raceNo,
          horse: parseString(row.horse),
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
          exp: parseNumber(form?.["3LSA"]) ?? parseNumber(form?.["PEAK"]) ?? null,
          ls1: parseNumber(form?.["1LS"]),
          ls2: parseNumber(form?.["2LS"]),
          ls3: parseNumber(form?.["3LS"]),
          ls4: parseNumber(form?.["4LS"]),
          ls5: parseNumber(form?.["5LS"]),
          peak: parseNumber(form?.["PEAK"]),
        };
      });
  }, [marketRows, formByHorseKey]);

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
          if (a.modelRank !== null && b.modelRank !== null) return a.modelRank - b.modelRank;
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

  const topRated = currentRace?.rows.find((r) => !r.isScratched && r.modelRank === 1)
    ?? currentRace?.rows.find((r) => !r.isScratched)
    ?? null;

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
                selectedHorseKey=""
                onSelectHorse={() => {}}
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

