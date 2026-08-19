import React, { useEffect, useRef, useState } from "react";
import Papa from "papaparse";
import { getMeetingDisplayState } from "../../utils/meetingDisplayState";

type Row = Record<string, string | number | boolean | null | undefined>;

type MarketRunner = {
  id: string;
  horse: string;
  horseNo: number | null;
  canonicalKey: string;
  track: string;
  raceNo: string;
  barrier: string;
  silkUrl: string;
  isScratched: boolean;
  live: number | null;
  open: number | null;
  previousPrice: number | null;
};

type MarketTabProps = {
  selectedMeetingKey: string;
  selectedRaceKey: string;
  currentMeeting?: {
    raceDate: string;
    track: string;
    dayBucket: string;
    meetingStatus: string;
    dashboardReady: string;
  } | null;
  currentRace?: {
    raceNo: number;
    raceTime: string;
    raceClass: string;
    distance: number | null;
    rows?: Row[];
  } | null;
};

const REFRESH_MS = 5000;

function clean(value: unknown): string {
  const out = String(value ?? "").trim();
  return out && out.toUpperCase() !== "NAN" && out !== "-" ? out : "";
}

function compact(value: unknown): string {
  return clean(value).toUpperCase().replace(/[^A-Z0-9]+/g, "");
}

function num(value: unknown): number | null {
  const raw = clean(value).replace(/[^\d.-]/g, "");
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

function money(value: number | null): string {
  return value === null || value <= 0 ? "—" : `$${value.toFixed(2)}`;
}

function first(row: Row, keys: string[]): string {
  for (const key of keys) {
    const value = clean(row[key]);
    if (value) return value;
  }
  return "";
}

function firstNum(row: Row, keys: string[]): number | null {
  for (const key of keys) {
    const value = num(row[key]);
    if (value !== null) return value;
  }
  return null;
}

function canonicalHorseKey(row: Row, horse: string): string {
  return (
    compact(row.horse_key) ||
    compact(row.runner_key).replace(/^\d{8}[A-Z]+R\d+/, "") ||
    compact(horse).replace(/NZ$|AUS$|GB$|IRE$|FR$/g, "")
  );
}

async function loadCsv(path: string): Promise<Row[]> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return [];
    const csv = await response.text();
    const parsed = Papa.parse<Row>(csv, { header: true, skipEmptyLines: true });
    return parsed.data || [];
  } catch {
    return [];
  }
}

function selectedTrackFromMeetingKey(value: string): string {
  const parts = clean(value).split("_");
  return parts.length ? parts[parts.length - 1] : "";
}

function selectedRaceNoFromRaceKey(value: string): string {
  const match = clean(value).match(/_R(\d+)$/i);
  return match ? match[1] : "";
}

function raceNoKey(value: unknown): string {
  const parsed = num(value);
  if (parsed !== null) return String(Math.trunc(parsed));
  const match = clean(value).match(/\d+/);
  return match ? String(Number(match[0])) : compact(value);
}

function toRunner(row: Row): MarketRunner {
  const horse = first(row, ["horse", "runner", "runner_name", "selection_name"]);
  const track = first(row, ["track", "meeting", "meeting_name", "track_name"]);
  const raceNo = first(row, ["race_no", "raceNo", "race_number", "race"]);
  const canonicalKey = canonicalHorseKey(row, horse);

  return {
    id: `${compact(track)}-${raceNo}-${canonicalKey}`,
    horse,
    horseNo: firstNum(row, ["horse_no", "horseNo", "runner_number", "tab_no", "no", "saddlecloth"]),
    canonicalKey,
    track,
    raceNo,
    barrier: first(row, ["barrier", "bar", "barrier_no"]),
    silkUrl: first(row, ["local_silk_path", "silkUrl", "silk_url", "mobile_silk_image"]),
    isScratched: ["TRUE", "YES", "1", "SCRATCHED", "LATESCRATCHED"].includes(
      first(row, ["is_scratched", "scratch_status", "runner_status", "tab_fixed_betting_status"]).toUpperCase()
    ),
    live: firstNum(row, ["live_price", "sportsbet_price", "ui_price", "market_price", "fixed_win", "price"]),
    open: firstNum(row, ["open_price", "opening_price", "mid_price"]),
    previousPrice: firstNum(row, ["previous_price", "prev_price"]),
  };
}

