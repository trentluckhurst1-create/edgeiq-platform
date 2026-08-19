import React, { useMemo } from "react";
import { getSilksUrl, silkFallback } from "../utils/silks";

type RawRow = Record<string, any>;

type SpeedMapTabProps = {
  biasProfile?: any[];
  raceDistance?: string | number | null;
  trackCondition?: string;
  data?: RawRow[];
  runners?: RawRow[];
  selectedMeeting?: string;
  selectedHorse?: string;
  onSelectHorse?: (horse: string) => void;
  paceRows?: RawRow[];
  raceShape?: RawRow | null;
};

type MapBand = "ON_PACE" | "MIDFIELD" | "BACKMARKER" | "UNKNOWN";

type MapRunner = {
  key: string;
  horse: string;
  shortName: string;
  saddlecloth: string;
  rawBarrier: number | null;
  barrier: number;
  barrierLabel: string;
  jockey: string;
  price: string;
  silkUrl: string;
  xPct: number;
  yPct: number;
  band: MapBand;
  zone: "front" | "mid" | "back";
};

function text(value: unknown): string {
  const s = String(value ?? "").trim();
  return !s || ["nan", "null", "undefined", "n/a", "unknown", "none"].includes(s.toLowerCase()) ? "" : s;
}

function val(row: RawRow | null | undefined, keys: string[]): string {
  if (!row) return "";
  for (const key of keys) {
    const v = text(row[key]);
    if (v) return v;
  }
  return "";
}

function cleanKey(value: unknown): string {
  return String(value ?? "").toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^A-Z0-9]/g, "");
}

function num(value: unknown): number | null {
  const raw = text(value);
  if (!raw || raw === "-") return null;
  const n = Number(raw.replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function boolish(value: unknown): boolean {
  const s = String(value ?? "").trim().toLowerCase();
  return ["1", "true", "yes", "y", "scratched", "scr", "withdrawn"].includes(s);
}

function horseName(row: RawRow): string {
  return val(row, ["horse", "Horse", "runner", "Runner", "horse_name", "runner_name", "name"]);
}

function shortHorseName(value: string): string {
  const cleaned = value.replace(/\([^)]*\)/g, "").trim();
  if (cleaned.length <= 24) return cleaned;
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length <= 2) return cleaned.slice(0, 24);
  return `${words[0]} ${words[1]}`.slice(0, 24);
}

function bestSilkUrl(row: RawRow | null | undefined): string {
  const explicit = val(row, [
    "silkUrl",
    "silk_url",
    "silks",
    "silk",
    "silk_image",
    "mobile_silk_image",
    "image",
    "runner_image",
    "tab_silk",
    "racing_silk",
    "local_silk_path",
  ]);

  if (!explicit) return getSilksUrl(row?.horse);
  if (/^https?:\/\//i.test(explicit) || explicit.startsWith("/") || explicit.startsWith("data:")) return explicit.replace(/\\/g, "/");

  const normalized = explicit.replace(/\\/g, "/");
  const publicIndex = normalized.toLowerCase().lastIndexOf("/public/");
  if (publicIndex >= 0) return normalized.slice(publicIndex + "/public".length);

  const silkIndex = normalized.toLowerCase().lastIndexOf("/silks/");
  if (silkIndex >= 0) return normalized.slice(silkIndex);

  return normalized.includes(".") ? `/${normalized.replace(/^\/+/, "")}` : getSilksUrl(row?.horse, explicit);
}

function mergeRows(speedRows: RawRow[], raceRunners: RawRow[]): RawRow[] {
  const speedByHorse = new Map<string, RawRow>();

  for (const row of speedRows) {
    const key = cleanKey(horseName(row));
    if (key) speedByHorse.set(key, row);
  }

  if (!raceRunners.length) return speedRows;

  return raceRunners
    .filter((runner) => horseName(runner))
    .map((runner) => ({ ...runner, ...(speedByHorse.get(cleanKey(horseName(runner))) ?? {}) }));
}

function saddlecloth(row: RawRow, fallback: number): string {
  return val(row, ["saddlecloth", "horse_no", "number", "runner_number", "tab_no", "horseNo", "No", "no"]) || String(fallback + 1);
}

function barrierNumber(row: RawRow): number | null {
  return num(val(row, ["barrier", "Barrier", "bar", "gate"]));
}

function priceText(row: RawRow): string {
  const price = val(row, ["live_price", "ui_price", "sportsbet_price", "market_price", "fixed_win", "price"]);
  if (!price || price === "-") return "-";
  const n = num(price);
  return n === null ? price : n.toFixed(2).replace(/\.00$/, "");
}

function runStyleText(row: RawRow): string {
  return val(row, [
    "settling_band",
    "map_position",
    "settling_position",
    "tempo_role",
    "run_style",
    "speed_map_bucket",
    "pace_profile",
    "sectional_profile",
  ]).toUpperCase();
}

function bandOf(row: RawRow): MapBand {
  const raw = runStyleText(row);

  if (raw.includes("LEAD") || raw.includes("FRONT") || raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) return "ON_PACE";
  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) return "BACKMARKER";
  if (raw.includes("MID") || raw.includes("OFF")) return "MIDFIELD";

  const barrier = barrierNumber(row);
  if (barrier !== null) {
    if (barrier <= 3) return "ON_PACE";
    if (barrier <= 7) return "MIDFIELD";
    return "BACKMARKER";
  }

  return "UNKNOWN";
}

