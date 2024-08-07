import calendar
import json
import os
from datetime import datetime

import matplotlib.pyplot as plt

from typing import Union


def get_month_days(year: Union[int, str], month: Union[int, str]) -> int:
    """ `Month` as well as `year` can be either a string or an integer.
    Supported are months as integers (1-12) or as strings (e.g., 'jan',
    'feb', 'mar', ...) in English or German e.g. 'okt'.
    Returns the number of days in the month.

    """

    month_map = {
        'jan': 1,
        'feb': 2,
        'mar': 3,
        'apr': 4,
        'mai': 5,
        'may': 5,
        'jun': 6,
        'jul': 7,
        'aug': 8,
        'sep': 9,
        'okt': 10,
        'oct': 10,
        'nov': 11,
        'dez': 12,
        'dec': 12,
    }
    if isinstance(month, str):
        if month.isdigit():
            month = int(month)
        month = month_map[month[:3].lower()]
    if isinstance(year, str):
        year = int(year)
    _, last_day = calendar.monthrange(year, month)
    return last_day


def get_month_abbr(full_month_name: str) -> str:
    """
    This function takes a full month name as a string and returns its
    abbreviation.

    full_month_name (str): The full name of the month (e.g., 'January').
    Returns str: The abbreviated name of the month (e.g., 'Jan').
    """
    month_number = list(calendar.month_name).index(full_month_name.capitalize())
    return calendar.month_abbr[month_number]


def calculate_percentage_blocked(blocked_days: int, total_days: int) -> float:
    return (blocked_days / total_days) * 100


def store_villa_data(villas, label):
    today = datetime.today().strftime('%Y%m%d')
    filename = f'../../data/{today}_{label}.json'
    with open(filename, 'w') as f:
        json.dump(villas, f, indent=4)


def load_villa_data(label):
    # filename = f'../../data/villas_{label}.json'
    dirname = f'../../data'

    files = os.listdir(dirname)
    files = [f for f in files if f.endswith('.json') and label in f]
    if not files:
        return {}

    files.sort()
    filename = files[-1]

    with open(os.path.join(dirname, filename), 'r') as f:
        return json.load(f)



def sort_villa_data(villas):
    return sorted(villas, key=lambda v: v['name'])


def print_availability_results(villas: list[dict]) -> None:
    """
    Print the availability results. The format is like the following:
    #            | month 1 | month 2 | ..
    # villa  1   |         |         | ..
    # villa  2   |         |         | ..
    # ..         |         |         | ..
    """
    if not villas:
        return None

    villas = sort_villa_data(villas)

    # Get unique months
    unique_months = list()
    for villa in villas:
        for month in villa["months"]:
            unique_months.append(month["month_name"])
        break

    # Print the header
    header = "| {:<30} |".format('Villa')
    sep_line = "+ {:<30} +".format('-' * 30)
    for month in unique_months:
        header += " {:>8} |".format(month)
        sep_line += " {:>8} +".format('-' * 8)
    header += " {:>8} |".format('Average')
    sep_line += " {:>8} +".format('-' * 8)

    print(sep_line)
    print(header)
    print(sep_line)

    # Print villa blocked days for each month
    for villa in villas:
        villa_line = "| {:<30} |".format(villa["name"][:30])
        for month in unique_months:
            for data in villa["months"]:
                if data["month_name"] == month:
                    if 'percentage_blocked' in data:
                        val = round(data["percentage_blocked"], 1)
                        villa_line += " {:>8.1f} |".format(val)
                    else:
                        villa_line += " {:>8} |".format('-')
                    break
            else:
                # month is not present
                villa_line += " {:>8} |".format('+')  # If data for the
        # print average percentage blocked for the villa
        villa_line += " {:>8.1f} |".format(villa["average_percentage_blocked"])
        print(villa_line)

    print(sep_line)


def draw_availability_graph(villas: list[dict], filename='') -> None:
    font_size = 8

    if not villas:
        return None

    villas = sort_villa_data(villas)

    months = [month['month_name'] for month in villas[0]['months']]
    for villa in villas:
        booked_days = [month['blocked_days'] for month in villa['months']]
        plt.plot(months, booked_days, label=villa['name'][:25])

    plt.xlabel('Months', fontsize=font_size)
    plt.xticks(rotation=30)
    plt.ylabel('Booked Days', fontsize=font_size)
    plt.title('Booked Days for Each Villa Over Months')
    plt.legend(loc=(1.03, 0), fontsize=font_size)
    plt.tight_layout()

    if filename:
        plt.savefig(filename, bbox_inches='tight', dpi=300)

    plt.show()
