import calendar
import json
import os
from datetime import date, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import blended_transform_factory

from typing import Optional, Union

# How far the scrapers look back and ahead, in months.
MONTHS_HISTORY = 24
MONTHS_AHEAD = 6

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
PLOTS_DIR = PROJECT_ROOT / 'plots'
REPORTS_DIR = PROJECT_ROOT / 'reports'

# Intervillas labels its months in German, NMB in English.
MONTH_ABBR_DE = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
MONTH_ABBR_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mai': 5, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'oct': 10, 'nov': 11,
    'dez': 12, 'dec': 12,
}


def get_month_days(year: Union[int, str], month: Union[int, str]) -> int:
    """ `Month` as well as `year` can be either a string or an integer.
    Supported are months as integers (1-12) or as strings (e.g., 'jan',
    'feb', 'mar', ...) in English or German e.g. 'okt'.
    Returns the number of days in the month.

    """

    if isinstance(month, str):
        if month.isdigit():
            month = int(month)
        else:
            month = MONTH_MAP[month[:3].lower()]
    if isinstance(year, str):
        year = int(year)
    _, last_day = calendar.monthrange(year, month)
    return last_day


def calculate_percentage_blocked(blocked_days: int, total_days: int) -> float:
    return (blocked_days / total_days) * 100


def parse_month_label(month_name: str) -> tuple[int, int]:
    """Turn a label such as 'Okt 2025' into `(2025, 10)`."""
    abbr, year = month_name.split(' ')
    return int(year), MONTH_MAP[abbr[:3].lower()]


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + month - 1) + delta
    return index // 12, index % 12 + 1


def month_window(today: date = None, back: int = MONTHS_HISTORY,
                 ahead: int = MONTHS_AHEAD) -> list[tuple[int, int]]:
    """The months to collect: `back` months of history up to and including the
    current month, plus `ahead` months into the future."""
    today = today or date.today()
    return [add_months(today.year, today.month, offset)
            for offset in range(-back, ahead)]


def month_labels(months: list[tuple[int, int]], abbr: list[str]) -> list[str]:
    return [f'{abbr[month - 1]} {year}' for year, month in months]


def make_month_entry(month_name: str,
                     blocked_days: Optional[int]) -> dict:
    """Build a month record. `blocked_days` of `None` means 'no data'."""
    if blocked_days is None:
        return {'month_name': month_name, 'available_days': None,
                'blocked_days': None, 'percentage_blocked': None}

    year, month = parse_month_label(month_name)
    total_days = get_month_days(year, month)
    return {
        'month_name': month_name,
        'available_days': total_days - blocked_days,
        'blocked_days': blocked_days,
        'percentage_blocked': calculate_percentage_blocked(blocked_days,
                                                           total_days),
    }


def average_percentage_blocked(months: list[dict]) -> Optional[float]:
    """Average over the months that actually carry data."""
    known = [month['percentage_blocked'] for month in months
             if month.get('percentage_blocked') is not None]
    return sum(known) / len(known) if known else None


def store_villa_data(villas, label):
    today = datetime.today().strftime('%Y%m%d')
    DATA_DIR.mkdir(exist_ok=True)
    filename = DATA_DIR / f'{today}_{label}.json'
    with open(filename, 'w') as f:
        json.dump(villas, f, indent=4)
    print(f'Stored {len(villas)} villas in {filename}')


def _snapshot_files(label) -> list[str]:
    if not DATA_DIR.is_dir():
        return []
    files = [f for f in os.listdir(DATA_DIR)
             if f.endswith('.json') and label in f]
    return sorted(files)


def load_villa_data(label):
    """Load the most recent snapshot for `label`."""
    files = _snapshot_files(label)
    if not files:
        return []

    with open(DATA_DIR / files[-1], 'r') as f:
        return json.load(f)


