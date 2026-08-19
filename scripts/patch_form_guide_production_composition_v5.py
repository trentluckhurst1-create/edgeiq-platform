from pathlib import Path
from datetime import datetime
import re
import shutil

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")
TSX = ROOT / "src" / "edgeiq-os" / "race" / "components" / "RaceFormGuideWorkspace.tsx"
CSS = ROOT / "src" / "edgeiq-os" / "styles" / "edgeiqOsV2.css"

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

tsx_backup = TSX.with_name(
    f"{TSX.stem}_CHECKPOINT_BEFORE_PRODUCTION_COMPOSITION_V5_{stamp}{TSX.suffix}"
)
css_backup = CSS.with_name(
    f"{CSS.stem}_CHECKPOINT_BEFORE_PRODUCTION_COMPOSITION_V5_{stamp}{CSS.suffix}"
)

shutil.copy2(TSX, tsx_backup)
shutil.copy2(CSS, css_backup)

tsx = TSX.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

# ============================================================
# SAFE FUNCTION REPLACEMENT
# Stops at either "function" or "export function".
# ============================================================

def replace_function(source: str, name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"^function {re.escape(name)}\b[\s\S]*?(?=^(?:export\s+)?function |\Z)",
        re.MULTILINE,
    )

    match = pattern.search(source)

    if not match:
        raise SystemExit(
            f"PATCH_ABORTED: function {name} was not found."
        )

    return (
        source[:match.start()]
        + replacement.rstrip()
        + "\n\n"
        + source[match.end():]
    )


# ============================================================
# DEDICATED RUNNER HERO
# ============================================================

runner_hero = r'''
function RunnerHeroHeader({ runner }: { runner: FormGuideRunnerDisplay }) {
  const horseDescription = [
    runner.age ? `${runner.age}yo` : "",
    runner.sex,
    runner.breeding,
  ].filter(Boolean);

  const connections = [
    runner.trainer ? `Trainer: ${runner.trainer}` : "",
    runner.jockey
      ? `Jockey: ${runner.jockey}${runner.weight ? ` (${runner.weight})` : ""}`
      : "",
  ].filter(Boolean);

  const raceDetails = [
    horseDescription.length ? horseDescription.join(" | ") : "",
    runner.effectiveBarrier
      ? `Effective Barrier ${runner.effectiveBarrier}`
      : runner.barrier
        ? `Barrier ${runner.barrier}`
        : "",
  ].filter(Boolean);

  return (
    <header
      className="eiq-form-production-runner-hero"
      data-region="runner_hero_header"
    >
      <div className="eiq-form-production-runner-number">
        {cleanDisplay(runner.no)}
      </div>

      <div className="eiq-form-production-silk">
        {runner.silkUrl ? (
          <img
            src={runner.silkUrl}
            alt={`${runner.horse} silks`}
            loading="lazy"
          />
        ) : (
          <span
            className="eiq-form-production-silk-placeholder"
            aria-label="Silks unavailable"
          />
        )}
      </div>

      <div className="eiq-form-production-identity">
        <h3>{cleanDisplay(runner.horse)}</h3>

        <p className="eiq-form-production-connections">
          {connections.length ? connections.join(" | ") : DASH}
        </p>

        <p className="eiq-form-production-description">
          {raceDetails.length ? raceDetails.join(" | ") : DASH}
        </p>

        {runner.scratched ? (
          <strong className="eiq-form-production-scratched">
            SCRATCHED
          </strong>
        ) : null}
      </div>

      <CurrentMetricStrip runner={runner} />
    </header>
  );
}
'''

# Insert immediately before RunnerProfile once.
if "function RunnerHeroHeader(" not in tsx:
    marker = "function RunnerProfile("
    position = tsx.find(marker)

    if position < 0:
        raise SystemExit(
            "PATCH_ABORTED: RunnerProfile insertion point was not found."
        )

    tsx = tsx[:position] + runner_hero.strip() + "\n\n" + tsx[position:]


# ============================================================
# DEDICATED INTELLIGENCE GRID
# ============================================================

intelligence_grid = r'''
function RunnerIntelligenceGrid({ runner }: { runner: FormGuideRunnerDisplay }) {
  return (
    <section
      className="eiq-form-production-intelligence-grid"
      data-region="runner_intelligence_grid"
    >
      <TodayMatch runner={runner} />

      <div
        className="eiq-form-production-profile"
        data-region="profile_matrix_wrap"
      >
        <HorseProfileMatrix runner={runner} />
      </div>

      <KeyInsights runner={runner} />
    </section>
  );
}
'''

if "function RunnerIntelligenceGrid(" not in tsx:
    marker = "function RunnerProfile("
    position = tsx.find(marker)

    if position < 0:
        raise SystemExit(
            "PATCH_ABORTED: RunnerProfile insertion point was not found."
        )

    tsx = tsx[:position] + intelligence_grid.strip() + "\n\n" + tsx[position:]


# ============================================================
# PRODUCTION RUNNER CARD
# ============================================================

