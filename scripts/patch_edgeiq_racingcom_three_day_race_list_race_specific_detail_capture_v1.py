from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "build_edgeiq_racingcom_three_day_race_list_v1.py"
CHECKPOINT = ROOT / "scripts" / "build_edgeiq_racingcom_three_day_race_list_v1_CHECKPOINT_PRE_RACE_SPECIFIC_DETAIL_CAPTURE_20260723.py"
text = TARGET.read_text(encoding="utf-8")
if not CHECKPOINT.exists():
    CHECKPOINT.write_text(text, encoding="utf-8")
needle = """            for r in races:
                if r.get("isTrial") or r.get("isJumpOut"):
                    continue
                race_no = clean(r.get("raceNumber"))
                if not race_no:
                    continue
                detailed = race_form_payloads.get(clean(r.get("id"))) or race_form_payloads.get(race_no)
                merged_race = merge_race(r, detailed)
"""
replacement = """            def capture_race_detail(race_no_value):
                detail_page = context.new_page()

                def handle_detail_response(resp):
                    if "graphql.rmdprod.racing.com" not in resp.url:
                        return
                    try:
                        txt = resp.text()
                        data = json.loads(txt)
                        detail = ((data.get("data") or {}).get("getRaceForm"))
                        if isinstance(detail, dict) and detail.get("formRaceEntries"):
                            keys = {
                                clean(detail.get("id")),
                                clean(detail.get("raceCode")),
                                clean(detail.get("raceNumber")),
                            }
                            for key in keys:
                                if key:
                                    race_form_payloads[key] = detail
                    except Exception:
                        pass

                detail_page.on("response", handle_detail_response)
                try:
                    detail_page.goto(f"{m['form_url']}/race/{race_no_value}", wait_until="domcontentloaded", timeout=45000)
                    detail_page.wait_for_timeout(6000)
                except Exception:
                    pass
                detail_page.close()

            for race in races:
                race_no_for_detail = clean(race.get("raceNumber"))
                if not race_no_for_detail:
                    continue
                if not (race_form_payloads.get(clean(race.get("id"))) or race_form_payloads.get(race_no_for_detail)):
                    capture_race_detail(race_no_for_detail)

            for r in races:
                if r.get("isTrial") or r.get("isJumpOut"):
                    continue
                race_no = clean(r.get("raceNumber"))
                if not race_no:
                    continue
                detailed = race_form_payloads.get(clean(r.get("id"))) or race_form_payloads.get(race_no)
                merged_race = merge_race(r, detailed)
"""
if needle not in text:
    raise SystemExit("target block not found")
TARGET.write_text(text.replace(needle, replacement), encoding="utf-8")
print(f"patched {TARGET}")
print(f"checkpoint {CHECKPOINT}")
