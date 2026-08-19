import requests

url = "https://www.racingaustralia.horse/FreeFields/HorseFullForm.aspx?HorseCode=NzE0Njc4MTM0"

html = requests.get(url).text

with open("debug_ra_page.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Saved debug_ra_page.html")
