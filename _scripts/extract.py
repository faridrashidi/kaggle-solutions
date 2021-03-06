lastnumber = 412
title_id = "cOMZdl"
desc_id = "iHHIVP"
subdesc_id = "cUPDWd"
prize_id = "emXfmI"
which = '2 months ago'


from bs4 import BeautifulSoup
import sys
with open('url.html', 'r') as f:
    contents = f.read()
    soup = BeautifulSoup(contents, features="html.parser")
i = lastnumber + 1
for item in soup.find_all("li", {"class": "mdc-list-item"}):
    date = item.find("span", {"class": subdesc_id})
    if date and date.text.split(' • ')[1] == which:
        i += 1
fout = open('new.txt', 'w') # fout = sys.stdout
for item in soup.find_all("li", {"class": "mdc-list-item"}):
    date = item.find("span", {"class": subdesc_id})
    if date and date.text.split(' • ')[1] == which:
        i -= 1
        kind = date.text.split(' • ')[0]
        team = date.text.split(' • ')[-1].replace(' Teams','')
        try:
            team = "{:,}".format(int(team))
        except:
            team = "-"
        link = "https://www.kaggle.com" + item.find("a")["href"]
        image = item.find("img")["src"].split("?t=")[0]
        year = '2021'
        isHot = 'false'
        done = 'false'
        title = item.find("div", {"class": title_id}).text
        desc = item.find("span", {"class": desc_id}).text
        desc = desc.replace(":", ";").replace("'","")
        prize = item.find("div", {"class": prize_id}).text
        print(f"  - number: '{i}'", file=fout)
        print(f"    title: '{title}'", file=fout)
        print(f"    desc: '{desc}'", file=fout)
        print(f"    kind: '{kind}'", file=fout)
        print(f"    prize: '{prize}'", file=fout)
        print(f"    team: '{team}'", file=fout)
        print(f"    link: '{link}'", file=fout)
        print(f"    image: '{image}'", file=fout)
        print(f"    year: '{year}'", file=fout)
        print(f"    isHot: '{isHot}'", file=fout)
        print(f"    done: '{done}'", file=fout)
        print(f"    solutions: ", file=fout)
        for _ in range(3):
            print(f"      - rank: ''", file=fout)
            print(f"        link: ''", file=fout)
            print(f"        kind: 'description'", file=fout)
fout.close()
