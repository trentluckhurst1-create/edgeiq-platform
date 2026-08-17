import { createServer } from "node:http";
import {
  closeSync,
  createReadStream,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  statSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, extname, join, resolve, sep } from "node:path";
import { spawn } from "node:child_process";

const root = resolve(process.cwd());
const port = Number(process.env.PORT || 10000);
const dataRoot = resolve(process.env.EDGEIQ_DATA_ROOT || join(root, "public", "data"));
const performanceRoot = resolve(
  process.env.EDGEIQ_PERFORMANCE_INTELLIGENCE_ROOT || join(root, "public", "performance-intelligence"),
);
const runtimeRoot = resolve(process.env.EDGEIQ_RUNTIME_ROOT || root);
const performanceDocsRoot = resolve(
  process.env.EDGEIQ_PERFORMANCE_DOCS_ROOT || join(root, "docs", "performance-intelligence"),
);
const marketDataRoot = resolve(
  process.env.EDGEIQ_MARKET_DATA_ROOT || join(root, "data", "market", "ladbrokes"),
);
const healthPath = resolve(
  process.env.EDGEIQ_HEALTH_PATH || join(dataRoot, "edgeiq_production_health_v1.json"),
);
const refreshEnabled = String(process.env.EDGEIQ_REFRESH_ENABLED || "false").toLowerCase() === "true";
const refreshOnStartup = String(process.env.EDGEIQ_REFRESH_ON_STARTUP || "false").toLowerCase() === "true";
const refreshToken = process.env.EDGEIQ_REFRESH_TOKEN || "";
const refreshLocalTime = process.env.EDGEIQ_REFRESH_LOCAL_TIME || "05:45";
const refreshTimeZone = process.env.EDGEIQ_REFRESH_TIMEZONE || "Australia/Melbourne";
const refreshLockPath = resolve(process.env.EDGEIQ_REFRESH_LOCK_PATH || join(runtimeRoot, "state", "edgeiq_refresh.lock"));
const distRoot = resolve(root, "dist");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
};

let refreshRunning = false;
let lastSchedulerDate = "";

function ensureLinked(relativePath, targetRoot) {
  const linkPath = join(root, relativePath);
  mkdirSync(targetRoot, { recursive: true });
  mkdirSync(resolve(linkPath, ".."), { recursive: true });
  if (existsSync(linkPath)) return;
  symlinkSync(targetRoot, linkPath, process.platform === "win32" ? "junction" : "dir");
}

function safePath(base, requestPath) {
  const decoded = decodeURIComponent(requestPath.split("?")[0]);
  const candidate = resolve(base, `.${decoded}`);
  return candidate === base || candidate.startsWith(base + sep) ? candidate : null;
}

function sendJson(response, statusCode, payload) {
  const body = JSON.stringify(payload, null, 2);
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  response.end(body);
}

function readHealth() {
  if (!existsSync(healthPath)) {
    return {
      EDGEIQ_PRODUCTION_HEALTH: "UNKNOWN",
      reason: "health artifact not written yet",
      healthPath,
    };
  }
  try {
    return JSON.parse(readFileSync(healthPath, "utf8"));
  } catch (error) {
    return {
      EDGEIQ_PRODUCTION_HEALTH: "FAIL",
      reason: "health artifact is unreadable",
      error: error instanceof Error ? error.message : String(error),
      healthPath,
    };
  }
}

function servicePayload() {
  return {
    status: "alive",
    refreshRunning,
    runtimeRoot,
    dataRoot,
    performanceRoot,
    performanceDocsRoot,
    marketDataRoot,
    healthPath,
    refreshLockPath,
    refreshEnabled,
    refreshOnStartup,
    refreshLocalTime,
    refreshTimeZone,
  };
}

function serveFile(response, filePath) {
  if (!filePath || !existsSync(filePath) || !statSync(filePath).isFile()) return false;
  response.writeHead(200, {
    "content-type": mimeTypes[extname(filePath).toLowerCase()] || "application/octet-stream",
    "cache-control": filePath.includes(`${sep}data${sep}`) ? "no-store" : "public, max-age=60",
  });
  createReadStream(filePath).pipe(response);
  return true;
}

function acquireRefreshLock(trigger) {
  mkdirSync(dirname(refreshLockPath), { recursive: true });
  if (existsSync(refreshLockPath)) {
    const ageMs = Date.now() - statSync(refreshLockPath).mtimeMs;
    if (ageMs > 6 * 60 * 60 * 1000) unlinkSync(refreshLockPath);
  }
  try {
    const handle = openSync(refreshLockPath, "wx");
    writeFileSync(handle, JSON.stringify({ pid: process.pid, trigger, startedAt: new Date().toISOString() }));
    closeSync(handle);
    return true;
  } catch {
    return false;
  }
}

function releaseRefreshLock() {
  try {
    if (existsSync(refreshLockPath)) unlinkSync(refreshLockPath);
  } catch {
    // The next refresh will treat an old lock as stale.
  }
}

