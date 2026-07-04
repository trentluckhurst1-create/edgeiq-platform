import React, { useEffect, useMemo, useState } from "react";

type SummaryRow = {
  metric: string;
  value: string | number;
};

type ConfidenceRow = {
  forecast_confidence: string;
  races: string | number;
  top_pick_count: string | number;
  top_pick_winners: string | number;
  top_pick_strike_rate_pct: string | number;
  top_pick_place_rate_pct: string | number;
  avg_winner_rank: string | number;
};

type StrengthRow = {
  race_strength_label: string;
  races: string | number;
  top_pick_count: string | number;
  top_pick_winners: string | number;
  top_pick_strike_rate_pct: string | number;
  top_pick_place_rate_pct: string | number;
  avg_winner_rank: string | number;
};

type RankRow = {
  model_rank: string | number;
  races: string | number;
  top_pick_count: string | number;
  top_pick_winners: string | number;
  top_pick_strike_rate_pct: string | number;
  top_pick_place_rate_pct: string | number;
  avg_winner_rank: string | number;
};

type DailyRow = {
  race_date: string;
  races: string | number;
  top_pick_count: string | number;
  top_pick_winners: string | number;
  top_pick_place_rate_pct: string | number;
  top_pick_strike_rate_pct: string | number;
  avg_winner_model_rank: string | number;
};

type RaceReviewRow = {
  race_date: string;
  track: string;
  race_no: string | number;
  winner: string;
  winner_model_rank: string | number;
  winner_model_win_probability: string | number;
  forecast_confidence: string;
  race_strength_label: string;
  model_top_pick: string;
  top_pick_win_probability: string | number;
  top_pick_finish_position: string | number;
  top_pick_won: string | number;
};

function parseCsv(text: string): Record<string, string>[] {
  const lines = text
    .replace(/\r/g, "")
    .split("\n")
    .filter((line) => line.trim().length > 0);

  if (!lines.length) return [];

  const parseLine = (line: string): string[] => {
    const out: string[] = [];
    let cur = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      const next = line[i + 1];

      if (ch === '"' && inQuotes && next === '"') {
        cur += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = !inQuotes;
      } else if (ch === "," && !inQuotes) {
        out.push(cur);
        cur = "";
      } else {
        cur += ch;
      }
    }

    out.push(cur);
    return out.map((v) => v.trim());
  };

  const headers = parseLine(lines[0]);

  return lines.slice(1).map((line) => {
    const values = parseLine(line);
    const row: Record<string, string> = {};
    headers.forEach((h, idx) => {
      row[h] = values[idx] ?? "";
    });
    return row;
  });
}

async function loadCsv<T = Record<string, string>>(path: string): Promise<T[]> {
  const res = await fetch(`${path}?t=${Date.now()}`);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  const text = await res.text();
  return parseCsv(text) as T[];
}

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function num(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function cardMetric(summary: SummaryRow[], metric: string): string {
  const row = summary.find((r) => r.metric === metric);
  return row ? fmt(row.value) : "";
}

function statusValue(summary: SummaryRow[]): string {
  const row = summary.find((r) => r.metric === "status");
  return row ? String(row.value) : "";
}

function noteValue(summary: SummaryRow[]): string {
  const row = summary.find((r) => r.metric === "note");
  return row ? String(row.value) : "";
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      style={{
        background: "#111827",
        border: "1px solid #1f2937",
        borderRadius: 14,
        padding: 16,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          color: "#f9fafb",
          fontWeight: 700,
          fontSize: 16,
          marginBottom: 12,
          letterSpacing: 0.3,
        }}
      >
        {title}
      </div>
      {children}
    </section>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      style={{
        background: "#0b1220",
        border: "1px solid #1f2937",
        borderRadius: 12,
        padding: 14,
        minHeight: 86,
      }}
    >
      <div style={{ color: "#9ca3af", fontSize: 12, marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ color: "#ffffff", fontSize: 24, fontWeight: 800 }}>
        {value}
      </div>
    </div>
  );
}

