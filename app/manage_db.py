# manage_db.py
import argparse
from sqlalchemy.orm import Session
from db_schema import ENGINE, switch_engine, init_db, populate_from_dict, create_report_db, list_report_dbs
from competence_data import COMPETENCES

def main():
    ap = argparse.ArgumentParser(description="DB initialisieren / updaten")
    ap.add_argument("cmd", choices=["init", "drop", "populate"])
    ap.add_argument("--db", type=str, help="PostgreSQL database name (e.g. reports_2025_26_hj)")
    ap.add_argument("--force", action="store_true", help="Schema droppen vor init")
    args = ap.parse_args()

    if args.db:
        if args.db not in list_report_dbs():
            create_report_db(args.db)
            print(f"PostgreSQL-Datenbank '{args.db}' erstellt.")
        switch_engine(args.db)

    if args.cmd == "init":
        init_db(drop=args.force)
        print("✔ Datenbank-Schema angelegt.")
    elif args.cmd == "drop":
        init_db(drop=True)
        print("✔ Schema gelöscht und neu angelegt.")
    elif args.cmd == "populate":
        with Session(ENGINE) as ses:
            populate_from_dict(COMPETENCES, ses)
            print("✔ Kompetenzen eingelesen.")

if __name__ == "__main__":
    main()