function moveBase(row: MarketRunner): number | null {
  return row.previousPrice ?? row.open ?? null;
}

function movePct(row: MarketRunner): number | null {
  const base = moveBase(row);
  if (row.live === null || base === null || base <= 0) return null;
  return ((row.live - base) / base) * 100;
}

function marketMove(row: MarketRunner): "FIRMING" | "DRIFTING" | "STABLE" | "SCRATCHED" {
  if (row.isScratched) return "SCRATCHED";
  const move = movePct(row);
  if (move === null || Math.abs(move) < 1) return "STABLE";
  return move < 0 ? "FIRMING" : "DRIFTING";
}

function marketViewLabel(row: MarketRunner, favourite: MarketRunner | null): string {
  if (row.isScratched) return "SCRATCHED";
  if (favourite && row.canonicalKey === favourite.canonicalKey) return "MARKET LEADER";

  const move = marketMove(row);
  if (move === "FIRMING") return "SUPPORTED";
  if (move === "DRIFTING") return "SOFTENING";
  return "STABLE";
}

function pillColors(label: string): { background: string; border: string; color: string } {
  const value = label.toUpperCase();

  if (
    value.includes("SUPPORTED") ||
    value.includes("FIRMING") ||
    value.includes("HIGH") ||
    value.includes("CLEAR") ||
    value.includes("READY") ||
    value.includes("LIVE")
  ) {
    return {
      background: "rgba(16,185,129,0.18)",
      border: "rgba(16,185,129,0.4)",
      color: "#bbf7d0",
    };
  }

  if (
    value.includes("BALANCED") ||
    value.includes("MEDIUM") ||
    value.includes("STABLE") ||
    value.includes("OPEN") ||
    value.includes("NEUTRAL")
  ) {
    return {
      background: "rgba(245,158,11,0.18)",
      border: "rgba(245,158,11,0.4)",
      color: "#fde68a",
    };
  }

  if (
    value.includes("DRIFT") ||
    value.includes("WEAK") ||
    value.includes("LOW") ||
    value.includes("SCRATCH")
  ) {
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

function pill(label: string, minWidth = 84): React.ReactElement {
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
      {label || "—"}
    </span>
  );
}

function bookPercent(rows: MarketRunner[]): number | null {
  const priced = rows.filter((row) => !row.isScratched && row.live !== null && row.live > 0);
  if (!priced.length) return null;
  return priced.reduce((sum, row) => sum + (1 / Number(row.live)), 0) * 100;
}

function marketPersonality(activeRows: MarketRunner[], pricedRows: MarketRunner[], firmers: MarketRunner[], drifters: MarketRunner[]): string {
  const favourite = [...pricedRows].sort((a, b) => Number(a.live) - Number(b.live))[0] ?? null;
  if (!pricedRows.length) return "NO MARKET";
  if ((firmers.length + drifters.length) >= 4) return "ACTIVE MARKET";
  if ((firmers.length + drifters.length) <= 1) return "QUIET MARKET";
  if (favourite?.live !== null && favourite?.live !== undefined && favourite.live <= 2.5) return "CLEAR FAVOURITE";
  if (activeRows.length >= 10 && favourite?.live !== null && favourite?.live !== undefined && favourite.live >= 4) return "OPEN RACE";
  return "BALANCED MARKET";
}

function personalityCopy(personality: string, favouriteName: string): string {
  if (personality === "CLEAR FAVOURITE") return `${favouriteName} controls TAB betting and holds clear market leadership.`;
  if (personality === "OPEN RACE") return "TAB betting is spread across the field with no runner taking full market control.";
  if (personality === "ACTIVE MARKET") return "TAB prices are moving and market pressure is becoming more active.";
  if (personality === "QUIET MARKET") return "TAB market activity is quiet with limited meaningful movement.";
  if (personality === "NO MARKET") return "TAB prices are not currently available for this race.";
  return "TAB betting is balanced with no extreme market shape detected.";
}

export default function MarketTab({
  selectedMeetingKey,
  selectedRaceKey,
  currentMeeting,
  currentRace,
}: MarketTabProps): React.ReactElement {
  const [rows, setRows] = useState<MarketRunner[]>([]);
  const [updatedAt, setUpdatedAt] = useState("");
  const previousPrices = useRef<Record<string, number>>({});
  const [priceFlashes, setPriceFlashes] = useState<Record<string, "firm" | "drift">>({});
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;

    async function load(): Promise<void> {
      const terminalRows = await loadCsv("/data/edgeiq_vic_live_terminal_feed_v1.csv");
      const currentRaceRows = Array.isArray(currentRace?.rows) ? currentRace.rows : [];

      const selectedTrack = currentMeeting?.track || selectedTrackFromMeetingKey(selectedMeetingKey) || "";
      const selectedRaceNo = currentRace?.raceNo ? String(currentRace.raceNo) : selectedRaceNoFromRaceKey(selectedRaceKey);

      let nextRows = terminalRows
        .map(toRunner)
        .filter((row) => compact(row.track) === compact(selectedTrack) && compact(row.raceNo) === compact(selectedRaceNo))
        .filter((row) => row.horse)
        .sort((a, b) => {
          const aNo = a.horseNo ?? 999;
          const bNo = b.horseNo ?? 999;
          if (aNo !== bNo) return aNo - bNo;
          return a.horse.localeCompare(b.horse);
        });

      if (!nextRows.length && currentRaceRows.length) {
        nextRows = currentRaceRows
          .map((row) => toRunner(row))
          .filter((row) => row.horse)
          .filter((row) => !selectedTrack || compact(row.track) === compact(selectedTrack))
          .filter((row) => !selectedRaceNo || compact(row.raceNo) === compact(selectedRaceNo))
          .sort((a, b) => {
            const aNo = a.horseNo ?? 999;
            const bNo = b.horseNo ?? 999;
            if (aNo !== bNo) return aNo - bNo;
            return a.horse.localeCompare(b.horse);
          });
      }

      const nextFlashes: Record<string, "firm" | "drift"> = {};

      nextRows.forEach((row) => {
        if (!row.canonicalKey || row.live === null || row.isScratched) return;
        const previous = previousPrices.current[row.canonicalKey];
        if (previous !== undefined) {
          if (row.live < previous) nextFlashes[row.canonicalKey] = "firm";
          if (row.live > previous) nextFlashes[row.canonicalKey] = "drift";
        }
        previousPrices.current[row.canonicalKey] = row.live;
      });

      if (!aliveRef.current) return;

      setPriceFlashes(nextFlashes);
      window.setTimeout(() => {
        if (aliveRef.current) setPriceFlashes({});
      }, 1900);

      setRows(nextRows);
      setUpdatedAt(new Date().toLocaleTimeString());
    }

    void load();
    const timer = window.setInterval(load, REFRESH_MS);

    return () => {
      aliveRef.current = false;
      window.clearInterval(timer);
    };
  }, [selectedMeetingKey, selectedRaceKey, currentMeeting?.track, currentRace]);

  const meetingDisplayState = getMeetingDisplayState(currentMeeting);
  const futureMeetingWithFields = meetingDisplayState === "FUTURE_MEETING_WITH_FIELDS";
  const futureMeetingWithoutFields = meetingDisplayState === "FUTURE_MEETING_WITHOUT_FIELDS";
  const futureMeetingDayBucket = clean(currentMeeting?.dayBucket).replace("DAY+2", "DAY +2") || "UPCOMING";
  const futureMeetingStatus = clean(currentMeeting?.meetingStatus).replace(/_/g, " ") || "FIELDS PENDING";
  const selectedRaceLabel =
    currentMeeting?.track && currentRace?.raceNo
      ? `${currentMeeting.track} R${currentRace.raceNo}`
      : currentMeeting?.track || "Upcoming race";
  const selectedRaceMeta = [
    currentRace?.distance ? `${currentRace.distance}m` : "",
    clean(currentRace?.raceClass),
    clean(currentRace?.raceTime),
  ]
    .filter(Boolean)
    .join(" | ");
  const declaredFieldCount = Array.isArray((currentRace as any)?.rows) ? (currentRace as any).rows.length : 0;
  const futureMeetingPreviewOnly = futureMeetingWithFields && !rows.length && declaredFieldCount === 0;

  if (futureMeetingWithoutFields && currentMeeting) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">
            <span>EDGEiQ MARKET INTELLIGENCE</span>
            {pill(futureMeetingDayBucket, 96)}
          </div>

          <div style={{ padding: 12, display: "grid", gap: 12 }}>
            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Selected Meeting</div>
              <div className="edgeiq-mini-note-value">{currentMeeting.track}</div>
              <div className="edgeiq-mini-note-sub">
                {currentMeeting.raceDate} | {futureMeetingStatus}
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Market Pending</div>
              <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                TAB prices are not available yet because this meeting is still waiting on runner fields. EDGEiQ will populate market views automatically once the meeting becomes field-ready.
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Meeting Status</div>
                <div className="edgeiq-terminal-stat-value" style={{ color: "#fde68a" }}>
                  {futureMeetingStatus}
                </div>
                <div className="edgeiq-terminal-stat-sub">runner fields are still pending for this meeting</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">TAB Prices</div>
                <div className="edgeiq-terminal-stat-value">MARKET PENDING</div>
                <div className="edgeiq-terminal-stat-sub">no live prices shown until the meeting is field-ready</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Track Profile</div>
                <div className="edgeiq-terminal-stat-value">PROFILE PENDING</div>
                <div className="edgeiq-terminal-stat-sub">track intelligence will populate automatically later</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (futureMeetingPreviewOnly && currentMeeting) {
    return (
      <div className="edgeTabSurface">
        <section className="edgeiq-decision-panel">
          <div className="edgeiq-panel-title">
            <span>EDGEiQ MARKET INTELLIGENCE</span>
            {pill(futureMeetingDayBucket, 96)}
          </div>

          <div style={{ padding: 12, display: "grid", gap: 12 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Selected Meeting</div>
                <div className="edgeiq-mini-note-value">{currentMeeting.track}</div>
                <div className="edgeiq-mini-note-sub">
                  {currentMeeting.raceDate} | {futureMeetingStatus}
                </div>
              </div>
              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Selected Race</div>
                <div className="edgeiq-mini-note-value">{selectedRaceLabel}</div>
                <div className="edgeiq-mini-note-sub">
                  {selectedRaceMeta || "Fields are loaded and EDGEiQ is monitoring the race."}
                </div>
              </div>
            </div>

            <div className="edgeiq-mini-note">
              <div className="edgeiq-mini-note-label">Market Pending</div>
              <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                TAB prices are not available yet for this future race. EDGEiQ will populate market views automatically once TAB pre-race prices are released.
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Meeting Status</div>
                <div className="edgeiq-terminal-stat-value" style={{ color: "#bbf7d0" }}>
                  {futureMeetingStatus}
                </div>
                <div className="edgeiq-terminal-stat-sub">runner fields are already loaded for this meeting</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Declared Field</div>
                <div className="edgeiq-terminal-stat-value">{declaredFieldCount || "FIELDS READY"}</div>
                <div className="edgeiq-terminal-stat-sub">
                  {declaredFieldCount ? "runners currently loaded for the selected race" : "runner fields are available and awaiting market release"}
                </div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">TAB Prices</div>
                <div className="edgeiq-terminal-stat-value">MARKET PENDING</div>
                <div className="edgeiq-terminal-stat-sub">TAB prices will appear automatically when available</div>
              </div>
              <div className="edgeiq-terminal-stat">
                <div className="edgeiq-terminal-stat-label">Race Intelligence</div>
                <div className="edgeiq-terminal-stat-value">INTELLIGENCE PENDING</div>
                <div className="edgeiq-terminal-stat-sub">market-linked race intelligence is waiting on pre-race feeds</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  const activeRows = rows.filter((row) => !row.isScratched);
  const pricedRows = activeRows.filter((row) => row.live !== null && row.live > 0);
  const favourite = [...pricedRows].sort((a, b) => Number(a.live) - Number(b.live))[0] ?? null;

  const firmers = activeRows.filter((row) => marketMove(row) === "FIRMING");
  const drifters = activeRows.filter((row) => marketMove(row) === "DRIFTING");
  const stable = activeRows.filter((row) => marketMove(row) === "STABLE");

  const strongestFirm = [...firmers].sort((a, b) => (movePct(a) ?? 0) - (movePct(b) ?? 0))[0] ?? null;
  const strongestDrift = [...drifters].sort((a, b) => (movePct(b) ?? 0) - (movePct(a) ?? 0))[0] ?? null;

  const personality = marketPersonality(activeRows, pricedRows, firmers, drifters);
  const track = rows[0]?.track || "-";
  const raceNo = rows[0]?.raceNo || "-";
  const overround = bookPercent(rows);

  const marketConfidence =
    pricedRows.length >= Math.max(1, activeRows.length - 1)
      ? "HIGH"
      : pricedRows.length >= Math.max(1, Math.floor(activeRows.length * 0.7))
        ? "MEDIUM"
        : "LOW";

  const marketState =
    firmers.length > drifters.length + 1
      ? "SUPPORT"
      : drifters.length > firmers.length + 1
        ? "DRIFTING"
        : firmers.length + drifters.length === 0
          ? "QUIET"
          : "BALANCED";

  const marketPendingOnly = futureMeetingWithFields && activeRows.length > 0 && pricedRows.length === 0;

  const story =
    marketPendingOnly
      ? "Runner fields are loaded for this future race, but TAB pre-race prices are not available yet. EDGEiQ is showing the declared field while live market coverage remains pending."
      : personality === "QUIET MARKET"
      ? `The TAB market remains stable with little meaningful movement. ${favourite?.horse || "The market leader"} continues to hold favouritism at ${money(favourite?.live ?? null)}. No significant support or drift has emerged and market conviction remains ${marketConfidence.toLowerCase()}.`
      : personality === "ACTIVE MARKET"
        ? `TAB prices are becoming more active approaching jump time. ${firmers.length} runner${firmers.length === 1 ? "" : "s"} firming and ${drifters.length} drifting as market sentiment begins to take shape.`
        : personality === "OPEN RACE"
          ? `TAB betting remains spread across the field with no runner fully controlling the market. The race currently presents a competitive market profile.`
          : `${personalityCopy(personality, favourite?.horse || "The market leader")} ${pricedRows.length} active runners are priced by TAB.`;

  const marketStatusTone =
    marketState === "SUPPORT"
      ? "SUPPORTED"
      : marketState === "DRIFTING"
        ? "SOFTENING"
        : marketState === "QUIET"
          ? "QUIET"
          : "BALANCED";

  const topCards = [
    {
      label: "Active Runners",
      value: String(activeRows.length),
      sub: "runners still active in the TAB market",
      color: "#e2e8f0",
    },
    {
      label: "Scratched",
      value: String(Math.max(0, rows.length - activeRows.length)),
      sub: "scratchings already reflected in the race",
      color: "#cbd5e1",
    },
    {
      label: "TAB Prices",
      value: String(pricedRows.length),
      sub: `${activeRows.length ? Math.round((pricedRows.length / activeRows.length) * 100) : 0}% of active runners priced`,
      color: "#bbf7d0",
    },
    {
      label: "Market Leader",
      value: favourite?.horse || "No leader yet",
      sub: favourite ? `${money(favourite.live)} TAB price` : "TAB leader not established yet",
      color: "#7dd3fc",
    },
    {
      label: "Biggest Firmer",
      value: strongestFirm?.horse || "None",
      sub: strongestFirm ? `${money(moveBase(strongestFirm))} to ${money(strongestFirm.live)}` : "no meaningful support detected",
      color: "#fde68a",
    },
    {
      label: "Market Depth",
      value: overround !== null ? `${overround.toFixed(1)}%` : "—",
      sub: "TAB overround across priced active runners",
      color: "#fca5a5",
    },
  ] as const;

  return (
    <div className="edgeTabSurface">
      <section className="edgeiq-decision-panel">
        <div className="edgeiq-panel-title">
          <span>EDGEiQ MARKET INTELLIGENCE</span>
          {pill(updatedAt ? `Updated ${updatedAt}` : "Live", updatedAt ? 128 : 72)}
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
              <div className="edgeiq-mini-note-label">Selected Race</div>
              <div className="edgeiq-mini-note-value">{track !== "-" ? `${track} R${raceNo}` : "TAB market view"}</div>
              <div className="edgeiq-mini-note-sub">
                How TAB is shaping the selected race right now.
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              {pill(personality, 112)}
              {pill(`${marketConfidence} CONFIDENCE`, 126)}
            </div>
          </div>

          {!rows.length ? (
            <div className="edgeiq-no-live">TAB prices are not available for the selected race yet.</div>
          ) : (
            <>
              {marketPendingOnly ? (
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">Market Pending</div>
                  <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                    TAB prices are not available yet for this future race. EDGEiQ runner context is loaded and market fields will populate automatically when TAB releases pre-race prices.
                  </div>
                </div>
              ) : null}

              <div className="edgeiq-mini-note">
                <div className="edgeiq-mini-note-label">Market Story</div>
                <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                  {story}
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: 10,
                }}
              >
                {topCards.map((card) => (
                  <div key={card.label} className="edgeiq-terminal-stat" style={{ minHeight: 100 }}>
                    <div className="edgeiq-terminal-stat-label">{card.label}</div>
                    <div className="edgeiq-terminal-stat-value" style={{ color: card.color, fontSize: card.value.length > 18 ? 18 : 22 }}>
                      {card.value}
                    </div>
                    <div className="edgeiq-terminal-stat-sub">{card.sub}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      {!!rows.length ? (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              gap: 12,
            }}
          >
            <section className="edgeiq-decision-panel">
              <div className="edgeiq-panel-title">MARKET MOVERS</div>
              <div
                style={{
                  padding: 12,
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                  gap: 10,
                }}
              >
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">Market Leader</div>
                  <div className="edgeiq-mini-note-value">{favourite?.horse || "No leader yet"}</div>
                  <div className="edgeiq-mini-note-sub">{favourite ? `${money(favourite.live)} TAB price` : "TAB leader not established yet"}</div>
                </div>
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">Strongest Firmer</div>
                  <div className="edgeiq-mini-note-value">{strongestFirm?.horse || "No firmer"}</div>
                  <div className="edgeiq-mini-note-sub">
                    {strongestFirm ? `${money(moveBase(strongestFirm))} to ${money(strongestFirm.live)}` : "No meaningful support is showing yet"}
                  </div>
                </div>
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">Largest Drifter</div>
                  <div className="edgeiq-mini-note-value">{strongestDrift?.horse || "No drifter"}</div>
                  <div className="edgeiq-mini-note-sub">
                    {strongestDrift ? `${money(moveBase(strongestDrift))} to ${money(strongestDrift.live)}` : "No meaningful softening is showing yet"}
                  </div>
                </div>
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">Stable Runners</div>
                  <div className="edgeiq-mini-note-value">{stable.length}</div>
                  <div className="edgeiq-mini-note-sub">active runners holding a stable TAB quote</div>
                </div>
              </div>
            </section>

            <section className="edgeiq-decision-panel">
              <div className="edgeiq-panel-title">MARKET PICTURE</div>
              <div style={{ padding: 12, display: "grid", gap: 10 }}>
                <div className="edgeiq-mini-note">
                  <div className="edgeiq-mini-note-label">TAB Read</div>
                  <div style={{ marginTop: 6, color: "#dbe7f3", fontSize: 13, lineHeight: 1.55 }}>
                    TAB market activity is currently reading <strong style={{ color: "#f8fafc" }}>{marketStatusTone.toLowerCase()}</strong>, with <strong style={{ color: "#f8fafc" }}>{pricedRows.length}</strong> active runners carrying a price and <strong style={{ color: "#f8fafc" }}>{firmers.length + drifters.length}</strong> runners showing meaningful movement.
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                    gap: 10,
                  }}
                >
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Market State</div>
                    <div className="edgeiq-mini-note-value">{marketStatusTone}</div>
                    <div className="edgeiq-mini-note-sub">overall direction of the TAB market</div>
                  </div>
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">TAB Coverage</div>
                    <div className="edgeiq-mini-note-value">{activeRows.length ? `${Math.round((pricedRows.length / activeRows.length) * 100)}%` : "0%"}</div>
                    <div className="edgeiq-mini-note-sub">active runners currently carrying a TAB quote</div>
                  </div>
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Market Depth</div>
                    <div className="edgeiq-mini-note-value">{overround !== null ? `${overround.toFixed(1)}%` : "—"}</div>
                    <div className="edgeiq-mini-note-sub">TAB overround across the live field</div>
                  </div>
                  <div className="edgeiq-mini-note">
                    <div className="edgeiq-mini-note-label">Movement Count</div>
                    <div className="edgeiq-mini-note-value">{firmers.length + drifters.length}</div>
                    <div className="edgeiq-mini-note-sub">runners showing support or softening</div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <section className="edgeiq-decision-panel">
            <div className="edgeiq-panel-title">TAB PRICE BOARD</div>
            <div style={{ padding: 12, display: "grid", gap: 8 }}>
              <div className="edgeiq-data-note">Runner | Barrier | Opening Price | TAB Price | Move | Market View</div>

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
                    minWidth: 860,
                    fontSize: 12,
                  }}
                >
                  <thead>
                    <tr style={{ background: "rgba(15,23,42,0.96)" }}>
                      {["#", "RUNNER", "BARRIER", "OPENING PRICE", "TAB PRICE", "MOVE", "MARKET VIEW"].map((header) => (
                        <th
                          key={header}
                          style={{
                            textAlign: header === "#" || header === "BARRIER" ? "center" : header.includes("PRICE") ? "right" : "left",
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
                    {rows.map((row, index) => {
                      const move = marketMove(row);
                      const viewLabel = marketViewLabel(row, favourite);
                      const priceFlash = priceFlashes[row.canonicalKey];
                      const scratched = row.isScratched;
                      const pendingTabPrice = futureMeetingWithFields && !scratched && row.live === null;

                      return (
                        <tr
                          key={row.id}
                          style={{
                            background: scratched
                              ? "rgba(30,41,59,0.18)"
                              : index % 2 === 0
                                ? "rgba(2,6,23,0.55)"
                                : "rgba(15,23,42,0.38)",
                            opacity: scratched ? 0.5 : 1,
                            filter: scratched ? "grayscale(0.85)" : undefined,
                          }}
                        >
                          <td style={{ ...tableCellStyle, textAlign: "center", color: scratched ? "#94a3b8" : "#e2e8f0", fontWeight: 900 }}>
                            {row.horseNo ?? index + 1}
                          </td>
                          <td style={{ ...tableCellStyle, color: scratched ? "#94a3b8" : "#f8fafc", fontWeight: 900 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                              {row.silkUrl ? (
                                <img
                                  src={row.silkUrl}
                                  alt=""
                                  loading="lazy"
                                  style={{ width: 22, height: 22, borderRadius: 999, objectFit: "cover", border: "1px solid rgba(148,163,184,0.2)" }}
                                />
                              ) : (
                                <span
                                  style={{
                                    width: 22,
                                    height: 22,
                                    borderRadius: 999,
                                    border: "1px solid rgba(71,85,105,0.65)",
                                    background: "rgba(15,23,42,0.85)",
                                    display: "inline-flex",
                                  }}
                                />
                              )}
                              <span>{row.horse}</span>
                              {scratched ? pill("SCRATCHED", 88) : null}
                            </div>
                          </td>
                          <td style={{ ...tableCellStyle, textAlign: "center", color: scratched ? "#94a3b8" : "#dbeafe" }}>{row.barrier || "—"}</td>
                          <td style={{ ...tableNumberStyle, color: scratched ? "#94a3b8" : "#dbeafe" }}>
                            {scratched ? "—" : money(moveBase(row))}
                          </td>
                          <td
                            style={{
                              ...tableNumberStyle,
                              color: scratched ? "#94a3b8" : "#f8fafc",
                              background:
                                pendingTabPrice
                                  ? "rgba(245,158,11,0.08)"
                                  : priceFlash === "firm"
                                  ? "rgba(16,185,129,0.12)"
                                  : priceFlash === "drift"
                                    ? "rgba(248,113,113,0.12)"
                                    : undefined,
                            }}
                          >
                            {scratched ? "—" : pendingTabPrice ? "MARKET PENDING" : money(row.live)}
                          </td>
                          <td style={{ ...tableCellStyle, textAlign: "center" }}>
                            {pill(pendingTabPrice ? "PENDING" : move, 92)}
                          </td>
                          <td style={tableCellStyle}>
                            {pill(pendingTabPrice ? "PENDING" : viewLabel, 112)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

const tableCellStyle: React.CSSProperties = {
  padding: "10px 12px",
  borderBottom: "1px solid rgba(148,163,184,0.08)",
  color: "#dbeafe",
  whiteSpace: "nowrap",
};

const tableNumberStyle: React.CSSProperties = {
  ...tableCellStyle,
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
  fontWeight: 800,
};