function DataTable({
  columns,
  rows,
}: {
  columns: { key: string; label: string }[];
  rows: Record<string, unknown>[];
}) {
  return (
    <div
      style={{
        overflowX: "auto",
        border: "1px solid #1f2937",
        borderRadius: 12,
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          minWidth: 760,
          background: "#0b1220",
        }}
      >
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  textAlign: "left",
                  padding: "10px 12px",
                  borderBottom: "1px solid #1f2937",
                  color: "#9ca3af",
                  fontSize: 12,
                  fontWeight: 700,
                  background: "#0f172a",
                  position: "sticky",
                  top: 0,
                }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{
                  padding: 16,
                  color: "#9ca3af",
                  borderBottom: "1px solid #1f2937",
                }}
              >
                No rows yet.
              </td>
            </tr>
          ) : (
            rows.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td
                    key={col.key}
                    style={{
                      padding: "10px 12px",
                      borderBottom: "1px solid #172033",
                      color: "#e5e7eb",
                      fontSize: 13,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {fmt(row[col.key])}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function DashboardAnalytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  const [summary, setSummary] = useState<SummaryRow[]>([]);
  const [confidence, setConfidence] = useState<ConfidenceRow[]>([]);
  const [strength, setStrength] = useState<StrengthRow[]>([]);
  const [rankRows, setRankRows] = useState<RankRow[]>([]);
  const [daily, setDaily] = useState<DailyRow[]>([]);
  const [raceReview, setRaceReview] = useState<RaceReviewRow[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        setLoading(true);
        setError("");

        const [
          summaryData,
          confidenceData,
          strengthData,
          rankData,
          dailyData,
          reviewData,
        ] = await Promise.all([
          loadCsv<SummaryRow>("/dashboard_summary.csv"),
          loadCsv<ConfidenceRow>("/dashboard_confidence_breakdown.csv"),
          loadCsv<StrengthRow>("/dashboard_race_strength_breakdown.csv"),
          loadCsv<RankRow>("/dashboard_model_rank_breakdown.csv"),
          loadCsv<DailyRow>("/dashboard_daily_results.csv"),
          loadCsv<RaceReviewRow>("/dashboard_race_review.csv"),
        ]);

        if (cancelled) return;

        setSummary(summaryData);
        setConfidence(confidenceData);
        setStrength(strengthData);
        setRankRows(rankData);
        setDaily(dailyData);
        setRaceReview(reviewData);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load dashboard analytics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const noOverlapYet = useMemo(
    () => statusValue(summary) === "NO_OVERLAP_YET",
    [summary]
  );

  const raceReviewSorted = useMemo(() => {
    return [...raceReview].sort((a, b) => {
      const ad = a.race_date || "";
      const bd = b.race_date || "";
      if (ad !== bd) return bd.localeCompare(ad);
      const at = a.track || "";
      const bt = b.track || "";
      if (at !== bt) return at.localeCompare(bt);
      return Number(a.race_no || 0) - Number(b.race_no || 0);
    });
  }, [raceReview]);

  return (
    <div
      style={{
        padding: 18,
        background: "#030712",
        color: "#e5e7eb",
        minHeight: "100%",
      }}
    >
      <div
        style={{
          marginBottom: 18,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "#ffffff" }}>
            Model Dashboard
          </div>
          <div style={{ fontSize: 13, color: "#9ca3af", marginTop: 4 }}>
            Prediction accountability, strike rates, rank review and race-by-race model assessment.
          </div>
        </div>
      </div>

      {loading && (
        <SectionCard title="Loading">
          <div style={{ color: "#9ca3af" }}>Loading dashboard analytics"</div>
        </SectionCard>
      )}

      {!loading && error && (
        <SectionCard title="Dashboard Error">
          <div style={{ color: "#fca5a5", fontWeight: 600 }}>{error}</div>
        </SectionCard>
      )}

      {!loading && !error && (
        <>
          {noOverlapYet && (
            <SectionCard title="Status">
              <div style={{ color: "#fde68a", fontWeight: 700, marginBottom: 8 }}>
                No scored races yet
              </div>
              <div style={{ color: "#9ca3af", fontSize: 14 }}>
                {noteValue(summary) || "Predictions are being logged, but no logged races have flowed into results yet."}
              </div>
            </SectionCard>
          )}

          <SectionCard title="Summary">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 12,
              }}
            >
              <MetricCard label="Races Analysed" value={cardMetric(summary, "races_analysed")} />
              <MetricCard label="Top Pick Strike %" value={cardMetric(summary, "top_pick_strike_rate_pct")} />
              <MetricCard label="Top Pick Place %" value={cardMetric(summary, "top_pick_place_rate_pct")} />
              <MetricCard label="Winners From Top 3 %" value={cardMetric(summary, "winners_from_top3_pct")} />
              <MetricCard label="Avg Winner Rank" value={cardMetric(summary, "avg_winner_model_rank")} />
              <MetricCard label="Median Winner Rank" value={cardMetric(summary, "median_winner_model_rank")} />
            </div>
          </SectionCard>

          <SectionCard title="Confidence Breakdown">
            <DataTable
              columns={[
                { key: "forecast_confidence", label: "Confidence" },
                { key: "races", label: "Races" },
                { key: "top_pick_count", label: "Top Picks" },
                { key: "top_pick_winners", label: "Top Pick Winners" },
                { key: "top_pick_strike_rate_pct", label: "Strike %" },
                { key: "top_pick_place_rate_pct", label: "Place %" },
                { key: "avg_winner_rank", label: "Avg Winner Rank" },
              ]}
              rows={confidence as unknown as Record<string, unknown>[]}
            />
          </SectionCard>

          <SectionCard title="Race Strength Breakdown">
            <DataTable
              columns={[
                { key: "race_strength_label", label: "Race Strength" },
                { key: "races", label: "Races" },
                { key: "top_pick_count", label: "Top Picks" },
                { key: "top_pick_winners", label: "Top Pick Winners" },
                { key: "top_pick_strike_rate_pct", label: "Strike %" },
                { key: "top_pick_place_rate_pct", label: "Place %" },
                { key: "avg_winner_rank", label: "Avg Winner Rank" },
              ]}
              rows={strength as unknown as Record<string, unknown>[]}
            />
          </SectionCard>

          <SectionCard title="Model Rank Breakdown">
            <DataTable
              columns={[
                { key: "model_rank", label: "Model Rank" },
                { key: "races", label: "Races" },
                { key: "top_pick_count", label: "Top Picks" },
                { key: "top_pick_winners", label: "Top Pick Winners" },
                { key: "top_pick_strike_rate_pct", label: "Strike %" },
                { key: "top_pick_place_rate_pct", label: "Place %" },
                { key: "avg_winner_rank", label: "Avg Winner Rank" },
              ]}
              rows={rankRows as unknown as Record<string, unknown>[]}
            />
          </SectionCard>

          <SectionCard title="Daily Results">
            <DataTable
              columns={[
                { key: "race_date", label: "Date" },
                { key: "races", label: "Races" },
                { key: "top_pick_count", label: "Top Picks" },
                { key: "top_pick_winners", label: "Top Pick Winners" },
                { key: "top_pick_strike_rate_pct", label: "Strike %" },
                { key: "top_pick_place_rate_pct", label: "Place %" },
                { key: "avg_winner_model_rank", label: "Avg Winner Rank" },
              ]}
              rows={daily as unknown as Record<string, unknown>[]}
            />
          </SectionCard>

          <SectionCard title="Race Review">
            <DataTable
              columns={[
                { key: "race_date", label: "Date" },
                { key: "track", label: "Track" },
                { key: "race_no", label: "R" },
                { key: "winner", label: "Winner" },
                { key: "winner_model_rank", label: "Winner Rank" },
                { key: "winner_model_win_probability", label: "Winner Win %" },
                { key: "model_top_pick", label: "Model Top Pick" },
                { key: "top_pick_finish_position", label: "Top Pick Finish" },
                { key: "top_pick_won", label: "Top Pick Won" },
                { key: "forecast_confidence", label: "Confidence" },
                { key: "race_strength_label", label: "Strength" },
              ]}
              rows={raceReviewSorted as unknown as Record<string, unknown>[]}
            />
          </SectionCard>
        </>
      )}
    </div>
  );
}


