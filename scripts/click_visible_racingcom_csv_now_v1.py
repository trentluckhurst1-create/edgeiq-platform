from pathlib import Path
import pandas as pd
import time
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
PUBLIC = ROOT / "dashboard" / "racing-dashboard" / "public" / "data"
OUTDIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_manual_visible_csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

OUT = PUBLIC / "edgeiq_vic_visible_page_csv_click_v1.csv"
DIAG = PUBLIC / "edgeiq_vic_visible_page_csv_click_diagnostics_v1.csv"

DOWNLOADS = Path.home() / "Downloads"

rows = []

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]
    pages = context.pages

    page = None
    for pg in pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                page = pg
                break
        except Exception:
            pass

    if page is None:
        raise RuntimeError("No visible Racing.com speed-data page found. Leave the visible page open.")

    print("USING PAGE:", page.url)

    before = {f.name for f in DOWNLOADS.glob("*")}

    page.bring_to_front()
    page.wait_for_timeout(1000)

    try:
        page.locator("text=Accept All Cookies").click(timeout=3000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(1000)

    html = page.content()
    (OUTDIR / "visible_page_before_click.html").write_text(html, encoding="utf-8", errors="ignore")

    candidates = page.evaluate("""
    () => {
      const out = [];
      const els = Array.from(document.querySelectorAll('a, button, span, div'));
      for (const e of els) {
        const txt = (e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim();
        const href = e.getAttribute && e.getAttribute('href');
        if (txt.toLowerCase().includes('csv') || txt.toLowerCase().includes('download race sectional data') || (href || '').toLowerCase().includes('csv')) {
          const r = e.getBoundingClientRect();
          out.push({
            tag: e.tagName,
            text: txt,
            href: href || '',
            x: r.x,
            y: r.y,
            w: r.width,
            h: r.height
          });
        }
      }
      return out;
    }
    """)

    pd.DataFrame(candidates).to_csv(PUBLIC / "edgeiq_vic_visible_page_csv_dom_candidates_v1.csv", index=False)

    print("DOM CSV CANDIDATES:")
    if candidates:
        print(pd.DataFrame(candidates).to_string(index=False))
    else:
        print("NONE")

    clicked = False
    click_method = ""

    try:
        with page.expect_download(timeout=30000) as dl:
            page.evaluate("""
            () => {
              const els = Array.from(document.querySelectorAll('a, button, span, div'));
              const csvs = els.filter(e => ((e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase() === 'csv'));
              const csv = csvs[csvs.length - 1];
              if (!csv) throw new Error('CSV exact element not found');
              csv.scrollIntoView({block: 'center'});
              csv.click();
            }
            """)
        download = dl.value
        target = OUTDIR / (download.suggested_filename or "racingcom_visible_page.csv")
        download.save_as(target)
        clicked = True
        click_method = "EXPECT_DOWNLOAD_EXACT_CSV"
    except Exception as e:
        print("EXPECT_DOWNLOAD_EXACT_CSV FAILED:", repr(e))

    if not clicked:
        try:
            page.evaluate("""
            () => {
              const els = Array.from(document.querySelectorAll('a, button, span, div'));
              const csvs = els.filter(e => ((e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase().includes('csv')));
              const csv = csvs[csvs.length - 1];
              if (!csv) throw new Error('CSV contains element not found');
              csv.scrollIntoView({block: 'center'});
              csv.click();
            }
            """)
            page.wait_for_timeout(8000)
            clicked = True
            click_method = "JS_CLICK_CONTAINS_CSV"
        except Exception as e:
            print("JS_CLICK_CONTAINS_CSV FAILED:", repr(e))

    after = [f for f in DOWNLOADS.glob("*") if f.name not in before and not f.name.endswith(".crdownload")]
    saved_file = ""

    if after:
        latest = sorted(after, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        target = OUTDIR / latest.name
        shutil.copy2(latest, target)
        saved_file = str(target)

    parsed_rows = 0
    cols = ""
    if saved_file:
        try:
            df = pd.read_csv(saved_file, low_memory=False)
            parsed_rows = len(df)
            cols = " | ".join(map(str, df.columns))
        except Exception as e:
            cols = "PARSE_FAILED: " + repr(e)

    rows.append({
        "page_url": page.url,
        "clicked": clicked,
        "click_method": click_method,
        "download_found": bool(saved_file),
        "saved_file": saved_file,
        "parsed_rows": parsed_rows,
        "columns": cols,
        "dom_candidates": len(candidates),
    })

    browser.close()

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

diag = pd.DataFrame([{
    "clicked": int(out["clicked"].sum()),
    "download_found": int(out["download_found"].sum()),
    "parsed_rows": int(out["parsed_rows"].sum()),
    "dom_candidates": int(out["dom_candidates"].sum()),
}])
diag.to_csv(DIAG, index=False)

print(out.to_string(index=False))
print("SAVED:", OUT)
print("SAVED:", DIAG)
print("DOM CANDIDATES:", PUBLIC / "edgeiq_vic_visible_page_csv_dom_candidates_v1.csv")
print("DOWNLOAD DIR:", OUTDIR)
