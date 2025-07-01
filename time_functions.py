import requests
from datetime import datetime, timedelta, date

def fetch_halfyear_report_day(state='TH', year=None):
    year = year or get_school_year()
    url = f"https://ferien-api.de/api/v1/holidays/{state}/{year}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Fehler beim Abrufen der Ferien-Daten: {e}")
    except ValueError:
        raise RuntimeError("Antwort konnte nicht als JSON gelesen werden.")
    
    for entry in data:
        if "winterferien" in entry.get("name", "").lower():
            try:
                start = datetime.fromisoformat(entry["start"])
                return (start - timedelta(days=1)).date().strftime("%d.%m.%y")
            except Exception as e:
                raise RuntimeError(f"Ungültiges Startdatum: {entry.get('start')} ({e})")
    
    raise ValueError(f"Winterferien für {state} im Jahr {year} nicht gefunden.")

def fetch_last_school_day(state='TH', year=None):
    year = year or get_school_year()
    url = f"https://ferien-api.de/api/v1/holidays/{state}/{year}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Fehler beim Abrufen der Ferien-Daten: {e}")
    except ValueError:
        raise RuntimeError("Antwort konnte nicht als JSON gelesen werden.")
    
    for entry in data:
        if "sommerferien" in entry.get("name", "").lower():
            try:
                start = datetime.fromisoformat(entry["start"])
                return (start - timedelta(days=1)).date().strftime("%d.%m.%y")
            except Exception as e:
                raise RuntimeError(f"Ungültiges Startdatum: {entry.get('start')} ({e})")
    
    raise ValueError(f"Sommerferien für {state} im Jahr {year} nicht gefunden.")


def get_school_year(today=None):
    today = today or date.today()
    if today.month >= 8:  # August–December → new school year starts this year
        return f"{today.year}/{today.year + 1}"
    else:                 # January–July → school year started last year
        return f"{today.year - 1}/{today.year}"

def get_school_year_report(today=None):
    today = today or date.today()
    if today.month >= 8:  # August–December → new school year starts this year
        return f"{today.year + 1}"
    else:                 # January–July → school year started last year
        return f"{today.year}"
