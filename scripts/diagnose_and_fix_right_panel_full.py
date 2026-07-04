from pathlib import Path
import re

app = Path(r".\src\App.tsx")
form = Path(r".\src\components\FormTab.tsx")

app_text = app.read_text(encoding="utf-8")
form_text = form.read_text(encoding="utf-8")

print("=" * 80)
print("DIAGNOSE RIGHT PANEL")
print("=" * 80)

print("APP PASSES speedRows:", "speedRows={currentSpeedRows}" in app_text)
print("FORM ACCEPTS speedRows:", "speedRows?" in form_text)
print("FORM USES selectedSpeed:", "selectedSpeed" in form_text)
print("FORM HAS MAP SPD:", "Map SPD" in form_text)

print("=" * 80)
print("PATCH APP FORMTAB PROP")
print("=" * 80)

pattern = r'(<FormTab\s+[\s\S]*?selectedCareerStats=\{selectedCareerStats\})([\s\S]*?/>)'

def repl(m):
    block = m.group(0)
    if "speedRows={currentSpeedRows}" not in block:
        block = block.replace(
            "selectedCareerStats={selectedCareerStats}",
            "selectedCareerStats={selectedCareerStats}\n                    speedRows={currentSpeedRows}"
        )
    return block

app_text_new, count = re.subn(pattern, repl, app_text, count=1)

if count != 1:
    raise SystemExit("FAILED: Could not find FormTab block in App.tsx")

app.write_text(app_text_new, encoding="utf-8")

print("APP PATCH COUNT:", count)
print("APP PASSES speedRows NOW:", "speedRows={currentSpeedRows}" in app_text_new)

print("=" * 80)
print("REWRITE FORMTAB CLEANLY")
print("=" * 80)