function runRefresh(trigger) {
  if (refreshRunning) return false;
  if (!acquireRefreshLock(trigger)) return false;
  refreshRunning = true;
  const child = spawn("python", ["scripts/edgeiq_production_refresh_launcher_v1.py", "--trigger", trigger], {
    cwd: root,
    env: process.env,
    stdio: "inherit",
  });
  child.on("exit", (code) => {
    refreshRunning = false;
    releaseRefreshLock();
    if (code !== 0) console.error(`EDGEIQ refresh failed with exit code ${code}`);
  });
  return true;
}

function melbourneDateTimeParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-AU", {
    timeZone: refreshTimeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(now);
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

function schedulerTick(now = new Date()) {
  if (!refreshEnabled) return;
  const parts = melbourneDateTimeParts(now);
  const dateKey = `${parts.year}-${parts.month}-${parts.day}`;
  const timeKey = `${parts.hour}:${parts.minute}`;
  if (timeKey === refreshLocalTime && lastSchedulerDate !== dateKey) {
    lastSchedulerDate = dateKey;
    runRefresh("internal-scheduler");
  }
}

function schedulerContractSelfTest() {
  const before = lastSchedulerDate;
  const parts = melbourneDateTimeParts(new Date("2026-01-15T18:45:00Z"));
  const hasMelbourneZone = refreshTimeZone === "Australia/Melbourne";
  const minutePrecision = /^\d{2}:\d{2}$/.test(refreshLocalTime);
  refreshRunning = true;
  const concurrentBlocked = runRefresh("contract-test") === false;
  refreshRunning = false;
  lastSchedulerDate = before;
  const pass = hasMelbourneZone && minutePrecision && concurrentBlocked && Boolean(parts.year && parts.hour);
  console.log(JSON.stringify({
    SCHEDULER_CONTRACT: pass ? "PASS" : "FAIL",
    timezone: refreshTimeZone,
    refreshLocalTime,
    dstSafeTimezoneName: hasMelbourneZone,
    noConcurrentRefresh: concurrentBlocked,
    injectedClockSupported: true,
    parsedParts: parts,
  }, null, 2));
  process.exit(pass ? 0 : 1);
}

if (process.env.EDGEIQ_RENDER_SERVER_TEST_MODE === "scheduler-contract") {
  schedulerContractSelfTest();
}

ensureLinked("public/data", dataRoot);
ensureLinked("public/performance-intelligence", performanceRoot);
ensureLinked("docs/performance-intelligence", performanceDocsRoot);
ensureLinked("data/market/ladbrokes", marketDataRoot);

if (refreshOnStartup) {
  runRefresh("startup");
}

if (refreshEnabled) {
  setInterval(schedulerTick, 60_000);
  schedulerTick();
}

createServer((request, response) => {
  const url = request.url || "/";
  if (url.startsWith("/healthz")) {
    sendJson(response, 200, servicePayload());
    return;
  }
  if (url.startsWith("/readyz")) {
    const health = readHealth();
    const ok = health.EDGEIQ_PRODUCTION_HEALTH === "PASS";
    sendJson(response, ok ? 200 : 503, { ...servicePayload(), productionHealth: health.EDGEIQ_PRODUCTION_HEALTH || "UNKNOWN" });
    return;
  }
  if (url.startsWith("/api/health")) {
    const health = readHealth();
    sendJson(response, health.EDGEIQ_PRODUCTION_HEALTH === "PASS" ? 200 : 503, { ...servicePayload(), ...health });
    return;
  }
  if (url.startsWith("/api/refresh")) {
    if (request.method !== "POST") {
      sendJson(response, 405, { error: "POST required" });
      return;
    }
    if (refreshToken) {
      const provided = request.headers.authorization || "";
      if (provided !== `Bearer ${refreshToken}`) {
        sendJson(response, 401, { error: "refresh token required" });
        return;
      }
    }
    const started = runRefresh("http");
    sendJson(response, started ? 202 : 409, { status: started ? "accepted" : "already_running_or_locked", refreshRunning });
    return;
  }
  if (url.startsWith("/data/")) {
    if (!serveFile(response, safePath(dataRoot, url.slice("/data".length)))) sendJson(response, 404, { error: "not found" });
    return;
  }
  if (url.startsWith("/performance-intelligence/")) {
    const prefix = "/performance-intelligence";
    if (!serveFile(response, safePath(performanceRoot, url.slice(prefix.length)))) sendJson(response, 404, { error: "not found" });
    return;
  }
  const staticPath = safePath(distRoot, url === "/" ? "/index.html" : url);
  if (serveFile(response, staticPath)) return;
  serveFile(response, join(distRoot, "index.html"));
}).listen(port, "0.0.0.0", () => {
  console.log(`EDGEIQ_RENDER_SERVER listening on ${port}`);
  console.log(`EDGEIQ_DATA_ROOT=${dataRoot}`);
  console.log(`EDGEIQ_REFRESH_ENABLED=${refreshEnabled}`);
});
