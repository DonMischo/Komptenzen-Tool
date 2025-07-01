from pathlib import Path
from db_schema import switch_engine, init_db
from student_loader import sync_students
import argparse, sys

ap = argparse.ArgumentParser()
ap.add_argument("--db", type=Path, help="Pfad zur SQLite-Datei")
args = ap.parse_args()

if args.db:
    dbfile = args.db.resolve()
    if not dbfile.exists():
        switch_engine(dbfile)      # Datei anlegen & Tabellen
        init_db(drop=False, populate=True)
        sync_students()
    else:
        switch_engine(dbfile)
else:
    print("⚠️  --db nicht gesetzt – benutze kompetenzen.db")

# Engine steht → jetzt erst UI importieren
import ui_components as ui
ui.run_ui()