def load_villa_history(label, only_listed=True):
    """Merge every stored snapshot into one villa list.

    Snapshots only ever hold months observed at the time they were taken, so
    older files supply the history that the live sources no longer serve. When
    two snapshots cover the same month the newer one wins: bookings only
    accumulate, so a later observation is always the more complete one.

    Villas are matched by name. `only_listed` drops the ones that have since
    left the portfolio; pass `False` to keep their history too.
    """
    villas = {}
    listed = set()
    for filename in _snapshot_files(label):  # oldest first
        with open(DATA_DIR / filename, 'r') as f:
            snapshot = json.load(f)

        listed = {villa['name'] for villa in snapshot}
        for villa in snapshot:
            merged = villas.setdefault(villa['name'], {'months': {}})
            months = merged['months']
            merged.update({k: v for k, v in villa.items() if k != 'months'})
            merged['months'] = months

            for month in villa['months']:
                if month.get('blocked_days') is None:
                    continue  # never let a gap overwrite a real observation
                months[month['month_name']] = month

    if only_listed:  # `listed` holds the names from the newest snapshot
        villas = {name: villa for name, villa in villas.items()
                  if name in listed}

    for villa in villas.values():
        villa['months'] = sorted(villa['months'].values(),
                                 key=lambda m: parse_month_label(
                                     m['month_name']))
        villa['average_percentage_blocked'] = average_percentage_blocked(
            villa['months'])

    return list(villas.values())


def select_months(villas: list[dict], months: list[str]) -> list[dict]:
    """Restrict every villa to `months`, inserting gaps where data is missing."""
    selected = []
    for villa in villas:
        known = {month['month_name']: month for month in villa['months']}
        villa = dict(villa)
        villa['months'] = [known.get(name) or make_month_entry(name, None)
                           for name in months]
        villa['average_percentage_blocked'] = average_percentage_blocked(
            villa['months'])
        selected.append(villa)
    return selected


def average_for_year(months: list[dict], year: int) -> Optional[float]:
    """Average percentage blocked over one calendar year's months with data."""
    known = [month['percentage_blocked'] for month in months
             if month['percentage_blocked'] is not None
             and parse_month_label(month['month_name'])[0] == year]
    return sum(known) / len(known) if known else None


def sort_villa_data(villas):
    return sorted(villas, key=lambda v: v['name'])


def _ordered_months(villas: list[dict]) -> list[str]:
    names = {month['month_name'] for villa in villas
             for month in villa['months']}
    return sorted(names, key=parse_month_label)


def forecast_index(months: list[str], today: date = None) -> Optional[int]:
    """Index of the first month that has not fully elapsed.

    Everything from there on is 'bookings taken so far' rather than realized
    occupancy, and will keep climbing as the months approach. Comparing the two
    halves without saying so would read as collapsing demand.
    """
    today = today or date.today()
    for index, month in enumerate(months):
        if parse_month_label(month) >= (today.year, today.month):
            return index
    return None


def portfolio_percentages(villas: list[dict],
                          months: list[str]) -> dict[str, Optional[float]]:
    """Mean percentage blocked across all villas, per month."""
    averages = {}
    for month in months:
        known = [entry['percentage_blocked']
                 for villa in villas
                 for entry in villa['months']
                 if entry['month_name'] == month
                 and entry['percentage_blocked'] is not None]
        averages[month] = sum(known) / len(known) if known else None
    return averages


def elapsed_months(today: date = None) -> list[int]:
    """The months of the current year that have fully elapsed.

    Only these carry realized occupancy. The current month is still filling up
    and the ones after it are forecast, so neither belongs in a comparison
    against a completed year.
    """
    today = today or date.today()
    return list(range(1, today.month))


def average_for_labels(months: list[dict],
                       labels: list[str]) -> Optional[float]:
    """Average percentage blocked over exactly `labels`, ignoring gaps."""
    wanted = set(labels)
    known = [month['percentage_blocked'] for month in months
             if month['month_name'] in wanted
             and month['percentage_blocked'] is not None]
    return sum(known) / len(known) if known else None


def _format_percentage(percentage: Optional[float]) -> str:
    return '-' if percentage is None else f'{percentage:.1f}'


def _format_delta(delta: Optional[float]) -> str:
    return '-' if delta is None else f'{delta:+.1f}'


