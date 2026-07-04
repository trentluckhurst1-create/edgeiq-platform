from pathlib import Path

path = Path(r".\src\components\SpeedMapTab.tsx")

path.write_text(r'''
import { useMemo } from "react";
import { getSilksUrl, silkFallback } from "../utils/silks";

type RawRow = Record<string, any>;

type SpeedMapTabProps = {
  data?: RawRow[];
  selectedMeeting?: string;
  selectedHorse?: string;
  onSelectHorse?: (horse: string) => void;
  paceRows?: RawRow[];
  raceShape?: RawRow | null;
};

type Runner = {
  horse: string;
  saddlecloth: string;
  jockey: string;
  barrier: number;
  spd: number;
  silkUrl: string;
  mapPosition: string;
  isScratched: boolean;
};

function val(row: RawRow | null | undefined, keys: string[]) {
  if (!row) return "";
  for (const k of keys) {
    const v = row[k];
    if (v !== undefined && v !== null && String(v).trim() !== "") return String(v).trim();
  }
  return "";
}

function clean(x: any) {
  return String(x ?? "").toUpperCase().replace(/\([^)]*\)/g, "").replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
}

function num(x: any) {
  const n = Number(String(x ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function boolish(x: any): boolean {
  const s = String(x ?? "").trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "y";
}

function pos(x: any) {
  const v = clean(x);
  if (v.includes("LEAD")) return "LEADER";
  if (v.includes("PACE")) return "ON PACE";
  if (v.includes("BACK") || v.includes("CLOS")) return "BACKMARKER";
  return "MIDFIELD";
}

function runnerFrom(row: RawRow): Runner {
  const horse = val(row, ["horse", "Horse", "runner", "Runner", "horse_name", "runner_name", "name"]);
  const sectionalWeapon = num(val(row, ["sectional_weapon_score", "sectional_strength_score"]));
  const latePower = num(val(row, ["late_power_index"]));
  const rawSpeed = num(val(row, ["speed_score", "spd", "early_speed_score", "settling_score"]));
  const style = pos(val(row, ["map_position", "map_style", "speed_map_bucket", "run_style", "speed_map", "map_bucket", "bucket", "position"]));

  let spd = rawSpeed || sectionalWeapon || latePower || 50;

  if (style === "LEADER") spd = Math.max(spd, 82);
  if (style === "ON PACE") spd = Math.max(spd, 68);
  if (style === "MIDFIELD") spd = Math.max(spd, 48);
  if (style === "BACKMARKER") spd = Math.max(spd, 28);

  return {
    horse,
    saddlecloth: val(row, ["saddlecloth", "number", "runner_number", "tab_no", "horse_no", "No", "no"]),
    jockey: val(row, ["jockey", "Jockey"]),
    barrier: num(val(row, ["barrier", "Barrier", "bar", "gate"])),
    spd: Math.max(1, Math.min(100, Math.round(spd))),
    silkUrl: val(row, ["silk_url", "silkUrl", "silks", "silk", "image"]),
    mapPosition: style,
    isScratched: boolish(val(row, ["is_scratched", "isScratched", "scratched"])),
  };
}

function styleSortValue(style: string) {
  if (style === "LEADER") return 95;
  if (style === "ON PACE") return 75;
  if (style === "MIDFIELD") return 55;
  return 35;
}

export default function SpeedMapTab({
  data = [],
  selectedHorse,
  onSelectHorse,
  paceRows = [],
  raceShape = null,
}: SpeedMapTabProps) {
  const paceByHorse = useMemo(() => {
    const map = new Map<string, RawRow>();
    paceRows.forEach((row) => {
      const k1 = clean(val(row, ["horse_key", "horse"])).replace(/[^A-Z0-9]/g, "");
      const k2 = clean(val(row, ["horse"])).replace(/[^A-Z0-9]/g, "");
      if (k1) map.set(k1, row);
      if (k2) map.set(k2, row);
    });
    return map;
  }, [paceRows]);

  const runners = useMemo(() => {
    return data
      .map((row) => {
        const runner = runnerFrom(row);
        const pace = paceByHorse.get(clean(runner.horse).replace(/[^A-Z0-9]/g, ""));
        const paceStyle = val(pace, ["run_style"]);
        const mapPosition = paceStyle ? pos(paceStyle) : runner.mapPosition;
        return {
          ...runner,
          mapPosition,
          spd: runner.spd || styleSortValue(mapPosition),
        };
      })
      .filter((r) => r.horse && r.barrier > 0 && !r.isScratched)
      .sort((a, b) => a.spd - b.spd || a.barrier - b.barrier);
  }, [data, paceByHorse]);

  const tempo = String(raceShape?.projected_tempo_shape || "").trim() || "UNKNOWN";
  const pressure = String(raceShape?.pressure_index || "").trim() || "0";
  const shape = String(raceShape?.preferred_archetype || "").trim() || "-";
  const confidence = String(raceShape?.shape_confidence || "").trim() || "LOW";

  return (
    <section className="edgeiq-speed terminal-panel-stack">
      <div className="edgeiq-speed-benchmark">
        <div className="edgeiq-speed-benchmark-head">
          <div>
            <div className="edgeiq-speed-kicker">EDGEiQ TRUE SPEED MAP</div>
            <h2>200m Settling Map</h2>
            <p>Benchmark bar · higher SPD projects further back in running</p>
          </div>

          <div className="edgeiq-speed-summary">
            <div><span>Tempo</span><strong>{tempo}</strong></div>
            <div><span>Pressure</span><strong>{pressure}/100</strong></div>
            <div><span>Shape</span><strong>{shape}</strong></div>
            <div><span>Confidence</span><strong>{confidence}</strong></div>
          </div>
        </div>

        <div className="edgeiq-speed-table">
          <div className="edgeiq-speed-row edgeiq-speed-header">
            <span>#</span>
            <span>Horse</span>
            <span>Jockey</span>
            <span>Barrier</span>
            <span>SPD</span>
            <span className="scale">0</span>
            <span className="scale">10</span>
            <span className="scale">20</span>
            <span className="scale">30</span>
            <span className="scale">40</span>
            <span className="scale">50</span>
            <span className="scale">60</span>
            <span className="scale">70</span>
            <span className="scale">80</span>
            <span className="scale">90</span>
            <span className="scale">100</span>
          </div>

          {runners.map((runner) => {
            const selected = clean(selectedHorse) === clean(runner.horse);
            return (
              <button
                key={`${runner.horse}-${runner.saddlecloth}`}
                type="button"
                className={`edgeiq-speed-row ${selected ? "selected" : ""}`}
                onClick={() => onSelectHorse?.(runner.horse)}
              >
                <span>{runner.saddlecloth || "-"}</span>

                <span className="horse">
                  <img src={getSilksUrl(runner.horse, runner.silkUrl)} alt="" onError={silkFallback} />
                  <strong>{runner.horse}</strong>
                </span>

                <span>{runner.jockey || "-"}</span>
                <span>{runner.barrier || "-"}</span>
                <span className="spd">{runner.spd}</span>

                <span className="bar-cell" style={{ gridColumn: "6 / 16" }}>
                  <i style={{ width: `${runner.spd}%` }} />
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
''', encoding="utf-8")

print("REBUILT SpeedMapTab AS STYLE 1 BENCHMARK BAR")
