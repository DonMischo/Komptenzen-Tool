import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, List, Dict

import requests

# ---------------------------------------------------------------------------
# Simple on‑disk cache -------------------------------------------------------
# ---------------------------------------------------------------------------
# All fetched JSON payloads are stored in <package>/data/ so the API is
# contacted only when the cached file is missing or considered too old.
# ---------------------------------------------------------------------------

CACHE_DIR: Path = Path(__file__).resolve().parent / "data"
CACHE_DIR.mkdir(exist_ok=True)


def _sanitize_year_for_filename(year: str | int) -> str:
    """Return *year* with path‑unfriendly characters replaced."""
    return str(year).replace("/", "-")


def _load_or_fetch_holidays(
    state: str = "TH",
    year: str | int | None = None,
    *,
    max_age_days: int = 30,
) -> List[Dict[str, Any]]:
    """Return the holiday list for *state* and *year*.

    1. If a cached copy (``data/holidays_{state}_{year}.json``) exists and is
       not older than *max_age_days*, it is loaded and returned.
    2. Otherwise the data is fetched from https://ferien-api.de, stored in the
       cache directory, and returned.
    """

    year = year or get_school_year()
    sanitized_year = _sanitize_year_for_filename(year)
    cache_file = CACHE_DIR / f"holidays_{state}_{sanitized_year}.json"

    # ---------------------------------------------------------------------
    # 1 ) Try the cache -----------------------------------------------------
    # ---------------------------------------------------------------------
    if cache_file.exists():
        age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if age <= timedelta(days=max_age_days):
            try:
                with cache_file.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                # Corrupted cache – remove it and fall through to refetch
                cache_file.unlink(missing_ok=True)

    # ---------------------------------------------------------------------
    # 2.) Fetch fresh from the API -----------------------------------------
    # ---------------------------------------------------------------------
    url = f"https://ferien-api.de/api/v1/holidays/{state}/{year}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Fehler beim Abrufen der Ferien-Daten: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Antwort konnte nicht als JSON gelesen werden.") from exc

    # Cache the fresh data (best-effort)
    try:
        with cache_file.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        # Caching failures should not break the function
        pass

    return data


# ---------------------------------------------------------------------------
# Public convenience wrappers -----------------------------------------------
# ---------------------------------------------------------------------------

def fetch_halfyear_report_day(state: str = "TH", year: str | int | None = None) -> str:
    """Return the date of the Zeugnis‑ (half-year) day.

    This is defined as the last school day *before* the Winterferien. The date
    string is returned in the format ``DD.MM.YYYY``.
    """
    year = get_school_year_report()
    data = _load_or_fetch_holidays(state, year)

    for entry in data:
        if "winterferien" in entry.get("name", "").lower():
            try:
                start = datetime.fromisoformat(entry["start"])
                return (start - timedelta(days=1)).strftime("%d.%m.%Y")
            except Exception as exc:
                raise RuntimeError(
                    f"Ungültiges Startdatum: {entry.get('start')} ({exc})"
                ) from exc

    raise ValueError(f"Winterferien für {state} im Jahr {year} nicht gefunden.")


def fetch_last_school_day(state: str = "TH", year: str | int | None = None) -> str:
    """Return the last school day before the Sommerferien (``DD.MM.YYYY``)."""
    year = get_school_year_report()
    data = _load_or_fetch_holidays(state, year)

    for entry in data:
        if "sommerferien" in entry.get("name", "").lower():
            try:
                start = datetime.fromisoformat(entry["start"])
                return (start - timedelta(days=1)).strftime("%d.%m.%Y")
            except Exception as exc:
                raise RuntimeError(
                    f"Ungültiges Startdatum: {entry.get('start')} ({exc})"
                ) from exc

    raise ValueError(f"Sommerferien für {state} im Jahr {year} nicht gefunden.")


# ---------------------------------------------------------------------------
# Auxiliary helpers ---------------------------------------------------------
# ---------------------------------------------------------------------------

def get_school_year(today: date | None = None) -> str:
    today = today or date.today()
    if today.month >= 8:  # August–December → new school year starts this year
        return f"{today.year}/{today.year + 1}"
    else:                 # January–July → school year started last year
        return f"{today.year - 1}/{today.year}"


def get_school_year_report(today: date | None = None) -> str:
    today = today or date.today()
    return str(today.year + 1) if today.month >= 8 else str(today.year)


if __name__ == "__main__":
    # Quick sanity-checks for the two public helpers
    state = "TH"           # Thuringia
    school_year = get_school_year()          # e.g. "2024/2025"
    calendar_year = "2026" # e.g. "2025"

    print(f"💡 School year detected: {school_year}")
    print(f"📄 Half-year report day ({state}, {calendar_year}):",
          fetch_halfyear_report_day(state, calendar_year))
    print(f"🏁 Last school day before summer break ({state}, {calendar_year}):",
          fetch_last_school_day(state, calendar_year))
