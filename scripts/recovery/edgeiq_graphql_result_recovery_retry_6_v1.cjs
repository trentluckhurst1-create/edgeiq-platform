const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = process.cwd();
const RECOVERY_DIR = path.join(ROOT, "scripts", "recovery");
const OUTPUT_DIR = path.join(ROOT, "recovery-output");
const MANIFEST = path.join(RECOVERY_DIR, "edgeiq_manifest_RECOVERY_RETRY_6_V1.json");
const OUT = path.join(OUTPUT_DIR, "edgeiq_graphql_recovery_retry_6_v1_results.csv");
const AUDIT = path.join(OUTPUT_DIR, "edgeiq_graphql_recovery_retry_6_v1_audit.csv");
const SUMMARY = path.join(OUTPUT_DIR, "edgeiq_graphql_recovery_retry_6_v1_summary.csv");
const MACHINE = path.join(OUTPUT_DIR, "edgeiq_graphql_recovery_retry_6_v1_machine_summary.env");
const DATE_DISCOVERY_SEED_SLUGS = [
  "flemington",
  "moe",
  "ballarat",
  "sportsbet-ballarat-synthetic",
  "bet365-hamilton",
  "casterton",
  "southside-pakenham-synthetic",
];

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function clean(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}

function esc(value) {
  return `"${clean(value).replace(/"/g, '""')}"`;
}

function writeCsv(file, rows, fields) {
  const lines = [fields.map(esc).join(",")];
  for (const row of rows) lines.push(fields.map(field => esc(row[field])).join(","));
  fs.writeFileSync(file, lines.join("\n"), "utf8");
}

