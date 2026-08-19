from playwright.sync_api import sync_playwright
import pandas as pd
import time

def scrape_horse(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)

        # WAIT FOR TABLE TO LOAD
        page.wait_for_selector("table", timeout=10000)

        html = page.content()
        browser.close()

        return html
