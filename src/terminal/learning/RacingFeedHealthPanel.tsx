import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";

type CsvRow = Record<string, string>;
type Tone = "good" | "warn" | "bad" | "neutral";

const FILES = {
  freshnessSummary: "/data/edgeiq_racing_public_data_freshness_summary_v1.csv",
  refreshSummary: "/data/edgeiq_racing_public_data_refresh_summary_v1.csv",
  refreshLog: "/data/edgeiq_racing_public_data_refresh_log_v1.csv",
  staleFeeds: "/data/edgeiq_racing_public_data_stale_feeds_v1.csv",
  missingFeeds: "/data/edgeiq_racing_public_data_missing_feeds_v1.csv",
};

function clean(value: unknown): string {
  const output = String(value ?? "").trim();
  return output && !["NAN", "NULL", "UNDEFINED"].includes(output.toUpperCase()) ? output : "";
}

function upper(value: unknown): string {
  return clean(value).toUpperCase();
}

function metric(rows: CsvRow[], key: string, fallback = ""): string {
  return clean(rows.find((row) => clean(row.metric) === key)?.value) || fallback;
}

function toneFrom(value: unknown): Tone {
  const status = upper(value);
  if (!status) return "neutral";
  if (status.includes("FAIL") || status.includes("BLOCKED") || status.includes("MISSING")) return "bad";
  if (status.includes("WARN") || status.includes("STALE") || status.includes("SKIP") || status.includes("EMPTY")) return "warn";
  if (status.includes("PASS") || status.includes("FRESH") || status.includes("HEALTHY") || status.includes("OK")) return "good";
  return "neutral";
}

function toneClass(value: Tone): string {
  if (value === "good") return "edgeiq-chip edgeiq-chip--good";
  if (value === "warn") return "edgeiq-chip edgeiq-chip--warn";
  if (value === "bad") return "edgeiq-chip edgeiq-chip--bad";
  return "edgeiq-chip";
}

async function readCsv(path: string): Promise<CsvRow[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    if (csv.trim().toLowerCase().startsWith("<!doctype html") || csv.includes("<html")) {
      return [];
    }
    return Papa.parse<CsvRow>(csv, { header: true, skipEmptyLines: true }).data ?? [];
  } catch {
    return [];
  }
}