function fallbackX(row: RawRow, index: number): number {
  const raw = runStyleText(row);
  const jitter = ((index * 7) % 11) - 5;

  if (raw.includes("LEAD") || raw.includes("FRONT")) return clamp(86 + jitter * 0.7, 80, 91);
  if (raw.includes("PACE") || raw.includes("HANDY") || raw.includes("STALK")) return clamp(70 + jitter * 1.2, 60, 79);
  if (raw.includes("OFF")) return clamp(55 + jitter * 1.3, 48, 63);
  if (raw.includes("MID")) return clamp(40 + jitter * 1.5, 30, 50);
  if (raw.includes("BACK") || raw.includes("CLOS") || raw.includes("REAR") || raw.includes("LATE")) return clamp(18 + jitter * 1.4, 8, 28);

  const score = num(row.settling_score) ?? num(row.early_speed_score) ?? num(row.barrier_speed) ?? num(row.speed_score);
  return score === null ? clamp(42 + jitter * 1.4, 32, 52) : clamp(10 + score * 0.05, 10, 88);
}

function xPosition(row: RawRow, index: number): number {
  const explicit = num(row.map_x_pct);
  if (explicit !== null) return clamp(explicit, 8, 90);
  return fallbackX(row, index);
}

function zoneOf(band: MapBand): MapRunner["zone"] {
  if (band === "ON_PACE") return "front";
  if (band === "BACKMARKER") return "back";
  return "mid";
}

function xForZone(row: RawRow, band: MapBand, indexInZone: number): number {
  const explicit = xPosition(row, indexInZone);
  const jitter = (indexInZone % 3) * 3;

  if (band === "ON_PACE") return clamp(explicit, 10 + jitter, 32);
  if (band === "BACKMARKER") return clamp(explicit, 68 + jitter, 88);
  if (band === "MIDFIELD") return clamp(explicit, 38 + jitter, 62);
  return clamp(explicit, 36, 62);
}

function yForBarrierLane(barrier: number, fieldSize: number): number {
  const safeSize = Math.max(1, fieldSize);
  const laneFromTop = safeSize - barrier;
  return ((laneFromTop + 0.5) / safeSize) * 100;
}

function classifyRows(speedRows: RawRow[], raceRunners: RawRow[]): MapRunner[] {
  const mergedRows = mergeRows(speedRows, raceRunners).filter((row) => horseName(row));

  const activeRows = mergedRows
    .filter((row) => !boolish(row.isScratched ?? row.is_scratched ?? row.scratched ?? row.runner_status ?? row.status))
    .sort((a, b) => {
      const ab = barrierNumber(a) ?? 999;
      const bb = barrierNumber(b) ?? 999;
      if (ab !== bb) return ab - bb;

      const an = num(a.horse_no ?? a.saddlecloth ?? a.number ?? a.horseNo) ?? 999;
      const bn = num(b.horse_no ?? b.saddlecloth ?? b.number ?? b.horseNo) ?? 999;
      return an - bn;
    });

  const effectiveBarrierByHorse = new Map<string, number>();
  activeRows.forEach((row, index) => {
    const key = cleanKey(horseName(row));
    if (key) effectiveBarrierByHorse.set(key, index + 1);
  });

  return activeRows
    .map((row, index) => {
      const horse = horseName(row);
      const key = cleanKey(horse);
      const rawBarrier = barrierNumber(row);
      const effectiveBarrier = effectiveBarrierByHorse.get(key) ?? index + 1;
      const band = bandOf(row);
      const zone = zoneOf(band);

      return {
        key: key || String(index),
        horse,
        shortName: shortHorseName(horse),
        saddlecloth: saddlecloth(row, index),
        rawBarrier,
        barrier: effectiveBarrier,
        barrierLabel: rawBarrier === null || rawBarrier === effectiveBarrier ? String(effectiveBarrier) : `${effectiveBarrier} from ${Math.trunc(rawBarrier)}`,
        jockey: val(row, ["jockey", "Jockey", "rider"]),
        price: priceText(row),
        silkUrl: bestSilkUrl(row),
        xPct: xForZone(row, band, effectiveBarrier - 1),
        yPct: yForBarrierLane(effectiveBarrier, activeRows.length),
        band,
        zone,
      };
    })
    .sort((a, b) => a.barrier - b.barrier);
}