def _delta(current: Optional[float],
           previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None:
        return None  # a year without data cannot be compared
    return current - previous


def _table_row(first: str, cells: list[str], average: str,
               boundary: Optional[int], separator: str = '|') -> str:
    row = f'{separator} {first:<30} '
    for index, cell in enumerate(cells):
        # the divider marks where realized months end and forecast begins
        row += ('‖' if index == boundary else separator) + f' {cell:>8} '
    return row + f'{separator} {average:>8} {separator}'


def print_availability_results(villas: list[dict], today: date = None,
                               year: int = None) -> list[str]:
    """
    Print the availability results. The format is like the following:
    #            | month 1 | month 2 | ..
    # villa  1   |         |         | ..
    # villa  2   |         |         | ..
    # ..         |         |         | ..

    The average column covers `year` only (the current one by default), so it
    is not diluted by the previous year's months.

    Returns the rendered lines, so the very same table can go into a PDF
    without being laid out a second time.
    """
    if not villas:
        return []

    today = today or date.today()
    year = year or today.year

    villas = sort_villa_data(villas)
    unique_months = _ordered_months(villas)
    boundary = forecast_index(unique_months, today)

    sep_line = _table_row('-' * 30, ['-' * 8] * len(unique_months), '-' * 8,
                          boundary, separator='+')

    lines = [sep_line,
             _table_row('Villa', unique_months, f'Avg {year}', boundary),
             sep_line]

    # A villa's blocked days for each month
    for villa in villas:
        months = {month['month_name']: month for month in villa['months']}
        cells = [_format_percentage(
            (months.get(month) or {}).get('percentage_blocked'))
            for month in unique_months]
        lines.append(_table_row(villa['name'][:30], cells, _format_percentage(
            average_for_year(villa['months'], year)), boundary))

    lines.append(sep_line)

    # And the portfolio as a whole, which is what a season actually looks like
    averages = portfolio_percentages(villas, unique_months)
    known = [value for month, value in averages.items()
             if value is not None and parse_month_label(month)[0] == year]
    lines.append(_table_row(
        f'ALL VILLAS (n={len(villas)})',
        [_format_percentage(averages[m]) for m in unique_months],
        _format_percentage(sum(known) / len(known) if known else None),
        boundary))
    lines.append(sep_line)

    if boundary is not None:
        lines.append('‖ left: realized occupancy | right: bookings taken so '
                     'far (still rising)')
    lines.append(f'Avg {year} mixes realized and forecast months, so it '
                 f'understates the year')
    lines.append("'-' means no data was ever collected for that month")

    print('\n'.join(lines))
    return lines


def print_year_comparison(villas: list[dict], abbr: list[str],
                          today: date = None) -> list[str]:
    """Compare each villa's occupancy against the same months a year earlier.

    Only the elapsed months of the current year are used, on both sides, so the
    two figures mean the same thing. Comparing a finished year against one that
    is half forecast would show every villa 'down'.

    Returns the rendered lines, so the very same table can go into a PDF
    without being laid out a second time.
    """
    if not villas:
        return []

    today = today or date.today()
    year, previous = today.year, today.year - 1
    numbers = elapsed_months(today)
    if not numbers:
        print(f'No month of {year} has elapsed yet -- nothing to compare')
        return []

    current_labels = month_labels([(year, m) for m in numbers], abbr)
    previous_labels = month_labels([(previous, m) for m in numbers], abbr)
    window = f'{abbr[numbers[0] - 1]}-{abbr[numbers[-1] - 1]}'

    villas = sort_villa_data(villas)
    headers = [abbr[number - 1] for number in numbers] + [
        str(previous), str(year)]
    sep_line = _table_row('-' * 30, ['-' * 8] * len(headers), '-' * 8, None,
                          separator='+')

    lines = [f'--- {window} {previous} vs {window} {year} '
             f'(percentage points) ---',
             sep_line,
             _table_row('Villa', headers, 'Delta', None),
             sep_line]

    for villa in villas:
        months = {month['month_name']: month for month in villa['months']}

        cells = []
        for current, prior in zip(current_labels, previous_labels):
            cells.append(_format_delta(_delta(
                (months.get(current) or {}).get('percentage_blocked'),
                (months.get(prior) or {}).get('percentage_blocked'))))

        before = average_for_labels(villa['months'], previous_labels)
        after = average_for_labels(villa['months'], current_labels)
        cells += [_format_percentage(before), _format_percentage(after)]
        lines.append(_table_row(villa['name'][:30], cells,
                                _format_delta(_delta(after, before)), None))

    lines.append(sep_line)

    # the portfolio as a whole, month by month
    averages = portfolio_percentages(villas, previous_labels + current_labels)
    cells = [_format_delta(_delta(averages[current], averages[prior]))
             for current, prior in zip(current_labels, previous_labels)]

    known = [averages[label] for label in previous_labels
             if averages[label] is not None]
    before = sum(known) / len(known) if known else None
    known = [averages[label] for label in current_labels
             if averages[label] is not None]
    after = sum(known) / len(known) if known else None

    cells += [_format_percentage(before), _format_percentage(after)]
    lines.append(_table_row(f'ALL VILLAS (n={len(villas)})', cells,
                            _format_delta(_delta(after, before)), None))
    lines.append(sep_line)
    lines.append(f'Month columns are {year} minus {previous}, in percentage '
                 f'points; + means busier than last year')
    lines.append("'-' means one of the two years has no data for that month")

    print('\n'.join(lines))
    return lines


def draw_availability_heatmap(villas: list[dict], filename='',
                              title='', today: date = None,
                              year: int = None) -> None:
    """Draw villas x months of `year` as a colour grid.

    A line per villa turns into unreadable spaghetti at this many series; a
    heatmap shows the same data at a glance, and missing months stay visibly
    grey instead of pretending to be zero.
    """
    if not villas:
        return None

    today = today or date.today()
    year = year or today.year

    villas = sort_villa_data(villas)
    unique_months = [month for month in _ordered_months(villas)
                     if parse_month_label(month)[0] == year]
    if not unique_months:
        return None
    boundary = forecast_index(unique_months, today)

    grid = []
    for villa in villas:
        months = {month['month_name']: month for month in villa['months']}
        grid.append([(months.get(name) or {}).get('percentage_blocked')
                     for name in unique_months])

    # masked cells render in the colormap's 'bad' colour, i.e. grey
    data = np.ma.masked_invalid(
        np.array(grid, dtype=float))  # None -> nan -> masked

    colormap = plt.get_cmap('YlOrRd').copy()
    colormap.set_bad('#d9d9d9')

    height = max(3.0, 0.16 * len(villas) + 1.5)
    figure, axes = plt.subplots(figsize=(0.42 * len(unique_months) + 5, height))
    image = axes.imshow(data, aspect='auto', cmap=colormap, vmin=0, vmax=100)

    axes.set_xticks(range(len(unique_months)))
    axes.set_xticklabels(unique_months, rotation=90, fontsize=7)
    axes.set_yticks(range(len(villas)))
    axes.set_yticklabels([villa['name'][:28] for villa in villas], fontsize=6)

    if boundary is not None:
        axes.axvline(boundary - 0.5, color='black', linewidth=1.5)
        # x in data coords, y in axes coords: just above the grid, under the
        # title (which `pad` lifts out of the way)
        labels = blended_transform_factory(axes.transData, axes.transAxes)
        axes.text(boundary - 0.6, 1.005, '<- realized', fontsize=7, ha='right',
                  va='bottom', transform=labels)
        axes.text(boundary - 0.4, 1.005, 'forecast ->', fontsize=7, ha='left',
                  va='bottom', transform=labels)

    axes.set_title(title or f'{year}: percentage of days blocked', pad=20)
    figure.colorbar(image, ax=axes, label='% of days blocked', pad=0.02)
    figure.tight_layout()

    if filename:
        PLOTS_DIR.mkdir(exist_ok=True)
        figure.savefig(filename, bbox_inches='tight', dpi=150)

    plt.show()
    plt.close(figure)
