import React from "react";
type Row = Record<string, any>;
type BenchmarkMode = "CLASS_BENCHMARK" | "ALL_CLASSES_BENCHMARK";

type EnrichedRunnerLike = {
  row: Row;
  runnerHistory?: Row[];
  runnerCareer?: Row;
  [key: string]: any;
};

type FormRunCard = {
  key: string;
  date: string;
  track: string;
  distance: string;
  raceClass: string;
  going: string;
  barrier: string;
  jockey: string;
  finishingPosition: string;
  beatenMargin: string;
  sp: string;
  rating: number | null;
};

type ProfileGroup = {
  title: string;
  rows: [string, { starts: number; wins: number; places: number; ratingTotal: number; ratingCount: number }][];
};

type RaceFormWorkspaceProps = {
  selected: EnrichedRunnerLike;
  formSelector: React.ReactNode;
  formRows: FormRunCard[];
  projected: number | null;
  formNarrative: string;
  trajectoryValues: { label: string; value: number | null }[];
  profileGroups: ProfileGroup[];
  gearProfileRows: Row[];
  formSectionalProfileRows: Row[];
  formBenchmarkMode: BenchmarkMode;
  selectedRunnerToken: string;
  selectedBestRatingLast5Value: number | null;
  selectedAVGRatingLast5Value: number | null;
  careerStarts: number | null;
  careerWins: number | null;
  careerPlaces: number | null;
  careerWinPct: number | null;
  careerPlacePct: number | null;

  setFormBenchmarkMode: (value: BenchmarkMode) => void;
  setFullHistoryRunner: (value: EnrichedRunnerLike) => void;

  horse: (row: Row) => string;
  saddle: (row: Row) => number;
  firstText: (row: Row | undefined, keys: string[], fallback?: string) => string;
  text: (value: unknown) => string;
  num: (value: unknown) => number | null;
  signed: (value: number, digits?: number) => string;
  renderMetricValue: (value: number | null, digits?: number, signedMode?: boolean) => string;
  cleanHorse: (value: unknown) => string;
  cleanTrack: (value: unknown) => string;
};

