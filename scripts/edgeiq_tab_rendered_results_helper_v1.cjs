
const { chromium } = require("playwright");
const fs = require("fs");

async function main() {
  const url = process.argv[2];
  const outPath = process.argv[3];

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 2200 },
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 EDGEiQ"
  });

  const payload = {
    url,
    ok: false,
    error: "",
    title: "",
    text: "",
    scripts: [],
    htmlSnippet: ""
  };

  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForTimeout(7000);

    payload.title = await page.title().catch(() => "");
    payload.text = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");

    const scripts = await page.locator("script").evaluateAll(nodes =>
      nodes.map(n => n.textContent || "").filter(t => t && t.length > 100)
    ).catch(() => []);

    payload.scripts = scripts.slice(0, 80);
    payload.htmlSnippet = (await page.content()).slice(0, 500000);
    payload.ok = true;
  } catch (e) {
    payload.error = String(e && e.stack ? e.stack : e);
  }

  fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), "utf8");
  await browser.close();
}

main().catch(e => {
  fs.writeFileSync(process.argv[3], JSON.stringify({ ok:false, error:String(e && e.stack ? e.stack : e) }, null, 2), "utf8");
  process.exit(0);
});
