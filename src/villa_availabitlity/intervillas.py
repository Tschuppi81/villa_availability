"""Retrieve villa availability from the Intervillas Florida Directus API.

The site is a Vue SPA backed by a public Directus instance proxied under the
same origin, so no browser rendering is needed anymore. Availability is derived
from the `bookings` collection: a booking blocks the nights `[start_date,
end_date)`, i.e. the check-in day is blocked and the check-out day is free
again for the next guest.
"""

from collections import defaultdict
from datetime import date, timedelta

import requests

from src.villa_availabitlity.common import MONTH_ABBR_DE, make_month_entry, \
    average_percentage_blocked, get_month_days, month_labels, month_window

API_BASE = 'https://www.intervillas-florida.com'
VILLA_LIST_PATH = 'ferienhaus-cape-coral'
SITE = 'florida'

# Booking states that make a day unavailable ('blocked' are turnover/owner days)
BLOCKING_STATUSES = 'pending,confirmed,blocked'

# The relaunch migrated only the bookings that were still live at cutover, so
# earlier months hold nothing but the residue of long stays reaching into 2026.
# Reporting those as '0% booked' would be a lie; months before the floor are
# left to the archived snapshots in `data/` instead. See `load_villa_history`.
DIRECTUS_HISTORY_FLOOR = date(2026, 1, 1)

TIMEOUT = 30


def _get_items(collection: str, **params) -> list[dict]:
    response = requests.get(f'{API_BASE}/items/{collection}', params=params,
                            timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()['data']


def get_intervillas() -> list[dict]:
    """Return the published villas as dicts with `id`, `name` and `url`."""
    items = _get_items(
        'villas',
        **{'filter[status][_eq]': 'published',
           f'filter[site_{SITE}][_eq]': 'true',
           'fields': 'id,name,slug',
           'sort': 'sort',
           'limit': -1},
    )

    villas = [{'id': item['id'],
               'name': item['name'].strip(),
               'url': f'{API_BASE}/{VILLA_LIST_PATH}/{item["slug"]}'}
              for item in items]

    print(f'Found {len(villas)} villas')
    return sorted(villas, key=lambda v: v['name'])


def get_bookings_by_villa() -> dict[int, list[tuple[date, date]]]:
    """Fetch every blocking booking in one request, grouped by villa id."""
    items = _get_items(
        'bookings',
        **{'filter[status][_in]': BLOCKING_STATUSES,
           'fields': 'villa,start_date,end_date',
           'sort': 'start_date',
           'limit': -1},
    )

    bookings = defaultdict(list)
    for item in items:
        if not (item['villa'] and item['start_date'] and item['end_date']):
            continue
        bookings[item['villa']].append((date.fromisoformat(item['start_date']),
                                        date.fromisoformat(item['end_date'])))
    return bookings


def get_blocked_dates(bookings: list[tuple[date, date]]) -> set[date]:
    """Expand bookings into the set of blocked days.

    The check-out day (`end_date`) stays available, so only the nights
    `[start_date, end_date)` are blocked. A set also collapses the overlap
    between adjacent bookings that share a turnover day.
    """
    blocked = set()
    for start, end in bookings:
        day = start
        while day < end:
            blocked.add(day)
            day += timedelta(days=1)
    return blocked


def count_blocked_days(blocked_dates: set[date], year: int, month: int) -> int:
    total_days = get_month_days(year, month)
    return sum(date(year, month, day) in blocked_dates
               for day in range(1, total_days + 1))


def scrape_intervillas(today: date = None) -> list[dict]:
    """Collect availability for every published villa.

    Only months the API can actually speak to are returned; the earlier ones
    come from the archived snapshots when the data is loaded again.
    """
    months = [(year, month) for year, month in month_window(today)
              if date(year, month, 1) >= DIRECTUS_HISTORY_FLOOR]
    labels = month_labels(months, MONTH_ABBR_DE)
    print(f'Collecting {labels[0]} .. {labels[-1]} from the Directus API')

    bookings_by_villa = get_bookings_by_villa()

    intervillas = []
    for villa in get_intervillas():
        blocked_dates = get_blocked_dates(bookings_by_villa[villa['id']])

        villa['months'] = [
            make_month_entry(label, count_blocked_days(blocked_dates, *month))
            for label, month in zip(labels, months)
        ]
        villa['average_percentage_blocked'] = average_percentage_blocked(
            villa['months'])

        intervillas.append(villa)

    return intervillas