export default function RacingFeedHealthPanel(): React.ReactElement {
  const [freshnessSummary, setFreshnessSummary] = useState<CsvRow[]>([]);
  const [refreshSummary, setRefreshSummary] = useState<CsvRow[]>([]);
  const [refreshLog, setRefreshLog] = useState<CsvRow[]>([]);
  const [staleFeeds, setStaleFeeds] = useState<CsvRow[]>([]);
  const [missingFeeds, setMissingFeeds] = useState<CsvRow[]>([]);
  const [loadedAt, setLoadedAt] = useState("");
  const [hasLoaded, setHasLoaded] = useState(false);

  useEffect(() => {
    let alive = true;

    async function load(): Promise<void> {
      const [freshness, refresh, log, stale, missing] = await Promise.all([
        readCsv(FILES.freshnessSummary),
        readCsv(FILES.refreshSummary),
        readCsv(FILES.refreshLog),
        readCsv(FILES.staleFeeds),
        readCsv(FILES.missingFeeds),
      ]);

      if (!alive) return;

      setFreshnessSummary(freshness);
      setRefreshSummary(refresh);
      setRefreshLog(log);
      setStaleFeeds(stale);
      setMissingFeeds(missing);
      setLoadedAt(new Date().toLocaleTimeString());
      setHasLoaded(true);
    }

    load();
    const timer = window.setInterval(load, 60000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const summary = useMemo(() => {
    const refreshStatus = metric(refreshSummary, "overall_status", "UNAVAILABLE");
    const staleCount = metric(freshnessSummary, "stale_count", "0");
    const missingCount = metric(freshnessSummary, "missing_count", "0");
    const blockers = metric(freshnessSummary, "required_surface_blockers", "0");
    const topFeed =
      metric(freshnessSummary, "top_blocker_feed")
      || clean(staleFeeds[0]?.feed_name)
      || "No blocker recorded";
    const topReason =
      metric(freshnessSummary, "top_blocker_reason")
      || clean(staleFeeds[0]?.reason)
      || "No blocker reason recorded";

    const passed = metric(refreshSummary, "steps_passed", "0");
    const failed = metric(refreshSummary, "steps_failed", "0");
    const skipped = metric(refreshSummary, "steps_skipped", "0");

    return {
      refreshStatus,
      staleCount,
      missingCount,
      blockers,
      topFeed,
      topReason,
      passed,
      failed,
      skipped,
    };
  }, [freshnessSummary, refreshSummary, staleFeeds]);

  const latestRun = useMemo(() => {
    return [...refreshLog]
      .filter((row) => clean(row.refreshed_at))
      .sort((a, b) => clean(b.refreshed_at).localeCompare(clean(a.refreshed_at)))[0] ?? null;
  }, [refreshLog]);

  const topStale = useMemo(() => staleFeeds.slice(0, 5), [staleFeeds]);
  const skippedSteps = useMemo(
    () => refreshLog.filter((row) => upper(row.status) === "SKIP").slice(0, 5),
    [refreshLog],
  );

  const truthMessage = useMemo(() => {
    if (!hasLoaded) {
      return "Loading feed audit...";
    }
    if (summary.refreshStatus === "HEALTHY" && Number(summary.staleCount) === 0 && Number(summary.blockers) === 0) {
      return "Surface feeds are fresh enough for normal terminal use.";
    }
    if (summary.refreshStatus === "WARNING" || Number(summary.staleCount) > 0 || Number(summary.blockers) > 0) {
      return "Do not assume live data unless the feed stack is fresh.";
    }
    return "Feed health is unavailable. Treat market surfaces as observational only.";
  }, [hasLoaded, summary]);

  return (
    <section className="edgeiq-panel span-2">
      <div className="edgeiq-panel-title">RACING FEED HEALTH</div>

      <div className="edgeiq-terminal-banner">
        <div>
          <div className="edgeiq-terminal-banner-label">Current data truth</div>
          <div className="edgeiq-terminal-banner-value">{truthMessage}</div>
          <div className="edgeiq-terminal-banner-sub">
            {hasLoaded ? `${summary.topFeed} | ${summary.topReason}` : "Refreshing audit files..."}
          </div>
        </div>
        <span className={toneClass(toneFrom(summary.refreshStatus))}>
          {hasLoaded ? summary.refreshStatus : "LOADING"}
        </span>
      </div>

      <div className="edgeiq-terminal-stat-grid edgeiq-terminal-stat-grid--compact">
        <Stat label="Stale feeds" value={hasLoaded ? summary.staleCount : "-"} tone={!hasLoaded ? "neutral" : Number(summary.staleCount) ? "warn" : "good"} sub="current freshness audit" />
        <Stat label="Missing feeds" value={hasLoaded ? summary.missingCount : "-"} tone={!hasLoaded ? "neutral" : Number(summary.missingCount) ? "bad" : "good"} sub="missing on disk" />
        <Stat label="Surface blockers" value={hasLoaded ? summary.blockers : "-"} tone={!hasLoaded ? "neutral" : Number(summary.blockers) ? "warn" : "good"} sub="required surfaces affected" />
        <Stat label="Refresh steps" value={hasLoaded ? summary.passed : "-"} tone={!hasLoaded ? "neutral" : "good"} sub={hasLoaded ? `${summary.failed} failed | ${summary.skipped} skipped` : "awaiting summary"} />
      </div>

      <div className="edgeiq-learning-grid">
        <div className="edgeiq-terminal-subgrid">
          <CompactTable title="Top stale feeds" rows={topStale} empty={hasLoaded ? "No stale feeds in the current audit." : "Loading stale-feed audit..."} />
        </div>

        <div className="edgeiq-terminal-subgrid">
          <CompactTable title="Skipped refresh paths" rows={skippedSteps} empty={hasLoaded ? "No refresh steps were skipped." : "Loading refresh log..."} />

          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">Last refresh</div>
            <div className="edgeiq-mini-note-value">{clean(latestRun?.refreshed_at) || "Unavailable"}</div>
            <div className="edgeiq-mini-note-sub">
              {clean(latestRun?.feed_name) || "No recent step"} | {clean(latestRun?.status) || "Unavailable"} | UI poll {loadedAt || "loading"}
            </div>
          </div>

          <div className="edgeiq-mini-note">
            <div className="edgeiq-mini-note-label">Missing feeds</div>
            <div className="edgeiq-mini-note-value">{hasLoaded ? String(missingFeeds.length) : "-"}</div>
            <div className="edgeiq-mini-note-sub">
              {hasLoaded
                ? (missingFeeds.length
                  ? clean(missingFeeds[0]?.feed_name)
                  : "No missing public/data feeds detected in the active surface set.")
                : "Loading missing-feed audit..."}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
  sub,
}: {
  label: string;
  value: string;
  tone: Tone;
  sub: string;
}): React.ReactElement {
  return (
    <div className="edgeiq-stat-card">
      <div className="label">{label}</div>
      <div className={`value ${tone === "good" ? "emerald" : tone === "bad" ? "red" : tone === "warn" ? "gold" : "blue"}`}>{value}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}

function CompactTable({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: CsvRow[];
  empty: string;
}): React.ReactElement {
  return (
    <div className="edgeiq-terminal-mini-table">
      <div className="edgeiq-terminal-mini-title">{title}</div>
      {rows.length ? (
        <div className="edgeiq-terminal-mini-rows">
          {rows.map((row, index) => (
            <div className="edgeiq-terminal-mini-row" key={`${title}-${clean(row.feed_name || row.script_name || row.step_name)}-${index}`}>
              <div className="edgeiq-terminal-mini-head">
                <span>{clean(row.feed_name) || clean(row.step_name) || clean(row.script_name) || "Unknown"}</span>
                <span className={toneClass(toneFrom(row.freshness_status || row.status))}>
                  {clean(row.freshness_status) || clean(row.status) || "UNKNOWN"}
                </span>
              </div>
              <div className="edgeiq-terminal-mini-sub">
                {clean(row.reason) || clean(row.notes) || clean(row.recommended_action) || "No detail available"}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="edgeiq-empty-state">{empty}</div>
      )}
    </div>
  );
}