function normaliseTrack(value) {
  return clean(value)
    .normalize("NFKD")
    .toUpperCase()
    .replace(/\b(BET365|SPORTSBET|BETDELUXE|LADBROKES|SOUTHSIDE)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .replace(/\b(RACECOURSE|RACING|CLUB)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function slugify(value) {
  return normaliseTrack(value).toLowerCase().replace(/\s+/g, "-");
}

function candidateUrls(meeting) {
  const urls = [];
  const add = url => {
    if (url && !urls.includes(url)) urls.push(url);
  };
  add(clean(meeting.meeting_url));

  try {
    const parsed = new URL(meeting.meeting_url);
    const parts = parsed.pathname.split("/").filter(Boolean);
    const slug = parts[2] || "";
    const date = meeting.meeting_date;
    const stripped = slug.replace(/^(bet365|sportsbet|betdeluxe|ladbrokes|southside)-/i, "");
    add(`https://www.racing.com/form/${date}/${stripped}`);
    add(`https://www.racing.com/form/${date}/${slugify(meeting.track)}`);
  } catch (_e) {
    add(`https://www.racing.com/form/${meeting.meeting_date}/${slugify(meeting.track)}`);
  }

  return urls;
}

function opName(url) {
  try {
    const parsed = new URL(url);
    const explicit = parsed.searchParams.get("operationName");
    if (explicit) return explicit;
    const decoded = decodeURIComponent(url);
    const match = decoded.match(/\b(?:query|mutation)\s+([A-Za-z0-9_]+)/);
    return match ? match[1] : "";
  } catch (_e) {
    return "";
  }
}

function collectRaceArrays(node, out = []) {
  if (!node || typeof node !== "object") return out;
  if (Array.isArray(node)) {
    if (node.some(item => item && typeof item === "object" && Object.prototype.hasOwnProperty.call(item, "raceNumber"))) {
      out.push(node);
    }
    for (const item of node) collectRaceArrays(item, out);
    return out;
  }
  for (const value of Object.values(node)) collectRaceArrays(value, out);
  return out;
}

function chooseRaceArray(payloads) {
  const arrays = [];
  for (const payload of payloads) collectRaceArrays(payload.json, arrays);
  arrays.sort((a, b) => {
    const aEntries = a.reduce((n, race) => n + (Array.isArray(race.formRaceEntries) ? race.formRaceEntries.length : 0), 0);
    const bEntries = b.reduce((n, race) => n + (Array.isArray(race.formRaceEntries) ? race.formRaceEntries.length : 0), 0);
    return bEntries - aEntries || b.length - a.length;
  });
  return arrays[0] || [];
}

function meetingLists(payloads) {
  const out = [];
  for (const payload of payloads) {
    const rows = payload.json?.data?.GetRaceMeetingsByStateNew;
    if (Array.isArray(rows)) out.push(...rows);
  }
  return out;
}

function firstMeeting(payloads) {
  for (const payload of payloads) {
    const data = payload.json && payload.json.data;
    const candidates = [
      data && data.getMeeting,
      data && Array.isArray(data.GetMeetingByVenueDateTrial) && data.GetMeetingByVenueDateTrial[0],
      data && Array.isArray(data.GetMeetingByVenue) && data.GetMeetingByVenue[0],
    ].filter(Boolean);
    if (candidates.length) return candidates[0];
  }
  return {};
}

function money(value) {
  const n = Number(clean(value).replace("$", "").replace(",", ""));
  return Number.isFinite(n) ? n : "";
}

function margin(value) {
  const n = Number(clean(value).replace("L", ""));
  return Number.isFinite(n) ? n : "";
}

function fingerprint(rows) {
  return rows
    .slice()
    .sort((a, b) => Number(a.finish || 999) - Number(b.finish || 999) || clean(a.horse).localeCompare(clean(b.horse)))
    .map(row => [row.finish, row.horse_code || row.horse, row.barrier, row.trainer, row.jockey, row.weight, row.margin, row.starting_price].map(clean).join("|"))
    .join("\n");
}

function validateRaceFingerprints(rows) {
  const byMeeting = new Map();
  for (const row of rows) {
    const key = `${row.race_date}|${normaliseTrack(row.track)}`;
    if (!byMeeting.has(key)) byMeeting.set(key, new Map());
    const races = byMeeting.get(key);
    if (!races.has(row.race_no)) races.set(row.race_no, []);
    races.get(row.race_no).push(row);
  }
  const failures = [];
  for (const [meeting, races] of byMeeting) {
    const byFp = new Map();
    for (const [raceNo, raceRows] of races) {
      const fp = fingerprint(raceRows);
      if (!fp) continue;
      if (!byFp.has(fp)) byFp.set(fp, []);
      byFp.get(fp).push(raceNo);
    }
    for (const raceNos of byFp.values()) {
      if (new Set(raceNos).size > 1) failures.push(`${meeting}|RACES=${[...new Set(raceNos)].join(",")}`);
    }
  }
  return failures;
}

async function captureMeeting(browser, meeting, url) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
  const page = await context.newPage();
  const payloads = [];
  const emptyMeetingLookups = [];

  page.on("response", async response => {
    const url = response.url();
    if (!url.includes("graphql.rmdprod.racing.com")) return;
    let body = "";
    try {
      body = await response.text();
    } catch (_e) {
      return;
    }
    let json = null;
    try {
      json = JSON.parse(body);
    } catch (_e) {
      return;
    }
    const operation = opName(url);
    if (operation === "GetMeetingByVenueDateTrial" && Array.isArray(json?.data?.GetMeetingByVenueDateTrial) && json.data.GetMeetingByVenueDateTrial.length === 0) {
      emptyMeetingLookups.push({ operation, status: response.status(), url: url.slice(0, 500) });
    }
    payloads.push({ operation, status: response.status(), json });
  });

  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
    try { await page.waitForLoadState("networkidle", { timeout: 10000 }); } catch (_e) {}
    await page.waitForTimeout(7000);
  } finally {
    await context.close().catch(() => {});
  }

  const meetingPayload = firstMeeting(payloads);
  const races = chooseRaceArray(payloads);
  return { url, meetingPayload, races, payloads, emptyMeetingLookups };
}

function meetingMatches(requested, actual, races) {
  const date = clean(actual.date) || clean(races[0]?.meet?.date);
  const venue = clean(actual.trackName || actual.venue || actual.venueName || races[0]?.meet?.venue);
  const requestedTrack = normaliseTrack(requested.track);
  const actualTrack = normaliseTrack(venue);
  return {
    ok: date === requested.meeting_date && requestedTrack === actualTrack,
    date,
    venue,
    requestedTrack,
    actualTrack,
  };
}

function rowsFromRaces(requested, meetingPayload, races, sourceUrl) {
  const rows = [];
  for (const race of races) {
    if (String(race.isTrial) === "1" || String(race.isJumpOut) === "1") {
      throw new Error(`Trial/jumpout race leaked into official recovery: race_id=${race.id}`);
    }
    const entries = Array.isArray(race.formRaceEntries) ? race.formRaceEntries : [];
    const meet = race.meet || {};
    for (const entry of entries) {
      rows.push({
        race_date: clean(meetingPayload.date || requested.meeting_date),
        track: clean(meetingPayload.trackName || meetingPayload.venue || meet.venue || requested.track),
        venue_name: clean(meetingPayload.venueName),
        state: clean(meetingPayload.state),
        meet_code: clean(meetingPayload.id || entry.meetCode || race.meetCode),
        meet_url: clean(meetingPayload.meetUrl || meet.meetUrl || sourceUrl),
        race_id: clean(race.id),
        race_no: clean(race.raceNumber),
        race_status: clean(race.raceStatus),
        race_name: clean(race.name),
        race_class: clean(race.rdcClass || race.class || race.nameForm),
        distance: clean(race.distance),
        race_time_utc: clean(race.time),
        track_condition: clean(meet.trackCondition || meetingPayload.trackCondition || race.trackCondition),
        track_rating: clean(meet.trackRating || meetingPayload.trackRating || race.trackRating),
        rail_position: clean(meet.railPosition || meetingPayload.railPosition),
        previous_rail_position: clean(meet.previousRailPosition || meetingPayload.previousRailPosition),
        weather: clean(meet.weather || meetingPayload.weather),
        rainfall: clean(meetingPayload.rainfall),
        penetrometer: clean(meetingPayload.penetrometer),
        has_sectionals: clean(race.hasSectionals),
        has_results: clean(race.hasResults),
        has_speed_map: clean(race.hasSpeedMap),
        runner_id: clean(entry.id),
        race_entry_number: clean(entry.raceEntryNumber),
        horse: clean(entry.horseName),
        horse_code: clean(entry.horseCode),
        trainer: clean(entry.trainerName),
        trainer_code: clean(entry.trainerCode),
        jockey: clean(entry.jockeyName),
        jockey_code: clean(entry.jockeyCode),
        barrier: clean(entry.barrierNumber),
        live_barrier: clean(entry.liveBarrierNumber),
        weight: clean(entry.weight),
        scratched: clean(entry.scratched),
        finish: clean(entry.finish),
        finish_abv: clean(entry.finishAbv),
        margin: clean(entry.margin),
        margin_l: margin(entry.margin),
        starting_price: clean(entry.startingPrice),
        starting_price_decimal: money(entry.startingPrice),
        winning_time: clean(entry.winningTime),
        comment_short: clean(entry.commentShort),
        comment: clean(entry.comment),
        comment_stewards: clean(entry.commentStewards),
        gear_changes: clean(entry.gearChanges),
        source: "RACING_COM_GRAPHQL_RECOVERY_RETRY_6_V2",
        built_at: new Date().toISOString(),
      });
    }
  }
  return rows;
}

async function recoverMeeting(browser, meeting) {
  const notes = [];
  for (const url of candidateUrls(meeting)) {
    const capture = await captureMeeting(browser, meeting, url);
    const match = meetingMatches(meeting, capture.meetingPayload, capture.races);
    const racesWithEntries = capture.races.filter(race => Array.isArray(race.formRaceEntries) && race.formRaceEntries.length);
    notes.push(`url=${url};payloads=${capture.payloads.length};empty_meeting_lookups=${capture.emptyMeetingLookups.length};races=${capture.races.length};races_with_entries=${racesWithEntries.length};venue=${match.venue};date=${match.date}`);
    if (!match.ok) continue;
    if (capture.meetingPayload.isTrial === true || capture.meetingPayload.isJumpOut === true) {
      return { status: "TRIAL_JUMPOUT_REJECTED", rows: [], races: 0, note: notes.join(" || ") };
    }
    if (!racesWithEntries.length) continue;
    const rows = rowsFromRaces(meeting, capture.meetingPayload, capture.races, url);
    const fingerprintFailures = validateRaceFingerprints(rows);
    if (fingerprintFailures.length) {
      return { status: "CROSS_RACE_FINGERPRINT_FAILURE", rows: [], races: capture.races.length, note: fingerprintFailures.join(";") };
    }
    return { status: "OK", rows, races: capture.races.length, note: notes.join(" || ") };
  }

  const discovery = await discoverMeetingFromDateList(browser, meeting);
  notes.push(discovery.note);

  if (discovery.matchedUrl) {
    const capture = await captureMeeting(browser, meeting, discovery.matchedUrl);
    const match = meetingMatches(meeting, capture.meetingPayload, capture.races);
    const racesWithEntries = capture.races.filter(race => Array.isArray(race.formRaceEntries) && race.formRaceEntries.length);
    notes.push(`date_list_matched_url=${discovery.matchedUrl};races=${capture.races.length};races_with_entries=${racesWithEntries.length};venue=${match.venue};date=${match.date}`);
    if (match.ok && racesWithEntries.length) {
      const rows = rowsFromRaces(meeting, capture.meetingPayload, capture.races, discovery.matchedUrl);
      const fingerprintFailures = validateRaceFingerprints(rows);
      if (fingerprintFailures.length) {
        return { status: "CROSS_RACE_FINGERPRINT_FAILURE", rows: [], races: capture.races.length, note: fingerprintFailures.join(";") };
      }
      return { status: "OK", rows, races: capture.races.length, note: notes.join(" || ") };
    }
  }

  if (discovery.dateListFound) {
    return { status: "NO_MATCHING_MEETING_IN_DATE_LIST", rows: [], races: 0, note: notes.join(" || ") };
  }

  return { status: "MEETING_UNRESOLVED", rows: [], races: 0, note: notes.join(" || ") };
}

async function discoverMeetingFromDateList(browser, meeting) {
  const tried = [];
  const discovered = [];

  for (const slug of DATE_DISCOVERY_SEED_SLUGS) {
    const url = `https://www.racing.com/form/${meeting.meeting_date}/${slug}`;
    if (tried.includes(url)) continue;
    tried.push(url);
    const capture = await captureMeeting(browser, meeting, url);
    const list = meetingLists(capture.payloads).filter(item => clean(item.date) === meeting.meeting_date);
    if (!list.length) continue;
    discovered.push(...list);
    const match = list.find(item => normaliseTrack(item.venue) === normaliseTrack(meeting.track) && item.isTrial !== true && item.isJumpOut !== true);
    if (match && match.meetUrl) {
      return {
        dateListFound: true,
        matchedUrl: match.meetUrl,
        note: `date_list_seed=${url};meetings=${list.map(item => clean(item.venue)).join("|")};matched=${match.meetUrl}`,
      };
    }
    break;
  }

  return {
    dateListFound: discovered.length > 0,
    matchedUrl: "",
    note: discovered.length
      ? `date_list_meetings=${[...new Set(discovered.map(item => clean(item.venue)))].join("|")}`
      : `date_list_unavailable;tried=${tried.join("|")}`,
  };
}

async function main() {
  const manifestRows = JSON.parse(fs.readFileSync(MANIFEST, "utf8").replace(/^\uFEFF/, ""));
  const browser = await chromium.launch({ headless: true, args: ["--disable-dev-shm-usage", "--no-sandbox"] });
  const allRows = [];
  const audit = [];

  try {
    for (const meeting of manifestRows) {
      console.log(`[RECOVERY] ${meeting.meeting_date}|${meeting.track}`);
      const result = await recoverMeeting(browser, meeting);
      allRows.push(...result.rows);
      audit.push({
        meeting_date: meeting.meeting_date,
        track: meeting.track,
        meeting_url: meeting.meeting_url,
        status: result.status,
        note: result.note.slice(0, 4000),
        races: result.races,
        rows: result.rows.length,
      });
      console.log(`[RECOVERY_STATUS] ${meeting.meeting_date}|${meeting.track}|${result.status}|rows=${result.rows.length}|races=${result.races}`);
    }
  } finally {
    await browser.close().catch(() => {});
  }

  const fields = Object.keys(allRows[0] || { race_date: "", track: "", horse: "" });
  writeCsv(OUT, allRows, fields);
  writeCsv(AUDIT, audit, ["meeting_date", "track", "meeting_url", "status", "note", "races", "rows"]);

  const failed = audit.filter(row => row.status !== "OK");
  const raceKeys = new Set(allRows.map(row => `${row.race_date}|${normaliseTrack(row.track)}|${row.race_no}`));
  const fingerprintFailures = validateRaceFingerprints(allRows);
  const trialLeakage = allRows.filter(row => /trial|jumpout/i.test(`${row.track} ${row.race_name} ${row.meet_url}`)).length;
  const governanceStatus = failed.length === 0 && fingerprintFailures.length === 0 && trialLeakage === 0 ? "PASS" : allRows.length ? "PARTIAL" : "FAIL";

  const summaryRows = [
    ["REQUESTED_MEETINGS", manifestRows.length],
    ["RECOVERED_MEETINGS", audit.filter(row => row.status === "OK").length],
    ["FAILED_MEETINGS", failed.length],
    ["RUNNER_ROWS", allRows.length],
    ["UNIQUE_RACES", raceKeys.size],
    ["RACE_IDENTITY_FAILURES", audit.filter(row => /IDENTITY/.test(row.status)).length],
    ["CROSS_RACE_FINGERPRINT_FAILURES", fingerprintFailures.length],
    ["TRIAL_JUMPOUT_LEAKAGE", trialLeakage],
    ["GOVERNANCE_STATUS", governanceStatus],
  ];
  writeCsv(SUMMARY, summaryRows.map(([metric, value]) => ({ metric, value })), ["metric", "value"]);
  fs.writeFileSync(MACHINE, summaryRows.map(([metric, value]) => `${metric}=${value}`).join("\n") + "\n", "utf8");
  console.log(fs.readFileSync(MACHINE, "utf8"));

  if (governanceStatus === "FAIL") process.exitCode = 10;
  if (governanceStatus === "PARTIAL") process.exitCode = 11;
}

if (require.main === module) {
  main().catch(error => {
    fs.writeFileSync(MACHINE, `GOVERNANCE_STATUS=FAIL\nERROR=${clean(error.message || error)}\n`, "utf8");
    console.error(error);
    process.exitCode = 12;
  });
}

module.exports = {
  normaliseTrack,
  candidateUrls,
  collectRaceArrays,
  validateRaceFingerprints,
  meetingMatches,
  meetingLists,
};
