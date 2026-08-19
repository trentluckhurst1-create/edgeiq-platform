from bs4 import BeautifulSoup

def parse_form_rows(horse, horse_key, url, html):
    soup = BeautifulSoup(html, "lxml")

    rows = []

    table = soup.find("table")

    if not table:
        return []

    trs = table.find_all("tr")

    for tr in trs:
        tds = tr.find_all("td")

        if len(tds) < 5:
            continue

        try:
            date = tds[0].get_text(strip=True)
            track = tds[1].get_text(strip=True)
            distance = tds[2].get_text(strip=True)
            finish = tds[3].get_text(strip=True)
            margin = tds[4].get_text(strip=True)

            rows.append({
                "horse": horse,
                "horse_key": horse_key,
                "run_date": date,
                "track": track,
                "distance": distance,
                "finish_pos": finish,
                "margin": margin,
                "run_type": "RACE",
                "source_url": url
            })

        except:
            continue

    return rows
