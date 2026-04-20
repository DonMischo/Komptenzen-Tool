from dotenv import load_dotenv
load_dotenv()

from db_schema import switch_engine, init_db, list_report_dbs, create_report_db
from student_loader import sync_students
import argparse, sys

ap = argparse.ArgumentParser()
ap.add_argument("--db", type=str, help="PostgreSQL database name, e.g. reports_2025_26_hj")
args = ap.parse_args()

if args.db:
    # Create the PostgreSQL database if it doesn't exist yet
    if args.db not in list_report_dbs():
        print(f"Datenbank '{args.db}' nicht gefunden – wird angelegt …")
        create_report_db(args.db)
    switch_engine(args.db)
    init_db(drop=False, populate=True)
    sync_students()

# Engine steht → jetzt erst UI importieren
import ui_components as ui
ui.run_ui()