function bandClass(band: MapBand): string {
  return band.toLowerCase().replace("_", "-");
}

function bandTitle(band: MapBand): string {
  if (band === "ON_PACE") return "On pace";
  if (band === "MIDFIELD") return "Midfield";
  if (band === "BACKMARKER") return "Backmarker";
  return "No map signal";
}

export default function SpeedMapTab({
  data = [],
  runners: raceRunners = [],
  selectedHorse,
  onSelectHorse,
}: SpeedMapTabProps): React.ReactElement {
  const mapRunners = useMemo(() => classifyRows(data, raceRunners), [data, raceRunners]);
  const selectedKey = cleanKey(selectedHorse);
  const barrierStack = useMemo(() => [...mapRunners].sort((a, b) => b.barrier - a.barrier), [mapRunners]);
  const laneRows = useMemo(() => barrierStack.map((runner) => runner.barrier), [barrierStack]);

  return (
    <section className="edgeiq-racecourse-map">
      <div className="racecourse-stage">
        <div className="racecourse-track" aria-label="Projected settling map">
          <div className="racecourse-zone racecourse-zone-front"><span>Front</span></div>
          <div className="racecourse-zone racecourse-zone-mid"><span>Midfield</span></div>
          <div className="racecourse-zone racecourse-zone-start"><span>Barrier</span></div>
          <div className="racecourse-direction-line" />
          {laneRows.map((barrier) => (
            <div className="racecourse-lane" style={{ top: `${yForBarrierLane(barrier, mapRunners.length)}%` }} key={barrier} />
          ))}

          {mapRunners.map((runner) => (
            <button
              type="button"
              key={runner.key}
              className={`racecourse-runner ${bandClass(runner.band)} ${runner.key === selectedKey ? "selected" : ""}`}
              style={{ left: `${runner.xPct}%`, top: `${runner.yPct}%` }}
              onClick={() => onSelectHorse?.(runner.horse)}
              title={`${runner.horse} | B${runner.barrierLabel} | ${bandTitle(runner.band)} | ${runner.price}`}
            >
              <span className="racecourse-runner-pulse" />
              <span className="racecourse-runner-no">{runner.saddlecloth}</span>
              <span className="racecourse-silk">
                <img src={runner.silkUrl || getSilksUrl(runner.horse)} alt="" onError={silkFallback} />
              </span>
              <strong>{runner.shortName}</strong>
            </button>
          ))}
        </div>

        <aside
          className="racecourse-barriers"
          aria-label="Compressed active barriers"
          style={{ gridTemplateRows: `repeat(${Math.max(1, barrierStack.length)}, minmax(0, 1fr))` }}
        >
          {barrierStack.map((runner) => (
            <button
              type="button"
              key={`barrier-${runner.key}`}
              className={`racecourse-barrier-runner ${bandClass(runner.band)} ${runner.key === selectedKey ? "selected" : ""}`}
              onClick={() => onSelectHorse?.(runner.horse)}
              title={`${runner.horse} | B${runner.barrierLabel}`}
            >
              <span className="racecourse-barrier-number">{runner.barrier}</span>
              <span className="racecourse-barrier-silk">
                <img src={runner.silkUrl || getSilksUrl(runner.horse)} alt="" onError={silkFallback} />
              </span>
              <strong>{runner.shortName}</strong>
              {runner.price && runner.price !== "-" ? <em>{runner.price}</em> : null}
            </button>
          ))}
        </aside>
      </div>
    </section>
  );
}
