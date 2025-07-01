from __future__ import annotations
"""
db_cli.py – interactive database chooser + optional Streamlit launcher.

Usage
-----
python db_cli.py              # interactive menu, prints chosen path
python db_cli.py --run        # menu + starts Streamlit UI afterwards

The script is also installable as console‑script entry point (see setup.cfg):
    db-cli --run
"""

import argparse
import subprocess
import sys
import re
from pathlib import Path
from typing import List

from sqlalchemy import create_engine

from db_schema import Base, switch_engine, init_db
from student_loader import sync_students
from time_functions import get_school_year

# ---------------------------------------------------------------------------

DATA_DIR = Path("db")          # central directory for all report databases
DATA_DIR.mkdir(exist_ok=True)

DB_RX = re.compile(r"reports_(\d{4}-\d{2})_(hj|ej)\.db", re.I)

# ---------- helpers --------------------------------------------------------

def _list_dbs() -> List[str]:
    """Return sorted list of existing DB filenames inside DATA_DIR."""
    return sorted(f.name for f in DATA_DIR.glob("reports_*.db"))

def _parse_key(name: str) -> tuple[int, int]:
    """Helper key: (schoolyear, term) where term ej=2, hj=1 for sorting."""
    m = DB_RX.fullmatch(name)
    if not m:
        return (0, 0)
    y, term = m.groups()
    return (int(y.split("-")[0]), 2 if term.lower() == "ej" else 1)

def _most_recent(files: List[str]) -> str | None:
    """Return filename of most recent DB or None."""
    return max(files, key=_parse_key) if files else None

def _suggest_filename(term: str) -> str:
    """Return default filename for new DB such as reports_2025-26_hj.db."""
    sy = get_school_year().replace("/", "-")   # e.g. "2025-26"
    return f"reports_{sy}_{term}.db"

def _create_database(path: Path) -> None:
    """Create empty schema in given SQLite file."""
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)

# ---------- interactive menu ----------------------------------------------

def choose_interactive() -> Path:
    """CLI menu to choose or create a database; returns Path."""
    while True:
        files = _list_dbs()
        print("\n===== Datenbank-Auswahl =====")
        print("1) Aktuellste DB verwenden")
        print("2) Ältere DB wählen")
        print("3) Neue DB anlegen")
        print("4) Beenden (q)")
        choice = input("Auswahl [1-4]: ").strip().lower()

        if choice in {"4", "q"}:
            raise KeyboardInterrupt

        # 1) most recent
        if choice == "1":
            recent = _most_recent(files)
            if recent:
                return DATA_DIR / recent
            print("Keine Datenbank vorhanden.")
            continue

        # 2) pick from list
        if choice == "2":
            if not files:
                print("Keine Datenbank vorhanden.")
                continue
            for i, f in enumerate(files, 1):
                print(f"{i}) {f}")
            sel = input("Nummer wählen: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(files):
                return DATA_DIR / files[int(sel) - 1]
            print("Ungültige Auswahl.")
            continue

        # 3) create new
        if choice == "3":
            term = ""
            while term not in {"hj", "ej"}:
                term = input("Termin [hj/ej]: ").strip().lower()

            default = _suggest_filename(term)
            name    = input(f"Dateiname [{default}]: ").strip() or default
            path    = DATA_DIR / name

            is_new = not path.exists()
            path.parent.mkdir(exist_ok=True)
            path.touch(exist_ok=True)

            # point ORM to new file and ensure schema / default data
            switch_engine(path)
            init_db(drop=False, populate=True)

            if is_new:
                sync_students()
                print("Neue DB angelegt & Schüler importiert.")
            else:
                print("Bestehende DB gewählt / Schema geprüft.")
            return path

        print("Bitte 1-4 eingeben.")

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Interaktive DB-Auswahl und optionaler Streamlit‑Start."
    )
    ap.add_argument(
        "--run",
        action="store_true",
        help="Starte nach Auswahl direkt die Streamlit‑UI"
    )
    args = ap.parse_args()

    try:
        chosen = choose_interactive()
    except KeyboardInterrupt:
        print("\nAbbruch.")
        sys.exit(1)

    # stdout only path -> other scripts may capture it
    print(chosen.resolve())

    if args.run:
        print(f"\nStarte Streamlit mit {chosen.name} …")
        subprocess.run(
            ["streamlit", "run", "KompetenzenTool.py", "--", "--db", str(chosen.resolve())],
            check=True,
        )

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
