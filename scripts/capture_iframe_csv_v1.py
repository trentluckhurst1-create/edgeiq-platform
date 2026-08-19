from pathlib import Path
import pandas as pd
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()

OUTDIR = ROOT / "outputs" / "sectionals" / "raw" / "VIC" / "racingcom_iframe_csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = Path.home() / "Downloads"

with sync_playwright() as p:

    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    page = None

    for pg in context.pages:
        try:
            if "racing.com/form/" in pg.url and "speed-data" in pg.url:
                page = pg
                break
        except:
            pass

    if page is None:
        raise RuntimeError("NO SPEED DATA PAGE FOUND")

    page.bring_to_front()
    page.wait_for_timeout(3000)

    print("=" * 80)
    print("PAGE URL")
    print(page.url)

    print("=" * 80)
    print("FRAMES")

    for idx, fr in enumerate(page.frames):
        print(idx, fr.url)

    target = None

    for fr in page.frames:
        if "dxp-static.racing.com/sectionals" in fr.url:
            target = fr
            break

    if target is None:
        raise RuntimeError("SECTIONALS FRAME NOT FOUND")

    print("=" * 80)
    print("TARGET FRAME")
    print(target.url)

    before = {f.name for f in DOWNLOADS.glob("*")}

    try:
        page.locator("text=Accept All Cookies").click(timeout=3000)
        page.wait_for_timeout(1000)
    except:
        pass

    candidates = target.evaluate("""
    () => {
      const out = [];

      const els = Array.from(document.querySelectorAll('*'));

      for (const e of els) {

        const txt = (e.innerText || e.textContent || '').replace(/\\s+/g, ' ').trim();

        if (
          txt.toLowerCase().includes('csv') ||
          txt.toLowerCase().includes('download')
        ) {

          const r = e.getBoundingClientRect();

          out.push({
            tag: e.tagName,
            text: txt,
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

    df = pd.DataFrame(candidates)

    out_csv = ROOT / "dashboard" / "racing-dashboard" / "public" / "data" / "edgeiq_iframe_dom_candidates_v1.csv"

    df.to_csv(out_csv, index=False)

    print("=" * 80)
    print("CANDIDATES")
    print(df.to_string(index=False))

    clicked = False

    try:

        with page.expect_download(timeout=20000) as dl:

            target.evaluate("""
            () => {

              const els = Array.from(document.querySelectorAll('*'));

              const csv = els.find(e => {
                const txt = (e.innerText || e.textContent || '').trim().toLowerCase();
                return txt === 'csv';
              });

              if (!csv) {
                throw new Error('CSV BUTTON NOT FOUND');
              }

              csv.scrollIntoView({block:'center'});

              csv.click();
            }
            """)

        download = dl.value

        target_file = OUTDIR / (download.suggested_filename or "sectionals.csv")

        download.save_as(target_file)

        print("=" * 80)
        print("DOWNLOAD SUCCESS")
        print(target_file)

        clicked = True

    except Exception as e:

        print("=" * 80)
        print("DOWNLOAD FAILED")
        print(repr(e))

    page.wait_for_timeout(5000)

    after = [
        f for f in DOWNLOADS.glob("*")
        if f.name not in before
        and not f.name.endswith(".crdownload")
    ]

    if after:

        latest = sorted(after, key=lambda x: x.stat().st_mtime, reverse=True)[0]

        target_path = OUTDIR / latest.name

        shutil.copy2(latest, target_path)

        print("=" * 80)
        print("FOUND DOWNLOAD")
        print(target_path)

        try:

            df = pd.read_csv(target_path, low_memory=False)

            print("=" * 80)
            print("CSV PARSED")
            print("ROWS:", len(df))
            print("COLUMNS:")
            print(list(df.columns))

        except Exception as e:

            print("PARSE FAILED:", repr(e))

    browser.close()

print("=" * 80)
print("DONE")
