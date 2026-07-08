from datetime import date, datetime

from src.villa_availabitlity.common import MONTH_ABBR_DE, MONTH_ABBR_EN, \
    PLOTS_DIR, draw_availability_heatmap, load_villa_history, month_labels, \
    print_availability_results, print_year_comparison, select_months, \
    store_villa_data

SOURCES = (('nmb', MONTH_ABBR_EN), ('intervillas', MONTH_ABBR_DE))
from src.villa_availabitlity.intervillas import scrape_intervillas
from src.villa_availabitlity.nmb import scrape_nmb
from src.villa_availabitlity.t_menu import Menu

today = datetime.today().strftime('%Y%m%d')


def scrape_and_store_data():
    print('--- Scraping data ---')
    print('- NMB')
    villas = scrape_nmb()
    store_villa_data(villas, 'nmb')

    print('- Intervillas')
    intervillas = scrape_intervillas()
    store_villa_data(intervillas, 'intervillas')


def reported_months(abbr: list[str]) -> list[str]:
    """The last and the current calendar year, month by month."""
    current_year = date.today().year
    return month_labels([(year, month)
                         for year in (current_year - 1, current_year)
                         for month in range(1, 13)], abbr)


def show_data(label: str, abbr: list[str]) -> None:
    """Table over the last and the current year, heatmap of the current one."""
    year = date.today().year
    villas = select_months(load_villa_history(label), reported_months(abbr))
    print_availability_results(villas)
    draw_availability_heatmap(
        villas, PLOTS_DIR / f'{today}_{label}.png',
        title=f'{label} {year}: percentage of days blocked')


def load_and_show_data():
    for label, abbr in SOURCES:
        print(f'--- Show {label} data ---')
        show_data(label, abbr)


def compare_years():
    for label, abbr in SOURCES:
        print(f'--- Compare {label} year over year ---')
        villas = select_months(load_villa_history(label),
                               reported_months(abbr))
        print_year_comparison(villas, abbr)


if __name__ == "__main__":
    menu = Menu(0, 'Villa availability')
    menu.add_sub_menu(Menu(1, 'Scrape webpages and store data', scrape_and_store_data))
    menu.add_sub_menu(Menu(2, 'Load data and visualize it', load_and_show_data))
    menu.add_sub_menu(Menu(3, 'Compare this year with the last', compare_years))

    menu.run()
