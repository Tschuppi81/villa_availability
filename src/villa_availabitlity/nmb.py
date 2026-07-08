"""Retrieve villa availability from NMB Florida Vacation Rentals.

The site is a Joomla install running the `com_fwrealestate` component. It has
no JSON API, but the calendar on an item page is refreshed through an AJAX
endpoint that renders six months of calendar as raw HTML for any month/year it
is given -- including months in the past. That is what makes history available
here, where Intervillas can only offer what its Directus instance still holds.

A day counts as blocked when it is fully booked (`fwre-booking-active`) or is a
check-in day (`checkin`). The check-out day stays free for the next guest, so
it is not counted -- the same convention the Intervillas scraper uses.
"""

import requests

from bs4 import BeautifulSoup

from src.villa_availabitlity.common import MONTH_ABBR_EN, MONTH_MAP, \
    average_percentage_blocked, make_month_entry, month_labels, month_window

BASE_URL = 'https://www.nmbfloridavacationrentals.com'
LIST_URL = f'{BASE_URL}/all-vacation-rentals'
ITEM_URL = f'{LIST_URL}/item'

# The calendar endpoint always answers with six months, starting at the
# requested one.
MONTHS_PER_REQUEST = 6

TIMEOUT = 30


def get_nmb_villas(session: requests.Session) -> list[dict]:
    """Return the listed villas as dicts with `id`, `name` and `url`."""
    response = session.get(LIST_URL, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    villas = []
    for v in soup.find_all('div', class_='fw-list-property'):
        villa_id = v.get('id', '').replace('fw-property-id-', '')
        if not villa_id:
            continue
        villas.append({
            'id': villa_id,
            'name': v.find('h2').text.strip(),
            'url': BASE_URL + v.find('a')['href'],
        })

    print(f'Found {len(villas)} villas')
    return villas


def fetch_calendar(session: requests.Session, villa_id: str, year: int,
                   month: int) -> dict[tuple[int, int], int]:
    """Fetch six months of calendar and count the blocked days in each."""
    response = session.post(
        ITEM_URL,
        data={'format': 'raw', 'layout': 'calendar', 'month': month,
              'year': year, 'id': villa_id},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    blocked_days = {}
    for table in soup.find_all('table'):
        # the header reads e.g. 'July 2026'
        month_name, month_year = table.find('th').text.strip().split(' ')
        key = (int(month_year), MONTH_MAP[month_name[:3].lower()])

        booked = table.find_all(class_='fwre-booking-active')
        checkins = table.find_all(class_='checkin')
        blocked_days[key] = len(booked) + len(checkins)

    return blocked_days


def get_blocked_days(session: requests.Session, villa_id: str,
                     months: list[tuple[int, int]]
                     ) -> dict[tuple[int, int], int]:
    """Walk the window in six-month steps, since that is what one request
    returns, and keep only the months that were asked for."""
    blocked_days = {}
    for start in range(0, len(months), MONTHS_PER_REQUEST):
        year, month = months[start]
        blocked_days.update(fetch_calendar(session, villa_id, year, month))

    return {month: blocked_days.get(month) for month in months}


def scrape_nmb(today=None) -> list[dict]:
    months = month_window(today)
    labels = month_labels(months, MONTH_ABBR_EN)
    print(f'Collecting {labels[0]} .. {labels[-1]} from the calendar endpoint')

    session = requests.Session()

    villas = []
    for villa in get_nmb_villas(session):
        print(f'{villa["name"]}')
        blocked_days = get_blocked_days(session, villa['id'], months)

        villa['months'] = [make_month_entry(label, blocked_days[month])
                           for label, month in zip(labels, months)]
        villa['average_percentage_blocked'] = average_percentage_blocked(
            villa['months'])

        villas.append(villa)

    return villas
