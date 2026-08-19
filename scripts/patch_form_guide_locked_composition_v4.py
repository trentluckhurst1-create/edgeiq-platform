from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

tsx_backup = TSX.with_name(
    f"{TSX.stem}_CHECKPOINT_BEFORE_LOCKED_COMPOSITION_V4_{stamp}{TSX.suffix}"
)
css_backup = CSS.with_name(
    f"{CSS.stem}_CHECKPOINT_BEFORE_LOCKED_COMPOSITION_V4_{stamp}{CSS.suffix}"
)

shutil.copy2(TSX, tsx_backup)
shutil.copy2(CSS, css_backup)

tsx = TSX.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

# ============================================================
# FUNCTION REPLACEMENT UTILITY
# ============================================================

def replace_function(source: str, function_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"^function {re.escape(function_name)}\b[\s\S]*?(?=^function |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(source)

    if not match:
        raise SystemExit(
            f"PATCH_ABORTED: function {function_name} was not found. "
            "No active files were written."
        )

    return source[:match.start()] + replacement.rstrip() + "\n\n" + source[match.end():]


# ============================================================
# 1. VALUE-FIRST LOCKED METRIC RIBBON
# ============================================================

current_metric_strip = r'''
function CurrentMetricStrip({ runner }: { runner: FormGuideRunnerDisplay }) {
  const metrics = [
    {
      key: "epi",
      label: "EPI TODAY",
      value: runner.epi,
      supporting: runner.epiDifference,
    },
    {
      key: "eri",
      label: "ERI",
      value: runner.rating,
      supporting: runner.epiRank ? `Rank ${runner.epiRank}` : "",
    },
    {
      key: "suitability",
      label: "SUITABILITY",
      value: runner.suitabilityScore,
      supporting: runner.suitabilityLabel,
    },
    {
      key: "momentum",
      label: "FORM MOMENTUM",
      value: runner.formMomentum,
      supporting:
        runner.formMomentumDirection === "up"
          ? "Rising"
          : runner.formMomentumDirection === "down"
            ? "Easing"
            : "",
    },
    {
      key: "edge",
      label: "EDGE",
      value: runnerValueDeltaDisplay(runner),
      supporting: "",
    },
    {
      key: "fair",
      label: "EDGEiQ PRICE (FAIR)",
      value: runner.edgeiqPrice,
      supporting: "",
    },
    {
      key: "market",
      label: "MARKET",
      value: runner.marketPrice,
      supporting: "",
    },
  ];

  return (
    <dl
      className="eiq-form-v4-current-strip eiq-form-final-current-strip eiq-form-locked-metric-ribbon"
      data-region="hero_metrics"
    >
      {metrics.map((metric) => (
        <div
          key={metric.key}
          className={metric.value ? "" : "is-empty"}
          data-metric={metric.key}
        >
          <dd>{cleanDisplay(metric.value)}</dd>
          <dt>{metric.label}</dt>
          {metric.supporting ? (
            <small>{cleanDisplay(metric.supporting)}</small>
          ) : (
            <small aria-hidden="true">&nbsp;</small>
          )}
        </div>
      ))}
    </dl>
  );
}
'''

tsx = replace_function(tsx, "CurrentMetricStrip", current_metric_strip)

# ============================================================
# 2. HORSE PROFILE MATRIX WITH LOCKED LEGEND
# ============================================================

horse_profile_matrix = r'''
function HorseProfileMatrix({ runner }: { runner: FormGuideRunnerDisplay }) {
  const career = profileLineByLabel(runner.careerProfile, ["Career"]);
  const distance = profileLineByLabel(runner.careerProfile, ["Distance"]);
  const track = profileLineByLabel(runner.careerProfile, ["Track"]);
  const trackDistance = profileLineByLabel(runner.careerProfile, ["Track/Dist", "Track Distance"]);
  const firm = profileLineByLabel(runner.conditionProfile, ["Firm"]);
  const todayGoing =
    runner.conditionProfile.find((row) => row.matchesToday) ??
    profileLineByLabel(runner.conditionProfile, ["Good"]);
  const soft = profileLineByLabel(runner.conditionProfile, ["Soft"]);
  const heavy = profileLineByLabel(runner.conditionProfile, ["Heavy"]);
  const todayClass = bestProfileLine(runner.classProfile);
  const jockey = profileLineByLabel(runner.jockeyProfile, ["Current Jockey", "Jockey"]);
  const firstUp = profileLineByLabel(runner.raceDayPattern, ["1st Up", "First Up"]);
  const secondUp = profileLineByLabel(runner.raceDayPattern, ["2nd Up", "Second Up"]);
  const thirdUp = profileLineByLabel(runner.raceDayPattern, ["3rd Up", "Third Up"]);

  const columns: ProfileMatrixColumn[] = [
    { key: "career", label: "CAREER", today: false, primary: false, source: career },
    { key: "today_distance", label: "DISTANCE", today: Boolean(distance?.matchesToday || distance?.record), primary: false, source: distance },
    { key: "today_track", label: "TRACK", today: Boolean(track?.matchesToday || track?.record), primary: false, source: track },
    { key: "firm", label: "FIRM", today: false, primary: false, source: firm },
    { key: "today_going", label: todayGoing?.label || "GOING", today: Boolean(todayGoing?.matchesToday || todayGoing?.record), primary: true, source: todayGoing },
    { key: "soft", label: "SOFT", today: false, primary: false, source: soft },
    { key: "heavy", label: "HEAVY", today: false, primary: false, source: heavy },
    { key: "track_dist", label: "TRACK/DIST", today: Boolean(trackDistance?.matchesToday || trackDistance?.record), primary: false, source: trackDistance },
    { key: "today_class", label: "CLASS", today: Boolean(todayClass?.matchesToday || todayClass?.record), primary: false, source: todayClass },
    { key: "today_jockey", label: "JOCKEY", today: Boolean(jockey?.matchesToday || jockey?.record), primary: false, source: jockey },
    { key: "first_up", label: "1ST UP", today: false, primary: false, source: firstUp },
    { key: "second_up", label: "2ND UP", today: false, primary: false, source: secondUp },
    { key: "third_up", label: "3RD UP", today: false, primary: false, source: thirdUp },
  ];

  const rows: Array<[ProfileMetricKey, string]> = [
    ["starts", "STARTS"],
    ["wins", "WINS"],
    ["places", "PLACES"],
    ["winPct", "WIN %"],
    ["placePct", "PLACE %"],
    ["avgEpi", "AVG EPI"],
    ["avgEri", "AVG ERI"],
  ];

  return (
    <section className="eiq-form-final-profile-matrix" data-region="profile_matrix">
      <header>
        <span>HORSE PROFILE</span>
      </header>

      <div
        className="eiq-form-final-profile-grid"
        role="table"
        aria-label="Horse Profile Career Matrix"
      >
        <div className="eiq-form-final-profile-cell eiq-form-final-profile-cell--head">
          CATEGORY
        </div>

        {columns.map((column) => (
          <div
            key={column.key}
            className={`eiq-form-final-profile-cell eiq-form-final-profile-cell--head ${column.today ? "is-today" : ""} ${column.primary ? "is-primary" : ""}`.trim()}
          >
            {column.today ? <em>TODAY</em> : null}
            <strong>{column.label}</strong>
          </div>
        ))}

        {rows.map(([metric, label]) => (
          <Fragment key={metric}>
            <div className="eiq-form-final-profile-cell eiq-form-final-profile-cell--rowhead">
              {label}
            </div>

            {columns.map((column) => (
              <div
                key={`${metric}-${column.key}`}
                className={`eiq-form-final-profile-cell ${column.today ? "is-today" : ""} ${column.primary ? "is-primary" : ""}`.trim()}
              >
                {cleanDisplay(profileMetricValue(column, metric, runner))}
              </div>
            ))}
          </Fragment>
        ))}
      </div>

      <div className="eiq-form-profile-legend" aria-label="Horse profile highlighting legend">
        <span>
          <i className="is-today" aria-hidden="true" />
          Blue outline = today&apos;s matching condition
        </span>
        <span>
          <i className="is-primary" aria-hidden="true" />
          Green column = primary today&apos;s condition
        </span>
      </div>
    </section>
  );
}
'''

tsx = replace_function(tsx, "HorseProfileMatrix", horse_profile_matrix)

# ============================================================
# 3. GOVERNED TODAY'S MATCH — NO STARS, NO INVENTED SCORES
# ============================================================

today_match = r'''
function TodayMatch({ runner }: { runner: FormGuideRunnerDisplay }) {
  const track = profileLineByLabel(runner.careerProfile, ["Track"]);
  const distance = profileLineByLabel(runner.careerProfile, ["Distance"]);
  const going = runner.conditionProfile.find((row) => row.matchesToday) ?? null;
  const classMatch = bestProfileLine(runner.classProfile);

  const rows = [
    {
      label: "Track",
      value: track?.label || "Current Track",
      evidence: track?.record || "",
    },
    {
      label: "Distance",
      value: distance?.label || "Today Distance",
      evidence: distance?.record || "",
    },
    {
      label: "Going",
      value: going?.label || "",
      evidence: going?.record || "",
    },
    {
      label: "Rail",
      value: "",
      evidence: "",
    },
    {
      label: "Tempo",
      value: runner.shapeFit || "",
      evidence: "",
    },
    {
      label: "Pace Setup",
      value: runner.earlySpeed || runner.late || "",
      evidence: "",
    },
  ];

  return (
    <aside
      className="eiq-form-v4-today-match eiq-form-final-today-match"
      data-region="today_match"
    >
      <h3>TODAY&apos;S MATCH</h3>

      <dl className="eiq-form-today-match-list">
        {rows.map((item) => (
          <div key={item.label} className={item.value || item.evidence ? "" : "is-empty"}>
            <dt>{item.label}</dt>
            <dd>{cleanDisplay(item.value)}</dd>
            <small>{cleanDisplay(item.evidence)}</small>
          </div>
        ))}
      </dl>

      <div className="eiq-form-final-match-rating">
        <span>OVERALL MATCH</span>
        <strong>{cleanDisplay(runner.suitabilityScore)}</strong>
        <small>{cleanDisplay(runner.suitabilityLabel || classMatch?.label)}</small>
      </div>
    </aside>
  );
}
'''

tsx = replace_function(tsx, "TodayMatch", today_match)

# ============================================================
# 4. GOVERNED INSIGHTS PANEL
# ============================================================

key_insights = r'''
function KeyInsights({ runner }: { runner: FormGuideRunnerDisplay }) {
  const dossier = buildRunnerProfileDossier(runner);
  const groups = dossier.keyInsights;
  const firstItems = groups
    .flatMap((group) => group.items.map((item) => item.text))
    .filter(Boolean)
    .slice(0, 5);

  return (
    <section
      className="eiq-form-v31-insights eiq-form-v4-key-insights eiq-form-final-match-read"
      data-region="match_insights"
    >
      <h3>TODAY&apos;S MATCH INSIGHTS</h3>

      {firstItems.length ? (
        <ul>
          {firstItems.map((item) => (
            <li key={item}>
              <i aria-hidden="true" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p>
          {runner.scratched
            ? "Runner is scratched. Historical evidence remains below."
            : "No governed match insight is available for this runner."}
        </p>
      )}
    </section>
  );
}
'''

tsx = replace_function(tsx, "KeyInsights", key_insights)

# ============================================================
# 5. LOCKED RUNNER HERO COMPOSITION
# ============================================================

runner_profile = r'''
function RunnerProfile({ runner }: { runner: FormGuideRunnerDisplay }) {
  const secondaryIdentity = [
    runner.age ? `${runner.age}yo` : "",
    runner.sex,
    runner.breeding,
  ].filter(Boolean);

  const professionalIdentity = [
    runner.trainer ? `Trainer: ${runner.trainer}` : "",
    runner.jockey
      ? `Jockey: ${runner.jockey}${runner.weight ? ` (${runner.weight})` : ""}`
      : "",
  ].filter(Boolean);

  const raceIdentity = [
    secondaryIdentity.length ? secondaryIdentity.join(" | ") : "",
    runner.effectiveBarrier
      ? `Effective Barrier ${runner.effectiveBarrier}`
      : runner.barrier
        ? `Barrier ${runner.barrier}`
        : "",
  ].filter(Boolean);

  return (
    <article
      id={runnerProfileId(runner)}
      className={`eiq-form-v31-runner-sheet eiq-form-v4-runner-sheet eiq-form-final-runner-sheet ${runner.scratched ? "is-scratched" : ""}`.trim()}
      data-runner-profile="true"
      data-runner-no={runner.no}
    >
      <section
        className="eiq-form-v3-runner-header eiq-form-v31-runner-header eiq-form-v4-runner-header eiq-form-final-runner-header eiq-form-locked-runner-hero"
        data-region="runner_header"
      >
        <div className="eiq-form-runner-number">
          {cleanDisplay(runner.no)}
        </div>

        <div className="eiq-form-runner-silk-wrap">
          {runner.silkUrl ? (
            <img
              className="eiq-form-detail-silk"
              src={runner.silkUrl}
              alt={`${runner.horse} silks`}
              loading="lazy"
            />
          ) : (
            <span
              className="eiq-form-detail-silk eiq-form-silk--fallback"
              aria-hidden="true"
            />
          )}
        </div>

        <div className="eiq-form-v3-runner-identity">
          <strong>{runner.horse}</strong>

          <p className="eiq-form-runner-connections">
            {professionalIdentity.length
              ? professionalIdentity.join(" | ")
              : DASH}
          </p>

          <p className="eiq-form-runner-description">
            {raceIdentity.length ? raceIdentity.join(" | ") : DASH}
          </p>
        </div>

        <CurrentMetricStrip runner={runner} />
      </section>

      <section
        className="eiq-form-v4-dossier-grid eiq-form-approved-dossier-grid eiq-form-final-dossier-grid"
        data-region="expanded_runner"
      >
        <TodayMatch runner={runner} />

        <div
          className="eiq-form-v4-dossier-main eiq-form-final-dossier-main"
          data-region="profile_matrix_wrap"
        >
          <HorseProfileMatrix runner={runner} />
        </div>

        <KeyInsights runner={runner} />
      </section>

      <RecentForm runner={runner} />

      <div
        className="eiq-form-final-sectional-legend"
        data-region="sectional_legend"
      >
        <strong>Sectionals (Lengths):</strong>
        <span>Negative = faster than standard</span>
        <span>Positive = slower than standard</span>
      </div>
    </article>
  );
}
'''

tsx = replace_function(tsx, "RunnerProfile", runner_profile)

# ============================================================
# 6. LOCKED COMPOSITION CSS
# ============================================================

START = "/* EDGEIQ_FORM_GUIDE_LOCKED_COMPOSITION_V4_START */"
END = "/* EDGEIQ_FORM_GUIDE_LOCKED_COMPOSITION_V4_END */"

locked_css = r'''
/* EDGEIQ_FORM_GUIDE_LOCKED_COMPOSITION_V4_START */

.eiq-race-form-guide--final-locked {
  --fg-blue: #075fe4;
  --fg-navy: #07145d;
  --fg-green: #18733b;
  --fg-green-soft: #eef7f0;
  --fg-red: #aa2831;
  --fg-red-soft: #faeded;
  --fg-today-soft: #eef5ff;
  --fg-line: #d8e1ed;
  --fg-muted: #66738d;
}

/* ------------------------------------------------------------
   RUNNER HERO
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked .eiq-form-locked-runner-hero {
  display: grid !important;
  grid-template-columns:
    46px
    58px
    minmax(265px, 0.9fr)
    minmax(720px, 2fr) !important;
  align-items: center;
  gap: 10px;
  min-height: 82px;
  padding: 9px 11px !important;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-number {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 5px;
  background: var(--fg-blue);
  color: #ffffff;
  font-size: 21px;
  font-weight: 900;
  line-height: 1;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-silk-wrap {
  display: grid;
  width: 56px;
  height: 60px;
  place-items: center;
}

.eiq-race-form-guide--final-locked .eiq-form-detail-silk {
  width: 52px;
  height: 58px;
  object-fit: contain;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-runner-hero .eiq-form-v3-runner-identity strong {
  display: block;
  color: var(--fg-navy);
  font-size: 20px;
  font-weight: 900;
  line-height: 1.1;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-runner-hero .eiq-form-v3-runner-identity p {
  margin: 0;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-connections {
  margin-top: 6px !important;
  color: #202c60 !important;
  font-size: 9.5px !important;
  font-weight: 800 !important;
}

.eiq-race-form-guide--final-locked .eiq-form-runner-description {
  margin-top: 4px !important;
  color: var(--fg-muted) !important;
  font-size: 9px !important;
  font-weight: 700 !important;
}

/* ------------------------------------------------------------
   VALUE-FIRST METRIC RIBBON
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked .eiq-form-locked-metric-ribbon {
  display: grid;
  grid-template-columns: repeat(7, minmax(82px, 1fr));
  width: 100%;
  border: 1px solid #d7dfeb;
  border-radius: 5px;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon > div {
  display: flex;
  min-width: 0;
  min-height: 61px;
  padding: 7px 6px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #dce4ee;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon > div:last-child {
  border-right: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon dd {
  order: 1;
  margin: 0;
  color: var(--fg-navy);
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon dt {
  order: 2;
  margin-top: 5px;
  color: var(--fg-navy);
  font-size: 7.5px;
  font-weight: 900;
  line-height: 1.15;
  text-align: center;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon small {
  order: 3;
  min-height: 10px;
  margin-top: 3px;
  color: var(--fg-green);
  font-size: 8px;
  font-weight: 800;
  line-height: 1;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon [data-metric="edge"] dd {
  color: var(--fg-green);
}

/* ------------------------------------------------------------
   DOSSIER GRID
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
  grid-template-columns:
    minmax(190px, 0.75fr)
    minmax(790px, 3.4fr)
    minmax(220px, 0.85fr) !important;
  gap: 7px !important;
  padding: 7px 8px 5px !important;
}

/* ------------------------------------------------------------
   TODAY'S MATCH
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked .eiq-form-today-match-list {
  margin: 0;
  padding: 4px 8px;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list > div {
  display: grid;
  grid-template-columns: 55px minmax(55px, 1fr);
  grid-template-areas:
    "label value"
    "label evidence";
  min-height: 36px;
  padding: 6px 1px;
  border-bottom: 1px solid #edf1f5;
  column-gap: 7px;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list > div:last-child {
  border-bottom: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list dt {
  grid-area: label;
  color: var(--fg-navy);
  font-size: 8.5px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list dd {
  grid-area: value;
  margin: 0;
  color: var(--fg-navy);
  font-size: 8.5px;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list small {
  grid-area: evidence;
  margin-top: 2px;
  color: var(--fg-green);
  font-size: 8px;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list .is-empty dd,
.eiq-race-form-guide--final-locked
.eiq-form-today-match-list .is-empty small {
  color: #8a94a7;
}

/* ------------------------------------------------------------
   PROFILE MATRIX
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--head em {
  display: block;
  margin-bottom: 3px;
  color: var(--fg-blue);
  font-size: 6.5px;
  font-style: normal;
  font-weight: 900;
  letter-spacing: 0.04em;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--head strong {
  display: block;
  font-size: 7.5px;
  font-weight: 900;
  line-height: 1.1;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-today {
  background: var(--fg-today-soft) !important;
  box-shadow:
    inset 1px 0 0 #74a8ff,
    inset -1px 0 0 #74a8ff;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-primary {
  background: var(--fg-green-soft) !important;
  box-shadow:
    inset 1px 0 0 #78b18a,
    inset -1px 0 0 #78b18a;
  color: #155d30;
}

.eiq-race-form-guide--final-locked .eiq-form-profile-legend {
  display: flex;
  min-height: 24px;
  padding: 5px 9px;
  align-items: center;
  justify-content: center;
  gap: 22px;
  border-top: 1px solid #e4e9f0;
  color: #4e5c76;
  font-size: 7.5px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked .eiq-form-profile-legend span {
  display: flex;
  align-items: center;
  gap: 5px;
}

.eiq-race-form-guide--final-locked .eiq-form-profile-legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.eiq-race-form-guide--final-locked
.eiq-form-profile-legend i.is-today {
  border: 1px solid #74a8ff;
  background: var(--fg-today-soft);
}

.eiq-race-form-guide--final-locked
.eiq-form-profile-legend i.is-primary {
  border: 1px solid #78b18a;
  background: var(--fg-green-soft);
}

/* ------------------------------------------------------------
   INSIGHTS
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li {
  display: grid;
  grid-template-columns: 11px minmax(0, 1fr);
  gap: 6px;
  padding: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li::before {
  display: none;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li i {
  width: 9px;
  height: 9px;
  margin-top: 2px;
  border: 1px solid #68a57e;
  border-radius: 50%;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li span {
  color: var(--fg-navy);
  font-size: 8.5px;
  font-weight: 750;
  line-height: 1.35;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read > p {
  margin: 0;
  padding: 12px 10px;
  color: var(--fg-muted);
  font-size: 8.5px;
  line-height: 1.4;
}

/* ------------------------------------------------------------
   RECENT FORM
   ------------------------------------------------------------ */

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 th {
  color: var(--fg-navy) !important;
  font-weight: 900 !important;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 td {
  color: var(--fg-navy) !important;
  font-weight: 700 !important;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 .is-negative {
  background: var(--fg-green-soft);
  color: var(--fg-green) !important;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 .is-positive {
  background: var(--fg-red-soft);
  color: var(--fg-red) !important;
}

/* ------------------------------------------------------------
   RESPONSIVE
   ------------------------------------------------------------ */

@media (max-width: 1450px) {
  .eiq-race-form-guide--final-locked .eiq-form-locked-runner-hero {
    grid-template-columns: 44px 54px minmax(245px, 0.85fr) minmax(640px, 2fr) !important;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns:
      minmax(180px, 0.72fr)
      minmax(700px, 3.2fr)
      minmax(200px, 0.82fr) !important;
  }
}

@media (max-width: 1200px) {
  .eiq-race-form-guide--final-locked .eiq-form-locked-runner-hero {
    grid-template-columns: 44px 54px minmax(240px, 1fr) !important;
  }

  .eiq-race-form-guide--final-locked .eiq-form-locked-metric-ribbon {
    grid-column: 1 / -1;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-dossier-grid {
    grid-template-columns: minmax(190px, 0.8fr) minmax(680px, 3fr) !important;
  }

  .eiq-race-form-guide--final-locked .eiq-form-final-match-read {
    grid-column: 1 / -1;
  }
}

/* EDGEIQ_FORM_GUIDE_LOCKED_COMPOSITION_V4_END */
'''

if START in css and END in css:
    start_index = css.index(START)
    end_index = css.index(END) + len(END)
    css = css[:start_index] + locked_css.strip() + css[end_index:]
else:
    css = css.rstrip() + "\n\n" + locked_css.strip() + "\n"

TSX.write_text(tsx, encoding="utf-8", newline="\n")
CSS.write_text(css, encoding="utf-8", newline="\n")

print(f"UPDATED_TSX={TSX}")
print(f"UPDATED_CSS={CSS}")
print(f"CHECKPOINT_TSX={tsx_backup}")
print(f"CHECKPOINT_CSS={css_backup}")
print("FORM_GUIDE_LOCKED_COMPOSITION_V4_PATCH_PASS")
