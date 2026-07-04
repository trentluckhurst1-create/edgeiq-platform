import React from "react";
import FormGuide from "./FormGuide";
import PerformanceGraph from "./PerformanceGraph";

interface RunnerRow {
  horse: string;
  barrier?: number;
  jockey?: string;
  trainer?: string;
  rating?: number;
  rated_price?: number;
  market_price?: number;
  overlay_pct?: number;
  edge_pct?: number;
  map_position?: string;
  best_bet?: boolean;
  value_flag?: boolean;
  risk_flag?: boolean;
  runs_count_total?: number;
  recent_runs_compact?: string;
  avg_margin_last_5?: number;
  avg_sp_last_5?: number;
  last_3_avg_rating?: number;
  last_5_avg_rating?: number;
  last_10_best_rating?: number;
  same_track_runs?: number;
  same_distance_band_runs?: number;
  jumpout_or_trial_runs?: number;
}

interface FormRunRow {
  horse: string;
  date: string;
  track: string;
  distance?: number;
  barrier?: number;
  jockey?: string;
  finish?: number;
  margin?: number;
  sp?: number;
  track_condition?: string;
  rating?: number;
  race_class?: string;
  race_name?: string;
  field_size?: number;
  weight_carried?: number;
  race_quality_name?: string;
  historical_race_rating?: number;
  historical_race_strength?: number;
  is_trial?: boolean;
}

interface Props {
  runner: RunnerRow | null;
  runs: FormRunRow[];
}

function formatPrice(value?: number) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "-";
}

function formatPct(value?: number) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "-";
}

function formatNumber(value?: number, decimals = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(decimals) : "-";
}

function isTrialRun(run: FormRunRow) {
  if (typeof run.is_trial === "boolean") return run.is_trial;

  const text = `${run.race_class || ""} ${run.race_name || ""}`.toLowerCase();
  return (
    text.includes("jump out") ||
    text.includes("jumpout") ||
    text.includes("trial") ||
    text.includes("-trl")
  );
}

function getOfficialRuns(runs: FormRunRow[]) {
  return runs.filter((run) => !isTrialRun(run));
}

function getTrialRuns(runs: FormRunRow[]) {
  return runs.filter((run) => isTrialRun(run));
}

function bestRecentRating(runs: FormRunRow[]) {
  const values = runs
    .map((r) => r.rating)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!values.length) return undefined;
  return Math.max(...values);
}

function avgRecentRating(runs: FormRunRow[], count: number) {
  const values = runs
    .slice(0, count)
    .map((r) => r.rating)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!values.length) return undefined;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function countTop3(runs: FormRunRow[]) {
  return runs.filter((r) => typeof r.finish === "number" && Number.isFinite(r.finish) && r.finish <= 3)
    .length;
}

function countWins(runs: FormRunRow[]) {
  return runs.filter((r) => r.finish === 1).length;
}

function bestMarginWin(runs: FormRunRow[]) {
  const wins = runs.filter(
    (r) => r.finish === 1 && typeof r.margin === "number" && Number.isFinite(r.margin)
  );
  if (!wins.length) return undefined;
  return Math.max(...wins.map((r) => r.margin as number));
}

function averageSP(runs: FormRunRow[], count: number) {
  const values = runs
    .slice(0, count)
    .map((r) => r.sp)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!values.length) return undefined;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function distanceRangeText(runs: FormRunRow[]) {
  const values = runs
    .map((r) => r.distance)
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (!values.length) return "-";
  return `${Math.min(...values)}m - ${Math.max(...values)}m`;
}