form.write_text(r'''import React, { useMemo } from "react";
import type {
  CareerStats,
  FormHistoryRow,
  FormSummary,
  FullCareerFormRow,
  RatingDisplayRow,
} from "../App";
import { getSilksUrl, silkFallback } from "../utils/silks";

type Props = {
  runners: RatingDisplayRow[];
  selectedHorseKey: string;
  onSelectHorse: (horseKey: string) => void;
  selectedHorseHistory?: FormHistoryRow[];
  selectedFullCareer?: FullCareerFormRow[];
  selectedSummary?: FormSummary | null;
  selectedCareerStats?: CareerStats | null;
  speedRows?: Record<string, any>[];
};

function safe(v: unknown): string {
  const s = String(v ?? "").trim();
  if (!s || s.toLowerCase() === "nan" || s.toLowerCase() === "null") return "-";
  return s;
}

function num(v: unknown): number | null {
  const n = Number(String(v ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function price(v: unknown): string {
  const n = num(v);
  return n === null || n <= 0 ? "-" : n.toFixed(2);
}

function rating(v: unknown): string {
  const n = num(v);
  return n === null ? "-" : n.toFixed(1);
}

function dateShort(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return safe(value);
  return d.toLocaleDateString("en-AU", { day: "2-digit", month: "short" });
}

function record(starts?: number, wins?: number, seconds?: number, thirds?: number): string {
  return `${starts ?? 0}-${wins ?? 0}-${seconds ?? 0}-${thirds ?? 0}`;
}

function canon(v: unknown): string {
  return String(v ?? "")
    .toUpperCase()
    .replace(/\([^)]*\)/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function actionFor(row: RatingDisplayRow | null): string {
  if (!row || row.isScratched) return "-";
  if (row.fakeOverlayRisk || row.highEdgeReview || !row.marketPrice || !row.ratedPrice) return "WAIT";
  if (row.edgePct == null) return "SUPPRESSED";
  if ((row.modelConfidenceScore ?? 0) < 35 && row.edgePct > 20) return "SUPPRESSED";
  if (row.edgePct >= 15) return "EXECUTE";
  if (row.edgePct >= 7) return "WATCH";
  return "PASS";
}

function selectedRow(rows: RatingDisplayRow[], selectedHorseKey: string): RatingDisplayRow | null {
  return (
    rows.find((row) => row.horseKey === selectedHorseKey) ??
    rows.find((row) => !row.isScratched) ??
    rows[0] ??
    null
  );
}

export default function FormTab({
  runners,
  selectedHorseKey,
  selectedHorseHistory = [],
  selectedFullCareer = [],
  selectedSummary = null,
  selectedCareerStats = null,
  speedRows = [],
}: Props): React.ReactElement {
  const selected = selectedRow(runners, selectedHorseKey);

  const selectedSpeed = speedRows.find((row) => {
    return canon(row.horse ?? row.horse_name ?? row.runner_name) === canon(selected?.horse);
  });

  const fullCareer = useMemo(
    () =>
      [...selectedFullCareer].sort(
        (a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime()
      ),
    [selectedFullCareer]
  );

  const source = fullCareer.length ? fullCareer : selectedHorseHistory;

  const official = [...source]
    .filter((run) => run.isOfficialRace)
    .sort((a, b) => new Date(b.runDate).getTime() - new Date(a.runDate).getTime())
    .slice(0, 5);

  const action = actionFor(selected);

  return (
    <section className="edgeiq-runner-intel terminal-card">
      <div className="runner-intel-head">
        <img src={getSilksUrl(selected?.horse, selected?.silkUrl)} alt="" onError={silkFallback} />
        <div>
          <div className="kicker">SELECTED RUNNER INTELLIGENCE</div>
          <h2>{selected?.horse ?? "-"}</h2>
          <p>No {selected?.horseNo ?? "-"} | Bar {selected?.barrier ?? "-"} | {selected?.jockey || "-"} | {selected?.trainer || "-"}</p>
        </div>
      </div>

      <div className="runner-intel-price-grid">
        <div><span>LIVE</span><strong>{price(selected?.marketPrice)}</strong></div>
        <div><span>FAIR</span><strong>{price(selected?.ratedPrice)}</strong></div>
        <div><span>EDGE</span><strong>{selected?.edgePct != null ? `${selected.edgePct.toFixed(1)}%` : "-"}</strong></div>
        <div><span>ACTION</span><strong>{action}</strong></div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Race Map DNA</div>
        <div className="runner-intel-grid">
          <div><span>MAP SPD</span><strong>{safe(selectedSpeed?.projected_spd)}</strong></div>
          <div><span>SETTLING</span><strong>{safe(selectedSpeed?.settling_band)}</strong></div>
          <div><span>DNA CONF</span><strong>{safe(selectedSpeed?.confidence)}</strong></div>
          <div><span>ARCHETYPE</span><strong>{safe(selectedSpeed?.archetype)}</strong></div>
        </div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Profile</div>
        <div className="runner-intel-grid">
          <div><span>CONF</span><strong>{selected?.modelConfidenceScore != null ? selected.modelConfidenceScore.toFixed(0) : "-"}</strong></div>
          <div><span>RUN STYLE</span><strong>{safe(selected?.run_style_cluster || selected?.sectional_profile)}</strong></div>
          <div><span>TEMPO FIT</span><strong>{safe(selected?.tempo_fit)}</strong></div>
          <div><span>LATE POWER</span><strong>{selected?.late_power_index != null ? selected.late_power_index.toFixed(0) : "-"}</strong></div>
          <div><span>BURST</span><strong>{selected?.burst_index != null ? selected.burst_index.toFixed(0) : "-"}</strong></div>
          <div><span>FATIGUE</span><strong>{selected?.fatigue_risk_index != null ? selected.fatigue_risk_index.toFixed(0) : "-"}</strong></div>
          <div><span>SECTIONAL</span><strong>{selected?.sectional_weapon_score != null ? selected.sectional_weapon_score.toFixed(0) : "-"}</strong></div>
          <div><span>GEAR</span><strong>{safe(selected?.gearChanges)}</strong></div>
        </div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Record</div>
        <div className="runner-intel-records">
          <div><span>CAREER</span><strong>{record(selectedCareerStats?.careerStarts, selectedCareerStats?.careerWins, selectedCareerStats?.careerSeconds, selectedCareerStats?.careerThirds)}</strong></div>
          <div><span>TRACK</span><strong>{record(selectedCareerStats?.trackStarts, selectedCareerStats?.trackWins, selectedCareerStats?.trackSeconds, selectedCareerStats?.trackThirds)}</strong></div>
          <div><span>DIST</span><strong>{record(selectedCareerStats?.distanceStarts, selectedCareerStats?.distanceWins, selectedCareerStats?.distanceSeconds, selectedCareerStats?.distanceThirds)}</strong></div>
          <div><span>T/D</span><strong>{record(selectedCareerStats?.trackDistanceStarts, selectedCareerStats?.trackDistanceWins, selectedCareerStats?.trackDistanceSeconds, selectedCareerStats?.trackDistanceThirds)}</strong></div>
        </div>
      </div>

      <div className="runner-intel-section">
        <div className="section-title">Last 5 Official Starts</div>
        <div className="runner-intel-runs">
          {official.map((run) => (
            <div key={run.id}>
              <span>{dateShort(run.runDate)}</span>
              <strong>{safe(run.track)}</strong>
              <span>{run.distance ? `${run.distance}m` : "-"}</span>
              <span>{safe(run.finishPos)}</span>
              <em>{displayRating(run)}</em>
            </div>
          ))}
          {!official.length ? <div className="empty">Insufficient history.</div> : null}
        </div>
      </div>
    </section>
  );
}

function displayRating(run: FormHistoryRow | FullCareerFormRow): string {
  if ("ratingDisplay" in run && run.ratingDisplay) return run.runType === "RACE" ? run.ratingDisplay : "-";
  return run.runType === "RACE" ? rating(run.runRating) : "-";
}
''', encoding="utf-8")

print("FORMTAB FULL REWRITE COMPLETE")
