from __future__ import annotations
"""
db_cli.py – interactive PostgreSQL database chooser + optional Streamlit launcher.
"""

import argparse
import subprocess
import sys
import re
from typing import List

from dotenv import load_dotenv
load_dotenv()

from db_schema import (
    switch_engine, init_db, list_report_dbs, create_report_db, suggest_db_name, _pg_base_url,
)
from student_loader import sync_students

DB_RX = re.compile(r"^reports_(\d{4})_(\d{2})_(hj|ej)$", re.I)

def _parse_key(name: str) -> tuple[int, int]:
    m = DB_RX.fullmatch(name)
    if not m:
        return (0, 0)
    y1, _y2, term = m.groups()
    return (int(y1), 2 if term.lower() == "ej" else 1)

def _most_recent(names: List[str]) -> str | None:
    return max(names, key=_parse_key) if names else None

def choose_interactive() -> str:
    while True:
        dbs = list_report_dbs()
        print("\n===== Datenbank-Auswahl =====")
        print("1) Aktuellste DB verwenden")
        print("2) Ältere DB wählen")
        print("3) Neue DB anlegen")
        print("4) Beenden (q)")
        choice = input("Auswahl [1-4]: ").strip().lower()

        if choice in {"4", "q"}:
            raise KeyboardInterrupt

        if choice == "1":
            recent = _most_recent(dbs)
            if recent:
                return recent
            print("Keine Datenbank vorhanden.")
            continue

        if choice == "2":
            if not dbs:
                print("Keine Datenbank vorhanden.")
                continue
            for i, name in enumerate(dbs, 1):
                print(f"  {i}) {name}")
            sel = input("Nummer wählen: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(dbs):
                return dbs[int(sel) - 1]
            print("Ungültige Auswahl.")
            continue

        if choice == "3":
            term = ""
            while term not in {"hj", "ej"}:
                term = input("Termin [hj/ej]: ").strip().lower()
            default = suggest_db_name(term)
            name = input(f"DB-Name [{default}]: ").strip() or default
            if not DB_RX.fullmatch(name):
                print(f"⚠️  Ungültiger Name '{name}'. Erwartet: reports_YYYY_YY_hj/ej")
                continue
            is_new = name not in dbs
            if is_new:
                create_report_db(name)
                print(f"PostgreSQL-Datenbank '{name}' erstellt.")
            switch_engine(name)
            init_db(drop=False, populate=True)
            if is_new:
                sync_students()
                print("Schüler importiert.")
            else:
                print("Bestehende DB gewählt / Schema geprüft.")
            return name

        print("Bitte 1-4 eingeben.")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    try:
        db_name = choose_interactive()
    except KeyboardInterrupt:
        print("\nAbbruch.")
        sys.exit(1)

    print(db_name)

    if args.run:
        subprocess.run(
            ["streamlit", "run", "KompetenzenTool.py", "--", "--db", db_name],
            check=True,
        )

if __name__ == "__main__":
    main()
