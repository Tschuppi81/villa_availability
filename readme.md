# Villa Availability

Scrapes how heavily booked the holiday villas of two Cape Coral rental agencies
are, stores a snapshot per run, and prints/plots the result.

| Source | Site | How the data is read |
| --- | --- | --- |
| `intervillas` | [intervillas-florida.com](https://www.intervillas-florida.com) | Public **Directus API** (`/items/villas`, `/items/bookings`) -- two requests, no browser |
| `nmb` | [nmbfloridavacationrentals.com](https://www.nmbfloridavacationrentals.com) | Joomla `com_fwrealestate` **calendar AJAX endpoint**, parsed with BeautifulSoup |

A day counts as *blocked* when it is fully booked or is a check-in day. The
check-out day stays free for the next guest, so it is not counted. Both scrapers
follow this convention, which keeps their numbers comparable.

## Setup

1. **Clone the repository**
   ```sh
   git clone https://github.com/yourusername/villa_availability.git
   cd villa_availability
   ```

2. **Create a virtual environment**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

4. **Run the application** -- from the repository root, so that the
   `src.villa_availabitlity` imports resolve
   ```sh
   python -m src.villa_availabitlity.main
   ```

## Menu

| # | Entry | What it does |
| --- | --- | --- |
| 1 | Scrape webpages and store data | Collects 24 months of history plus 6 months ahead and writes `data/<YYYYMMDD>_<source>.json` |
| 2 | Load data and visualize it | Prints a table for the last and the current year, and writes a heatmap to `plots/` |
| 3 | Compare this year with the last | Year-over-year table, restricted to the months that have fully elapsed |

## How the data is kept

Each run of menu 1 writes one snapshot per source. A snapshot only ever holds
the months that source could actually serve at the time, so nothing is invented.

Menu 2 and 3 merge **every** snapshot in `data/` back together. Where two
snapshots cover the same month the newer one wins: bookings only accumulate, so
a later observation is the more complete one. This is how months that the live
sites no longer serve stay available.

Villas are matched by name across snapshots, and villas that have since left a
portfolio are dropped from the report (`load_villa_history(..., only_listed=False)`
keeps them).

### Realized vs. forecast

Months that have not fully elapsed hold *bookings taken so far*, not occupancy,
and they keep climbing as the month approaches. The reports never mix the two
silently:

- the table marks the boundary with `‖`, the heatmap with a vertical line
- menu 3 compares only elapsed months against the same months a year earlier

### Known gap: Intervillas before 2026

The Intervillas relaunch migrated only the bookings that were still live at
cutover, so its Directus API holds nothing usable before **January 2026** --
earlier months contain only the residue of long stays reaching into 2026.
`DIRECTUS_HISTORY_FLOOR` in `intervillas.py` stops the scraper from reporting
those as "0 % booked".

The archived snapshots cover **Jul 2024 - Jun 2025**, which leaves
**Jul - Dec 2025 with no data at all**. Those months print as `-` and break the
heatmap into grey cells rather than being drawn as zero.

NMB has no such gap: its calendar endpoint serves any past month, so its history
is scraped live and is genuine realized occupancy.

> Snapshot months taken from an old archive reflect the bookings known *at the
> time of that snapshot*. For months far beyond the snapshot date this
> undercounts the eventual occupancy, which flatters the year-over-year deltas
> for Intervillas. NMB's history is unaffected.

## Tests

```sh
pip install pytest
python -m pytest tests/
```

## TODO

- [ ] Add a `--force` option to menu 1 to scrape even if the last snapshot is recent
- [ ] replace request by niquest 
- [ ] review project / file structure
