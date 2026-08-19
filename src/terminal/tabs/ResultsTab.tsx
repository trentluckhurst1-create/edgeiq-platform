import React, { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type Row = Record<string, string>;

const FILES = {
  review: "/data/edgeiq_results_review_v1.csv",
  reviewSummary: "/data/edgeiq_results_review_v1_summary.csv",
  performanceSummary: "/data/edgeiq_execution_performance_summary_v2.csv",
  performanceDetail: "/data/edgeiq_execution_performance_v2.csv",
};

type RaceReviewSummary = {
  key: string;
  meetingDate: string;
  track: string;
  raceNo: number;
  label: string;
  starters: number;
  winner: Row | null;
  modelLeader: Row | null;
  bestValue: Row | null;
  fairCount: number;
  marketCount: number;
  confidenceCount: number;
  reviewDepth: string;
  reviewDepthRank: number;
  rows: Row[];
};

function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function num(value: unknown): number | null {
  const raw = text(value).replace(/[$,%u]/g, "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function cleanTrack(value: unknown): string {
  return text(value).toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function meetingDate(row: Row): string {
  return text(row.meeting_date || row.race_date || row.date);
}

function track(row: Row): string {
  return text(row.track || row.meeting || row.meeting_name);
}

function raceNo(row: Row): number {
  return Math.trunc(num(row.race_no || row.race_number || row.race) ?? 0);
}

function horse(row: Row): string {
  return text(row.horse || row.runner || row.runner_name);
}

function finishPosition(row: Row): number | null {
  return num(row.finish_position || row.finishPosition || row.position || row.result);
}

function barrier(row: Row): string {
  const value = num(row.barrier || row.bar);
  return value === null ? "-" : String(Math.trunc(value));
}

function fairPrice(row: Row): number | null {
  return num(row.edgeiq_fair_price_v1);
}

function marketPrice(row: Row): number | null {
  return num(row.edgeiq_market_price_v1);
}

function officialSp(row: Row): number | null {
  return num(row.sp);
}

function valueEdge(row: Row): number | null {
  const direct = num(row.edgeiq_pre_race_edge_pct_v1);
  if (direct !== null) return direct;

  const fair = fairPrice(row);
  const market = marketPrice(row);
  if (fair !== null && fair > 0 && market !== null && market > 0) {
    return ((market / fair) - 1) * 100;
  }

  return null;
}

function betQuality(row: Row): string {
  return text(row.bet_quality_grade_v1_1).toUpperCase();
}

function sectionalStatus(row: Row): string {
  const raw = text(row.sectional_read_status_v1).toUpperCase();
  if (!raw) return "UNAVAILABLE";
  if (raw.includes("PENDING")) return "PENDING REVIEW";
  if (raw.includes("MATCH")) return "AVAILABLE";
  return raw.replace(/_/g, " ");
}

function isValidReviewRow(row: Row): boolean {
  return !!meetingDate(row) && !!track(row) && raceNo(row) > 0 && !!horse(row) && finishPosition(row) !== null;
}

function isStarter(row: Row): boolean {
  const finish = finishPosition(row);
  return finish !== null && finish < 900;
}

function raceKey(row: Row): string {
  return [meetingDate(row), cleanTrack(track(row)), String(raceNo(row))].join("|");
}

function raceLabel(row: Row): string {
  return `${formatDate(meetingDate(row))} | ${track(row)} | R${raceNo(row)}`;
}

function money(value: number | null): string {
  if (value === null || !Number.isFinite(value) || value <= 0) return "-";
  return `$${value.toFixed(2)}`;
}

function pct(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  return `${value.toFixed(1)}%`;
}

function signedUnits(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}u`;
}

function formatDate(value: string): string {
  const raw = text(value);
  if (!raw) return "-";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function reviewDepthLabel(starters: number, fairCount: number, marketCount: number, confidenceCount: number): string {
  const fairTarget = Math.max(3, Math.ceil(starters * 0.3));
  const confidenceTarget = Math.max(2, Math.ceil(starters * 0.2));

  if (fairCount >= fairTarget && confidenceCount >= confidenceTarget) return "FULL REVIEW";
  if (fairCount > 0 || marketCount > 0 || confidenceCount > 0) return "PARTIAL REVIEW";
  return "RESULT ONLY";
}

function reviewDepthRank(label: string): number {
  if (label === "FULL REVIEW") return 3;
  if (label === "PARTIAL REVIEW") return 2;
  return 1;
}

function outcomeLabel(row: Row): string {
  const finish = finishPosition(row);
  if (finish === null) return "-";
  if (finish === 1) return "WINNER";
  if (finish <= 3) return "PLACED";
  if (finish === 999) return "NON-RUNNER";
  return "UNPLACED";
}

function pillColors(label: string): { background: string; border: string; color: string } {
  const value = label.toUpperCase();

  if (value.includes("FULL") || value === "WINNER" || value === "HIGH") {
    return {
      background: "rgba(16,185,129,0.18)",
      border: "rgba(16,185,129,0.42)",
      color: "#bbf7d0",
    };
  }

  if (value.includes("PARTIAL") || value === "PLACED" || value === "MEDIUM") {
    return {
      background: "rgba(245,158,11,0.18)",
      border: "rgba(245,158,11,0.4)",
      color: "#fde68a",
    };
  }

  if (value.includes("RESULT") || value.includes("UNPLACED") || value.includes("LOW")) {
    return {
      background: "rgba(248,113,113,0.18)",
      border: "rgba(248,113,113,0.4)",
      color: "#fecaca",
    };
  }

  return {
    background: "rgba(59,130,246,0.16)",
    border: "rgba(96,165,250,0.4)",
    color: "#dbeafe",
  };
}

function edgeTextColor(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "#cbd5e1";
  if (value < 0) return "#fca5a5";
  if (value >= 100) return "#e2e8f0";
  return "#fde68a";
}

function pill(label: string, minWidth = 82): React.ReactElement {
  const colors = pillColors(label);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth,
        border: `1px solid ${colors.border}`,
        borderRadius: 999,
        padding: "4px 9px",
        fontSize: 10,
        fontWeight: 900,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: colors.color,
        background: colors.background,
      }}
    >
      {label || "-"}
    </span>
  );
}

function parseMetricRows(rows: Row[]): Map<string, string> {
  const map = new Map<string, string>();
  rows.forEach((row) => {
    const metric = text(row.metric);
    if (metric) map.set(metric, text(row.value));
  });
  return map;
}

function metricNumber(map: Map<string, string>, key: string): number | null {
  const value = map.get(key);
  return value === undefined ? null : num(value);
}

function humanizeSegment(dimension: string, segment: string): string {
  const dim = text(dimension).toUpperCase();
  const seg = text(segment).replace(/_/g, " ").toLowerCase();

  if (dim === "MOVE_TYPE") return `${seg} market moves`;
  if (dim === "MARKET_SIGNAL") return `${seg} market behaviour`;
  if (dim === "EXECUTION_TIER") return `${seg} execution tier`;
  if (dim === "EDGE_BUCKET") return `${seg} edge bucket`;
  if (dim === "SCORE_BUCKET") return `${seg} score bucket`;
  if (dim === "REVIEW_LABEL") return seg;
  if (dim === "MARKET_READ") return `${seg} market reads`;
  return seg;
}

async function loadCsv<T extends Record<string, string>>(path: string): Promise<T[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const textValue = await response.text();
    const parsed = Papa.parse<T>(textValue, { header: true, skipEmptyLines: true });
    return parsed.data || [];
  } catch {
    return [];
  }
}

export default function ResultsTab(): React.ReactElement {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewRows, setReviewRows] = useState<Row[]>([]);
  const [reviewSummaryRows, setReviewSummaryRows] = useState<Row[]>([]);
  const [performanceSummaryRows, setPerformanceSummaryRows] = useState<Row[]>([]);
  const [performanceDetailRows, setPerformanceDetailRows] = useState<Row[]>([]);
  const [selectedRaceKey, setSelectedRaceKey] = useState("");

  useEffect(() => {
    let active = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError("");

      try {
        const [review, reviewSummary, performanceSummary, performanceDetail] = await Promise.all([
          loadCsv<Row>(FILES.review),
          loadCsv<Row>(FILES.reviewSummary),
          loadCsv<Row>(FILES.performanceSummary),
          loadCsv<Row>(FILES.performanceDetail),
        ]);

        if (!active) return;

        const validRows = review.filter(isValidReviewRow);
        setReviewRows(validRows);
        setReviewSummaryRows(reviewSummary);
        setPerformanceSummaryRows(performanceSummary);
        setPerformanceDetailRows(performanceDetail);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load EDGEiQ review data.");
      } finally {
        if (active) setLoading(false);
      }
    }

    load();

    return () => {
      active = false;
    };
  }, []);

  const reviewSummaryMap = useMemo(() => parseMetricRows(reviewSummaryRows), [reviewSummaryRows]);
  const performanceSummary = useMemo(() => performanceSummaryRows[0] ?? {}, [performanceSummaryRows]);

  const raceSummaries = useMemo(() => {
    const grouped = new Map<string, Row[]>();

    reviewRows.forEach((row) => {
      const key = raceKey(row);
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key)!.push(row);
    });

    return [...grouped.entries()]
      .map(([key, rows]): RaceReviewSummary => {
        const orderedRows = rows
          .slice()
          .sort((a, b) => (finishPosition(a) ?? 999) - (finishPosition(b) ?? 999));
        const starters = orderedRows.filter(isStarter);
        const winner = starters.find((row) => finishPosition(row) === 1) ?? null;
        const fairRows = starters.filter((row) => fairPrice(row) !== null);
        const modelLeader =
          fairRows
            .slice()
            .sort((a, b) => (fairPrice(a) ?? 999) - (fairPrice(b) ?? 999))[0] ?? null;
        const bestValue =
          starters
            .filter((row) => valueEdge(row) !== null)
            .slice()
            .sort((a, b) => (valueEdge(b) ?? -999) - (valueEdge(a) ?? -999))[0] ?? null;
        const fairCount = fairRows.length;
        const marketCount = starters.filter((row) => marketPrice(row) !== null).length;
        const confidenceCount = starters.filter((row) => !!betQuality(row)).length;
        const depth = reviewDepthLabel(starters.length, fairCount, marketCount, confidenceCount);

        return {
          key,
          meetingDate: meetingDate(rows[0]),
          track: track(rows[0]),
          raceNo: raceNo(rows[0]),
          label: raceLabel(rows[0]),
          starters: starters.length,
          winner,
          modelLeader,
          bestValue,
          fairCount,
          marketCount,
          confidenceCount,
          reviewDepth: depth,
          reviewDepthRank: reviewDepthRank(depth),
          rows: orderedRows,
        };
      })
      .sort((a, b) => {
        const dateDiff = b.meetingDate.localeCompare(a.meetingDate);
        if (dateDiff !== 0) return dateDiff;
        const trackDiff = a.track.localeCompare(b.track);
        if (trackDiff !== 0) return trackDiff;
        return b.raceNo - a.raceNo;
      });
  }, [reviewRows]);

  useEffect(() => {
    if (!selectedRaceKey && raceSummaries.length > 0) {
      setSelectedRaceKey(raceSummaries[0].key);
    }
  }, [raceSummaries, selectedRaceKey]);

  const selectedRace = useMemo(
    () => raceSummaries.find((race) => race.key === selectedRaceKey) ?? raceSummaries[0] ?? null,
    [raceSummaries, selectedRaceKey],
  );

  const reviewWindow = useMemo(() => {
    const dates = [...new Set(reviewRows.map((row) => meetingDate(row)).filter(Boolean))].sort();
    if (!dates.length) return "-";
    if (dates.length === 1) return formatDate(dates[0]);
    return `${formatDate(dates[0])} - ${formatDate(dates[dates.length - 1])}`;
  }, [reviewRows]);

  const meetingCount = useMemo(() => {
    return new Set(reviewRows.map((row) => `${meetingDate(row)}|${cleanTrack(track(row))}`)).size;
  }, [reviewRows]);

  const fairMatchedRows = useMemo(() => reviewRows.filter((row) => fairPrice(row) !== null).length, [reviewRows]);
  const marketMatchedRows = useMemo(() => reviewRows.filter((row) => marketPrice(row) !== null).length, [reviewRows]);
  const officialSpRows = useMemo(() => reviewRows.filter((row) => officialSp(row) !== null).length, [reviewRows]);
  const confidenceMatchedRows = useMemo(() => reviewRows.filter((row) => !!betQuality(row)).length, [reviewRows]);
  const winnerModelReadCount = useMemo(
    () => raceSummaries.filter((race) => race.winner && fairPrice(race.winner) !== null).length,
    [raceSummaries],
  );

  const bestPerformanceSegment = useMemo(() => {
    return performanceDetailRows
      .filter((row) => (num(row.bets) ?? 0) >= 3 && num(row.roi_pct) !== null)
      .slice()
      .sort((a, b) => (num(b.roi_pct) ?? -999) - (num(a.roi_pct) ?? -999))[0] ?? null;
  }, [performanceDetailRows]);

  const weakestPerformanceSegment = useMemo(() => {
    return performanceDetailRows
      .filter((row) => (num(row.bets) ?? 0) >= 3 && num(row.roi_pct) !== null)
      .slice()
      .sort((a, b) => (num(a.roi_pct) ?? 999) - (num(b.roi_pct) ?? 999))[0] ?? null;
  }, [performanceDetailRows]);

  const performanceNarrative = useMemo(() => {
    const reviewedBets = num(performanceSummary.reviewed_bets);
    const wins = num(performanceSummary.wins);
    const strikePct = num(performanceSummary.strike_pct);
    const profitUnits = num(performanceSummary.profit_units);
    const roiPct = num(performanceSummary.roi_pct);
    const pending = num(performanceSummary.pending);

    if (reviewedBets === null) {
      return "Performance review data is not yet available in the current results view.";
    }

    return [
      `EDGEiQ has reviewed ${reviewedBets.toFixed(0)} settled opportunities so far, with ${wins?.toFixed(0) ?? 0} winners and a ${strikePct?.toFixed(1) ?? 0}% strike rate.`,
      `Current review profit stands at ${signedUnits(profitUnits)} with ROI at ${pct(roiPct)}.`,
      pending && pending > 0 ? `${pending.toFixed(0)} opportunities are still waiting on final review.` : "No open review items are currently waiting to settle.",
    ].join(" ");
  }, [performanceSummary]);

  const winnerNarrative = useMemo(() => {
    if (!selectedRace || !selectedRace.winner) {
      return "Select a reviewed race to see how the winner lined up against EDGEiQ before the jump.";
    }

    const winnerRow = selectedRace.winner;
    const winnerName = horse(winnerRow);
    const winnerFair = fairPrice(winnerRow);
    const winnerMarket = marketPrice(winnerRow);
    const winnerSp = officialSp(winnerRow);
    const winnerEdge = valueEdge(winnerRow);
    const topModel = selectedRace.modelLeader ? horse(selectedRace.modelLeader) : "";
    const bestValueHorse = selectedRace.bestValue ? horse(selectedRace.bestValue) : "";
    const notes: string[] = [];

    notes.push(`${winnerName} won ${selectedRace.track} R${selectedRace.raceNo}.`);

    if (winnerFair !== null) {
      notes.push(`EDGEiQ had the winner marked at a fair price of ${money(winnerFair)}.`);
    } else {
      notes.push("EDGEiQ did not have a matched fair-price read on the winner.");
    }

    if (winnerMarket !== null) {
      notes.push(`The TAB market had the winner at ${money(winnerMarket)} before the jump.`);
    } else if (winnerSp !== null) {
      notes.push(`Official SP settled at ${money(winnerSp)}.`);
    }

    if (topModel) {
      if (topModel === winnerName) {
        notes.push("The shortest EDGEiQ fair runner won the race.");
      } else {
        notes.push(`${topModel} was EDGEiQ's top-rated runner before the jump.`);
      }
    }

    if (bestValueHorse) {
      if (bestValueHorse === winnerName && winnerEdge !== null) {
        notes.push(`The winner also carried the strongest matched value edge at ${pct(winnerEdge)}.`);
      } else {
        notes.push(`Best matched value sat with ${bestValueHorse}.`);
      }
    }

    if (selectedRace.reviewDepth === "FULL REVIEW") {
      notes.push("This race has fuller EDGEiQ review coverage.");
    } else if (selectedRace.reviewDepth === "PARTIAL REVIEW") {
      notes.push("This race has partial EDGEiQ review coverage.");
    } else {
      notes.push("This race is currently available from the finishing result only.");
    }

    return notes.join(" ");
  }, [selectedRace]);

  const resultsOverviewCards = [
    {
      label: "Meetings Reviewed",
      value: String(meetingCount),
      sub: reviewWindow,
      tone: "#7dd3fc",
    },
    {
      label: "Races Reviewed",
      value: String(metricNumber(reviewSummaryMap, "races") ?? raceSummaries.length),
      sub: "completed races in the review window",
      tone: "#e2e8f0",
    },
    {
      label: "Runner Results",
      value: String(metricNumber(reviewSummaryMap, "rows") ?? reviewRows.length),
      sub: "individual runner outcomes loaded",
      tone: "#e2e8f0",
    },
    {
      label: "EDGEiQ Fair Prices",
      value: String(fairMatchedRows),
      sub: "runners carrying an EDGEiQ fair price before the jump",
      tone: "#bbf7d0",
    },
    {
      label: "Market Reads Captured",
      value: String(marketMatchedRows),
      sub: "runners with a TAB market price captured before the jump",
      tone: "#fde68a",
    },
    {
      label: "Winners With EDGEiQ Read",
      value: String(winnerModelReadCount),
      sub: `${officialSpRows} runners also have an official SP captured`,
      tone: "#fca5a5",
    },
  ] as const;

  if (loading) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-no-live">Loading EDGEiQ review data...</div>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-no-live">{error}</div>
        </section>
      </div>
    );
  }

  return (
    <div className="edgeTabSurface">
      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">
          <span>RESULTS OVERVIEW</span>
          <span className="edgeiq-pill good">{reviewWindow}</span>
        </div>

        <div style={{ padding: 12, display: "grid", gap: 12 }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div style={{ minWidth: 0 }}>
              <div className="edgeiq-mini-note-label">EDGEiQ REVIEW CENTRE</div>
              <div className="edgeiq-mini-note-value">What happened and how EDGEiQ performed</div>
              <div className="edgeiq-mini-note-sub">
                Review coverage across completed races, winners and settled EDGEiQ calls.
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              {pill(`${raceSummaries.length} RACES`, 76)}
              {pill(`${confidenceMatchedRows} EDGEIQ CONFIDENCE`, 132)}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 10,
            }}
          >
            {resultsOverviewCards.map((card) => (
              <div key={card.label} className="edgeiq-terminal-stat" style={{ minHeight: 100 }}>
                <div className="edgeiq-terminal-stat-label">{card.label}</div>
                <div className="edgeiq-terminal-stat-value" style={{ color: card.tone }}>
                  {card.value}
                </div>
                <div className="edgeiq-terminal-stat-sub">{card.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">EDGEiQ PERFORMANCE SUMMARY</div>
        <div style={{ padding: 12, display: "grid", gap: 12 }}>
          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">Review Summary</div>
            <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
              {performanceNarrative}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Reviewed Calls</div>
              <div className="edgeiq-terminal-stat-value">{num(performanceSummary.reviewed_bets)?.toFixed(0) ?? "-"}</div>
              <div className="edgeiq-terminal-stat-sub">settled EDGEiQ calls reviewed so far</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Winners</div>
              <div className="edgeiq-terminal-stat-value">{num(performanceSummary.wins)?.toFixed(0) ?? "-"}</div>
              <div className="edgeiq-terminal-stat-sub">reviewed EDGEiQ calls that won</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Strike Rate</div>
              <div className="edgeiq-terminal-stat-value">{pct(num(performanceSummary.strike_pct))}</div>
              <div className="edgeiq-terminal-stat-sub">winner strike across reviewed calls</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Profit / Loss</div>
              <div className="edgeiq-terminal-stat-value">{signedUnits(num(performanceSummary.profit_units))}</div>
              <div className="edgeiq-terminal-stat-sub">current review profit in units</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">ROI</div>
              <div className="edgeiq-terminal-stat-value">{pct(num(performanceSummary.roi_pct))}</div>
              <div className="edgeiq-terminal-stat-sub">return on reviewed calls</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Pending Reviews</div>
              <div className="edgeiq-terminal-stat-value">{num(performanceSummary.pending)?.toFixed(0) ?? "-"}</div>
              <div className="edgeiq-terminal-stat-sub">opportunities still awaiting final review</div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: 10,
            }}
          >
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Best Recent Pattern</div>
              <div className="edgeiq-mini-note-value" style={{ fontSize: 16 }}>
                {bestPerformanceSegment
                  ? `${humanizeSegment(bestPerformanceSegment.dimension, bestPerformanceSegment.segment)}`
                  : "Not enough reviewed depth yet"}
              </div>
              <div className="edgeiq-mini-note-sub">
                {bestPerformanceSegment
                  ? `${bestPerformanceSegment.bets} bets | ${pct(num(bestPerformanceSegment.strike_pct))} strike | ${pct(num(bestPerformanceSegment.roi_pct))} ROI`
                  : "No segment has enough reviewed depth to highlight yet."}
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Pressure Point</div>
              <div className="edgeiq-mini-note-value" style={{ fontSize: 16 }}>
                {weakestPerformanceSegment
                  ? `${humanizeSegment(weakestPerformanceSegment.dimension, weakestPerformanceSegment.segment)}`
                  : "Not enough reviewed depth yet"}
              </div>
              <div className="edgeiq-mini-note-sub">
                {weakestPerformanceSegment
                  ? `${weakestPerformanceSegment.bets} bets | ${pct(num(weakestPerformanceSegment.strike_pct))} strike | ${pct(num(weakestPerformanceSegment.roi_pct))} ROI`
                  : "No weak segment is flagged yet from the current review view."}
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Review Flags</div>
              <div className="edgeiq-mini-note-value" style={{ fontSize: 16 }}>
                {num(performanceSummary.fake_overlay_count)?.toFixed(0) ?? "0"} false signals
              </div>
              <div className="edgeiq-mini-note-sub">
                {num(performanceSummary.edge_decay_loss_count)?.toFixed(0) ?? "0"} losses where the price moved away before the finish.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">RACE REVIEW BOARD</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          <div className="edgeiq-data-note">
            Select a completed race to review the winner, the model read and the finishing order.
          </div>

          {raceSummaries.map((race) => {
            const selected = selectedRace?.key === race.key;
            return (
              <button
                key={race.key}
                type="button"
                onClick={() => setSelectedRaceKey(race.key)}
                style={{
                  width: "100%",
                  display: "grid",
                  gridTemplateColumns: "130px minmax(190px, 1.2fr) 88px 98px 118px minmax(150px, 1fr) 122px",
                  gap: 10,
                  alignItems: "center",
                  border: selected ? "1px solid rgba(52,211,153,0.55)" : "1px solid rgba(41,72,90,0.82)",
                  borderRadius: 10,
                  background: selected ? "rgba(8,33,28,0.88)" : "rgba(5,14,22,0.82)",
                  color: "#dbe7f3",
                  padding: "10px 12px",
                  textAlign: "left",
                }}
              >
                <div>
                  <div style={miniLabelStyle}>Race</div>
                  <div style={miniValueStyle}>R{race.raceNo}</div>
                  <div style={miniSubStyle}>{formatDate(race.meetingDate)}</div>
                </div>

                <div style={{ minWidth: 0 }}>
                  <div style={miniLabelStyle}>Winner</div>
                  <div style={miniValueStyle}>{race.winner ? horse(race.winner) : "-"}</div>
                  <div style={miniSubStyle}>{race.track}</div>
                </div>

                <div>
                  <div style={miniLabelStyle}>Field</div>
                  <div style={miniValueStyle}>{race.starters}</div>
                </div>

                <div>
                  <div style={miniLabelStyle}>Fair Prices</div>
                  <div style={miniValueStyle}>{race.fairCount}</div>
                </div>

                <div>
                  <div style={miniLabelStyle}>Confidence</div>
                  <div style={miniValueStyle}>{race.confidenceCount}</div>
                </div>

                <div style={{ minWidth: 0 }}>
                  <div style={miniLabelStyle}>Best Value</div>
                  <div style={miniValueStyle}>
                    {race.bestValue ? horse(race.bestValue) : "-"}
                  </div>
                  <div style={miniSubStyle}>
                    {race.bestValue ? pct(valueEdge(race.bestValue)) : "No current value runner highlighted"}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  {pill(race.reviewDepth, 110)}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">WINNER ANALYSIS</div>
        <div style={{ padding: 12, display: "grid", gap: 12 }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div className="edgeiq-mini-note-label">Selected Race</div>
              <div className="edgeiq-mini-note-value">
                {selectedRace ? `${selectedRace.track} R${selectedRace.raceNo}` : "No race selected"}
              </div>
              <div className="edgeiq-mini-note-sub">
                {selectedRace ? formatDate(selectedRace.meetingDate) : "Select a race from the review board"}
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {selectedRace ? pill(selectedRace.reviewDepth, 110) : null}
              {selectedRace?.winner ? pill(outcomeLabel(selectedRace.winner), 80) : null}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Winner</div>
              <div className="edgeiq-terminal-stat-value" style={{ fontSize: 20 }}>
                {selectedRace?.winner ? horse(selectedRace.winner) : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">official winner for the selected race</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Official SP</div>
              <div className="edgeiq-terminal-stat-value">
                {selectedRace?.winner ? money(officialSp(selectedRace.winner)) : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">official starting price captured in review</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">EDGEiQ Fair Price</div>
              <div className="edgeiq-terminal-stat-value">
                {selectedRace?.winner ? money(fairPrice(selectedRace.winner)) : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">EDGEiQ fair price held by the winner before the jump</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Top Rated Runner</div>
              <div className="edgeiq-terminal-stat-value" style={{ fontSize: 20 }}>
                {selectedRace?.modelLeader ? horse(selectedRace.modelLeader) : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">shortest EDGEiQ fair price in the race</div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">Best Value</div>
              <div className="edgeiq-terminal-stat-value" style={{ fontSize: 20 }}>
                {selectedRace?.bestValue ? horse(selectedRace.bestValue) : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">
                {selectedRace?.bestValue ? pct(valueEdge(selectedRace.bestValue)) : "no current value edge"}
              </div>
            </div>
            <div className="edgeiq-terminal-stat">
              <div className="edgeiq-terminal-stat-label">EDGEiQ Confidence</div>
              <div className="edgeiq-terminal-stat-value">
                {selectedRace?.winner ? betQuality(selectedRace.winner) || "-" : "-"}
              </div>
              <div className="edgeiq-terminal-stat-sub">EDGEiQ confidence carried by the winner before the jump</div>
            </div>
          </div>

          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">EDGEiQ Review Read</div>
            <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
              {winnerNarrative}
            </div>
          </div>
        </div>
      </section>

      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">EDGEiQ REVIEW PANEL</div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          <div className="edgeiq-data-note">
            Finish order against the EDGEiQ prices and confidence available before the jump.
          </div>

          <div
            style={{
              overflowX: "auto",
              border: "1px solid rgba(41,72,90,0.7)",
              borderRadius: 12,
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 1080,
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ background: "rgba(15,23,42,0.96)" }}>
                  {["FINISH", "RUNNER", "BARRIER", "MARKET PRICE", "FAIR PRICE", "VALUE EDGE", "BET QUALITY", "SECTIONAL REVIEW", "OUTCOME"].map((header) => (
                    <th
                      key={header}
                      style={{
                        textAlign: "left",
                        padding: "10px 12px",
                        color: "#93c5fd",
                        fontSize: 10,
                        fontWeight: 900,
                        letterSpacing: "0.12em",
                        borderBottom: "1px solid rgba(148,163,184,0.16)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {selectedRace?.rows.map((row, index) => {
                  const winnerRow = finishPosition(row) === 1;
                  return (
                    <tr
                      key={`${selectedRace.key}|${horse(row)}|${index}`}
                      style={{
                        background: winnerRow
                          ? "rgba(18,80,62,0.38)"
                          : index % 2 === 0
                            ? "rgba(2,6,23,0.55)"
                            : "rgba(15,23,42,0.38)",
                      }}
                    >
                      <td style={tdStrong}>{finishPosition(row) ?? "-"}</td>
                      <td style={tdHorse}>
                        <div>{horse(row)}</div>
                        <div style={{ color: "#94a3b8", fontSize: 11, fontWeight: 500, marginTop: 2 }}>
                          {text(row.jockey) || text(row.trainer) || "-"}
                        </div>
                      </td>
                      <td style={td}>{barrier(row)}</td>
                      <td style={tdNum}>{money(marketPrice(row) ?? officialSp(row))}</td>
                      <td style={tdNum}>{money(fairPrice(row))}</td>
                      <td style={{ ...tdNum, color: edgeTextColor(valueEdge(row)) }}>{pct(valueEdge(row))}</td>
                      <td style={td}>{betQuality(row) || "-"}</td>
                      <td style={td}>{sectionalStatus(row)}</td>
                      <td style={td}>{pill(outcomeLabel(row), 82)}</td>
                    </tr>
                  );
                })}

                {!selectedRace?.rows.length && (
                  <tr>
                    <td colSpan={9} style={{ ...td, textAlign: "center", padding: 24, color: "#64748b" }}>
                      No reviewed runners are loaded for the selected race.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

const miniLabelStyle: React.CSSProperties = {
  color: "#6f8493",
  fontSize: 9,
  fontWeight: 900,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
};

const miniValueStyle: React.CSSProperties = {
  color: "#eef7ff",
  fontSize: 13,
  fontWeight: 900,
  lineHeight: 1.2,
};

const miniSubStyle: React.CSSProperties = {
  color: "#94a3b8",
  fontSize: 10,
  lineHeight: 1.3,
};

const td: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid rgba(148,163,184,0.08)",
  color: "#dbeafe",
  whiteSpace: "nowrap",
};

const tdStrong: React.CSSProperties = {
  ...td,
  color: "#f8fafc",
  fontWeight: 900,
};

const tdHorse: React.CSSProperties = {
  ...td,
  color: "#ffffff",
  fontWeight: 900,
  whiteSpace: "normal",
  minWidth: 180,
};

const tdNum: React.CSSProperties = {
  ...td,
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
  fontWeight: 800,
};
