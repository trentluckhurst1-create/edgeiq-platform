from bs4 import BeautifulSoup

def parse_form_rows(horse, horse_key, url, html):
    soup = BeautifulSoup(html, "lxml")

    rows = []

    tables = soup.find_all("table")

    for table in tables:
        text = table.get_text(" ", strip=True).lower()

        # ONLY accept tables that look like race form
        if "track" in text and "distance" in text and "jockey" in text:
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

                    # FILTER OUT HEADERS
                    if "date" in date.lower():
                        continue

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

            # BREAK once correct table found
            if rows:
                return rows

    return []
