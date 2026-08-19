from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "build_edgeiq_racingcom_three_day_race_list_v1.py"
CHECKPOINT = ROOT / "scripts" / "build_edgeiq_racingcom_three_day_race_list_v1_CHECKPOINT_PRE_FULL_RACEFORM_ENTRIES_20260723.py"

text = TARGET.read_text(encoding="utf-8")
if not CHECKPOINT.exists():
    CHECKPOINT.write_text(text, encoding="utf-8")

start = text.index("def fetch_races_browser(meetings):")
end = text.index("\ndef write_csv(path, rows, fields):", start)
new_func = """def fetch_races_browser(meetings):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(f\"PLAYWRIGHT_NOT_AVAILABLE: {e}\")

    rows = []
    built_at = datetime.now(timezone.utc).isoformat(timespec=\"seconds\")

    def merge_race(base_race, detailed_race):
        if not isinstance(detailed_race, dict):
            return base_race
        merged = dict(base_race)
        for key in [
            \"id\", \"raceNumber\", \"raceStatus\", \"distance\", \"time\", \"name\", \"nameForm\",
            \"trackCondition\", \"trackRating\", \"rdcClass\", \"isTrial\", \"isJumpOut\",
            \"trackCode\", \"condition\", \"class\", \"group\", \"raceTime\", \"standardTimeDifference\",
            \"formRaceEntries\",
        ]:
            value = detailed_race.get(key)
            if value not in (None, \"\", []):
                merged[key] = value
        venue = detailed_race.get(\"venue\")
        if isinstance(venue, dict) and not merged.get(\"meet\"):
            merged[\"meet\"] = {\"venue\": venue.get(\"venueName\")}
        return merged

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=\"Mozilla/5.0\",
            viewport={\"width\": 1280, \"height\": 900},
        )

        for m in meetings:
            page = context.new_page()
            race_list_payloads = []
            race_form_payloads = {}

            def handle_response(resp):
                if \"graphql.rmdprod.racing.com\" not in resp.url:
                    return
                try:
                    txt = resp.text()
                    data = json.loads(txt)
                    data_obj = data.get(\"data\") or {}
                    races = data_obj.get(\"getNoCacheRacesForMeet\") or []
                    if races:
                        race_list_payloads.append(races)
                    detail = data_obj.get(\"getRaceForm\")
                    if isinstance(detail, dict) and detail.get(\"formRaceEntries\"):
                        keys = {
                            clean(detail.get(\"id\")),
                            clean(detail.get(\"raceCode\")),
                            clean(detail.get(\"raceNumber\")),
                        }
                        for key in keys:
                            if key:
                                race_form_payloads[key] = detail
                except Exception:
                    pass

            page.on(\"response\", handle_response)
            try:
                page.goto(m[\"form_url\"], wait_until=\"domcontentloaded\", timeout=45000)
                page.wait_for_timeout(8000)
            except Exception:
                pass
            page.close()

            races = race_list_payloads[-1] if race_list_payloads else []

            if not races and m.get(\"meet_code\"):
                page = context.new_page()
                try:
                    page.goto(gql_url_for_race_list(m[\"meet_code\"]), wait_until=\"networkidle\", timeout=45000)
                    body = page.locator(\"body\").inner_text(timeout=10000)
                    data = json.loads(body)
                    races = ((data.get(\"data\") or {}).get(\"getNoCacheRacesForMeet\") or [])
                except Exception:
                    races = []
                page.close()

            for r in races:
                if r.get(\"isTrial\") or r.get(\"isJumpOut\"):
                    continue
                race_no = clean(r.get(\"raceNumber\"))
                if not race_no:
                    continue
                detailed = race_form_payloads.get(clean(r.get(\"id\"))) or race_form_payloads.get(race_no)
                merged_race = merge_race(r, detailed)
                entries = merged_race.get(\"formRaceEntries\") or []
                rows.append({
                    **m,
                    \"race_id\": clean(merged_race.get(\"id\")),
                    \"race_no\": race_no,
                    \"race_name\": clean(merged_race.get(\"name\")),
                    \"race_class\": clean(merged_race.get(\"rdcClass\") or merged_race.get(\"class\") or merged_race.get(\"nameForm\")),
                    \"distance\": clean(merged_race.get(\"distance\")),
                    \"race_time_utc\": clean(merged_race.get(\"time\")),
                    \"race_status\": clean(merged_race.get(\"raceStatus\") or merged_race.get(\"status\")),
                    \"track_condition\": clean(merged_race.get(\"trackCondition\") or merged_race.get(\"condition\")),
                    \"track_rating\": clean(merged_race.get(\"trackRating\")),
                    \"rail_position\": \"\",
                    \"weather\": \"\",
                    \"weather_wind_direction\": \"\",
                    \"weather_wind_speed\": \"\",
                    \"weather_rain\": \"\",
                    \"weather_min\": \"\",
                    \"weather_max\": \"\",
                    \"rainfall\": \"\",
                    \"form_entries_json\": json.dumps(entries, ensure_ascii=False),
                    \"source\": \"RACING_COM_GETMEETSBYMONTH_PLUS_GETRACEFORM\",
                    \"built_at\": built_at,
                })

        context.close()
        browser.close()

    return rows
"""
TARGET.write_text(text[:start] + new_func + text[end:], encoding="utf-8")
print(f"patched {TARGET}")
print(f"checkpoint {CHECKPOINT}")
