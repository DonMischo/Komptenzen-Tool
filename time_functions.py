"""
time_functions.py

Fetch school holiday periods from Ferienwiki ICS feeds, cache them locally,
and compute report days (last school days) for both half-year (before winter holidays)
and end-year (before summer holidays), taking into account weekends
(weekends don’t count as school days).

Requires: icalendar (pip install icalendar)
Optionally consider using the `holidays` or `workalendar` packages for built-in German holiday calendars.
"""
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any
import requests
from icalendar import Calendar

# Directory for caching .ics files
CACHE_DIR: Path = Path(__file__).resolve().parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

# ICS URL template for Ferienwiki (adjust if their URL pattern changes)
ICS_URL_TEMPLATE = "https://www.ferienwiki.de/exports/ferien/{year}/de/{state}"



def get_school_year(today: date | None = None) -> str:
    """Return the current school year as "YYYY/YYYY" (e.g. "2025/2026")."""
    today = today or date.today()
    return f"{today.year}/{today.year+1}" if today.month >= 8 else f"{today.year-1}/{today.year}"


def get_school_year_report(today: date | None = None) -> str:
    """Return the calendar year for reports: year of winter or summer break."""
    today = today or date.today()
    return str(today.year+1) if today.month >= 8 else str(today.year)


def _load_or_fetch_holidays(
    state: str = "thueringen",
    year: str | int | None = None,
    *,
    max_age_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Download (or load from cache) the ICS for the given state and year,
    parse all VEVENTs into a list of {"name": str, "start": ISO-datetime} dicts.
    """
    year = year or get_school_year_report()
    cache_file = CACHE_DIR / f"ferien_{state}_{year}.ics"
    url = ICS_URL_TEMPLATE.format(state=state, year=year)
    data_bytes: bytes | None = None

    # Try cache first
    if cache_file.exists():
        age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age <= timedelta(days=max_age_days):
            data_bytes = cache_file.read_bytes()

    # Fetch if needed
    if data_bytes is None:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data_bytes = resp.content
        try:
            cache_file.write_bytes(data_bytes)
        except Exception:
            pass

    # Parse ICS
    cal = Calendar.from_ical(data_bytes)
    events: List[Dict[str, Any]] = []
    for comp in cal.walk():
        if comp.name == "VEVENT":
            summary = str(comp.get("SUMMARY"))
            dtstart = comp.get("DTSTART").dt
            # Normalize to date
            dt_obj = dtstart.date() if hasattr(dtstart, "date") else dtstart
            iso = datetime.combine(dt_obj, datetime.min.time()).isoformat()
            events.append({"name": summary, "start": iso})
    return events


def _get_last_school_day_before(dt: datetime) -> date:
    """Return the last school day before the given datetime,
    skipping weekends (Sat/Sun → move back to Fri)."""
    day = dt.date() - timedelta(days=1)
    while day.weekday() >= 5:  # 5=Sat, 6=Sun
        day -= timedelta(days=1)
    return day


def fetch_halfyear_report_day(
    state: str = "thueringen", year: str | int | None = None
) -> str:
    """Return the report day (last school day) before winter holidays in DD.MM.YYYY."""
    year = year or get_school_year_report()
    events = _load_or_fetch_holidays(state, year)
    for entry in events:
        if "winterferien" in entry["name"].lower():
            dt = datetime.fromisoformat(entry["start"])
            rep = _get_last_school_day_before(dt)
            return rep.strftime("%d.%m.%Y")
    raise ValueError(f"Winterferien für {state} im Jahr {year} nicht gefunden.")


def fetch_last_school_day(
    state: str = "thueringen", year: str | int | None = None
) -> str:
    """Return the report day (last school day) before summer holidays in DD.MM.YYYY."""
    year = year or get_school_year_report()
    events = _load_or_fetch_holidays(state, year)
    for entry in events:
        if "sommerferien" in entry["name"].lower():
            dt = datetime.fromisoformat(entry["start"])
            rep = _get_last_school_day_before(dt)
            return rep.strftime("%d.%m.%Y")
    raise ValueError(f"Sommerferien für {state} im Jahr {year} nicht gefunden.")


if __name__ == "__main__":
    state = "thueringen"
    sy = get_school_year()
    cy = get_school_year_report()
    print(f"School year: {sy}")
    print(f"Half-year report day: {fetch_halfyear_report_day(state, cy)}")
    print(f"Last school day before summer: {fetch_last_school_day(state, cy)}")