function trackConditionSummary(runs: FormRunRow[]) {
  const counts = new Map<string, number>();
  runs.forEach((r) => {
    const key = String(r.track_condition || "").trim();
    if (!key) return;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  if (!counts.size) return "-";
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
}

function classSummary(runs: FormRunRow[]) {
  const values = runs.map((r) => String(r.race_class || "").trim()).filter(Boolean);
  if (!values.length) return "-";
  return values[0];
}

function recentFinishesText(runs: FormRunRow[], count = 5) {
  const values = runs.slice(0, count).map((r) =>
    typeof r.finish === "number" && Number.isFinite(r.finish) ? String(r.finish) : "-"
  );
  return values.length ? values.join("  ") : "-";
}

function profileNotes(runner: RunnerRow, officialRuns: FormRunRow[], trialRuns: FormRunRow[]) {
  const notes: string[] = [];
  const rating = runner.rating ?? 0;
  const best = bestRecentRating(officialRuns);
  const avg3 = avgRecentRating(officialRuns, 3);
  const avg5 = avgRecentRating(officialRuns, 5);
  const wins = countWins(officialRuns);
  const top3 = countTop3(officialRuns);

  if (typeof best === "number" && best >= rating + 2) {
    notes.push("Has already produced a figure above today's required level.");
  }
  if (typeof avg3 === "number" && avg3 >= rating - 1.5) {
    notes.push("Recent figures are holding close to today's benchmark.");
  } else if (typeof avg3 === "number" && avg3 < rating - 5) {
    notes.push("Recent figures need to lift to match today's rating demand.");
  }
  if (typeof avg5 === "number" && typeof avg3 === "number" && avg3 > avg5 + 1.5) {
    notes.push("Profile suggests the horse is improving into this race.");
  }
  if (wins >= 2 || top3 >= 3) {
    notes.push("Has enough positive recent race results to suggest competitiveness.");
  }
  if (!officialRuns.length && trialRuns.length) {
    notes.push("Mostly trial/jumpout profile so far, with limited exposed race form.");
  }
  if (!officialRuns.length && !trialRuns.length) {
    notes.push("Very light exposed profile in current form file.");
  }

  return notes;
}

function whyWin(runner: RunnerRow, officialRuns: FormRunRow[]) {
  const bullets: string[] = [];
  const rating = runner.rating ?? 0;
  const best = bestRecentRating(officialRuns);
  const avg3 = avgRecentRating(officialRuns, 3);
  const top3 = countTop3(officialRuns);
  const recentStrongRun = officialRuns.some(
    (r) =>
      typeof r.rating === "number" &&
      r.rating >= rating - 1.5 &&
      typeof r.finish === "number" &&
      r.finish <= 3
  );

  if (runner.best_bet) bullets.push("Top-rated runner in the race profile.");
  if (typeof best === "number" && best >= rating + 2) {
    bullets.push("Peak race figure says the horse has the talent to win this.");
  }
  if (typeof avg3 === "number" && avg3 >= rating - 2) {
    bullets.push("Last three race ratings are strong enough to measure up here.");
  }
  if (recentStrongRun) {
    bullets.push("Recent race profile includes a competitive finish at the right level.");
  }
  if (top3 >= 2) {
    bullets.push("Recent placing pattern suggests reliable race-shape competitiveness.");
  }

  return bullets.length
    ? bullets
    : ["Needs things to go right, but there is enough underlying ability to be competitive."];
}

function whyNot(runner: RunnerRow, officialRuns: FormRunRow[]) {
  const bullets: string[] = [];
  const rating = runner.rating ?? 0;
  const avg3 = avgRecentRating(officialRuns, 3);
  const avg5 = avgRecentRating(officialRuns, 5);
  const lastRun = officialRuns[0];

  if (runner.risk_flag) {
    bullets.push("Current rating profile sits below the race's top benchmark.");
  }
  if (typeof avg3 === "number" && avg3 < rating - 4) {
    bullets.push("Recent race figures have been below today's target level.");
  }
  if (
    lastRun &&
    typeof lastRun.finish === "number" &&
    lastRun.finish >= 7 &&
    typeof lastRun.margin === "number" &&
    lastRun.margin >= 4
  ) {
    bullets.push("Most recent race run was comfortably beaten, which adds risk.");
  }
  if (typeof avg5 === "number" && avg5 < rating - 5) {
    bullets.push("Broader race profile suggests a lift is needed, not just one spike run.");
  }
  if (!officialRuns.length) {
    bullets.push("There is very little exposed race form to trust with confidence.");
  }

  return bullets.length ? bullets : ["Very few obvious knocks from the visible profile."];
}

function tagList(runner: RunnerRow, officialRuns: FormRunRow[], trialRuns: FormRunRow[]) {
  const tags: { text: string; tone?: "green" | "red" | "blue" | "gold" }[] = [];
  const best = bestRecentRating(officialRuns);
  const avg3 = avgRecentRating(officialRuns, 3);
  const wins = countWins(officialRuns);

  if (runner.best_bet) tags.push({ text: "Best Bet", tone: "gold" });
  if (runner.value_flag) tags.push({ text: "Value", tone: "green" });
  if (runner.risk_flag) tags.push({ text: "Risk", tone: "red" });
  if (typeof best === "number" && typeof runner.rating === "number" && best >= runner.rating + 2) {
    tags.push({ text: "Peak Figure Proven", tone: "blue" });
  }
  if (typeof avg3 === "number" && typeof runner.rating === "number" && avg3 >= runner.rating - 2) {
    tags.push({ text: "Recent Figures Solid", tone: "green" });
  }
  if (wins >= 2) {
    tags.push({ text: "Winning Profile", tone: "blue" });
  }
  if (countTop3(officialRuns.slice(0, 5)) >= 2) {
    tags.push({ text: "Competitive Form", tone: "blue" });
  }
  if (!officialRuns.length && trialRuns.length) {
    tags.push({ text: "Trial Profile", tone: "red" });
  }
  if (!officialRuns.length && !trialRuns.length) {
    tags.push({ text: "Light Profile", tone: "red" });
  }

  return tags;
}

export default function RunnerDetail({ runner, runs }: Props) {
  if (!runner) {
    return <div style={styles.empty}>Select a runner to view detail</div>;
  }

  const officialRuns = getOfficialRuns(runs);
  const trialRuns = getTrialRuns(runs);

  const best = bestRecentRating(officialRuns);
  const avg3 = avgRecentRating(officialRuns, 3);
  const avg5 = avgRecentRating(officialRuns, 5);
  const top3Count = countTop3(officialRuns);
  const wins = countWins(officialRuns);
  const bestWinningMargin = bestMarginWin(officialRuns);
  const avgSp3 = averageSP(officialRuns, 3);
  const tags = tagList(runner, officialRuns, trialRuns);
  const positives = whyWin(runner, officialRuns);
  const negatives = whyNot(runner, officialRuns);
  const notes = profileNotes(runner, officialRuns, trialRuns);

  return (
    <div style={styles.wrap}>
      <div style={styles.heroCard}>
        <div style={styles.heroTop}>
          <div style={styles.heroLeft}>
            <div style={styles.horseName}>{runner.horse}</div>
            <div style={styles.subLine}>
              {runner.trainer || "-"} " {runner.jockey || "-"}
            </div>
          </div>

          <div style={styles.priceBlock}>
            <div style={styles.priceLabel}>Rated</div>
            <div style={styles.priceValue}>{formatPrice(runner.rated_price)}</div>
          </div>
        </div>

        <div style={styles.tagRow}>
          {tags.map((tag, index) => (
            <span
              key={`${tag.text}-${index}`}
              style={{
                ...styles.tag,
                ...(tag.tone === "green" ? styles.tagGreen : {}),
                ...(tag.tone === "red" ? styles.tagRed : {}),
                ...(tag.tone === "blue" ? styles.tagBlue : {}),
                ...(tag.tone === "gold" ? styles.tagGold : {})
              }}
            >
              {tag.text}
            </span>
          ))}
        </div>
      </div>

      <PerformanceGraph runs={officialRuns} todayRating={runner.rating ?? 0} />

      <div style={styles.analysisGrid}>
        <div style={styles.analysisCard}>
          <div style={styles.analysisTitle}>Why Win</div>
          <ul style={styles.analysisList}>
            {positives.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>

        <div style={styles.analysisCard}>
          <div style={styles.analysisTitle}>Why Not</div>
          <ul style={styles.analysisList}>
            {negatives.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Race Snapshot</div>
        <div style={styles.metricGrid}>
          <Metric label="Barrier" value={runner.barrier ?? "-"} />
          <Metric label="Rating" value={formatNumber(runner.rating)} />
          <Metric label="Rated Price" value={formatPrice(runner.rated_price)} />
          <Metric label="Market" value={formatPrice(runner.market_price)} />
          <Metric label="Overlay" value={formatPct(runner.overlay_pct ?? runner.edge_pct)} />
          <Metric label="Map" value={runner.map_position || "-"} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Performance Profile</div>
        <div style={styles.metricGrid}>
          <Metric label="Best Recent Rating" value={formatNumber(best)} />
          <Metric label="Average Last 3" value={formatNumber(avg3)} />
          <Metric label="Average Last 5" value={formatNumber(avg5)} />
          <Metric label="Top 3 Finishes" value={top3Count} />
          <Metric label="Wins Shown" value={wins} />
          <Metric label="Best Winning Margin" value={formatNumber(bestWinningMargin)} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Suitability & Context</div>
        <div style={styles.metricGrid}>
          <Metric label="Distance Range" value={distanceRangeText(officialRuns)} />
          <Metric label="Common Going" value={trackConditionSummary(officialRuns)} />
          <Metric label="Latest Class" value={classSummary(officialRuns)} />
          <Metric label="Avg SP Last 3" value={formatNumber(avgSp3, 1)} />
          <Metric label="Recent Finishes" value={recentFinishesText(officialRuns)} />
          <Metric label="Official Starts" value={officialRuns.length} />
          <Metric label="Trials / Jumpouts" value={trialRuns.length} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Profile Notes</div>
        <div style={styles.noteCard}>
          {notes.length ? (
            <ul style={styles.noteList}>
              {notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          ) : (
            <div style={styles.noteText}>No additional notes available.</div>
          )}
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Form Guide</div>
        <FormGuide runs={runs} todayRating={runner.rating ?? 0} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={styles.metricCard}>
      <div style={styles.metricLabel}>{label}</div>
      <div style={styles.metricValue}>{value}</div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    padding: 16,
    color: "#e5e7eb"
  },
  empty: {
    padding: 24,
    color: "#94a3b8"
  },
  heroCard: {
    padding: 16,
    border: "1px solid #1f2937",
    borderRadius: 14,
    background: "linear-gradient(180deg, #0f172a 0%, #111827 100%)",
    marginBottom: 16
  },
  heroTop: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "flex-start",
    marginBottom: 12
  },
  heroLeft: {
    minWidth: 0
  },
  horseName: {
    fontSize: 26,
    fontWeight: 800,
    lineHeight: 1.1,
    marginBottom: 6
  },
  subLine: {
    fontSize: 13,
    color: "#94a3b8"
  },
  priceBlock: {
    minWidth: 92,
    textAlign: "right"
  },
  priceLabel: {
    fontSize: 12,
    color: "#94a3b8",
    marginBottom: 4
  },
  priceValue: {
    fontSize: 24,
    fontWeight: 800,
    color: "#4ade80"
  },
  tagRow: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap"
  },
  tag: {
    padding: "6px 10px",
    borderRadius: 999,
    background: "#1e293b",
    fontSize: 12,
    fontWeight: 700
  },
  tagGreen: {
    background: "rgba(34,197,94,0.18)",
    color: "#4ade80"
  },
  tagRed: {
    background: "rgba(239,68,68,0.18)",
    color: "#f87171"
  },
  tagBlue: {
    background: "rgba(59,130,246,0.18)",
    color: "#60a5fa"
  },
  tagGold: {
    background: "rgba(250,204,21,0.18)",
    color: "#facc15"
  },
  analysisGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: 12,
    marginBottom: 16
  },
  analysisCard: {
    padding: 14,
    border: "1px solid #1f2937",
    borderRadius: 12,
    background: "#0f172a"
  },
  analysisTitle: {
    fontSize: 14,
    fontWeight: 800,
    marginBottom: 8
  },
  analysisList: {
    margin: 0,
    paddingLeft: 18,
    color: "#cbd5e1",
    fontSize: 13,
    lineHeight: 1.45
  },
  section: {
    marginBottom: 16
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: 800,
    marginBottom: 10,
    color: "#f3f4f6"
  },
  metricGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: 10
  },
  metricCard: {
    padding: 12,
    border: "1px solid #1f2937",
    borderRadius: 10,
    background: "#0f172a"
  },
  metricLabel: {
    fontSize: 12,
    color: "#94a3b8",
    marginBottom: 4
  },
  metricValue: {
    fontWeight: 700,
    fontSize: 15
  },
  noteCard: {
    padding: 14,
    border: "1px solid #1f2937",
    borderRadius: 12,
    background: "#0f172a"
  },
  noteList: {
    margin: 0,
    paddingLeft: 18,
    color: "#cbd5e1",
    fontSize: 13,
    lineHeight: 1.5
  },
  noteText: {
    color: "#cbd5e1",
    fontSize: 13
  }
};