runner_profile = r'''
function RunnerProfile({ runner }: { runner: FormGuideRunnerDisplay }) {
  return (
    <article
      id={runnerProfileId(runner)}
      className={`eiq-form-production-runner-card ${runner.scratched ? "is-scratched" : ""}`.trim()}
      data-runner-profile="true"
      data-runner-no={runner.no}
    >
      <RunnerHeroHeader runner={runner} />

      <RunnerIntelligenceGrid runner={runner} />

      <RecentForm runner={runner} />

      <footer
        className="eiq-form-production-sectional-legend"
        data-region="sectional_legend"
      >
        <strong>Sectionals (Lengths):</strong>
        <span>Negative = faster than standard</span>
        <span>Positive = slower than standard</span>
      </footer>
    </article>
  );
}
'''

tsx = replace_function(tsx, "RunnerProfile", runner_profile)


# ============================================================
# PRODUCTION COMPOSITION CSS
# ============================================================

START = "/* EDGEIQ_FORM_GUIDE_PRODUCTION_COMPOSITION_V5_START */"
END = "/* EDGEIQ_FORM_GUIDE_PRODUCTION_COMPOSITION_V5_END */"

production_css = r'''
/* EDGEIQ_FORM_GUIDE_PRODUCTION_COMPOSITION_V5_START */

.eiq-race-form-guide--final-locked {
  --fg-primary: #075fe4;
  --fg-primary-soft: #edf4ff;
  --fg-navy: #07145d;
  --fg-text: #18234d;
  --fg-muted: #67728a;
  --fg-border: #d7e0eb;
  --fg-positive: #176d37;
  --fg-positive-soft: #edf7ef;
  --fg-negative: #a62b33;
  --fg-negative-soft: #faeded;
}

/* ============================================================
   RUNNER CARD
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-runner-card {
  width: 100%;
  margin: 0;
  border: 1px solid #76a8ff;
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-runner-card.is-scratched {
  opacity: 0.6;
}

/* ============================================================
   RUNNER HERO
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-runner-hero {
  display: grid;
  grid-template-columns:
    44px
    56px
    minmax(275px, 0.85fr)
    minmax(690px, 2.15fr);
  align-items: center;
  gap: 10px;
  min-height: 80px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--fg-border);
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-runner-number {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 5px;
  background: var(--fg-primary);
  color: #ffffff;
  font-size: 21px;
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk {
  display: grid;
  width: 54px;
  height: 60px;
  place-items: center;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk img {
  display: block;
  width: 50px;
  height: 58px;
  object-fit: contain;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk-placeholder {
  position: relative;
  display: block;
  width: 32px;
  height: 45px;
  border: 1px solid #cbd6e2;
  border-radius: 9px 9px 5px 5px;
  background: #f7f9fc;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk-placeholder::before,
.eiq-race-form-guide--final-locked
.eiq-form-production-silk-placeholder::after {
  position: absolute;
  top: 7px;
  width: 11px;
  height: 18px;
  border: 1px solid #cbd6e2;
  background: #f7f9fc;
  content: "";
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk-placeholder::before {
  left: -8px;
  transform: rotate(20deg);
}

.eiq-race-form-guide--final-locked
.eiq-form-production-silk-placeholder::after {
  right: -8px;
  transform: rotate(-20deg);
}

.eiq-race-form-guide--final-locked
.eiq-form-production-identity {
  min-width: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-identity h3 {
  margin: 0;
  color: var(--fg-navy);
  font-size: 20px;
  font-weight: 900;
  line-height: 1.08;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-connections {
  margin: 6px 0 0;
  color: var(--fg-navy);
  font-size: 9.5px;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-description {
  margin: 4px 0 0;
  color: var(--fg-muted);
  font-size: 8.8px;
  font-weight: 700;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-scratched {
  display: inline-block;
  margin-top: 5px;
  color: var(--fg-negative);
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 0.06em;
}

/* ============================================================
   METRIC RIBBON
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon {
  display: grid;
  grid-template-columns: repeat(7, minmax(82px, 1fr));
  width: 100%;
  border: 1px solid var(--fg-border);
  border-radius: 5px;
  background: #ffffff;
  overflow: hidden;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon > div {
  display: flex;
  min-width: 0;
  min-height: 58px;
  padding: 6px 5px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--fg-border);
  text-align: center;
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
  font-size: 7.2px;
  font-weight: 900;
  line-height: 1.15;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon small {
  order: 3;
  min-height: 9px;
  margin-top: 3px;
  color: var(--fg-positive);
  font-size: 7.8px;
  font-weight: 800;
}

.eiq-race-form-guide--final-locked
.eiq-form-locked-metric-ribbon .is-empty {
  background: #fbfcfe;
}

/* ============================================================
   THREE-COLUMN INTELLIGENCE GRID
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid {
  display: grid;
  grid-template-columns:
    minmax(195px, 0.72fr)
    minmax(790px, 3.45fr)
    minmax(215px, 0.83fr);
  align-items: stretch;
  gap: 7px;
  padding: 7px 8px 5px;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-final-today-match,
.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-production-profile,
.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-final-match-read {
  min-width: 0;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--fg-border);
  border-radius: 5px;
  background: #ffffff;
  overflow: hidden;
}

/* ============================================================
   PANEL HEADERS
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-final-today-match h3,
.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-final-profile-matrix header,
.eiq-race-form-guide--final-locked
.eiq-form-production-intelligence-grid
.eiq-form-final-match-read h3 {
  display: flex;
  align-items: center;
  min-height: 31px;
  margin: 0;
  padding: 7px 9px;
  border-bottom: 1px solid var(--fg-border);
  background: #ffffff;
  color: var(--fg-navy);
  font-size: 8.8px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

/* ============================================================
   TODAY'S MATCH
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list {
  padding: 3px 8px;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list > div {
  grid-template-columns: 55px minmax(60px, 1fr);
  min-height: 33px;
  padding: 5px 1px;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list dt,
.eiq-race-form-guide--final-locked
.eiq-form-today-match-list dd {
  font-size: 8px;
}

.eiq-race-form-guide--final-locked
.eiq-form-today-match-list small {
  font-size: 7.5px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-rating {
  margin: 5px 8px 8px;
  padding: 7px 8px;
  background: #ffffff;
}

/* ============================================================
   PROFILE MATRIX
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-profile,
.eiq-race-form-guide--final-locked
.eiq-form-production-profile
.eiq-form-final-profile-matrix {
  height: auto;
  min-height: 0;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell {
  min-height: 31px;
  padding: 4px 4px;
  font-size: 8px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--head {
  min-height: 41px;
  font-size: 7.2px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell--rowhead {
  background: #f2efe7;
  color: var(--fg-navy);
  font-weight: 900;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-today {
  background: var(--fg-primary-soft);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-profile-cell.is-primary {
  background: var(--fg-positive-soft);
}

.eiq-race-form-guide--final-locked
.eiq-form-profile-legend {
  min-height: 21px;
  padding: 4px 7px;
  font-size: 7px;
}

/* ============================================================
   INSIGHTS
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read ul {
  gap: 7px;
  padding: 9px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-match-read li span {
  font-size: 8px;
  line-height: 1.35;
}

/* ============================================================
   RECENT FORM
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form {
  margin: 0 8px 4px;
  border: 0;
  border-top: 1px solid var(--fg-border);
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form header {
  min-height: 28px;
  padding: 6px 0 4px;
  border: 0;
  background: #ffffff;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 th {
  height: 27px;
  padding: 4px 5px;
  font-size: 7.4px;
}

.eiq-race-form-guide--final-locked
.eiq-form-run-table--v4 td {
  height: 27px;
  padding: 4px 5px;
  font-size: 8px;
}

.eiq-race-form-guide--final-locked
.eiq-form-final-recent-form .eiq-form-empty {
  min-height: 46px;
  padding: 15px;
  font-size: 9px;
}

/* ============================================================
   SECTIONAL LEGEND
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-production-sectional-legend {
  display: flex;
  min-height: 23px;
  margin: 0 8px 6px;
  padding: 4px 1px;
  align-items: center;
  gap: 16px;
  color: #505b73;
  font-size: 7.4px;
  font-weight: 700;
}

/* ============================================================
   ALL-RUNNER SPACING
   ============================================================ */

.eiq-race-form-guide--final-locked
.eiq-form-all-runner-dossiers__list {
  gap: 12px;
}

/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 1400px) {
  .eiq-race-form-guide--final-locked
  .eiq-form-production-runner-hero {
    grid-template-columns:
      42px
      52px
      minmax(245px, 0.85fr)
      minmax(620px, 2fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-production-intelligence-grid {
    grid-template-columns:
      minmax(180px, 0.7fr)
      minmax(700px, 3.3fr)
      minmax(195px, 0.8fr);
  }
}

@media (max-width: 1180px) {
  .eiq-race-form-guide--final-locked
  .eiq-form-production-runner-hero {
    grid-template-columns: 42px 52px minmax(250px, 1fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-locked-metric-ribbon {
    grid-column: 1 / -1;
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-production-intelligence-grid {
    grid-template-columns:
      minmax(180px, 0.75fr)
      minmax(680px, 3.2fr);
  }

  .eiq-race-form-guide--final-locked
  .eiq-form-final-match-read {
    grid-column: 1 / -1;
  }
}

/* EDGEIQ_FORM_GUIDE_PRODUCTION_COMPOSITION_V5_END */
'''

if START in css and END in css:
    start = css.index(START)
    end = css.index(END) + len(END)
    css = css[:start] + production_css.strip() + css[end:]
else:
    css = css.rstrip() + "\n\n" + production_css.strip() + "\n"

TSX.write_text(tsx, encoding="utf-8", newline="\n")
CSS.write_text(css, encoding="utf-8", newline="\n")

print(f"UPDATED_TSX={TSX}")
print(f"UPDATED_CSS={CSS}")
print(f"CHECKPOINT_TSX={tsx_backup}")
print(f"CHECKPOINT_CSS={css_backup}")
print("FORM_GUIDE_PRODUCTION_COMPOSITION_V5_PATCH_PASS")
