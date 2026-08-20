const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = process.cwd();
const DATA = path.join(ROOT, "public", "data");

const MONTH_CODE = "RECOVERY_20260625_20260819";
const MONTH_NAME = "recovery";
const YEAR = "20260625_20260819";

const RECOVERY_DIR = path.join(ROOT, "scripts", "recovery");
const OUTPUT_DIR = path.join(ROOT, "recovery-output");

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const MANIFEST = path.join(
  RECOVERY_DIR,
  "edgeiq_manifest_RECOVERY_RETRY_6_V1.json"
);

const OUT = path.join(
  OUTPUT_DIR,
  "edgeiq_graphql_recovery_retry_6_v1_results.csv"
);

const SUMMARY = path.join(
  OUTPUT_DIR,
  "edgeiq_graphql_recovery_retry_6_v1_summary.csv"
);

const AUDIT = path.join(
  OUTPUT_DIR,
  "edgeiq_graphql_recovery_retry_6_v1_audit.csv"
);

function esc(v){ return `"${String(v ?? "").replace(/"/g,'""')}"`; }
function clean(v){ return v === null || v === undefined ? "" : String(v).trim(); }
function money(v){ const n = Number(clean(v).replace("$","").replace(",","")); return Number.isFinite(n) ? n : ""; }
function margin(v){ const n = Number(clean(v).replace("L","")); return Number.isFinite(n) ? n : ""; }
function opName(url){ const mm=url.match(/query=query%20([^%(]+)/); return mm ? decodeURIComponent(mm[1]) : ""; }

function writeCsv(file, rows, fields) {
  const lines = [fields.map(esc).join(",")];
  for (const r of rows) lines.push(fields.map(f => esc(r[f])).join(","));
  fs.writeFileSync(file, lines.join("\n"), "utf8");
}

(async () => {
  if (!fs.existsSync(MANIFEST)) {
    console.error(`[MISSING_MANIFEST] ${MANIFEST}`);
    process.exit(2);
  }

  const manifestRows = JSON.parse(fs.readFileSync(MANIFEST,"utf8").replace(/^\uFEFF/, ""));
  const meetingsMap = new Map();

  for (const r of manifestRows) {
    if (!r.meeting_date || !r.track || !r.meeting_url) continue;
    const key = `${r.meeting_date}|${r.track}|${r.meeting_url}`;
    if (!meetingsMap.has(key)) {
      meetingsMap.set(key, {
        meeting_date: r.meeting_date,
        track: r.track,
        meeting_url: r.meeting_url
      });
    }
  }

  const meetings = [...meetingsMap.values()];
  console.log(`[${MONTH_CODE}] meetings=${meetings.length}`);

  if (meetings.length === 0) {
    writeCsv(SUMMARY, [
      { metric: "status", value: `edgeiq_graphql_${MONTH_NAME}_${YEAR}_results_v1_NO_MEETINGS` },
      { metric: "month_code", value: MONTH_CODE },
      { metric: "manifest", value: MANIFEST },
      { metric: "output_rows", value: 0 },
      { metric: "built_at", value: new Date().toISOString() }
    ], ["metric","value"]);
    process.exit(0);
  }

  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage", "--no-sandbox"]
  });

  const allRows = [];
  const audit = [];

  for (const meetItem of meetings) {
    let meetingCap = null;
    let racesCap = null;
    const attemptNotes = [];

    for (let attempt = 1; attempt <= 3; attempt++) {
      const page = await browser.newPage({
        viewport: { width: 1440, height: 1200 }
      });

      const captures = [];

      page.on("response", async (response) => {
        const url = response.url();

        if (!url.includes("graphql.rmdprod.racing.com")) return;

        let body = "";

        try {
          body = await response.text();
        } catch {
          return;
        }

        captures.push({
          operation: opName(url),
          status: response.status(),
          body
        });
      });

      console.log(
        `[OPEN_ATTEMPT_${attempt}] ${meetItem.meeting_date} | ` +
        `${meetItem.track} | ${meetItem.meeting_url}`
      );

      try {
        await page.goto(
          meetItem.meeting_url,
          {
            waitUntil: "domcontentloaded",
            timeout: 90000
          }
        );

        // Allow Racing.com client-side GraphQL requests to initialise.
        await page.waitForTimeout(12000);

        meetingCap = captures.find(
          x => x.operation === "getMeeting_CD" && x.status === 200
        ) || null;

        racesCap = captures.find(
          x => x.operation === "getRacesForMeet_CD" && x.status === 200
        ) || null;

        console.log(
          `[CAPTURE_ATTEMPT_${attempt}] ` +
          `meeting=${meetingCap ? "YES" : "NO"} ` +
          `races=${racesCap ? "YES" : "NO"} ` +
          `graphql_responses=${captures.length}`
        );

        if (meetingCap && racesCap) {
          await page.close();
          break;
        }

        attemptNotes.push(
          `attempt=${attempt}:` +
          `meeting=${meetingCap ? "YES" : "NO"},` +
          `races=${racesCap ? "YES" : "NO"},` +
          `captures=${captures.length}`
        );

        // Retry from a genuinely fresh navigation state.
        if (attempt < 3) {
          try {
            await page.reload({
              waitUntil: "domcontentloaded",
              timeout: 90000
            });

            await page.waitForTimeout(5000);
          } catch {
            // Fresh page will be created by the next attempt anyway.
          }
        }

      } catch (e) {
        attemptNotes.push(
          `attempt=${attempt}:PAGE_ERROR:${String(e).slice(0,120)}`
        );

        console.error(
          `[PAGE_ATTEMPT_ERROR_${attempt}] ` +
          `${meetItem.meeting_date}|${meetItem.track}|` +
          `${String(e).slice(0,180)}`
        );
      }

      await page.close();

      if (attempt < 3) {
        await new Promise(resolve => setTimeout(resolve, 3000));
      }
    }

    if (!meetingCap || !racesCap) {
      audit.push({
        meeting_date: meetItem.meeting_date,
        track: meetItem.track,
        meeting_url: meetItem.meeting_url,
        status: "MISSING_PAYLOAD_AFTER_RETRY",
        note: attemptNotes.join(" ; ").slice(0,1000),
        races: 0,
        rows: 0
      });

      console.error(
        `[FAILED_AFTER_3_ATTEMPTS] ` +
        `${meetItem.meeting_date}|${meetItem.track}|` +
        `${attemptNotes.join(" ; ")}`
      );

      continue;
    }

    let meeting = {};
    let races = [];

    try {
      meeting = JSON.parse(meetingCap.body)?.data?.getMeeting || {};
      races = JSON.parse(racesCap.body)?.data?.getRacesForMeet || [];
    } catch (e) {
      audit.push({
        meeting_date: meetItem.meeting_date,
        track: meetItem.track,
        meeting_url: meetItem.meeting_url,
        status: "JSON_ERROR",
        note: String(e).slice(0,180),
        races: 0,
        rows: 0
      });
      continue;
    }

    let meetingRows = 0;

    for (const race of races) {
      const meet = race.meet || {};
      const entries = race.formRaceEntries || [];

      for (const e of entries) {
        if (!e) { continue; }
        allRows.push({
          race_date: clean(meeting.date || meetItem.meeting_date),
          track: clean(meeting.trackName || meeting.venue || meetItem.track),
          venue_name: clean(meeting.venueName),
          state: clean(meeting.state),
          meet_code: clean(meeting.id || e.meetCode),
          meet_url: clean(meet.meetUrl || meetItem.meeting_url),
          race_id: clean(race.id),
          race_no: clean(race.raceNumber),
          race_status: clean(race.raceStatus),
          race_name: clean(race.name),
          race_class: clean(race.rdcClass || race.class),
          distance: clean(race.distance),
          race_time_utc: clean(race.time),
          track_condition: clean(meet.trackCondition || meeting.trackCondition || race.trackCondition),
          track_rating: clean(meet.trackRating || meeting.trackRating || race.trackRating),
          rail_position: clean(meet.railPosition || meeting.railPosition),
          previous_rail_position: clean(meet.previousRailPosition || meeting.previousRailPosition),
          weather: clean(meet.weather || meeting.weather),
          rainfall: clean(meeting.rainfall),
          penetrometer: clean(meeting.penetrometer),
          has_sectionals: clean(race.hasSectionals),
          has_results: clean(race.hasResults),
          has_speed_map: clean(race.hasSpeedMap),
          runner_id: clean(e?.id),
          race_entry_number: clean(e?.raceEntryNumber),
          horse: clean(e?.horseName),
          horse_code: clean(e.horseCode),
          trainer: clean(e.trainerName),
          trainer_code: clean(e.trainerCode),
          jockey: clean(e.jockeyName),
          jockey_code: clean(e.jockeyCode),
          barrier: clean(e.barrierNumber),
          live_barrier: clean(e.liveBarrierNumber),
          weight: clean(e?.weight),
          scratched: clean(e.scratched),
          finish: clean(e?.finish),
          finish_abv: clean(e.finishAbv),
          margin: clean(e.margin),
          margin_l: margin(e.margin),
          starting_price: clean(e?.startingPrice),
          starting_price_decimal: money(e.startingPrice),
          winning_time: clean(e.winningTime),
          comment_short: clean(e.commentShort),
          comment: clean(e.comment),
          comment_stewards: clean(e.commentStewards),
          gear_changes: clean(e.gearChanges),
          source: "RACING_COM_GRAPHQL_RECOVERY_RETRY_6_V1",
          built_at: new Date().toISOString()
        });
        meetingRows++;
      }
    }

    audit.push({
      meeting_date: meetItem.meeting_date,
      track: meetItem.track,
      meeting_url: meetItem.meeting_url,
      status: "OK",
      note: "",
      races: races.length,
      rows: meetingRows
    });
  }

  await browser.close();

  const fields = Object.keys(allRows[0] || { race_date:"", track:"", horse:"" });
  writeCsv(OUT, allRows, fields);

  const summaryRows = [
    { metric: "status", value: `edgeiq_graphql_${MONTH_NAME}_${YEAR}_results_v1_BUILT` },
    { metric: "month_code", value: MONTH_CODE },
    { metric: "manifest", value: MANIFEST },
    { metric: "meetings_attempted", value: meetings.length },
    { metric: "meetings_ok", value: audit.filter(a => a.status === "OK").length },
    { metric: "meetings_failed", value: audit.filter(a => a.status !== "OK").length },
    { metric: "output_rows", value: allRows.length },
    { metric: "unique_races", value: new Set(allRows.map(r => `${r.race_date}|${r.track}|${r.race_no}`)).size },
    { metric: "unique_tracks", value: new Set(allRows.map(r => r.track)).size },
    { metric: "rows_with_horse", value: allRows.filter(r => r.horse).length },
    { metric: "rows_with_trainer", value: allRows.filter(r => r.trainer).length },
    { metric: "rows_with_jockey", value: allRows.filter(r => r.jockey).length },
    { metric: "rows_with_sp", value: allRows.filter(r => r.starting_price).length },
    { metric: "rows_with_rail", value: allRows.filter(r => r.rail_position).length },
    { metric: "output_csv", value: OUT },
    { metric: "audit_csv", value: AUDIT },
    { metric: "built_at", value: new Date().toISOString() }
  ];

  writeCsv(SUMMARY, summaryRows, ["metric","value"]);
  writeCsv(AUDIT, audit, ["meeting_date","track","meeting_url","status","note","races","rows"]);

  
const failedMeetings = audit.filter(a => a.status !== "OK");

if (allRows.length === 0) {
  console.error("[RECOVERY_FAIL] zero result rows recovered");
  process.exitCode = 10;
}

if (failedMeetings.length > 0) {
  console.error(`[RECOVERY_REVIEW] failed_meetings=${failedMeetings.length}`);
  for (const failure of failedMeetings) {
    console.error(
      `[FAILED_MEETING] ${failure.meeting_date}|${failure.track}|${failure.status}|${failure.note}`
    );
  }
  process.exitCode = 11;
}

console.log(`[edgeiq_graphql_${MONTH_NAME}_${YEAR}_results_v1] COMPLETE`);
  console.log("rows=" + allRows.length);
  console.log("summary=" + SUMMARY);
})();