export function RaceFormWorkspace(props: RaceFormWorkspaceProps) {
  const {
    selected,
    formSelector,
    formRows,
    projected,
    formNarrative,
    trajectoryValues,
    profileGroups,
    gearProfileRows,
    formSectionalProfileRows,
    formBenchmarkMode,
    selectedRunnerToken,
    selectedBestRatingLast5Value,
    selectedAVGRatingLast5Value,
    careerStarts,
    careerWins,
    careerPlaces,
    careerWinPct,
    careerPlacePct,
    setFormBenchmarkMode,
    setFullHistoryRunner,
    horse,
    saddle,
    firstText,
    text,
    num,
    signed,
    renderMetricValue,
    cleanHorse,
    cleanTrack,
  } = props;

  const empty = "-";

  const cleanRunText = (value: unknown) => {
    const raw = String(value ?? "").trim();
    if (!raw || /^(UNKNOWN|NOT LOADED|SOURCE GAP|SOURCE_MISSING|NULL|N\/A|NA|UNDEFINED|0\.0)$/i.test(raw)) return "-";
    return raw;
  };

  const cleanPosition = (value: unknown) => {
    const raw = cleanRunText(value);
    const numeric = Number(String(raw).replace(/[^0-9.-]/g, ""));
    if (Number.isFinite(numeric) && (numeric > Math.max(formRows.length, 1) + 25 || numeric > 30 || numeric <= 0)) return "-";
    return raw;
  };

  const posClass = (value: string) => {
    const numeric = Number(String(value).replace(/[^0-9.-]/g, ""));
    if (!Number.isFinite(numeric)) return "";
    if (numeric === 1) return "pos-good";
    if (numeric >= 7) return "pos-bad";
    return "";
  };

  const formHeatClass = (value: number | null) => {
    if (value === null) return "epi-heat-cell epi-heat-missing";
    const scoreBand =
      value >= 80 ? "epi-heat-elite" :
      value >= 70 ? "epi-heat-strong" :
      value >= 60 ? "epi-heat-positive" :
      value >= 50 ? "epi-heat-neutral" :
      value >= 40 ? "epi-heat-risk" :
      "epi-heat-poor";
    return `epi-heat-cell ${scoreBand}`;
  };

  const dateToken = (value: unknown) => {
    const raw = cleanRunText(value);
    const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (iso) return `${iso[1]}${iso[2]}${iso[3]}`;

    const compact = raw.match(/^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{2,4})$/);
    if (compact) {
      const months: Record<string, string> = {
        JAN: "01", FEB: "02", MAR: "03", APR: "04", MAY: "05", JUN: "06",
        JUL: "07", AUG: "08", SEP: "09", SEPT: "09", OCT: "10", NOV: "11", DEC: "12",
      };
      const year = compact[3].length === 2 ? `20${compact[3]}` : compact[3];
      return `${year}${months[compact[2].slice(0, 3).toUpperCase()] || "00"}${compact[1].padStart(2, "0")}`;
    }

    return raw.replace(/[^0-9A-Z]/gi, "").toUpperCase();
  };

  const gearRowsForRunner = gearProfileRows
    .filter((row) => cleanHorse(firstText(row, ["normalized_runner", "runner"], "")) === selectedRunnerToken)
    .sort((a, b) => dateToken(b.race_date).localeCompare(dateToken(a.race_date)));

  const sectionalRowsForRunner = formSectionalProfileRows
    .filter((row) => cleanHorse(firstText(row, ["normalized_runner", "runner"], "")) === selectedRunnerToken && firstText(row, ["benchmark_mode"], "") === formBenchmarkMode)
    .sort((a, b) => dateToken(b.race_date).localeCompare(dateToken(a.race_date)));

  const matchHistoricalFeedRow = (rows: Row[], run: FormRunCard) => {
    const runDate = dateToken(run.date);
    const runTrack = cleanTrack(run.track);
    return rows.find((row) => dateToken(row.race_date) === runDate && (!runTrack || cleanTrack(row.track) === runTrack)) || null;
  };

  const gearForRun = (run: FormRunCard) => matchHistoricalFeedRow(gearRowsForRunner, run);
  const currentGearRow = gearRowsForRunner[0] || null;
  const currentGear = cleanRunText(firstText(currentGearRow || undefined, ["gear_current"], ""));
  const currentGearChange = cleanRunText(firstText(currentGearRow || undefined, ["gear_changes", "gear_added", "gear_removed"], ""));
  const sectionalForRun = (run: FormRunCard) => matchHistoricalFeedRow(sectionalRowsForRunner, run);
  const leadingSectionalRow = formRows.map((run) => sectionalForRun(run)).find((row): row is Row => !!row) || sectionalRowsForRunner[0] || null;
  const splitLabels = text(leadingSectionalRow?.split_labels).split(";").filter(Boolean);
  const splitLengths = text(leadingSectionalRow?.split_lengths).split(";").map((value) => num(value));
  const splitPairs = splitLabels.map((label, index) => ({ label, value: splitLengths[index] ?? null })).filter((entry) => entry.label);

  return (
    <section className="edgeiq-form-showcase edgeiq-product-section edgeiq-product-v4-panel edgeiq-form-showcase-v2 edgeiq-form-clean-v3 edgeiq-form-study-v2 edgeiq-form-profile-v4 edgeiq-form-dossier-match">
      {formSelector}

      <div className="edgeiq-form-study-header edgeiq-form-profile-header">
        <span className="edgeiq-field-silk edgeiq-form-profile-silk" aria-label={`${horse(selected.row)} silk`}><i /></span>
        <div>
          <span>FORM</span>
          <strong>{saddle(selected.row) === 999 ? "-" : saddle(selected.row)} {horse(selected.row)}</strong>
          <em>{firstText(selected.row, ["jockey", "jockey_name", "rider"], "-")} / {firstText(selected.row, ["trainer", "trainer_name"], "-")}</em>
        </div>
        <div className="edgeiq-form-study-inline-metrics">
          {[["Current EPI", projected], ["Peak", selectedBestRatingLast5Value], ["Average", selectedAVGRatingLast5Value]].map(([label, value]) => (
            <span key={`form-study-inline-${label}`}>
              <b>{label}</b>
              <strong>{typeof value === "number" ? renderMetricValue(value, 1) : empty}</strong>
            </span>
          ))}
        </div>
      </div>

      <div className="edgeiq-form-gear-bar">
        <span><b>Current Gear</b><strong>{currentGear === "-" ? "No gear listed" : currentGear}</strong></span>
        <span><b>Gear Change</b><strong>{currentGearChange === "-" ? "No recorded change" : currentGearChange}</strong></span>
      </div>

      <section className="edgeiq-form-sectional-strip-panel">
        <div className="edgeiq-form-sectional-strip-head">
          <div>
            <span>EDGEiQ Standardised Sectionals</span>
            <strong>{formBenchmarkMode === "CLASS_BENCHMARK" ? "Class benchmark" : "All-classes benchmark"}</strong>
          </div>
          <div className="edgeiq-form-benchmark-toggle">
            {(["CLASS_BENCHMARK", "ALL_CLASSES_BENCHMARK"] as BenchmarkMode[]).map((mode) => (
              <button type="button" key={`form-benchmark-${mode}`} className={formBenchmarkMode === mode ? "is-active" : ""} onClick={() => setFormBenchmarkMode(mode)}>
                {mode === "CLASS_BENCHMARK" ? "Class" : "All-classes"}
              </button>
            ))}
          </div>
        </div>

        {splitPairs.length ? (
          <div className="edgeiq-form-sectional-strip">
            {splitPairs.map((entry) => (
              <span key={`form-split-${entry.label}`} className={entry.value === null ? "is-missing" : entry.value < 0 ? "is-fast" : "is-neutral"}>
                <b>{entry.label}</b>
                <strong>{entry.value === null ? empty : `${signed(entry.value, 1)}L`}</strong>
              </span>
            ))}
          </div>
        ) : (
          <div className="edgeiq-form-sectional-empty">No benchmark-backed sectional splits available for this runner.</div>
        )}
      </section>

      <section className="edgeiq-form-last-five edgeiq-form-last-five-wide">
        <div className="edgeiq-form-table-title">Last Five Starts</div>
        <div className="edgeiq-form-table edgeiq-product-v4-table">
          <div className="edgeiq-form-table-row head">
            {["Date", "Track", "Dist", "Class", "Going", "Bar", "Jockey", "Gear", "Pos", "Margin", "SP", "Rating"].map((label) => (
              <span key={`form-main-head-${label}`}>{label}</span>
            ))}
          </div>

          {!formRows.length ? (
            <div className="edgeiq-form-table-empty">No detailed performance-history lines available.</div>
          ) : formRows.map((run) => {
            const pos = cleanPosition(run.finishingPosition);
            const runGear = gearForRun(run);
            const gearText = cleanRunText(firstText(runGear || undefined, ["gear_changes", "gear_current", "gear_added", "gear_removed"], ""));
            return (
              <div key={`form-main-row-${run.key}`} className="edgeiq-form-table-row edgeiq-form-profile-row edgeiq-form-table-row-gear">
                <span>{cleanRunText(run.date)}</span>
                <span>{cleanRunText(run.track)}</span>
                <span>{cleanRunText(run.distance)}</span>
                <span>{cleanRunText(run.raceClass)}</span>
                <span>{cleanRunText(run.going)}</span>
                <span>{cleanRunText(run.barrier)}</span>
                <span>{cleanRunText(run.jockey)}</span>
                <span>{gearText}</span>
                <span className={posClass(pos)}>{pos}</span>
                <span>{cleanRunText(run.beatenMargin)}</span>
                <span>{cleanRunText(run.sp)}</span>
                <span>{run.rating !== null ? renderMetricValue(run.rating, 1) : "-"}</span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="edgeiq-form-trajectory-strip" aria-label="Rating progression">
        {trajectoryValues.map((entry) => (
          <span key={`form-trajectory-${entry.label}`} className={formHeatClass(entry.value)}>
            <b>{entry.label}</b>
            <strong>{entry.value === null ? empty : renderMetricValue(entry.value, 1)}</strong>
          </span>
        ))}
      </div>

      <div className="edgeiq-form-profile-grid">
        {profileGroups.map((group) => (
          <section key={`form-profile-${group.title}`} className="edgeiq-form-profile-panel">
            <strong>{group.title} Profile</strong>
            <div className="edgeiq-form-profile-table edgeiq-product-v4-table">
              <div className="edgeiq-form-profile-table-row head">
                <span>{group.title}</span><span>Starts</span><span>Wins</span><span>Places</span><span>Rating</span>
              </div>
              {group.rows.length ? group.rows.map(([label, bucket]) => (
                <div className="edgeiq-form-profile-table-row" key={`profile-${group.title}-${label}`}>
                  <span>{label}</span>
                  <span>{bucket.starts}</span>
                  <span>{bucket.wins}</span>
                  <span>{bucket.places}</span>
                  <span>{bucket.ratingCount ? renderMetricValue(bucket.ratingTotal / bucket.ratingCount, 1) : empty}</span>
                </div>
              )) : (
                <div className="edgeiq-form-profile-empty">Profile not loaded</div>
              )}
            </div>
          </section>
        ))}
      </div>

      <section className="edgeiq-form-career-summary">
        <strong>Career Summary</strong>
        <div>
          {[["Starts", careerStarts], ["Wins", careerWins], ["Places", careerPlaces], ["Win %", careerWinPct], ["Place %", careerPlacePct]].map(([label, value]) => (
            <article key={`form-career-${label}`}>
              <span>{label}</span>
              <b>{typeof value === "number" ? (String(label).includes("%") ? `${value.toFixed(1)}%` : String(Math.trunc(value))) : empty}</b>
            </article>
          ))}
          <button type="button" className="edgeiq-field-history-link" onClick={() => setFullHistoryRunner(selected)}>Full history</button>
        </div>
      </section>

      {formNarrative ? <p className="edgeiq-form-short-read">{formNarrative}</p> : null}
    </section>
  );
}

