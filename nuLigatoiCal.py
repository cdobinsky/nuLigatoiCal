from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from icalendar import Calendar, Event

SPIELPLAN_URL = 'https://hvn-handball.liga.nu/cgi-bin/WebObjects/nuLigaHBDE.woa/wa/groupPage?displayTyp=vorrunde&displayDetail=meetings&championship=Hannover+2020%2F21&group=269069'
VEREIN = 'TV Hannover-Badenstedt'


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e):
    """
    Error Logging
    """
    print(e)


def get_games(plan):
    games = []
    date = ''
    for row in plan:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        if cols:
            games.append(cols[1:7])
    for game in games:
        if game[0]:
            games = game[0]
        else:
            game[0] = date
    data = [x for x in games if VEREIN in x]
    for idx, game in enumerate(data):
        games[idx].remove(VEREIN)
    return games


def get_addresses(plan):
    # Extrahiert die Links von den Hallen der Spiele
    hallen_links = []
    for row in plan:
        cols = row.find_all('a')
        cols = [(ele.text.strip(), ele['href']) for ele in cols]
        hallen_links.append([ele for ele in cols if ele])
    hallen_links = hallen_links[5:]

    # Extrahiert die Adresse der Hallen
    addresses = {}
    for link in hallen_links:
        url = 'https://hvn-handball.liga.nu' + link[0][1]
        if link[0][0] not in addresses:
            halle_resp = simple_get(url)
            halle_html = BeautifulSoup(halle_resp, 'html.parser')
            halle = halle_html.find_all('p')
            halle = [ele.text.strip().split('\n') for ele in halle]
            halle = [ele.strip() for ele in halle[0]]
            halle = halle[0] + ', ' + halle[3] + ' ' + halle[4].split()[0]
            addresses[link[0][0]] = halle
    return addresses


def create_calendar(data):
    cal = Calendar()
    for entry in data:
        print(entry)
        event = Event()
        event.add('summary', entry[2])
        event.add('dtstart', entry[0])
        event.add('dtend', entry[0] + timedelta(hours=2))
        event.add('location', entry[1])
        cal.add_component(event)

    f = open('saison20-21.ics', 'wb')
    f.write(cal.to_ical())
    f.close()


if __name__ == "__main__":
    plan_resp = simple_get(SPIELPLAN_URL)
    plan_html = BeautifulSoup(plan_resp, 'html.parser')
    rows = plan_html.find_all('tr')
    spiele = get_games(rows)
    hallen = get_addresses(rows)

    # Erstellt die Liste fuer den Kalendar
    full_data = []
    for match in spiele:
        item = [datetime.strptime(match[0] + ' ' + match[1].split()[0], '%d.%m.%Y %H:%M'), hallen[match[2]], match[4]]
        full_data.append(item)

    create_calendar(full_data)
